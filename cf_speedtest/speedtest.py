#! /usr/bin/env python3
from __future__ import annotations

import argparse
import math
import statistics
import time
from timeit import default_timer as timer

import requests
import urllib3

import cf_speedtest.locations as locations
import cf_speedtest.options as options

REQ_SESSION = requests.Session()

CGI_ENDPOINT = 'https://speed.cloudflare.com/cdn-cgi/trace'
DOWNLOAD_ENDPOINT = 'https://speed.cloudflare.com/__down?measId=0&bytes={}'
UPLOAD_ENDPOINT = 'https://speed.cloudflare.com/__up?measId=0'

UPLOAD_HEADERS = {
    'Connection': 'keep-alive',
    'DNT': '1',
    'Content-Type': 'text/plain;charset=UTF-8',
    'Accept': '*/*',
}

PROXY_DICT = None
VERIFY_SSL = True
OUTPUT_FILE = None

# Could use python's statistics library, but quantiles are only available
# in version 3.8 and above


def percentile(data: list, percentile: int) -> float:
    size = len(data)
    return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]

# returns ms of how long cloudflare took to process the request, this is in the Server-Timing header


def get_server_timing(server_timing: str) -> float:
    split = server_timing.split(';')
    for part in split:
        if "dur=" in part:
            split = part.split("=")[1]
            if ', ' in part:
                # Sometimes it will be in the format `dur=56.999922, cfL4`
                split = part.split("=")[1].split(', ')[0]
            return float(split) / 1000

# given an amount of bytes, upload it and return the elapsed seconds taken


def upload_test(total_bytes: int) -> int | float:
    start = timer()

    r = REQ_SESSION.post(
        UPLOAD_ENDPOINT, data=bytearray(
            total_bytes,
        ), headers=UPLOAD_HEADERS, verify=VERIFY_SSL, proxies=PROXY_DICT,
    )
    r.raise_for_status()
    total_time_taken = timer() - start

    # trust what the server says as time taken
    server_time_taken = get_server_timing(r.headers['Server-Timing'])

    if OUTPUT_FILE:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as datafile:
            datafile.write(
                f'{time.time()},up,{total_bytes},{total_time_taken},{server_time_taken}\n',
            )

    return total_bytes, server_time_taken

# given an amount of bytes, download it and return the elapsed seconds taken


def download_test(total_bytes: int) -> int | float:
    endpoint = DOWNLOAD_ENDPOINT.format(total_bytes)
    start = timer()

    r = REQ_SESSION.get(endpoint, verify=VERIFY_SSL, proxies=PROXY_DICT)
    r.raise_for_status()

    total_time_taken = timer() - start

    content_size = len(r.content)
    server_time_taken = get_server_timing(r.headers['Server-Timing'])

    if OUTPUT_FILE:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as datafile:
            datafile.write(
                f'{time.time()},down,{content_size},{total_time_taken},{server_time_taken}\n',
            )

    return content_size, total_time_taken - server_time_taken

# calculates http "latency" by measuring download of an empty payload


def latency_test() -> float:
    endpoint = DOWNLOAD_ENDPOINT.format(0)

    start = timer()
    r = REQ_SESSION.get(endpoint, verify=VERIFY_SSL,  proxies=PROXY_DICT)
    r.raise_for_status()

    total_time_taken = timer() - start
    server_time_taken = get_server_timing(r.headers['Server-Timing'])

    if OUTPUT_FILE:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as datafile:
            datafile.write(
                f'{time.time()},down,{len(r.content)},{total_time_taken},{server_time_taken}\n',
            )

    return total_time_taken - server_time_taken

# See https://speed.cloudflare.com/cdn-cgi/trace


def get_our_country() -> str:
    r = REQ_SESSION.get(CGI_ENDPOINT, verify=VERIFY_SSL,  proxies=PROXY_DICT)
    r.raise_for_status()

    cgi_data = r.text
    cgi_dict = {
        k: v for k, v in [
            line.split(
                '=',
            ) for line in cgi_data.splitlines()
        ]
    }

    return cgi_dict.get('loc') or 'Unknown'


def preamble() -> str:
    r = REQ_SESSION.get(
        DOWNLOAD_ENDPOINT.format(
            0,
        ), verify=VERIFY_SSL,  proxies=PROXY_DICT,
    )
    r.raise_for_status()

    our_ip = r.headers.get('cf-meta-ip')
    colo = r.headers.get('cf-meta-colo')
    server_city = colo
    server_country = next(
        (
            loc.get(
                'cca2',
            ) or 'Unknown' for loc in locations.SERVER_LOCATIONS if loc['iata'] == colo.upper()
        ), 'Unknown',
    )
    preamble_str = f'Your IP:\t{our_ip} ({get_our_country()})\nServer loc:\t{server_city} ({colo}) - ({server_country})'

    return preamble_str

# runs x amount of y-byte tests, given a test_type ("down" or "up")
# returns a list of measurements in bits per second


def run_tests(test_type: str, bytes_to_xfer: int, iteration_count: int = 8) -> list:
    measurements = []

    for i in range(0, iteration_count):
        if test_type == 'down':
            xferd_bytes_total, seconds_taken = download_test(bytes_to_xfer)
        elif test_type == 'up':
            xferd_bytes_total, seconds_taken = upload_test(bytes_to_xfer)
        else:
            return measurements

        bits_per_second = (int(xferd_bytes_total) / seconds_taken) * 8
        measurements.append(bits_per_second)

    return measurements

# runs a standard test of upload and download, similar to what
# simulates what is ran on speed.cloudflare.com


def run_standard_test(
    measurement_sizes: list,
    measurement_percentile: int = 90,
    verbose: bool = False,
    test_patience: int = 15,
) -> dict:
    LATENCY_MEASUREMENTS = []
    DOWNLOAD_MEASUREMENTS = []
    UPLOAD_MEASUREMENTS = []

    if verbose:
        print(preamble(), '\n')

    latency_test()  # ignore first request as it contains http connection setup
    for i in range(0, 20):
        LATENCY_MEASUREMENTS.append(latency_test() * 1000)

    # Assume the median latency is our latency (just like the website)
    latency = percentile(LATENCY_MEASUREMENTS, 50)
    jitter = statistics.stdev(LATENCY_MEASUREMENTS)
    if verbose:
        print(f"{'Latency:':<16} {latency:.2f} ms")
        print(f"{'Jitter:':<16} {jitter:.2f} ms")
        print('Running speed tests...\n')

    first_dl_test, first_ul_test = True, True
    continue_dl_test, continue_ul_test = True, True
    current_up_speed_mbps = 0
    current_down_speed_mbps = 0

    # The SLOWEST test should take no longer than 30 seconds
    for i in range(0, len(measurement_sizes)):
        measurement = measurement_sizes[i]
        download_test_count = (-2 * i + 12) 	# this is how the website does it
        upload_test_count = (-2 * i + 10) 		# this is how the website does it
        total_download_bytes = measurement * download_test_count
        total_upload_bytes = measurement * upload_test_count

        if not first_dl_test:
            if current_down_speed_mbps * test_patience < total_download_bytes / 125000:
                continue_dl_test = False
        else:
            first_dl_test = False

        if continue_dl_test:
            # print(f"Testing download ({measurement / 1_000_000:.2f}MiB) ({download_test_count} time(s))")
            DOWNLOAD_MEASUREMENTS += run_tests(
                'down',
                measurement, download_test_count,
            )
            current_down_speed_mbps = percentile(
                DOWNLOAD_MEASUREMENTS, measurement_percentile,
            ) / 1_000_000
            if verbose:
                # print(f"Current down: {current_down_speed_mbps:.2f} Mbit/sec")
                print(
                    f"{'Current speeds:':<24} {'Down: '}{current_down_speed_mbps:.2f} Mbit/sec\t"
                    f"{'Up: '}{current_up_speed_mbps:.2f} Mbit/sec",
                )

        if not first_ul_test:
            if current_up_speed_mbps * test_patience < total_upload_bytes / 125_000:
                continue_ul_test = False
        else:
            first_ul_test = False

        if continue_ul_test:
            # print(f"Testing upload ({measurement / 1_000_000:.2f}MiB) ({upload_test_count} time(s))")
            UPLOAD_MEASUREMENTS += run_tests(
                'up',
                measurement, upload_test_count,
            )
            current_up_speed_mbps = percentile(
                UPLOAD_MEASUREMENTS, measurement_percentile,
            ) / 1_000_000
            if verbose:
                # print(f"Current up: {current_up_speed_mbps:.2f} Mbit/sec")
                print(
                    f"{'Current speeds:':<24} {'Down: '}{current_down_speed_mbps:.2f} Mbit/sec\t"
                    f"{'Up: '}{current_up_speed_mbps:.2f} Mbit/sec",
                )

    # all raw measurements are in bits per second
    pctile_download = percentile(DOWNLOAD_MEASUREMENTS, measurement_percentile)
    pctile_upload = percentile(UPLOAD_MEASUREMENTS, measurement_percentile)
    download_stdev = statistics.stdev(DOWNLOAD_MEASUREMENTS)
    upload_stdev = statistics.stdev(UPLOAD_MEASUREMENTS)

    return {
        'download_measurements': DOWNLOAD_MEASUREMENTS,
        'upload_measurements': UPLOAD_MEASUREMENTS,
        'latency_measurements': LATENCY_MEASUREMENTS,
        'download_speed': pctile_download,
        'upload_speed': pctile_upload,
        'download_stdev': download_stdev,
        'upload_stdev': upload_stdev,
    }


def main(argv=None) -> int:
    global PROXY_DICT, VERIFY_SSL, OUTPUT_FILE
    # disable annoying warning when using verify=False in requests.get("x", verify=False)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    parser = argparse.ArgumentParser()
    parser_with_args = options.add_run_options(parser)

    args = parser_with_args.parse_args(argv)
    percentile = args.percentile
    VERIFY_SSL = args.verifyssl
    OUTPUT_FILE = args.output
    patience = args.testpatience
    proxy = args.proxy

    # clear the output file
    if OUTPUT_FILE:
        open(args.output, 'w').close()

    # set up proxy dictionary
    if proxy:
        if proxy.startswith('socks'):
            PROXY_DICT = {'http': f'{proxy}', 'https': f'{proxy}'}
        elif proxy.startswith('http'):
            PROXY_DICT = {'http': f'{proxy}', 'https': f'{proxy}'}
        else:
            PROXY_DICT = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}',
            }
    else:
        PROXY_DICT = None

    # Taken from speed.cloudflare.com
    # byte count for each test, ranging from 100KB to 250MB
    measurement_sizes =\
        [
            100_000,
            1_000_000,
            10_000_000,
            25_000_000,
            100_000_000,
            250_000_000,
        ]

    speeds = run_standard_test(measurement_sizes, percentile, True, patience)

    d = speeds['download_speed']
    u = speeds['upload_speed']
    d_s = speeds['download_stdev']  # noqa
    u_s = speeds['upload_stdev']   # noqa

    print(
        f"{args.percentile}{'th percentile results:':<24} Down: {d/1_000_000:.2f} Mbit/sec\t"
        f'Up: {u/1_000_000:.2f} Mbit/sec',
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

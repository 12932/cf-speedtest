from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
from timeit import default_timer as timer
from typing import Any

import requests
import urllib3

from cf_speedtest import locations, options

REQ_SESSION = requests.Session()
REQ_SESSION.headers.update(
    {
        'Referer': 'https://speed.cloudflare.com/',
        'Origin': 'https://speed.cloudflare.com',
    }
)

CGI_ENDPOINT = 'https://speed.cloudflare.com/cdn-cgi/trace'
META_ENDPOINT = 'https://speed.cloudflare.com/meta'
DOWNLOAD_ENDPOINT = 'https://speed.cloudflare.com/__down?measId=0&bytes={}'
UPLOAD_ENDPOINT = 'https://speed.cloudflare.com/__up?measId=0'

UPLOAD_HEADERS = {
    'Connection': 'keep-alive',
    'DNT': '1',
    'Content-Type': 'text/plain;charset=UTF-8',
    'Accept': '*/*',
}

# Taken from speed.cloudflare.com: byte count for each test, ranging from 100KB to 250MB
MEASUREMENT_SIZES = [
    100_000,
    1_000_000,
    10_000_000,
    25_000_000,
    100_000_000,
    250_000_000,
]

PROXY_DICT: dict[str, str] | None = None
VERIFY_SSL = True
OUTPUT_FILE: str | None = None

# Server-Timing metrics emitted by speed.cloudflare.com. Older deployments sent a single
# `cfRequestDuration;dur=N`; current ones send `cfSpeedEdge;dur=N, cfSpeedWorker;dur=N`
# (plus an unrelated `cfL4;desc=...`). These patterns mirror Cloudflare's own JS client.
_CF_REQUEST_DURATION_RE = re.compile(r'(?:^|,\s*)cfReq(?:uest)?Dur(?:ation)?;\s*dur=([0-9.]+)', re.IGNORECASE)
_CF_SPEED_DURATION_RE = re.compile(r'(?:^|,\s*)cfSpeed[a-zA-Z]*;\s*dur=([0-9.]+)', re.IGNORECASE)


def percentile(data: list[float], percentile: int) -> float:
    """Return the value at ``percentile`` (0-100) of ``data`` using the nearest-rank method."""
    if not data:
        return 0.0
    ordered = sorted(data)
    rank = math.ceil(len(ordered) * percentile / 100)
    return ordered[max(rank, 1) - 1]


def get_server_timing(server_timing: str | None) -> float:
    """Return the seconds Cloudflare spent processing a request, from its ``Server-Timing`` header.

    Prefers ``cfRequestDuration`` when present, otherwise sums every ``cfSpeed*`` metric.
    Missing or unrecognised headers yield 0.0 so a measurement is never inflated.
    """
    if not server_timing:
        return 0.0

    match = _CF_REQUEST_DURATION_RE.search(server_timing)
    if match:
        return float(match.group(1)) / 1000

    total_ms = sum(float(m.group(1)) for m in _CF_SPEED_DURATION_RE.finditer(server_timing))
    return total_ms / 1000


def _record_measurement(direction: str, byte_count: int, total_seconds: float, server_seconds: float) -> None:
    """Append one raw measurement row to the CSV output file, if one was requested."""
    if not OUTPUT_FILE:
        return
    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as datafile:
            datafile.write(f'{time.time()},{direction},{byte_count},{total_seconds},{server_seconds}\n')
    except OSError:
        pass  # Silently ignore file write errors


def upload_test(total_bytes: int) -> tuple[int, float]:
    """Upload ``total_bytes`` and return ``(bytes_sent, seconds_taken)`` excluding server processing time."""
    start = timer()

    try:
        r = REQ_SESSION.post(
            UPLOAD_ENDPOINT,
            data=bytearray(total_bytes),
            headers=UPLOAD_HEADERS,
            verify=VERIFY_SSL,
            proxies=PROXY_DICT,
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'Upload test failed: {e}') from e

    total_time_taken = timer() - start
    server_time_taken = get_server_timing(r.headers.get('Server-Timing'))
    _record_measurement('up', total_bytes, total_time_taken, server_time_taken)

    return total_bytes, total_time_taken - server_time_taken


def download_test(total_bytes: int) -> tuple[int, float]:
    """Download ``total_bytes`` and return ``(bytes_received, seconds_taken)`` excluding server processing time."""
    endpoint = DOWNLOAD_ENDPOINT.format(total_bytes)
    start = timer()

    try:
        r = REQ_SESSION.get(endpoint, verify=VERIFY_SSL, proxies=PROXY_DICT, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'Download test failed: {e}') from e

    total_time_taken = timer() - start
    content_size = len(r.content)
    server_time_taken = get_server_timing(r.headers.get('Server-Timing'))
    _record_measurement('down', content_size, total_time_taken, server_time_taken)

    return content_size, total_time_taken - server_time_taken


def latency_test() -> float:
    """Measure HTTP round-trip seconds by downloading an empty payload."""
    endpoint = DOWNLOAD_ENDPOINT.format(0)

    start = timer()
    try:
        r = REQ_SESSION.get(endpoint, verify=VERIFY_SSL, proxies=PROXY_DICT, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'Latency test failed: {e}') from e

    total_time_taken = timer() - start
    server_time_taken = get_server_timing(r.headers.get('Server-Timing'))
    _record_measurement('down', len(r.content), total_time_taken, server_time_taken)

    return total_time_taken - server_time_taken


def get_our_country() -> str:
    """Return our two-letter country code as seen by Cloudflare (see /cdn-cgi/trace)."""
    try:
        r = REQ_SESSION.get(CGI_ENDPOINT, verify=VERIFY_SSL, proxies=PROXY_DICT, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'Failed to get country info: {e}') from e

    cgi_dict = dict(line.split('=', 1) for line in r.text.splitlines() if '=' in line)
    return cgi_dict.get('loc') or 'Unknown'


def get_meta() -> dict[str, str]:
    """Return client/server location metadata from speed.cloudflare.com/meta.

    Every value defaults to ``'Unknown'`` when Cloudflare omits it (see issue #13).
    """
    try:
        r = REQ_SESSION.get(META_ENDPOINT, verify=VERIFY_SSL, proxies=PROXY_DICT, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f'Failed to get server metadata: {e}') from e

    meta = r.json()
    colo_info = meta.get('colo') or {}
    colo = colo_info.get('iata') or 'Unknown'

    # Cloudflare's /meta usually carries the server country, otherwise look it up from the IATA code
    server_country = colo_info.get('cca2') or next(
        (loc.get('cca2') or 'Unknown' for loc in locations.SERVER_LOCATIONS if loc['iata'] == colo),
        'Unknown',
    )

    return {
        'client_ip': meta.get('clientIp') or 'Unknown',
        'client_country': meta.get('country') or 'Unknown',
        'server_city': colo_info.get('city') or colo,
        'server_iata': colo,
        'server_country': server_country,
    }


def preamble() -> str:
    """Human readable summary of where we are and which Cloudflare PoP we hit."""
    meta = get_meta()
    return (
        f'Your IP:\t{meta["client_ip"]} ({meta["client_country"]})\n'
        f'Server loc:\t{meta["server_city"]} ({meta["server_iata"]}) - ({meta["server_country"]})'
    )


def build_proxy_dict(proxy: str | None) -> dict[str, str] | None:
    """Turn a ``--proxy`` argument into a ``requests`` proxies mapping (HTTP is assumed if no scheme)."""
    if not proxy:
        return None
    if not proxy.startswith(('socks', 'http')):
        proxy = f'http://{proxy}'
    return {'http': proxy, 'https': proxy}


def run_tests(test_type: str, bytes_to_xfer: int, iteration_count: int = 8) -> list[float]:
    """Run ``iteration_count`` transfers of ``bytes_to_xfer`` and return each result in bits per second."""
    measurements: list[float] = []

    for _ in range(iteration_count):
        if test_type == 'down':
            xferd_bytes_total, seconds_taken = download_test(bytes_to_xfer)
        elif test_type == 'up':
            xferd_bytes_total, seconds_taken = upload_test(bytes_to_xfer)
        else:
            return measurements

        if seconds_taken > 0:
            measurements.append((xferd_bytes_total / seconds_taken) * 8)

    return measurements


def run_standard_test(
    measurement_sizes: list[int],
    measurement_percentile: int = 90,
    verbose: bool = False,
    test_patience: int = 15,
    skip_slow_tests: bool = True,
) -> dict[str, Any]:
    """Run the same sequence of latency, download and upload tests as speed.cloudflare.com.

    Speeds in the result are in bits per second, latency values in milliseconds.
    """
    latency_measurements: list[float] = []
    download_measurements: list[float] = []
    upload_measurements: list[float] = []

    latency_test()  # ignore first request as it contains http connection setup
    for _ in range(20):
        latency_measurements.append(latency_test() * 1000)

    # Assume the median latency is our latency (just like the website)
    latency = percentile(latency_measurements, 50)
    jitter = statistics.stdev(latency_measurements)
    if verbose:
        print(f'{"Latency:":<16} {latency:.2f} ms')
        print(f'{"Jitter:":<16} {jitter:.2f} ms')
        print('Running speed tests...\n')

    continue_dl_test, continue_ul_test = True, True
    current_up_speed_mbps = 0.0
    current_down_speed_mbps = 0.0

    def print_progress() -> None:
        if verbose:
            print(
                f'{"Current speeds:":<24} Down: {current_down_speed_mbps:.2f} Mbit/sec\t'
                f'Up: {current_up_speed_mbps:.2f} Mbit/sec',
            )

    for i, measurement in enumerate(measurement_sizes):
        download_test_count = -2 * i + 12  # this is how the website does it
        upload_test_count = -2 * i + 10  # this is how the website does it
        total_download_bytes = measurement * download_test_count
        total_upload_bytes = measurement * upload_test_count

        # After the first size, skip any size that would take longer than test_patience at the current speed
        if skip_slow_tests and i > 0 and current_down_speed_mbps * test_patience < total_download_bytes / 125_000:
            continue_dl_test = False

        if continue_dl_test:
            download_measurements += run_tests('down', measurement, download_test_count)
            current_down_speed_mbps = percentile(download_measurements, measurement_percentile) / 1_000_000
            print_progress()

        if skip_slow_tests and i > 0 and current_up_speed_mbps * test_patience < total_upload_bytes / 125_000:
            continue_ul_test = False

        if continue_ul_test:
            upload_measurements += run_tests('up', measurement, upload_test_count)
            current_up_speed_mbps = percentile(upload_measurements, measurement_percentile) / 1_000_000
            print_progress()

    download_stdev = statistics.stdev(download_measurements) if len(download_measurements) >= 2 else 0.0
    upload_stdev = statistics.stdev(upload_measurements) if len(upload_measurements) >= 2 else 0.0

    return {
        'download_measurements': download_measurements,
        'upload_measurements': upload_measurements,
        'latency_measurements': latency_measurements,
        'latency': latency,
        'jitter': jitter,
        'download_speed': percentile(download_measurements, measurement_percentile),
        'upload_speed': percentile(upload_measurements, measurement_percentile),
        'download_stdev': download_stdev,
        'upload_stdev': upload_stdev,
    }


def format_json_result(meta: dict[str, str], results: dict[str, Any], measurement_percentile: int) -> dict[str, Any]:
    """Shape a ``run_standard_test`` result into the stable document printed by ``--json``."""
    return {
        'client_ip': meta['client_ip'],
        'client_country': meta['client_country'],
        'server': {
            'city': meta['server_city'],
            'iata': meta['server_iata'],
            'country': meta['server_country'],
        },
        'percentile': measurement_percentile,
        'latency_ms': round(results['latency'], 3),
        'jitter_ms': round(results['jitter'], 3),
        'download_mbps': round(results['download_speed'] / 1_000_000, 3),
        'upload_mbps': round(results['upload_speed'] / 1_000_000, 3),
        'download_stdev_mbps': round(results['download_stdev'] / 1_000_000, 3),
        'upload_stdev_mbps': round(results['upload_stdev'] / 1_000_000, 3),
        'latency_measurements_ms': results['latency_measurements'],
        'download_measurements_bps': results['download_measurements'],
        'upload_measurements_bps': results['upload_measurements'],
    }


def main(argv: list[str] | None = None) -> int:
    global PROXY_DICT, VERIFY_SSL, OUTPUT_FILE
    # disable annoying warning when using verify=False in requests.get("x", verify=False)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    parser = argparse.ArgumentParser(
        prog='cf-speedtest',
        description='Command-line internet speed test using speed.cloudflare.com',
    )
    args = options.add_run_options(parser).parse_args(argv)

    VERIFY_SSL = args.verifyssl
    OUTPUT_FILE = args.output
    PROXY_DICT = build_proxy_dict(args.proxy)

    # clear the output file
    if OUTPUT_FILE:
        open(OUTPUT_FILE, 'w', encoding='utf-8').close()

    try:
        if args.json:
            meta = get_meta()
            results = run_standard_test(
                MEASUREMENT_SIZES,
                args.percentile,
                verbose=False,
                test_patience=args.testpatience,
                skip_slow_tests=not args.disableskipping,
            )
            print(json.dumps(format_json_result(meta, results, args.percentile), indent=2))
            return 0

        print(preamble(), '\n')
        results = run_standard_test(
            MEASUREMENT_SIZES,
            args.percentile,
            verbose=True,
            test_patience=args.testpatience,
            skip_slow_tests=not args.disableskipping,
        )
    except RuntimeError as e:
        print(f'error: {e}', file=sys.stderr)
        return 1

    down_mbps = results['download_speed'] / 1_000_000
    up_mbps = results['upload_speed'] / 1_000_000
    print(
        f'{args.percentile}{"th percentile results:":<24} Down: {down_mbps:.2f} Mbit/sec\tUp: {up_mbps:.2f} Mbit/sec',
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

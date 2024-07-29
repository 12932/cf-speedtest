from __future__ import annotations

import argparse


def str_to_bool(s: str) -> bool:
    if isinstance(s, bool):
        return s
    if s.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif s.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(
            f'Boolean value expected, received {s!r}',
        )


def valid_percentile(s: str) -> int:
    try:
        value = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f'Expected integer between 0 and 100, received {s!r}',
        )

    if not (0 <= value <= 100):
        raise argparse.ArgumentTypeError(
            f'Expected integer between 0 and 100, received {s}',
        )

    return value


def add_run_options(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='The file to output the csv data of measurements to',
    )

    parser.add_argument(
        '--percentile', '-p',
        default=90,
        type=valid_percentile,
        help=(
            'The percentile of measurements to be considered download speed '
            ' where default is 90 https://en.wikipedia.org/wiki/Percentile'
        ),
    )

    parser.add_argument(
        '--verifyssl', '-k',
        default=True,
        type=str_to_bool,
        help=(
            'Whether to verify that the server connection is secure by validating the server '
            'certificate has the correct name and verifies successfully using this machines certificate store'
        ),
    )

    parser.add_argument(
        '--proxy', '-x',
        default=None,
        type=str,
        help=(
            'Use the specified proxy. Supports HTTP/HTTPS/SOCKS5 with or without authentication'
        ),
    )

    parser.add_argument(
        '--testpatience', '-t',
        type=int,
        default=20,
        help='The longest time to wait for an individual test to run. NOTICE: When used with --disableskipping, --testpatience will be ignored',
    )

    parser.add_argument(
        '--disableskipping', '-s',
        action='store_true',
        help='Dont skip any speed test. This will ignore any --testpatience setting ',
    )

    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output results of tests in JSON format. NOTICE: When using this option, output will be delayed until the execution is finished',
    )

    return parser

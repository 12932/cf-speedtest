from __future__ import annotations

import pytest

from cf_speedtest import options
from cf_speedtest import speedtest


@pytest.mark.parametrize(
    'input_str, expected', [
        ('yes', True),
        ('no', False),
        ('true', True),
        ('false', False),
        ('1', True),
        ('0', False),
        ('YES', True),
        ('NO', False),
        ('True', True),
        ('False', False),
        ('y', True),
        ('n', False),
    ],
)
def test_str_to_bool_valid(input_str, expected):
    assert options.str_to_bool(input_str) == expected


@pytest.mark.parametrize('input_str', ['invalid', 'maybe', '2', '-1'])
def test_str_to_bool_invalid(input_str):
    with pytest.raises(speedtest.argparse.ArgumentTypeError):
        options.str_to_bool(input_str)


@pytest.mark.parametrize(
    'input_str, expected', [
        ('0', 0),
        ('50', 50),
        ('100', 100),
    ],
)
def test_valid_percentile_valid(input_str, expected):
    assert options.valid_percentile(input_str) == expected


@pytest.mark.parametrize('input_str', ['-1', '101', 'invalid', '50.5'])
def test_valid_percentile_invalid(input_str):
    with pytest.raises(speedtest.argparse.ArgumentTypeError):
        options.valid_percentile(input_str)

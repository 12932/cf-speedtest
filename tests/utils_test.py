from __future__ import annotations

import pytest

from cf_speedtest import speedtest


@pytest.mark.parametrize(
    'data, percentile, expected', [
        ([1, 2, 3, 4, 5], 50, 3),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90, 9),
        ([1, 1, 1, 1, 1], 100, 1),
        ([1, 2, 3, 4, 5], 0, 1),
    ],
)
def test_percentile(data, percentile, expected):
    assert speedtest.percentile(data, percentile) == expected


@pytest.mark.parametrize(
    'server_timing, expected', [
        ('dur=1234.5', 1.2345),
        ('key=value;dur=5678.9', 5.6789),
        ('invalid', 0.0),
        ('dur=1000', 1.0),
        ('start=0;dur=500;desc="Backend"', 0.5),
    ],
)
def test_get_server_timing(server_timing, expected):
    assert speedtest.get_server_timing(server_timing) == expected

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from cf_speedtest import speedtest


@pytest.mark.parametrize(
    'test_type, bytes_to_xfer, iteration_count, expected_len', [
        ('down', 1000, 3, 3),
        ('up', 1000, 5, 5),
        ('invalid', 1000, 2, 0),
    ],
)
def test_run_tests(test_type, bytes_to_xfer, iteration_count, expected_len):
    with patch('cf_speedtest.speedtest.download_test', return_value=(1000, 0.1)), \
            patch('cf_speedtest.speedtest.upload_test', return_value=(1000, 0.2)):

        results = speedtest.run_tests(
            test_type, bytes_to_xfer, iteration_count,
        )
        assert len(results) == expected_len

        if test_type == 'down':
            assert results[0] == 80000  # (1000 / 0.1) * 8
        elif test_type == 'up':
            assert results[0] == 40000  # (1000 / 0.2) * 8


@patch('cf_speedtest.speedtest.run_tests')
@patch('cf_speedtest.speedtest.latency_test')
@patch('cf_speedtest.speedtest.preamble')
def test_run_standard_test(mock_preamble, mock_latency_test, mock_run_tests):
    mock_latency_test.return_value = 0.05
    mock_run_tests.side_effect = [
        [100000000, 200000000],  # download
        [50000000, 100000000],  # upload
    ]

    results = speedtest.run_standard_test(
        [1000000], measurement_percentile=90, verbose=True,
    )

    assert results['download_speed'] == 200000000
    assert results['upload_speed'] == 100000000
    assert len(results['latency_measurements']) == 20


@pytest.mark.parametrize(
    'args, expected_exit_code', [
        (['--percentile', '90', '--verifyssl', 'False', '--testpatience', '10'], 0),
        (['--proxy', '100.24.216.83:80'], 0),
        (['--output', 'test_output.csv'], 0),
    ],
)
def test_main_unit(args, expected_exit_code, mock_requests_session):
    with patch('cf_speedtest.speedtest.run_standard_test') as mock_run_test:
        mock_run_test.return_value = {
            'download_speed': 100000000,
            'upload_speed': 50000000,
            'download_stdev': 1000000,
            'upload_stdev': 500000,
            'latency_measurements': [10, 20, 30],
            'download_measurements': [90000000, 100000000, 110000000],
            'upload_measurements': [45000000, 50000000, 55000000],
        }

        assert speedtest.main(args) == expected_exit_code


@pytest.mark.parametrize(
    'proxy, expected_dict', [
        (
            '100.24.216.83:80', {
                'http': 'http://100.24.216.83:80', 'https': 'http://100.24.216.83:80',
            },
        ),
        (
            'socks5://127.0.0.1:9150',
            {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'},
        ),
        (
            'http://user:pass@10.10.1.10:3128',
            {
                'http': 'http://user:pass@10.10.1.10:3128',
                'https': 'http://user:pass@10.10.1.10:3128',
            },
        ),
    ],
)
def test_proxy_unit(proxy, expected_dict):
    with patch('cf_speedtest.speedtest.run_standard_test') as mock_run_test:
        mock_run_test.return_value = {
            'download_speed': 100000000,
            'upload_speed': 50000000,
            'download_stdev': 1000000,
            'upload_stdev': 500000,
            'latency_measurements': [10, 20, 30],
            'download_measurements': [90000000, 100000000, 110000000],
            'upload_measurements': [45000000, 50000000, 55000000],
        }

        speedtest.main(['--proxy', proxy])
        assert speedtest.PROXY_DICT == expected_dict


def test_output_file(mock_time):
    output_file = 'test_output.csv'

    with patch('cf_speedtest.speedtest.run_standard_test') as mock_run_test, \
            patch('builtins.open', create=True) as mock_open:
        mock_run_test.return_value = {
            'download_speed': 100000000,
            'upload_speed': 50000000,
            'download_stdev': 1000000,
            'upload_stdev': 500000,
            'latency_measurements': [10, 20, 30],
            'download_measurements': [90000000, 100000000, 110000000],
            'upload_measurements': [45000000, 50000000, 55000000],
        }

        speedtest.main(['--output', output_file])

        mock_open.assert_called_with(output_file, 'w')

    if os.path.exists(output_file):
        os.remove(output_file)

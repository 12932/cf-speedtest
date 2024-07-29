from __future__ import annotations

import csv
import os

import pytest

from cf_speedtest import speedtest


@pytest.mark.integration
def test_country():
    country = speedtest.get_our_country()
    assert isinstance(country, str)
    assert len(country) == 2  # Assuming country codes are always 2 characters


@pytest.mark.integration
def test_preamble():
    preamble_text = speedtest.preamble(False)
    assert isinstance(preamble_text, str)
    assert 'Your IP:' in preamble_text
    assert 'Server loc:' in preamble_text


@pytest.mark.integration
def test_main():
    assert speedtest.main() == 0


@pytest.mark.integration
@pytest.mark.skip(reason='will fail without proxy')
def test_proxy():
    assert speedtest.main(['--proxy', '100.24.216.83:80']) == 0


@pytest.mark.integration
def test_nossl():
    assert speedtest.main(['--verifyssl', 'False']) == 0


@pytest.mark.integration
def test_csv_output():
    temp_file = 'test_output.csv'

    assert speedtest.main(['--output', temp_file]) == 0

    assert os.path.exists(temp_file)
    assert os.path.getsize(temp_file) > 0

    with open(temp_file) as csvfile:
        try:
            csv.reader(csvfile)
            next(csv.reader(csvfile))
        except csv.Error:
            pytest.fail('The output file is not a valid CSV')

    os.remove(temp_file)

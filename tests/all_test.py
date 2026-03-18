from __future__ import annotations

import pytest

from cf_speedtest import speedtest


def test_country():
    speedtest.get_our_country()


def test_preamble():
    speedtest.preamble()


def test_main():
    assert speedtest.main([]) == 0


@pytest.mark.skip(reason='Hardcoded proxy server is no longer available')
def test_proxy():
    assert speedtest.main(['--proxy', '100.24.216.83:80']) == 0


def test_nossl():
    assert speedtest.main(['--verifyssl', 'False']) == 0

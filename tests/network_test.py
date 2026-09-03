"""Tests that talk to the real speed.cloudflare.com. Deselect with ``pytest -m "not network"``."""

from __future__ import annotations

import json

import pytest

from cf_speedtest import speedtest

pytestmark = pytest.mark.network


def test_country():
    assert speedtest.get_our_country() != ''


def test_preamble():
    assert speedtest.preamble().startswith('Your IP:')


def test_server_timing_header_is_understood():
    """Guard against Cloudflare changing the Server-Timing format again (see PRs #6 and #7)."""
    r = speedtest.REQ_SESSION.get(speedtest.DOWNLOAD_ENDPOINT.format(1000), timeout=30)
    r.raise_for_status()
    assert speedtest.get_server_timing(r.headers.get('Server-Timing')) > 0


def test_main():
    assert speedtest.main([]) == 0


def test_main_json(capsys):
    assert speedtest.main(['--json']) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc['download_mbps'] > 0
    assert doc['upload_mbps'] > 0


@pytest.mark.skip(reason='Hardcoded proxy server is no longer available')
def test_proxy():
    assert speedtest.main(['--proxy', '100.24.216.83:80']) == 0


def test_nossl():
    assert speedtest.main(['--verifyssl', 'False']) == 0

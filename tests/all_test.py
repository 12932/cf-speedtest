from __future__ import annotations

import pytest

from cf_speedtest import speedtest


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_country():
    speedtest.get_our_country()


def test_preamble():
    speedtest.preamble()


@pytest.mark.parametrize(
    ('payload', 'expected_server'),
    [
        (
            {'clientIp': '203.0.113.10', 'country': 'US', 'colo': None},
            'Server loc:\tUnknown (Unknown) - (Unknown)',
        ),
        (
            {'clientIp': '203.0.113.10', 'country': 'US'},
            'Server loc:\tUnknown (Unknown) - (Unknown)',
        ),
    ],
)
def test_preamble_handles_missing_colo_metadata(monkeypatch, payload, expected_server):
    def fake_get(*args, **kwargs):
        return FakeResponse(payload)

    monkeypatch.setattr(speedtest.REQ_SESSION, 'get', fake_get)

    assert speedtest.preamble() == f'Your IP:\t203.0.113.10 (US)\n{expected_server}'


def test_main():
    assert speedtest.main([]) == 0


@pytest.mark.skip(reason='Hardcoded proxy server is no longer available')
def test_proxy():
    assert speedtest.main(['--proxy', '100.24.216.83:80']) == 0


def test_nossl():
    assert speedtest.main(['--verifyssl', 'False']) == 0

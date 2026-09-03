from __future__ import annotations

import json

import pytest

from cf_speedtest import speedtest


class FakeResponse:
    def __init__(self, payload=None, headers=None, content=b''):
        self.payload = payload
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


# --- percentile -----------------------------------------------------------------------------


def test_percentile_empty():
    assert speedtest.percentile([], 90) == 0.0


@pytest.mark.parametrize(
    ('pct', 'expected'),
    [(0, 1), (1, 1), (50, 5), (90, 9), (100, 10)],
)
def test_percentile_nearest_rank(pct, expected):
    data = [10, 3, 7, 1, 9, 2, 8, 4, 6, 5]
    assert speedtest.percentile(data, pct) == expected


# --- Server-Timing ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('header', 'expected_seconds'),
    [
        (None, 0.0),
        ('', 0.0),
        # Legacy single metric
        ('cfRequestDuration;dur=12.5', 0.0125),
        ('cfReqDur;dur=7', 0.007),
        # Current format: edge + worker, plus an unrelated L4 metric (as joined by requests)
        (
            'cfSpeedEdge;dur=5, cfSpeedWorker;dur=27, cfL4;desc="?proto=TCP&rtt=5017&min_rtt=4954"',
            0.032,
        ),
        ('cfSpeedEdge;dur=3, cfSpeedWorker;dur=19', 0.022),
        # cfRequestDuration wins when both are present
        ('cfSpeedEdge;dur=5, cfRequestDuration;dur=40, cfSpeedWorker;dur=27', 0.040),
        # Unknown metrics never inflate the measurement
        ('cfL4;desc="?proto=TCP&rtt=5017"', 0.0),
        ('garbage', 0.0),
        ('cfSpeedEdge;dur=abc', 0.0),
    ],
)
def test_get_server_timing(header, expected_seconds):
    assert speedtest.get_server_timing(header) == pytest.approx(expected_seconds)


# --- proxies ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('proxy', 'expected'),
    [
        (None, None),
        ('', None),
        ('socks5://127.0.0.1:1080', {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}),
        ('http://127.0.0.1:8181', {'http': 'http://127.0.0.1:8181', 'https': 'http://127.0.0.1:8181'}),
        ('https://user:pw@proxy:443', {'http': 'https://user:pw@proxy:443', 'https': 'https://user:pw@proxy:443'}),
        ('127.0.0.1:8080', {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}),
    ],
)
def test_build_proxy_dict(proxy, expected):
    assert speedtest.build_proxy_dict(proxy) == expected


# --- metadata / preamble ---------------------------------------------------------------------


def test_get_meta_full(monkeypatch):
    payload = {
        'clientIp': '203.0.113.10',
        'country': 'US',
        'colo': {'iata': 'PDX', 'cca2': 'US', 'city': 'Portland'},
    }
    monkeypatch.setattr(speedtest.REQ_SESSION, 'get', lambda *a, **k: FakeResponse(payload))

    assert speedtest.get_meta() == {
        'client_ip': '203.0.113.10',
        'client_country': 'US',
        'server_city': 'Portland',
        'server_iata': 'PDX',
        'server_country': 'US',
    }


def test_get_meta_falls_back_to_locations_table(monkeypatch):
    payload = {'clientIp': '203.0.113.10', 'country': 'AU', 'colo': {'iata': 'TIA'}}
    monkeypatch.setattr(speedtest.REQ_SESSION, 'get', lambda *a, **k: FakeResponse(payload))

    meta = speedtest.get_meta()
    assert meta['server_country'] == 'AL'
    assert meta['server_city'] == 'TIA'  # no city in payload -> fall back to IATA


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
    """Regression test for issue #13 (AttributeError: 'NoneType' object has no attribute 'upper')."""
    monkeypatch.setattr(speedtest.REQ_SESSION, 'get', lambda *a, **k: FakeResponse(payload))

    assert speedtest.preamble() == f'Your IP:\t203.0.113.10 (US)\n{expected_server}'


def test_get_our_country_parses_trace(monkeypatch):
    class TraceResponse(FakeResponse):
        text = 'fl=123\nh=speed.cloudflare.com\nip=203.0.113.10\nloc=NZ\nnoequals\n'

    monkeypatch.setattr(speedtest.REQ_SESSION, 'get', lambda *a, **k: TraceResponse())
    assert speedtest.get_our_country() == 'NZ'


# --- end-to-end with the network stubbed out -------------------------------------------------


@pytest.fixture
def fake_network(monkeypatch):
    """Stub every function that talks to Cloudflare with deterministic, instant answers."""
    monkeypatch.setattr(speedtest, 'latency_test', lambda: 0.010)
    # 1 MB/s down, 0.5 MB/s up
    monkeypatch.setattr(speedtest, 'download_test', lambda n: (n, n / 1_000_000))
    monkeypatch.setattr(speedtest, 'upload_test', lambda n: (n, n / 500_000))
    monkeypatch.setattr(
        speedtest,
        'get_meta',
        lambda: {
            'client_ip': '203.0.113.10',
            'client_country': 'US',
            'server_city': 'Portland',
            'server_iata': 'PDX',
            'server_country': 'US',
        },
    )
    return monkeypatch


def test_run_standard_test_skips_slow_sizes(fake_network):
    calls: list[int] = []

    def counting_download(n):
        calls.append(n)
        return n, n / 1_000_000

    fake_network.setattr(speedtest, 'download_test', counting_download)
    results = speedtest.run_standard_test([100_000, 1_000_000, 250_000_000], test_patience=1)

    # 250 MB at 8 Mbit/s would take far longer than test_patience -> skipped
    assert 250_000_000 not in calls
    assert results['download_speed'] == pytest.approx(8_000_000)
    assert results['upload_speed'] == pytest.approx(4_000_000)
    assert results['latency'] == pytest.approx(10.0)
    assert results['jitter'] == 0.0


def test_run_standard_test_disable_skipping(fake_network):
    calls: list[int] = []

    def counting_download(n):
        calls.append(n)
        return n, n / 1_000_000

    fake_network.setattr(speedtest, 'download_test', counting_download)
    speedtest.run_standard_test([100_000, 1_000_000, 250_000_000], test_patience=1, skip_slow_tests=False)

    assert 250_000_000 in calls


def test_main_text_output(fake_network, capsys):
    assert speedtest.main([]) == 0
    out = capsys.readouterr().out
    assert 'Your IP:\t203.0.113.10 (US)' in out
    assert 'Latency:' in out
    assert '90th percentile results:' in out
    assert 'Down: 8.00 Mbit/sec' in out
    assert 'Up: 4.00 Mbit/sec' in out


def test_main_json_output(fake_network, capsys):
    assert speedtest.main(['--json', '--percentile', '50', '--disableskipping']) == 0
    out = capsys.readouterr().out
    doc = json.loads(out)

    assert doc['client_ip'] == '203.0.113.10'
    assert doc['server'] == {'city': 'Portland', 'iata': 'PDX', 'country': 'US'}
    assert doc['percentile'] == 50
    assert doc['latency_ms'] == pytest.approx(10.0)
    assert doc['download_mbps'] == pytest.approx(8.0)
    assert doc['upload_mbps'] == pytest.approx(4.0)
    assert len(doc['latency_measurements_ms']) == 20
    assert doc['download_measurements_bps']
    assert doc['upload_measurements_bps']
    # JSON mode must print nothing else
    assert out.strip().startswith('{') and out.strip().endswith('}')


def test_main_writes_csv(fake_network, tmp_path):
    out_file = tmp_path / 'data.csv'
    out_file.write_text('stale\n')

    assert speedtest.main(['--output', str(out_file)]) == 0

    # main() truncates the file; the stubbed transfer functions never write rows
    assert out_file.read_text() == ''
    assert str(out_file) == speedtest.OUTPUT_FILE


def test_main_reports_network_errors(monkeypatch, capsys):
    def boom():
        raise RuntimeError('Failed to get server metadata: connection refused')

    monkeypatch.setattr(speedtest, 'get_meta', boom)

    assert speedtest.main([]) == 1
    assert 'error: Failed to get server metadata' in capsys.readouterr().err

# cf-speedtest

A simple internet speed test CLI tool using [speed.cloudflare.com](https://speed.cloudflare.com)

[![PyPI version](https://img.shields.io/pypi/v/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)
[![CI](https://github.com/12932/cf-speedtest/actions/workflows/main.yml/badge.svg)](https://github.com/12932/cf-speedtest/actions/workflows/main.yml)
[![PyPI downloads](https://img.shields.io/pypi/dm/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)

## Installation

```bash
# Recommended
uv tool install cf-speedtest

# Or run without installing
uvx cf-speedtest

# Or with pip
pip install -U cf-speedtest
```

## Usage

```bash
# Run a speedtest
cf-speedtest

# Machine-readable output (single JSON document once the test finishes)
cf-speedtest --json

# Run every transfer size, even ones that would exceed --testpatience at your speed
cf-speedtest --disableskipping

# Without SSL verification
cf-speedtest --verifyssl=false

# Custom percentile (default 90)
cf-speedtest --percentile 80

# Output raw measurements to CSV
cf-speedtest --output speed_data.csv

# With proxy
cf-speedtest --proxy socks5://127.0.0.1:1080
cf-speedtest --proxy http://127.0.0.1:8181
```

Example `--json` output:

```json
{
  "client_ip": "203.0.113.10",
  "client_country": "US",
  "server": {"city": "Portland", "iata": "PDX", "country": "US"},
  "percentile": 90,
  "latency_ms": 5.12,
  "jitter_ms": 0.41,
  "download_mbps": 812.3,
  "upload_mbps": 95.7,
  "download_stdev_mbps": 40.2,
  "upload_stdev_mbps": 3.1,
  "latency_measurements_ms": [...],
  "download_measurements_bps": [...],
  "upload_measurements_bps": [...]
}
```

The CSV written by `--output` has one row per request: `unix_time,direction,bytes,total_seconds,server_seconds`.

## Requirements

- Python 3.10+

## Development

Python 3.14 is the default interpreter (`.python-version`); the package itself supports 3.10+.

```bash
uv sync                          # creates .venv with the dev dependency group
uv run pytest -m "not network"   # fast unit tests
uv run pytest                    # also runs tests that hit speed.cloudflare.com
uv run ruff check . && uv run ruff format .
uv run pre-commit install        # optional: run the same checks on commit
```

## Releasing

1. Bump `version` in `pyproject.toml` and update `CHANGELOG.md`, then `uv lock`.
2. Tag and push: `git tag v0.3.0 && git push --tags`.
3. Create a GitHub release for that tag. The `Publish to PyPI` workflow builds and uploads via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) (no API token needed).

## Disclaimers

- Single-threaded
- Works over HTTP(S), which has some overhead
- Latency measured via HTTP requests
- Cloudflare has a global network, but you may connect to a distant PoP due to ISP peering

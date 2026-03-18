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

# Or with pip
pip install -U cf-speedtest
```

## Usage

```bash
# Run a speedtest
cf-speedtest

# Without SSL verification
cf-speedtest --verifyssl=false

# Custom percentile (default 90)
cf-speedtest --percentile 80

# Output to CSV
cf-speedtest --output speed_data.csv

# With proxy
cf-speedtest --proxy socks5://127.0.0.1:1080
cf-speedtest --proxy http://127.0.0.1:8181
```

## Requirements

- Python 3.10+

## Disclaimers

- Single-threaded
- Works over HTTP(S), which has some overhead
- Latency measured via HTTP requests
- Cloudflare has a global network, but you may connect to a distant PoP due to ISP peering

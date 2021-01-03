# cf_speedtest

## A simple internet speed test tool/library, which uses https://speed.cloudflare.com (provided by Cloudflare)

[![PyPI version](https://img.shields.io/pypi/v/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)
[![PyPI status](https://img.shields.io/pypi/status/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)
[![PyPI downloads](https://img.shields.io/pypi/dm/cf-speedtest.svg)](https://pypi.python.org/pypi/cf-speedtest)

## Basic CLI usage:

- ### Running a normal speedtest:
	- `cf_speedtest`

- ### Without verifying SSL:
	- `cf_speedtest --verifyssl=false`

- ### Specify a [percentile](https://en.wikipedia.org/wiki/Percentile) of measurements to be considered your speed (default 90):
	- `cf_speedtest --percentile 80`

- ### Output measurements to a CSV file:
	- `cf_speedtest --output speed_data.csv`

- ### Specify a SOCKS/HTTP proxy to use (with or without authentication):
	- `cf_speedtest --proxy socks5://127.0.0.1:1080`
	- `cf_speedtest --proxy socks5://admin:admin@127.0.0.1:1080`
	- `cf_speedtest --proxy http://127.0.0.1:8181`
	- `cf_speedtest --proxy http://admin:admin@127.0.0.1:8181`
	- `cf_speedtest --proxy 127.0.0.1:8181`

## Programmatic usage:
	- TODO

#### TODO:
	- Programmatic usage
	- Multi-threaded speedtest
	- Continuous mode

#### Disclaimers:
	- This library is purely single-threaded
	- This library works entirely over HTTP(S), which has some overhead
	- Latency is measured with HTTP requests
	- Cloudflare has a global network, but you may be connected to a distant PoP due to ISP peering and other factors
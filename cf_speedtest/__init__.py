from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('cf-speedtest')
except PackageNotFoundError:  # pragma: no cover - running from a source checkout without install
    __version__ = '0.0.0+unknown'

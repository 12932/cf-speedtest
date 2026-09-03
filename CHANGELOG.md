# Changelog

## 0.3.0 - 2026-09-03

### Fixed
- Cloudflare now sends `Server-Timing: cfSpeedEdge;dur=N, cfSpeedWorker;dur=N`. The old parser silently
  returned `0` for that format, so server processing time was never subtracted from measurements. The parser
  now mirrors Cloudflare's own client (prefers `cfRequestDuration`, otherwise sums `cfSpeed*`).
  Follows up on #6 by @akarasik and #7 by @Cyberes.
- `--percentile 0` returned the maximum measurement instead of the minimum.
- Regression test for the `preamble()` crash when Cloudflare omits `colo` metadata (#13, test from #14 by @KairosOps).
- Network failures print a one-line error and exit 1 instead of a traceback.

### Added
- `--json` / `-j`: print results as a single JSON document. Based on #10 by @akarasik.
- `--disableskipping` / `-s`: run every transfer size regardless of measured speed. Based on #10 by @akarasik.
- `--version` / `-V`.
- `cf_speedtest.__version__`.

### Changed
- Tooling moved fully onto `uv` + `ruff`: `uv.lock` is committed, `uv sync` installs the dev group, CI lints,
  runs unit tests across Python 3.10-3.14, runs the network tests once, and smoke-tests the built wheel.
- Releases publish to PyPI through GitHub trusted publishing (`.github/workflows/publish.yml`).
- Test suite split into fast unit tests and `network`-marked tests.

## 0.2.0

- Replaced `setup.py` / `requirements.txt` / `tox` with `pyproject.toml` and `uv` packaging.
- Fixed crash when `/meta` has no `colo` (#13).

from __future__ import annotations

import argparse

import pytest

from cf_speedtest import __version__, options


def make_parser() -> argparse.ArgumentParser:
    return options.add_run_options(argparse.ArgumentParser(prog='cf-speedtest'))


@pytest.mark.parametrize('value', ['yes', 'true', 'T', 'y', '1', 'TRUE'])
def test_str_to_bool_truthy(value):
    assert options.str_to_bool(value) is True


@pytest.mark.parametrize('value', ['no', 'false', 'F', 'n', '0', 'FALSE'])
def test_str_to_bool_falsy(value):
    assert options.str_to_bool(value) is False


def test_str_to_bool_passthrough_and_invalid():
    assert options.str_to_bool(True) is True
    with pytest.raises(argparse.ArgumentTypeError):
        options.str_to_bool('maybe')


@pytest.mark.parametrize('value', ['0', '50', '100'])
def test_valid_percentile_accepts_range(value):
    assert options.valid_percentile(value) == int(value)


@pytest.mark.parametrize('value', ['-1', '101', 'ninety'])
def test_valid_percentile_rejects(value):
    with pytest.raises(argparse.ArgumentTypeError):
        options.valid_percentile(value)


def test_defaults():
    args = make_parser().parse_args([])
    assert args.output is None
    assert args.percentile == 90
    assert args.verifyssl is True
    assert args.proxy is None
    assert args.testpatience == 20
    assert args.disableskipping is False
    assert args.json is False


def test_flags_parse():
    args = make_parser().parse_args(
        ['-o', 'out.csv', '-p', '50', '-k', 'false', '-x', 'socks5://127.0.0.1:1080', '-t', '5', '-s', '-j'],
    )
    assert args.output == 'out.csv'
    assert args.percentile == 50
    assert args.verifyssl is False
    assert args.proxy == 'socks5://127.0.0.1:1080'
    assert args.testpatience == 5
    assert args.disableskipping is True
    assert args.json is True


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        make_parser().parse_args(['--version'])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f'cf-speedtest {__version__}'

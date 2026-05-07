"""Tests for schemasnap.cmd_baseline CLI sub-commands."""

from __future__ import annotations

import argparse
from unittest.mock import patch, MagicMock

import pytest

from schemasnap.cmd_baseline import (
    add_baseline_subparsers,
    cmd_baseline_set,
    cmd_baseline_show,
    cmd_baseline_check,
)
from schemasnap.baseline import BaselineEntry


def _make_args(**kwargs):
    defaults = {"env": "prod", "snapshot_dir": "snapshots", "file": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# baseline-set
# ---------------------------------------------------------------------------

def test_cmd_baseline_set_uses_latest_when_no_file():
    args = _make_args(file=None)
    with patch("schemasnap.cmd_baseline.latest_snapshot", return_value="snap_prod_abc.json") as mock_latest, \
         patch("schemasnap.cmd_baseline.set_baseline_from_snapshot") as mock_set:
        mock_set.return_value = BaselineEntry(env="prod", snapshot_file="snap_prod_abc.json", hash="abc", set_at="2024-01-01T00:00:00Z")
        rc = cmd_baseline_set(args)
    assert rc == 0
    mock_latest.assert_called_once_with("snapshots", "prod")
    mock_set.assert_called_once()


def test_cmd_baseline_set_uses_explicit_file():
    args = _make_args(file="my_snap.json")
    with patch("schemasnap.cmd_baseline.set_baseline_from_snapshot") as mock_set:
        mock_set.return_value = BaselineEntry(env="prod", snapshot_file="my_snap.json", hash="xyz", set_at="2024-01-01T00:00:00Z")
        rc = cmd_baseline_set(args)
    assert rc == 0
    mock_set.assert_called_once_with("snapshots", "prod", "my_snap.json")


def test_cmd_baseline_set_returns_1_when_no_snapshot():
    args = _make_args(file=None)
    with patch("schemasnap.cmd_baseline.latest_snapshot", return_value=None):
        rc = cmd_baseline_set(args)
    assert rc == 1


# ---------------------------------------------------------------------------
# baseline-show
# ---------------------------------------------------------------------------

def test_cmd_baseline_show_prints_entry(capsys):
    args = _make_args()
    entry = BaselineEntry(env="prod", snapshot_file="snap.json", hash="deadbeef", set_at="2024-06-01T12:00:00Z")
    with patch("schemasnap.cmd_baseline.get_baseline", return_value=entry):
        rc = cmd_baseline_show(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "deadbeef" in out
    assert "snap.json" in out


def test_cmd_baseline_show_returns_1_when_not_set(capsys):
    args = _make_args()
    with patch("schemasnap.cmd_baseline.get_baseline", return_value=None):
        rc = cmd_baseline_show(args)
    assert rc == 1


# ---------------------------------------------------------------------------
# baseline-check
# ---------------------------------------------------------------------------

def test_cmd_baseline_check_ok_when_matching(capsys):
    args = _make_args(file="current.json")
    with patch("schemasnap.cmd_baseline.compare_to_baseline", return_value=True):
        rc = cmd_baseline_check(args)
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cmd_baseline_check_drift_when_not_matching(capsys):
    args = _make_args(file="current.json")
    with patch("schemasnap.cmd_baseline.compare_to_baseline", return_value=False):
        rc = cmd_baseline_check(args)
    assert rc == 1
    assert "DRIFT" in capsys.readouterr().out


def test_cmd_baseline_check_returns_2_on_missing_baseline(capsys):
    args = _make_args(file="current.json")
    with patch("schemasnap.cmd_baseline.compare_to_baseline", side_effect=ValueError("No baseline set for environment 'prod'")):
        rc = cmd_baseline_check(args)
    assert rc == 2


def test_cmd_baseline_check_uses_latest_when_no_file():
    args = _make_args(file=None)
    with patch("schemasnap.cmd_baseline.latest_snapshot", return_value="latest.json") as mock_latest, \
         patch("schemasnap.cmd_baseline.compare_to_baseline", return_value=True):
        rc = cmd_baseline_check(args)
    assert rc == 0
    mock_latest.assert_called_once_with("snapshots", "prod")


# ---------------------------------------------------------------------------
# Parser registration smoke test
# ---------------------------------------------------------------------------

def test_add_baseline_subparsers_registers_commands():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_baseline_subparsers(sub)
    # Should parse without error
    args = parser.parse_args(["baseline-show", "--env", "staging"])
    assert args.env == "staging"

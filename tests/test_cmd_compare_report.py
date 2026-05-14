"""Tests for schemasnap.cmd_compare_report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_compare_report import add_compare_report_subparsers, cmd_compare_report
from schemasnap.snapshot import capture_snapshot


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        snapshot_a="a.json",
        snapshot_b="b.json",
        fmt="text",
        output=None,
        env_a="env_a",
        env_b="env_b",
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_snap(directory: Path, env: str, schema: dict) -> Path:
    return Path(capture_snapshot(schema, env=env, snapshot_dir=str(directory)))


# ---------------------------------------------------------------------------
# parser registration
# ---------------------------------------------------------------------------

def test_add_compare_report_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_compare_report_subparsers(sub)
    ns = parser.parse_args(["compare-report", "a.json", "b.json"])
    assert ns.snapshot_a == "a.json"
    assert ns.snapshot_b == "b.json"


def test_add_compare_report_subparsers_default_fmt():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_compare_report_subparsers(sub)
    ns = parser.parse_args(["compare-report", "a.json", "b.json"])
    assert ns.fmt == "text"


# ---------------------------------------------------------------------------
# missing files
# ---------------------------------------------------------------------------

def test_cmd_compare_report_missing_a_returns_1(tmp_path):
    snap_b = _write_snap(tmp_path, "prod", {"users": {"id": "int"}})
    args = _make_args(snapshot_a=str(tmp_path / "nope.json"), snapshot_b=str(snap_b))
    assert cmd_compare_report(args) == 1


def test_cmd_compare_report_missing_b_returns_1(tmp_path):
    snap_a = _write_snap(tmp_path, "prod", {"users": {"id": "int"}})
    args = _make_args(snapshot_a=str(snap_a), snapshot_b=str(tmp_path / "nope.json"))
    assert cmd_compare_report(args) == 1


# ---------------------------------------------------------------------------
# no changes
# ---------------------------------------------------------------------------

def test_cmd_compare_report_no_changes_returns_0(tmp_path):
    schema = {"users": {"id": "int", "name": "text"}}
    snap_a = _write_snap(tmp_path, "staging", schema)
    snap_b = _write_snap(tmp_path, "prod", schema)
    args = _make_args(snapshot_a=str(snap_a), snapshot_b=str(snap_b))
    assert cmd_compare_report(args) == 0


# ---------------------------------------------------------------------------
# drift detected
# ---------------------------------------------------------------------------

def test_cmd_compare_report_drift_returns_1(tmp_path):
    snap_a = _write_snap(tmp_path, "staging", {"users": {"id": "int"}})
    snap_b = _write_snap(tmp_path, "prod", {"users": {"id": "int", "email": "text"}})
    args = _make_args(snapshot_a=str(snap_a), snapshot_b=str(snap_b))
    assert cmd_compare_report(args) == 1


# ---------------------------------------------------------------------------
# output formats
# ---------------------------------------------------------------------------

def test_cmd_compare_report_json_format_is_valid(tmp_path, capsys):
    schema = {"orders": {"id": "int"}}
    snap_a = _write_snap(tmp_path, "staging", schema)
    snap_b = _write_snap(tmp_path, "prod", schema)
    args = _make_args(snapshot_a=str(snap_a), snapshot_b=str(snap_b), fmt="json")
    cmd_compare_report(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "has_changes" in data


def test_cmd_compare_report_writes_file(tmp_path):
    schema = {"items": {"id": "int"}}
    snap_a = _write_snap(tmp_path, "staging", schema)
    snap_b = _write_snap(tmp_path, "prod", schema)
    out_file = tmp_path / "report.txt"
    args = _make_args(
        snapshot_a=str(snap_a),
        snapshot_b=str(snap_b),
        output=str(out_file),
    )
    cmd_compare_report(args)
    assert out_file.exists()
    assert out_file.stat().st_size > 0

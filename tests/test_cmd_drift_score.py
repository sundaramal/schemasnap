"""Tests for schemasnap.cmd_drift_score."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_drift_score import add_drift_score_subparsers, cmd_drift_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = {"fmt": "text", "threshold": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_snapshot(path: Path, schema: dict) -> None:
    import json as _json
    path.write_text(_json.dumps({"environment": "test", "schema": schema}))


@pytest.fixture()
def snap_dir(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# add_drift_score_subparsers
# ---------------------------------------------------------------------------

def test_add_drift_score_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_drift_score_subparsers(sub)
    args = parser.parse_args(["drift-score", "a.json", "b.json"])
    assert args.primary == "a.json"
    assert args.secondary == "b.json"


def test_add_drift_score_subparsers_default_fmt():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_drift_score_subparsers(sub)
    args = parser.parse_args(["drift-score", "a.json", "b.json"])
    assert args.fmt == "text"


# ---------------------------------------------------------------------------
# cmd_drift_score
# ---------------------------------------------------------------------------

def test_cmd_drift_score_missing_primary_returns_1(snap_dir):
    args = _make_args(
        primary=str(snap_dir / "missing.json"),
        secondary=str(snap_dir / "also_missing.json"),
    )
    assert cmd_drift_score(args) == 1


def test_cmd_drift_score_missing_secondary_returns_1(snap_dir):
    primary = snap_dir / "primary.json"
    _write_snapshot(primary, {"users": {"id": "int"}})
    args = _make_args(
        primary=str(primary),
        secondary=str(snap_dir / "missing.json"),
    )
    assert cmd_drift_score(args) == 1


def test_cmd_drift_score_identical_returns_zero(snap_dir):
    schema = {"users": {"id": "int", "name": "text"}}
    p = snap_dir / "p.json"
    s = snap_dir / "s.json"
    _write_snapshot(p, schema)
    _write_snapshot(s, schema)
    args = _make_args(primary=str(p), secondary=str(s))
    assert cmd_drift_score(args) == 0


def test_cmd_drift_score_json_output_is_valid(snap_dir, capsys):
    schema = {"orders": {"id": "int"}}
    p = snap_dir / "p.json"
    s = snap_dir / "s.json"
    _write_snapshot(p, schema)
    _write_snapshot(s, schema)
    args = _make_args(primary=str(p), secondary=str(s), fmt="json")
    rc = cmd_drift_score(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "overall" in data
    assert "table_score" in data


def test_cmd_drift_score_threshold_exceeded_returns_1(snap_dir):
    p = snap_dir / "p.json"
    s = snap_dir / "s.json"
    _write_snapshot(p, {"a": {"col1": "int"}})
    _write_snapshot(s, {"z": {"colX": "text", "colY": "bool"}})
    # completely different schemas → high drift; threshold=0.0 should trigger
    args = _make_args(primary=str(p), secondary=str(s), threshold=0.0)
    assert cmd_drift_score(args) == 1


def test_cmd_drift_score_threshold_not_exceeded_returns_zero(snap_dir):
    schema = {"users": {"id": "int"}}
    p = snap_dir / "p.json"
    s = snap_dir / "s.json"
    _write_snapshot(p, schema)
    _write_snapshot(s, schema)
    args = _make_args(primary=str(p), secondary=str(s), threshold=1.0)
    assert cmd_drift_score(args) == 0

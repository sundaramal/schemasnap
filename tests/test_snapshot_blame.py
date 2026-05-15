"""Tests for snapshot_blame and cmd_snapshot_blame."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.snapshot_blame import compute_blame, BlameReport
from schemasnap.cmd_snapshot_blame import add_snapshot_blame_subparsers, cmd_snapshot_blame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str, schema: dict, idx: int = 0) -> Path:
    import json as _json
    from schemasnap.snapshot import compute_schema_hash

    h = compute_schema_hash(schema)
    filename = f"{env}_{idx:04d}_{h}.json"
    data = {"environment": env, "schema_hash": h, "schema": schema}
    p = directory / filename
    p.write_text(_json.dumps(data))
    return p


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests – compute_blame
# ---------------------------------------------------------------------------

def test_blame_single_snapshot_all_tables_attributed(snap_dir):
    schema = {"users": ["id", "email"], "orders": ["id", "amount"]}
    _write_snapshot(snap_dir, "prod", schema, idx=0)
    report = compute_blame(str(snap_dir))
    tables = {e.table for e in report.entries if e.column is None}
    assert "users" in tables
    assert "orders" in tables


def test_blame_new_table_in_second_snapshot(snap_dir):
    schema_v1 = {"users": ["id", "email"]}
    schema_v2 = {"users": ["id", "email"], "orders": ["id", "amount"]}
    _write_snapshot(snap_dir, "prod", schema_v1, idx=0)
    _write_snapshot(snap_dir, "prod", schema_v2, idx=1)
    report = compute_blame(str(snap_dir))
    orders_entry = next(
        (e for e in report.entries if e.table == "orders" and e.column is None), None
    )
    assert orders_entry is not None
    assert "_0001_" in orders_entry.first_seen_file


def test_blame_column_first_appearance_tracked(snap_dir):
    schema_v1 = {"users": ["id"]}
    schema_v2 = {"users": ["id", "email"]}
    _write_snapshot(snap_dir, "prod", schema_v1, idx=0)
    _write_snapshot(snap_dir, "prod", schema_v2, idx=1)
    report = compute_blame(str(snap_dir))
    email_entry = next(
        (e for e in report.entries if e.table == "users" and e.column == "email"), None
    )
    assert email_entry is not None
    assert "_0001_" in email_entry.first_seen_file


def test_blame_env_filter(snap_dir):
    _write_snapshot(snap_dir, "prod", {"t1": ["a"]}, idx=0)
    _write_snapshot(snap_dir, "staging", {"t2": ["b"]}, idx=0)
    report = compute_blame(str(snap_dir), env="prod")
    tables = {e.table for e in report.entries if e.column is None}
    assert "t1" in tables
    assert "t2" not in tables


def test_blame_report_for_table_helper(snap_dir):
    schema = {"users": ["id", "email"]}
    _write_snapshot(snap_dir, "prod", schema, idx=0)
    report = compute_blame(str(snap_dir))
    user_entries = report.for_table("users")
    assert len(user_entries) >= 1


# ---------------------------------------------------------------------------
# CLI tests – cmd_snapshot_blame
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = {"env": None, "table": None, "fmt": "text", "func": cmd_snapshot_blame}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_blame_missing_dir_returns_1(tmp_path):
    args = _make_args(snapshot_dir=str(tmp_path / "no_such_dir"))
    assert cmd_snapshot_blame(args) == 1


def test_cmd_blame_text_output_returns_zero(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", {"users": ["id", "email"]}, idx=0)
    args = _make_args(snapshot_dir=str(snap_dir))
    rc = cmd_snapshot_blame(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "users" in out


def test_cmd_blame_json_output_is_valid(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", {"orders": ["id", "total"]}, idx=0)
    args = _make_args(snapshot_dir=str(snap_dir), fmt="json")
    rc = cmd_snapshot_blame(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert any(e["table"] == "orders" for e in payload)


def test_add_snapshot_blame_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_blame_subparsers(sub)
    args = parser.parse_args(["snapshot-blame", "/some/dir"])
    assert args.func is cmd_snapshot_blame

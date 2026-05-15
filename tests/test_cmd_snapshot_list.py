"""Tests for schemasnap.cmd_snapshot_list."""
from __future__ import annotations

import argparse
import json
import os

import pytest

from schemasnap.cmd_snapshot_list import add_snapshot_list_subparsers, cmd_snapshot_list
from schemasnap.snapshot import capture_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"dir": "snapshots", "env": None, "fmt": "text", "show_tables": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_snapshot(snap_dir: str, env: str, schema: dict) -> str:
    return capture_snapshot(schema, environment=env, snapshot_dir=snap_dir)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def snap_dir(tmp_path):
    d = tmp_path / "snaps"
    d.mkdir()
    return str(d)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_snapshot_list_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_list_subparsers(sub)
    args = parser.parse_args(["snapshot-list", "--dir", "."])
    assert args.func is cmd_snapshot_list


def test_cmd_snapshot_list_missing_dir_returns_1(tmp_path):
    args = _make_args(dir=str(tmp_path / "nonexistent"))
    assert cmd_snapshot_list(args) == 1


def test_cmd_snapshot_list_empty_dir_returns_0(snap_dir, capsys):
    args = _make_args(dir=snap_dir)
    rc = cmd_snapshot_list(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No snapshots found" in captured.out


def test_cmd_snapshot_list_empty_dir_json_returns_empty_list(snap_dir, capsys):
    args = _make_args(dir=snap_dir, fmt="json")
    rc = cmd_snapshot_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data == []


def test_cmd_snapshot_list_shows_snapshots(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", {"users": {"id": "int"}})
    args = _make_args(dir=snap_dir)
    rc = cmd_snapshot_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "prod" in out


def test_cmd_snapshot_list_json_contains_expected_keys(snap_dir, capsys):
    _write_snapshot(snap_dir, "staging", {"orders": {"id": "int", "total": "float"}})
    args = _make_args(dir=snap_dir, fmt="json")
    cmd_snapshot_list(args)
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    row = data[0]
    assert row["environment"] == "staging"
    assert row["table_count"] == 1
    assert "schema_hash" in row


def test_cmd_snapshot_list_env_filter(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", {"a": {}})
    _write_snapshot(snap_dir, "staging", {"b": {}})
    args = _make_args(dir=snap_dir, env="prod", fmt="json")
    cmd_snapshot_list(args)
    data = json.loads(capsys.readouterr().out)
    assert all(r["environment"] == "prod" for r in data)


def test_cmd_snapshot_list_show_tables_includes_table_names(snap_dir, capsys):
    _write_snapshot(snap_dir, "dev", {"products": {"id": "int"}, "reviews": {"id": "int"}})
    args = _make_args(dir=snap_dir, show_tables=True, fmt="json")
    cmd_snapshot_list(args)
    data = json.loads(capsys.readouterr().out)
    assert "tables" in data[0]
    assert set(data[0]["tables"]) == {"products", "reviews"}


def test_cmd_snapshot_list_text_show_tables_prints_names(snap_dir, capsys):
    _write_snapshot(snap_dir, "dev", {"accounts": {"id": "int"}})
    args = _make_args(dir=snap_dir, show_tables=True, fmt="text")
    cmd_snapshot_list(args)
    out = capsys.readouterr().out
    assert "accounts" in out

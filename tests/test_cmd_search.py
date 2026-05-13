"""Tests for cmd_search subcommand."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_search import add_search_subparsers, cmd_search


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = dict(
        snapshot_dir=".",
        table_pattern=None,
        column_pattern=None,
        env_filter=None,
        fmt="text",
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_snapshot(directory: Path, env: str, schema: dict) -> Path:
    import hashlib, json, datetime
    content = {
        "environment": env,
        "captured_at": datetime.datetime.utcnow().isoformat(),
        "schema": schema,
    }
    raw = json.dumps(content, sort_keys=True)
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    path = directory / f"{env}_{h}.json"
    path.write_text(raw)
    return path


@pytest.fixture()
def snap_dir(tmp_path):
    schema = {
        "users": {"id": "int", "email": "varchar"},
        "orders": {"id": "int", "total": "numeric"},
    }
    _write_snapshot(tmp_path, "prod", schema)
    _write_snapshot(tmp_path, "staging", {"products": {"sku": "varchar", "price": "numeric"}})
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_search_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_search_subparsers(sub)
    args = parser.parse_args(["search", "."])
    assert hasattr(args, "func")


def test_cmd_search_missing_dir_returns_1(tmp_path):
    args = _make_args(snapshot_dir=str(tmp_path / "nonexistent"))
    assert cmd_search(args) == 1


def test_cmd_search_no_pattern_returns_zero(snap_dir):
    args = _make_args(snapshot_dir=str(snap_dir))
    assert cmd_search(args) == 0


def test_cmd_search_table_pattern_text(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), table_pattern="users")
    rc = cmd_search(args)
    assert rc == 0
    captured = capsys.readouterr().out
    assert "users" in captured
    assert "orders" not in captured


def test_cmd_search_column_pattern_json(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), column_pattern="email", fmt="json")
    rc = cmd_search(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert all(r["column"] == "email" for r in data)


def test_cmd_search_no_matches_message(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), table_pattern="nonexistent_xyz")
    rc = cmd_search(args)
    assert rc == 0
    assert "No matches found" in capsys.readouterr().out


def test_cmd_search_env_filter(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), env_filter="staging", fmt="json")
    rc = cmd_search(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    envs = {r["environment"] for r in data}
    assert envs <= {"staging"}

"""Tests for cmd_snapshot_diff_chain."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_diff_chain import (
    add_snapshot_diff_chain_subparsers,
    cmd_snapshot_diff_chain,
    _snapshots_for_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str, schema: dict, ts: str) -> Path:
    import json as _json

    path = directory / f"{env}_{ts}_abc123.json"
    payload = {"environment": env, "schema": schema, "hash": "abc123"}
    path.write_text(_json.dumps(payload))
    return path


def _make_args(snap_dir: str, env: str = "prod", limit: int = 5, fmt: str = "text"):
    ns = argparse.Namespace()
    ns.dir = snap_dir
    ns.env = env
    ns.limit = limit
    ns.fmt = fmt
    return ns


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


SCHEMA_V1 = {"users": {"id": "int", "name": "text"}}
SCHEMA_V2 = {"users": {"id": "int", "name": "text", "email": "text"}}
SCHEMA_V3 = {"users": {"id": "int", "name": "text", "email": "text"}, "orders": {"id": "int"}}


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

def test_add_snapshot_diff_chain_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_diff_chain_subparsers(sub)
    args = parser.parse_args(["diff-chain", "--dir", "/tmp", "--env", "prod"])
    assert args.func is cmd_snapshot_diff_chain


def test_add_snapshot_diff_chain_subparsers_defaults(snap_dir):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_diff_chain_subparsers(sub)
    args = parser.parse_args(["diff-chain", "--dir", str(snap_dir), "--env", "prod"])
    assert args.limit == 5
    assert args.fmt == "text"


# ---------------------------------------------------------------------------
# _snapshots_for_env
# ---------------------------------------------------------------------------

def test_snapshots_for_env_filters_by_env(snap_dir):
    _write_snapshot(snap_dir, "prod", SCHEMA_V1, "20240101T000000")
    _write_snapshot(snap_dir, "staging", SCHEMA_V1, "20240101T000000")
    result = _snapshots_for_env(snap_dir, "prod")
    assert all("prod" in p.name for p in result)


def test_snapshots_for_env_sorted_oldest_first(snap_dir):
    _write_snapshot(snap_dir, "prod", SCHEMA_V2, "20240102T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_V1, "20240101T000000")
    result = _snapshots_for_env(snap_dir, "prod")
    assert result[0].name < result[1].name


# ---------------------------------------------------------------------------
# cmd_snapshot_diff_chain
# ---------------------------------------------------------------------------

def test_cmd_diff_chain_missing_dir_returns_1(tmp_path):
    args = _make_args(str(tmp_path / "nonexistent"))
    assert cmd_snapshot_diff_chain(args) == 1


def test_cmd_diff_chain_too_few_snapshots_returns_1(snap_dir):
    _write_snapshot(snap_dir, "prod", SCHEMA_V1, "20240101T000000")
    args = _make_args(str(snap_dir))
    assert cmd_snapshot_diff_chain(args) == 1


def test_cmd_diff_chain_text_returns_zero(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", SCHEMA_V1, "20240101T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_V2, "20240102T000000")
    args = _make_args(str(snap_dir), fmt="text")
    rc = cmd_snapshot_diff_chain(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "→" in out


def test_cmd_diff_chain_json_returns_zero(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", SCHEMA_V1, "20240101T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_V2, "20240102T000000")
    args = _make_args(str(snap_dir), fmt="json")
    rc = cmd_snapshot_diff_chain(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert "from" in data[0] and "to" in data[0] and "diff" in data[0]


def test_cmd_diff_chain_limit_respected(snap_dir, capsys):
    for day in range(1, 6):  # 5 snapshots → 4 pairs
        _write_snapshot(snap_dir, "prod", SCHEMA_V1, f"202401{day:02d}T000000")
    args = _make_args(str(snap_dir), fmt="json", limit=2)
    cmd_snapshot_diff_chain(args)
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2

"""Tests for schemasnap.cmd_snapshot_index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_index import add_snapshot_index_subparsers, cmd_snapshot_index


# ------------------------------------------------------------------ helpers

def _write_snapshot(directory: Path, env: str, schema_hash: str, schema: dict) -> Path:
    filename = f"snapshot_{env}_{schema_hash}.json"
    path = directory / filename
    payload = {"environment": env, "schema_hash": schema_hash, "schema": schema}
    path.write_text(json.dumps(payload))
    return path


def _make_args(**kwargs):
    defaults = {"snapshot_dir": ".", "env": None, "schema_hash": None, "fmt": "text"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def snap_dir(tmp_path):
    _write_snapshot(tmp_path, "prod", "aabbcc0011", {"users": {"id": "int"}})
    _write_snapshot(tmp_path, "staging", "ddeeff2233", {"orders": {"id": "int"}})
    return tmp_path


# ------------------------------------------------------------------ tests

def test_add_snapshot_index_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_index_subparsers(sub)
    args = parser.parse_args(["snapshot-index", "/some/dir"])
    assert hasattr(args, "func")


def test_add_snapshot_index_subparsers_default_fmt():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_index_subparsers(sub)
    args = parser.parse_args(["snapshot-index", "/some/dir"])
    assert args.fmt == "text"


def test_cmd_snapshot_index_missing_dir_returns_1(tmp_path):
    args = _make_args(snapshot_dir=str(tmp_path / "nonexistent"))
    assert cmd_snapshot_index(args) == 1


def test_cmd_snapshot_index_returns_zero(snap_dir):
    args = _make_args(snapshot_dir=str(snap_dir))
    assert cmd_snapshot_index(args) == 0


def test_cmd_snapshot_index_text_output(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir))
    cmd_snapshot_index(args)
    out = capsys.readouterr().out
    assert "prod" in out
    assert "staging" in out


def test_cmd_snapshot_index_json_output(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), fmt="json")
    cmd_snapshot_index(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 2
    envs = {e["env"] for e in data}
    assert envs == {"prod", "staging"}


def test_cmd_snapshot_index_env_filter(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), env="prod")
    rc = cmd_snapshot_index(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "prod" in out
    assert "staging" not in out


def test_cmd_snapshot_index_unknown_env_returns_1(snap_dir):
    args = _make_args(snapshot_dir=str(snap_dir), env="dev")
    assert cmd_snapshot_index(args) == 1


def test_cmd_snapshot_index_hash_lookup(snap_dir, capsys):
    args = _make_args(snapshot_dir=str(snap_dir), schema_hash="aabb")
    rc = cmd_snapshot_index(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "aabbcc0011" in out


def test_cmd_snapshot_index_bad_hash_returns_1(snap_dir):
    args = _make_args(snapshot_dir=str(snap_dir), schema_hash="zzzzzz")
    assert cmd_snapshot_index(args) == 1

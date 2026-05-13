"""Tests for schemasnap.clone and schemasnap.cmd_clone."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from schemasnap.clone import clone_snapshot, CloneResult, _rewrite_env
from schemasnap.cmd_clone import cmd_clone


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


def _write_snapshot(directory: Path, env: str, schema_hash: str, schema: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = directory / f"snapshot_{env}_{schema_hash}.json"
    payload = {"environment": env, "schema_hash": schema_hash, "schema": schema}
    filename.write_text(json.dumps(payload))
    return filename


# ---------------------------------------------------------------------------
# Unit tests for _rewrite_env
# ---------------------------------------------------------------------------

def test_rewrite_env_changes_environment_field():
    data = {"environment": "prod", "schema": {}}
    result = _rewrite_env(data, "staging")
    assert result["environment"] == "staging"


def test_rewrite_env_does_not_mutate_original():
    data = {"environment": "prod", "schema": {}}
    _rewrite_env(data, "staging")
    assert data["environment"] == "prod"


# ---------------------------------------------------------------------------
# clone_snapshot tests
# ---------------------------------------------------------------------------

def test_clone_creates_dest_file(snap_dir):
    _write_snapshot(snap_dir, "prod", "abc123", {"users": {}})
    result = clone_snapshot(snap_dir, "prod", "staging")
    assert result.success
    assert result.dest_file is not None
    assert result.dest_file.exists()


def test_clone_dest_env_embedded_in_filename(snap_dir):
    _write_snapshot(snap_dir, "prod", "abc123", {"users": {}})
    result = clone_snapshot(snap_dir, "prod", "staging")
    assert "staging" in result.dest_file.name


def test_clone_dest_file_has_correct_env_field(snap_dir):
    _write_snapshot(snap_dir, "prod", "abc123", {"orders": {}})
    result = clone_snapshot(snap_dir, "prod", "staging")
    dest_data = json.loads(result.dest_file.read_text())
    assert dest_data["environment"] == "staging"


def test_clone_schema_preserved(snap_dir):
    schema = {"users": {"id": "int", "name": "text"}}
    _write_snapshot(snap_dir, "prod", "abc123", schema)
    result = clone_snapshot(snap_dir, "prod", "staging")
    dest_data = json.loads(result.dest_file.read_text())
    assert dest_data["schema"] == schema


def test_clone_missing_env_returns_failure(snap_dir):
    snap_dir.mkdir()
    result = clone_snapshot(snap_dir, "prod", "staging")
    assert not result.success
    assert "prod" in result.message


def test_clone_explicit_file_not_found_returns_failure(snap_dir, tmp_path):
    snap_dir.mkdir()
    result = clone_snapshot(snap_dir, "prod", "staging", source_file=tmp_path / "ghost.json")
    assert not result.success


def test_clone_explicit_file_used_when_provided(snap_dir):
    src = _write_snapshot(snap_dir, "prod", "deadbeef", {"items": {}})
    result = clone_snapshot(snap_dir, "prod", "qa", source_file=src)
    assert result.success
    assert result.source_file == src


# ---------------------------------------------------------------------------
# cmd_clone tests
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = {"snapshot_dir": "snapshots", "file": None}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_cmd_clone_success_returns_zero(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", "abc123", {})
    args = _make_args(source_env="prod", dest_env="staging", snapshot_dir=str(snap_dir))
    assert cmd_clone(args) == 0
    captured = capsys.readouterr()
    assert "staging" in captured.out


def test_cmd_clone_failure_returns_one(snap_dir, capsys):
    snap_dir.mkdir()
    args = _make_args(source_env="prod", dest_env="staging", snapshot_dir=str(snap_dir))
    assert cmd_clone(args) == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.out

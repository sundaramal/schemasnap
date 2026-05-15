"""Tests for schemasnap.cmd_snapshot_rename."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_rename import add_snapshot_rename_subparsers, cmd_snapshot_rename


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str, schema_hash: str = "abcd1234") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{env}_2024-01-15T10-30-00_{schema_hash[:8]}.json"
    data = {
        "environment": env,
        "schema_hash": schema_hash,
        "captured_at": "2024-01-15T10:30:00",
        "schema": {"users": {"id": "int"}},
    }
    path = directory / filename
    path.write_text(json.dumps(data))
    return path


def _make_args(snap_dir: Path, file: str, new_env: str, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        file=file,
        new_env=new_env,
        dir=str(snap_dir),
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_snapshot_rename_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_rename_subparsers(sub)
    args = parser.parse_args(["snapshot-rename", "snap.json", "prod"])
    assert args.func is cmd_snapshot_rename


def test_add_snapshot_rename_subparsers_default_dir():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_rename_subparsers(sub)
    args = parser.parse_args(["snapshot-rename", "snap.json", "prod"])
    assert args.dir == "snapshots"


def test_cmd_snapshot_rename_missing_file_returns_1(tmp_path):
    args = _make_args(tmp_path, str(tmp_path / "nonexistent.json"), "prod")
    assert cmd_snapshot_rename(args) == 1


def test_cmd_snapshot_rename_creates_new_file(tmp_path):
    src = _write_snapshot(tmp_path, "staging")
    args = _make_args(tmp_path, str(src), "production")
    result = cmd_snapshot_rename(args)
    assert result == 0
    files = list(tmp_path.glob("production_*.json"))
    assert len(files) == 1


def test_cmd_snapshot_rename_updates_environment_field(tmp_path):
    src = _write_snapshot(tmp_path, "staging")
    args = _make_args(tmp_path, str(src), "production")
    cmd_snapshot_rename(args)
    new_file = next(tmp_path.glob("production_*.json"))
    data = json.loads(new_file.read_text())
    assert data["environment"] == "production"


def test_cmd_snapshot_rename_removes_old_file(tmp_path):
    src = _write_snapshot(tmp_path, "staging")
    old_name = src.name
    args = _make_args(tmp_path, str(src), "production")
    cmd_snapshot_rename(args)
    assert not (tmp_path / old_name).exists()


def test_cmd_snapshot_rename_dry_run_does_not_create_file(tmp_path):
    src = _write_snapshot(tmp_path, "staging")
    args = _make_args(tmp_path, str(src), "production", dry_run=True)
    result = cmd_snapshot_rename(args)
    assert result == 0
    assert not list(tmp_path.glob("production_*.json"))
    # original file should still be present
    assert src.exists()


def test_cmd_snapshot_rename_preserves_schema_hash(tmp_path):
    src = _write_snapshot(tmp_path, "staging", schema_hash="deadbeef1234")
    args = _make_args(tmp_path, str(src), "production")
    cmd_snapshot_rename(args)
    new_file = next(tmp_path.glob("production_*.json"))
    data = json.loads(new_file.read_text())
    assert data["schema_hash"] == "deadbeef1234"

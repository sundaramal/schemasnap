"""Tests for schemasnap.cmd_snapshot_copy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_copy import add_snapshot_copy_subparsers, cmd_snapshot_copy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA = {
    "environment": "prod",
    "schema_hash": "abc123",
    "schema": {
        "users": {
            "id": {"type": "integer"},
            "email": {"type": "varchar"},
        }
    },
}


def _write_snapshot(directory: Path, env: str = "prod") -> Path:
    data = dict(_SCHEMA)
    data["environment"] = env
    p = directory / f"snapshot_{env}_abc123.json"
    p.write_text(json.dumps(data))
    return p


def _make_args(source: str, dest_env: str, dest_dir: str | None = None, fmt: str = "text") -> argparse.Namespace:
    return argparse.Namespace(
        source=source,
        dest_env=dest_env,
        dest_dir=dest_dir,
        fmt=fmt,
        func=cmd_snapshot_copy,
    )


# ---------------------------------------------------------------------------
# Sub-parser registration
# ---------------------------------------------------------------------------


def test_add_snapshot_copy_subparsers_registers_command():
    root = argparse.ArgumentParser()
    sub = root.add_subparsers()
    add_snapshot_copy_subparsers(sub)
    args = root.parse_args(["snapshot-copy", "snap.json", "staging"])
    assert args.func is cmd_snapshot_copy


def test_add_snapshot_copy_subparsers_default_fmt():
    root = argparse.ArgumentParser()
    sub = root.add_subparsers()
    add_snapshot_copy_subparsers(sub)
    args = root.parse_args(["snapshot-copy", "snap.json", "staging"])
    assert args.fmt == "text"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_cmd_snapshot_copy_missing_source_returns_1(tmp_path):
    args = _make_args(str(tmp_path / "nonexistent.json"), "staging")
    assert cmd_snapshot_copy(args) == 1


def test_cmd_snapshot_copy_missing_dest_dir_returns_1(tmp_path):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), "staging", dest_dir=str(tmp_path / "no_such_dir"))
    assert cmd_snapshot_copy(args) == 1


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


def test_cmd_snapshot_copy_creates_new_file(tmp_path):
    snap = _write_snapshot(tmp_path, env="prod")
    args = _make_args(str(snap), "staging")
    rc = cmd_snapshot_copy(args)
    assert rc == 0
    dest_files = [f for f in tmp_path.iterdir() if "staging" in f.name]
    assert len(dest_files) == 1


def test_cmd_snapshot_copy_new_file_has_correct_env(tmp_path):
    snap = _write_snapshot(tmp_path, env="prod")
    args = _make_args(str(snap), "staging")
    cmd_snapshot_copy(args)
    dest = next(f for f in tmp_path.iterdir() if "staging" in f.name)
    data = json.loads(dest.read_text())
    assert data["environment"] == "staging"


def test_cmd_snapshot_copy_json_fmt_is_valid_json(tmp_path, capsys):
    snap = _write_snapshot(tmp_path, env="prod")
    args = _make_args(str(snap), "staging", fmt="json")
    rc = cmd_snapshot_copy(args)
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["dest_env"] == "staging"
    assert "dest" in payload
    assert "schema_hash" in payload


def test_cmd_snapshot_copy_respects_dest_dir(tmp_path):
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()
    snap = _write_snapshot(src_dir, env="prod")
    args = _make_args(str(snap), "qa", dest_dir=str(dst_dir))
    rc = cmd_snapshot_copy(args)
    assert rc == 0
    dest_files = list(dst_dir.iterdir())
    assert len(dest_files) == 1
    assert "qa" in dest_files[0].name

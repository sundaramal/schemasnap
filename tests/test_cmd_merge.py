"""Tests for schemasnap.cmd_merge."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_merge import add_merge_subparsers, cmd_merge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(path: Path, env: str, schema: dict) -> Path:
    data = {"environment": env, "schema": schema}
    path.write_text(json.dumps(data))
    return path


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"output": None, "env": None, "as_json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_add_merge_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_merge_subparsers(sub)
    args = parser.parse_args(["merge", "a.json", "b.json"])
    assert hasattr(args, "func")
    assert args.func is cmd_merge


def test_cmd_merge_missing_primary_returns_1(snap_dir):
    args = _make_args(
        primary=str(snap_dir / "missing.json"),
        secondary=str(snap_dir / "also_missing.json"),
    )
    assert cmd_merge(args) == 1


def test_cmd_merge_missing_secondary_returns_1(snap_dir):
    primary = _write_snapshot(snap_dir / "primary.json", "prod", {"users": {"id": "int"}})
    args = _make_args(
        primary=str(primary),
        secondary=str(snap_dir / "missing.json"),
    )
    assert cmd_merge(args) == 1


def test_cmd_merge_writes_output_file(snap_dir, capsys):
    primary = _write_snapshot(snap_dir / "p.json", "prod", {"users": {"id": "int"}})
    secondary = _write_snapshot(snap_dir / "s.json", "staging", {"orders": {"id": "int"}})
    out_file = snap_dir / "merged.json"
    args = _make_args(
        primary=str(primary),
        secondary=str(secondary),
        output=str(out_file),
    )
    rc = cmd_merge(args)
    assert rc == 0
    assert out_file.exists()
    merged = json.loads(out_file.read_text())
    assert "users" in merged["schema"]
    assert "orders" in merged["schema"]


def test_cmd_merge_env_override(snap_dir):
    primary = _write_snapshot(snap_dir / "p.json", "prod", {"users": {"id": "int"}})
    secondary = _write_snapshot(snap_dir / "s.json", "staging", {})
    out_file = snap_dir / "merged.json"
    args = _make_args(
        primary=str(primary),
        secondary=str(secondary),
        output=str(out_file),
        env="combined",
    )
    cmd_merge(args)
    merged = json.loads(out_file.read_text())
    assert merged["environment"] == "combined"


def test_cmd_merge_json_summary_flag(snap_dir, capsys):
    primary = _write_snapshot(snap_dir / "p.json", "prod", {"t": {"id": "int"}})
    secondary = _write_snapshot(snap_dir / "s.json", "staging", {"t": {"id": "text"}})
    args = _make_args(
        primary=str(primary),
        secondary=str(secondary),
        as_json=True,
    )
    rc = cmd_merge(args)
    assert rc == 0
    captured = capsys.readouterr()
    # stderr should contain a valid JSON summary
    summary = json.loads(captured.err.strip().splitlines()[-1])
    assert "conflicts" in summary
    assert "summary" in summary

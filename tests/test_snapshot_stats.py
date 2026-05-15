"""Tests for schemasnap.snapshot_stats and cmd_snapshot_stats."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from schemasnap.snapshot_stats import collect_snapshot_stats, render_stats_text
from schemasnap.cmd_snapshot_stats import cmd_snapshot_stats, add_snapshot_stats_subparsers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap(env: str, schema: dict) -> dict:
    return {"environment": env, "hash": "abc123", "schema": schema}


SCHEMA_A = {"users": {"id": "int", "name": "text"}, "orders": {"id": "int"}}
SCHEMA_B = {"users": {"id": "int", "email": "text"}}


# ---------------------------------------------------------------------------
# Unit tests: collect_snapshot_stats
# ---------------------------------------------------------------------------

def test_collect_stats_empty():
    result = collect_snapshot_stats([])
    assert result["snapshot_count"] == 0
    assert result["total_tables"] == 0
    assert result["most_common_tables"] == []


def test_collect_stats_single_snapshot():
    result = collect_snapshot_stats([_snap("prod", SCHEMA_A)])
    assert result["snapshot_count"] == 1
    assert result["total_tables"] == 2
    assert result["total_columns"] == 3
    assert result["environments"] == ["prod"]


def test_collect_stats_multiple_snapshots():
    snaps = [_snap("prod", SCHEMA_A), _snap("staging", SCHEMA_B)]
    result = collect_snapshot_stats(snaps)
    assert result["snapshot_count"] == 2
    assert set(result["environments"]) == {"prod", "staging"}
    assert result["total_tables"] == 3  # 2 + 1
    assert result["total_columns"] == 5  # 3 + 2


def test_most_common_tables_ordering():
    snaps = [
        _snap("prod", {"users": {"id": "int"}}),
        _snap("staging", {"users": {"id": "int"}}),
        _snap("dev", {"orders": {"id": "int"}}),
    ]
    result = collect_snapshot_stats(snaps)
    assert result["most_common_tables"][0]["table"] == "users"
    assert result["most_common_tables"][0]["appearances"] == 2


def test_avg_tables_per_snapshot():
    snaps = [_snap("prod", SCHEMA_A), _snap("prod", SCHEMA_B)]
    result = collect_snapshot_stats(snaps)
    assert result["avg_tables_per_snapshot"] == 1.5


# ---------------------------------------------------------------------------
# Unit tests: render_stats_text
# ---------------------------------------------------------------------------

def test_render_stats_text_contains_key_fields():
    stats = collect_snapshot_stats([_snap("prod", SCHEMA_A)])
    text = render_stats_text(stats)
    assert "Snapshots" in text
    assert "prod" in text
    assert "users" in text


def test_render_stats_text_empty():
    stats = collect_snapshot_stats([])
    text = render_stats_text(stats)
    assert "0" in text


# ---------------------------------------------------------------------------
# Integration tests: cmd_snapshot_stats
# ---------------------------------------------------------------------------

@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    from schemasnap.snapshot import capture_snapshot
    capture_snapshot(SCHEMA_A, "prod", directory=tmp_path)
    capture_snapshot(SCHEMA_B, "staging", directory=tmp_path)
    return tmp_path


def _args(snap_dir, fmt="text", env=None):
    return SimpleNamespace(dir=str(snap_dir), fmt=fmt, env=env)


def test_cmd_snapshot_stats_returns_zero(snap_dir, capsys):
    assert cmd_snapshot_stats(_args(snap_dir)) == 0


def test_cmd_snapshot_stats_missing_dir_returns_1(tmp_path):
    missing = tmp_path / "no_such_dir"
    assert cmd_snapshot_stats(_args(missing)) == 1


def test_cmd_snapshot_stats_json_output(snap_dir, capsys):
    cmd_snapshot_stats(_args(snap_dir, fmt="json"))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["snapshot_count"] == 2
    assert "prod" in data["environments"]


def test_cmd_snapshot_stats_env_filter(snap_dir, capsys):
    cmd_snapshot_stats(_args(snap_dir, fmt="json", env="prod"))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["snapshot_count"] == 1


def test_add_snapshot_stats_subparsers_registers_command():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_stats_subparsers(sub)
    args = parser.parse_args(["snapshot-stats", "--dir", "/tmp", "--fmt", "json"])
    assert args.func is cmd_snapshot_stats
    assert args.fmt == "json"

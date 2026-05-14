"""Tests for schemasnap.cmd_similarity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_similarity import add_similarity_subparsers, cmd_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(path: Path, env: str, schema: dict) -> None:
    import json as _json
    path.write_text(
        _json.dumps({"environment": env, "schema": schema, "hash": "abc"})
    )


def _make_args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {
        "snapshot_a": str(tmp_path / "a.json"),
        "snapshot_b": str(tmp_path / "b.json"),
        "fmt": "text",
        "threshold": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Subparser registration
# ---------------------------------------------------------------------------

def test_add_similarity_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_similarity_subparsers(sub)
    args = parser.parse_args(["similarity", "a.json", "b.json"])
    assert hasattr(args, "func")


def test_add_similarity_subparsers_default_fmt():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_similarity_subparsers(sub)
    args = parser.parse_args(["similarity", "a.json", "b.json"])
    assert args.fmt == "text"


# ---------------------------------------------------------------------------
# Missing files
# ---------------------------------------------------------------------------

def test_cmd_similarity_missing_snapshot_a_returns_1(tmp_path):
    _write_snapshot(tmp_path / "b.json", "prod", {})
    args = _make_args(tmp_path, snapshot_a=str(tmp_path / "nope.json"))
    assert cmd_similarity(args) == 1


def test_cmd_similarity_missing_snapshot_b_returns_1(tmp_path):
    _write_snapshot(tmp_path / "a.json", "dev", {})
    args = _make_args(tmp_path, snapshot_b=str(tmp_path / "nope.json"))
    assert cmd_similarity(args) == 1


# ---------------------------------------------------------------------------
# Identical schemas
# ---------------------------------------------------------------------------

def test_cmd_similarity_identical_returns_zero(tmp_path):
    schema = {"users": {"id": "int", "name": "text"}}
    _write_snapshot(tmp_path / "a.json", "dev", schema)
    _write_snapshot(tmp_path / "b.json", "prod", schema)
    args = _make_args(tmp_path)
    assert cmd_similarity(args) == 0


def test_cmd_similarity_json_format(tmp_path, capsys):
    schema = {"orders": {"id": "int"}}
    _write_snapshot(tmp_path / "a.json", "dev", schema)
    _write_snapshot(tmp_path / "b.json", "prod", schema)
    args = _make_args(tmp_path, fmt="json")
    rc = cmd_similarity(args)
    assert rc == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "overall_score" in data
    assert data["overall_score"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Threshold enforcement
# ---------------------------------------------------------------------------

def test_cmd_similarity_below_threshold_returns_1(tmp_path):
    schema_a = {"users": {"id": "int", "name": "text"}}
    schema_b = {"orders": {"order_id": "int", "total": "float"}}
    _write_snapshot(tmp_path / "a.json", "dev", schema_a)
    _write_snapshot(tmp_path / "b.json", "prod", schema_b)
    args = _make_args(tmp_path, threshold=0.9)
    assert cmd_similarity(args) == 1


def test_cmd_similarity_above_threshold_returns_zero(tmp_path):
    schema = {"users": {"id": "int"}}
    _write_snapshot(tmp_path / "a.json", "dev", schema)
    _write_snapshot(tmp_path / "b.json", "prod", schema)
    args = _make_args(tmp_path, threshold=0.5)
    assert cmd_similarity(args) == 0

"""Tests for schemasnap.cmd_snapshot_show."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_show import add_snapshot_show_subparsers, cmd_snapshot_show


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str = "prod") -> Path:
    data = {
        "environment": env,
        "timestamp": "2024-01-01T00:00:00",
        "hash": "abc123",
        "schema": {
            "users": [
                {"name": "id", "type": "integer"},
                {"name": "email", "type": "varchar"},
            ],
            "orders": [
                {"name": "order_id", "type": "integer"},
            ],
        },
    }
    path = directory / f"snapshot_{env}_abc123.json"
    path.write_text(json.dumps(data))
    return path


def _make_args(snap_file: str, fmt: str = "text", table: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(snapshot_file=snap_file, fmt=fmt, table=table)


# ---------------------------------------------------------------------------
# subparser registration
# ---------------------------------------------------------------------------

def test_add_snapshot_show_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_show_subparsers(sub)
    args = parser.parse_args(["snapshot-show", "some_file.json"])
    assert args.func is cmd_snapshot_show


def test_add_snapshot_show_subparsers_default_fmt():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_show_subparsers(sub)
    args = parser.parse_args(["snapshot-show", "some_file.json"])
    assert args.fmt == "text"


# ---------------------------------------------------------------------------
# cmd_snapshot_show
# ---------------------------------------------------------------------------

def test_cmd_snapshot_show_missing_file_returns_1(tmp_path):
    args = _make_args(str(tmp_path / "nonexistent.json"))
    assert cmd_snapshot_show(args) == 1


def test_cmd_snapshot_show_text_returns_zero(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="text")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "prod" in out
    assert "users" in out
    assert "orders" in out


def test_cmd_snapshot_show_json_returns_zero(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="json")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "schema" in parsed
    assert "users" in parsed["schema"]


def test_cmd_snapshot_show_csv_returns_zero(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="csv")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "table" in out.lower() or "users" in out


def test_cmd_snapshot_show_markdown_returns_zero(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="markdown")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "|" in out


def test_cmd_snapshot_show_filter_table(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="text", table="users")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "users" in out
    assert "orders" not in out


def test_cmd_snapshot_show_unknown_table_returns_1(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="text", table="nonexistent")
    rc = cmd_snapshot_show(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "nonexistent" in err


def test_cmd_snapshot_show_json_with_table_filter(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    args = _make_args(str(snap), fmt="json", table="orders")
    rc = cmd_snapshot_show(args)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "orders" in parsed["schema"]
    assert "users" not in parsed["schema"]

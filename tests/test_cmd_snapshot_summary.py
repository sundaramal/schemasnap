"""Unit tests for schemasnap.cmd_snapshot_summary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_summary import (
    add_snapshot_summary_subparsers,
    cmd_snapshot_summary,
)


def _write_snapshot(path: Path, env: str = "prod") -> Path:
    data = {
        "environment": env,
        "hash": "deadbeef",
        "schema": {
            "accounts": {"id": "int", "name": "varchar"},
        },
    }
    path.write_text(json.dumps(data))
    return path


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"snapshot": "", "fmt": "text"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_snapshot_summary_subparsers_registers_command() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_summary_subparsers(sub)
    args = parser.parse_args(["snapshot-summary", "some_file.json"])
    assert hasattr(args, "func")


def test_add_snapshot_summary_subparsers_default_fmt() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_summary_subparsers(sub)
    args = parser.parse_args(["snapshot-summary", "x.json"])
    assert args.fmt == "text"


def test_cmd_snapshot_summary_missing_file_returns_1(tmp_path: Path) -> None:
    args = _make_args(snapshot=str(tmp_path / "nope.json"))
    assert cmd_snapshot_summary(args) == 1


def test_cmd_snapshot_summary_text_returns_zero(tmp_path: Path) -> None:
    snap = _write_snapshot(tmp_path / "snap.json")
    args = _make_args(snapshot=str(snap), fmt="text")
    assert cmd_snapshot_summary(args) == 0


def test_cmd_snapshot_summary_json_returns_zero(tmp_path: Path) -> None:
    snap = _write_snapshot(tmp_path / "snap.json")
    args = _make_args(snapshot=str(snap), fmt="json")
    assert cmd_snapshot_summary(args) == 0


def test_cmd_snapshot_summary_text_output(tmp_path: Path, capsys) -> None:
    snap = _write_snapshot(tmp_path / "snap.json", env="staging")
    args = _make_args(snapshot=str(snap), fmt="text")
    cmd_snapshot_summary(args)
    captured = capsys.readouterr()
    assert "staging" in captured.out
    assert "accounts" in captured.out


def test_cmd_snapshot_summary_json_output(tmp_path: Path, capsys) -> None:
    snap = _write_snapshot(tmp_path / "snap.json", env="dev")
    args = _make_args(snapshot=str(snap), fmt="json")
    cmd_snapshot_summary(args)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["environment"] == "dev"
    assert parsed["table_count"] == 1

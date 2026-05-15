"""Tests for cmd_snapshot_compare_chain CLI sub-command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_compare_chain import (
    add_snapshot_compare_chain_subparsers,
    cmd_snapshot_compare_chain,
)


def _write_snapshot(directory: Path, env: str, tag: str, schema: dict) -> None:
    data = {"environment": env, "schema": schema}
    (directory / f"{env}_{tag}.json").write_text(json.dumps(data))


def _make_args(**kwargs):
    defaults = {
        "env": "prod",
        "dir": "snapshots",
        "limit": 0,
        "fmt": "text",
        "changed_only": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_add_snapshot_compare_chain_subparsers_registers_command() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_compare_chain_subparsers(sub)
    args = parser.parse_args(["compare-chain", "prod"])
    assert args.env == "prod"


def test_add_snapshot_compare_chain_subparsers_defaults() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_compare_chain_subparsers(sub)
    args = parser.parse_args(["compare-chain", "staging"])
    assert args.dir == "snapshots"
    assert args.limit == 0
    assert args.fmt == "text"
    assert args.changed_only is False


def test_cmd_compare_chain_missing_dir_returns_1(tmp_path: Path) -> None:
    args = _make_args(dir=str(tmp_path / "no_such_dir"))
    assert cmd_snapshot_compare_chain(args) == 1


def test_cmd_compare_chain_empty_dir_returns_zero(snap_dir: Path) -> None:
    args = _make_args(env="prod", dir=str(snap_dir))
    assert cmd_snapshot_compare_chain(args) == 0


def test_cmd_compare_chain_text_output(snap_dir: Path, capsys) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int", "name": "text"}})
    args = _make_args(env="prod", dir=str(snap_dir))
    rc = cmd_snapshot_compare_chain(args)
    assert rc == 0
    captured = capsys.readouterr().out
    assert "CHANGED" in captured


def test_cmd_compare_chain_json_output(snap_dir: Path, capsys) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}})
    args = _make_args(env="prod", dir=str(snap_dir), fmt="json")
    rc = cmd_snapshot_compare_chain(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["env"] == "prod"
    assert "links" in data


def test_cmd_compare_chain_changed_only_filters(snap_dir: Path, capsys) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "003", {"t": {"id": "int", "x": "text"}})
    args = _make_args(env="prod", dir=str(snap_dir), changed_only=True)
    rc = cmd_snapshot_compare_chain(args)
    assert rc == 0
    captured = capsys.readouterr().out
    # only the changing link should appear
    assert "CHANGED" in captured
    assert captured.count("->") == 1


def test_cmd_compare_chain_limit_flag(snap_dir: Path) -> None:
    for i in range(1, 6):
        _write_snapshot(snap_dir, "prod", f"{i:03d}", {"t": {"id": "int"}})
    args = _make_args(env="prod", dir=str(snap_dir), limit=2)
    assert cmd_snapshot_compare_chain(args) == 0

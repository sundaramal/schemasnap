"""Integration tests for snapshot-summary via the argument parser."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_summary import add_snapshot_summary_subparsers


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    add_snapshot_summary_subparsers(sub)
    return parser


def _write_snapshot(path: Path, env: str, schema: dict) -> Path:
    data = {"environment": env, "hash": "cafebabe", "schema": schema}
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_integration_text_output_contains_hash(snap_dir: Path, capsys) -> None:
    snap = _write_snapshot(
        snap_dir / "snap.json",
        env="prod",
        schema={"widgets": {"id": "int", "name": "text"}},
    )
    parser = _make_parser()
    args = parser.parse_args(["snapshot-summary", str(snap)])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "cafebabe" in out


def test_integration_json_output_structure(snap_dir: Path, capsys) -> None:
    snap = _write_snapshot(
        snap_dir / "snap.json",
        env="staging",
        schema={
            "alpha": {"a": "int"},
            "beta": {"b": "int", "c": "varchar"},
        },
    )
    parser = _make_parser()
    args = parser.parse_args(["snapshot-summary", str(snap), "--fmt", "json"])
    rc = args.func(args)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["table_count"] == 2
    assert parsed["column_count"] == 3
    assert set(parsed["tables"]) == {"alpha", "beta"}


def test_integration_empty_schema(snap_dir: Path, capsys) -> None:
    snap = _write_snapshot(snap_dir / "empty.json", env="dev", schema={})
    parser = _make_parser()
    args = parser.parse_args(["snapshot-summary", str(snap), "--fmt", "json"])
    rc = args.func(args)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["table_count"] == 0
    assert parsed["column_count"] == 0

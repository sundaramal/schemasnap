"""Integration tests: diff-chain via the full CLI parser."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_diff_chain import (
    add_snapshot_diff_chain_subparsers,
    cmd_snapshot_diff_chain,
)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schemasnap")
    sub = parser.add_subparsers(dest="command")
    add_snapshot_diff_chain_subparsers(sub)
    return parser


def _write_snapshot(directory: Path, env: str, schema: dict, ts: str) -> Path:
    import json as _json

    path = directory / f"{env}_{ts}_abc.json"
    payload = {"environment": env, "schema": schema, "hash": "abc"}
    path.write_text(_json.dumps(payload))
    return path


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


SCHEMA_A = {"accounts": {"id": "int"}}
SCHEMA_B = {"accounts": {"id": "int", "balance": "numeric"}}
SCHEMA_C = {"accounts": {"id": "int", "balance": "numeric"}, "ledger": {"id": "int"}}


def test_integration_three_snapshots_two_diffs(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", SCHEMA_A, "20240101T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_B, "20240102T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_C, "20240103T000000")

    parser = _make_parser()
    args = parser.parse_args(["diff-chain", "--dir", str(snap_dir), "--env", "prod", "--fmt", "json"])
    rc = args.func(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2


def test_integration_no_cross_env_contamination(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", SCHEMA_A, "20240101T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_B, "20240102T000000")
    _write_snapshot(snap_dir, "staging", SCHEMA_A, "20240101T000000")
    _write_snapshot(snap_dir, "staging", SCHEMA_C, "20240102T000000")

    parser = _make_parser()
    args = parser.parse_args(["diff-chain", "--dir", str(snap_dir), "--env", "prod", "--fmt", "json"])
    rc = args.func(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    # Only prod pairs; staging must not appear
    for entry in data:
        assert "staging" not in entry["from"]
            

def test_integration_json_diff_structure(snap_dir, capsys):
    _write_snapshot(snap_dir, "prod", SCHEMA_A, "20240101T000000")
    _write_snapshot(snap_dir, "prod", SCHEMA_B, "20240102T000000")

    parser = _make_parser()
    args = parser.parse_args(["diff-chain", "--dir", str(snap_dir), "--env", "prod", "--fmt", "json"])
    args.func(args)
    data = json.loads(capsys.readouterr().out)
    entry = data[0]
    assert "from" in entry
    assert "to" in entry
    diff = entry["diff"]
    assert "added_tables" in diff or "removed_tables" in diff or "modified_tables" in diff


def test_integration_limit_zero_means_all(snap_dir, capsys):
    for i in range(1, 5):
        _write_snapshot(snap_dir, "prod", SCHEMA_A, f"202401{i:02d}T000000")

    parser = _make_parser()
    args = parser.parse_args(
        ["diff-chain", "--dir", str(snap_dir), "--env", "prod", "--fmt", "json", "--limit", "0"]
    )
    args.func(args)
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 3  # 4 snapshots → 3 pairs

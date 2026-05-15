"""Integration tests: build_parser -> compare-chain end-to-end."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_compare_chain import add_snapshot_compare_chain_subparsers


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    add_snapshot_compare_chain_subparsers(sub)
    return parser


def _write_snapshot(directory: Path, env: str, tag: str, schema: dict) -> None:
    data = {"environment": env, "schema": schema}
    (directory / f"{env}_{tag}.json").write_text(json.dumps(data))


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_integration_three_snapshots_via_parser(snap_dir: Path, capsys) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"orders": {"id": "int"}})
    _write_snapshot(
        snap_dir, "prod", "002", {"orders": {"id": "int", "total": "numeric"}}
    )
    _write_snapshot(
        snap_dir, "prod", "003", {"orders": {"id": "int", "total": "numeric"}}
    )
    parser = _make_parser()
    args = parser.parse_args(["compare-chain", "prod", "--dir", str(snap_dir)])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "links=2" in out
    assert "changed=1" in out


def test_integration_json_output_structure(snap_dir: Path, capsys) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}, "s": {"x": "text"}})
    parser = _make_parser()
    args = parser.parse_args(
        ["compare-chain", "prod", "--dir", str(snap_dir), "--fmt", "json"]
    )
    rc = args.func(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_links"] == 1
    assert data["changed_links"] == 1
    link = data["links"][0]
    assert "s" in link["added_tables"]


def test_integration_no_cross_env_contamination(snap_dir: Path) -> None:
    _write_snapshot(snap_dir, "prod", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "prod", "002", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "staging", "001", {"t": {"id": "int"}})
    _write_snapshot(snap_dir, "staging", "002", {"t": {"id": "int"}})
    from schemasnap.snapshot_compare_chain import compare_snapshot_chain

    prod_result = compare_snapshot_chain(str(snap_dir), "prod")
    staging_result = compare_snapshot_chain(str(snap_dir), "staging")
    assert prod_result.total_links == 1
    assert staging_result.total_links == 1

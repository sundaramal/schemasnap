"""Integration tests: snapshot-show via the full argument parser."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from schemasnap.cmd_snapshot_show import add_snapshot_show_subparsers


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schemasnap")
    sub = parser.add_subparsers(dest="command")
    add_snapshot_show_subparsers(sub)
    return parser


def _write_snapshot(directory: Path) -> Path:
    data = {
        "environment": "staging",
        "timestamp": "2024-06-01T12:00:00",
        "hash": "deadbeef",
        "schema": {
            "products": [
                {"name": "id", "type": "bigint"},
                {"name": "sku", "type": "varchar"},
                {"name": "price", "type": "numeric"},
            ],
            "categories": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "text"},
            ],
        },
    }
    path = directory / "snapshot_staging_deadbeef.json"
    path.write_text(json.dumps(data))
    return path


def test_integration_text_output_contains_metadata(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    parser = _make_parser()
    args = parser.parse_args(["snapshot-show", str(snap)])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "staging" in out
    assert "deadbeef" in out
    assert "2" in out  # 2 tables


def test_integration_json_roundtrip(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    parser = _make_parser()
    args = parser.parse_args(["snapshot-show", str(snap), "--fmt", "json"])
    rc = args.func(args)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["environment"] == "staging"
    assert set(parsed["schema"].keys()) == {"products", "categories"}


def test_integration_table_flag_isolates_table(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    parser = _make_parser()
    args = parser.parse_args(["snapshot-show", str(snap), "--table", "products"])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "products" in out
    assert "categories" not in out


def test_integration_csv_all_columns_present(tmp_path, capsys):
    snap = _write_snapshot(tmp_path)
    parser = _make_parser()
    args = parser.parse_args(["snapshot-show", str(snap), "--fmt", "csv"])
    rc = args.func(args)
    assert rc == 0
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) >= 2  # header + at least one data row
    assert "sku" in out


def test_integration_missing_file_returns_1(tmp_path):
    parser = _make_parser()
    args = parser.parse_args(["snapshot-show", str(tmp_path / "ghost.json")])
    rc = args.func(args)
    assert rc == 1

"""Integration tests: round-trip archive create -> list -> extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_archive import add_snapshot_archive_subparsers


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    add_snapshot_archive_subparsers(sub)
    return parser


def _write_snapshot(directory: Path, env: str, hash_: str, tables: dict | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{env}_{hash_}.json"
    path.write_text(json.dumps({
        "environment": env,
        "schema_hash": hash_,
        "captured_at": "2024-03-15T08:00:00",
        "schema": tables or {"users": {"id": "int", "email": "text"}},
    }))
    return path


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    d = tmp_path / "snaps"
    _write_snapshot(d, "prod", "hash1")
    _write_snapshot(d, "prod", "hash2")
    _write_snapshot(d, "dev", "hash3")
    return d


# ---------------------------------------------------------------------------
# integration tests
# ---------------------------------------------------------------------------

def test_roundtrip_create_and_extract(snap_dir: Path, tmp_path: Path) -> None:
    """Files written into snap_dir survive create -> extract unchanged."""
    parser = _make_parser()
    archive = tmp_path / "bundle.zip"
    restored = tmp_path / "restored"

    args_create = parser.parse_args(["archive-create", "--dir", str(snap_dir), "--out", str(archive)])
    assert args_create.func(args_create) == 0

    args_extract = parser.parse_args(["archive-extract", str(archive), "--dir", str(restored)])
    assert args_extract.func(args_extract) == 0

    original_names = {p.name for p in snap_dir.glob("*.json")}
    restored_names = {p.name for p in restored.glob("*.json")}
    assert original_names == restored_names


def test_env_filter_only_archives_matching(snap_dir: Path, tmp_path: Path) -> None:
    parser = _make_parser()
    archive = tmp_path / "prod_only.zip"
    args = parser.parse_args([
        "archive-create", "--dir", str(snap_dir), "--out", str(archive), "--env", "prod",
    ])
    assert args.func(args) == 0

    from schemasnap.snapshot_archive import list_archive_contents
    contents = list_archive_contents(archive)
    assert all(c["environment"] == "prod" for c in contents)
    assert len(contents) == 2


def test_list_json_output_matches_create_count(snap_dir: Path, tmp_path: Path, capsys) -> None:
    parser = _make_parser()
    archive = tmp_path / "all.zip"

    args_create = parser.parse_args(["archive-create", "--dir", str(snap_dir), "--out", str(archive)])
    args_create.func(args_create)

    args_list = parser.parse_args(["archive-list", str(archive), "--fmt", "json"])
    args_list.func(args_list)

    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 3

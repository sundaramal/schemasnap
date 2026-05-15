"""Tests for schemasnap.cmd_snapshot_archive CLI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_archive import (
    add_snapshot_archive_subparsers,
    cmd_archive_create,
    cmd_archive_extract,
    cmd_archive_list,
)
from schemasnap.snapshot_archive import create_archive


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str, hash_: str) -> Path:
    import json as _json
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{env}_{hash_}.json"
    path.write_text(_json.dumps({
        "environment": env,
        "schema_hash": hash_,
        "captured_at": "2024-06-01T12:00:00",
        "schema": {},
    }))
    return path


def _make_args(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    d = tmp_path / "snaps"
    _write_snapshot(d, "prod", "abc123")
    _write_snapshot(d, "staging", "def456")
    return d


# ---------------------------------------------------------------------------
# subparser registration
# ---------------------------------------------------------------------------

def test_add_snapshot_archive_subparsers_registers_commands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_archive_subparsers(sub)
    choices = list(sub.choices.keys())  # type: ignore[attr-defined]
    assert "archive-create" in choices
    assert "archive-extract" in choices
    assert "archive-list" in choices


# ---------------------------------------------------------------------------
# cmd_archive_create
# ---------------------------------------------------------------------------

def test_cmd_archive_create_returns_zero(snap_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "bundle.zip"
    args = _make_args(dir=str(snap_dir), out=str(out), env=None)
    assert cmd_archive_create(args) == 0
    assert out.exists()


def test_cmd_archive_create_missing_dir_returns_1(tmp_path: Path) -> None:
    args = _make_args(dir=str(tmp_path / "nope"), out=str(tmp_path / "out.zip"), env=None)
    assert cmd_archive_create(args) == 1


# ---------------------------------------------------------------------------
# cmd_archive_extract
# ---------------------------------------------------------------------------

def test_cmd_archive_extract_returns_zero(snap_dir: Path, tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    create_archive(snap_dir, archive)
    dest = tmp_path / "restored"
    args = _make_args(archive=str(archive), dir=str(dest))
    assert cmd_archive_extract(args) == 0
    assert any(dest.iterdir())


def test_cmd_archive_extract_missing_archive_returns_1(tmp_path: Path) -> None:
    args = _make_args(archive=str(tmp_path / "ghost.zip"), dir=str(tmp_path / "out"))
    assert cmd_archive_extract(args) == 1


# ---------------------------------------------------------------------------
# cmd_archive_list
# ---------------------------------------------------------------------------

def test_cmd_archive_list_text_returns_zero(snap_dir: Path, tmp_path: Path, capsys) -> None:
    archive = tmp_path / "bundle.zip"
    create_archive(snap_dir, archive)
    args = _make_args(archive=str(archive), fmt="text")
    assert cmd_archive_list(args) == 0


def test_cmd_archive_list_json_is_valid(snap_dir: Path, tmp_path: Path, capsys) -> None:
    archive = tmp_path / "bundle.zip"
    create_archive(snap_dir, archive)
    args = _make_args(archive=str(archive), fmt="json")
    cmd_archive_list(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 2


def test_cmd_archive_list_missing_archive_returns_1(tmp_path: Path) -> None:
    args = _make_args(archive=str(tmp_path / "ghost.zip"), fmt="text")
    assert cmd_archive_list(args) == 1

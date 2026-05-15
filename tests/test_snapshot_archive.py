"""Tests for schemasnap.snapshot_archive."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from schemasnap.snapshot_archive import (
    ArchiveResult,
    create_archive,
    extract_archive,
    list_archive_contents,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(directory: Path, env: str, hash_: str, tables: dict | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{env}_{hash_}.json"
    data = {
        "environment": env,
        "schema_hash": hash_,
        "captured_at": "2024-01-01T00:00:00",
        "schema": tables or {},
    }
    path = directory / filename
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    d = tmp_path / "snapshots"
    _write_snapshot(d, "prod", "aaa111")
    _write_snapshot(d, "prod", "bbb222")
    _write_snapshot(d, "staging", "ccc333")
    return d


# ---------------------------------------------------------------------------
# create_archive
# ---------------------------------------------------------------------------

def test_create_archive_produces_zip(snap_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.zip"
    result = create_archive(snap_dir, dest)
    assert dest.exists()
    assert zipfile.is_zipfile(dest)


def test_create_archive_result_snapshot_count(snap_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.zip"
    result = create_archive(snap_dir, dest)
    assert result.snapshot_count == 3
    assert result.skipped == []


def test_create_archive_env_filter(snap_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.zip"
    result = create_archive(snap_dir, dest, env="prod")
    assert result.snapshot_count == 2


def test_create_archive_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_archive(tmp_path / "no_such_dir", tmp_path / "out.zip")


def test_create_archive_summary_contains_path(snap_dir: Path, tmp_path: Path) -> None:
    dest = tmp_path / "out.zip"
    result = create_archive(snap_dir, dest)
    assert str(dest) in result.summary


# ---------------------------------------------------------------------------
# extract_archive
# ---------------------------------------------------------------------------

def test_extract_archive_restores_files(snap_dir: Path, tmp_path: Path) -> None:
    archive = tmp_path / "out.zip"
    create_archive(snap_dir, archive)
    dest = tmp_path / "restored"
    paths = extract_archive(archive, dest)
    assert len(paths) == 3
    assert all(p.exists() for p in paths)


def test_extract_archive_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_archive(tmp_path / "ghost.zip", tmp_path / "out")


# ---------------------------------------------------------------------------
# list_archive_contents
# ---------------------------------------------------------------------------

def test_list_archive_contents_returns_metadata(snap_dir: Path, tmp_path: Path) -> None:
    archive = tmp_path / "out.zip"
    create_archive(snap_dir, archive)
    contents = list_archive_contents(archive)
    assert len(contents) == 3
    envs = {c["environment"] for c in contents}
    assert "prod" in envs
    assert "staging" in envs


def test_list_archive_contents_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list_archive_contents(tmp_path / "ghost.zip")


def test_list_archive_contents_has_hash(snap_dir: Path, tmp_path: Path) -> None:
    archive = tmp_path / "out.zip"
    create_archive(snap_dir, archive)
    contents = list_archive_contents(archive)
    assert all("schema_hash" in c for c in contents)

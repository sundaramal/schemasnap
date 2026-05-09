"""Tests for schemasnap.rollback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemasnap.rollback import rollback_to, _find_snapshot_by_hash, _find_snapshot_by_tag
from schemasnap.snapshot import capture_snapshot
from schemasnap.tag import save_tag


SCHEMA_A = {"users": {"id": "int", "name": "text"}}
SCHEMA_B = {"orders": {"id": "int", "total": "float"}}


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


def test_rollback_requires_exactly_one_ref(snap_dir):
    with pytest.raises(ValueError, match="exactly one"):
        rollback_to(snap_dir, "prod", schema_hash="abc", tag_name="v1")

    with pytest.raises(ValueError, match="exactly one"):
        rollback_to(snap_dir, "prod")


def test_rollback_by_hash_not_found_returns_failure(snap_dir):
    snap_dir.mkdir(parents=True)
    result = rollback_to(snap_dir, "prod", schema_hash="deadbeef")
    assert not result.success
    assert "deadbeef" in result.message


def test_rollback_by_hash_success(snap_dir):
    snap_dir.mkdir(parents=True)
    original = capture_snapshot(SCHEMA_A, "prod", snap_dir)
    original_hash = original.stem.split("_")[-1]

    result = rollback_to(snap_dir, "prod", schema_hash=original_hash)

    assert result.success
    assert original_hash in result.source_file
    # A new snapshot file should have been written
    assert result.dest_file != result.source_file
    dest = Path(result.dest_file)
    assert dest.exists()
    assert json.loads(dest.read_text()) == SCHEMA_A


def test_rollback_by_tag_not_found_returns_failure(snap_dir):
    snap_dir.mkdir(parents=True)
    result = rollback_to(snap_dir, "prod", tag_name="v1")
    assert not result.success
    assert "v1" in result.message


def test_rollback_by_tag_success(snap_dir):
    snap_dir.mkdir(parents=True)
    original = capture_snapshot(SCHEMA_A, "staging", snap_dir)
    save_tag(snap_dir, "staging", "release-1", original.name)

    result = rollback_to(snap_dir, "staging", tag_name="release-1")

    assert result.success
    dest = Path(result.dest_file)
    assert dest.exists()
    assert json.loads(dest.read_text()) == SCHEMA_A


def test_find_snapshot_by_hash_returns_none_when_missing(snap_dir):
    snap_dir.mkdir(parents=True)
    assert _find_snapshot_by_hash(snap_dir, "prod", "nope") is None


def test_find_snapshot_by_tag_returns_none_when_missing(snap_dir):
    snap_dir.mkdir(parents=True)
    assert _find_snapshot_by_tag(snap_dir, "prod", "ghost") is None

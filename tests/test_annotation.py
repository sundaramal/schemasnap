"""Tests for schemasnap.annotation."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from schemasnap.annotation import (
    AnnotationEntry,
    _annotations_path,
    delete_annotation,
    get_annotations_for,
    load_annotations,
    save_annotation,
)


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _entry(snapshot_file: str = "snap_prod_abc.json", note: str = "ok") -> AnnotationEntry:
    return AnnotationEntry(
        snapshot_file=snapshot_file,
        env="prod",
        note=note,
        author="alice",
        timestamp="2024-01-01T00:00:00+00:00",
    )


def test_load_annotations_empty_when_no_file(tmp_dir):
    assert load_annotations(str(tmp_dir)) == []


def test_save_and_load_roundtrip(tmp_dir):
    entry = _entry()
    save_annotation(str(tmp_dir), entry)
    loaded = load_annotations(str(tmp_dir))
    assert len(loaded) == 1
    assert loaded[0] == entry


def test_save_multiple_entries(tmp_dir):
    save_annotation(str(tmp_dir), _entry(note="first"))
    save_annotation(str(tmp_dir), _entry(note="second"))
    loaded = load_annotations(str(tmp_dir))
    assert len(loaded) == 2
    assert loaded[0].note == "first"
    assert loaded[1].note == "second"


def test_annotations_file_is_jsonl(tmp_dir):
    save_annotation(str(tmp_dir), _entry())
    lines = _annotations_path(str(tmp_dir)).read_text().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert "snapshot_file" in data
    assert "note" in data


def test_get_annotations_for_filters_by_file(tmp_dir):
    save_annotation(str(tmp_dir), _entry(snapshot_file="snap_a.json", note="for a"))
    save_annotation(str(tmp_dir), _entry(snapshot_file="snap_b.json", note="for b"))
    results = get_annotations_for(str(tmp_dir), "snap_a.json")
    assert len(results) == 1
    assert results[0].note == "for a"


def test_get_annotations_for_returns_empty_when_no_match(tmp_dir):
    save_annotation(str(tmp_dir), _entry(snapshot_file="snap_a.json"))
    results = get_annotations_for(str(tmp_dir), "snap_b.json")
    assert results == []


def test_delete_annotation_removes_entry(tmp_dir):
    e = _entry()
    save_annotation(str(tmp_dir), e)
    removed = delete_annotation(str(tmp_dir), e.snapshot_file, e.author, e.timestamp)
    assert removed == 1
    assert load_annotations(str(tmp_dir)) == []


def test_delete_annotation_keeps_others(tmp_dir):
    e1 = _entry(note="keep")
    e2 = AnnotationEntry(
        snapshot_file="snap_prod_abc.json",
        env="prod",
        note="remove",
        author="bob",
        timestamp="2024-06-01T00:00:00+00:00",
    )
    save_annotation(str(tmp_dir), e1)
    save_annotation(str(tmp_dir), e2)
    removed = delete_annotation(str(tmp_dir), e2.snapshot_file, e2.author, e2.timestamp)
    assert removed == 1
    remaining = load_annotations(str(tmp_dir))
    assert len(remaining) == 1
    assert remaining[0].note == "keep"


def test_delete_annotation_returns_zero_when_no_match(tmp_dir):
    save_annotation(str(tmp_dir), _entry())
    removed = delete_annotation(str(tmp_dir), "nonexistent.json", "alice", "ts")
    assert removed == 0
    assert len(load_annotations(str(tmp_dir))) == 1

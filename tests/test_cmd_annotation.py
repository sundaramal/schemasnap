"""Tests for schemasnap.cmd_annotation CLI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.annotation import AnnotationEntry, save_annotation
from schemasnap.cmd_annotation import (
    cmd_annotation_add,
    cmd_annotation_delete,
    cmd_annotation_list,
    cmd_annotation_show,
)


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        snapshot_file="snap_prod_abc.json",
        env="prod",
        note="test note",
        author="alice",
        snapshot_dir="/tmp/snap",
        as_json=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_annotation_add_returns_zero(tmp_dir, capsys):
    args = _make_args(snapshot_dir=str(tmp_dir))
    rc = cmd_annotation_add(args)
    assert rc == 0


def test_cmd_annotation_add_saves_entry(tmp_dir):
    args = _make_args(snapshot_dir=str(tmp_dir), note="important change")
    cmd_annotation_add(args)
    from schemasnap.annotation import load_annotations
    entries = load_annotations(str(tmp_dir))
    assert len(entries) == 1
    assert entries[0].note == "important change"
    assert entries[0].author == "alice"


def test_cmd_annotation_show_text(tmp_dir, capsys):
    entry = AnnotationEntry(
        snapshot_file="snap_prod_abc.json",
        env="prod",
        note="hello",
        author="bob",
        timestamp="2024-01-01T00:00:00+00:00",
    )
    save_annotation(str(tmp_dir), entry)
    args = _make_args(snapshot_dir=str(tmp_dir), as_json=False)
    rc = cmd_annotation_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "hello" in out
    assert "bob" in out


def test_cmd_annotation_show_json(tmp_dir, capsys):
    entry = AnnotationEntry(
        snapshot_file="snap_prod_abc.json",
        env="prod",
        note="json note",
        author="carol",
        timestamp="2024-01-02T00:00:00+00:00",
    )
    save_annotation(str(tmp_dir), entry)
    args = _make_args(snapshot_dir=str(tmp_dir), as_json=True)
    cmd_annotation_show(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["note"] == "json note"


def test_cmd_annotation_list_json(tmp_dir, capsys):
    save_annotation(str(tmp_dir), AnnotationEntry(
        snapshot_file="snap_a.json", env="dev", note="n1", author="a",
        timestamp="2024-01-01T00:00:00+00:00"
    ))
    save_annotation(str(tmp_dir), AnnotationEntry(
        snapshot_file="snap_b.json", env="prod", note="n2", author="b",
        timestamp="2024-01-02T00:00:00+00:00"
    ))
    args = argparse.Namespace(snapshot_dir=str(tmp_dir), as_json=True)
    rc = cmd_annotation_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2


def test_cmd_annotation_delete_removes_entry(tmp_dir, capsys):
    ts = "2024-03-01T00:00:00+00:00"
    entry = AnnotationEntry(
        snapshot_file="snap_prod_abc.json", env="prod",
        note="to delete", author="alice", timestamp=ts
    )
    save_annotation(str(tmp_dir), entry)
    args = argparse.Namespace(
        snapshot_dir=str(tmp_dir),
        snapshot_file="snap_prod_abc.json",
        author="alice",
        timestamp=ts,
    )
    rc = cmd_annotation_delete(args)
    assert rc == 0
    from schemasnap.annotation import load_annotations
    assert load_annotations(str(tmp_dir)) == []

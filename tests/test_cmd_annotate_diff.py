"""Tests for schemasnap.cmd_annotate_diff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_annotate_diff import add_annotate_diff_subparsers, cmd_annotate_diff
from schemasnap.annotation import load_annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(path: Path, env: str, schema: dict) -> None:
    payload = {"environment": env, "schema": schema}
    path.write_text(json.dumps(payload))


def _make_args(tmp_path: Path, **overrides):
    snap_a = tmp_path / "snap_a.json"
    snap_b = tmp_path / "snap_b.json"
    _write_snapshot(snap_a, "prod", {"users": {"id": "int"}})
    _write_snapshot(snap_b, "staging", {"users": {"id": "int", "email": "text"}})

    defaults = dict(
        snapshot_a=str(snap_a),
        snapshot_b=str(snap_b),
        note="Expected: email column added in staging sprint-42",
        author="alice",
        annotations_dir=str(tmp_path),
        no_audit=True,
    )
    defaults.update(overrides)
    ns = argparse.Namespace(**defaults)
    return ns


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

def test_add_annotate_diff_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_annotate_diff_subparsers(sub)
    args = parser.parse_args([])
    # just verify no error during registration


def test_add_annotate_diff_subparsers_default_author(tmp_path):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    add_annotate_diff_subparsers(sub)
    snap_a = tmp_path / "a.json"
    snap_b = tmp_path / "b.json"
    snap_a.write_text("{}")
    snap_b.write_text("{}")
    args = parser.parse_args(["annotate-diff", str(snap_a), str(snap_b), "--note", "x"])
    assert args.author == "schemasnap"


# ---------------------------------------------------------------------------
# cmd_annotate_diff
# ---------------------------------------------------------------------------

def test_cmd_annotate_diff_returns_zero(tmp_path):
    args = _make_args(tmp_path)
    rc = cmd_annotate_diff(args)
    assert rc == 0


def test_cmd_annotate_diff_saves_annotation_for_both_files(tmp_path):
    args = _make_args(tmp_path)
    cmd_annotate_diff(args)

    entries = load_annotations(tmp_path)
    assert len(entries) == 2
    notes = {e.note for e in entries}
    assert notes == {args.note}


def test_cmd_annotate_diff_records_author(tmp_path):
    args = _make_args(tmp_path, author="bob")
    cmd_annotate_diff(args)

    entries = load_annotations(tmp_path)
    authors = {e.author for e in entries}
    assert authors == {"bob"}


def test_cmd_annotate_diff_missing_snapshot_a_returns_1(tmp_path):
    args = _make_args(tmp_path)
    args.snapshot_a = str(tmp_path / "nonexistent.json")
    rc = cmd_annotate_diff(args)
    assert rc == 1


def test_cmd_annotate_diff_missing_snapshot_b_returns_1(tmp_path):
    args = _make_args(tmp_path)
    args.snapshot_b = str(tmp_path / "nonexistent.json")
    rc = cmd_annotate_diff(args)
    assert rc == 1


def test_cmd_annotate_diff_identical_snapshots_still_annotates(tmp_path):
    snap_a = tmp_path / "snap_a.json"
    snap_b = tmp_path / "snap_b.json"
    schema = {"orders": {"id": "int"}}
    _write_snapshot(snap_a, "prod", schema)
    _write_snapshot(snap_b, "prod", schema)

    args = argparse.Namespace(
        snapshot_a=str(snap_a),
        snapshot_b=str(snap_b),
        note="no changes expected",
        author="ci",
        annotations_dir=str(tmp_path),
        no_audit=True,
    )
    rc = cmd_annotate_diff(args)
    assert rc == 0
    entries = load_annotations(tmp_path)
    assert len(entries) == 2

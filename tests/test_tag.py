"""Tests for schemasnap.tag and schemasnap.cmd_tag."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.tag import (
    TagEntry,
    get_tag,
    list_tags,
    load_tags,
    remove_tag,
    save_tag,
)
from schemasnap.cmd_tag import cmd_tag_set, cmd_tag_show, cmd_tag_list, cmd_tag_remove


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> str:
    return str(tmp_path)


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"snapshot_dir": "snapshots", "env": "prod", "tag": "v1", "note": "", "file": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- tag module ---

def test_load_tags_empty_when_no_file(tmp_dir):
    assert load_tags(tmp_dir) == []


def test_save_and_load_tag_roundtrip(tmp_dir):
    entry = TagEntry(snapshot_file="snap_prod_abc.json", tag="release-1", env="prod", note="first")
    save_tag(tmp_dir, entry)
    tags = load_tags(tmp_dir)
    assert len(tags) == 1
    assert tags[0].tag == "release-1"
    assert tags[0].note == "first"


def test_save_tag_overwrites_same_file(tmp_dir):
    e1 = TagEntry(snapshot_file="snap.json", tag="old", env="prod")
    e2 = TagEntry(snapshot_file="snap.json", tag="new", env="prod")
    save_tag(tmp_dir, e1)
    save_tag(tmp_dir, e2)
    tags = load_tags(tmp_dir)
    assert len(tags) == 1
    assert tags[0].tag == "new"


def test_get_tag_returns_entry(tmp_dir):
    entry = TagEntry(snapshot_file="snap.json", tag="stable", env="staging")
    save_tag(tmp_dir, entry)
    result = get_tag(tmp_dir, "stable")
    assert result is not None
    assert result.env == "staging"


def test_get_tag_returns_none_when_missing(tmp_dir):
    assert get_tag(tmp_dir, "nonexistent") is None


def test_remove_tag_returns_true_when_exists(tmp_dir):
    save_tag(tmp_dir, TagEntry(snapshot_file="f.json", tag="x", env="dev"))
    assert remove_tag(tmp_dir, "x") is True
    assert get_tag(tmp_dir, "x") is None


def test_remove_tag_returns_false_when_missing(tmp_dir):
    assert remove_tag(tmp_dir, "ghost") is False


def test_list_tags_filters_by_env(tmp_dir):
    save_tag(tmp_dir, TagEntry(snapshot_file="a.json", tag="t1", env="prod"))
    save_tag(tmp_dir, TagEntry(snapshot_file="b.json", tag="t2", env="staging"))
    prod_tags = list_tags(tmp_dir, env="prod")
    assert len(prod_tags) == 1
    assert prod_tags[0].tag == "t1"


# --- cmd_tag ---

def test_cmd_tag_set_uses_explicit_file(tmp_dir):
    args = _make_args(snapshot_dir=tmp_dir, env="prod", tag="v2", file="snap_prod_xyz.json", note="")
    rc = cmd_tag_set(args)
    assert rc == 0
    assert get_tag(tmp_dir, "v2") is not None


def test_cmd_tag_set_returns_1_when_no_snapshot(tmp_dir):
    args = _make_args(snapshot_dir=tmp_dir, env="prod", tag="v2", file=None, note="")
    rc = cmd_tag_set(args)
    assert rc == 1


def test_cmd_tag_show_prints_entry(tmp_dir, capsys):
    save_tag(tmp_dir, TagEntry(snapshot_file="snap.json", tag="rel", env="prod", note="hi"))
    args = _make_args(snapshot_dir=tmp_dir, tag="rel")
    rc = cmd_tag_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "rel" in out
    assert "snap.json" in out


def test_cmd_tag_show_returns_1_when_missing(tmp_dir):
    args = _make_args(snapshot_dir=tmp_dir, tag="nope")
    rc = cmd_tag_show(args)
    assert rc == 1


def test_cmd_tag_list_prints_all(tmp_dir, capsys):
    save_tag(tmp_dir, TagEntry(snapshot_file="a.json", tag="alpha", env="dev"))
    save_tag(tmp_dir, TagEntry(snapshot_file="b.json", tag="beta", env="dev"))
    args = _make_args(snapshot_dir=tmp_dir, env=None)
    rc = cmd_tag_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_cmd_tag_remove_success(tmp_dir):
    save_tag(tmp_dir, TagEntry(snapshot_file="s.json", tag="old", env="prod"))
    args = _make_args(snapshot_dir=tmp_dir, tag="old")
    rc = cmd_tag_remove(args)
    assert rc == 0
    assert get_tag(tmp_dir, "old") is None


def test_cmd_tag_remove_returns_1_when_missing(tmp_dir):
    args = _make_args(snapshot_dir=tmp_dir, tag="ghost")
    rc = cmd_tag_remove(args)
    assert rc == 1

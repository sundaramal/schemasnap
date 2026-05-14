"""Integration tests: cmd_prune wired through the full argument parser."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from schemasnap.cmd_prune import add_prune_subparsers, cmd_prune
import argparse


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schemasnap")
    sub = parser.add_subparsers(dest="command")
    add_prune_subparsers(sub)
    return parser


def _write_snapshot(directory: Path, env: str, ts: datetime) -> Path:
    stamp = ts.strftime("%Y%m%dT%H%M%S")
    fname = directory / f"{env}_{stamp}_deadbeef.json"
    fname.write_text(
        json.dumps({"environment": env, "schema": {}, "captured_at": ts.isoformat()})
    )
    return fname


@pytest.fixture()
def snap_dir(tmp_path):
    d = tmp_path / "snaps"
    d.mkdir()
    return d


def test_prune_via_parser_removes_old_by_age(snap_dir):
    now = datetime.now(tz=timezone.utc)
    old = now - timedelta(days=40)
    recent = now - timedelta(days=2)
    _write_snapshot(snap_dir, "prod", old)
    _write_snapshot(snap_dir, "prod", recent)

    parser = _make_parser()
    args = parser.parse_args(["prune", "--snapshot-dir", str(snap_dir), "--max-age-days", "30"])
    rc = args.func(args)
    assert rc == 0
    remaining = list(snap_dir.glob("prod_*.json"))
    assert len(remaining) == 1


def test_prune_keeps_all_when_within_limits(snap_dir):
    now = datetime.now(tz=timezone.utc)
    for i in range(3):
        _write_snapshot(snap_dir, "staging", now - timedelta(hours=i))

    parser = _make_parser()
    args = parser.parse_args(["prune", "--snapshot-dir", str(snap_dir), "--max-count", "10"])
    rc = args.func(args)
    assert rc == 0
    assert len(list(snap_dir.glob("*.json"))) == 3


def test_prune_env_filter_leaves_other_envs_intact(snap_dir):
    now = datetime.now(tz=timezone.utc)
    for i in range(4):
        _write_snapshot(snap_dir, "prod", now - timedelta(days=i))
    for i in range(4):
        _write_snapshot(snap_dir, "dev", now - timedelta(days=i))

    parser = _make_parser()
    args = parser.parse_args(
        ["prune", "--snapshot-dir", str(snap_dir), "--max-count", "2", "--env", "prod"]
    )
    rc = args.func(args)
    assert rc == 0
    assert len(list(snap_dir.glob("prod_*.json"))) == 2
    assert len(list(snap_dir.glob("dev_*.json"))) == 4


def test_prune_dry_run_zero_exit_no_deletion(snap_dir):
    now = datetime.now(tz=timezone.utc)
    for i in range(5):
        _write_snapshot(snap_dir, "qa", now - timedelta(days=i))

    parser = _make_parser()
    args = parser.parse_args(
        ["prune", "--snapshot-dir", str(snap_dir), "--max-count", "1", "--dry-run"]
    )
    rc = args.func(args)
    assert rc == 0
    assert len(list(snap_dir.glob("qa_*.json"))) == 5

"""Tests for schemasnap.cmd_prune."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from schemasnap.cmd_prune import add_prune_subparsers, cmd_prune


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = dict(
        snapshot_dir="snapshots",
        env=None,
        max_age_days=None,
        max_count=None,
        dry_run=False,
        audit_dir=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_snapshot(directory: Path, env: str, ts: datetime, schema: dict) -> Path:
    stamp = ts.strftime("%Y%m%dT%H%M%S")
    fname = directory / f"{env}_{stamp}_abc123.json"
    fname.write_text(json.dumps({"environment": env, "schema": schema, "captured_at": ts.isoformat()}))
    return fname


@pytest.fixture()
def snap_dir(tmp_path):
    return tmp_path / "snapshots"


# ---------------------------------------------------------------------------
# subparser registration
# ---------------------------------------------------------------------------

def test_add_prune_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_prune_subparsers(sub)
    args = parser.parse_args(["prune", "--snapshot-dir", "s", "--max-count", "5"])
    assert args.max_count == 5


# ---------------------------------------------------------------------------
# missing / invalid args
# ---------------------------------------------------------------------------

def test_cmd_prune_missing_dir_returns_1(tmp_path):
    args = _make_args(snapshot_dir=str(tmp_path / "no_such_dir"), max_count=3)
    assert cmd_prune(args) == 1


def test_cmd_prune_no_policy_returns_1(snap_dir):
    snap_dir.mkdir()
    args = _make_args(snapshot_dir=str(snap_dir))  # neither max_age_days nor max_count
    assert cmd_prune(args) == 1


# ---------------------------------------------------------------------------
# pruning by count
# ---------------------------------------------------------------------------

def test_cmd_prune_by_count_removes_excess(snap_dir):
    snap_dir.mkdir()
    now = datetime.now(tz=timezone.utc)
    for i in range(5):
        _write_snapshot(snap_dir, "prod", now - timedelta(days=i), {"t": {}})

    args = _make_args(snapshot_dir=str(snap_dir), max_count=2, env="prod")
    rc = cmd_prune(args)
    assert rc == 0
    remaining = list(snap_dir.glob("prod_*.json"))
    assert len(remaining) == 2


def test_cmd_prune_dry_run_does_not_delete(snap_dir):
    snap_dir.mkdir()
    now = datetime.now(tz=timezone.utc)
    for i in range(4):
        _write_snapshot(snap_dir, "staging", now - timedelta(days=i), {})

    args = _make_args(snapshot_dir=str(snap_dir), max_count=1, dry_run=True)
    rc = cmd_prune(args)
    assert rc == 0
    assert len(list(snap_dir.glob("*.json"))) == 4


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

def test_cmd_prune_writes_audit_entry(snap_dir, tmp_path):
    snap_dir.mkdir()
    audit_dir = tmp_path / "audit"
    now = datetime.now(tz=timezone.utc)
    for i in range(3):
        _write_snapshot(snap_dir, "dev", now - timedelta(days=i), {})

    args = _make_args(
        snapshot_dir=str(snap_dir),
        max_count=1,
        audit_dir=str(audit_dir),
    )
    rc = cmd_prune(args)
    assert rc == 0
    audit_file = audit_dir / "audit.jsonl"
    assert audit_file.exists()
    entries = [json.loads(line) for line in audit_file.read_text().splitlines()]
    assert any(e.get("action") == "prune" for e in entries)

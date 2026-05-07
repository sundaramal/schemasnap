"""Tests for schemasnap.retention and schemasnap.cmd_retention."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from schemasnap.retention import (
    RetentionPolicy,
    apply_retention,
    evaluate_retention,
)
from schemasnap.cmd_retention import cmd_retention_apply, cmd_retention_check


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_snap(directory: Path, name: str, age_days: float = 0) -> str:
    """Write a minimal snapshot JSON and optionally backdate its mtime."""
    p = directory / name
    p.write_text(json.dumps({"schema": {}, "env": "test"}))
    if age_days:
        past = time.time() - age_days * 86400
        os.utime(p, (past, past))
    return str(p)


# ---------------------------------------------------------------------------
# evaluate_retention
# ---------------------------------------------------------------------------

def test_evaluate_returns_empty_for_empty_dir(snap_dir: Path) -> None:
    policy = RetentionPolicy(max_age_days=7)
    assert evaluate_retention(str(snap_dir), policy) == []


def test_evaluate_age_limit_removes_old(snap_dir: Path) -> None:
    old = _write_snap(snap_dir, "prod_old.json", age_days=30)
    _write_snap(snap_dir, "prod_new.json", age_days=1)
    policy = RetentionPolicy(max_age_days=7)
    victims = evaluate_retention(str(snap_dir), policy)
    assert old in victims
    assert len(victims) == 1


def test_evaluate_count_limit_removes_excess(snap_dir: Path) -> None:
    for i in range(5):
        _write_snap(snap_dir, f"prod_snap{i}.json", age_days=5 - i)
    policy = RetentionPolicy(max_count=3)
    victims = evaluate_retention(str(snap_dir), policy)
    assert len(victims) == 2


def test_evaluate_env_filter_limits_scope(snap_dir: Path) -> None:
    _write_snap(snap_dir, "prod_a.json", age_days=30)
    _write_snap(snap_dir, "staging_b.json", age_days=30)
    policy = RetentionPolicy(max_age_days=7, env_filter=["prod"])
    victims = evaluate_retention(str(snap_dir), policy)
    assert all("prod" in v for v in victims)
    assert len(victims) == 1


def test_evaluate_no_limits_returns_empty(snap_dir: Path) -> None:
    _write_snap(snap_dir, "prod_snap.json", age_days=365)
    policy = RetentionPolicy()
    assert evaluate_retention(str(snap_dir), policy) == []


# ---------------------------------------------------------------------------
# apply_retention
# ---------------------------------------------------------------------------

def test_apply_dry_run_does_not_delete(snap_dir: Path) -> None:
    old = _write_snap(snap_dir, "prod_old.json", age_days=30)
    policy = RetentionPolicy(max_age_days=7)
    deleted = apply_retention(str(snap_dir), policy, dry_run=True)
    assert old in deleted
    assert Path(old).exists()  # file still present


def test_apply_deletes_files(snap_dir: Path) -> None:
    old = _write_snap(snap_dir, "prod_old.json", age_days=30)
    policy = RetentionPolicy(max_age_days=7)
    deleted = apply_retention(str(snap_dir), policy, dry_run=False)
    assert old in deleted
    assert not Path(old).exists()


# ---------------------------------------------------------------------------
# cmd_retention_check
# ---------------------------------------------------------------------------

def _args(**kwargs):
    defaults = dict(
        snapshot_dir="snapshots",
        max_age_days=None,
        max_count=None,
        env=[],
        output_json=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_cmd_check_returns_zero(snap_dir: Path) -> None:
    args = _args(snapshot_dir=str(snap_dir), max_age_days=7)
    assert cmd_retention_check(args) == 0


def test_cmd_check_json_output(snap_dir: Path, capsys) -> None:
    _write_snap(snap_dir, "prod_old.json", age_days=30)
    args = _args(snapshot_dir=str(snap_dir), max_age_days=7, output_json=True)
    cmd_retention_check(args)
    out = json.loads(capsys.readouterr().out)
    assert "would_delete" in out
    assert len(out["would_delete"]) == 1


def test_cmd_apply_requires_yes(snap_dir: Path, capsys) -> None:
    _write_snap(snap_dir, "prod_old.json", age_days=30)
    args = _args(snapshot_dir=str(snap_dir), max_age_days=7, yes=False)
    rc = cmd_retention_apply(args)
    assert rc == 1


def test_cmd_apply_with_yes_deletes(snap_dir: Path) -> None:
    old = _write_snap(snap_dir, "prod_old.json", age_days=30)
    args = _args(snapshot_dir=str(snap_dir), max_age_days=7, yes=True)
    rc = cmd_retention_apply(args)
    assert rc == 0
    assert not Path(old).exists()

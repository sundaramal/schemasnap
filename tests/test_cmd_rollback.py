"""Tests for schemasnap.cmd_rollback."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from schemasnap.cmd_rollback import add_rollback_subparsers, cmd_rollback
from schemasnap.rollback import RollbackResult


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "env": "prod",
        "snap_dir": "snapshots",
        "schema_hash": None,
        "tag_name": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_rollback_success_returns_zero(capsys):
    ok = RollbackResult(
        success=True,
        source_file="snapshots/prod_old.json",
        dest_file="snapshots/prod_new.json",
        message="Rolled back env='prod' to ref='abc123'",
    )
    with patch("schemasnap.cmd_rollback.rollback_to", return_value=ok):
        rc = cmd_rollback(_make_args(schema_hash="abc123"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Rolled back" in out
    assert "prod_new.json" in out


def test_cmd_rollback_failure_returns_one(capsys):
    fail = RollbackResult(
        success=False,
        source_file="",
        dest_file="",
        message="No snapshot found for env='prod' ref='bad'",
    )
    with patch("schemasnap.cmd_rollback.rollback_to", return_value=fail):
        rc = cmd_rollback(_make_args(schema_hash="bad"))
    assert rc == 1
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_add_rollback_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    add_rollback_subparsers(subs)
    args = parser.parse_args(["rollback", "prod", "--hash", "abc"])
    assert args.env == "prod"
    assert args.schema_hash == "abc"
    assert args.tag_name is None


def test_add_rollback_subparsers_tag_variant():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    add_rollback_subparsers(subs)
    args = parser.parse_args(["rollback", "staging", "--tag", "v2"])
    assert args.tag_name == "v2"
    assert args.schema_hash is None


def test_cmd_rollback_passes_snap_dir(tmp_path):
    ok = RollbackResult(success=True, source_file="a", dest_file="b", message="ok")
    with patch("schemasnap.cmd_rollback.rollback_to", return_value=ok) as mock_rb:
        cmd_rollback(_make_args(snap_dir=str(tmp_path), tag_name="v1"))
    call_kwargs = mock_rb.call_args
    assert call_kwargs[0][0] == Path(str(tmp_path))

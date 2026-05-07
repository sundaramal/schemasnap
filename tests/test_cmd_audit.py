"""Tests for schemasnap.cmd_audit CLI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.audit import AuditEntry, append_audit
from schemasnap.cmd_audit import cmd_audit, add_audit_subparsers


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_args(tmp_dir: Path, event=None, env=None, as_json=False) -> argparse.Namespace:
    return argparse.Namespace(
        audit_cmd="list",
        dir=str(tmp_dir),
        event=event,
        env=env,
        as_json=as_json,
    )


def test_cmd_audit_list_empty(tmp_dir, capsys):
    args = _make_args(tmp_dir)
    rc = cmd_audit(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No audit entries found" in out


def test_cmd_audit_list_shows_entries(tmp_dir, capsys):
    append_audit(str(tmp_dir), AuditEntry.now("capture", "prod", {"hash": "deadbeef"}))
    args = _make_args(tmp_dir)
    rc = cmd_audit(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "capture" in out
    assert "prod" in out


def test_cmd_audit_list_json_output(tmp_dir, capsys):
    append_audit(str(tmp_dir), AuditEntry.now("compare", "staging", {"changes": 2}))
    args = _make_args(tmp_dir, as_json=True)
    rc = cmd_audit(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["event"] == "compare"


def test_cmd_audit_list_filter_event(tmp_dir, capsys):
    append_audit(str(tmp_dir), AuditEntry.now("capture", "prod", {}))
    append_audit(str(tmp_dir), AuditEntry.now("compare", "prod", {}))
    args = _make_args(tmp_dir, event="capture")
    rc = cmd_audit(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "capture" in out
    assert "compare" not in out


def test_cmd_audit_unknown_subcommand_returns_1(tmp_dir):
    args = argparse.Namespace(audit_cmd="nonexistent", dir=str(tmp_dir))
    rc = cmd_audit(args)
    assert rc == 1


def test_add_audit_subparsers_registers_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    add_audit_subparsers(sub)
    parsed = parser.parse_args(["audit", "list", "--dir", "snapshots"])
    assert parsed.cmd == "audit"

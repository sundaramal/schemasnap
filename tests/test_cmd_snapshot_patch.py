"""Tests for schemasnap.cmd_snapshot_patch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from schemasnap.cmd_snapshot_patch import add_snapshot_patch_subparsers, cmd_snapshot_patch


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(path: Path, schema: dict, env: str = "test") -> None:
    data = {"environment": env, "schema": schema}
    path.write_text(json.dumps(data))


def _make_args(tmp_path: Path, **kwargs):
    base = tmp_path / "base.json"
    frm = tmp_path / "from.json"
    to = tmp_path / "to.json"
    ns = argparse.Namespace(
        base=str(base),
        from_snap=str(frm),
        to_snap=str(to),
        output=None,
        allow_missing=False,
    )
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns, base, frm, to


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_add_snapshot_patch_subparsers_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_snapshot_patch_subparsers(sub)
    args = parser.parse_args(["snapshot-patch", "b", "f", "t"])
    assert args.base == "b"


def test_cmd_snapshot_patch_missing_base_returns_1(tmp_path):
    ns, base, frm, to = _make_args(tmp_path)
    _write_snapshot(frm, {"users": {"id": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}})
    # base not written
    assert cmd_snapshot_patch(ns) == 1


def test_cmd_snapshot_patch_missing_from_returns_1(tmp_path):
    ns, base, frm, to = _make_args(tmp_path)
    _write_snapshot(base, {"users": {"id": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}})
    assert cmd_snapshot_patch(ns) == 1


def test_cmd_snapshot_patch_success_prints_json(tmp_path, capsys):
    ns, base, frm, to = _make_args(tmp_path)
    _write_snapshot(base, {"users": {"id": "int"}})
    _write_snapshot(frm, {"users": {"id": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}, "orders": {"order_id": "int"}})
    rc = cmd_snapshot_patch(ns)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "orders" in data["schema"]


def test_cmd_snapshot_patch_writes_output_file(tmp_path):
    out_file = tmp_path / "patched.json"
    ns, base, frm, to = _make_args(tmp_path, output=str(out_file))
    _write_snapshot(base, {"users": {"id": "int"}})
    _write_snapshot(frm, {"users": {"id": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}, "orders": {"order_id": "int"}})
    rc = cmd_snapshot_patch(ns)
    assert rc == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "orders" in data["schema"]


def test_cmd_snapshot_patch_conflict_returns_1(tmp_path):
    ns, base, frm, to = _make_args(tmp_path)
    # base does NOT have 'ghost', but diff says remove it
    _write_snapshot(base, {"users": {"id": "int"}})
    _write_snapshot(frm, {"users": {"id": "int"}, "ghost": {"x": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}})
    rc = cmd_snapshot_patch(ns)
    assert rc == 1


def test_cmd_snapshot_patch_allow_missing_succeeds(tmp_path):
    ns, base, frm, to = _make_args(tmp_path, allow_missing=True)
    _write_snapshot(base, {"users": {"id": "int"}})
    _write_snapshot(frm, {"users": {"id": "int"}, "ghost": {"x": "int"}})
    _write_snapshot(to, {"users": {"id": "int"}})
    rc = cmd_snapshot_patch(ns)
    assert rc == 0

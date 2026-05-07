"""Tests for schemasnap.cmd_plugin CLI sub-commands."""

from __future__ import annotations

import argparse
import json

import pytest

from schemasnap.cmd_plugin import add_plugin_subparsers, cmd_plugin_list, cmd_plugin_load
from schemasnap.plugin import PluginRegistry, get_registry


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"load": None, "modules": []}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_plugin_list_returns_zero(capsys) -> None:
    args = _make_args()
    rc = cmd_plugin_list(args)
    assert rc == 0


def test_cmd_plugin_list_output_is_valid_json(capsys) -> None:
    args = _make_args()
    cmd_plugin_list(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "capture_backends" in data
    assert "alert_handlers" in data


def test_cmd_plugin_list_loads_extra_modules(capsys) -> None:
    args = _make_args(load=["json"])
    rc = cmd_plugin_list(args)
    assert rc == 0


def test_cmd_plugin_load_valid_module(capsys) -> None:
    args = _make_args(modules=["json", "csv"])
    rc = cmd_plugin_load(args)
    assert rc == 0


def test_cmd_plugin_load_invalid_module_returns_1(capsys) -> None:
    args = _make_args(modules=["schemasnap._no_such_module_abc"])
    rc = cmd_plugin_load(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_add_plugin_subparsers_registers_commands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    add_plugin_subparsers(sub)
    # parse 'plugin list' — should not raise
    ns = parser.parse_args(["plugin", "list"])
    assert ns.plugin_cmd == "list"


def test_add_plugin_subparsers_load_command() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    add_plugin_subparsers(sub)
    ns = parser.parse_args(["plugin", "load", "json"])
    assert ns.plugin_cmd == "load"
    assert "json" in ns.modules

"""Tests for schemasnap.plugin registry."""

from __future__ import annotations

import pytest

from schemasnap.plugin import PluginRegistry, load_plugin, load_plugins_from_list


@pytest.fixture()
def registry() -> PluginRegistry:
    return PluginRegistry()


def _dummy_capture(env: str, output_dir: str) -> dict:
    return {}


def _dummy_alert(result) -> None:  # noqa: ANN001
    pass


def test_register_capture_adds_backend(registry: PluginRegistry) -> None:
    registry.register_capture("sqlite", _dummy_capture)
    assert "sqlite" in registry.capture_backends


def test_register_capture_duplicate_raises(registry: PluginRegistry) -> None:
    registry.register_capture("sqlite", _dummy_capture)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_capture("sqlite", _dummy_capture)


def test_get_capture_returns_callable(registry: PluginRegistry) -> None:
    registry.register_capture("pg", _dummy_capture)
    fn = registry.get_capture("pg")
    assert fn is _dummy_capture


def test_get_capture_missing_raises(registry: PluginRegistry) -> None:
    with pytest.raises(KeyError, match="No capture backend"):
        registry.get_capture("nonexistent")


def test_register_alert_appends(registry: PluginRegistry) -> None:
    registry.register_alert(_dummy_alert)
    assert _dummy_alert in registry.alert_handlers


def test_register_multiple_alerts(registry: PluginRegistry) -> None:
    def h1(): pass
    def h2(): pass
    registry.register_alert(h1)
    registry.register_alert(h2)
    assert len(registry.alert_handlers) == 2


def test_load_plugin_imports_module() -> None:
    # json is always available; just confirm no ImportError is raised
    load_plugin("json")


def test_load_plugin_bad_path_raises() -> None:
    with pytest.raises(ImportError):
        load_plugin("schemasnap._does_not_exist_xyz")


def test_load_plugins_from_list_none_is_noop() -> None:
    # Should not raise
    load_plugins_from_list(None)


def test_load_plugins_from_list_loads_all() -> None:
    load_plugins_from_list(["json", "csv"])

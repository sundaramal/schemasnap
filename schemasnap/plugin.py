"""Plugin registry for schemasnap — allows third-party capture and alert plugins."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class PluginRegistry:
    """Holds registered capture backends and alert handlers."""

    capture_backends: Dict[str, Callable] = field(default_factory=dict)
    alert_handlers: List[Callable] = field(default_factory=list)

    def register_capture(self, name: str, fn: Callable) -> None:
        """Register a named capture backend."""
        if name in self.capture_backends:
            raise ValueError(f"Capture backend '{name}' is already registered.")
        self.capture_backends[name] = fn

    def register_alert(self, fn: Callable) -> None:
        """Register an alert handler callable."""
        self.alert_handlers.append(fn)

    def get_capture(self, name: str) -> Callable:
        """Return a capture backend by name, raising KeyError if absent."""
        if name not in self.capture_backends:
            raise KeyError(
                f"No capture backend named '{name}'. "
                f"Available: {list(self.capture_backends)}"
            )
        return self.capture_backends[name]


# Module-level default registry
_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Return the global plugin registry."""
    return _registry


def load_plugin(dotted_path: str) -> None:
    """Import a module by dotted path to trigger its plugin registrations.

    Example entry-point style usage::

        load_plugin("mypackage.schemasnap_plugin")
    """
    importlib.import_module(dotted_path)


def load_plugins_from_list(paths: Optional[List[str]]) -> None:
    """Load multiple plugins from a list of dotted import paths."""
    for path in paths or []:
        load_plugin(path)

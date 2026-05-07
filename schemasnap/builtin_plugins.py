"""Built-in capture backends shipped with schemasnap.

Registers the following named backends into the global plugin registry:

* ``dict``  — accepts a raw schema dict (useful for testing / piping JSON).
* ``json_file`` — reads a schema from a JSON file on disk.

This module is imported automatically by :mod:`schemasnap.cli` so the
built-in backends are always available without manual ``--load`` flags.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from schemasnap.plugin import get_registry
from schemasnap.snapshot import capture_snapshot


def _capture_from_dict(
    schema: Dict[str, Any],
    env: str,
    output_dir: str,
) -> str:
    """Capture a snapshot from an already-loaded schema dict.

    Returns the path of the written snapshot file.
    """
    return capture_snapshot(schema, env, output_dir)


def _capture_from_json_file(
    schema_file: str,
    env: str,
    output_dir: str,
) -> str:
    """Load a schema from *schema_file* (JSON) and capture a snapshot.

    Returns the path of the written snapshot file.
    """
    path = Path(schema_file)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    return capture_snapshot(schema, env, output_dir)


def register_builtin_plugins() -> None:
    """Register all built-in backends. Safe to call multiple times (idempotent)."""
    registry = get_registry()
    if "dict" not in registry.capture_backends:
        registry.register_capture("dict", _capture_from_dict)
    if "json_file" not in registry.capture_backends:
        registry.register_capture("json_file", _capture_from_json_file)


# Auto-register when this module is imported
register_builtin_plugins()

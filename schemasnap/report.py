"""Reporting utilities: render and optionally write diff reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemasnap.diff import SchemaDiff


def diff_to_dict(diff: SchemaDiff) -> dict[str, Any]:
    """Serialize a SchemaDiff to a plain dictionary."""
    return {
        "env": diff.env,
        "old_hash": diff.old_hash,
        "new_hash": diff.new_hash,
        "has_changes": diff.has_changes,
        "added_tables": diff.added_tables,
        "removed_tables": diff.removed_tables,
        "modified_tables": diff.modified_tables,
    }


def render_text_report(diff: SchemaDiff) -> str:
    """Return a human-readable text report for a diff."""
    return diff.summary()


def render_json_report(diff: SchemaDiff, indent: int = 2) -> str:
    """Return a JSON-formatted report for a diff."""
    return json.dumps(diff_to_dict(diff), indent=indent)


def write_report(
    diff: SchemaDiff,
    output_dir: str | Path,
    fmt: str = "text",
) -> Path:
    """Write a diff report to *output_dir* and return the file path.

    Args:
        diff: The SchemaDiff to report on.
        output_dir: Directory where the report file will be written.
        fmt: Either ``"text"`` or ``"json"``.

    Returns:
        Path to the written report file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    old_short = diff.old_hash[:8] if diff.old_hash else "none"
    new_short = diff.new_hash[:8] if diff.new_hash else "none"
    extension = "json" if fmt == "json" else "txt"
    filename = f"diff_{diff.env}_{old_short}_{new_short}.{extension}"
    report_path = output_dir / filename

    if fmt == "json":
        content = render_json_report(diff)
    else:
        content = render_text_report(diff)

    report_path.write_text(content, encoding="utf-8")
    return report_path

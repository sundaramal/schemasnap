"""Export snapshots to various formats (CSV, HTML, Markdown)."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from schemasnap.snapshot import load_snapshot
from schemasnap.diff import diff_snapshots, has_changes


def snapshot_to_rows(schema: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten a schema dict into a list of rows suitable for tabular export."""
    rows = []
    for table, columns in sorted(schema.items()):
        for col_name, col_def in sorted(columns.items()):
            rows.append({"table": table, "column": col_name, "definition": col_def})
    return rows


def render_csv(schema: dict[str, Any]) -> str:
    """Render a schema snapshot as CSV text."""
    rows = snapshot_to_rows(schema)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["table", "column", "definition"])
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def render_markdown(schema: dict[str, Any], title: str = "Schema Snapshot") -> str:
    """Render a schema snapshot as a Markdown document."""
    lines = [f"# {title}\n"]
    for table, columns in sorted(schema.items()):
        lines.append(f"## {table}\n")
        lines.append("| Column | Definition |")
        lines.append("|--------|------------|")
        for col_name, col_def in sorted(columns.items()):
            lines.append(f"| `{col_name}` | {col_def} |")
        lines.append("")
    return "\n".join(lines)


def render_html(schema: dict[str, Any], title: str = "Schema Snapshot") -> str:
    """Render a schema snapshot as a minimal HTML document."""
    parts = [f"<!DOCTYPE html><html><head><title>{title}</title></head><body>"]
    parts.append(f"<h1>{title}</h1>")
    for table, columns in sorted(schema.items()):
        parts.append(f"<h2>{table}</h2>")
        parts.append("<table border='1'><tr><th>Column</th><th>Definition</th></tr>")
        for col_name, col_def in sorted(columns.items()):
            parts.append(f"<tr><td><code>{col_name}</code></td><td>{col_def}</td></tr>")
        parts.append("</table>")
    parts.append("</body></html>")
    return "\n".join(parts)


def export_snapshot(
    snapshot_file: str | Path,
    fmt: str,
    output: str | Path | None = None,
) -> str:
    """Load a snapshot file and export it in the requested format.

    Args:
        snapshot_file: Path to the JSON snapshot file.
        fmt: One of 'csv', 'markdown', 'html'.
        output: Optional file path to write to; if None, returns the string.

    Returns:
        The rendered content as a string.
    """
    data = load_snapshot(Path(snapshot_file))
    schema = data.get("schema", {})
    env = data.get("env", str(snapshot_file))

    renderers = {"csv": render_csv, "markdown": render_markdown, "html": render_html}
    if fmt not in renderers:
        raise ValueError(f"Unsupported format '{fmt}'. Choose from: {', '.join(renderers)}.")

    if fmt == "csv":
        content = render_csv(schema)
    else:
        content = renderers[fmt](schema, title=f"Schema Snapshot — {env}")

    if output is not None:
        Path(output).write_text(content, encoding="utf-8")
    return content

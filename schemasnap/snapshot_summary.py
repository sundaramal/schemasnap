"""Snapshot summary: produce a concise human/machine-readable overview of a single snapshot."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from schemasnap.snapshot import load_snapshot


@dataclass
class SnapshotSummary:
    environment: str
    snapshot_hash: str
    table_count: int
    column_count: int
    tables: List[str] = field(default_factory=list)
    column_counts_by_table: Dict[str, int] = field(default_factory=dict)


def compute_summary(snapshot_path: Path) -> SnapshotSummary:
    """Load a snapshot file and compute its summary statistics."""
    data = load_snapshot(snapshot_path)
    schema: dict = data.get("schema", {})
    environment: str = data.get("environment", "unknown")
    snapshot_hash: str = data.get("hash", "")

    column_counts: Dict[str, int] = {
        table: len(columns) for table, columns in schema.items()
    }
    total_columns = sum(column_counts.values())

    return SnapshotSummary(
        environment=environment,
        snapshot_hash=snapshot_hash,
        table_count=len(schema),
        column_count=total_columns,
        tables=sorted(schema.keys()),
        column_counts_by_table=column_counts,
    )


def render_summary_text(summary: SnapshotSummary) -> str:
    lines = [
        f"Environment : {summary.environment}",
        f"Hash        : {summary.snapshot_hash}",
        f"Tables      : {summary.table_count}",
        f"Columns     : {summary.column_count}",
        "",
        "Table breakdown:",
    ]
    for table in summary.tables:
        count = summary.column_counts_by_table[table]
        lines.append(f"  {table:<40} {count} column(s)")
    return "\n".join(lines)


def render_summary_json(summary: SnapshotSummary) -> str:
    return json.dumps(
        {
            "environment": summary.environment,
            "hash": summary.snapshot_hash,
            "table_count": summary.table_count,
            "column_count": summary.column_count,
            "tables": summary.tables,
            "column_counts_by_table": summary.column_counts_by_table,
        },
        indent=2,
    )

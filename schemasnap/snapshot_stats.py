"""Aggregate statistics computed across a collection of snapshots."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def collect_snapshot_stats(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a dict of aggregate stats for *snapshots*.

    Each snapshot is expected to have the shape produced by
    ``schemasnap.snapshot.load_snapshot``:
    ``{"environment": str, "hash": str, "schema": {table: {col: type}}}``.
    """
    if not snapshots:
        return {
            "snapshot_count": 0,
            "environments": [],
            "total_tables": 0,
            "total_columns": 0,
            "avg_tables_per_snapshot": 0.0,
            "avg_columns_per_table": 0.0,
            "most_common_tables": [],
        }

    env_set: set[str] = set()
    table_counter: Counter = Counter()
    total_tables = 0
    total_columns = 0

    for snap in snapshots:
        env_set.add(snap.get("environment", "unknown"))
        schema: Dict[str, Any] = snap.get("schema", {})
        total_tables += len(schema)
        for cols in schema.values():
            total_columns += len(cols) if isinstance(cols, dict) else 0
        for table in schema:
            table_counter[table] += 1

    n = len(snapshots)
    avg_cols = total_columns / total_tables if total_tables else 0.0

    return {
        "snapshot_count": n,
        "environments": sorted(env_set),
        "total_tables": total_tables,
        "total_columns": total_columns,
        "avg_tables_per_snapshot": round(total_tables / n, 2),
        "avg_columns_per_table": round(avg_cols, 2),
        "most_common_tables": [
            {"table": t, "appearances": c}
            for t, c in table_counter.most_common(10)
        ],
    }


def render_stats_text(stats: Dict[str, Any]) -> str:
    """Render *stats* as a human-readable text block."""
    lines = [
        f"Snapshots      : {stats['snapshot_count']}",
        f"Environments   : {', '.join(stats['environments']) or '—'}",
        f"Total tables   : {stats['total_tables']}",
        f"Total columns  : {stats['total_columns']}",
        f"Avg tables/snap: {stats['avg_tables_per_snapshot']}",
        f"Avg cols/table : {stats['avg_columns_per_table']}",
        "",
        "Most common tables:",
    ]
    for entry in stats["most_common_tables"]:
        lines.append(f"  {entry['table']:<40} {entry['appearances']} snapshot(s)")
    if not stats["most_common_tables"]:
        lines.append("  (none)")
    return "\n".join(lines)

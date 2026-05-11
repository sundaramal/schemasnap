"""Collect and expose snapshot/diff metrics for monitoring integrations."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from schemasnap.snapshot import list_snapshots, load_snapshot
from schemasnap.diff import diff_snapshots, has_changes


@dataclass
class SnapshotMetrics:
    env: str
    total_snapshots: int
    total_tables: int
    total_columns: int
    latest_hash: Optional[str] = None
    drift_detected: bool = False
    added_tables: int = 0
    removed_tables: int = 0
    modified_tables: int = 0
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "env": self.env,
            "total_snapshots": self.total_snapshots,
            "total_tables": self.total_tables,
            "total_columns": self.total_columns,
            "latest_hash": self.latest_hash,
            "drift_detected": self.drift_detected,
            "added_tables": self.added_tables,
            "removed_tables": self.removed_tables,
            "modified_tables": self.modified_tables,
            **self.extra,
        }


def _count_columns(schema: dict) -> int:
    return sum(len(cols) for cols in schema.values())


def collect_metrics(snapshot_dir: Path, env: str) -> SnapshotMetrics:
    """Compute metrics for the given environment's snapshots."""
    snaps = list_snapshots(snapshot_dir, env=env)
    total_snapshots = len(snaps)

    if total_snapshots == 0:
        return SnapshotMetrics(env=env, total_snapshots=0, total_tables=0, total_columns=0)

    latest = load_snapshot(snaps[-1])
    schema = latest.get("schema", {})
    total_tables = len(schema)
    total_columns = _count_columns(schema)
    latest_hash = latest.get("hash")

    metrics = SnapshotMetrics(
        env=env,
        total_snapshots=total_snapshots,
        total_tables=total_tables,
        total_columns=total_columns,
        latest_hash=latest_hash,
    )

    if total_snapshots >= 2:
        prev = load_snapshot(snaps[-2])
        diff = diff_snapshots(prev, latest)
        metrics.drift_detected = has_changes(diff)
        metrics.added_tables = len(diff.added)
        metrics.removed_tables = len(diff.removed)
        metrics.modified_tables = len(diff.modified)

    return metrics


def render_metrics_json(metrics: SnapshotMetrics) -> str:
    return json.dumps(metrics.to_dict(), indent=2)


def render_metrics_text(metrics: SnapshotMetrics) -> str:
    lines: List[str] = [
        f"Environment : {metrics.env}",
        f"Snapshots   : {metrics.total_snapshots}",
        f"Tables      : {metrics.total_tables}",
        f"Columns     : {metrics.total_columns}",
        f"Latest hash : {metrics.latest_hash or 'n/a'}",
        f"Drift       : {'YES' if metrics.drift_detected else 'no'}",
    ]
    if metrics.drift_detected:
        lines += [
            f"  Added     : {metrics.added_tables}",
            f"  Removed   : {metrics.removed_tables}",
            f"  Modified  : {metrics.modified_tables}",
        ]
    return "\n".join(lines)

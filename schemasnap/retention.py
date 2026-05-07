"""Retention policy evaluation for snapshots."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from schemasnap.snapshot import list_snapshots, load_snapshot


@dataclass
class RetentionPolicy:
    """Defines how long and how many snapshots to keep per environment."""
    max_age_days: Optional[int] = None       # None means no age limit
    max_count: Optional[int] = None          # None means no count limit
    env_filter: List[str] = field(default_factory=list)  # empty = all envs


def _snapshot_timestamp(path: str) -> Optional[datetime]:
    """Extract UTC timestamp from snapshot metadata, fallback to mtime."""
    try:
        snap = load_snapshot(path)
        ts = snap.get("captured_at")
        if ts:
            return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    except Exception:
        pass
    mtime = os.path.getmtime(path)
    return datetime.fromtimestamp(mtime, tz=timezone.utc)


def evaluate_retention(
    snapshot_dir: str,
    policy: RetentionPolicy,
) -> List[str]:
    """Return list of snapshot file paths that violate the retention policy.

    Files are sorted oldest-first; count limit removes the oldest excess files.
    """
    all_files = list_snapshots(snapshot_dir)
    if not all_files:
        return []

    # Filter by environment if requested
    if policy.env_filter:
        def _env_of(p: str) -> str:
            return Path(p).stem.split("_")[0]
        all_files = [f for f in all_files if _env_of(f) in policy.env_filter]

    # Sort oldest first
    all_files.sort(key=lambda p: _snapshot_timestamp(p) or datetime.min.replace(tzinfo=timezone.utc))

    to_delete: set[str] = set()
    now = datetime.now(tz=timezone.utc)

    if policy.max_age_days is not None:
        cutoff = now - timedelta(days=policy.max_age_days)
        for f in all_files:
            ts = _snapshot_timestamp(f)
            if ts and ts < cutoff:
                to_delete.add(f)

    if policy.max_count is not None:
        remaining = [f for f in all_files if f not in to_delete]
        excess = len(remaining) - policy.max_count
        if excess > 0:
            for f in remaining[:excess]:
                to_delete.add(f)

    return [f for f in all_files if f in to_delete]


def apply_retention(
    snapshot_dir: str,
    policy: RetentionPolicy,
    dry_run: bool = False,
) -> List[str]:
    """Delete snapshots that violate *policy*. Returns list of deleted paths."""
    victims = evaluate_retention(snapshot_dir, policy)
    if not dry_run:
        for path in victims:
            try:
                os.remove(path)
            except OSError:
                pass
    return victims

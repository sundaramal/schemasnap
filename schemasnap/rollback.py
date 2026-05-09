"""Rollback support: restore a snapshot to a previous version by hash or tag."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .snapshot import load_snapshot, list_snapshots
from .tag import load_tags


@dataclass
class RollbackResult:
    success: bool
    source_file: str
    dest_file: str
    message: str


def _find_snapshot_by_hash(snap_dir: Path, env: str, schema_hash: str) -> Optional[Path]:
    """Return the first snapshot file whose name contains the given hash."""
    for p in list_snapshots(snap_dir, env):
        if schema_hash in p.name:
            return p
    return None


def _find_snapshot_by_tag(snap_dir: Path, env: str, tag_name: str) -> Optional[Path]:
    """Return the snapshot file referenced by a tag for the given env."""
    tags = load_tags(snap_dir)
    key = f"{env}:{tag_name}"
    entry = tags.get(key)
    if entry is None:
        return None
    candidate = snap_dir / entry.snapshot_file
    return candidate if candidate.exists() else None


def rollback_to(
    snap_dir: Path,
    env: str,
    *,
    schema_hash: Optional[str] = None,
    tag_name: Optional[str] = None,
    dest_name: Optional[str] = None,
) -> RollbackResult:
    """Copy a historical snapshot as the new 'current' snapshot for an env.

    Exactly one of schema_hash or tag_name must be provided.
    Returns a RollbackResult describing the outcome.
    """
    if (schema_hash is None) == (tag_name is None):
        raise ValueError("Provide exactly one of schema_hash or tag_name.")

    if schema_hash:
        source = _find_snapshot_by_hash(snap_dir, env, schema_hash)
        ref = schema_hash
    else:
        source = _find_snapshot_by_tag(snap_dir, env, tag_name)  # type: ignore[arg-type]
        ref = tag_name

    if source is None:
        return RollbackResult(
            success=False,
            source_file="",
            dest_file="",
            message=f"No snapshot found for env='{env}' ref='{ref}'",
        )

    schema = load_snapshot(source)
    from .snapshot import capture_snapshot  # local import to avoid circular

    dest = capture_snapshot(schema, env, snap_dir)
    return RollbackResult(
        success=True,
        source_file=str(source),
        dest_file=str(dest),
        message=f"Rolled back env='{env}' to ref='{ref}'",
    )

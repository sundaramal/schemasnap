"""Clone a snapshot from one environment label to another.

Useful for seeding a new environment baseline from an existing snapshot
without re-capturing the live database.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .snapshot import load_snapshot, latest_snapshot


@dataclass
class CloneResult:
    success: bool
    source_file: Optional[Path] = None
    dest_file: Optional[Path] = None
    message: str = ""


def _rewrite_env(snapshot_data: dict, new_env: str) -> dict:
    """Return a copy of *snapshot_data* with the environment field replaced."""
    updated = dict(snapshot_data)
    updated["environment"] = new_env
    return updated


def clone_snapshot(
    snapshot_dir: Path,
    source_env: str,
    dest_env: str,
    source_file: Optional[Path] = None,
) -> CloneResult:
    """Clone the latest (or specified) snapshot of *source_env* to *dest_env*.

    The cloned file is written into *snapshot_dir* with the destination
    environment name embedded in the filename so it is discoverable by the
    normal snapshot utilities.
    """
    snapshot_dir = Path(snapshot_dir)

    if source_file is None:
        source_file = latest_snapshot(snapshot_dir, source_env)
        if source_file is None:
            return CloneResult(
                success=False,
                message=f"No snapshot found for environment '{source_env}' in {snapshot_dir}",
            )
    else:
        source_file = Path(source_file)
        if not source_file.exists():
            return CloneResult(
                success=False,
                message=f"Source file not found: {source_file}",
            )

    data = load_snapshot(source_file)
    updated = _rewrite_env(data, dest_env)

    # Build destination filename: swap the env portion of the original name.
    original_stem = source_file.stem  # e.g. snapshot_prod_abc123
    new_stem = original_stem.replace(source_env, dest_env, 1)
    dest_file = snapshot_dir / f"{new_stem}{source_file.suffix}"

    dest_file.write_text(json.dumps(updated, indent=2))

    return CloneResult(
        success=True,
        source_file=source_file,
        dest_file=dest_file,
        message=f"Cloned '{source_env}' → '{dest_env}': {dest_file.name}",
    )

"""Baseline management: mark a snapshot as the accepted baseline for an environment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASELINE_FILENAME = ".baseline.json"


@dataclass
class BaselineEntry:
    env: str
    snapshot_file: str
    hash: str
    set_at: str  # ISO-8601 timestamp


def _baseline_path(snapshot_dir: str) -> Path:
    return Path(snapshot_dir) / BASELINE_FILENAME


def load_baselines(snapshot_dir: str) -> dict[str, BaselineEntry]:
    """Return mapping of env -> BaselineEntry for all recorded baselines."""
    path = _baseline_path(snapshot_dir)
    if not path.exists():
        return {}
    with path.open() as fh:
        raw = json.load(fh)
    return {
        env: BaselineEntry(**data)
        for env, data in raw.items()
    }


def save_baseline(snapshot_dir: str, entry: BaselineEntry) -> None:
    """Persist a baseline entry for the given environment."""
    baselines = load_baselines(snapshot_dir)
    baselines[entry.env] = entry
    path = _baseline_path(snapshot_dir)
    with path.open("w") as fh:
        json.dump(
            {env: vars(e) for env, e in baselines.items()},
            fh,
            indent=2,
        )


def get_baseline(snapshot_dir: str, env: str) -> Optional[BaselineEntry]:
    """Return the baseline entry for *env*, or None if none is set."""
    return load_baselines(snapshot_dir).get(env)


def set_baseline_from_snapshot(snapshot_dir: str, env: str, snapshot_file: str) -> BaselineEntry:
    """Read hash from an existing snapshot file and record it as the baseline."""
    import datetime
    from schemasnap.snapshot import load_snapshot

    data = load_snapshot(snapshot_file)
    schema_hash = data.get("hash", "")
    entry = BaselineEntry(
        env=env,
        snapshot_file=os.path.basename(snapshot_file),
        hash=schema_hash,
        set_at=datetime.datetime.utcnow().isoformat() + "Z",
    )
    save_baseline(snapshot_dir, entry)
    return entry


def compare_to_baseline(snapshot_dir: str, env: str, current_snapshot_file: str) -> bool:
    """Return True if the current snapshot matches the baseline hash (no drift)."""
    from schemasnap.snapshot import load_snapshot

    baseline = get_baseline(snapshot_dir, env)
    if baseline is None:
        raise ValueError(f"No baseline set for environment '{env}'")
    current = load_snapshot(current_snapshot_file)
    return current.get("hash", "") == baseline.hash

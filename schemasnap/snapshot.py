"""Snapshot capture, persistence, and retrieval utilities."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def compute_schema_hash(schema: dict) -> str:
    """Return a stable SHA-256 hex digest for *schema*."""
    serialised = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialised.encode()).hexdigest()


def capture_snapshot(schema: dict, env: str, snapshot_dir: str) -> str:
    """Persist *schema* as a JSON snapshot file and return its path."""
    os.makedirs(snapshot_dir, exist_ok=True)
    schema_hash = compute_schema_hash(schema)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{env}_{timestamp}_{schema_hash[:8]}.json"
    path = os.path.join(snapshot_dir, filename)
    payload = {
        "env": env,
        "timestamp": timestamp,
        "hash": schema_hash,
        "schema": schema,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def load_snapshot(path: str) -> dict:
    """Load and return a snapshot dict from *path*."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def list_snapshots(snapshot_dir: str, env: Optional[str] = None) -> list[str]:
    """Return sorted snapshot file paths, optionally filtered by *env*."""
    base = Path(snapshot_dir)
    if not base.exists():
        return []
    files = sorted(base.glob("*.json"))
    if env:
        files = [f for f in files if f.name.startswith(f"{env}_")]
    return [str(f) for f in files]


def latest_snapshot(
    snapshot_dir: str,
    env: Optional[str] = None,
    exclude: Optional[str] = None,
) -> Optional[str]:
    """Return the most recent snapshot path, optionally excluding *exclude*."""
    snapshots = list_snapshots(snapshot_dir, env)
    if exclude:
        snapshots = [s for s in snapshots if s != exclude]
    return snapshots[-1] if snapshots else None

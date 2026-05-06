"""Core module for capturing and storing database schema snapshots."""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SNAPSHOT_DIR = Path(".schemasnap/snapshots")


def compute_schema_hash(schema: dict) -> str:
    """Compute a stable SHA256 hash of a schema dictionary."""
    serialized = json.dumps(schema, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


def capture_snapshot(env: str, schema: dict, label: Optional[str] = None) -> Path:
    """
    Save a schema snapshot for the given environment.

    Args:
        env: Environment name (e.g. 'production', 'staging').
        schema: Dictionary representing the database schema.
        label: Optional human-readable label for the snapshot.

    Returns:
        Path to the saved snapshot file.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    schema_hash = compute_schema_hash(schema)

    snapshot = {
        "env": env,
        "timestamp": timestamp,
        "label": label or "",
        "schema_hash": schema_hash,
        "schema": schema,
    }

    filename = SNAPSHOT_DIR / f"{env}_{timestamp}_{schema_hash[:8]}.json"
    filename.write_text(json.dumps(snapshot, indent=2))
    return filename


def load_snapshot(path: Path) -> dict:
    """Load a snapshot from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {path}")
    return json.loads(path.read_text())


def list_snapshots(env: Optional[str] = None) -> list[Path]:
    """
    List all available snapshots, optionally filtered by environment.

    Returns:
        Sorted list of snapshot file paths (oldest first).
    """
    if not SNAPSHOT_DIR.exists():
        return []
    pattern = f"{env}_*.json" if env else "*.json"
    return sorted(SNAPSHOT_DIR.glob(pattern))


def latest_snapshot(env: str) -> Optional[Path]:
    """Return the most recent snapshot for an environment, or None."""
    snapshots = list_snapshots(env)
    return snapshots[-1] if snapshots else None

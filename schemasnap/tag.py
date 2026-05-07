"""Tag snapshots with human-readable labels for easier reference."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

_TAGS_FILENAME = "tags.json"


@dataclass
class TagEntry:
    snapshot_file: str
    tag: str
    env: str
    note: str = ""


def _tags_path(snapshot_dir: str) -> Path:
    return Path(snapshot_dir) / _TAGS_FILENAME


def load_tags(snapshot_dir: str) -> List[TagEntry]:
    """Load all tag entries from the tags file."""
    path = _tags_path(snapshot_dir)
    if not path.exists():
        return []
    with path.open() as fh:
        raw = json.load(fh)
    return [TagEntry(**entry) for entry in raw]


def save_tag(snapshot_dir: str, entry: TagEntry) -> None:
    """Save or overwrite a tag for a given snapshot file."""
    tags = load_tags(snapshot_dir)
    tags = [t for t in tags if t.snapshot_file != entry.snapshot_file]
    tags.append(entry)
    path = _tags_path(snapshot_dir)
    with path.open("w") as fh:
        json.dump([asdict(t) for t in tags], fh, indent=2)


def get_tag(snapshot_dir: str, tag: str) -> Optional[TagEntry]:
    """Return the TagEntry whose tag label matches, or None."""
    for entry in load_tags(snapshot_dir):
        if entry.tag == tag:
            return entry
    return None


def remove_tag(snapshot_dir: str, tag: str) -> bool:
    """Remove a tag by label. Returns True if it existed."""
    tags = load_tags(snapshot_dir)
    new_tags = [t for t in tags if t.tag != tag]
    if len(new_tags) == len(tags):
        return False
    path = _tags_path(snapshot_dir)
    with path.open("w") as fh:
        json.dump([asdict(t) for t in new_tags], fh, indent=2)
    return True


def list_tags(snapshot_dir: str, env: Optional[str] = None) -> List[TagEntry]:
    """Return all tags, optionally filtered by environment."""
    tags = load_tags(snapshot_dir)
    if env is not None:
        tags = [t for t in tags if t.env == env]
    return tags

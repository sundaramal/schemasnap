"""Snapshot annotation support — attach human-readable notes to snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AnnotationEntry:
    snapshot_file: str
    env: str
    note: str
    author: str
    timestamp: str


def _annotations_path(snapshot_dir: str) -> Path:
    return Path(snapshot_dir) / "annotations.jsonl"


def load_annotations(snapshot_dir: str) -> List[AnnotationEntry]:
    """Load all annotation entries from the annotations log."""
    path = _annotations_path(snapshot_dir)
    if not path.exists():
        return []
    entries: List[AnnotationEntry] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            data = json.loads(line)
            entries.append(AnnotationEntry(**data))
    return entries


def save_annotation(snapshot_dir: str, entry: AnnotationEntry) -> None:
    """Append an annotation entry to the annotations log."""
    path = _annotations_path(snapshot_dir)
    with path.open("a") as fh:
        fh.write(json.dumps(asdict(entry)) + "\n")


def get_annotations_for(
    snapshot_dir: str, snapshot_file: str
) -> List[AnnotationEntry]:
    """Return all annotations attached to a specific snapshot file."""
    return [
        e
        for e in load_annotations(snapshot_dir)
        if e.snapshot_file == snapshot_file
    ]


def delete_annotation(
    snapshot_dir: str, snapshot_file: str, author: str, timestamp: str
) -> int:
    """Remove a specific annotation. Returns number of entries removed."""
    entries = load_annotations(snapshot_dir)
    kept = [
        e
        for e in entries
        if not (
            e.snapshot_file == snapshot_file
            and e.author == author
            and e.timestamp == timestamp
        )
    ]
    removed = len(entries) - len(kept)
    path = _annotations_path(snapshot_dir)
    path.write_text("".join(json.dumps(asdict(e)) + "\n" for e in kept))
    return removed

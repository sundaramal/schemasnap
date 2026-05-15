"""Snapshot archiving: compress and bundle snapshots into a single archive file."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ArchiveResult:
    archive_path: Path
    snapshot_count: int
    skipped: List[str]

    @property
    def summary(self) -> str:
        parts = [f"Archived {self.snapshot_count} snapshot(s) -> {self.archive_path}"]
        if self.skipped:
            parts.append(f"Skipped {len(self.skipped)} file(s)")
        return "; ".join(parts)


def _is_snapshot_file(path: Path) -> bool:
    return path.suffix == ".json" and path.is_file()


def create_archive(
    snapshot_dir: Path,
    dest: Path,
    env: Optional[str] = None,
) -> ArchiveResult:
    """Compress all (or env-filtered) snapshots in *snapshot_dir* into a zip archive."""
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

    candidates = sorted(snapshot_dir.glob("*.json"))
    if env:
        candidates = [p for p in candidates if f"_{env}_" in p.name or p.name.startswith(f"{env}_")]

    archived = 0
    skipped: List[str] = []

    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for snap in candidates:
            if not _is_snapshot_file(snap):
                skipped.append(snap.name)
                continue
            zf.write(snap, arcname=snap.name)
            archived += 1

    return ArchiveResult(archive_path=dest, snapshot_count=archived, skipped=skipped)


def extract_archive(archive: Path, dest_dir: Path) -> List[Path]:
    """Extract snapshots from *archive* into *dest_dir*; return list of extracted paths."""
    if not archive.is_file():
        raise FileNotFoundError(f"Archive not found: {archive}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: List[Path] = []

    with zipfile.ZipFile(archive, "r") as zf:
        for name in zf.namelist():
            zf.extract(name, dest_dir)
            extracted.append(dest_dir / name)

    return extracted


def list_archive_contents(archive: Path) -> List[dict]:
    """Return metadata for each snapshot inside *archive* without extracting."""
    if not archive.is_file():
        raise FileNotFoundError(f"Archive not found: {archive}")

    contents = []
    with zipfile.ZipFile(archive, "r") as zf:
        for info in zf.infolist():
            with zf.open(info.filename) as fh:
                try:
                    data = json.load(fh)
                    contents.append({
                        "filename": info.filename,
                        "environment": data.get("environment"),
                        "captured_at": data.get("captured_at"),
                        "schema_hash": data.get("schema_hash"),
                        "compressed_size": info.compress_size,
                    })
                except (json.JSONDecodeError, KeyError):
                    contents.append({"filename": info.filename, "error": "invalid json"})
    return contents

"""Compare a chain of snapshots for a given environment, producing a sequence of diffs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from schemasnap.diff import SchemaDiff, diff_snapshots
from schemasnap.snapshot import list_snapshots, load_snapshot


@dataclass
class ChainLink:
    """A single diff between two consecutive snapshots."""

    from_file: str
    to_file: str
    diff: SchemaDiff

    @property
    def has_changes(self) -> bool:
        return self.diff.has_changes


@dataclass
class CompareChainResult:
    """Result of comparing a chain of snapshots."""

    env: str
    links: List[ChainLink] = field(default_factory=list)

    @property
    def total_links(self) -> int:
        return len(self.links)

    @property
    def changed_links(self) -> int:
        return sum(1 for lnk in self.links if lnk.has_changes)

    def summary(self) -> str:
        return (
            f"env={self.env} links={self.total_links} "
            f"changed={self.changed_links} unchanged={self.total_links - self.changed_links}"
        )


def compare_snapshot_chain(
    snapshot_dir: str,
    env: str,
    limit: Optional[int] = None,
) -> CompareChainResult:
    """Load all snapshots for *env*, sort by filename, and diff consecutive pairs."""
    all_files = list_snapshots(snapshot_dir, env=env)
    if not all_files:
        return CompareChainResult(env=env)

    # list_snapshots returns filenames; build sorted absolute paths
    base = Path(snapshot_dir)
    sorted_files = sorted(all_files)
    if limit is not None and limit > 0:
        sorted_files = sorted_files[-limit:]

    links: List[ChainLink] = []
    for prev_name, next_name in zip(sorted_files, sorted_files[1:]):
        prev_snap = load_snapshot(str(base / prev_name))
        next_snap = load_snapshot(str(base / next_name))
        diff = diff_snapshots(prev_snap["schema"], next_snap["schema"])
        links.append(ChainLink(from_file=prev_name, to_file=next_name, diff=diff))

    return CompareChainResult(env=env, links=links)

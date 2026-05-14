"""CLI subcommands for schema lineage tracking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .lineage import load_lineage, record_lineage, get_parent
from .snapshot import load_snapshot


def add_lineage_subparsers(sub: argparse.Action) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("lineage", help="Manage snapshot lineage")
    s = p.add_subparsers(dest="lineage_cmd", required=True)

    rec = s.add_parser("record", help="Record parent→child lineage for a snapshot")
    rec.add_argument("snapshot", help="Path to child snapshot file")
    rec.add_argument("--parent", default=None, help="Path to parent snapshot file")
    rec.add_argument("--dir", dest="snap_dir", default="snapshots",
                     help="Snapshot directory (for lineage storage)")
    rec.set_defaults(func=cmd_lineage_record)

    show = s.add_parser("show", help="Show lineage chain for a snapshot")
    show.add_argument("snapshot", help="Path to snapshot file")
    show.add_argument("--dir", dest="snap_dir", default="snapshots")
    show.add_argument("--fmt", choices=["text", "json"], default="text")
    show.set_defaults(func=cmd_lineage_show)

    lst = s.add_parser("list", help="List all recorded lineage entries")
    lst.add_argument("--dir", dest="snap_dir", default="snapshots")
    lst.add_argument("--fmt", choices=["text", "json"], default="text")
    lst.set_defaults(func=cmd_lineage_list)

    p.set_defaults(func=cmd_lineage)


def cmd_lineage(args: argparse.Namespace) -> int:
    """Dispatch to lineage sub-command."""
    if hasattr(args, "func") and args.func is not cmd_lineage:
        return args.func(args)
    print("Use a lineage sub-command: record | show | list", file=sys.stderr)
    return 1


def cmd_lineage_record(args: argparse.Namespace) -> int:
    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        print(f"Snapshot not found: {snap_path}", file=sys.stderr)
        return 1
    snap = load_snapshot(str(snap_path))
    parent_hash: str | None = None
    if args.parent:
        parent_path = Path(args.parent)
        if not parent_path.exists():
            print(f"Parent snapshot not found: {parent_path}", file=sys.stderr)
            return 1
        parent_snap = load_snapshot(str(parent_path))
        parent_hash = parent_snap.get("hash")
    child_hash = snap.get("hash")
    if not child_hash:
        print("Snapshot missing 'hash' field.", file=sys.stderr)
        return 1
    snap_dir = Path(args.snap_dir)
    record_lineage(snap_dir, child_hash=child_hash, parent_hash=parent_hash,
                   metadata={"child_file": str(snap_path), "parent_file": args.parent})
    print(f"Recorded lineage: {parent_hash or 'root'} -> {child_hash}")
    return 0


def cmd_lineage_show(args: argparse.Namespace) -> int:
    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        print(f"Snapshot not found: {snap_path}", file=sys.stderr)
        return 1
    snap = load_snapshot(str(snap_path))
    child_hash = snap.get("hash")
    snap_dir = Path(args.snap_dir)
    entries = load_lineage(snap_dir)
    chain = []
    current = child_hash
    visited: set[str] = set()
    while current:
        if current in visited:
            break
        visited.add(current)
        entry = get_parent(entries, current)
        chain.append({"hash": current, "parent": entry.parent_hash if entry else None})
        current = entry.parent_hash if entry else None
    if args.fmt == "json":
        print(json.dumps(chain, indent=2))
    else:
        for item in chain:
            parent_label = item["parent"] or "(root)"
            print(f"  {item['hash'][:12]}  <-  {parent_label[:12] if item['parent'] else '(root)'}")
    return 0


def cmd_lineage_list(args: argparse.Namespace) -> int:
    snap_dir = Path(args.snap_dir)
    entries = load_lineage(snap_dir)
    if args.fmt == "json":
        data = [
            {"child": e.child_hash, "parent": e.parent_hash, "metadata": e.metadata}
            for e in entries
        ]
        print(json.dumps(data, indent=2))
    else:
        if not entries:
            print("No lineage entries recorded.")
        for e in entries:
            parent_label = e.parent_hash[:12] if e.parent_hash else "(root)"
            print(f"  {e.child_hash[:12]}  parent={parent_label}")
    return 0

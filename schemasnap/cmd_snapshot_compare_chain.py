"""CLI sub-command: snapshot compare-chain."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from schemasnap.snapshot_compare_chain import compare_snapshot_chain


def add_snapshot_compare_chain_subparsers(sub: _SubParsersAction) -> None:  # type: ignore[type-arg]
    p: ArgumentParser = sub.add_parser(
        "compare-chain",
        help="Diff consecutive snapshots for an environment",
    )
    p.add_argument("env", help="Environment name to compare")
    p.add_argument(
        "--dir",
        default="snapshots",
        help="Snapshot directory (default: snapshots)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only compare the N most recent snapshots (0 = all)",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    p.add_argument(
        "--changed-only",
        action="store_true",
        help="Only print links that have changes",
    )
    p.set_defaults(func=cmd_snapshot_compare_chain)


def cmd_snapshot_compare_chain(args: Namespace) -> int:
    snap_dir = args.dir
    if not Path(snap_dir).is_dir():
        print(f"error: snapshot directory not found: {snap_dir}", file=sys.stderr)
        return 1

    limit = args.limit if args.limit > 0 else None
    result = compare_snapshot_chain(snap_dir, args.env, limit=limit)

    links = result.links
    if args.changed_only:
        links = [lnk for lnk in links if lnk.has_changes]

    if args.fmt == "json":
        out = {
            "env": result.env,
            "total_links": result.total_links,
            "changed_links": result.changed_links,
            "links": [
                {
                    "from": lnk.from_file,
                    "to": lnk.to_file,
                    "added_tables": list(lnk.diff.added_tables),
                    "removed_tables": list(lnk.diff.removed_tables),
                    "modified_tables": list(lnk.diff.modified_tables.keys()),
                    "has_changes": lnk.has_changes,
                }
                for lnk in links
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print(result.summary())
        for lnk in links:
            status = "CHANGED" if lnk.has_changes else "unchanged"
            print(f"  {lnk.from_file} -> {lnk.to_file}  [{status}]")
            if lnk.has_changes:
                if lnk.diff.added_tables:
                    print(f"    + added:    {sorted(lnk.diff.added_tables)}")
                if lnk.diff.removed_tables:
                    print(f"    - removed:  {sorted(lnk.diff.removed_tables)}")
                if lnk.diff.modified_tables:
                    print(f"    ~ modified: {sorted(lnk.diff.modified_tables)}")

    return 0

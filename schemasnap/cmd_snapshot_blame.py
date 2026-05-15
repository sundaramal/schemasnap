"""CLI sub-command: snapshot-blame"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .snapshot_blame import compute_blame


def add_snapshot_blame_subparsers(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "snapshot-blame",
        help="Show which snapshot first introduced each table / column.",
    )
    p.add_argument("snapshot_dir", help="Directory containing snapshot files.")
    p.add_argument("--env", default=None, help="Restrict to a specific environment.")
    p.add_argument(
        "--table", default=None, help="Restrict output to a specific table."
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_blame)


def cmd_snapshot_blame(args: argparse.Namespace) -> int:
    snap_dir = args.snapshot_dir
    if not Path(snap_dir).is_dir():
        print(f"error: directory not found: {snap_dir}", file=sys.stderr)
        return 1

    report = compute_blame(snap_dir, env=getattr(args, "env", None))

    entries = report.entries
    if args.table:
        entries = [e for e in entries if e.table == args.table]

    if not entries:
        print("No blame entries found.")
        return 0

    if args.fmt == "json":
        payload = [
            {
                "table": e.table,
                "column": e.column,
                "first_seen_file": e.first_seen_file,
                "first_seen_env": e.first_seen_env,
                "first_seen_hash": e.first_seen_hash,
            }
            for e in entries
        ]
        print(json.dumps(payload, indent=2))
    else:
        for e in entries:
            target = f"{e.table}.{e.column}" if e.column else e.table
            print(f"{target:45s}  {e.first_seen_file}  ({e.first_seen_env})")

    return 0

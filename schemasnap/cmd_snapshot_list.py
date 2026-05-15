"""CLI sub-command: list snapshots stored in a directory."""
from __future__ import annotations

import argparse
import json
import os
from typing import List

from schemasnap.snapshot import list_snapshots, load_snapshot


def add_snapshot_list_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "snapshot-list",
        help="List captured snapshots in a directory.",
    )
    p.add_argument(
        "--dir",
        default="snapshots",
        help="Directory that contains snapshot files (default: snapshots).",
    )
    p.add_argument(
        "--env",
        default=None,
        help="Filter snapshots by environment name.",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--show-tables",
        action="store_true",
        default=False,
        help="Include table names from each snapshot.",
    )
    p.set_defaults(func=cmd_snapshot_list)


def cmd_snapshot_list(args: argparse.Namespace) -> int:
    snap_dir: str = args.dir
    env_filter: str | None = args.env
    fmt: str = args.fmt
    show_tables: bool = args.show_tables

    if not os.path.isdir(snap_dir):
        print(f"[error] directory not found: {snap_dir}")
        return 1

    files: List[str] = list_snapshots(snap_dir)
    if env_filter:
        files = [f for f in files if f"_{env_filter}_" in os.path.basename(f)]

    if not files:
        if fmt == "json":
            print(json.dumps([]))
        else:
            print("No snapshots found.")
        return 0

    rows = []
    for filepath in sorted(files):
        snap = load_snapshot(filepath)
        entry: dict = {
            "file": os.path.basename(filepath),
            "environment": snap.get("environment", "unknown"),
            "captured_at": snap.get("captured_at", "unknown"),
            "schema_hash": snap.get("schema_hash", "unknown"),
            "table_count": len(snap.get("schema", {})),
        }
        if show_tables:
            entry["tables"] = sorted(snap.get("schema", {}).keys())
        rows.append(entry)

    if fmt == "json":
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            line = (
                f"{r['file']}  env={r['environment']}  "
                f"captured_at={r['captured_at']}  "
                f"hash={r['schema_hash'][:12]}  "
                f"tables={r['table_count']}"
            )
            print(line)
            if show_tables and r.get("tables"):
                for tbl in r["tables"]:
                    print(f"  - {tbl}")

    return 0

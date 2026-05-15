"""CLI sub-command: snapshot-show — pretty-print a single snapshot file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.snapshot import load_snapshot
from schemasnap.export import render_markdown, render_csv, snapshot_to_rows


def add_snapshot_show_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "snapshot-show",
        help="Display the contents of a snapshot file.",
    )
    p.add_argument("snapshot_file", help="Path to the .json snapshot file.")
    p.add_argument(
        "--fmt",
        choices=["json", "text", "csv", "markdown"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--table",
        metavar="TABLE",
        default=None,
        help="Show only the named table.",
    )
    p.set_defaults(func=cmd_snapshot_show)


def cmd_snapshot_show(args: argparse.Namespace) -> int:
    path = Path(args.snapshot_file)
    if not path.exists():
        print(f"Error: snapshot file not found: {path}", file=sys.stderr)
        return 1

    snapshot = load_snapshot(path)
    schema: dict = snapshot.get("schema", {})

    if args.table:
        if args.table not in schema:
            print(f"Error: table '{args.table}' not found in snapshot.", file=sys.stderr)
            return 1
        schema = {args.table: schema[args.table]}

    fmt = args.fmt

    if fmt == "json":
        print(json.dumps(snapshot if not args.table else {**snapshot, "schema": schema}, indent=2))

    elif fmt == "text":
        env = snapshot.get("environment", "unknown")
        ts = snapshot.get("timestamp", "unknown")
        h = snapshot.get("hash", "unknown")
        print(f"Environment : {env}")
        print(f"Timestamp   : {ts}")
        print(f"Hash        : {h}")
        print(f"Tables      : {len(schema)}")
        print()
        for table, columns in sorted(schema.items()):
            print(f"  {table}")
            for col in columns:
                print(f"    - {col['name']}  ({col['type']})")

    elif fmt == "csv":
        tmp = {**snapshot, "schema": schema}
        print(render_csv(snapshot_to_rows(tmp)), end="")

    elif fmt == "markdown":
        tmp = {**snapshot, "schema": schema}
        print(render_markdown(snapshot_to_rows(tmp)))

    return 0

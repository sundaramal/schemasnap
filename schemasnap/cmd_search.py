"""CLI subcommands for searching snapshots by table/column patterns."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.search import SearchConfig, search_snapshots


def add_search_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "search",
        help="Search snapshot files for matching tables or columns.",
    )
    p.add_argument("snapshot_dir", help="Directory containing snapshot files.")
    p.add_argument(
        "--table",
        dest="table_pattern",
        default=None,
        metavar="PATTERN",
        help="Regex pattern to match table names.",
    )
    p.add_argument(
        "--column",
        dest="column_pattern",
        default=None,
        metavar="PATTERN",
        help="Regex pattern to match column names.",
    )
    p.add_argument(
        "--env",
        dest="env_filter",
        default=None,
        metavar="ENV",
        help="Restrict search to a specific environment prefix.",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_search)


def cmd_search(args: argparse.Namespace) -> int:
    snap_dir = Path(args.snapshot_dir)
    if not snap_dir.is_dir():
        print(f"error: directory not found: {snap_dir}", file=sys.stderr)
        return 1

    cfg = SearchConfig(
        table_pattern=args.table_pattern,
        column_pattern=args.column_pattern,
        env_filter=getattr(args, "env_filter", None),
    )

    results = search_snapshots(snap_dir, cfg)

    if args.fmt == "json":
        payload = [
            {
                "snapshot": r.snapshot_file,
                "environment": r.environment,
                "table": r.table,
                "column": r.column,
            }
            for r in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        if not results:
            print("No matches found.")
        else:
            for r in results:
                col_part = f"  column={r.column}" if r.column else ""
                print(f"[{r.environment}] {r.snapshot_file}  table={r.table}{col_part}")

    return 0

"""CLI subcommand: merge two snapshot files into one."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.merge import merge_snapshot_files


def add_merge_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the 'merge' subcommand."""
    p = subparsers.add_parser(
        "merge",
        help="Merge two snapshot files, preferring primary on conflict.",
    )
    p.add_argument("primary", help="Path to the primary snapshot file.")
    p.add_argument("secondary", help="Path to the secondary snapshot file.")
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write merged snapshot to this file (default: stdout).",
    )
    p.add_argument(
        "--env",
        default=None,
        help="Override the 'environment' field in the merged snapshot.",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Print a JSON summary instead of a human-readable report.",
    )
    p.set_defaults(func=cmd_merge)


def cmd_merge(args: argparse.Namespace) -> int:
    """Execute the merge subcommand."""
    primary_path = Path(args.primary)
    secondary_path = Path(args.secondary)

    if not primary_path.exists():
        print(f"[error] primary snapshot not found: {primary_path}", file=sys.stderr)
        return 1
    if not secondary_path.exists():
        print(f"[error] secondary snapshot not found: {secondary_path}", file=sys.stderr)
        return 1

    result = merge_snapshot_files(str(primary_path), str(secondary_path))

    merged = result.merged_snapshot
    if args.env:
        merged = {**merged, "environment": args.env}

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(merged, indent=2))
        print(f"Merged snapshot written to {out_path}")
    else:
        print(json.dumps(merged, indent=2))

    if args.as_json:
        summary = {
            "conflicts": result.conflict_count(),
            "summary": result.summary(),
        }
        print(json.dumps(summary, indent=2), file=sys.stderr)
    else:
        print(result.summary(), file=sys.stderr)

    return 0

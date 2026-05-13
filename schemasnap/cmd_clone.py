"""CLI sub-command: schemasnap clone."""
from __future__ import annotations

import argparse
from pathlib import Path

from .clone import clone_snapshot


def add_clone_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "clone",
        help="Clone a snapshot from one environment label to another.",
    )
    p.add_argument("source_env", help="Source environment name (e.g. 'prod').")
    p.add_argument("dest_env", help="Destination environment name (e.g. 'staging').")
    p.add_argument(
        "--snapshot-dir",
        default="snapshots",
        help="Directory containing snapshots (default: snapshots).",
    )
    p.add_argument(
        "--file",
        default=None,
        help="Explicit source snapshot file (defaults to latest for source_env).",
    )
    p.set_defaults(func=cmd_clone)


def cmd_clone(args: argparse.Namespace) -> int:
    result = clone_snapshot(
        snapshot_dir=Path(args.snapshot_dir),
        source_env=args.source_env,
        dest_env=args.dest_env,
        source_file=args.file,
    )
    if result.success:
        print(result.message)
        return 0
    print(f"ERROR: {result.message}")
    return 1

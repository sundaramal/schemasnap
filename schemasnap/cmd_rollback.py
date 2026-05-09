"""CLI sub-commands for rollback."""

from __future__ import annotations

import argparse
from pathlib import Path

from .rollback import rollback_to


def add_rollback_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("rollback", help="Restore a snapshot to a previous version")
    p.add_argument("env", help="Environment name (e.g. production)")
    p.add_argument("--snap-dir", default="snapshots", help="Snapshot directory")

    ref_group = p.add_mutually_exclusive_group(required=True)
    ref_group.add_argument("--hash", dest="schema_hash", help="Schema hash to roll back to")
    ref_group.add_argument("--tag", dest="tag_name", help="Tag name to roll back to")

    p.set_defaults(func=cmd_rollback)


def cmd_rollback(args: argparse.Namespace) -> int:
    snap_dir = Path(args.snap_dir)
    result = rollback_to(
        snap_dir,
        args.env,
        schema_hash=getattr(args, "schema_hash", None),
        tag_name=getattr(args, "tag_name", None),
    )
    if result.success:
        print(f"[rollback] {result.message}")
        print(f"  source : {result.source_file}")
        print(f"  written: {result.dest_file}")
        return 0
    else:
        print(f"[rollback] ERROR: {result.message}")
        return 1

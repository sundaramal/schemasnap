"""CLI subcommand: snapshot-stats — show aggregate statistics for a snapshot directory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from schemasnap.snapshot import list_snapshots, load_snapshot
from schemasnap.snapshot_stats import collect_snapshot_stats, render_stats_text


def add_snapshot_stats_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "snapshot-stats",
        help="Print aggregate statistics across all snapshots in a directory.",
    )
    p.add_argument("--dir", required=True, help="Directory containing snapshot files.")
    p.add_argument(
        "--env",
        default=None,
        help="Filter to a specific environment name.",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_stats)


def cmd_snapshot_stats(args: argparse.Namespace) -> int:
    snap_dir = Path(args.dir)
    if not snap_dir.is_dir():
        print(f"[error] directory not found: {snap_dir}", file=sys.stderr)
        return 1

    files: List[Path] = list_snapshots(snap_dir)
    if args.env:
        files = [f for f in files if args.env in f.stem]

    if not files:
        print("[info] no snapshots found.", file=sys.stderr)
        return 0

    snapshots = [load_snapshot(f) for f in files]
    stats = collect_snapshot_stats(snapshots)

    if args.fmt == "json":
        print(json.dumps(stats, indent=2))
    else:
        print(render_stats_text(stats))

    return 0

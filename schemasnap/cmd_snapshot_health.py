"""CLI subcommand: snapshot-health — check a snapshot directory for issues."""
from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from schemasnap.snapshot_health import run_health_checks, render_health_text, render_health_json


def add_snapshot_health_subparsers(subparsers: _SubParsersAction) -> None:  # type: ignore[type-arg]
    p: ArgumentParser = subparsers.add_parser(
        "snapshot-health",
        help="Run health checks on a snapshot directory.",
    )
    p.add_argument("snap_dir", help="Directory containing snapshot files.")
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 on warnings as well as errors.",
    )
    p.set_defaults(func=cmd_snapshot_health)


def cmd_snapshot_health(args: Namespace) -> int:
    snap_dir = Path(args.snap_dir)
    if not snap_dir.is_dir():
        print(f"Error: directory not found: {snap_dir}", file=sys.stderr)
        return 1

    report = run_health_checks(snap_dir)

    if args.fmt == "json":
        print(render_health_json(report))
    else:
        print(render_health_text(report))

    if not report.passed:
        return 2
    if args.strict and report.issues:
        return 1
    return 0

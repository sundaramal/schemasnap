"""CLI sub-commands for exporting snapshots."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.export import export_snapshot
from schemasnap.snapshot import latest_snapshot


def add_export_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the 'export' sub-command onto *subparsers*."""
    parser = subparsers.add_parser(
        "export",
        help="Export a snapshot to CSV, Markdown, or HTML.",
    )
    parser.add_argument(
        "--env",
        required=True,
        help="Environment name whose latest snapshot will be exported.",
    )
    parser.add_argument(
        "--snapshot-dir",
        default="snapshots",
        help="Directory containing snapshot files (default: snapshots).",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Explicit snapshot file to export (overrides --env latest lookup).",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["csv", "markdown", "html"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write output to this file instead of stdout.",
    )
    parser.set_defaults(func=cmd_export)


def cmd_export(args: argparse.Namespace) -> int:
    """Handle the 'export' sub-command."""
    snapshot_dir = Path(args.snapshot_dir)

    if args.file:
        snapshot_file = Path(args.file)
    else:
        snapshot_file = latest_snapshot(snapshot_dir, args.env)
        if snapshot_file is None:
            print(
                f"[schemasnap] No snapshots found for env '{args.env}' in {snapshot_dir}",
                file=sys.stderr,
            )
            return 1

    try:
        content = export_snapshot(snapshot_file, fmt=args.fmt, output=args.output)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[schemasnap] Export failed: {exc}", file=sys.stderr)
        return 1

    if args.output:
        print(f"[schemasnap] Exported {args.fmt} to {args.output}")
    else:
        print(content)

    return 0

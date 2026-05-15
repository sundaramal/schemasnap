"""CLI sub-command: snapshot-copy — duplicate a snapshot file under a new environment label."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.clone import clone_snapshot


def add_snapshot_copy_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the *snapshot-copy* sub-command."""
    p = subparsers.add_parser(
        "snapshot-copy",
        help="Copy a snapshot file and re-label it for a different environment.",
    )
    p.add_argument("source", help="Path to the source snapshot JSON file.")
    p.add_argument("dest_env", help="Environment name to stamp on the copy.")
    p.add_argument(
        "--dest-dir",
        default=None,
        help="Directory where the new file is written (defaults to the source file's directory).",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_copy)


def cmd_snapshot_copy(args: argparse.Namespace) -> int:
    """Execute the snapshot-copy command.  Returns an exit code."""
    source = Path(args.source)
    if not source.is_file():
        print(f"ERROR: source file not found: {source}", file=sys.stderr)
        return 1

    dest_dir = Path(args.dest_dir) if args.dest_dir else source.parent
    if not dest_dir.is_dir():
        print(f"ERROR: destination directory not found: {dest_dir}", file=sys.stderr)
        return 1

    result = clone_snapshot(
        source_path=source,
        dest_env=args.dest_env,
        dest_dir=dest_dir,
    )

    if not result.success:
        print(f"ERROR: {result.message}", file=sys.stderr)
        return 1

    if args.fmt == "json":
        print(
            json.dumps(
                {
                    "source": str(source),
                    "dest": str(result.dest_path),
                    "dest_env": args.dest_env,
                    "schema_hash": result.schema_hash,
                }
            )
        )
    else:
        print(f"Copied  : {source}")
        print(f"New file: {result.dest_path}")
        print(f"Env     : {args.dest_env}")
        print(f"Hash    : {result.schema_hash}")

    return 0

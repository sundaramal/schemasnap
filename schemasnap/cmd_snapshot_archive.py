"""CLI sub-commands for snapshot archiving."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schemasnap.snapshot_archive import (
    ArchiveResult,
    create_archive,
    extract_archive,
    list_archive_contents,
)


def add_snapshot_archive_subparsers(sub: argparse.Action) -> None:  # type: ignore[type-arg]
    # --- create ---
    p_create = sub.add_parser("archive-create", help="Bundle snapshots into a zip archive")
    p_create.add_argument("--dir", default="snapshots", help="Snapshot directory")
    p_create.add_argument("--out", required=True, help="Destination archive path (.zip)")
    p_create.add_argument("--env", default=None, help="Filter by environment name")
    p_create.set_defaults(func=cmd_archive_create)

    # --- extract ---
    p_extract = sub.add_parser("archive-extract", help="Extract snapshots from a zip archive")
    p_extract.add_argument("archive", help="Archive file to extract")
    p_extract.add_argument("--dir", default="snapshots", help="Destination directory")
    p_extract.set_defaults(func=cmd_archive_extract)

    # --- list ---
    p_list = sub.add_parser("archive-list", help="List contents of a snapshot archive")
    p_list.add_argument("archive", help="Archive file to inspect")
    p_list.add_argument("--fmt", choices=["text", "json"], default="text")
    p_list.set_defaults(func=cmd_archive_list)


def cmd_archive_create(args: argparse.Namespace) -> int:
    snap_dir = Path(args.dir)
    dest = Path(args.out)
    try:
        result: ArchiveResult = create_archive(snap_dir, dest, env=args.env)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(result.summary)
    return 0


def cmd_archive_extract(args: argparse.Namespace) -> int:
    archive = Path(args.archive)
    dest_dir = Path(args.dir)
    try:
        paths = extract_archive(archive, dest_dir)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Extracted {len(paths)} file(s) to {dest_dir}")
    return 0


def cmd_archive_list(args: argparse.Namespace) -> int:
    archive = Path(args.archive)
    try:
        contents = list_archive_contents(archive)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.fmt == "json":
        print(json.dumps(contents, indent=2))
    else:
        if not contents:
            print("(empty archive)")
        else:
            for entry in contents:
                if "error" in entry:
                    print(f"  {entry['filename']}  [ERROR: {entry['error']}]")
                else:
                    print(
                        f"  {entry['filename']}  env={entry['environment']}  "
                        f"hash={entry['schema_hash']}  captured={entry['captured_at']}"
                    )
    return 0

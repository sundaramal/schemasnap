"""CLI sub-command: snapshot-index — list/query the snapshot index."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from schemasnap.snapshot_index import build_index


def add_snapshot_index_subparsers(sub) -> None:
    p = sub.add_parser(
        "snapshot-index",
        help="Build and display an index of all snapshots in a directory.",
    )
    p.add_argument("snapshot_dir", help="Directory that contains snapshot files.")
    p.add_argument(
        "--env",
        default=None,
        help="Filter index to a single environment.",
    )
    p.add_argument(
        "--hash",
        dest="schema_hash",
        default=None,
        help="Look up a single snapshot by (prefix of) its schema hash.",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_index)


def cmd_snapshot_index(args) -> int:
    snap_dir = Path(args.snapshot_dir)
    if not snap_dir.is_dir():
        print(f"error: directory not found: {snap_dir}", file=sys.stderr)
        return 1

    index = build_index(snap_dir)

    # Single-hash lookup
    if args.schema_hash:
        entry = index.by_hash(args.schema_hash)
        if entry is None:
            print(f"error: no snapshot found for hash prefix '{args.schema_hash}'",
                  file=sys.stderr)
            return 1
        entries = [entry]
    elif args.env:
        entries = index.by_env(args.env)
        if not entries:
            print(f"error: no snapshots found for environment '{args.env}'",
                  file=sys.stderr)
            return 1
    else:
        entries = index.entries

    if args.fmt == "json":
        payload = [
            {
                "path": str(e.path),
                "env": e.env,
                "schema_hash": e.schema_hash,
                "table_count": e.table_count,
                "tables": e.tables,
            }
            for e in entries
        ]
        print(json.dumps(payload, indent=2))
    else:
        for e in entries:
            print(f"{e.path.name}  env={e.env}  hash={e.schema_hash[:12]}  tables={e.table_count}")

    return 0

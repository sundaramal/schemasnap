"""CLI sub-commands for snapshot lineage."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from schemasnap.lineage import load_lineage, get_parent, lineage_chain


def add_lineage_subparsers(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("lineage", help="Inspect snapshot lineage")
    ls = p.add_subparsers(dest="lineage_cmd", required=True)

    p_list = ls.add_parser("list", help="List all lineage entries")
    p_list.add_argument("--snapshot-dir", default="snapshots")
    p_list.add_argument("--json", dest="as_json", action="store_true")

    p_show = ls.add_parser("show", help="Show parent of a snapshot")
    p_show.add_argument("snapshot_file")
    p_show.add_argument("--snapshot-dir", default="snapshots")
    p_show.add_argument("--json", dest="as_json", action="store_true")

    p_chain = ls.add_parser("chain", help="Show full ancestry chain of a snapshot")
    p_chain.add_argument("snapshot_file")
    p_chain.add_argument("--snapshot-dir", default="snapshots")
    p_chain.add_argument("--json", dest="as_json", action="store_true")

    p.set_defaults(func=cmd_lineage)


def cmd_lineage(args: argparse.Namespace) -> int:
    if args.lineage_cmd == "list":
        entries = load_lineage(args.snapshot_dir)
        data = [asdict(e) for e in entries]
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            if not data:
                print("No lineage entries found.")
            for e in data:
                parent = e["parent_file"] or "<root>"
                print(f"{e['snapshot_file']}  <-  {parent}  [{e['env']}]")
        return 0

    if args.lineage_cmd == "show":
        entry = get_parent(args.snapshot_dir, args.snapshot_file)
        if entry is None:
            print(f"No lineage entry for {args.snapshot_file}", file=sys.stderr)
            return 1
        if args.as_json:
            print(json.dumps(asdict(entry), indent=2))
        else:
            parent = entry.parent_file or "<root>"
            print(f"snapshot : {entry.snapshot_file}")
            print(f"parent   : {parent}")
            print(f"env      : {entry.env}")
            print(f"hash     : {entry.schema_hash}")
        return 0

    if args.lineage_cmd == "chain":
        chain = lineage_chain(args.snapshot_dir, args.snapshot_file)
        if not chain:
            print(f"No lineage data for {args.snapshot_file}", file=sys.stderr)
            return 1
        data = [asdict(e) for e in chain]
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            for i, e in enumerate(data):
                prefix = "  " * i + ("└─ " if i else "")
                print(f"{prefix}{e['snapshot_file']}  [{e['env']}]")
        return 0

    return 1

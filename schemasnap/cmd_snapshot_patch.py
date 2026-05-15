"""CLI sub-command: snapshot-patch — apply a diff to a snapshot file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .diff import diff_snapshots
from .snapshot import load_snapshot, capture_snapshot
from .snapshot_patch import apply_patch


def add_snapshot_patch_subparsers(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "snapshot-patch",
        help="Apply the diff between two snapshots onto a base snapshot.",
    )
    p.add_argument("base", help="Path to the base snapshot file.")
    p.add_argument("from_snap", help="Path to the 'before' snapshot used to compute the diff.")
    p.add_argument("to_snap", help="Path to the 'after' snapshot used to compute the diff.")
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Destination file for the patched snapshot (default: stdout as JSON).",
    )
    p.add_argument(
        "--allow-missing",
        action="store_true",
        default=False,
        help="Skip removals/modifications that target tables absent in the base.",
    )
    p.set_defaults(func=cmd_snapshot_patch)


def cmd_snapshot_patch(args: argparse.Namespace) -> int:
    for attr, label in [("base", "base"), ("from_snap", "from"), ("to_snap", "to")]:
        p = Path(getattr(args, attr))
        if not p.exists():
            print(f"[schemasnap] snapshot-patch: file not found: {p}", file=sys.stderr)
            return 1

    base_snap = load_snapshot(args.base)
    from_snap = load_snapshot(args.from_snap)
    to_snap = load_snapshot(args.to_snap)

    diff = diff_snapshots(from_snap["schema"], to_snap["schema"])
    result = apply_patch(base_snap, diff, allow_missing=args.allow_missing)

    if not result.success:
        print(f"[schemasnap] snapshot-patch failed: {result.message}", file=sys.stderr)
        return 1

    output_text = json.dumps(result.patched_schema, indent=2)

    if args.output:
        Path(args.output).write_text(output_text)
        print(f"[schemasnap] Patched snapshot written to {args.output}")
        print(f"  applied : {len(result.applied)} operation(s)")
        if result.skipped:
            print(f"  skipped : {len(result.skipped)} operation(s)")
    else:
        print(output_text)

    return 0

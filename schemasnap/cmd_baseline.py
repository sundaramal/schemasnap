"""CLI sub-commands for baseline management (set, show, check)."""

from __future__ import annotations

import argparse
import sys

from schemasnap.baseline import (
    get_baseline,
    set_baseline_from_snapshot,
    compare_to_baseline,
)
from schemasnap.snapshot import latest_snapshot


def add_baseline_subparsers(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register baseline sub-commands onto an existing subparsers group."""

    # --- set ---
    p_set = subparsers.add_parser("baseline-set", help="Mark the latest (or specified) snapshot as the baseline.")
    p_set.add_argument("--env", required=True, help="Environment name (e.g. prod)")
    p_set.add_argument("--snapshot-dir", default="snapshots", help="Directory containing snapshots")
    p_set.add_argument("--file", default=None, help="Specific snapshot file to use (default: latest)")
    p_set.set_defaults(func=cmd_baseline_set)

    # --- show ---
    p_show = subparsers.add_parser("baseline-show", help="Display the current baseline for an environment.")
    p_show.add_argument("--env", required=True, help="Environment name")
    p_show.add_argument("--snapshot-dir", default="snapshots", help="Directory containing snapshots")
    p_show.set_defaults(func=cmd_baseline_show)

    # --- check ---
    p_check = subparsers.add_parser("baseline-check", help="Check whether the latest snapshot matches the baseline.")
    p_check.add_argument("--env", required=True, help="Environment name")
    p_check.add_argument("--snapshot-dir", default="snapshots", help="Directory containing snapshots")
    p_check.add_argument("--file", default=None, help="Specific snapshot file to check (default: latest)")
    p_check.set_defaults(func=cmd_baseline_check)


def cmd_baseline_set(args: argparse.Namespace) -> int:
    snapshot_file = args.file or latest_snapshot(args.snapshot_dir, args.env)
    if snapshot_file is None:
        print(f"[baseline-set] No snapshot found for env '{args.env}' in {args.snapshot_dir}", file=sys.stderr)
        return 1
    entry = set_baseline_from_snapshot(args.snapshot_dir, args.env, snapshot_file)
    print(f"[baseline-set] Baseline set for '{args.env}': hash={entry.hash} file={entry.snapshot_file}")
    return 0


def cmd_baseline_show(args: argparse.Namespace) -> int:
    entry = get_baseline(args.snapshot_dir, args.env)
    if entry is None:
        print(f"[baseline-show] No baseline set for env '{args.env}'.")
        return 1
    print(f"env:           {entry.env}")
    print(f"snapshot_file: {entry.snapshot_file}")
    print(f"hash:          {entry.hash}")
    print(f"set_at:        {entry.set_at}")
    return 0


def cmd_baseline_check(args: argparse.Namespace) -> int:
    snapshot_file = args.file or latest_snapshot(args.snapshot_dir, args.env)
    if snapshot_file is None:
        print(f"[baseline-check] No snapshot found for env '{args.env}' in {args.snapshot_dir}", file=sys.stderr)
        return 1
    try:
        matches = compare_to_baseline(args.snapshot_dir, args.env, snapshot_file)
    except ValueError as exc:
        print(f"[baseline-check] {exc}", file=sys.stderr)
        return 2
    if matches:
        print(f"[baseline-check] OK — snapshot matches baseline for '{args.env}'.")
        return 0
    else:
        print(f"[baseline-check] DRIFT — snapshot does NOT match baseline for '{args.env}'.")
        return 1

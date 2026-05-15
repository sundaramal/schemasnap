"""cmd_snapshot_diff_chain: show a chain of diffs across consecutive snapshots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from schemasnap.snapshot import list_snapshots, load_snapshot
from schemasnap.diff import diff_snapshots
from schemasnap.report import diff_to_dict, render_text_report


def add_snapshot_diff_chain_subparsers(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = sub.add_parser(
        "diff-chain",
        help="Show diffs across consecutive snapshots for an environment.",
    )
    p.add_argument("--dir", required=True, help="Snapshot directory.")
    p.add_argument("--env", required=True, help="Environment name to filter snapshots.")
    p.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of consecutive pairs to diff (default: 5).",
    )
    p.add_argument(
        "--fmt",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_snapshot_diff_chain)


def _snapshots_for_env(snap_dir: Path, env: str) -> List[Path]:
    """Return snapshot files for *env* sorted oldest-first."""
    all_snaps = list_snapshots(snap_dir)
    filtered = [p for p in all_snaps if f"_{env}_" in p.name or p.name.startswith(f"{env}_")]
    return sorted(filtered)


def cmd_snapshot_diff_chain(args: argparse.Namespace) -> int:
    snap_dir = Path(args.dir)
    if not snap_dir.is_dir():
        print(f"[error] Directory not found: {snap_dir}")
        return 1

    snaps = _snapshots_for_env(snap_dir, args.env)
    if len(snaps) < 2:
        print(f"[error] Need at least 2 snapshots for env '{args.env}', found {len(snaps)}.")
        return 1

    pairs = list(zip(snaps, snaps[1:]))
    if args.limit > 0:
        pairs = pairs[-args.limit :]

    chain: list = []
    for older_path, newer_path in pairs:
        older = load_snapshot(older_path)
        newer = load_snapshot(newer_path)
        diff = diff_snapshots(older["schema"], newer["schema"])
        if args.fmt == "json":
            chain.append(
                {
                    "from": older_path.name,
                    "to": newer_path.name,
                    "diff": diff_to_dict(diff),
                }
            )
        else:
            print(f"\n--- {older_path.name}  →  {newer_path.name} ---")
            print(render_text_report(diff))

    if args.fmt == "json":
        print(json.dumps(chain, indent=2))

    return 0

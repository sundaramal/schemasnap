"""CLI sub-command: rename a snapshot file and update its internal metadata."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def add_snapshot_rename_subparsers(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "snapshot-rename",
        help="Rename a snapshot file and rewrite its environment metadata.",
    )
    p.add_argument("file", help="Path to the snapshot file to rename.")
    p.add_argument("new_env", help="New environment name to assign.")
    p.add_argument(
        "--dir",
        default="snapshots",
        help="Directory that holds snapshots (default: snapshots).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making changes.",
    )
    p.set_defaults(func=cmd_snapshot_rename)


def cmd_snapshot_rename(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"[error] snapshot not found: {src}")
        return 1

    try:
        data = json.loads(src.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[error] could not read snapshot: {exc}")
        return 1

    old_env = data.get("environment", "unknown")
    old_hash = data.get("schema_hash", "unknown")
    timestamp = data.get("captured_at", "unknown")

    # Build new filename mirroring the capture_snapshot convention:
    # <env>_<timestamp>_<hash>.json
    # Reuse the existing timestamp and hash so history is traceable.
    safe_ts = timestamp.replace(":", "-").replace(" ", "T")[:19]
    new_name = f"{args.new_env}_{safe_ts}_{old_hash[:8]}.json"
    dest_dir = Path(args.dir)
    dest = dest_dir / new_name

    data["environment"] = args.new_env

    if args.dry_run:
        print(f"[dry-run] would rename {src.name} -> {new_name}")
        print(f"[dry-run] environment: {old_env!r} -> {args.new_env!r}")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2))

    if src.resolve() != dest.resolve():
        src.unlink()

    print(f"Renamed {src.name} -> {new_name} (env: {old_env!r} -> {args.new_env!r})")
    return 0

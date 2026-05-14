"""CLI sub-command: annotate-diff

Attaches a free-text note to every snapshot file that participates in a
diff between two environments, recording *why* the diff was expected (or
unexpected).  The annotation is stored via schemasnap.annotation so it
appears in `annotation list` output as usual.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schemasnap.annotation import save_annotation, AnnotationEntry
from schemasnap.diff import diff_snapshots
from schemasnap.snapshot import load_snapshot
from schemasnap.audit_hooks import audit_compare


def add_annotate_diff_subparsers(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = sub.add_parser(
        "annotate-diff",
        help="Diff two snapshots and attach an annotation to both files.",
    )
    p.add_argument("snapshot_a", help="Path to the baseline snapshot file.")
    p.add_argument("snapshot_b", help="Path to the comparison snapshot file.")
    p.add_argument(
        "--note",
        required=True,
        help="Annotation text to attach to both snapshot files.",
    )
    p.add_argument(
        "--author",
        default="schemasnap",
        help="Author name recorded in the annotation (default: schemasnap).",
    )
    p.add_argument(
        "--annotations-dir",
        default=".",
        help="Directory where annotations.json is stored (default: current dir).",
    )
    p.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip writing an audit entry.",
    )
    p.set_defaults(func=cmd_annotate_diff)


def cmd_annotate_diff(args: argparse.Namespace) -> int:
    path_a = Path(args.snapshot_a)
    path_b = Path(args.snapshot_b)

    for p in (path_a, path_b):
        if not p.exists():
            print(f"ERROR: snapshot not found: {p}", file=sys.stderr)
            return 1

    snap_a = load_snapshot(path_a)
    snap_b = load_snapshot(path_b)

    diff = diff_snapshots(snap_a, snap_b)
    change_summary = diff.summary() if hasattr(diff, "summary") else str(diff)

    annotations_dir = Path(args.annotations_dir)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    for snap_path in (path_a, path_b):
        entry = AnnotationEntry(
            snapshot_file=str(snap_path),
            author=args.author,
            note=args.note,
        )
        save_annotation(annotations_dir, entry)

    if not args.no_audit:
        try:
            audit_compare(
                annotations_dir,
                env_a=snap_a.get("environment", str(path_a)),
                env_b=snap_b.get("environment", str(path_b)),
                has_changes=bool(diff.has_changes()),
            )
        except Exception:  # pragma: no cover
            pass

    print(f"Annotated both snapshots.")
    print(f"Diff summary: {change_summary}")
    return 0

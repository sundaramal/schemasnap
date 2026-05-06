"""Command-line interface for schemasnap compare operations."""

import argparse
import sys

from schemasnap.compare import compare_and_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schemasnap",
        description="Snapshot and diff database schemas across environments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare_parser = subparsers.add_parser(
        "compare", help="Compare schemas between two environments."
    )
    compare_parser.add_argument("source", help="Source environment name (e.g. staging)")
    compare_parser.add_argument("target", help="Target environment name (e.g. production)")
    compare_parser.add_argument(
        "--snapshot-dir",
        default="snapshots",
        help="Directory containing snapshots (default: snapshots)",
    )
    compare_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    compare_parser.add_argument(
        "--output",
        default=None,
        help="Write report to this file path instead of stdout",
    )

    return parser


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        result = compare_and_report(
            source_env=args.source,
            target_env=args.target,
            snapshot_dir=args.snapshot_dir,
            output_format=args.format,
            output_path=args.output,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.output:
        from schemasnap.report import render_text_report, render_json_report
        if args.format == "json":
            print(render_json_report(result.diff, args.source, args.target))
        else:
            print(render_text_report(result.diff, args.source, args.target))

    return 1 if result.has_changes else 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "compare":
        sys.exit(cmd_compare(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

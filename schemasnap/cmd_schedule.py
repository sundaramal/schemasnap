"""CLI subcommands for the schedule feature."""

import argparse
import logging

from schemasnap.schedule import ScheduleConfig, run_schedule
from schemasnap.notify import NotifyConfig, dispatch_notifications
from schemasnap.watch import WatchConfig

logger = logging.getLogger(__name__)


def add_schedule_subparsers(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the 'schedule' subcommand."""
    p = subparsers.add_parser(
        "schedule",
        help="Continuously capture snapshots on a fixed interval.",
    )
    p.add_argument("--db-url", required=True, help="Database connection URL.")
    p.add_argument("--env", required=True, help="Environment name (e.g. prod).")
    p.add_argument("--snapshot-dir", default="snapshots", help="Directory for snapshots.")
    p.add_argument("--interval", type=int, default=3600, help="Seconds between runs.")
    p.add_argument("--retention-days", type=int, default=30, help="Days to keep snapshots.")
    p.add_argument("--max-runs", type=int, default=None, help="Stop after N runs (testing).")
    p.add_argument("--slack-webhook", default=None, help="Slack webhook URL for drift alerts.")
    p.add_argument("--watch", action="store_true", help="Check for drift on each run.")
    p.set_defaults(func=cmd_schedule)


def cmd_schedule(args: argparse.Namespace) -> int:
    """Entry point for the 'schedule' subcommand."""
    watch_config: WatchConfig | None = None

    if args.watch:
        notify_cfg = None
        if args.slack_webhook:
            notify_cfg = NotifyConfig(slack_webhook_url=args.slack_webhook)

        def _alert(result):
            if notify_cfg and result.diff and result.diff.has_changes():
                dispatch_notifications(result, notify_cfg)

        watch_config = WatchConfig(alert_handlers=[_alert] if notify_cfg else [])

    config = ScheduleConfig(
        db_url=args.db_url,
        env=args.env,
        snapshot_dir=args.snapshot_dir,
        interval_seconds=args.interval,
        retention_days=args.retention_days,
        max_runs=args.max_runs,
        watch_config=watch_config,
    )

    try:
        run_schedule(config)
    except KeyboardInterrupt:
        logger.info("Schedule interrupted by user.")

    return 0

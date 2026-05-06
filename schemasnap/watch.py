"""Watch a database schema for changes and alert on drift."""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from schemasnap.snapshot import capture_snapshot, latest_snapshot, load_snapshot
from schemasnap.diff import diff_snapshots, has_changes
from schemasnap.report import render_text_report

logger = logging.getLogger(__name__)


@dataclass
class WatchConfig:
    snapshot_dir: str
    env: str
    interval_seconds: int = 60
    max_iterations: Optional[int] = None
    on_drift: Optional[Callable[[str], None]] = None
    alert_handlers: list = field(default_factory=list)


def default_drift_handler(report: str) -> None:
    """Default handler: log the drift report as a warning."""
    logger.warning("Schema drift detected:\n%s", report)


def watch_schema(schema: dict, config: WatchConfig) -> int:
    """Poll the schema at a fixed interval and report any drift.

    Returns the number of drift events detected.
    """
    handler = config.on_drift or default_drift_handler
    drift_count = 0
    iteration = 0

    # Capture the baseline snapshot
    baseline_path = capture_snapshot(schema, config.env, config.snapshot_dir)
    logger.info("Baseline snapshot saved: %s", baseline_path)

    while True:
        if config.max_iterations is not None and iteration >= config.max_iterations:
            break

        time.sleep(config.interval_seconds)
        iteration += 1

        new_path = capture_snapshot(schema, config.env, config.snapshot_dir)
        prev_path = latest_snapshot(
            config.snapshot_dir, config.env, exclude=new_path
        )

        if prev_path is None:
            logger.debug("No previous snapshot to compare against.")
            continue

        prev_snap = load_snapshot(prev_path)
        new_snap = load_snapshot(new_path)
        diff = diff_snapshots(prev_snap, new_snap)

        if has_changes(diff):
            drift_count += 1
            report = render_text_report(diff, config.env, config.env)
            handler(report)
            for extra_handler in config.alert_handlers:
                extra_handler(report)

    return drift_count

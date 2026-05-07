"""Scheduled snapshot capture with configurable intervals and retention."""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional
from datetime import datetime, timedelta

from schemasnap.snapshot import capture_snapshot, list_snapshots
from schemasnap.watch import WatchConfig, watch_schema

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for scheduled schema snapshot runs."""
    db_url: str
    env: str
    snapshot_dir: str
    interval_seconds: int = 3600
    retention_days: int = 30
    watch_config: Optional[WatchConfig] = None
    on_tick: Optional[Callable[[str, int], None]] = None
    max_runs: Optional[int] = None


def prune_old_snapshots(snapshot_dir: str, env: str, retention_days: int) -> int:
    """Delete snapshots older than retention_days. Returns count of pruned files."""
    import os
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    pruned = 0
    for snap_path in list_snapshots(snapshot_dir, env):
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(snap_path))
            if mtime < cutoff:
                os.remove(snap_path)
                logger.info("Pruned old snapshot: %s", snap_path)
                pruned += 1
        except OSError as exc:
            logger.warning("Could not prune %s: %s", snap_path, exc)
    return pruned


def run_schedule(config: ScheduleConfig) -> None:
    """Run snapshot capture on a fixed interval until max_runs is reached."""
    runs = 0
    logger.info(
        "Starting scheduled snapshots for env=%s every %ds",
        config.env, config.interval_seconds,
    )
    while config.max_runs is None or runs < config.max_runs:
        logger.info("Run #%d: capturing snapshot for env=%s", runs + 1, config.env)
        try:
            snap_path = capture_snapshot(
                config.db_url, config.env, config.snapshot_dir
            )
            logger.info("Snapshot saved: %s", snap_path)

            if config.watch_config:
                drift_count = watch_schema(
                    config.db_url, config.env,
                    config.snapshot_dir, config.watch_config,
                )
                logger.info("Drift check result: %d changes", drift_count)

            pruned = prune_old_snapshots(
                config.snapshot_dir, config.env, config.retention_days
            )
            if pruned:
                logger.info("Pruned %d old snapshot(s)", pruned)

            if config.on_tick:
                config.on_tick(snap_path, runs + 1)

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Scheduled run failed: %s", exc)

        runs += 1
        if config.max_runs is None or runs < config.max_runs:
            time.sleep(config.interval_seconds)

    logger.info("Scheduled run complete after %d iterations.", runs)

"""Audit retention helper — prune rows older than a threshold.

The app NEVER silently prunes. Operators call this on a cadence they
control (cron, manual run, staging script). The CLI entrypoint lives
in `scripts/audit_retention.py`.

Callable from code AND from the command line so tests can exercise the
logic without shelling out.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from app.config import settings
from app.db import fetch_one, transaction


def prune_audit_events(
    retention_days: Optional[int] = None, dry_run: bool = False
) -> dict:
    """Delete `security_audit_events` rows older than `retention_days`.

    Returns a summary dict (also logged). Safe to call repeatedly.
    """
    days = retention_days if retention_days is not None else settings.audit_retention_days
    if days <= 0:
        return {
            "status": "disabled",
            "retention_days": days,
            "cutoff": None,
            "matched": 0,
            "deleted": 0,
            "dry_run": dry_run,
        }

    cutoff = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    count_row = fetch_one(
        "SELECT COUNT(*) AS n FROM security_audit_events WHERE created_at < :cutoff",
        {"cutoff": cutoff_iso},
    )
    matched = int(count_row["n"]) if count_row else 0

    deleted = 0
    if not dry_run and matched:
        with transaction() as conn:
            result = conn.execute(
                text("DELETE FROM security_audit_events WHERE created_at < :cutoff"),
                {"cutoff": cutoff_iso},
            )
            deleted = result.rowcount or matched

    return {
        "status": "ok",
        "retention_days": days,
        "cutoff": cutoff_iso,
        "matched": matched,
        "deleted": deleted,
        "dry_run": dry_run,
    }

"""Operator CLI for pruning `security_audit_events`.

Usage:
    python scripts/audit_retention.py                 # use CHARTNAV_AUDIT_RETENTION_DAYS
    python scripts/audit_retention.py --days 90       # explicit threshold
    python scripts/audit_retention.py --dry-run       # report only, no delete

Requires DATABASE_URL in the environment (same contract as the API).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make `app.*` importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune old security_audit_events rows.")
    parser.add_argument("--days", type=int, default=None,
                        help="retention threshold in days (default: CHARTNAV_AUDIT_RETENTION_DAYS)")
    parser.add_argument("--dry-run", action="store_true", help="report without deleting")
    args = parser.parse_args()

    # Import AFTER parsing args so `--help` doesn't require DATABASE_URL.
    if not os.environ.get("DATABASE_URL"):
        # Fall back to the API's default SQLite for local dev.
        os.environ.setdefault(
            "DATABASE_URL",
            f"sqlite:///{Path(__file__).resolve().parents[1] / 'apps/api/chartnav.db'}",
        )

    from app.retention import prune_audit_events  # noqa: E402

    summary = prune_audit_events(retention_days=args.days, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

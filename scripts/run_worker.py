#!/usr/bin/env python3
"""ChartNav background worker (phase 23).

Minimal CLI that calls the same `app.services.worker` primitives the
HTTP endpoints expose. Intended for cron / systemd-timer / supervised
process use.

Usage:
    scripts/run_worker.py --once           # one tick, exit
    scripts/run_worker.py --drain          # drain the queue, exit
    scripts/run_worker.py --loop [--interval 5]  # loop forever
    scripts/run_worker.py --requeue-stale  # recover stale claims, exit

Exits non-zero on failure, zero on success. A tick that produced a
`failed` row is NOT a CLI failure — the row state is the honest
result; cron/supervisor should keep running.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Make `app` importable when this script runs from repo root.
_API_DIR = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(_API_DIR))


def _emit(event: dict) -> None:
    """JSON-per-line output so ops can tail + jq."""
    sys.stdout.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ChartNav worker")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--drain", action="store_true")
    mode.add_argument("--loop", action="store_true")
    mode.add_argument("--requeue-stale", action="store_true")
    parser.add_argument(
        "--interval", type=float, default=5.0,
        help="seconds between ticks in --loop mode (default 5)",
    )
    parser.add_argument(
        "--max-ticks", type=int, default=100,
        help="ceiling for --drain mode (default 100)",
    )
    args = parser.parse_args(argv)

    os.chdir(str(_API_DIR))
    from app.services import worker as _worker

    if args.once:
        tick = _worker.run_one()
        if tick is None:
            _emit({"event": "queue_empty"})
        else:
            _emit({
                "event": "tick",
                "input_id": tick.input_id,
                "status": tick.status,
                "ingestion_error": tick.ingestion_error,
            })
        return 0

    if args.drain:
        summary = _worker.run_until_empty(max_ticks=args.max_ticks)
        _emit({"event": "drain_complete", **summary})
        return 0

    if args.requeue_stale:
        recovered = _worker.requeue_stale_claims()
        _emit({"event": "requeue_stale", "recovered": recovered})
        return 0

    if args.loop:
        _emit({"event": "loop_start", "interval": args.interval})
        try:
            while True:
                tick = _worker.run_one()
                if tick is None:
                    time.sleep(args.interval)
                    continue
                _emit({
                    "event": "tick",
                    "input_id": tick.input_id,
                    "status": tick.status,
                    "ingestion_error": tick.ingestion_error,
                })
        except KeyboardInterrupt:
            _emit({"event": "loop_interrupted"})
            return 0

    return 1  # unreachable — argparse guarantees mode


if __name__ == "__main__":
    sys.exit(main())

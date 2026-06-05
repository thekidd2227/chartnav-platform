#!/usr/bin/env python3
"""Verify that the seeded demo DB matches the invariants the buyer demo relies on.

Read-only. Works against the local SQLite dev DB directly (no API needed).
Exit 0 if all invariants hold, 1 if any fail.

Usage:
    python3 scripts/verify_seed_invariants.py [--db apps/api/chartnav.db]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO / "apps/api" / "chartnav.db"

CHECKS: list[tuple[str, str, list, object]] = [
    (
        "patient PT-1001 (Morgan Lee) exists",
        "SELECT COUNT(*) FROM patients WHERE patient_identifier='PT-1001'",
        [],
        lambda r: r[0][0] >= 1,
    ),
    (
        "encounter 1 belongs to PT-1001 in org 1",
        "SELECT organization_id, patient_identifier FROM encounters WHERE id=1",
        [],
        lambda r: len(r) == 1 and r[0][0] == 1 and r[0][1] == "PT-1001",
    ),
    (
        "encounter 1 status is in_progress",
        "SELECT status FROM encounters WHERE id=1",
        [],
        lambda r: len(r) == 1 and r[0][0] == "in_progress",
    ),
    (
        "clinician clin@chartnav.local exists with role=clinician in org 1",
        "SELECT role, organization_id, is_active FROM users WHERE email='clin@chartnav.local'",
        [],
        lambda r: len(r) == 1 and r[0][0] == "clinician" and r[0][1] == 1 and r[0][2],
    ),
    (
        "admin admin@chartnav.local exists with role=admin in org 1",
        "SELECT role, organization_id FROM users WHERE email='admin@chartnav.local'",
        [],
        lambda r: len(r) == 1 and r[0][0] == "admin" and r[0][1] == 1,
    ),
    (
        "technician tech@chartnav.local exists in org 1",
        "SELECT role, organization_id FROM users WHERE email='tech@chartnav.local'",
        [],
        lambda r: len(r) == 1 and r[0][0] == "technician" and r[0][1] == 1,
    ),
    (
        "organization 1 is demo-eye-clinic",
        "SELECT slug FROM organizations WHERE id=1",
        [],
        lambda r: len(r) == 1 and r[0][0] == "demo-eye-clinic",
    ),
    (
        "provider Dr. Carter exists in org 1",
        "SELECT display_name FROM providers WHERE organization_id=1 AND display_name='Dr. Carter'",
        [],
        lambda r: len(r) == 1,
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify demo seed invariants")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite DB")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"FAIL: database not found at {db_path}")
        print(f"      Run: make reset-db   (from {REPO})")
        return 1

    con = sqlite3.connect(str(db_path))
    passed = 0
    failed = 0

    for label, sql, params, check_fn in CHECKS:
        try:
            rows = con.execute(sql, params).fetchall()
            if check_fn(rows):
                print(f"  ok   {label}")
                passed += 1
            else:
                print(f"  FAIL {label}  (query returned {rows})")
                failed += 1
        except Exception as e:
            print(f"  FAIL {label}  ({e})")
            failed += 1

    con.close()
    print()
    print(f"Seed invariants: {passed} pass / {failed} fail")
    if failed > 0:
        print("Recovery: bash scripts/reset_demo_state.sh")
        return 1
    print("Seed state is demo-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

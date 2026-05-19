#!/usr/bin/env bash
# scripts/reset_phase24b_retina_demo.sh — Phase 24C demo reset.
#
# Why this exists:
#   Phase 24B shipped the Morgan Lee retina follow-up wedge as a
#   deterministic fake-data orchestration that exercises every clinic
#   lane (front desk → tech workup → imaging review → MD encounter →
#   documentation → sign-off → internal follow-up). Phase 24C
#   packages that wedge for repeatable sales demos. This script is
#   the canonical pre-call reset: one command, deterministic state,
#   fake data only.
#
# What it does:
#   1. Refuses to run against anything that isn't the local SQLite
#      dev DB (no staging, no controlled-pilot, no production).
#   2. Exports `CHARTNAV_SEED_PHASE_24B_WEDGE=1` so the seed plants
#      the Morgan Lee retina follow-up wedge rows.
#   3. Drops + re-creates the local dev DB by delegating to
#      `make reset-db` (alembic migrate + idempotent seed via
#      `apps/api/scripts_seed.py`).
#   4. Verifies the wedge rows are present (7 queue items + retina
#      tracking + 2 imaging studies + 2 imaging files + 1 action
#      item) and prints a one-line PASS/FAIL line per check.
#   5. Prints the recommended browser-side localStorage cleanup
#      snippet (matches `scripts/reset_demo_state.sh`) so the
#      operator can paste it into DevTools once.
#   6. Prints the buyer-safety reminders: fake-data only, no real
#      PHI, no autonomous interpretation, no claims-submission, no
#      patient messaging, no device integrations.
#
# What this script does NOT do:
#   - does not modify production data;
#   - does not call the network;
#   - does not print secrets;
#   - does not approve real-PHI deployment (that gate lives in
#     `docs/security/chartnav-real-phi-go-live-gate.md`);
#   - does not generate media;
#   - does not publish the live website.
#
# Usage:
#   bash scripts/reset_phase24b_retina_demo.sh
# Exit codes:
#   0  reset completed; wedge present
#   1  refused (DATABASE_URL not local SQLite, or production hint)
#   2  reset/seed failed
#   3  wedge verification failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

EXPECTED_PREFIX="sqlite:///"
ACTIVE_URL="${DATABASE_URL:-}"

echo "ChartNav Phase 24C demo reset — Morgan Lee retina follow-up."
echo "Fake demo data only. No real PHI. No device integrations."
echo

# 1. Production / staging guard.
if [ -n "$ACTIVE_URL" ] && [[ "$ACTIVE_URL" != "$EXPECTED_PREFIX"* ]]; then
  echo "REFUSED: DATABASE_URL is set to '$ACTIVE_URL'." >&2
  echo "         This script only resets the local SQLite dev DB." >&2
  echo "         Unset DATABASE_URL or point it at sqlite:///<path> to continue." >&2
  exit 1
fi

# Belt-and-suspenders: refuse if any obvious production hint is set.
for guard_var in \
  CHARTNAV_ENV \
  CHARTNAV_DEPLOY_ENV \
  CHARTNAV_PROFILE; do
  v="${!guard_var:-}"
  case "$(printf '%s' "$v" | tr 'A-Z' 'a-z')" in
    prod|production|staging|stage|live|controlled-pilot|pilot)
      echo "REFUSED: $guard_var='$v' looks like a non-dev environment." >&2
      echo "         This script is for local fake-data demo only." >&2
      exit 1
      ;;
  esac
done

# 2. Enable the Phase 24B wedge gate for the seed.
export CHARTNAV_SEED_PHASE_24B_WEDGE=1

# Resolve the Python interpreter: prefer the project venv, fall back to
# system python. The demo host may not have the venv bootstrapped.
VENV_PY="$REPO_ROOT/apps/api/.venv/bin/python"
if [ -x "$VENV_PY" ]; then
  PY="$VENV_PY"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "FAILED — neither apps/api/.venv/bin/python nor python3 found." >&2
  exit 2
fi

DEV_DB="$REPO_ROOT/apps/api/chartnav.db"

echo "1. Resetting the local dev DB (alembic migrate + seed)…"
echo "   python:  $PY"
echo "   dev db:  $DEV_DB"
rm -f "$DEV_DB"
(
  cd "$REPO_ROOT/apps/api"
  "$PY" -m alembic upgrade head >/dev/null
  "$PY" scripts_seed.py >/dev/null
) || {
  echo "FAILED — migrate or seed returned non-zero." >&2
  exit 2
}
echo "   ok — dev DB rebuilt with Phase 24B wedge enabled."
echo

if [ ! -f "$DEV_DB" ]; then
  echo "FAILED — expected dev DB at $DEV_DB but file is missing." >&2
  exit 2
fi

echo "2. Verifying Phase 24B wedge rows in $DEV_DB"
# Use Python's sqlite3 module so the script does not depend on the
# `sqlite3` CLI binary being installed on the demo host. Temporarily
# disable `set -e` so we can read the verifier's exit code below.
set +e
"$PY" - "$DEV_DB" <<'PY'
import sqlite3, sys
db = sys.argv[1]
conn = sqlite3.connect(db)
checks = [
    ("Morgan Lee patient row (PT-1001)", 1,
     "SELECT COUNT(*) FROM patients WHERE patient_identifier='PT-1001'"),
    ("Dr. Carter provider row", 1,
     "SELECT COUNT(*) FROM providers WHERE display_name='Dr. Carter'"),
    ("Phase 24B wedge queue items (7 lanes)", 7,
     "SELECT COUNT(*) FROM work_queue_items WHERE source='phase_24b_wedge'"),
    ("Wedge queue items have assigned_user_id (role bind)", 7,
     "SELECT COUNT(*) FROM work_queue_items WHERE source='phase_24b_wedge' AND assigned_user_id IS NOT NULL"),
    ("Retina tracking row (diabetic retinopathy / 4 weeks)", 1,
     "SELECT COUNT(*) FROM retina_tracking WHERE follow_up_interval='4 weeks'"),
    ("Imaging studies: OCT macula + fundus photo", 2,
     "SELECT COUNT(*) FROM imaging_studies WHERE modality IN ('oct_macula','fundus_photo')"),
    ("Imaging files use placeholder:// storage URIs", 2,
     "SELECT COUNT(*) FROM imaging_files WHERE storage_uri LIKE 'placeholder://%'"),
    ("Internal follow-up action item", 1,
     "SELECT COUNT(*) FROM provider_action_items WHERE source_type='phase_24b_wedge'"),
]
failures = 0
for label, expected, sql in checks:
    try:
        actual = conn.execute(sql).fetchone()[0]
    except Exception as e:
        print(f"   ERROR    {label}: {e}")
        failures += 1
        continue
    if actual >= expected:
        print(f"   ok       {label} ({actual})")
    else:
        print(f"   MISSING  {label} (expected >= {expected}, got {actual})")
        failures += 1
sys.exit(3 if failures else 0)
PY
WEDGE_VERIFY_RC=$?
set -e
echo
if [ "$WEDGE_VERIFY_RC" -ne 0 ]; then
  echo "FAILED — Phase 24B wedge row(s) missing." >&2
  echo "         Check that scripts_seed.py runs cleanly with" >&2
  echo "         CHARTNAV_SEED_PHASE_24B_WEDGE=1 set." >&2
  exit 3
fi
echo "   All Phase 24B wedge rows present."
echo

# 4. Browser-side cleanup.
echo "3. Clearing browser-side demo state."
echo "   Paste the following into the browser DevTools console once:"
echo
cat <<'BROWSER'
   try {
     localStorage.removeItem("chartnav.demoStep");
     localStorage.removeItem("chartnav.demoMode");
     localStorage.removeItem("chartnav.devIdentity");
     console.info("ChartNav Phase 24C demo state cleared.");
   } catch (e) { console.warn("localStorage cleanup skipped", e); }
BROWSER
echo

# 5. Buyer-safety reminders.
echo "4. Buyer-safety reminders (read once before every demo):"
echo "   - Org slug:   demo-eye-clinic (fake)."
echo "   - Patient:    PT-1001 Morgan Lee (fake; no real PHI)."
echo "   - Provider:   Dr. Carter (fake NPI for demo only)."
echo "   - Imaging:    metadata only; placeholder:// storage URIs;"
echo "                 no binary upload, no device integration."
echo "   - Workflow:   ChartNav coordinates; the provider decides."
echo "   - Forbidden:  autonomous diagnosis, OCT/fundus interpretation,"
echo "                 disease grading, treatment recommendation,"
echo "                 automatic orders/referrals/coding/billing/claims,"
echo "                 patient messaging, HIPAA-compliant or"
echo "                 certified-EHR positioning, EHR replacement."
echo "   - Real PHI:   blocked by default. A controlled real-PHI pilot"
echo "                 requires BAA + practice security review + Phase 23"
echo "                 readiness gate."
echo
echo "Phase 24C demo reset complete."

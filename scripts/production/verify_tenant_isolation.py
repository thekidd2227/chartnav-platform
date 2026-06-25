#!/usr/bin/env python3
"""Static guard: patient-scoped endpoints must enforce organization scoping.

This is a defense-in-depth lint, not a substitute for the runtime tenant-
isolation tests (tests/test_eye_diagrams.py::TestOrgIsolation,
tests/test_patient_chart_foundation.py cross-org cases). It asserts that the
patient/eye-diagram data-access helpers scope by caller.organization_id and
return a non-disclosing 404, so a reviewer can catch a regression that drops
org scoping before it ships. Stdlib only.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = os.path.join(ROOT, "apps", "api", "app")
ROUTES = os.path.join(API, "api", "routes.py")
EYE = os.path.join(API, "api", "eye_diagrams.py")
ARTIFACTS_SVC = os.path.join(API, "services", "chart_artifacts.py")


def main() -> int:
    errs: list[str] = []
    routes = []

    # ── routes.py: patient detail / encounters / chart-sections ──────────
    if not os.path.exists(ROUTES):
        errs.append(f"routes.py not found at {ROUTES}")
    else:
        src = open(ROUTES, encoding="utf-8").read()
        if "def _load_patient_for_caller" not in src:
            errs.append("routes.py missing _load_patient_for_caller (org-scoped patient loader)")
        else:
            block = src.split("def _load_patient_for_caller", 1)[1][:600]
            if "caller.organization_id" not in block:
                errs.append("_load_patient_for_caller does not compare caller.organization_id")
            if "patient_not_found" not in block or "404" not in block:
                errs.append("_load_patient_for_caller does not raise a non-disclosing 404")
        routes = re.findall(r'@router\.\w+\("(/patients/\{patient_id:int\}[^"]*)"', src)
        if not routes:
            errs.append("no /patients/{id} routes found in routes.py — unexpected")
        # Each patient-scoped handler must resolve via the org-scoped loader.
        if src.count("_load_patient_for_caller") < 2:
            errs.append("_load_patient_for_caller used too few times to cover the patient routes")

    # ── eye_diagrams.py: canonical eye-diagram router (org-scoped) ───────
    if not os.path.exists(EYE):
        errs.append("eye_diagrams.py not found (canonical eye-diagram router)")
    else:
        esrc = open(EYE, encoding="utf-8").read()
        if "def _resolve_patient_in_org" not in esrc:
            errs.append("eye_diagrams.py missing _resolve_patient_in_org (org-scoped lookup)")
        else:
            block = esrc.split("def _resolve_patient_in_org", 1)[1][:400]
            if "caller.organization_id" not in block:
                errs.append("_resolve_patient_in_org does not scope by caller.organization_id")
            if "patient_not_found" not in block or "404" not in block:
                errs.append("_resolve_patient_in_org does not raise a non-disclosing 404")
        eye_routes = re.findall(r'@router\.\w+\("(/patients/\{patient_id\}[^"]*)"', esrc)
        routes += eye_routes
        if not eye_routes:
            errs.append("no /patients/{id}/eye-diagrams routes found in eye_diagrams.py")

    # ── chart_artifacts service: data access filters by organization_id ──
    if not os.path.exists(ARTIFACTS_SVC):
        errs.append("services/chart_artifacts.py not found")
    else:
        ssrc = open(ARTIFACTS_SVC, encoding="utf-8").read()
        if "organization_id" not in ssrc:
            errs.append("chart_artifacts service does not reference organization_id")
        if "def get_for_patient" not in ssrc:
            errs.append("chart_artifacts service missing get_for_patient (scoped read)")

    if errs:
        print("❌ tenant-isolation static guard FAILED:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"✅ tenant-isolation guard passed ({len(routes)} patient-scoped routes; "
          "org-scoped loaders + non-disclosing 404 present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

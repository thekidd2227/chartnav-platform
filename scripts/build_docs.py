"""Build consolidated HTML + PDF for ChartNav from docs/build + docs/diagrams.

Reproducible from repo: paths are resolved relative to the script so the
same command works locally and in CI. PDF rendering prefers headless
Chromium; set `CHARTNAV_PDF_BROWSER` to force a specific binary.
Falls back to reportlab (plain-text PDF) if no browser is available.

Run:
    python scripts/build_docs.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "docs/build"
DIAGR = REPO / "docs/diagrams"
OUT_HTML = REPO / "docs/final/chartnav-workflow-state-machine-build.html"
OUT_PDF = REPO / "docs/final/chartnav-workflow-state-machine-build.pdf"

SECTIONS = [
    ("Executive summary", None),
    ("01 — Current state", BUILD / "01-current-state.md"),
    ("02 — Workflow state machine", BUILD / "02-workflow-state-machine.md"),
    ("03 — API endpoints", BUILD / "03-api-endpoints.md"),
    ("04 — Data model", BUILD / "04-data-model.md"),
    ("05 — Build log", BUILD / "05-build-log.md"),
    ("06 — Known gaps + verification matrix", BUILD / "06-known-gaps.md"),
    ("07 — Auth, org scoping, RBAC", BUILD / "07-auth-and-scoping.md"),
    ("08 — Test strategy", BUILD / "08-test-strategy.md"),
    ("09 — CI & deploy hardening", BUILD / "09-ci-and-deploy-hardening.md"),
    ("10 — Doc artifact pipeline", BUILD / "10-doc-artifact-pipeline.md"),
    ("11 — Production-auth seam", BUILD / "11-production-auth-seam.md"),
    ("12 — Runtime config", BUILD / "12-runtime-config.md"),
    ("13 — Deploy target", BUILD / "13-deploy-target.md"),
    ("14 — Postgres parity", BUILD / "14-postgres-parity.md"),
    ("15 — Frontend integration", BUILD / "15-frontend-integration.md"),
    ("16 — Frontend test strategy", BUILD / "16-frontend-test-strategy.md"),
    ("17 — E2E & release", BUILD / "17-e2e-and-release.md"),
    ("18 — Operational hardening", BUILD / "18-operational-hardening.md"),
    ("19 — Staging deployment", BUILD / "19-staging-deployment.md"),
    ("20 — Observability", BUILD / "20-observability.md"),
    ("21 — Staging runbook", BUILD / "21-staging-runbook.md"),
    ("22 — Admin governance", BUILD / "22-admin-governance.md"),
    ("23 — Operator control plane", BUILD / "23-operator-control-plane.md"),
    ("24 — Invitations & governance", BUILD / "24-invitations-and-governance.md"),
    ("25 — Enterprise quality & compliance", BUILD / "25-enterprise-quality-and-compliance.md"),
    ("26 — Platform mode & interoperability", BUILD / "26-platform-mode-and-interoperability.md"),
    ("27 — Adoption & implementation model", BUILD / "27-adoption-and-implementation-model.md"),
    ("Diagram — System architecture", DIAGR / "system-architecture.md"),
    ("Diagram — Encounter status machine", DIAGR / "encounter-status-machine.md"),
    ("Diagram — ER", DIAGR / "er-diagram.md"),
    ("Diagram — API / data flow", DIAGR / "api-data-flow.md"),
]

EXEC_SUMMARY = """
This document consolidates **all** ChartNav backend phases delivered to
date.

**Phase 1 — Workflow spine.** Alembic migration `a1b2c3d4e5f6` introduced `encounters` and `workflow_events` tables with FKs and indexes. Six encounter endpoints. Idempotent seed.

**Phase 2 — State machine + filtering.** `POST /encounters/{id}/status` enforces explicit forward + rework edges. `GET /encounters` accepts `organization_id`, `location_id`, `status`, `provider_name` filters.

**Phase 3 — Dev auth + org scoping.** `apps/api/app/auth.py` resolves the caller from `X-User-Email`. Every encounter route became org-scoped: cross-org reads return 404, cross-org body/query assertions 403.

**Phase 4 — RBAC + full scoping + tests.** `apps/api/app/authz.py` introduces `admin` / `clinician` / `reviewer` roles and per-edge transition rules. `/organizations`, `/locations`, `/users` are now authenticated and scoped. `{error_code, reason}` envelope is standardized. 25-test pytest suite covers auth, scoping, RBAC, state-machine invariants.

**Phase 5 — CI + runtime hardening.** GitHub Actions workflow runs install + Alembic upgrade on an isolated CI DB + idempotent seed + pytest + live smoke. A separate `docs` job regenerates the final HTML/PDF. Root `Makefile`, `apps/api/scripts/smoke.sh`, and `scripts/build_docs.py` codify the local verification + doc-build paths.

**Phase 6 — Production seam + deploy target + Postgres parity.** DB layer moved to SQLAlchemy Core. `apps/api/app/config.py` centralizes env. `auth.py` gained a bearer stub that returns 501 honestly. Dockerfile hardened, `docker-compose.prod.yml` + `scripts/pg_verify.sh` + `backend-postgres` CI job land.

**Phase 7 — Frontend workflow UI.** Typed API client + identity seam + full two-pane workflow console (list + filters + detail + timeline + role-aware actions). Error banners surface the backend envelope verbatim.

**Phase 8 — Create UI + frontend tests + frontend CI.** Admin/clinician can create encounters through a modal; Vitest + Testing Library harness (12 tests) locks the UI down; dedicated `frontend` CI job runs typecheck + tests + build on every push/PR.

**Phase 9 — Playwright E2E + release pipeline.** Playwright boots backend + frontend together, 8 Chromium scenarios, new `e2e` CI job. `release.yml` workflow on `v*.*.*` tags: GHCR push + release bundle + GitHub Release with tarballs and MANIFEST.

**Phase 10 — Real JWT bearer auth + operational hardening.** Real PyJWT validation against a JWKS URL (signature + iss + aud + exp + claim mapping). Request correlation (`X-Request-ID`), structured JSON logs, `security_audit_events` table (`b2c3d4e5f6a7`), CORS driven by config, per-process rate limiter.

**Phase 11 — Staging deployment + observability.** New `/ready` + `/metrics` surfaces. Pinned-image staging compose + runbook scripts + release-bundled staging tarball. `deploy-config` CI job validates compose + shellcheck.

**Phase 12 — Admin governance + event discipline + pagination.** DB CHECK on `users.role`, `is_active` soft-delete flags, admin CRUD for users + locations, `EVENT_SCHEMAS` allowlist, encounter pagination via `limit`/`offset` + `X-Total-Count`. `AdminPanel` modal with Users + Locations tabs.

**Phase 13 — Operator control plane.** `GET/PATCH /organization` + `GET /security-audit-events` + admin panel Organization & Audit tabs. `invited_at` stamping on admin create.

**Phase 14 — Invitations, settings schema, audit export, event hardening, bulk users.** Migration `e5f6a7b8c9d0` adds `invitation_token_hash` (sha256-only), `invitation_expires_at`, `invitation_accepted_at`. New endpoints: `POST /users/{id}/invite`, `POST /invites/accept`, `POST /users/bulk`, `GET /security-audit-events/export`. Organization settings becomes a typed `OrganizationSettings` pydantic model (extra=forbid) with dedicated fields + an `extensions` forward-compat bucket. Event payloads enforce per-type value discipline (status enums, non-empty strings, non-negative ints). Admin UI adds per-user **Invite** with a one-shot raw-token banner, a **Bulk import…** dialog, an **Export CSV** button on the audit tab, typed inputs on the Organization tab, and a minimal `/invite?invite=<token>` accept screen. Suites grow to **110 pytest / 25 Vitest / 12 Playwright**.

**Phase 15 — Enterprise quality + compliance.** Five real enterprise-credibility guarantees land together. (1) **Accessibility baseline**: `@axe-core/playwright` over Chromium, 5 scans covering app shell + encounter list/detail + admin users/audit + invite accept; `serious`/`critical` findings are blocking; established fixes land `aria-label` on the event-type and inline role `<select>`s. (2) **Visual regression baseline**: 4 Playwright screenshots (encounter list, admin users, admin audit, invite accept) at 1280×820 with animations disabled and `maxDiffPixelRatio: 0.02`; macOS baselines committed for local dev; CI intentionally skips because Chromium renders differently on Linux (documented gap). (3) **Admin list scaling**: `GET /users` and `GET /locations` gain `limit`, `offset`, `q`, and (users) `role` query params with `X-Total-Count`/`X-Limit`/`X-Offset` headers; UI adds search + Prev/Next pager (25/page) on both tabs. (4) **Feature-flag consumption**: `organization.settings.feature_flags.audit_export` and `.bulk_import` now actually hide the **Export CSV** / **Bulk import…** buttons; defaults stay `true`; documented as a UX toggle, not a security control. (5) **Release compliance signals**: `scripts/sbom.py` captures project + git sha/tag/dirty + image tag + `pip list` + `npm list`; `scripts/release_build.sh` also emits `chartnav-api-<v>.digest.txt` via `docker image inspect`; both are attached to GitHub Releases and included in `MANIFEST.txt`. (6) **Audit retention scaffolding**: `apps/api/app/retention.py::prune_audit_events` + `scripts/audit_retention.py` CLI + `CHARTNAV_AUDIT_RETENTION_DAYS` env (default `0` = never); the app never silently prunes. Suites grow to **118 pytest / 28 Vitest / 21 Playwright** (12 workflow + 5 a11y + 4 visual-local).

**Phase 16 — Platform mode & interoperability (this phase).** ChartNav is now explicitly two products in one — a standalone lightweight EMR/EHR **and** an integration-first overlay on top of an existing EHR/EMR. The shape is architectural, not a feature flag bolted on. Four real changes landed together: (1) **Operating modes**: `CHARTNAV_PLATFORM_MODE` ∈ {`standalone`, `integrated_readthrough`, `integrated_writethrough`}, validated at import time; `standalone` pins the adapter to `native`, `integrated_*` defaults to `stub`. (2) **Adapter boundary** — `app/integrations/base.py::ClinicalSystemAdapter` protocol (`fetch_patient`, `search_patients`, `fetch_encounter`, `update_encounter_status`, `write_note`, `sync_reference_data`, `info`), `AdapterError` / `AdapterNotSupported`, `SourceOfTruth` enum. Ships two honest implementations: `NativeChartNavAdapter` (persists to the ChartNav DB via the same SA Core surface the HTTP routes use, refuses patient ops until a native `patients` table lands), and `StubClinicalSystemAdapter` (canned reads, write-through records writes to an in-process list, read-through raises `AdapterNotSupported`). Vendor adapters plug into a mutable `_VENDOR_ADAPTERS` registry via `register_vendor_adapter(key, factory)` — no decorator magic, grep-able. (3) **HTTP surface** — `GET /platform` (any authenticated caller) returns mode + adapter key + display name + supports-* flags + source-of-truth map. No secret leakage (asserted). (4) **Frontend awareness** — `api.ts` gains `getPlatform` + types; `AdminPanel` fetches `/platform` on mount and renders a platform banner above the tabs on every admin view. CI fallout from phase 15 was repaired in the same commit window: migration `c3d4e5f6a7b8` switched from `sa.text("1")` (Postgres-incompatible BOOLEAN default) to `sa.text("true")`, and vitest was downgraded to `^3.2.4` + lockfile regenerated to fix `npm ci` on Linux/Node 20 (Vitest 4 had transitively pulled rolldown + Vite 8 + esbuild 0.28, leaving the lockfile incomplete for non-mac platforms). Suites grow to **131 pytest** / **30 Vitest** / 21 Playwright. `GET /platform` is the only new endpoint.

Preserved untouched: `/health`, `/`, SQLite dev workflow, state machine + filtering surface, workflow_events model, existing endpoint contracts.
"""


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    in_table = False
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    def inline(s: str) -> str:
        import html
        import re
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return s

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            if not in_code:
                close_list(); close_table()
                in_code = True
                code_lang = line[3:].strip()
                if code_lang == "mermaid":
                    out.append('<div class="mermaid">')
                else:
                    out.append(f'<pre class="code lang-{code_lang}"><code>')
            else:
                if code_lang == "mermaid":
                    out.append("</div>")
                else:
                    out.append("</code></pre>")
                in_code = False
                code_lang = ""
            i += 1
            continue
        if in_code:
            if code_lang == "mermaid":
                out.append(line)
            else:
                import html
                out.append(html.escape(line))
            i += 1
            continue

        stripped = line.strip()
        if stripped.startswith("#"):
            close_list(); close_table()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            level = min(level, 6)
            out.append(f"<h{level}>{inline(text)}</h{level}>")
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and set(
            lines[i + 1].strip().replace("|", "").replace(":", "").replace("-", "").strip()
        ) == set():
            close_list()
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append('<table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in headers) + "</tr></thead><tbody>")
            i += 2
            in_table = True
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            close_table()
            continue

        if stripped.startswith("- "):
            close_table()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
            i += 1
            continue

        if not stripped:
            close_list(); close_table()
            i += 1
            continue

        close_list(); close_table()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_list(); close_table()
    return "\n".join(out)


def build_html() -> str:
    body_parts: list[str] = []
    toc: list[str] = []
    for idx, (title, path) in enumerate(SECTIONS, start=1):
        anchor = f"sec-{idx}"
        toc.append(f'<li><a href="#{anchor}">{title}</a></li>')
        body_parts.append(f'<section id="{anchor}"><h2>{title}</h2>')
        if path is None:
            body_parts.append(md_to_html(EXEC_SUMMARY))
        else:
            if not path.exists():
                body_parts.append(f"<p><em>missing: {path.relative_to(REPO)}</em></p>")
            else:
                body_parts.append(md_to_html(path.read_text()))
        body_parts.append("</section>")
    body = "\n".join(body_parts)
    toc_html = "<ol>" + "".join(toc) + "</ol>"

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>ChartNav — Consolidated Build</title>
<style>
  :root {{ --fg:#0F172A; --muted:#64748B; --line:#E5E7EB; --bg:#ffffff; --code:#F8FAFC; --accent:#0B6E79; }}
  html, body {{ background: var(--bg); color: var(--fg); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.55; }}
  body {{ max-width: 960px; margin: 0 auto; padding: 40px 32px 80px; }}
  h1 {{ font-size: 28px; letter-spacing: -0.01em; margin-bottom: 4px; }}
  h2 {{ font-size: 20px; margin-top: 36px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }}
  h3 {{ font-size: 16px; margin-top: 24px; }}
  h4 {{ font-size: 14px; color: var(--muted); }}
  code {{ background: var(--code); padding: 1px 5px; border-radius: 4px; font-size: 12.5px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  pre.code {{ background: var(--code); padding: 12px 14px; border-radius: 8px; overflow-x: auto; font-size: 12px; line-height: 1.45; }}
  pre.code code {{ background: transparent; padding: 0; }}
  table {{ border-collapse: collapse; margin: 10px 0 18px; font-size: 13px; }}
  th, td {{ border: 1px solid var(--line); padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #F1F5F9; }}
  ul, ol {{ padding-left: 22px; }}
  li {{ margin: 3px 0; }}
  section {{ page-break-after: always; }}
  section:last-of-type {{ page-break-after: auto; }}
  .mermaid {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 12px 0; }}
  header.cover {{ border-bottom: 2px solid var(--accent); padding-bottom: 16px; margin-bottom: 24px; }}
  header.cover .sub {{ color: var(--muted); font-size: 13px; }}
  nav.toc {{ background: #F8FAFC; border: 1px solid var(--line); border-radius: 8px; padding: 12px 18px; margin-bottom: 28px; }}
  nav.toc ol {{ margin: 4px 0; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
</script>
</head>
<body>
<header class="cover">
  <h1>ChartNav — Consolidated Build</h1>
  <div class="sub">Backend phases 1–16: spine → state machine → auth → RBAC → CI → production seam → Postgres → frontend → E2E → JWT + ops → staging → governance → control plane → invitations → enterprise quality &amp; compliance → platform mode &amp; interoperability<br>
  Repo: <code>thekidd2227/chartnav-platform</code></div>
</header>
<nav class="toc"><strong>Contents</strong>{toc_html}</nav>
{body}
</body></html>
"""


def _candidate_browsers() -> list[str]:
    forced = os.environ.get("CHARTNAV_PDF_BROWSER")
    if forced:
        return [forced]
    return [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "chromium-browser",
        "chromium",
        "google-chrome",
        "chrome",
    ]


def main() -> int:
    html = build_html()
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    print(f"wrote {OUT_HTML}")

    for browser in _candidate_browsers():
        bpath = Path(browser)
        if not bpath.exists():
            which = subprocess.run(["which", browser], capture_output=True)
            if which.returncode != 0:
                continue
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri(),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if OUT_PDF.exists() and OUT_PDF.stat().st_size > 0:
            print(f"wrote {OUT_PDF} via {browser}")
            return 0

    # Fallback: reportlab plain-text PDF
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("ChartNav — Consolidated Build", styles["Title"]),
            Paragraph("Backend phases 1–5", styles["Normal"]),
            Spacer(1, 16),
            Paragraph("Executive summary", styles["Heading2"]),
        ]
        for p in EXEC_SUMMARY.strip().split("\n\n"):
            story.append(Paragraph(p.replace("`", ""), styles["BodyText"]))
            story.append(Spacer(1, 6))
        for title, path in SECTIONS[1:]:
            if path is None or not path.exists():
                continue
            story.append(PageBreak())
            story.append(Paragraph(title, styles["Heading2"]))
            story.append(Preformatted(path.read_text(), styles["Code"]))
        SimpleDocTemplate(str(OUT_PDF), pagesize=LETTER).build(story)
        print(f"wrote {OUT_PDF} via reportlab fallback")
        return 0
    except Exception as e:
        print(f"PDF generation failed; no browser and reportlab fallback errored: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

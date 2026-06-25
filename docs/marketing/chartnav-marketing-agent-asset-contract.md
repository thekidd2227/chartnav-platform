# ChartNav marketing-agent asset contract

This is a binding contract for any automated marketing agent (or human) that
produces ChartNav marketing material. It governs **which images may be used and
how**.

## Allowed sources

- The agent may use an image **only if** it is listed with `status: "approved"`
  in `public/marketing-assets/chartnav/manifests/screenshot-manifest.json`, and
  surfaced in `public/marketing-assets/chartnav/approved-assets.json`.
- The agent **must not** crawl, read, or publish from any of:
  - `qa/` (including `qa/screenshots/**` and `qa/screenshots/marketing/staging/`)
  - `artifacts/`
  - `docs/demo/`
  - `test-results/`, Playwright output, any `*-results/` dir
  - `public/marketing-assets/chartnav/archive/` (archived-not-approved)
- If an asset referenced anywhere lacks a valid, approved manifest entry, the
  agent **must reject it** and use nothing in its place.

## Usage rules per asset

- Honor `allowed_channels` — never post an asset to a channel not listed.
- Honor `caption_guidance` — captions must be consistent with it.
- Use `alt_text` (or a faithful refinement) for accessibility.
- Never make, imply, or paraphrase any claim in `prohibited_claims`, and never
  assert (globally): HIPAA compliance/certification, FDA approval/clearance,
  BAA coverage, SOC 2, "secure"/"compliant" as a guarantee, autonomous
  diagnosis, automatic image interpretation, medication selection, or that a
  feature is "production-ready" or "clinically validated".
- Never infer product/clinical readiness from a screenshot. A screenshot shows
  a UI state, not a certification or a deployment.

## Integrity

- Treat `contains_phi`, `contains_localhost`, `contains_debug_ui`,
  `synthetic_demo_data_only`, and `captured_from` as gates: an approved asset
  has no PHI, no localhost/API/debug UI, only synthetic demo data, and comes
  from the real running application at a known commit (`app_version`).
- If the manifest fails `scripts/marketing/validate_chartnav_assets.py`, treat
  the **entire bank as unusable** until it passes.

## Today

`approved-assets.json` currently contains **zero** approved assets. Until a
human promotes fresh, provenance-stamped captures, the agent has **no** ChartNav
screenshots to use and must not fabricate or substitute any.

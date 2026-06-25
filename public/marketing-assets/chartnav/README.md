# ChartNav marketing asset bank (canonical)

This directory is the **single source of truth** for ChartNav marketing
screenshots. Nothing else in the repo is a canonical marketing source.

```
public/marketing-assets/chartnav/
├── approved/<category>/      # approved, publishable assets ONLY
├── archive/                  # archived-not-approved (provenance/history; never published)
├── manifests/
│   ├── screenshot-manifest.json         # full registry (approved + archived)
│   └── screenshot-manifest.schema.json  # JSON Schema for the manifest
├── approved-assets.json      # machine-readable APPROVED-only index (generated)
└── README.md
```

## Rules (enforced by CI: `.github/workflows/marketing-assets-validation.yml`)

- **Only `status: "approved"` entries may be used by marketing.** Use
  `approved-assets.json` (generated from the manifest) as the query surface.
- Every public file must have a manifest entry; no orphans; no duplicate
  SHA-256; no zero-byte/corrupt images.
- **Approved** assets must: be from the **real running application**
  (`captured_from`), carry a real 40-char **commit SHA** (`app_version`), be
  free of **PHI / localhost / debug UI**, use **synthetic demo data only**,
  carry a **reviewer**, **caption_guidance**, **alt_text**, **non-empty
  allowed_channels**, and **prohibited_claims**.
- **Archived** assets live under `archive/`, are never approved, and are
  excluded from `approved-assets.json`.

## Workflow

1. **Capture** (real app, demo mode, no debug chips) → staging:
   ```
   node scripts/marketing/capture_chartnav_marketing_assets.mjs
   # writes qa/screenshots/marketing/staging/*.png + *.meta.json (with commit SHA)
   ```
2. **Human review** each staged PNG (pixels): no PHI, no localhost/API chip,
   ChartNav branding, supported features, no unsupported claims.
3. **Promote** an approved capture:
   ```
   python scripts/marketing/promote_chartnav_asset.py --source <staged.png> \
     --id <slug> --category <cat> --feature "<feature>" --reviewer "<name>" \
     --app-version <40-char-sha> --captured-at <iso> --channels LinkedIn,website \
     --caption "<guidance>" --alt "<factual alt text>" --approve
   ```
4. **Regenerate** the index after any change:
   ```
   python scripts/marketing/generate_chartnav_manifest.py
   ```
5. **Validate** (also run in CI):
   ```
   python scripts/marketing/validate_chartnav_assets.py
   ```

## Current state (2026-06-25)

`approved/` is **empty**. The 10 pre-governance screenshots from the stash are
**archived-not-approved** (no verifiable commit-SHA provenance; chrome-bearing
frames showed a localhost API chip and a non-ChartNav "ARCG Systems" footer).
See `docs/marketing/chartnav-screenshot-source-audit.md`. Fresh captures through
the governed pipeline are required before anything is approved.

> Do not assert HIPAA compliance, FDA clearance, autonomous diagnosis, or
> automatic image interpretation anywhere. See the marketing-agent contract:
> `docs/marketing/chartnav-marketing-agent-asset-contract.md`.

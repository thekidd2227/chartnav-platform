#!/usr/bin/env python3
"""Deterministically (re)build the ChartNav marketing screenshot manifest.

- Recomputes file-derived fields (sha256, width, height) from disk.
- Preserves human approval metadata for existing entries (status, reviewed_by,
  approved_at, allowed_channels, caption_guidance, alt_text, prohibited_claims,
  feature, app_version, captured_*).
- NEVER promotes/approves automatically. Approval only happens via
  promote_chartnav_asset.py. Files under approved/ MUST already have an entry
  (else this errors — they must be added by the promotion tool).
- For files under archive/ with no entry, creates an honest
  'archived-not-approved' stub.

Usage:
  python scripts/marketing/generate_chartnav_manifest.py [--now ISO8601] [--check]

`--check` writes nothing and exits non-zero if the manifest is out of date
(useful as a CI guard). Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "public" / "marketing-assets" / "chartnav"
MANIFEST = ASSET_ROOT / "manifests" / "screenshot-manifest.json"

# Reuse the validator's image-size readers to stay consistent.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_chartnav_assets import image_size  # noqa: E402

DEFAULT_PROHIBITED = [
    "autonomous diagnosis",
    "automatic image interpretation",
    "FDA approved",
    "HIPAA certified",
]


def load_existing() -> dict:
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text())
            return {a["filename"]: a for a in data.get("assets", [])}
        except (json.JSONDecodeError, KeyError):
            return {}
    return {}


def archive_stub(rel: str) -> dict:
    stem = Path(rel).name.rsplit(".", 1)[0]
    return {
        "id": stem,
        "filename": rel,
        "feature": "Unclassified (archived)",
        "category": "dashboard",
        "status": "archived-not-approved",
        "captured_from": "unknown (pre-governance capture)",
        "captured_at": "1970-01-01T00:00:00Z",
        "app_version": "unknown",
        "sha256": "",
        "width": 0,
        "height": 0,
        "contains_phi": False,
        "contains_localhost": False,
        "contains_debug_ui": False,
        "synthetic_demo_data_only": True,
        "reviewed_by": "marketing-governance-audit",
        "approved_at": None,
        "allowed_channels": [],
        "caption_guidance": "ARCHIVED — not approved for any channel.",
        "alt_text": "Archived ChartNav screenshot retained for provenance only.",
        "prohibited_claims": list(DEFAULT_PROHIBITED),
    }


def build(now: str) -> dict:
    existing = load_existing()
    assets: list[dict] = []
    errors: list[str] = []

    for sub in ("approved", "archive"):
        base = ASSET_ROOT / sub
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not (p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")):
                continue
            rel = str(p.relative_to(ASSET_ROOT))
            entry = dict(existing.get(rel) or {})
            if not entry:
                if sub == "approved":
                    errors.append(
                        f"approved/ file has no manifest entry (promote it, "
                        f"don't hand-drop): {rel}"
                    )
                    continue
                entry = archive_stub(rel)
            # Recompute file-derived fields deterministically.
            raw = p.read_bytes()
            entry["filename"] = rel
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            size = image_size(p)
            if size:
                entry["width"], entry["height"] = size
            assets.append(entry)

    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        raise SystemExit(2)

    assets.sort(key=lambda a: a["filename"])
    return {"version": 1, "generated_at": now, "assets": assets}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None, help="ISO-8601 generated_at stamp")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    now = args.now
    if not now:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    built = build(now)

    if args.check:
        if not MANIFEST.exists():
            print("❌ manifest missing")
            return 1
        current = json.loads(MANIFEST.read_text())
        # Compare everything except generated_at.
        a = {k: v for k, v in current.items() if k != "generated_at"}
        b = {k: v for k, v in built.items() if k != "generated_at"}
        if a != b:
            print("❌ manifest is out of date — run generate_chartnav_manifest.py")
            return 1
        print("✅ manifest up to date")
        return 0

    MANIFEST.write_text(json.dumps(built, indent=2) + "\n")
    print(f"✅ wrote {MANIFEST.relative_to(ROOT)} ({len(built['assets'])} assets)")

    # Public, machine-readable approved-only index for the marketing agent.
    approved = [
        {
            "id": a["id"], "filename": a["filename"], "feature": a["feature"],
            "category": a["category"], "app_version": a["app_version"],
            "allowed_channels": a["allowed_channels"],
            "caption_guidance": a["caption_guidance"], "alt_text": a["alt_text"],
            "prohibited_claims": a["prohibited_claims"],
        }
        for a in built["assets"] if a["status"] == "approved"
    ]
    index = {"version": 1, "generated_at": now, "approved_assets": approved}
    approved_path = ASSET_ROOT / "approved-assets.json"
    approved_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"✅ wrote {approved_path.relative_to(ROOT)} ({len(approved)} approved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

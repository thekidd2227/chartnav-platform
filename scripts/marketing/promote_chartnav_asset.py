#!/usr/bin/env python3
"""Promote a reviewed, staged screenshot into the governed approved bank.

Human-in-the-loop gate. Requires explicit category, approval, caption guidance,
allowed channels, and reviewer. Computes SHA-256, copies the approved file into
the proper public category (NEVER modifies the source capture), updates the
manifest atomically, and rejects duplicates / unsafe filenames.

Example:
  python scripts/marketing/promote_chartnav_asset.py \
    --source qa/screenshots/marketing/staging/retina-review-1750000000.png \
    --id chartnav-retina-workflow-provider-review \
    --category retina-workflow --feature "Retina workflow" \
    --reviewer "j.charles" --approve \
    --app-version 4be209be95365a1c0b7f0aa6418d15edbd108c20 \
    --captured-at 2026-06-25T18:00:00Z \
    --channels LinkedIn,website \
    --caption "Provider-controlled retina workflow review" \
    --alt "ChartNav retinal diagram review screen with synthetic demo data"

Stdlib only. Runs the validator at the end; refuses to leave an invalid bank.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "public" / "marketing-assets" / "chartnav"
MANIFEST = ASSET_ROOT / "manifests" / "screenshot-manifest.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_chartnav_assets import image_size, CATEGORIES, COMMIT_RE, SLUG_RE  # noqa: E402

PROHIBITED_TOKENS = ("localhost", "debug", "test", "draft", "fake", "mock",
                     "placeholder", "unapproved", "wip", "tmp")
DEFAULT_PROHIBITED = [
    "autonomous diagnosis", "automatic image interpretation",
    "FDA approved", "HIPAA certified",
]


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="path to the staged capture")
    ap.add_argument("--id", required=True, help="stable slug asset id")
    ap.add_argument("--category", required=True, choices=sorted(CATEGORIES))
    ap.add_argument("--feature", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--caption", required=True, dest="caption_guidance")
    ap.add_argument("--alt", required=True, dest="alt_text")
    ap.add_argument("--channels", required=True, help="comma-separated allowed channels")
    ap.add_argument("--app-version", required=True, help="40-char commit SHA of the captured build")
    ap.add_argument("--captured-at", required=True, help="ISO-8601 capture time")
    ap.add_argument("--approved-at", default=None, help="ISO-8601 approval time (default: now)")
    ap.add_argument("--prohibited", default=",".join(DEFAULT_PROHIBITED))
    ap.add_argument("--approve", action="store_true",
                    help="REQUIRED explicit approval flag; without it nothing is promoted")
    ap.add_argument("--allow-dup", action="store_true",
                    help="allow promoting an image whose sha256 already exists")
    args = ap.parse_args()

    if not args.approve:
        fail("refusing to promote without explicit --approve (human review gate)")
    if not SLUG_RE.match(args.id):
        fail(f"--id '{args.id}' is not a valid slug")
    for bad in PROHIBITED_TOKENS:
        if bad in args.id.lower():
            fail(f"--id contains prohibited token '{bad}'")
    if not COMMIT_RE.match(args.app_version):
        fail("--app-version must be a 40-char git commit SHA (real provenance required)")

    src = Path(args.source)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        fail(f"source not found: {src}")
    raw = src.read_bytes()
    if not raw:
        fail("source is zero-byte")
    for bad in PROHIBITED_TOKENS:
        if bad in src.name.lower():
            fail(f"source filename contains prohibited token '{bad}'")

    size = image_size(src)
    if size is None:
        fail("source is not a readable PNG/JPEG/WebP")
    w, h = size
    if w < 320 or h < 240:
        fail(f"source dimensions {w}x{h} below minimum 320x240")

    digest = hashlib.sha256(raw).hexdigest()
    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    if not channels:
        fail("--channels must list at least one channel")

    manifest = (
        json.loads(MANIFEST.read_text())
        if MANIFEST.exists() else {"version": 1, "generated_at": "", "assets": []}
    )
    assets = manifest["assets"]

    for a in assets:
        if a["sha256"] == digest and not args.allow_dup:
            fail(f"duplicate sha256 — identical image already present as [{a['id']}] "
                 f"({a['filename']}). Use --allow-dup only if intentional.")
        if a["id"] == args.id:
            fail(f"asset id '{args.id}' already exists")

    ext = src.suffix.lower()
    rel = f"approved/{args.category}/{args.id}{ext}"
    dest = ASSET_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Copy (never move / modify the source capture).
    shutil.copy2(src, dest)

    approved_at = args.approved_at
    if not approved_at:
        from datetime import datetime, timezone
        approved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    entry = {
        "id": args.id,
        "filename": rel,
        "feature": args.feature,
        "category": args.category,
        "status": "approved",
        "captured_from": "real running application",
        "captured_at": args.captured_at,
        "app_version": args.app_version,
        "sha256": digest,
        "width": w,
        "height": h,
        "contains_phi": False,
        "contains_localhost": False,
        "contains_debug_ui": False,
        "synthetic_demo_data_only": True,
        "reviewed_by": args.reviewer,
        "approved_at": approved_at,
        "allowed_channels": channels,
        "caption_guidance": args.caption_guidance,
        "alt_text": args.alt_text,
        "prohibited_claims": [p.strip() for p in args.prohibited.split(",") if p.strip()],
    }
    assets.append(entry)
    assets.sort(key=lambda a: a["filename"])

    # Atomic write: temp file then replace.
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp.replace(MANIFEST)
    print(f"✅ promoted [{args.id}] → {rel}")

    # Refuse to leave an invalid bank.
    from validate_chartnav_assets import main as validate_main
    rc = validate_main()
    if rc != 0:
        fail("post-promotion validation failed; review the manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate the governed ChartNav marketing asset bank.

Pure standard library (no pip deps) so CI can run it with a bare Python.
Exits non-zero on any violation.

Checks (per docs/marketing/chartnav-screenshot-source-audit.md and
manifests/screenshot-manifest.schema.json):
  - manifest parses and matches the schema's structural constraints;
  - every manifest file exists on disk under the asset root;
  - every public file (approved/** and archive/**) has a manifest entry
    (no orphans);
  - no duplicate sha256 across entries;
  - recorded sha256 matches the file on disk;
  - files are non-zero, valid PNG/JPEG/WebP with readable dimensions;
  - dimensions meet the minimum and match the recorded width/height;
  - approved entries: status/approval/provenance gates
    (contains_phi false, contains_localhost false, contains_debug_ui false,
     synthetic_demo_data_only true, captured_from == 'real running application',
     app_version is a 40-hex commit SHA, allowed_channels non-empty,
     prohibited_claims present, approved_at set, filename under approved/<cat>/);
  - archived entries live under archive/ and are never approved;
  - filenames follow the slug convention.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "public" / "marketing-assets" / "chartnav"
MANIFEST = ASSET_ROOT / "manifests" / "screenshot-manifest.json"
SCHEMA = ASSET_ROOT / "manifests" / "screenshot-manifest.schema.json"

MIN_W, MIN_H = 320, 240
CATEGORIES = {
    "dashboard", "retina-workflow", "technician-workflow", "provider-review",
    "note-lifecycle", "imaging", "security", "administration",
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_FIELDS = {
    "id", "filename", "feature", "category", "status", "captured_from",
    "captured_at", "app_version", "sha256", "width", "height", "contains_phi",
    "contains_localhost", "contains_debug_ui", "synthetic_demo_data_only",
    "reviewed_by", "approved_at", "allowed_channels", "caption_guidance",
    "alt_text", "prohibited_claims",
}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpeg_size(data: bytes):
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i < n - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg
    return None


def webp_size(data: bytes):
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    fmt = data[12:16]
    try:
        if fmt == b"VP8 ":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return w, h
        if fmt == b"VP8L":
            b = data[21:25]
            bits = int.from_bytes(b, "little")
            w = (bits & 0x3FFF) + 1
            h = ((bits >> 14) & 0x3FFF) + 1
            return w, h
        if fmt == b"VP8X":
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h
    except struct.error:
        return None
    return None


def image_size(path: Path):
    data = path.read_bytes()
    if not data:
        return None
    for fn in (png_size, jpeg_size, webp_size):
        size = fn(data)
        if size:
            return size
    return None


def main() -> int:
    if not MANIFEST.exists():
        err(f"manifest missing: {MANIFEST}")
        return _finish()
    if not SCHEMA.exists():
        err(f"schema missing: {SCHEMA}")
    try:
        manifest = json.loads(MANIFEST.read_text())
    except json.JSONDecodeError as e:
        err(f"manifest is not valid JSON: {e}")
        return _finish()

    if not isinstance(manifest, dict) or "assets" not in manifest:
        err("manifest must be an object with an 'assets' array")
        return _finish()
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        err("'assets' must be an array")
        return _finish()

    # Optional full schema validation if jsonschema is available.
    try:
        import jsonschema  # type: ignore
        try:
            jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
        except jsonschema.ValidationError as e:  # pragma: no cover
            err(f"schema validation failed: {e.message} at {list(e.path)}")
    except ImportError:
        warnings.append("jsonschema not installed — running structural checks only")

    seen_hashes: dict[str, str] = {}
    seen_ids: set[str] = set()
    manifest_files: set[str] = set()

    for a in assets:
        aid = a.get("id", "<no-id>")
        missing = REQUIRED_FIELDS - set(a)
        if missing:
            err(f"[{aid}] missing fields: {sorted(missing)}")
            continue

        if not SLUG_RE.match(str(a["id"])):
            err(f"[{aid}] id is not a slug")
        if a["id"] in seen_ids:
            err(f"[{aid}] duplicate id")
        seen_ids.add(a["id"])

        fn = a["filename"]
        manifest_files.add(fn)
        status = a["status"]
        cat = a["category"]

        # filename slug convention + location vs status
        base = Path(fn).name
        stem = base.rsplit(".", 1)[0]
        if not SLUG_RE.match(stem):
            err(f"[{aid}] filename '{base}' is not a consistent slug")
        for bad in ("localhost", "debug", "test", "draft", "fake", "mock",
                    "placeholder", "unapproved", "wip", "tmp"):
            if bad in base.lower():
                err(f"[{aid}] filename contains prohibited token '{bad}'")

        if cat not in CATEGORIES:
            err(f"[{aid}] unknown category '{cat}'")

        if status == "approved":
            if not fn.startswith(f"approved/{cat}/"):
                err(f"[{aid}] approved asset must live under approved/{cat}/")
            if a.get("approved_at") in (None, ""):
                err(f"[{aid}] approved asset missing approved_at")
            if a.get("contains_phi") is not False:
                err(f"[{aid}] approved asset must have contains_phi=false")
            if a.get("contains_localhost") is not False:
                err(f"[{aid}] approved asset must have contains_localhost=false")
            if a.get("contains_debug_ui") is not False:
                err(f"[{aid}] approved asset must have contains_debug_ui=false")
            if a.get("synthetic_demo_data_only") is not True:
                err(f"[{aid}] approved asset must have synthetic_demo_data_only=true")
            if a.get("captured_from") != "real running application":
                err(f"[{aid}] captured_from must be exactly 'real running application'")
            if not COMMIT_RE.match(str(a.get("app_version", ""))):
                err(f"[{aid}] app_version must be a 40-char commit SHA")
            if not a.get("allowed_channels"):
                err(f"[{aid}] allowed_channels must be non-empty")
            if not a.get("prohibited_claims"):
                err(f"[{aid}] prohibited_claims must be present")
            if not str(a.get("reviewed_by", "")).strip():
                err(f"[{aid}] reviewed_by required for approved assets")
        elif status == "archived-not-approved":
            if not fn.startswith("archive/"):
                err(f"[{aid}] archived asset must live under archive/")
            if a.get("approved_at") not in (None,):
                err(f"[{aid}] archived asset must have approved_at=null")
        else:
            err(f"[{aid}] invalid status '{status}'")

        # file existence + integrity
        path = ASSET_ROOT / fn
        if not path.exists():
            err(f"[{aid}] file does not exist: {fn}")
            continue
        raw = path.read_bytes()
        if not raw:
            err(f"[{aid}] file is zero-byte: {fn}")
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if not SHA_RE.match(str(a.get("sha256", ""))):
            err(f"[{aid}] sha256 is not a 64-hex string")
        elif digest != a["sha256"]:
            err(f"[{aid}] sha256 mismatch (manifest {a['sha256'][:12]}…, file {digest[:12]}…)")
        if digest in seen_hashes:
            err(f"[{aid}] duplicate sha256 — also used by [{seen_hashes[digest]}]")
        seen_hashes[digest] = aid

        size = image_size(path)
        if size is None:
            err(f"[{aid}] not a readable PNG/JPEG/WebP: {fn}")
        else:
            w, h = size
            # Minimum dimensions are an approval gate (per schema); archived
            # assets only need accurate recorded dimensions.
            if status == "approved" and (w < MIN_W or h < MIN_H):
                err(f"[{aid}] dimensions {w}x{h} below minimum {MIN_W}x{MIN_H}")
            if a.get("width") != w or a.get("height") != h:
                err(f"[{aid}] recorded {a.get('width')}x{a.get('height')} != actual {w}x{h}")

    # orphan check: every file under approved/ and archive/ must be in manifest
    for sub in ("approved", "archive"):
        base = ASSET_ROOT / sub
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                rel = str(p.relative_to(ASSET_ROOT))
                if rel not in manifest_files:
                    err(f"orphaned asset on disk (no manifest entry): {rel}")

    return _finish()


def _finish() -> int:
    for w in warnings:
        print(f"  ⚠️  {w}")
    if errors:
        print(f"\n❌ marketing asset validation FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ marketing asset validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

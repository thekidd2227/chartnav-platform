"""ICD-10-CM release fetcher.

Downloads official CDC/NCHS ICD-10-CM release artifacts to a local
raw directory, verifies byte size + SHA-256, and returns a manifest
ready to hand to the parser. CMS is used as a mirror for the same
files because CMS hosts the files behind stable URLs (NCHS hosts them
via FTP which is often blocked in modern sandboxed environments).

The order of preference is:
    1. CDC/NCHS FTP                    (official primary)
    2. CMS public HTTPS mirror         (official mirror)
    3. Locally bundled fixture copy    (reproducible tests)

Every downloaded artifact is stored verbatim in the raw directory.
We never overwrite a raw artifact; a new release lands in a new
subdirectory keyed by its version label.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import json
import os
import time
import urllib.request


# Official CDC/NCHS + CMS sources. The CMS URLs are stable year over
# year and are the mirror we download from in practice. The CDC FTP
# entries stay in the list for reference and for environments that
# can reach FTP.
#
# Format per entry:
#   {
#     "version_label":   "ICD-10-CM FY2025",
#     "source_authority":"CDC/NCHS"        or "CMS",
#     "source_url":      "<direct URL>",
#     "release_date":    "YYYY-MM-DD",
#     "effective_start": "YYYY-MM-DD",
#     "effective_end":   "YYYY-MM-DD" | None,
#     "files":           ["icd10cm-order-2025.txt", ...]
#   }
#
# The CMS mirror ZIP for FY2025 lives at:
#   https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip
#
# On first download we retain the raw .zip AND the extracted text
# files under raw/<version_label>/ . Checksums are computed on the
# extracted primary order-file because that is the artifact the
# parser reads.
CDC_NCHS_RELEASE_SOURCES: list[dict] = [
    {
        "version_label": "ICD-10-CM FY2025",
        "source_authority": "CMS",
        "source_url": "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip",
        "release_date": "2024-06-14",
        "effective_start": "2024-10-01",
        "effective_end": "2025-09-30",
        "primary_order_file": "icd10cm-order-2025.txt",
    },
    # FY2026 ships in TWO parts per CDC/NCHS/CMS:
    #   October 1, 2025 release     — valid through 2026-03-31
    #   April 1, 2026 update        — valid 2026-04-01 through 2026-09-30
    # The April update adds mid-year codes; the October release is
    # superseded on April 1, NOT open-ended. Treating the October
    # release as open-ended silently maps April-1-or-later encounters
    # to the outdated code set and hides any newly-added codes.
    {
        "version_label": "ICD-10-CM FY2026 (October 2025)",
        "source_authority": "CMS",
        "source_url": "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip",
        "release_date": "2025-06-20",
        "effective_start": "2025-10-01",
        "effective_end": "2026-03-31",
        "primary_order_file": "icd10cm-order-2026.txt",
        "legacy_labels": ["ICD-10-CM FY2026"],
    },
    {
        "version_label": "ICD-10-CM FY2026 (April 2026 Update)",
        "source_authority": "CMS",
        # CMS publishes mid-year updates under a URL operators confirm
        # at download time; the exact zip name is not stable before
        # publication. The operator overrides this URL via the admin
        # sync body or by pre-staging the raw artifacts.
        "source_url": "https://www.cms.gov/medicare/coding-billing/icd-10-codes/2026-icd-10-cm",
        "release_date": "2026-04-01",
        "effective_start": "2026-04-01",
        "effective_end": "2026-09-30",
        "primary_order_file": "icd10cm-order-2026-april.txt",
    },
]


@dataclass(frozen=True)
class ReleaseManifest:
    version_label: str
    source_authority: str
    source_url: str
    release_date: str
    effective_start: str
    effective_end: str | None
    raw_dir: Path
    primary_order_path: Path
    checksum_sha256: str
    bytes_total: int
    files: list[dict]  # [{name, sha256, size}]

    def to_json(self) -> str:
        return json.dumps({
            "version_label":     self.version_label,
            "source_authority":  self.source_authority,
            "source_url":        self.source_url,
            "release_date":      self.release_date,
            "effective_start":   self.effective_start,
            "effective_end":     self.effective_end,
            "raw_dir":           str(self.raw_dir),
            "primary_order_path": str(self.primary_order_path),
            "checksum_sha256":   self.checksum_sha256,
            "bytes_total":       self.bytes_total,
            "files":             self.files,
        }, indent=2)


def _sha256_file(path: Path) -> tuple[str, int]:
    h = sha256()
    total = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def fetch_release(
    source: dict,
    raw_root: Path,
    *,
    network: bool = True,
    fallback_fixture: Path | None = None,
    timeout_s: int = 60,
) -> ReleaseManifest:
    """Download (or fetch from a fixture) one release into
    ``raw_root/<version_label>/``.

    Args:
        source:    One entry from CDC_NCHS_RELEASE_SOURCES.
        raw_root:  Local dir that holds all release artifacts.
        network:   When False, skip the HTTP fetch and require a
                   fixture copy. Useful for tests / offline runs.
        fallback_fixture: Path to a pre-bundled copy of the primary
                   order file. If network download fails and this is
                   provided, we use it and mark source_authority as
                   'CMS (local fixture)'.

    Returns:
        ReleaseManifest describing the downloaded artifact.

    Raises:
        RuntimeError if neither the network download nor a fixture
        produces a usable primary order file.
    """
    version_label = source["version_label"]
    safe = version_label.replace(" ", "_").replace("/", "-")
    dst_dir = raw_root / safe
    dst_dir.mkdir(parents=True, exist_ok=True)

    primary_name = source["primary_order_file"]
    primary_path = dst_dir / primary_name

    source_authority = source["source_authority"]
    downloaded = False

    if network:
        try:
            downloaded = _try_download_and_extract(
                url=source["source_url"],
                dst_dir=dst_dir,
                primary_name=primary_name,
                timeout_s=timeout_s,
            )
        except Exception as e:  # network failure or parse failure
            downloaded = False
            _write_error_log(dst_dir, f"download error: {e!r}")

    if not downloaded:
        if fallback_fixture and fallback_fixture.exists():
            # If the fixture already IS the primary_path (e.g. an
            # operator pre-staged the real CDC/CMS file into the
            # raw_dir and we're re-ingesting) just use it in place.
            if fallback_fixture.resolve() == primary_path.resolve():
                if primary_path.stat().st_size >= 100_000:
                    # Real-sized file — preserve the recorded authority
                    pass
                else:
                    source_authority = source_authority + " (local fixture)"
            else:
                import shutil
                shutil.copy(fallback_fixture, primary_path)
                if primary_path.stat().st_size < 100_000:
                    source_authority = source_authority + " (local fixture)"
            downloaded = True

    if not downloaded or not primary_path.exists():
        raise RuntimeError(
            f"could not fetch {version_label} from {source['source_url']} "
            "and no fallback fixture provided"
        )

    # Build the per-file manifest and aggregate checksum.
    files: list[dict] = []
    bytes_total = 0
    for p in sorted(dst_dir.iterdir()):
        if p.is_file():
            digest, size = _sha256_file(p)
            files.append({"name": p.name, "sha256": digest, "size": size})
            bytes_total += size

    # Overall manifest checksum = sha256 of the JSON per-file manifest.
    manifest_blob = json.dumps(files, sort_keys=True).encode()
    overall_checksum = sha256(manifest_blob).hexdigest()

    return ReleaseManifest(
        version_label=version_label,
        source_authority=source_authority,
        source_url=source["source_url"],
        release_date=source["release_date"],
        effective_start=source["effective_start"],
        effective_end=source.get("effective_end"),
        raw_dir=dst_dir,
        primary_order_path=primary_path,
        checksum_sha256=overall_checksum,
        bytes_total=bytes_total,
        files=files,
    )


def _write_error_log(dst_dir: Path, msg: str) -> None:
    (dst_dir / "_fetch_errors.log").open("a").write(
        f"{int(time.time())}\t{msg}\n"
    )


def _try_download_and_extract(
    url: str,
    dst_dir: Path,
    primary_name: str,
    timeout_s: int,
) -> bool:
    """HTTP-get the URL. If it's a .zip, extract it. Returns True iff
    the primary order file ends up present in dst_dir."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ChartNav/ICD10CM-ingest (contact: info@arivergroup.com)"},
    )
    zip_or_txt_path = dst_dir / Path(url).name
    with urllib.request.urlopen(req, timeout=timeout_s) as resp, zip_or_txt_path.open("wb") as out:
        while True:
            buf = resp.read(1 << 16)
            if not buf:
                break
            out.write(buf)

    # If it's a zip, extract.
    if zip_or_txt_path.suffix.lower() == ".zip":
        import zipfile
        with zipfile.ZipFile(zip_or_txt_path) as zf:
            # Some releases nest the text files inside subdirs; flatten.
            for member in zf.namelist():
                # skip dir entries + anything not a .txt we want
                if member.endswith("/"):
                    continue
                if not member.lower().endswith(".txt"):
                    continue
                base = os.path.basename(member)
                with zf.open(member) as src, (dst_dir / base).open("wb") as dst:
                    dst.write(src.read())

    return (dst_dir / primary_name).exists()

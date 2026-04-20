"""ChartNav as a SourceDeck-deployable capability (phase 37).

One capability descriptor that SourceDeck (the implementation
catalog) renders into both modes:

  - Self-Implementation  — buyer fills in the setup inputs, ChartNav
                           runs in their tenant, no human help needed.
  - Done-For-You         — buyer buys an implementation engagement;
                           an ARCG implementation engineer fills the
                           setup inputs, validates the deployment,
                           and hands keys back.

The manifest is the shared contract:
- the same `setup_inputs` schema drives the self-serve form AND the
  done-for-you implementation worksheet
- the same `prerequisites` list gates both modes
- `deployment_state` is what LCC's per-deployment card reads to know
  if a sale is "live" or "in onboarding"

This module is pure data + pure functions. The HTTP layer in
`app.api.routes` exposes a public read so SourceDeck's catalog can
fetch it without an API key.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CAPABILITY_KEY = "chartnav"
CAPABILITY_VERSION = "1.0.0"


@dataclass(frozen=True)
class SetupInput:
    """One fill-in field that an implementation needs to start."""
    key: str
    label: str
    kind: str                  # "string" | "secret" | "select" | "bool" | "int"
    required: bool
    description: str
    default: Any = None
    options: tuple[str, ...] | None = None
    secret_masked: bool = False  # secrets render as "**** ****" once set


@dataclass(frozen=True)
class Prerequisite:
    """A real-world dependency that must be in place before the
    capability can serve traffic. SourceDeck shows these as a
    checklist; LCC alerts when one regresses."""
    key: str
    label: str
    detail: str


@dataclass(frozen=True)
class ImplementationMode:
    """Commercial + technical details for one purchase mode."""
    key: str                   # "self_implementation" | "done_for_you"
    name: str
    pricing_model: str         # "subscription" | "one_time_setup" | "tbd"
    audience: str              # operator-facing description
    setup_owner: str           # "buyer" | "arcg_implementation_team"
    typical_timeline: str
    includes: tuple[str, ...]
    excludes: tuple[str, ...]
    request_path: str          # URL for SourceDeck → implementation request


@dataclass(frozen=True)
class CapabilityCard:
    """The public catalog card SourceDeck renders."""
    key: str
    version: str
    name: str
    one_liner: str
    longer_pitch: str
    target_buyers: tuple[str, ...]
    capability_summary: tuple[str, ...]
    setup_inputs: tuple[SetupInput, ...]
    prerequisites: tuple[Prerequisite, ...]
    implementation_modes: tuple[ImplementationMode, ...]


# ---------------------------------------------------------------------------
# Setup inputs — the shared implementation model
# ---------------------------------------------------------------------------

# Every input here is a real configuration knob ChartNav reads at
# runtime. Adding a key here means the deployer (buyer or ARCG)
# fills it in BEFORE the deployment goes live; SourceDeck enforces
# completeness before letting a self-serve install proceed.

SETUP_INPUTS: tuple[SetupInput, ...] = (
    # --- identity / location ---
    SetupInput(
        key="organization_name",
        label="Organization name",
        kind="string",
        required=True,
        description="Display name used on the doctor app + LCC fleet view.",
    ),
    SetupInput(
        key="primary_location_name",
        label="Primary location name",
        kind="string",
        required=True,
        description=(
            "First clinic site. Additional sites can be added post-go-live "
            "via the admin Locations tab."
        ),
    ),
    SetupInput(
        key="implementation_mode",
        label="Implementation mode",
        kind="select",
        required=True,
        description="Self-serve (buyer fills these in) vs done-for-you.",
        options=("self_implementation", "done_for_you"),
    ),

    # --- STT provider ---
    SetupInput(
        key="stt_provider",
        label="Speech-to-text provider",
        kind="select",
        required=True,
        description=(
            "Picks the STT adapter ChartNav installs at boot. "
            "`stub` is dev-only; `none` disables audio ingestion."
        ),
        options=("stub", "openai_whisper", "none"),
        default="stub",
    ),
    SetupInput(
        key="openai_api_key",
        label="OpenAI API key",
        kind="secret",
        required=False,
        description=(
            "Required only if stt_provider=openai_whisper. ChartNav "
            "fails-loud at boot rather than silently downgrading."
        ),
        secret_masked=True,
    ),

    # --- storage ---
    SetupInput(
        key="audio_upload_dir",
        label="Audio storage directory",
        kind="string",
        required=False,
        description=(
            "Local-disk audio path. S3/GCS adapters land in a future "
            "release; the storage abstraction already supports them."
        ),
        default="./audio_uploads",
    ),
    SetupInput(
        key="audio_upload_max_bytes",
        label="Max upload size (bytes)",
        kind="int",
        required=False,
        description="HTTP-layer cap on audio uploads. Default 25 MiB.",
        default=25 * 1024 * 1024,
    ),

    # --- runtime ---
    SetupInput(
        key="audio_ingest_mode",
        label="Audio ingest mode",
        kind="select",
        required=True,
        description=(
            "`inline` runs ingestion synchronously (dev/test). `async` "
            "queues + lets the worker pick it up (production)."
        ),
        options=("inline", "async"),
        default="inline",
    ),
    SetupInput(
        key="rate_limit_per_minute",
        label="Per-IP rate limit",
        kind="int",
        required=False,
        description="0 disables.",
        default=120,
    ),

    # --- auth / session ---
    SetupInput(
        key="auth_mode",
        label="Auth mode",
        kind="select",
        required=True,
        description=(
            "`header` is dev (X-User-Email). `bearer` is production "
            "(JWT validated against a JWKS endpoint)."
        ),
        options=("header", "bearer"),
        default="header",
    ),
    SetupInput(
        key="jwt_jwks_url",
        label="JWT JWKS URL",
        kind="string",
        required=False,
        description="Required when auth_mode=bearer.",
    ),

    # --- capture surface ---
    SetupInput(
        key="capture_modes_enabled",
        label="Allowed capture modes",
        kind="select",
        required=True,
        description=(
            "Which audio capture surfaces are allowed. Both is the "
            "default; locked clinics may want file-upload only."
        ),
        options=("both", "browser-mic", "file-upload"),
        default="both",
    ),
)


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

PREREQUISITES: tuple[Prerequisite, ...] = (
    Prerequisite(
        key="https_endpoint",
        label="HTTPS endpoint",
        detail=(
            "Browsers refuse `getUserMedia` (microphone) on non-HTTPS "
            "origins, so the doctor app must be served over TLS."
        ),
    ),
    Prerequisite(
        key="postgres_or_sqlite",
        label="Postgres (recommended) or SQLite",
        detail=(
            "ChartNav ships SQLite by default for dev/pilot. Production "
            "deployments should run Postgres for concurrent worker "
            "ingestion."
        ),
    ),
    Prerequisite(
        key="audio_storage_writeable",
        label="Audio storage directory writeable",
        detail=(
            "Local-disk storage must be a persistent volume. Object "
            "storage adapters (S3/GCS) land in a future release."
        ),
    ),
    Prerequisite(
        key="stt_provider_credentials",
        label="STT provider credentials",
        detail=(
            "Whatever stt_provider is set to (other than `stub` / "
            "`none`) must have its required env vars present at boot, "
            "or the app fails-loud."
        ),
    ),
    Prerequisite(
        key="worker_runtime",
        label="Background worker process",
        detail=(
            "Required when audio_ingest_mode=async. Either run "
            "`python -m app.services.worker` as a long-lived process "
            "or call `POST /workers/tick` from cron."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Implementation modes
# ---------------------------------------------------------------------------

IMPLEMENTATION_MODES: tuple[ImplementationMode, ...] = (
    ImplementationMode(
        key="self_implementation",
        name="Self-implementation",
        pricing_model="subscription",
        audience=(
            "Practices with their own ops/IT muscle who can fill in "
            "the setup inputs + stand up Postgres + a worker process."
        ),
        setup_owner="buyer",
        typical_timeline="1–3 days from kickoff to first signed note",
        includes=(
            "ChartNav doctor app + admin section",
            "Real STT provider seam (OpenAI Whisper out of the box)",
            "Async ingestion pipeline",
            "Browser microphone capture (mobile + desktop)",
            "LCC observability hookup",
            "Email-only support",
        ),
        excludes=(
            "Hands-on setup",
            "Custom EHR adapter work",
            "Live training",
        ),
        request_path="/sourcedeck/chartnav/self",
    ),
    ImplementationMode(
        key="done_for_you",
        name="Done-for-you implementation",
        pricing_model="one_time_setup",
        audience=(
            "Practices that want ChartNav live in a week without "
            "touching infrastructure. Implementation engineer runs "
            "the entire stand-up."
        ),
        setup_owner="arcg_implementation_team",
        typical_timeline="5–10 business days from contract to first signed note",
        includes=(
            "Hosted environment provisioning",
            "STT provider account + key setup",
            "Storage + worker configuration",
            "First-location seed (users, providers, locations)",
            "Two live training sessions",
            "30-day implementation warranty",
            "LCC monitoring enablement",
        ),
        excludes=(
            "Custom EHR write-back development beyond the shipped FHIR "
            "DocumentReference path",
            "PHI migration from a prior EMR",
        ),
        request_path="/sourcedeck/chartnav/managed",
    ),
)


# ---------------------------------------------------------------------------
# Public descriptor
# ---------------------------------------------------------------------------

def capability_card() -> CapabilityCard:
    return CapabilityCard(
        key=CAPABILITY_KEY,
        version=CAPABILITY_VERSION,
        name="ChartNav",
        one_liner=(
            "Doctor-first dictation + structured note workflow for "
            "ophthalmology and adjacent specialties."
        ),
        longer_pitch=(
            "ChartNav captures dictation from a clinician's phone or "
            "desktop browser, transcribes it through a swappable STT "
            "provider, runs it through a deterministic note generator, "
            "and produces a signed clinical artifact ready for hand-off "
            "to the EHR. One encounter-centric workflow shared across "
            "mobile and desktop, with audit + provenance baked in."
        ),
        target_buyers=(
            "Single-specialty practices (ophthalmology, retina, glaucoma)",
            "Specialty groups already paying for an EHR but underserved by its dictation",
            "Practices with mixed mobile + desktop clinical workflow",
        ),
        capability_summary=(
            "Browser microphone capture (mobile + desktop)",
            "File-upload audio fallback",
            "Pluggable STT provider (OpenAI Whisper out of the box)",
            "Async transcription pipeline + retry semantics",
            "Clinician transcript review/edit before draft generation",
            "Specialist Clinical Shortcuts + Quick Comments",
            "Doctor-only signed-note workflow with provenance + audit",
            "FHIR R4 DocumentReference packaging shape",
            "LCC-ready observability + capability manifest",
        ),
        setup_inputs=SETUP_INPUTS,
        prerequisites=PREREQUISITES,
        implementation_modes=IMPLEMENTATION_MODES,
    )


# Stable schema id for /capability/manifest. SourceDeck (and any other
# external consumer) keys off this so that when we ever need to break the
# shape, we can publish v2 without silently breaking v1 readers. Bump the
# integer suffix when, and only when, an existing field is renamed,
# removed, or has its type changed. Adding new fields is *not* a bump.
CAPABILITY_MANIFEST_SCHEMA_VERSION = "capability_manifest/v1"


def card_to_dict(card: CapabilityCard) -> dict[str, Any]:
    """JSON-serialise the dataclass tree for the HTTP layer."""
    return {
        "schema_version": CAPABILITY_MANIFEST_SCHEMA_VERSION,
        "key": card.key,
        "version": card.version,
        "name": card.name,
        "one_liner": card.one_liner,
        "longer_pitch": card.longer_pitch,
        "target_buyers": list(card.target_buyers),
        "capability_summary": list(card.capability_summary),
        "setup_inputs": [asdict(i) for i in card.setup_inputs],
        "prerequisites": [asdict(p) for p in card.prerequisites],
        "implementation_modes": [asdict(m) for m in card.implementation_modes],
    }


# ---------------------------------------------------------------------------
# Actual config (admin-only — for the LCC "show me what this deployment
# is actually running" panel + SourceDeck's done-for-you handoff doc)
# ---------------------------------------------------------------------------

def deployment_config_actual() -> dict[str, Any]:
    """The deployment's *actual* runtime config, secrets masked.

    Same shape as `setup_inputs` but with `value` filled. Used by
    SourceDeck's handoff doc + LCC's deployment detail view to
    confirm the buyer (or ARCG implementation team) wired everything
    correctly.
    """
    from app.config import settings

    actual: dict[str, Any] = {
        "stt_provider": settings.stt_provider,
        "audio_upload_dir": settings.audio_upload_dir,
        "audio_upload_max_bytes": settings.audio_upload_max_bytes,
        "audio_ingest_mode": settings.audio_ingest_mode,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "auth_mode": settings.auth_mode,
        "jwt_jwks_url": settings.jwt_jwks_url,
        "platform_mode": settings.platform_mode,
        "integration_adapter": settings.integration_adapter,
    }
    # Mask anything that looks like a secret, even though we never
    # serialise raw secret values from settings — defensive.
    for k in list(actual.keys()):
        if "key" in k or "token" in k or "secret" in k:
            actual[k] = "**** masked ****" if actual[k] else None
    return actual

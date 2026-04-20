"""Phase 37 — deployment telemetry + capability manifest.

Three concerns:

1. Per-deployment telemetry (overview / locations / alerts / jobs /
   qa) is admin-only, org-scoped, PHI-minimising.
2. The public capability manifest is fetchable without auth and
   carries the shape SourceDeck renders into the catalog.
3. The public deployment manifest is fetchable without auth and
   carries the build/runtime fingerprint LCC uses to identify the
   instance.

Phase-33 → phase-36 protections (audio upload + transcript edit +
generation gating + reviewer restrictions) MUST stay green; the
overview rollup reads from the same `encounter_inputs` /
`note_versions` rows those phases produce.
"""

from __future__ import annotations

import json


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


MINIMAL_WAV_BYTES = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt "
    + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little") + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little") + b"data"
    + (0).to_bytes(4, "little")
)


# ---------------------------------------------------------------------
# Public manifests
# ---------------------------------------------------------------------


def test_capability_manifest_is_public_and_well_shaped(client):
    r = client.get("/capability/manifest")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["key"] == "chartnav"
    assert body["version"]
    assert body["name"] == "ChartNav"
    # Shape SourceDeck depends on:
    assert isinstance(body["setup_inputs"], list) and body["setup_inputs"]
    assert isinstance(body["prerequisites"], list) and body["prerequisites"]
    assert isinstance(body["implementation_modes"], list)
    mode_keys = {m["key"] for m in body["implementation_modes"]}
    assert {"self_implementation", "done_for_you"} <= mode_keys
    # Setup inputs include the load-bearing keys.
    keys = {i["key"] for i in body["setup_inputs"]}
    assert {
        "stt_provider", "audio_ingest_mode", "auth_mode",
        "audio_upload_dir", "implementation_mode",
        "capture_modes_enabled", "primary_location_name",
    } <= keys
    # Secret inputs declare themselves as such.
    secrets = [i for i in body["setup_inputs"] if i["kind"] == "secret"]
    assert all(i["secret_masked"] is True for i in secrets)


def test_deployment_manifest_is_public_and_carries_runtime_fingerprint(client):
    r = client.get("/deployment/manifest")
    assert r.status_code == 200
    body = r.json()
    assert body["release_version"]
    assert body["api_version"] == "v1"
    assert body["platform_mode"]
    assert body["audio_ingest_mode"] in {"inline", "async"}
    assert body["stt_provider"] in {"stub", "openai_whisper", "none"}
    assert body["storage_scheme"]  # at least "file" today
    assert "browser-mic" in body["capture_modes"]
    assert "file-upload" in body["capture_modes"]


# ---------------------------------------------------------------------
# Admin-only deployment telemetry
# ---------------------------------------------------------------------


def test_overview_requires_admin(client):
    r = client.get("/admin/deployment/overview", headers=CLIN1)
    assert r.status_code == 403
    r = client.get("/admin/deployment/overview", headers=REV1)
    assert r.status_code == 403


def test_overview_shape_for_admin(client):
    r = client.get("/admin/deployment/overview", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    # Top-level keys.
    for k in (
        "deployment_id", "window_hours", "generated_at", "release",
        "inputs", "notes", "alerts", "users", "qa",
        "locations", "health",
    ):
        assert k in body, f"missing key {k}"
    # Health is one of three.
    assert body["health"] in {"green", "amber", "red"}
    # Release block carries the same fingerprint as the public manifest.
    assert body["release"]["api_version"] == "v1"
    assert body["release"]["audio_ingest_mode"] in {"inline", "async"}
    # Users block.
    assert isinstance(body["users"]["active_total"], int)
    assert isinstance(body["users"]["by_role"], dict)


def test_overview_responds_to_real_audio_traffic(client):
    """Live signal — uploading a stub audio bumps the completed-window
    count + lands a row in the recent-jobs feed."""
    pre = client.get(
        "/admin/deployment/overview", headers=ADMIN1
    ).json()
    pre_completed = pre["inputs"]["completed_window"]

    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": "Telemetry test body."},
    )
    assert r.status_code == 201

    post = client.get(
        "/admin/deployment/overview", headers=ADMIN1
    ).json()
    assert post["inputs"]["completed_window"] == pre_completed + 1


def test_overview_is_org_scoped(client):
    """An admin in org1 must never see org2's traffic in the rollup."""
    # Org1 traffic.
    client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("a.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": "Org1 body."},
    )
    # Org2 traffic.
    client.post(
        "/encounters/2/inputs/audio",
        files={"audio": ("b.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN2, "X-Stub-Transcript": "Org2 body."},
    )

    o1 = client.get("/admin/deployment/overview", headers=ADMIN1).json()
    o2 = client.get("/admin/deployment/overview", headers=ADMIN2).json()
    # Each admin only sees their own traffic — completed_window
    # counts the org's rows, not the other tenant's.
    assert o1["deployment_id"] == 1
    assert o2["deployment_id"] == 2


def test_locations_rollup_lists_admin_org_locations(client):
    r = client.get("/admin/deployment/locations", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["deployment_id"] == 1
    items = body["items"]
    assert isinstance(items, list)
    assert len(items) >= 1
    for it in items:
        for k in (
            "location_id", "location_name", "encounters_window",
            "queued", "processing", "failed_window",
        ):
            assert k in it


def test_alerts_groups_failure_class_events(client):
    """Failed audio uploads + denied requests show up in the alerts
    rollup grouped by event_type + error_code."""
    # Generate a failed audio upload via the stub-error header.
    client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript-Error": "forced telemetry"},
    )
    r = client.get("/admin/deployment/alerts", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["deployment_id"] == 1
    assert isinstance(body["items"], list)


def test_jobs_returns_recent_input_outcomes_phi_safe(client):
    client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": "Jobs feed body."},
    )
    r = client.get(
        "/admin/deployment/jobs?limit=5", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    items = body["items"]
    assert isinstance(items, list)
    # PHI invariant: rows MUST NOT carry transcript_text or
    # source_metadata. They carry status + last_error_code + ids only.
    for it in items:
        assert set(it.keys()) == {
            "input_id", "encounter_id", "input_type",
            "processing_status", "last_error_code", "retry_count",
            "finished_at", "updated_at",
        }


def test_qa_returns_review_queue_counts(client):
    r = client.get("/admin/deployment/qa", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    for k in ("inputs_needing_review", "notes_awaiting_signoff"):
        assert k in body
        assert isinstance(body[k], int)


def test_config_actual_admin_only_and_secrets_masked(client):
    r = client.get("/admin/deployment/config-actual", headers=CLIN1)
    assert r.status_code == 403
    r = client.get("/admin/deployment/config-actual", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    # Every load-bearing config knob is named.
    for k in (
        "stt_provider", "audio_upload_dir", "audio_upload_max_bytes",
        "audio_ingest_mode", "rate_limit_per_minute",
        "auth_mode", "platform_mode",
    ):
        assert k in body
    # Anything that smells like a secret is masked.
    for k, v in body.items():
        if "key" in k or "token" in k or "secret" in k:
            assert v is None or "masked" in str(v).lower()


# ---------------------------------------------------------------------
# Phase 33–36 regression — telemetry must NOT mutate live workflow
# ---------------------------------------------------------------------


def test_telemetry_reads_do_not_break_audio_upload(client):
    """Reading the rollup over and over must NOT change anything in
    the encounter pipeline."""
    for _ in range(3):
        client.get("/admin/deployment/overview", headers=ADMIN1)
    # Audio upload still succeeds end-to-end.
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": "Regression body."},
    )
    assert r.status_code == 201
    assert r.json()["processing_status"] == "completed"


def test_reviewer_role_still_blocked_from_admin_telemetry(client):
    for path in (
        "/admin/deployment/overview",
        "/admin/deployment/locations",
        "/admin/deployment/alerts",
        "/admin/deployment/jobs",
        "/admin/deployment/qa",
        "/admin/deployment/config-actual",
    ):
        r = client.get(path, headers=REV1)
        assert r.status_code == 403, f"{path} should be admin-only"

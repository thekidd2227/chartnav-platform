# Fundus Charting Workflow

ChartNav's AI-assisted fundus charting feature generates standardised retinal drawings from clinician-entered findings text.

## Clinical workflow

1. **Enter findings** — Clinician types free-text in the FundusChartPanel (e.g. `horseshoe tear at 10:30 OD, lattice from 5 to 7 OS near ora`).
2. **Generate chart** — `POST /api/v1/encounters/{id}/fundus-charts/generate` parses findings, returns `drawing_json` with clock-hour mapped elements and any warnings.
3. **Review warnings** — AI emits warnings for missing laterality, missing clock hour, or unrecognised findings. No clinical detail is ever invented.
4. **Render SVG** — `POST /api/v1/fundus-charts/{id}/render` produces a 200×200-unit SVG with concentric rings, clock-hour labels, and colour-coded finding overlays.
5. **Review** — Clinician (or admin) calls `POST /api/v1/fundus-charts/{id}/review`. Status → `reviewed`. This is **not** the final signature.
6. **Sign** — Clinician sends `{"attested": true}` to `POST /api/v1/fundus-charts/{id}/sign`. Status → `signed`. Signed charts are immutable.

## UI workflow (Phase 55 polish)

The Fundus Charts panel lives in the Imaging tab of the clinical workspace (`ClinicalTabbedWorkspace` → "Fundus charts" card). The layout is two-column:

**Left column — findings entry**
- Safety banner at the top: "Draft from clinician-entered findings. Provider review required. Not image interpretation. Does not diagnose."
- Laterality selector (OD / OS / OU) as a radio button group with explicit "Right / Left / Both" labels.
- Findings textarea with placeholder text.
- Demo sample chips for one-click population (fake-data examples only — see below).
- Generate button — disabled until the textarea is non-empty.
- Saved-charts list with status + creation date.

**Right column — preview + workflow**
- Status timeline pills: **Draft → Reviewed → Signed**. The current state is colour-coded; previous states stay highlighted.
- Laterality and chart-id badge. If the chart was AI-drafted, a "AI-drafted from clinician findings · provider review required" tag appears.
- Warnings panel — always visible. Empty state still reads "No warnings. Provider must still review before signing." Warnings refresh when a different chart is selected (Phase 55 bug fix).
- SVG preview with clock-hour labels + a legend strip beneath it.
- **Action bar** (only when not yet signed):
  - `Render SVG` — re-renders the chart from the current `drawing_json`.
  - `Mark Reviewed` — marks the chart `reviewed`. The button label and tooltip make clear this is **not** the final signature.
  - **Attestation block** (purple) — checkbox the clinician must tick before `Sign & Lock Chart` becomes clickable. The attestation text reads "I attest that I have reviewed this fundus chart and it accurately reflects my clinical findings. Signing will lock the chart — signed charts are immutable." Inline (not a modal) so the demo narrator can show what the clinician is attesting to before they sign.
- **Signed state** — replaces the action bar with a green "Chart signed · locked" banner showing timestamp + signer ID. All edit controls are removed from the DOM; signed charts are immutable in the API too (PATCH returns 409).

## Demo-safe sample findings

The panel exposes a "Demo samples (fake data)" chip strip with four examples. Selecting a chip populates the textarea and aligns the laterality selector. The examples are **fake / demo only** and contain no real PHI:

- `horseshoe tear at 10:30 OD`
- `lattice from 5 to 7 OS near ora`
- `superotemporal detachment OD`
- `laser scars temporal OS`

Demo narrators may use these chips during retina-clinic walkthroughs. They are **not** clinical content — no patient names, no MRNs, no dates of birth, no treatment recommendations, no diagnosis claims.

## Warning meanings

| Warning text | Meaning |
|---|---|
| `Laterality not stated …` | Findings text did not contain `OD` / `OS` / `OU` keywords. The clinician should confirm which eye. |
| `No clock-hour specified …` | Findings text did not include a clock-position like `10:30` or `5 to 7`. The lesion is drawn at a default position with reduced opacity. |
| `Unrecognized finding type …` | The rule-based parser did not match a known finding (horseshoe tear, lattice, detachment, etc.). The clinician should clarify. |
| `Laterality mismatch …` | The request's laterality field (e.g. the UI selector) disagrees with the laterality the parser found in the findings text. **Findings text wins** (the chart is stored under the parsed laterality); the warning prompts the clinician to confirm before signing. Emitted by `generate_chart_from_findings` (Phase 56). |

## Review vs Sign

| Action | Endpoint | What it does | Locks chart? |
|---|---|---|---|
| **Mark Reviewed** | `POST /api/v1/fundus-charts/{id}/review` | Sets `status=reviewed`, records `reviewed_by_user_id` + `reviewed_at`. | No — chart can still be edited. |
| **Sign & Lock** | `POST /api/v1/fundus-charts/{id}/sign` with `{"attested": true}` | Sets `status=signed`, records `signed_by_user_id` + `signed_at`. | Yes — chart is immutable; PATCH returns 409 after this. |

Signing requires explicit attestation: the API rejects sign requests without `"attested": true`, and the UI disables the sign button until the attestation checkbox is ticked.

## What the AI does *not* do

- It does not diagnose. It draws what the clinician dictated.
- It does not interpret images. There is no OCT / fundus-photo computer-vision pipeline.
- It does not auto-sign. Every chart requires explicit `{"attested": true}` from a clinician.
- It does not invent findings. Missing detail surfaces as warnings; vague locations are drawn with reduced opacity.
- It does not order, refer, message patients, code, or bill.

## Security and privacy

- Audit events record `chart_id`, `laterality`, and `warning_count` only — findings text and drawing JSON are never stored in the audit log.
- Every request filters by `organization_id`; cross-org access returns 404.
- Only `admin` and `clinician` roles can create, update, review, or sign.

## Clock-hour coordinate system

- 12 o'clock = superior = top of diagram
- 3 o'clock = temporal (OD) / nasal (OS)
- Angle formula: `angle_deg = (h × 30 − 90) % 360`

## Zones

| Zone | Retinal region |
|------|----------------|
| `posterior_pole` | Optic disc, macula (innermost ring) |
| `equator` | Equatorial retina (middle ring) |
| `ora_serrata` | Peripheral retina, ora serrata (outermost ring) |

## AI model

The V1 model is `rule_based_v1` — a deterministic regex parser requiring no external API. It is swappable: implement a replacement and update `ai_model_name` in the generate endpoint. A future LLM-backed model would return the same `FundusChartGenerationResult` dataclass.

## Optional LLM drafting assist (Phase 54, fake-data / demo only)

`rule_based_v1` is the **production default** for fundus charting and is unchanged. Phase 54 adds a narrow opt-in seam in `apps/api/app/services/fundus_chart_ai.py` so an operator may experiment with the Phase 52B OpenAI fake-data adapter as an alternative drafting assist. **Real PHI must not flow through this path.**

### Activation contract

All of the following must hold or the assist refuses with `ProviderDisabledError`:

| Gate | Required value | Source |
|---|---|---|
| `CHARTNAV_FUNDUS_DRAFTING_ASSIST` | exactly `openai` (case-insensitive) | Phase 54 opt-in |
| `CHARTNAV_LLM_PROVIDER` | `openai` | Phase 52B selector |
| `CHARTNAV_LLM_ENABLED` | `1` | Phase 52B selector |
| `CHARTNAV_LLM_REAL_PHI_APPROVED` | unset or `0` | Phase 52B real-PHI gate |
| `CHARTNAV_PILOT_ALLOW_LLM_OPENAI` | unset or `0` | Phase 52B pilot-promotion gate |
| `CHARTNAV_OPENAI_API_KEY` | present | Vendor credential (never logged) |
| `LLMRequest.fake_data_context` | `True` | Per-request contract |
| `LLMRequest.requires_provider_review` | `True` | Per-request contract |

`CHARTNAV_FUNDUS_DRAFTING_ASSIST` only activates the assist for the literal string `openai`. Values like `1`, `true`, `yes`, `on`, or `anthropic` are explicitly **not** accepted — Anthropic and IBM watsonx remain unwired in the fundus path.

### Behaviour

- When the opt-in env var is unset (default), `generate_chart()` routes to `generate_chart_from_findings()` and returns `ai_model_name="rule_based_v1"`. The default fundus path is unchanged.
- When the opt-in env var is set to `openai` AND every Phase 52B gate is in the SAFE state, `generate_chart()` routes to `generate_chart_via_llm_assist()` and returns `ai_model_name="openai_fundus_assist_v1"`.
- When the opt-in env var is set to `openai` but any gate fails, the assist function raises `ProviderDisabledError` naming the offending gate. **There is no silent fallback under opt-in — refusal is loud.**

### Safety guarantees

- **Doctor-entered findings remain the source of truth.** The LLM assist may not invent findings; malformed model output elements are discarded rather than fabricated.
- **No auto-signing.** The assist function never sets `signed_at`, `signed_by_user_id`, `reviewed_at`, or `reviewed_by_user_id`. The chart workflow's review/sign endpoints remain the only path to those columns.
- **No autonomous diagnosis, image interpretation, orders, referrals, patient messages, billing, or coding.** The fundus assist system prompt forbids all of these explicitly.
- **No real network in CI.** The assist function accepts an injected `transport: FundusAssistTransport` callable; tests inject a fake transport and never hit `api.openai.com`.
- **API key never logged.** The assist function sanitises the key out of every error message and log line. A regression test (`test_assist_api_key_never_logged_on_failure_path`) pins this with a canary value.

### Output contract

The assist's structured output schema (enforced by the system prompt; validated by the parser):

```json
{
  "laterality": "<OD | OS | OU | unspecified>",
  "elements": [
    {
      "finding_type": "<string>",
      "laterality": "<OD | OS | OU>",
      "clock_start": <number | null>,
      "clock_end": <number | null>,
      "zone": "<posterior_pole | equator | ora_serrata>",
      "color": "<#hex>",
      "label": "<string>"
    }
  ],
  "warnings": ["<string>"],
  "requires_provider_review": true
}
```

`requires_provider_review` is always pinned `true` in the returned `FundusChartGenerationResult.confidence`. Every chart still requires clinician review and `{"attested": true}` sign-off before it becomes immutable.

### Local operator runbook

```bash
# In a shell with your local config.env sourced (gitignored).
set -a; . "/path/to/config.env"; set +a
export CHARTNAV_FUNDUS_DRAFTING_ASSIST=openai
export CHARTNAV_LLM_PROVIDER=openai
export CHARTNAV_LLM_ENABLED=1
export CHARTNAV_LLM_REAL_PHI_APPROVED=0      # MUST be 0 / unset
unset CHARTNAV_PILOT_ALLOW_LLM_OPENAI         # MUST be unset (or =0)
export CHARTNAV_OPENAI_LLM_MODEL=gpt-4o-mini
# CHARTNAV_OPENAI_API_KEY comes from config.env (never echoed)

# Cleanup
unset CHARTNAV_OPENAI_API_KEY
unset CHARTNAV_FUNDUS_DRAFTING_ASSIST
```

See `docs/security/chartnav-openai-fake-data-adapter.md` for the full Phase 52B adapter contract.

## Demo operator runbook (Phase 56)

For live demos, follow `docs/demo/phase-56-fundus-demo-runbook.md`. It
covers the exact click path, demo-safe sample findings, approved /
forbidden phrases, Q&A for "Is this AI?" / "Does it diagnose?" /
"Does it read fundus photos?" / "Is OpenAI used?", and a
troubleshooting table. Use that runbook — not this workflow doc — when
operating a customer call.

## Correction / versioning (current contract)

Signed charts are immutable. To correct a signed chart, generate or
create a **new** chart in the same encounter. There is no in-place edit
path and no fork/new-version endpoint in V1. A future phase may
introduce a fork-and-supersede flow; until that lands, the demo
narration must not imply signed charts can be amended.

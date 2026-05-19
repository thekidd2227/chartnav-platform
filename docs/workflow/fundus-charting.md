# Fundus Charting Workflow

ChartNav's AI-assisted fundus charting feature generates standardised retinal drawings from clinician-entered findings text.

## Clinical workflow

1. **Enter findings** — Clinician types free-text in the FundusChartPanel (e.g. `horseshoe tear at 10:30 OD, lattice from 5 to 7 OS near ora`).
2. **Generate chart** — `POST /api/v1/encounters/{id}/fundus-charts/generate` parses findings, returns `drawing_json` with clock-hour mapped elements and any warnings.
3. **Review warnings** — AI emits warnings for missing laterality, missing clock hour, or unrecognised findings. No clinical detail is ever invented.
4. **Render SVG** — `POST /api/v1/fundus-charts/{id}/render` produces a 200×200-unit SVG with concentric rings, clock-hour labels, and colour-coded finding overlays.
5. **Review** — Clinician (or admin) calls `POST /api/v1/fundus-charts/{id}/review`. Status → `reviewed`.
6. **Sign** — Clinician sends `{"attested": true}` to `POST /api/v1/fundus-charts/{id}/sign`. Status → `signed`. Signed charts are immutable.

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

# ChartNav Release Evidence Checklist

Release / PR number:

Commit SHA:

Branch:

CI links:

## Required Results

| Check | Result | Evidence / link | Notes |
| --- | --- | --- | --- |
| Backend SQLite tests | pending |  |  |
| Backend Postgres tests | pending |  |  |
| Frontend typecheck | pending |  |  |
| Frontend tests | pending |  |  |
| Frontend build | pending |  |  |
| Docker build/smoke | pending |  |  |
| E2E tests | pending |  |  |
| Docs regeneration | pending |  |  |
| Commercial claim scanner | pending |  | `bash scripts/check_commercial_claims.sh` |
| Website claim scanner | pending |  | `bash scripts/check_website_claims.sh` |
| Demo claim scanner | pending |  | `bash scripts/check_demo_claims.sh` |
| Claim policy fixture tests | pending |  | `bash scripts/test_claim_policy_fixtures.sh` |
| Runtime safety validator | pending |  | `python3 scripts/check_runtime_safety.py` |
| Alembic head check | pending |  | `bash scripts/check_alembic_safety.sh` |
| Migration upgrade check | pending |  | Included in Alembic safety check when feasible |
| Demo reset check, if relevant | not applicable |  |  |
| Backup/restore smoke, if relevant | not applicable |  |  |

## Confirmations

- No real PHI processed:
- No production LLM enabled:
- No public marketing claim changes:
- No autonomous diagnosis added:
- No image interpretation added:
- No orders/referrals/patient messaging/billing/coding automation added:
- No deployment performed:

## Known Risks

-

## Go / No-Go

Decision: pending

Approver:

Date:

# Phase C — Security Posture and BAA Readiness

## 1. Problem solved
MSO and multi-site practice procurement teams will not sign a BAA, let
alone a subscription, without a security package they can hand to
their compliance officer. Answering these questions reactively by
email costs weeks per deal. A publishable security-posture document,
paired with a pre-reviewed BAA template, collapses that cycle.

## 2. Current state (architectural reality)
- Transport security: TLS is terminated at a reverse proxy / load
  balancer supplied by the deployment operator. ChartNav ships HTTP
  internally on a private network and documents this expectation.
- Data at rest: Postgres is the system of record. At-rest encryption
  is a responsibility of the deployment operator's storage layer. The
  deployment guide states this explicitly; ChartNav does not advertise
  at-rest encryption as an application-layer feature because it is not.
- Access control: RBAC is enforced server-side on every route via
  `ensure_same_org` plus role-check decorators in
  `backend/app/middleware/auth.py`. There is no client-side-only
  gating anywhere in the product.
- Audit trail:
  - `security_audit_events` captures authentication, authorization
    failures, password changes, role changes, session revocations.
  - `workflow_events` captures clinical state transitions: draft
    creation, pre-sign checkpoint passage, sign, amendment.
  - The evidence chain is hash-linked across events with an optional
    HMAC seal when `EVIDENCE_HMAC_KEY` is configured.
- Session governance: `user_sessions` table, logout revokes the
  session row, configurable idle timeout, forced re-auth on role
  change.
- Retention: `backend/scripts/audit_retention.py` rotates audit records
  per the operator's retention policy. Deployment operator runs this
  on a cadence documented in the runbook.
- Supply chain: SBOM produced per release, container image pinned by
  digest, runs as non-root, healthcheck endpoint.
- Accessibility: Axe-AA gate enforced in CI on the frontend.
- Testing: 231 backend tests, 55 frontend tests.

What ChartNav is not:
- Not SOC 2 audited. Not HITRUST certified. Not ISO 27001 certified.
- HIPAA posture is architectural and operational; it has not been
  audited by an independent third party.
- No penetration test report from a named firm.

## 3. Required state
A publishable security posture document, a BAA template reviewed by
outside counsel, a release-compliance checklist, and a deployment-
operator security runbook. Together these form the "data room" a
buyer's compliance officer can review without a live call.

## 4. Acceptance criteria
- `docs/chartnav/security/security-posture.md` exists and is
  versioned; every section in Section 5 is present and current.
- `docs/chartnav/legal/BAA-template.md` exists with the fields listed
  in Section 5.
- `docs/chartnav/security/release-compliance-checklist.md` is linked
  from the release runbook and is required to be green before a
  release tag is cut.
- A new endpoint `GET /about/security` returns a JSON manifest of
  posture facts (encryption-in-transit stance, audit event counts,
  evidence chain HMAC enabled bool, last retention-script run-time)
  for consumption by the operator dashboard.
- Pytest: `backend/tests/test_about_security.py` validates the shape
  of the manifest and that HMAC-enabled is surfaced honestly.
- Frontend: `data-testid="posture-manifest-card"` on the operator
  dashboard renders the manifest.

## 5. Codex implementation scope
Create:
- `docs/chartnav/security/security-posture.md` with sections:
  architecture overview, data flows, transport encryption, at-rest
  encryption (operator responsibility), authentication, RBAC, audit
  logging and evidence chain, session governance, retention and
  deletion, incident response, subcontractors, release process,
  accessibility, known non-certifications.
- `docs/chartnav/legal/BAA-template.md` with fields: covered entity,
  business associate, permitted uses and disclosures, subcontractor
  list (host cloud if applicable, DNS provider, error-telemetry
  provider if any), breach notification timelines, safeguards
  attestation, data-return-or-destruction clause on termination,
  termination for breach, governing law placeholder.
- `docs/chartnav/security/release-compliance-checklist.md`
- `docs/chartnav/runbooks/deployment-operator-security.md`
- `backend/app/routes/about_security.py`
- `backend/tests/test_about_security.py`
- `frontend/src/components/admin/PostureManifestCard.tsx`

Modify:
- `backend/app/routes/__init__.py` to register `about_security`
- `frontend/src/pages/admin/Dashboard.tsx` to mount the manifest card

BAA template skeleton:

```markdown
# Business Associate Agreement (Template)

Effective Date: [DATE]
Covered Entity: [LEGAL NAME]
Business Associate: [CHARTNAV LEGAL ENTITY]

1. Definitions
2. Permitted Uses and Disclosures
3. Safeguards (administrative, physical, technical)
4. Subcontractors
   - Hosting: [operator-controlled or named cloud]
   - Telemetry: [none | named vendor]
5. Breach Notification
   - Notice to Covered Entity: within [N] days of discovery
6. Access, Amendment, Accounting of Disclosures
7. Return or Destruction on Termination
8. Term and Termination
9. Governing Law: [STATE]
10. Signatures
```

Posture manifest JSON shape (from `GET /about/security`):

```json
{
  "product_version": "x.y.z",
  "tls_termination": "operator_managed",
  "at_rest_encryption": "operator_managed",
  "rbac_enforced": true,
  "session_idle_timeout_minutes": 15,
  "evidence_chain_hmac_enabled": true,
  "audit_retention_last_run": "2026-04-20T03:00:00Z",
  "certifications": []
}
```

The `certifications` array is intentionally empty until an audit is
completed. No value is ever injected that is not literally true.

## 6. Out of scope / documentation-or-process only
- SOC 2 Type I or Type II engagement. Budget, scope, and auditor
  selection are a commercial decision, not a Codex task.
- Penetration test engagement. Same reasoning.
- ISO 27001 or HITRUST. Not pursued in v1.
- State-specific addenda (TX HB300, CA CMIA) beyond noting them in
  the template as buyer-supplied redlines.

## 7. What can be demoed honestly now vs later
Now: the posture doc, the BAA template, the `/about/security` manifest,
the audit tab showing `security_audit_events` and `workflow_events`,
the evidence chain visualization, the release checklist.

Later, after an audit engagement: the posture doc's
`certifications` array contains entries; the marketing site displays
audit logos; RFP responses cite audit report identifiers.

## 8. Dependencies
- Existing audit tables and evidence chain are the substrate; no
  schema changes required.
- Outside counsel review of the BAA template is a blocking external
  dependency before it can be offered to buyers.

## 9. Truth limitations
- ChartNav is not certified under SOC 2, HITRUST, or ISO 27001 and
  this document is not a substitute for such certification.
- The posture document describes what the product enforces; the
  deployment operator remains responsible for the environment around
  it, including at-rest encryption and network segmentation.
- "Evidence chain HMAC enabled" reflects the runtime setting at manifest
  fetch time; it is not a guarantee of prior-period integrity without
  operator-side key management.

## 10. Risks if incomplete
- Procurement stalls indefinitely at the security-questionnaire stage.
- Buyers receive ad hoc answers from sales that later diverge from
  reality, creating a trust loss that kills renewal.
- Competitors with a ready data room close deals we would otherwise win
  on clinical merit.

# ChartNav Access Control Policy

> **Phase:** 23.
> **Type:** Policy applied to any ChartNav environment that may
> process real PHI under a controlled-pilot deployment. Practice
> reviews and accepts this policy as part of Gate 2 of
> `chartnav-real-phi-go-live-gate.md`.

## 1. Authentication mode

- **Production / controlled-pilot:** `CHARTNAV_AUTH_MODE=bearer`
  only. The header-mode auth (`X-User-Email`) is **forbidden**
  in any environment that may process real PHI. The validator
  (`scripts/validate_controlled_pilot_env.sh`) gates on this.
- **Development / demo / CI:** header-mode is acceptable on
  fake-data only.

## 2. Identity provider

- ChartNav delegates authentication to a practice-managed
  identity provider via OIDC / JWKS.
- Required env vars: `CHARTNAV_JWT_ISSUER`, `CHARTNAV_JWT_AUDIENCE`,
  `CHARTNAV_JWT_JWKS_URL`.
- ChartNav validates signature, issuer, audience, and expiry on
  every request. 11 dedicated tests cover this.

## 3. Multi-factor authentication

- **MFA is required at the identity provider** for every user
  with PHI access.
- Practice is responsible for enforcing MFA in its IdP policy.
- ChartNav does not provide its own MFA — it delegates to the
  IdP.

## 4. Least privilege

- ChartNav implements five roles: `admin`, `clinician`,
  `reviewer`, `technician`, `front_desk`.
- Each role has the narrowest access required to do its job
  (see `apps/api/app/authz.py` and the per-phase implementation
  docs).
- Writes on most resources are admin / clinician only;
  technician has create-only on operational measurement events;
  reviewer is read-only on clinical surfaces; front-desk has no
  access to clinical surfaces.
- Cross-organization access is **forbidden** and returns `404`
  (no existence leak) — not `403`.

## 5. Role review cadence

- Practice reviews assigned ChartNav roles **quarterly** at
  minimum.
- Any change of practice role (hire / promotion / termination)
  triggers an immediate ChartNav role review.
- Evidence: practice's role-review log.

## 6. User termination

- When a practice user is terminated, the practice must:
  1. Disable the user at the identity provider **immediately**.
  2. Within 24 hours, revoke any active ChartNav sessions
     (token revocation at the IdP, or wait for token expiry).
  3. Within 7 days, deactivate the user's ChartNav user row via
     the admin panel.
- Audit retention captures the user's historical activity for
  the agreed retention duration.

## 7. Admin access logging

- All admin-write operations record metadata-only audit rows in
  `security_audit_events`.
- Admin reads of `/admin/security/{ai-activity,events,posture,readiness}`
  do not currently audit; the access is gated by the admin role
  itself, which is provisioned only via the practice.
- A future enhancement could audit admin reads; practice may
  request this.

## 8. Shared accounts prohibited

- Each individual must have a unique ChartNav user. No shared
  logins, no service accounts with PHI access.
- The `users.email` unique constraint enforces this.

## 9. Session timeout

- Session timeout is enforced at the identity provider.
- Recommended timeout: 8 hours for clinical roles; 1 hour for
  admin role. Practice may adjust per its policy.

## 10. Support access approval

- ChartNav support staff have **no access** to the practice's
  controlled-pilot environment by default.
- Read-only support access requires written practice approval
  for a specific time window.
- Approved access generates audit events visible to the
  practice's admin.
- See `chartnav-support-phi-handling-policy.md` for the support
  process.

## 11. Special access (emergency / break-glass)

- ChartNav does not currently provide a break-glass mechanism.
- Emergency access requires the practice to use its standard
  admin role temporarily; the audit trail captures all activity.

## 12. Workstation / device security

- Practice is responsible for workstation security (encryption,
  OS patching, screen locking, MFA on the device, etc.).
- ChartNav assumes a hardened workstation; it does not
  re-implement OS-level controls.

## 13. API tokens

- Per-request bearer tokens are short-lived and issued by the
  identity provider.
- ChartNav does not issue long-lived API tokens for production
  use.
- Service-to-service integrations (if added) must be authorized
  through the same IdP with explicit scopes.

## 14. Cross-organization isolation

- Every database table is `organization_id`-scoped.
- Every endpoint validates the resource belongs to
  `caller.organization_id`.
- Cross-org reads / writes return `404` with the
  no-existence-leak invariant.
- 100+ tests across Phase 20B / 20C / 21A / 21B / 22 cover this
  contract.

---

## Policy review cadence

This policy is reviewed:

- Annually.
- On any material change to ChartNav's authentication or
  authorization architecture.
- After any access-control-related incident.

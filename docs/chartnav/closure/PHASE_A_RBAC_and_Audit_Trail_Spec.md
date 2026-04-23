# Phase A — RBAC and Audit Trail Spec

## 1. Problem solved

The buyer brief flagged that ChartNav's role model (admin / clinician / reviewer + a dormant `front_desk`) does not match how an ophthalmology practice actually runs. A real clinic has a front desk, a tech who pre-charts vitals and workup, the physician who examines and signs, a biller/coder who codes and submits, and an admin. Three seeded roles do not cover that shape. Without a complete role matrix, least-privilege and audit claims are soft.

This spec closes that gap by defining five roles end to end — access matrix, migration path, seed data, authz test coverage, and UI surface — plus the audit-trail contract that underpins every role decision.

## 2. Current state

- Roles enforced in code: `admin`, `clinician`, `reviewer`. `front_desk` is referenced in `apps/api/app/core/authz.py` (e.g. `canCreateEncounter`) but no user with that role is seeded and the DB `users.role` CHECK constraint does not list `technician` or `biller_coder`.
- Seed users:
  - org1 (`chartnav.local`): `admin@`, `clin@`, `rev@`
  - org2 (`northside.local`): `admin@`, `clin@`
- `ensure_same_org` is called on every authorized endpoint in `apps/api/app/api/routes.py`. Role check is a second gate.
- `security_audit_events` records authn events (login, role-guard denial, cross-org access attempt). `workflow_events` records encounter transitions.
- Axe-AA gate in `qa/a11y/` covers the roles that are currently rendered.

## 3. Required state

Five roles, defined and enforced:

| Capability | front_desk | technician | clinician | biller_coder | admin |
|---|---|---|---|---|---|
| Read patient demographics | R/W | R | R | R | R/W |
| Schedule / reminders | R/W | R | R | R | R/W |
| Create encounter (draft) | Yes | Yes | Yes | No | Yes |
| Chart VA/IOP/pre-workup | No | R/W | R/W | No | R/W |
| Chart assessment/plan | No | No | R/W | No | R/W |
| Sign encounter | No | No | Yes (author only) | No | No |
| Read signed note | No | Read own-org | Read own-org | Read own-org | Read own-org |
| Edit CPT/ICD picks | No | No | R/W pre-sign | R/W pre-export | R/W |
| Export bundle | No | No | Yes | Yes | Yes |
| Read audit events | No | No | Self only | No | Org |
| Read revision history | No | No | Own authored | No | Org |
| User / role management | No | No | No | No | Yes |

- `technician` and `biller_coder` are added to the `users.role` CHECK constraint.
- Two new seed users: `tech@chartnav.local`, `billing@chartnav.local` (org1 only; org2 seeds untouched to preserve multi-tenant separation proof).
- Role chip in the app header reflects the authenticated role.

## 4. Acceptance criteria

- Migration `apps/api/migrations/00XX_extend_user_roles.sql` adds `technician` and `biller_coder` to the CHECK constraint.
- `apps/api/app/core/authz.py` exposes typed guards: `can_create_encounter`, `can_chart_vitals`, `can_chart_assessment`, `can_sign`, `can_export`, `can_read_audit`, `can_manage_users`.
- Every route in `apps/api/app/api/routes.py` calls exactly one guard plus `ensure_same_org`.
- Extended tests land in `apps/api/tests/test_security_wave2.py` with one case per (role × guarded-action) cell in the matrix above — positive and negative paths.
- Seed script `apps/api/scripts/seed_dev.py` adds `tech@` and `billing@` with known passwords documented in `docs/chartnav/dev/dev_accounts.md` (dev-only, never prod).
- UI role chip — `data-testid="role-chip"` — renders exactly one of: `front_desk`, `technician`, `clinician`, `biller_coder`, `admin`.
- Denied actions surface a consistent error: HTTP 403, body `{"error_code": "ROLE_FORBIDDEN", "required": "<guard_name>"}`. A corresponding `security_audit_events` row is written with `event_type="role_denied"`.

## 5. Codex implementation scope

Migration:

```sql
-- 00XX_extend_user_roles.sql
-- SQLite: rebuild the table because CHECK constraints are immutable
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users_new (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  org_id INTEGER NOT NULL REFERENCES orgs(id),
  role TEXT NOT NULL CHECK (role IN
    ('front_desk','technician','clinician','biller_coder','admin','reviewer')),
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users_new SELECT * FROM users;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
COMMIT;
PRAGMA foreign_keys=ON;
```

Code:

- `apps/api/app/core/authz.py` — rewrite role guards as a dispatch table keyed by `(role, capability)`. Keep `reviewer` as an auxiliary read role alongside the five clinic-role matrix.
- `apps/api/app/api/routes.py` — replace ad-hoc role checks at every endpoint with the new guards.
- `apps/api/app/models/security_audit_event.py` — extend enum to include `role_denied`.
- Frontend: `apps/web/src/features/auth/RoleChip.tsx`, and role-aware nav visibility in the sidebar.

## 6. Out of scope / documentation-or-process only

- Break-glass access workflow (admin elevating into clinician to read a chart in a support case) — documented in `docs/chartnav/policy/break_glass.md`, not implemented.
- SSO / SAML integration (Okta, Azure AD) — parked.
- Fine-grained per-field ACLs (per-section write rules inside a template) — parked to Phase B.

## 7. Demo honestly now vs. later

**Now:** log in as each of the five roles and walk the product — front desk schedules, tech drafts and charts vitals, clinician charts assessment and signs, biller reviews codes and exports, admin manages users and reads org audit. Every forbidden action is shown to fail cleanly with the audit row.

**Later:** approval workflows that require two roles to act (e.g. admin + clinician to amend a signed note via addendum); SSO; customer-configurable roles.

## 8. Dependencies

- Phase A Structured Charting and Attestation (guards depend on the sign state and on revision visibility).
- Phase A Encounter Templates (tech vs. clinician boundary depends on section keys defined by templates).

## 9. Truth limitations

- Roles are coarse-grained. We are not claiming row-level security inside Postgres or per-field attribute-based access control.
- Audit trail is at the application layer, captured in SQLite (pilot) or Postgres (prod). We do not ship a WORM store or SIEM integration in Phase A.
- `reviewer` remains in the schema as a legacy/QA role. It is not part of the five-role matrix above and should not be assigned to clinical staff.

## 10. Risks if incomplete

- A tech or front-desk user can accidentally sign or export a record; or cannot chart the fields they actually own. Pilot workflow stalls on day one.
- Buyer security review finds that `front_desk` exists in code but nobody uses it, or that `technician` does not exist at all. Signals that "ophthalmology-first" is marketing, not engineering.
- Incomplete audit rows make post-incident review inconclusive — the opposite of the reason a clinic would choose a structured platform.

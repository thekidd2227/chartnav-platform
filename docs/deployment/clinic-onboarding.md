# Clinic onboarding

The administrative flow to bring a medical office onto hosted ChartNav, and the
exact experience clinic staff see.

## Provisioning flow (ChartNav operator + clinic admin)

1. **Organization provisioning** — create the clinic's `organization` (slug,
   display name). Synthetic demo tenants are kept separate from real tenants and
   are never seeded in production (`entrypoint.sh` refuses `seed` when
   `CHARTNAV_ENV=prod`).
2. **First administrator invitation** — invite the clinic's first admin
   (admin-security flow; user created with `role=admin`, `is_active`, bound to
   the org). Identity + credential live in the IdP.
3. **Role assignment** — admin assigns staff roles: `admin`, `clinician`,
   `reviewer`, plus operational roles (front desk, technician) where applicable.
4. **Location creation** — admin adds the clinic's location(s).
5. **Staff invitations** — admin invites staff; each accepts via the IdP.
6. **Account disablement** — admin can deactivate a user (`is_active=false`);
   disabled users fail auth.
7. **Invitation expiration** — invitations expire (see user-invitation fields /
   `admin-security`); expired invites cannot be redeemed.
8. **Password reset / MFA** — delegated to the IdP. ChartNav never stores
   passwords or MFA secrets.
9. **Branding** — clinic branding configuration only where already supported;
   not a blocker for onboarding.

## What clinic staff experience

| Item | Detail |
|---|---|
| Web URL | `https://app.chartnavmd.com` |
| Supported browsers | Chrome, Edge, Safari, Firefox (latest 2 versions) |
| Invitation | Secure email from the IdP / ChartNav admin |
| MFA setup | At first sign-in, enrolled in the IdP |
| First login | OIDC sign-in → ChartNav loads their org's workspace |
| Staff invitations | Clinic admin invites colleagues in-app |
| Support contact | `support@chartnavmd.com` (placeholder — confirm before launch) |
| Downtime / maintenance | Communicated in advance; rolling ECS deploys aim for zero-downtime; maintenance windows posted |

## Status

The org/admin/role/location/disablement/invitation primitives exist in the
backend (admin-security + native patients/providers). A polished end-to-end
self-serve onboarding UI and the production IdP wiring are **not yet
operational**; this documents the intended delivery experience.

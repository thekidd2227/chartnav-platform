// Dev identity persistence. In `header` auth mode the only piece of
// "identity" we carry is an email string sent as `X-User-Email`.
// Persisted in localStorage so refreshes don't lose the selection.

const KEY = "chartnav.devIdentity";

export const SEEDED_IDENTITIES: { email: string; label: string }[] = [
  { email: "admin@chartnav.local", label: "Org 1 · admin" },
  { email: "clin@chartnav.local", label: "Org 1 · clinician" },
  { email: "rev@chartnav.local", label: "Org 1 · reviewer" },
  // Phase 20C — operational roles for role-based dashboards.
  { email: "front@chartnav.local", label: "Org 1 · front desk" },
  { email: "tech@chartnav.local", label: "Org 1 · technician" },
  { email: "admin@northside.local", label: "Org 2 · admin" },
  { email: "clin@northside.local", label: "Org 2 · clinician" },
  { email: "front@northside.local", label: "Org 2 · front desk" },
  { email: "tech@northside.local", label: "Org 2 · technician" },
];

export function loadIdentity(): string {
  try {
    const v = localStorage.getItem(KEY);
    if (v && v.trim()) return v.trim();
  } catch {
    // localStorage unavailable (SSR, strict sandbox) — fall through
  }
  return SEEDED_IDENTITIES[0].email;
}

export function saveIdentity(email: string): void {
  try {
    localStorage.setItem(KEY, email);
  } catch {
    // best effort
  }
}

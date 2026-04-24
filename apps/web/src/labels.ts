// Display-label helpers — the single source of truth for how
// ChartNav renders human-facing text over system-facing fields.
//
// Why: the product previously led with internal references
// (#123, PT-1001, Loc #1, review_needed). Front-desk and
// low-training users had no anchor for "what is this?" or
// "what do I do next?". These helpers push internal IDs to
// secondary/detail positions and promote human answers —
// patient name, visit context, workflow stage, next action —
// to the primary label slots.
//
// Every helper is pure. No React, no API calls. Safe to unit-test.

import type { Encounter, Role } from "./api";

// ---------------------------------------------------------------------
// Canonical workflow stage model
// ---------------------------------------------------------------------
//
// The encounters table today carries these raw statuses:
//   scheduled, in_progress, review_needed, completed, abandoned
//
// The human-facing labels must be consistent across list view,
// day view, month view, encounter detail, the Note Workspace,
// and any admin surface. `formatStatus` is the ONLY place that
// maps raw → human. Do not inline this mapping anywhere else.
export type EncounterStatus =
  | "scheduled"
  | "in_progress"
  | "review_needed"
  | "completed"
  | "abandoned";

export const STATUS_LABEL: Record<string, string> = {
  scheduled: "Scheduled",
  in_progress: "In progress",
  review_needed: "Ready for review",
  completed: "Signed",
  abandoned: "Needs correction",
};

export function formatStatus(status: string | null | undefined): string {
  if (!status) return "—";
  return STATUS_LABEL[status] ?? status.replace(/_/g, " ");
}

// A short "what should I do next?" cue per status. Intentionally
// plain and action-oriented. Rendered as a subtitle on cards and
// in the Note Workspace header.
export const NEXT_ACTION_BY_STATUS: Record<string, string> = {
  scheduled: "Check the patient in when they arrive.",
  in_progress: "Continue the exam; capture dictation or notes.",
  review_needed: "Review findings and sign the note when ready.",
  completed: "Signed. Export or transmit as needed.",
  abandoned: "Resolve the blocker, then return to review.",
};

export function nextActionFor(status: string | null | undefined): string | null {
  if (!status) return null;
  return NEXT_ACTION_BY_STATUS[status] ?? null;
}

// ---------------------------------------------------------------------
// Patient / encounter naming
// ---------------------------------------------------------------------

/** The primary display name for a patient/encounter row. Falls
 *  back through patient_name → patient_identifier → "Unnamed
 *  patient" so the headline slot is never a bare system ID. */
export function patientDisplayName(
  e: Pick<Encounter, "patient_name" | "patient_identifier">
): string {
  const name = (e.patient_name ?? "").trim();
  if (name) return name;
  const mrn = (e.patient_identifier ?? "").trim();
  if (mrn) return mrn;
  return "Unnamed patient";
}

/** Short MRN line for secondary positions. Returns a string the
 *  caller can render in a `.sub` slot beside or beneath the
 *  primary name. Empty string when the MRN would be redundant
 *  (i.e. the primary label already displays it). */
export function patientMrnSecondary(
  e: Pick<Encounter, "patient_name" | "patient_identifier">
): string {
  const name = (e.patient_name ?? "").trim();
  const mrn = (e.patient_identifier ?? "").trim();
  if (!name) return ""; // MRN is already the primary label; don't repeat
  return mrn ? `MRN ${mrn}` : "";
}

// ---------------------------------------------------------------------
// Location / provider helpers
// ---------------------------------------------------------------------

export interface LocationLike {
  id: number;
  name: string;
}

/** Render a location by looking it up in the shared cache. Falls
 *  back to the bare name (never "Loc #1" — if the cache is cold,
 *  we show a softer "Clinic" so the user isn't confronted with a
 *  raw id). */
export function formatLocation(
  locationId: number | null | undefined,
  cache: LocationLike[] | null | undefined
): string {
  if (locationId == null) return "Clinic not set";
  const row = (cache ?? []).find((l) => l.id === locationId);
  if (row?.name) return row.name;
  return "Clinic";
}

/** Provider display — strips titles collisions and never exposes
 *  a `#id`. Accepts the denormalized provider_name column. */
export function formatProvider(
  providerName: string | null | undefined
): string {
  const raw = (providerName ?? "").trim();
  return raw || "Unassigned provider";
}

// ---------------------------------------------------------------------
// Visit type / activity cues
// ---------------------------------------------------------------------

/** Short visit-type label. ChartNav doesn't store a structured
 *  visit_type today; we infer a friendly label from the most-
 *  recent activity timestamp + any bridged external source. */
export function formatVisitContext(e: Encounter): string {
  if ((e as any).scheduled_at) return "Scheduled visit";
  if ((e as any).started_at) return "In-clinic visit";
  if ((e as any).completed_at) return "Completed visit";
  return "Visit";
}

// ---------------------------------------------------------------------
// Role + blocker helpers
// ---------------------------------------------------------------------

export const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  clinician: "Clinician",
  reviewer: "Reviewer",
  front_desk: "Front desk",
  technician: "Technician",
  biller_coder: "Biller / Coder",
};

export function formatRole(role: Role | string | null | undefined): string {
  if (!role) return "Role not assigned";
  return ROLE_LABEL[role] ?? String(role).replace(/_/g, " ");
}

/** Friendly names for release-gate blocker codes surfaced on the
 *  pre-sign checkpoint and in the "Needs correction" lane. */
export const BLOCKER_LABEL: Record<string, string> = {
  missing_data_flags_set: "Some required fields aren't filled in.",
  provider_review_suggested: "Generator suggests provider review.",
  extraction_confidence_low: "Auto-extracted findings are low-confidence.",
  final_approval_pending: "Waiting for final physician approval.",
  note_text_empty: "The note body is empty.",
  already_signed: "This note is already signed.",
  export_requires_sign: "Sign the note before exporting.",
};

export function formatBlocker(code: string): string {
  return BLOCKER_LABEL[code] ?? code.replace(/_/g, " ");
}

// ---------------------------------------------------------------------
// Encounter title composer — the single authoritative headline for
// an encounter across every surface. The old pattern `#{id} · MRN`
// violated the "who is this about?" rule; this helper never leads
// with the system id.
// ---------------------------------------------------------------------

export function formatEncounterTitle(
  e: Pick<Encounter, "patient_name" | "patient_identifier">
): string {
  return patientDisplayName(e);
}

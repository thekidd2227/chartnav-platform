// Single frontend API module. All backend calls funnel through here.
//
// - base URL comes from VITE_API_URL (falls back to http://localhost:8000)
// - current dev identity is an email string; every request sends it as
//   `X-User-Email` (header-mode auth). When the backend moves to bearer
//   mode, only this module changes.
// - every non-ok response is converted to an ApiError with the
//   {error_code, reason} envelope the backend ships.

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  errorCode: string;
  reason: string;
  constructor(status: number, errorCode: string, reason: string) {
    super(`${status} ${errorCode}: ${reason}`);
    this.status = status;
    this.errorCode = errorCode;
    this.reason = reason;
  }
}

export type Role = "admin" | "clinician" | "reviewer";

export interface Me {
  user_id: number;
  email: string;
  full_name: string | null;
  role: Role;
  organization_id: number;
}

export interface User {
  id: number;
  organization_id: number;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: number | boolean;
  invited_at: string | null;
  created_at: string;
}

export interface OrganizationSettings {
  default_provider_name?: string | null;
  encounter_page_size?: number | null;
  audit_page_size?: number | null;
  feature_flags?: Record<string, boolean> | null;
  extensions?: Record<string, unknown> | null;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  settings: OrganizationSettings | null;
  created_at: string;
}

export interface UserInvite {
  user_id: number;
  invitation_token: string;
  invitation_expires_at: string;
  ttl_days: number;
}

export interface BulkImportSummary {
  requested: number;
  created: number;
  skipped: number;
  errors: number;
}

export interface BulkUserResult {
  created: User[];
  skipped: { row: number; email: string; error_code: string }[];
  errors: { row: number; email: string; error_code: string; detail?: string }[];
  summary: BulkImportSummary;
}

export interface SecurityAuditEvent {
  id: number;
  event_type: string;
  request_id: string | null;
  actor_email: string | null;
  actor_user_id: number | null;
  organization_id: number | null;
  path: string | null;
  method: string | null;
  error_code: string | null;
  detail: string | null;
  remote_addr: string | null;
  created_at: string;
}

export interface AuditFilters {
  event_type?: string;
  error_code?: string;
  actor_email?: string;
  q?: string;
}

export interface Location {
  id: number;
  organization_id: number;
  name: string;
  is_active: number | boolean;
  created_at: string;
}

export interface Encounter {
  // Note: when the row comes from an integrated adapter (e.g. FHIR),
  // `id` is a string vendor id rather than a number. Typed as
  // `number | string` to keep the contract honest.
  id: number | string;
  organization_id: number | null;
  location_id: number | null;
  patient_identifier: string;
  patient_name: string | null;
  provider_name: string;
  status: string;
  patient_id?: number | string | null;
  provider_id?: number | string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  /** Source-of-truth tag — "chartnav" (native) or adapter key (e.g. "fhir", "stub"). */
  _source?: "chartnav" | "fhir" | "stub" | string;
  _external_ref?: string | null;
  _external_source?: string | null;
  _fhir_status?: string;
  _bridged?: boolean;
}

export interface WorkflowEvent {
  id: number;
  encounter_id: number;
  event_type: string;
  event_data: unknown;
  created_at: string;
}

export interface EncounterFilters {
  status?: string;
  provider_name?: string;
  location_id?: number;
}

async function request<T>(
  path: string,
  init: RequestInit & { email?: string | null } = {}
): Promise<T> {
  return (await requestWithResponse<T>(path, init)).body;
}

async function requestWithResponse<T>(
  path: string,
  init: RequestInit & { email?: string | null } = {}
): Promise<{ body: T; response: Response }> {
  const { email, ...fetchInit } = init;
  const headers = new Headers(fetchInit.headers || {});
  if (email && !headers.has("X-User-Email")) {
    headers.set("X-User-Email", email);
  }
  if (fetchInit.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...fetchInit, headers });
  const text = await res.text();
  let body: any = undefined;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    const detail = body && typeof body === "object" ? body.detail : undefined;
    const code =
      (detail && typeof detail === "object" && detail.error_code) ||
      "http_error";
    const reason =
      (detail && typeof detail === "object" && detail.reason) ||
      (typeof body === "string" ? body : res.statusText);
    throw new ApiError(res.status, code, reason);
  }
  return { body: body as T, response: res };
}

// ---- Endpoints ----------------------------------------------------------

export function getHealth(): Promise<{ status: string }> {
  return request("/health");
}

export function getMe(email: string): Promise<Me> {
  return request("/me", { email });
}

// ---------- Platform mode (phase 16) ----------

export type PlatformMode =
  | "standalone"
  | "integrated_readthrough"
  | "integrated_writethrough";

export type SourceOfTruth =
  | "chartnav"
  | "external"
  | "mirrored"
  | "not_supported";

export interface PlatformInfo {
  platform_mode: PlatformMode;
  integration_adapter: string;
  adapter: {
    key: string;
    display_name: string;
    description: string;
    supports: {
      patient_read: boolean;
      patient_write: boolean;
      encounter_read: boolean;
      encounter_write: boolean;
      document_write: boolean;
    };
    source_of_truth: Record<string, SourceOfTruth>;
  };
}

export function getPlatform(email: string): Promise<PlatformInfo> {
  return request("/platform", { email });
}

export function platformModeLabel(mode: PlatformMode): string {
  switch (mode) {
    case "standalone":
      return "Standalone (ChartNav-native)";
    case "integrated_readthrough":
      return "Integrated — read-through";
    case "integrated_writethrough":
      return "Integrated — write-through";
    default:
      return mode;
  }
}

export function listEncounters(
  email: string,
  filters: EncounterFilters = {}
): Promise<Encounter[]> {
  const qs = new URLSearchParams();
  if (filters.status) qs.set("status", filters.status);
  if (filters.provider_name) qs.set("provider_name", filters.provider_name);
  if (typeof filters.location_id === "number")
    qs.set("location_id", String(filters.location_id));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request(`/encounters${suffix}`, { email });
}

export function getEncounter(
  email: string,
  id: number | string
): Promise<Encounter> {
  return request(`/encounters/${encodeURIComponent(String(id))}`, { email });
}

export function getEncounterEvents(
  email: string,
  id: number | string
): Promise<WorkflowEvent[]> {
  return request(`/encounters/${id}/events`, { email });
}

export function createEncounterEvent(
  email: string,
  id: number | string,
  body: { event_type: string; event_data?: unknown }
): Promise<WorkflowEvent> {
  return request(`/encounters/${id}/events`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateEncounterStatus(
  email: string,
  id: number | string,
  status: string
): Promise<Encounter> {
  return request(`/encounters/${encodeURIComponent(String(id))}/status`, {
    email,
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export interface NewEncounterInput {
  organization_id: number;
  location_id: number;
  patient_identifier: string;
  patient_name?: string | null;
  provider_name: string;
  scheduled_at?: string | null;
  status?: "scheduled" | "in_progress";
}

export function createEncounter(
  email: string,
  body: NewEncounterInput
): Promise<Encounter> {
  return request(`/encounters`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listLocations(
  email: string,
  opts: { includeInactive?: boolean } = {}
): Promise<Location[]> {
  const qs = opts.includeInactive ? "?include_inactive=1" : "";
  return request(`/locations${qs}`, { email });
}

export function createLocation(email: string, name: string): Promise<Location> {
  return request("/locations", {
    email,
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function updateLocation(
  email: string,
  id: number,
  patch: { name?: string; is_active?: boolean }
): Promise<Location> {
  return request(`/locations/${id}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deactivateLocation(email: string, id: number): Promise<Location> {
  return request(`/locations/${id}`, { email, method: "DELETE" });
}

export function listUsers(
  email: string,
  opts: { includeInactive?: boolean } = {}
): Promise<User[]> {
  const qs = opts.includeInactive ? "?include_inactive=1&limit=500" : "?limit=500";
  return request(`/users${qs}`, { email });
}

export async function listUsersPage(
  email: string,
  opts: {
    includeInactive?: boolean;
    q?: string;
    role?: Role;
    limit?: number;
    offset?: number;
  } = {}
): Promise<{ items: User[]; total: number; limit: number; offset: number }> {
  const qs = new URLSearchParams();
  if (opts.includeInactive) qs.set("include_inactive", "1");
  if (opts.q) qs.set("q", opts.q);
  if (opts.role) qs.set("role", opts.role);
  if (typeof opts.limit === "number") qs.set("limit", String(opts.limit));
  if (typeof opts.offset === "number") qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { body, response } = await requestWithResponse<User[]>(
    `/users${suffix}`,
    { email }
  );
  return {
    items: body,
    total: parseInt(response.headers.get("X-Total-Count") || "0", 10),
    limit: parseInt(response.headers.get("X-Limit") || String(body.length), 10),
    offset: parseInt(response.headers.get("X-Offset") || "0", 10),
  };
}

export async function listLocationsPage(
  email: string,
  opts: {
    includeInactive?: boolean;
    q?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<{ items: Location[]; total: number; limit: number; offset: number }> {
  const qs = new URLSearchParams();
  if (opts.includeInactive) qs.set("include_inactive", "1");
  if (opts.q) qs.set("q", opts.q);
  if (typeof opts.limit === "number") qs.set("limit", String(opts.limit));
  if (typeof opts.offset === "number") qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { body, response } = await requestWithResponse<Location[]>(
    `/locations${suffix}`,
    { email }
  );
  return {
    items: body,
    total: parseInt(response.headers.get("X-Total-Count") || "0", 10),
    limit: parseInt(response.headers.get("X-Limit") || String(body.length), 10),
    offset: parseInt(response.headers.get("X-Offset") || "0", 10),
  };
}

export function createUser(
  email: string,
  body: { email: string; full_name?: string | null; role: Role }
): Promise<User> {
  return request("/users", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateUser(
  email: string,
  id: number,
  patch: {
    email?: string;
    full_name?: string | null;
    role?: Role;
    is_active?: boolean;
  }
): Promise<User> {
  return request(`/users/${id}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deactivateUser(email: string, id: number): Promise<User> {
  return request(`/users/${id}`, { email, method: "DELETE" });
}

// ---- Organization settings ----------------------------------------------

export function getOrganization(email: string): Promise<Organization> {
  return request("/organization", { email });
}

export function updateOrganization(
  email: string,
  patch: { name?: string; settings?: OrganizationSettings | null }
): Promise<Organization> {
  return request("/organization", {
    email,
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function inviteUser(email: string, userId: number): Promise<UserInvite> {
  return request(`/users/${userId}/invite`, { email, method: "POST" });
}

export function acceptInvite(token: string): Promise<{
  user_id: number;
  email: string;
  organization_id: number;
  role: Role;
  accepted: true;
}> {
  return request(`/invites/accept`, {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function bulkCreateUsers(
  email: string,
  users: { email: string; full_name?: string | null; role: Role }[]
): Promise<BulkUserResult> {
  return request("/users/bulk", {
    email,
    method: "POST",
    body: JSON.stringify({ users }),
  });
}

export function auditExportUrl(
  filters: AuditFilters = {}
): string {
  const qs = new URLSearchParams();
  if (filters.event_type) qs.set("event_type", filters.event_type);
  if (filters.error_code) qs.set("error_code", filters.error_code);
  if (filters.actor_email) qs.set("actor_email", filters.actor_email);
  if (filters.q) qs.set("q", filters.q);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return `${API_URL}/security-audit-events/export${suffix}`;
}

/**
 * CSV export helper. Browsers can't add headers to a plain anchor, so
 * we fetch with the auth header and then trigger a local download.
 */
export async function downloadAuditExport(
  email: string,
  filters: AuditFilters = {}
): Promise<void> {
  const url = auditExportUrl(filters);
  const res = await fetch(url, { headers: { "X-User-Email": email } });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, "export_failed", text || res.statusText);
  }
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  // Content-Disposition carries the filename server-side; fall back
  // to a timestamped default if the browser strips it.
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="([^"]+)"/.exec(disposition);
  a.download = match ? match[1] : `chartnav-audit-${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}

// ---- Security audit log -------------------------------------------------

export async function listAuditEvents(
  email: string,
  filters: AuditFilters = {},
  page: { limit?: number; offset?: number } = {}
): Promise<{ items: SecurityAuditEvent[]; total: number; limit: number; offset: number }> {
  const qs = new URLSearchParams();
  if (filters.event_type) qs.set("event_type", filters.event_type);
  if (filters.error_code) qs.set("error_code", filters.error_code);
  if (filters.actor_email) qs.set("actor_email", filters.actor_email);
  if (filters.q) qs.set("q", filters.q);
  if (typeof page.limit === "number") qs.set("limit", String(page.limit));
  if (typeof page.offset === "number") qs.set("offset", String(page.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { body, response } = await requestWithResponse<SecurityAuditEvent[]>(
    `/security-audit-events${suffix}`,
    { email }
  );
  const total = parseInt(response.headers.get("X-Total-Count") || "0", 10);
  const limit = parseInt(response.headers.get("X-Limit") || String(body.length), 10);
  const offset = parseInt(response.headers.get("X-Offset") || "0", 10);
  return { items: body, total, limit, offset };
}

/**
 * Paginated encounters. Returns both items and totals pulled from the
 * `X-*` response headers emitted by the backend.
 */
export async function listEncountersPage(
  email: string,
  filters: EncounterFilters = {},
  page: { limit?: number; offset?: number } = {}
): Promise<{ items: Encounter[]; total: number; limit: number; offset: number }> {
  const qs = new URLSearchParams();
  if (filters.status) qs.set("status", filters.status);
  if (filters.provider_name) qs.set("provider_name", filters.provider_name);
  if (typeof filters.location_id === "number")
    qs.set("location_id", String(filters.location_id));
  if (typeof page.limit === "number") qs.set("limit", String(page.limit));
  if (typeof page.offset === "number") qs.set("offset", String(page.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { body, response } = await requestWithResponse<Encounter[]>(
    `/encounters${suffix}`,
    { email }
  );
  const total = parseInt(response.headers.get("X-Total-Count") || "0", 10);
  const limit = parseInt(response.headers.get("X-Limit") || String(body.length), 10);
  const offset = parseInt(response.headers.get("X-Offset") || "0", 10);
  return { items: body, total, limit, offset };
}

// ---- Pure helpers -------------------------------------------------------
//
// Keep these in sync with apps/api/app/authz.py::TRANSITION_ROLES.
// Used only to drive UI affordances; backend remains the source of truth.

export const ALLOWED_STATUSES = [
  "scheduled",
  "in_progress",
  "draft_ready",
  "review_needed",
  "completed",
] as const;

type Edge = [string, string];
const CLINICIAN_EDGES: Edge[] = [
  ["scheduled", "in_progress"],
  ["in_progress", "draft_ready"],
  ["draft_ready", "in_progress"],
];
const REVIEWER_EDGES: Edge[] = [
  ["draft_ready", "review_needed"],
  ["review_needed", "draft_ready"],
  ["review_needed", "completed"],
];
const ALL_EDGES: Edge[] = [...CLINICIAN_EDGES, ...REVIEWER_EDGES];

export function allowedNextStatuses(role: Role, current: string): string[] {
  const edges =
    role === "admin"
      ? ALL_EDGES
      : role === "clinician"
      ? CLINICIAN_EDGES
      : REVIEWER_EDGES;
  return edges.filter(([from]) => from === current).map(([, to]) => to);
}

export function canCreateEvent(role: Role): boolean {
  return role === "admin" || role === "clinician";
}

export function canCreateEncounter(role: Role): boolean {
  return role === "admin" || role === "clinician";
}

export function isAdmin(role: Role): boolean {
  return role === "admin";
}

/**
 * Resolve a named feature flag from org settings. Flags are default-on
 * unless explicitly set to `false`. Rationale: the server returns `null`
 * settings for orgs that have never touched them — the UI should not
 * silently strip features in that state.
 */
export function featureEnabled(org: Organization | null, flag: string): boolean {
  const flags = org?.settings?.feature_flags;
  if (!flags) return true;
  const v = flags[flag];
  return v === undefined ? true : !!v;
}

// Event type allowlist — mirrors apps/api/app/api/routes.py::EVENT_SCHEMAS.
export const EVENT_TYPES = [
  "manual_note",
  "note_draft_requested",
  "note_draft_completed",
  "note_reviewed",
] as const;

export const EVENT_TYPE_REQUIRED: Record<string, readonly string[]> = {
  manual_note: ["note"],
  note_draft_requested: ["requested_by"],
  note_draft_completed: ["template"],
  note_reviewed: ["reviewer"],
};

// ---------- Native clinical layer (phase 18) ----------

export interface Patient {
  id: number;
  organization_id: number;
  external_ref: string | null;
  patient_identifier: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  sex_at_birth: string | null;
  is_active: number | boolean;
  created_at: string;
}

export interface Provider {
  id: number;
  organization_id: number;
  external_ref: string | null;
  display_name: string;
  npi: string | null;
  specialty: string | null;
  is_active: number | boolean;
  created_at: string;
}

export interface PatientCreateBody {
  patient_identifier: string;
  first_name: string;
  last_name: string;
  date_of_birth?: string | null;
  sex_at_birth?: string | null;
  external_ref?: string | null;
}

export interface ProviderCreateBody {
  display_name: string;
  npi?: string | null;
  specialty?: string | null;
  external_ref?: string | null;
}

export function listPatients(
  email: string,
  opts: { q?: string; limit?: number; offset?: number } = {}
): Promise<Patient[]> {
  const qs = new URLSearchParams();
  if (opts.q) qs.set("q", opts.q);
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  if (opts.offset !== undefined) qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return request(`/patients${suffix}`, { email });
}

export function createPatient(
  email: string,
  body: PatientCreateBody
): Promise<Patient> {
  return request("/patients", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listProviders(
  email: string,
  opts: { q?: string; limit?: number; offset?: number } = {}
): Promise<Provider[]> {
  const qs = new URLSearchParams();
  if (opts.q) qs.set("q", opts.q);
  if (opts.limit !== undefined) qs.set("limit", String(opts.limit));
  if (opts.offset !== undefined) qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return request(`/providers${suffix}`, { email });
}

export function createProvider(
  email: string,
  body: ProviderCreateBody
): Promise<Provider> {
  return request("/providers", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------- Transcript ingestion + note drafting (phase 19) ----------

export type InputType =
  | "audio_upload"
  | "text_paste"
  | "manual_entry"
  | "imported_transcript";

export type InputProcessingStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "needs_review";

export type NoteDraftStatus =
  | "draft"
  | "provider_review"
  | "revised"
  | "signed"
  | "exported";

export type NoteFormat = "soap" | "assessment_plan" | "consult_note" | "freeform";

export interface EncounterInput {
  id: number;
  encounter_id: number;
  input_type: InputType;
  processing_status: InputProcessingStatus;
  transcript_text: string | null;
  confidence_summary: string | null;
  source_metadata: string | null;
  created_by_user_id: number | null;
  // Phase 22 — async job lifecycle fields.
  retry_count?: number;
  last_error?: string | null;
  last_error_code?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  worker_id?: string | null;
  // Phase 23 — background-worker claim fields.
  claimed_by?: string | null;
  claimed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedFindings {
  id: number;
  encounter_id: number;
  input_id: number | null;
  chief_complaint: string | null;
  hpi_summary: string | null;
  visual_acuity_od: string | null;
  visual_acuity_os: string | null;
  iop_od: string | null;
  iop_os: string | null;
  structured_json: {
    diagnoses?: string[];
    medications?: string[];
    imaging?: string[];
    assessment?: string | null;
    plan?: string | null;
    follow_up_interval?: string | null;
    [key: string]: unknown;
  };
  extraction_confidence: "high" | "medium" | "low" | null;
  created_at: string;
}

export interface NoteVersion {
  id: number;
  encounter_id: number;
  version_number: number;
  draft_status: NoteDraftStatus;
  note_format: NoteFormat;
  note_text: string;
  source_input_id: number | null;
  extracted_findings_id: number | null;
  generated_by: "system" | "manual";
  provider_review_required: number | boolean;
  missing_data_flags: string[];
  signed_at: string | null;
  signed_by_user_id: number | null;
  exported_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NoteWithFindings {
  note: NoteVersion;
  findings: ExtractedFindings | null;
}

export function createEncounterInput(
  email: string,
  encounterId: number,
  body: {
    input_type: InputType;
    transcript_text?: string | null;
    processing_status?: InputProcessingStatus | null;
    confidence_summary?: string | null;
    source_metadata?: Record<string, unknown> | null;
  }
): Promise<EncounterInput> {
  return request(`/encounters/${encounterId}/inputs`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listEncounterInputs(
  email: string,
  encounterId: number
): Promise<EncounterInput[]> {
  return request(`/encounters/${encounterId}/inputs`, { email });
}

export function generateNoteVersion(
  email: string,
  encounterId: number,
  body: { input_id?: number; note_format?: NoteFormat } = {}
): Promise<NoteWithFindings> {
  return request(`/encounters/${encounterId}/notes/generate`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listEncounterNotes(
  email: string,
  encounterId: number
): Promise<NoteVersion[]> {
  return request(`/encounters/${encounterId}/notes`, { email });
}

export function getNoteVersion(
  email: string,
  noteId: number
): Promise<NoteWithFindings> {
  return request(`/note-versions/${noteId}`, { email });
}

export function patchNoteVersion(
  email: string,
  noteId: number,
  body: {
    note_text?: string;
    draft_status?: NoteDraftStatus;
    note_format?: NoteFormat;
  }
): Promise<NoteVersion> {
  return request(`/note-versions/${noteId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function submitNoteForReview(
  email: string,
  noteId: number
): Promise<NoteVersion> {
  return request(`/note-versions/${noteId}/submit-for-review`, {
    email,
    method: "POST",
  });
}

export function signNoteVersion(
  email: string,
  noteId: number
): Promise<NoteVersion> {
  return request(`/note-versions/${noteId}/sign`, { email, method: "POST" });
}

export function exportNoteVersion(
  email: string,
  noteId: number
): Promise<NoteVersion> {
  return request(`/note-versions/${noteId}/export`, { email, method: "POST" });
}

// ---------- Signed-note artifact (phase 25) --------------------------------

export type ArtifactFormat = "json" | "text" | "fhir";

/** Canonical ChartNav signed-note artifact envelope. */
export interface NoteArtifact {
  artifact_version: number;
  artifact_type: "chartnav.signed_note.v1";
  chartnav: {
    platform_mode: string;
    adapter_display_name: string | null;
    organization_id: number;
  };
  encounter: {
    id: number;
    status: string | null;
    patient_display: string | null;
    provider_display: string | null;
    source: "chartnav_native" | "fhir" | string;
    external_ref: string | null;
  };
  transcript_source: {
    input_id: number;
    input_type: string | null;
    processing_status: string | null;
    confidence_summary: string | null;
    transcript_excerpt: string;
    transcript_truncated: boolean;
    transcript_chars: number;
  } | null;
  extracted_findings: {
    chief_complaint: string | null;
    hpi_summary: string | null;
    visual_acuity: { od: string | null; os: string | null };
    iop: { od: string | null; os: string | null };
    structured: Record<string, unknown>;
    extraction_confidence: string | null;
  } | null;
  note: {
    id: number;
    version_number: number;
    format: string;
    draft_status: string;
    generated_by: string | null;
    generated_draft: string;
    clinician_final: string;
    edit_applied: boolean;
  };
  missing_data_flags: string[];
  signature: {
    signed_at: string | null;
    signed_by_email: string | null;
    signed_by_user_id: number | null;
    content_hash_sha256: string;
    hash_inputs: string;
  };
  export_envelope: {
    issued_at: string;
    issued_by_email: string | null;
    issued_by_user_id: number | null;
    format_variant: string;
    mime_type: string;
  };
}

/** Fetch the canonical JSON artifact for a signed note. */
export function getNoteArtifact(
  email: string,
  noteId: number
): Promise<NoteArtifact> {
  return request(`/note-versions/${noteId}/artifact?format=json`, { email });
}

/** Fetch the artifact in a chosen format. Returns the raw body — caller
 *  decides whether to render, download, or hand to an EHR adapter.
 *  Text comes back as a string; json/fhir as parsed JSON. */
export async function fetchNoteArtifactRaw(
  email: string,
  noteId: number,
  format: ArtifactFormat
): Promise<{ body: unknown; contentType: string; variant: string }> {
  const headers = new Headers({ "X-User-Email": email });
  const res = await fetch(
    `${API_URL}/note-versions/${noteId}/artifact?format=${format}`,
    { headers }
  );
  const contentType = res.headers.get("content-type") || "";
  const variant = res.headers.get("x-chartnav-artifact-variant") || "";
  const text = await res.text();
  if (!res.ok) {
    // Reuse the envelope contract from `request` for error parity.
    let detail: any;
    try {
      detail = JSON.parse(text)?.detail;
    } catch {
      detail = undefined;
    }
    const code =
      (detail && typeof detail === "object" && detail.error_code) ||
      "http_error";
    const reason =
      (detail && typeof detail === "object" && detail.reason) || text || res.statusText;
    throw new ApiError(res.status, code, reason);
  }
  const body = contentType.includes("json") && text ? JSON.parse(text) : text;
  return { body, contentType, variant };
}

/** Trigger a browser download for the chosen artifact format. The file
 *  extension + filename are stable so repeated exports of the same
 *  note-version land on the same name and a clinician can spot a
 *  re-export vs. a new version in their downloads folder. */
export async function downloadNoteArtifact(
  email: string,
  noteId: number,
  format: ArtifactFormat
): Promise<{ filename: string; variant: string }> {
  const { body, contentType, variant } = await fetchNoteArtifactRaw(
    email,
    noteId,
    format
  );
  const ext = format === "text" ? "txt" : "json";
  const filename = `chartnav-note-${noteId}.${format}.${ext}`;
  const payload =
    typeof body === "string" ? body : JSON.stringify(body, null, 2);
  const blob = new Blob([payload], {
    type: contentType || "application/octet-stream",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Give the browser a tick before revoking so the download actually starts.
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return { filename, variant };
}

export const MISSING_FLAG_LABELS: Record<string, string> = {
  chief_complaint_missing: "Chief complaint",
  visual_acuity_missing: "Visual acuity",
  iop_missing: "Intraocular pressure",
  diagnosis_missing: "Diagnosis",
  plan_missing: "Plan",
  follow_up_interval_missing: "Follow-up interval",
};

// ---------- Encounter source-of-truth helpers (phase 20) ----------

/** True when this encounter is owned by ChartNav's native DB. */
export function encounterIsNative(enc: Encounter | null | undefined): boolean {
  if (!enc) return false;
  // `_source` not set → assume native (backward compat with older
  // responses that haven't been migrated to the tag yet).
  const src = (enc as any)._source;
  return src === undefined || src === "chartnav";
}

/** Short, operator-facing label for where this encounter lives. */
export function encounterSourceLabel(enc: Encounter | null | undefined): string {
  const src = (enc as any)?._source;
  switch (src) {
    case "chartnav":
    case undefined:
      return "ChartNav (native)";
    case "fhir":
      return "External (FHIR)";
    case "stub":
      return "External (stub)";
    default:
      return `External (${src})`;
  }
}

// ---------- Encounter bridge (phase 21) ----------

export interface EncounterBridgeBody {
  external_ref: string;
  external_source: string;
  patient_identifier?: string | null;
  patient_name?: string | null;
  provider_name?: string | null;
  status?: string | null;
}

export interface BridgedEncounter extends Encounter {
  external_ref: string | null;
  external_source: string | null;
  _bridged: boolean;
  _external_ref: string | null;
  _external_source: string | null;
}

export function bridgeEncounter(
  email: string,
  body: EncounterBridgeBody
): Promise<BridgedEncounter> {
  return request("/encounters/bridge", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------- Ingestion lifecycle (phase 22) ----------

export interface EncounterInputJob extends EncounterInput {
  retry_count: number;
  last_error: string | null;
  last_error_code: string | null;
  started_at: string | null;
  finished_at: string | null;
  worker_id: string | null;
}

export interface ProcessResult {
  input: EncounterInputJob;
  ingestion_error: { error_code: string; reason: string } | null;
}

export function processEncounterInput(
  email: string,
  inputId: number,
): Promise<ProcessResult> {
  return request(`/encounter-inputs/${inputId}/process`, {
    email,
    method: "POST",
  });
}

export function retryEncounterInput(
  email: string,
  inputId: number,
): Promise<EncounterInputJob> {
  return request(`/encounter-inputs/${inputId}/retry`, {
    email,
    method: "POST",
  });
}

// ---------- Background worker + bridge refresh (phase 23) ----------

export interface WorkerTickResult {
  processed: boolean;
  queue_empty?: boolean;
  input_id?: number;
  status?: string;
  ingestion_error?: string | null;
}

export interface WorkerDrainSummary {
  worker_id: string;
  processed: number;
  completed: number;
  failed: number;
  error_codes: string[];
}

export interface BridgeRefreshResult {
  id: number;
  refreshed: boolean;
  mirrored: Record<string, string>;
  skipped_unchanged: string[];
}

export function runWorkerTick(email: string): Promise<WorkerTickResult> {
  return request("/workers/tick", { email, method: "POST" });
}

export function drainWorkerQueue(email: string): Promise<WorkerDrainSummary> {
  return request("/workers/drain", { email, method: "POST" });
}

export function requeueStaleClaims(
  email: string
): Promise<{ recovered: number }> {
  return request("/workers/requeue-stale", { email, method: "POST" });
}

export function refreshBridgedEncounter(
  email: string,
  encounterId: number | string
): Promise<BridgeRefreshResult> {
  return request(
    `/encounters/${encodeURIComponent(String(encounterId))}/refresh`,
    { email, method: "POST", body: "{}" }
  );
}

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
      /** Phase 26: adapter accepts a packaged FHIR DocumentReference
       *  via the `transmit_artifact` write-path. Reviewers use this
       *  flag to decide whether to render the Transmit button. */
      document_transmit?: boolean;
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

// ---------- Signed-note transmission (phase 26) --------------------------

export interface NoteTransmission {
  id: number;
  note_version_id: number;
  encounter_id: number;
  organization_id: number;
  adapter_key: string;
  target_system: string | null;
  transport_status:
    | "queued"
    | "dispatching"
    | "succeeded"
    | "failed"
    | "unsupported";
  request_body_hash: string | null;
  response_code: number | null;
  response_snippet: string | null;
  remote_id: string | null;
  last_error_code: string | null;
  last_error: string | null;
  attempt_number: number;
  attempted_at: string | null;
  completed_at: string | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

/** Initiate a transmission of a signed note artifact to the active
 *  adapter. Returns the persisted attempt row. Failures (remote 4xx/5xx,
 *  adapter unsupported) come back as a row with `transport_status="failed"`
 *  or `"unsupported"` — they are NOT exceptions. Only an HTTP 4xx from
 *  ChartNav's own gating (mode, role, already_transmitted, …) throws. */
export function transmitNoteVersion(
  email: string,
  noteId: number,
  opts: { force?: boolean } = {}
): Promise<NoteTransmission> {
  return request(`/note-versions/${noteId}/transmit`, {
    email,
    method: "POST",
    body: JSON.stringify({ force: !!opts.force }),
  });
}

/** List all transmission attempts for a note, newest first. */
export function listNoteTransmissions(
  email: string,
  noteId: number
): Promise<NoteTransmission[]> {
  return request(`/note-versions/${noteId}/transmissions`, { email });
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

// ---------- Clinician quick-comment pad (phase 27) -----------------------

export interface ClinicianQuickComment {
  id: number;
  organization_id: number;
  user_id: number;
  body: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** List the caller's own saved custom quick comments. */
export function listMyQuickComments(
  email: string,
  opts: { includeInactive?: boolean } = {}
): Promise<ClinicianQuickComment[]> {
  const qs = opts.includeInactive ? "?include_inactive=true" : "";
  return request(`/me/quick-comments${qs}`, { email });
}

export function createMyQuickComment(
  email: string,
  body: string
): Promise<ClinicianQuickComment> {
  return request(`/me/quick-comments`, {
    email,
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function updateMyQuickComment(
  email: string,
  id: number,
  patch: { body?: string; is_active?: boolean }
): Promise<ClinicianQuickComment> {
  return request(`/me/quick-comments/${id}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteMyQuickComment(
  email: string,
  id: number
): Promise<ClinicianQuickComment> {
  return request(`/me/quick-comments/${id}`, {
    email,
    method: "DELETE",
  });
}

// ---------- Quick-comment favorites + usage audit (phase 28) -------------

export interface ClinicianQuickCommentFavorite {
  id: number;
  organization_id: number;
  user_id: number;
  /** Stable preloaded-pack id (e.g. "sx-01"). Null for custom favorites. */
  preloaded_ref: string | null;
  /** FK into clinician_quick_comments. Null for preloaded favorites. */
  custom_comment_id: number | null;
  created_at: string;
}

export function listMyQuickCommentFavorites(
  email: string
): Promise<ClinicianQuickCommentFavorite[]> {
  return request("/me/quick-comments/favorites", { email });
}

/** Idempotent: re-firing with the same ref returns the existing row. */
export function favoriteQuickComment(
  email: string,
  ref: { preloaded_ref: string } | { custom_comment_id: number }
): Promise<ClinicianQuickCommentFavorite> {
  return request("/me/quick-comments/favorites", {
    email,
    method: "POST",
    body: JSON.stringify(ref),
  });
}

export function unfavoriteQuickComment(
  email: string,
  ref: { preloaded_ref: string } | { custom_comment_id: number }
): Promise<{ removed: number }> {
  const qs =
    "preloaded_ref" in ref
      ? `?preloaded_ref=${encodeURIComponent(ref.preloaded_ref)}`
      : `?custom_comment_id=${ref.custom_comment_id}`;
  return request(`/me/quick-comments/favorites${qs}`, {
    email,
    method: "DELETE",
  });
}

/** Best-effort usage audit: records that a doctor inserted a quick
 *  comment. Fails silently if the backend is offline — a missing
 *  audit event should never block the clinician's workflow. */
export async function recordQuickCommentUsage(
  email: string,
  payload:
    | {
        preloaded_ref: string;
        note_version_id?: number | null;
        encounter_id?: number | null;
      }
    | {
        custom_comment_id: number;
        note_version_id?: number | null;
        encounter_id?: number | null;
      }
): Promise<{ recorded: boolean; kind: "preloaded" | "custom" } | null> {
  try {
    return await request<{ recorded: boolean; kind: "preloaded" | "custom" }>(
      "/me/quick-comments/used",
      {
        email,
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
  } catch {
    return null;
  }
}

// ---------- Clinical Shortcut usage audit (phase 29) --------------------

/** Fire-and-forget usage-audit POST for a Clinical Shortcut insertion.
 *  Distinct from `recordQuickCommentUsage` on purpose so analytics can
 *  separate clipboard-style Quick Comments from specialist shorthand.
 *  Failure is swallowed — a missed telemetry event must not block
 *  the clinician's workflow. */
export async function recordClinicalShortcutUsage(
  email: string,
  payload: {
    shortcut_id: string;
    note_version_id?: number | null;
    encounter_id?: number | null;
  }
): Promise<{ recorded: boolean; shortcut_id: string } | null> {
  try {
    return await request<{ recorded: boolean; shortcut_id: string }>(
      "/me/clinical-shortcuts/used",
      {
        email,
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
  } catch {
    return null;
  }
}

// ---------- Clinical Shortcut favorites (phase 30) -----------------------

export interface ClinicalShortcutFavorite {
  id: number;
  organization_id: number;
  user_id: number;
  shortcut_ref: string;
  created_at: string;
}

export function listMyClinicalShortcutFavorites(
  email: string
): Promise<ClinicalShortcutFavorite[]> {
  return request("/me/clinical-shortcuts/favorites", { email });
}

export function favoriteClinicalShortcut(
  email: string,
  shortcutRef: string
): Promise<ClinicalShortcutFavorite> {
  return request("/me/clinical-shortcuts/favorites", {
    email,
    method: "POST",
    body: JSON.stringify({ shortcut_ref: shortcutRef }),
  });
}

export function unfavoriteClinicalShortcut(
  email: string,
  shortcutRef: string
): Promise<{ removed: number }> {
  return request(
    `/me/clinical-shortcuts/favorites?shortcut_ref=${encodeURIComponent(
      shortcutRef
    )}`,
    { email, method: "DELETE" }
  );
}

// ---------- Audio intake + transcript review (phase 33) ------------------

/** Stable enum of how an audio file reached the encounter. Threaded
 *  to the backend in the `X-Capture-Source` header and persisted on
 *  `source_metadata.capture_source` so audit + downstream tooling
 *  can distinguish a hand-uploaded file from a browser-mic recording.
 */
export type AudioCaptureSource = "browser-mic" | "file-upload";

/** Upload a raw audio file for an encounter and receive the
 *  persisted `encounter_inputs` row (already run through the
 *  ingestion pipeline, so `processing_status` is the final state).
 *
 *  Stub-transcript headers are exposed so test harnesses + dogfood
 *  flows can drive the pipeline deterministically without a real
 *  STT provider. A production deployment should never set these.
 *
 *  Phase-36 additions:
 *  - `captureSource` — `"browser-mic"` for live recordings,
 *    `"file-upload"` for the hand-uploaded path. Defaults to
 *    `"file-upload"` for backward compatibility with phase-33
 *    callers that didn't pass the option.
 */
export async function uploadEncounterAudio(
  email: string,
  encounterId: number,
  file: File,
  opts: {
    stubTranscript?: string;
    stubTranscriptError?: string;
    captureSource?: AudioCaptureSource;
  } = {}
): Promise<EncounterInput> {
  const form = new FormData();
  form.append("audio", file, file.name);
  const headers = new Headers({ "X-User-Email": email });
  if (opts.stubTranscript) {
    headers.set("X-Stub-Transcript", opts.stubTranscript);
  }
  if (opts.stubTranscriptError) {
    headers.set("X-Stub-Transcript-Error", opts.stubTranscriptError);
  }
  if (opts.captureSource) {
    headers.set("X-Capture-Source", opts.captureSource);
  }
  const res = await fetch(
    `${API_URL}/encounters/${encounterId}/inputs/audio`,
    { method: "POST", body: form, headers }
  );
  const text = await res.text();
  let body: any;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    body = text;
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
  return body as EncounterInput;
}

/** Clinician edit of a completed input's transcript, in place.
 *  The server refuses if the input isn't in `processing_status=completed`
 *  so a race with the ingestion pipeline is impossible.
 */
export function patchEncounterInputTranscript(
  email: string,
  inputId: number,
  transcriptText: string
): Promise<EncounterInput> {
  return request(`/encounter-inputs/${inputId}/transcript`, {
    email,
    method: "PATCH",
    body: JSON.stringify({ transcript_text: transcriptText }),
  });
}

// ---------- Eye-diagram artifacts (persistence shell) ----------
//
// This is the storage and identity foundation for retinal diagram
// artifacts. There is no drawing canvas, no AI proposal pipeline, and
// no apply/reject workflow yet — those land in a follow-up. Callers
// supply `drawing_json` as any JSON-shaped object; the backend stores
// it verbatim and returns it as a parsed object (never a string).

export interface EyeDiagramArtifact {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  created_by_user_id: number;
  artifact_type: "retinal_diagram";
  title: string;
  findings_text: string;
  drawing_json: Record<string, unknown>;
  version_number: number;
  parent_artifact_id: number | null;
  signed_at: string | null;
  signed_by_user_id: number | null;
  is_signed: boolean;
  created_at: string;
  updated_at: string;
}

export interface EyeDiagramListResponse {
  items: EyeDiagramArtifact[];
  total: number;
}

export interface EyeDiagramCreateInput {
  title?: string;
  findings_text?: string;
  drawing_json?: Record<string, unknown>;
  encounter_id?: number | null;
}

export interface EyeDiagramUpdateInput {
  title?: string;
  findings_text?: string;
  drawing_json?: Record<string, unknown>;
}

export function listPatientEyeDiagrams(
  email: string,
  patientId: number
): Promise<EyeDiagramListResponse> {
  return request(`/patients/${patientId}/eye-diagrams`, { email });
}

export function getPatientEyeDiagram(
  email: string,
  patientId: number,
  artifactId: number
): Promise<EyeDiagramArtifact> {
  return request(`/patients/${patientId}/eye-diagrams/${artifactId}`, { email });
}

export function createPatientEyeDiagram(
  email: string,
  patientId: number,
  input: EyeDiagramCreateInput
): Promise<EyeDiagramArtifact> {
  return request(`/patients/${patientId}/eye-diagrams`, {
    email,
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * Update an unsigned artifact in place. If the target is signed and
 * `fork` is true, the backend creates a new unsigned version whose
 * `parent_artifact_id` is the original. If signed and `fork` is false,
 * the backend returns 409 `artifact_signed_immutable`.
 */
export function updatePatientEyeDiagram(
  email: string,
  patientId: number,
  artifactId: number,
  input: EyeDiagramUpdateInput,
  options: { fork?: boolean } = {}
): Promise<EyeDiagramArtifact> {
  const qs = options.fork ? "?fork=true" : "";
  return request(`/patients/${patientId}/eye-diagrams/${artifactId}${qs}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/**
 * Stamp signed_at/signed_by on the artifact. Re-signing returns
 * 409 `artifact_already_signed`.
 */
export function signPatientEyeDiagram(
  email: string,
  patientId: number,
  artifactId: number
): Promise<EyeDiagramArtifact> {
  return request(`/patients/${patientId}/eye-diagrams/${artifactId}/sign`, {
    email,
    method: "POST",
  });
}

// ---------- Phase 8: scribe session lifecycle ----------
//
// One row per AI scribe session: the unit of work between provider
// source/transcript text and a finalized clinical artifact. The
// frontend never persists draft / processed / structured note content
// without going through these endpoints — there is no client-side
// finalization shortcut.

export type ScribeSessionStatus =
  | "draft"
  | "processing"
  | "ready_for_review"
  | "reviewed"
  | "finalized"
  | "discarded";

export type ScribeSessionInputMode =
  | "pasted_text"
  | "transcript"
  | "audio_placeholder";

export interface ScribeSession {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  created_by_user_id: number;
  status: ScribeSessionStatus;
  input_mode: ScribeSessionInputMode;
  source_text: string | null;
  transcript_text: string | null;
  draft_note_text: string | null;
  /** Engine-produced structured note. Always a real object on the wire. */
  structured_note_json: Record<string, string>;
  linked_artifact_id: number | null;
  review_notes: string | null;
  finalized_at: string | null;
  reviewed_at: string | null;
  reviewed_by_user_id: number | null;
  discarded_at: string | null;
  created_at: string;
  updated_at: string;
  is_terminal: boolean;
}

export interface ScribeSessionListResponse {
  items: ScribeSession[];
  total: number;
}

export interface ScribeSessionCreateInput {
  encounter_id?: number | null;
  input_mode?: ScribeSessionInputMode;
  source_text?: string;
  transcript_text?: string;
  linked_artifact_id?: number | null;
}

export interface ScribeSessionUpdateInput {
  source_text?: string;
  transcript_text?: string;
  review_notes?: string;
  encounter_id?: number | null;
  linked_artifact_id?: number | null;
  input_mode?: ScribeSessionInputMode;
}

export interface ScribeSessionReviewInput {
  review_notes?: string;
}

export function listPatientScribeSessions(
  email: string,
  patientId: number
): Promise<ScribeSessionListResponse> {
  return request(`/patients/${patientId}/scribe-sessions`, { email });
}

export function getPatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}`,
    { email }
  );
}

export function createPatientScribeSession(
  email: string,
  patientId: number,
  input: ScribeSessionCreateInput
): Promise<ScribeSession> {
  return request(`/patients/${patientId}/scribe-sessions`, {
    email,
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updatePatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number,
  input: ScribeSessionUpdateInput
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}`,
    {
      email,
      method: "PATCH",
      body: JSON.stringify(input),
    }
  );
}

export function processPatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}/process`,
    { email, method: "POST" }
  );
}

export function reviewPatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number,
  input: ScribeSessionReviewInput = {}
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}/review`,
    {
      email,
      method: "POST",
      body: JSON.stringify(input),
    }
  );
}

export function finalizePatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}/finalize`,
    { email, method: "POST" }
  );
}

export function discardPatientScribeSession(
  email: string,
  patientId: number,
  sessionId: number
): Promise<ScribeSession> {
  return request(
    `/patients/${patientId}/scribe-sessions/${sessionId}/discard`,
    { email, method: "POST" }
  );
}
// ---------- Phase 6: findings → diagram proposals ----------
//
// The proposal endpoint is read-only on the data side — calling it
// never writes to chart_artifacts. Proposals only become stored
// annotations after the provider explicitly applies them in the UI.

export interface RetinalProposalResponse {
  clinical_text: string;
  ignored_chatter: string[];
  uncertain_phrases: string[];
  proposed_annotations: Array<{
    proposal_id: string;
    kind: "symbol" | "text";
    symbol_type: string;
    eye: "OD" | "OS";
    x: number;
    y: number;
    zone: string | null;
    text: string;
    color: string;
    confidence: number;
    confidence_band: "high" | "medium" | "low";
    source_phrase: string;
    source_start: number;
    source_end: number;
    reason: string;
    missing_flags: string[];
    source: "ai_proposed";
  }>;
  confidence_summary: {
    high: number;
    medium: number;
    low: number;
    needs_review: boolean;
  };
  missing_flags: Array<{
    code: string;
    detail: string;
    source_phrase: string;
    source_start: number;
    source_end: number;
  }>;
}

export function proposeRetinalFromFindings(
  email: string,
  patientId: number,
  findings_text: string,
  drawing_json?: Record<string, unknown>
): Promise<RetinalProposalResponse> {
  return request(`/patients/${patientId}/eye-diagrams/propose-from-findings`, {
    email,
    method: "POST",
    body: JSON.stringify({ findings_text, drawing_json }),
  });
}

// ---------- Phase 9: provider-reviewed patient-friendly summaries ----------
//
// One row per draft summary. The frontend never sends anything to a
// patient — that's deferred. Status flows draft → reviewed →
// finalized; or draft|reviewed → discarded. finalized and discarded
// are immutable.

export type PatientSummaryStatus =
  | "draft"
  | "reviewed"
  | "finalized"
  | "discarded";

export interface PatientSummary {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  scribe_session_id: number | null;
  created_by_user_id: number;
  reviewed_by_user_id: number | null;
  status: PatientSummaryStatus;
  plain_language_summary: string;
  /** Real arrays on the wire — backend normalizes from JSON-encoded TEXT. */
  key_findings: string[];
  next_steps: string[];
  questions: string[];
  limitations_notice: string;
  review_notes: string | null;
  finalized_at: string | null;
  reviewed_at: string | null;
  discarded_at: string | null;
  created_at: string;
  updated_at: string;
  is_terminal: boolean;
}

export interface PatientSummaryListResponse {
  items: PatientSummary[];
  total: number;
}

export interface PatientSummaryCreateInput {
  encounter_id?: number | null;
  scribe_session_id?: number | null;
  provider_instructions?: string;
}

export interface PatientSummaryUpdateInput {
  plain_language_summary?: string;
  key_findings?: string[];
  next_steps?: string[];
  questions?: string[];
  limitations_notice?: string;
  review_notes?: string;
}

export interface PatientSummaryReviewInput {
  review_notes?: string;
}

export function listPatientSummaries(
  email: string,
  patientId: number
): Promise<PatientSummaryListResponse> {
  return request(`/patients/${patientId}/patient-summaries`, { email });
}

export function getPatientSummary(
  email: string,
  patientId: number,
  summaryId: number
): Promise<PatientSummary> {
  return request(
    `/patients/${patientId}/patient-summaries/${summaryId}`,
    { email }
  );
}

export function createPatientSummary(
  email: string,
  patientId: number,
  input: PatientSummaryCreateInput
): Promise<PatientSummary> {
  return request(`/patients/${patientId}/patient-summaries`, {
    email,
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updatePatientSummary(
  email: string,
  patientId: number,
  summaryId: number,
  input: PatientSummaryUpdateInput
): Promise<PatientSummary> {
  return request(
    `/patients/${patientId}/patient-summaries/${summaryId}`,
    {
      email,
      method: "PATCH",
      body: JSON.stringify(input),
    }
  );
}

export function reviewPatientSummary(
  email: string,
  patientId: number,
  summaryId: number,
  input: PatientSummaryReviewInput = {}
): Promise<PatientSummary> {
  return request(
    `/patients/${patientId}/patient-summaries/${summaryId}/review`,
    {
      email,
      method: "POST",
      body: JSON.stringify(input),
    }
  );
}

export function finalizePatientSummary(
  email: string,
  patientId: number,
  summaryId: number
): Promise<PatientSummary> {
  return request(
    `/patients/${patientId}/patient-summaries/${summaryId}/finalize`,
    { email, method: "POST" }
  );
}

export function discardPatientSummary(
  email: string,
  patientId: number,
  summaryId: number
): Promise<PatientSummary> {
  return request(
    `/patients/${patientId}/patient-summaries/${summaryId}/discard`,
    { email, method: "POST" }
  );
}

// ---------- Phase 10: provider-facing pre-visit clinical brief ----------
//
// On-demand, deterministic. The brief is a derived view over existing
// chart records (encounters, scribe sessions, retinal artifacts,
// patient summaries, workflow events). It is never persisted, never
// sent to a patient, never an order/coding tool, and never a clinical
// decision. POST /generate is the audited explicit-action route; GET
// is a read-only convenience (no audit emitted).

export interface PreVisitBriefRetinalSummary {
  total: number;
  signed_count: number;
  unsigned_count: number;
  has_unsigned_drafts: boolean;
  latest_signed: {
    id: number;
    title: string | null;
    signed_at: string | null;
    version_number: number | null;
    encounter_id: number | null;
  } | null;
}

export interface PreVisitBriefScribeSummary {
  session_id: number | null;
  status: string;
  updated_at?: string | null;
  finalized_at?: string | null;
  reviewed_at?: string | null;
  encounter_id?: number | null;
  chief_complaint_excerpt?: string | null;
  plan_excerpt?: string | null;
}

export interface PreVisitBriefSummaryContext {
  summary_id: number | null;
  status: string;
  source_kind?: string;
  finalized_at?: string | null;
  reviewed_at?: string | null;
  encounter_id?: number | null;
  scribe_session_id?: number | null;
  plain_language_excerpt?: string | null;
  key_findings_count?: number;
  next_steps_count?: number;
}

export interface PreVisitBriefPendingItem {
  kind: "encounter" | "scribe_session" | "patient_summary";
  id: number;
  status: string;
  encounter_id?: number | null;
  provider_name?: string | null;
  scheduled_at?: string | null;
  updated_at?: string | null;
}

export interface PreVisitBriefSuggestedItem {
  kind: "scribe_session" | "patient_summary";
  id: number;
  reason: string;
  updated_at?: string | null;
}

export interface PreVisitBrief {
  patient_id: number;
  brief_status: string;
  last_visit_summary: string | null;
  active_issues: string[];
  retinal_artifact_summary: PreVisitBriefRetinalSummary;
  recent_scribe_session_summary: PreVisitBriefScribeSummary;
  patient_summary_context: PreVisitBriefSummaryContext;
  pending_items: PreVisitBriefPendingItem[];
  suggested_review_items: PreVisitBriefSuggestedItem[];
  data_gaps: string[];
  source_counts: Record<string, number>;
  generated_at: string;
  notice: string;
}

export function generatePatientPreVisitBrief(
  email: string,
  patientId: number
): Promise<PreVisitBrief> {
  return request(
    `/patients/${patientId}/pre-visit-briefs/generate`,
    { email, method: "POST" }
  );
}

export function getPatientPreVisitBrief(
  email: string,
  patientId: number
): Promise<PreVisitBrief> {
  return request(`/patients/${patientId}/pre-visit-brief`, { email });
}

// ---------- Phase 11: provider action review queue ----------------
//
// One row per provider-reviewable action suggestion. Status flows
// suggested → accepted → completed; or suggested|accepted →
// dismissed. Direct suggested → completed is rejected. dismissed and
// completed are immutable. ChartNav never creates orders, sends
// referrals, messages patients, or takes action automatically — every
// item is a review task the provider explicitly resolves.

export type ProviderActionStatus =
  | "suggested"
  | "accepted"
  | "dismissed"
  | "completed";

export type ProviderActionPriority = "low" | "medium" | "high";

export interface ProviderActionItem {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  source_type: string | null;
  source_id: number | null;
  action_type: string;
  priority: ProviderActionPriority;
  title: string;
  reason: string;
  status: ProviderActionStatus;
  created_by_system: boolean;
  generated_batch_id: string | null;
  accepted_by_user_id: number | null;
  dismissed_by_user_id: number | null;
  completed_by_user_id: number | null;
  accepted_at: string | null;
  dismissed_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  is_terminal: boolean;
}

export interface ProviderActionItemListResponse {
  items: ProviderActionItem[];
  total: number;
}

export interface ProviderActionItemGenerateResponse {
  batch_id: string;
  generated_count: number;
  created_count: number;
  reused_count: number;
  items: ProviderActionItem[];
}

export interface ProviderActionItemListFilters {
  status?: ProviderActionStatus;
  priority?: ProviderActionPriority;
  action_type?: string;
  encounter_id?: number;
}

function _qs(filters: ProviderActionItemListFilters): string {
  const parts: string[] = [];
  if (filters.status) parts.push(`status=${encodeURIComponent(filters.status)}`);
  if (filters.priority)
    parts.push(`priority=${encodeURIComponent(filters.priority)}`);
  if (filters.action_type)
    parts.push(`action_type=${encodeURIComponent(filters.action_type)}`);
  if (filters.encounter_id !== undefined)
    parts.push(`encounter_id=${filters.encounter_id}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export function generateProviderActionItems(
  email: string,
  patientId: number
): Promise<ProviderActionItemGenerateResponse> {
  return request(
    `/patients/${patientId}/provider-action-items/generate`,
    { email, method: "POST" }
  );
}

export function listProviderActionItems(
  email: string,
  patientId: number,
  filters: ProviderActionItemListFilters = {}
): Promise<ProviderActionItemListResponse> {
  return request(
    `/patients/${patientId}/provider-action-items${_qs(filters)}`,
    { email }
  );
}

export function getProviderActionItem(
  email: string,
  patientId: number,
  actionId: number
): Promise<ProviderActionItem> {
  return request(
    `/patients/${patientId}/provider-action-items/${actionId}`,
    { email }
  );
}

export function acceptProviderActionItem(
  email: string,
  patientId: number,
  actionId: number
): Promise<ProviderActionItem> {
  return request(
    `/patients/${patientId}/provider-action-items/${actionId}/accept`,
    { email, method: "POST" }
  );
}

export function dismissProviderActionItem(
  email: string,
  patientId: number,
  actionId: number
): Promise<ProviderActionItem> {
  return request(
    `/patients/${patientId}/provider-action-items/${actionId}/dismiss`,
    { email, method: "POST" }
  );
}

export function completeProviderActionItem(
  email: string,
  patientId: number,
  actionId: number
): Promise<ProviderActionItem> {
  return request(
    `/patients/${patientId}/provider-action-items/${actionId}/complete`,
    { email, method: "POST" }
  );
}

// =============================================================
// Phase 20B — Structured data layer
// =============================================================
//
// Type definitions + thin wrapper functions for the structured-data
// endpoints (patient_segments / patient_segment_memberships /
// patient_tags / patient_problem_list / clinic_workflow_templates /
// clinic_workflow_stages / work_queue_items / role_view_presets).
//
// No UI components ship in Phase 20B — these typings are for
// downstream phases (20C dashboards, 21A specialty modules) to
// consume the API contract.

// ----- enums -------------------------------------------------------

export type Phase20BEye = "OD" | "OS" | "OU";

export type ProblemStatus = "active" | "monitoring" | "inactive" | "resolved";

export type QueuePriority = "low" | "normal" | "high" | "urgent";

export type QueueStatus =
  | "open"
  | "in_progress"
  | "blocked"
  | "completed"
  | "dismissed";

export type WorkflowOwnerRole =
  | "admin"
  | "clinician"
  | "reviewer"
  | "front_desk"
  | "technician";

export type ViewPresetRole = WorkflowOwnerRole;

// ----- segments + memberships -------------------------------------

export interface PatientSegment {
  id: number;
  organization_id: number;
  name: string;
  description: string | null;
  segment_type: string;
  criteria_json: Record<string, unknown> | unknown[] | null;
  is_active: boolean;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface PatientSegmentMembership {
  id: number;
  organization_id: number;
  patient_id: number;
  segment_id: number;
  source: string;
  reason: string | null;
  created_at: string;
}

export interface SegmentCreateBody {
  name: string;
  description?: string | null;
  segment_type: string;
  criteria_json?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface SegmentUpdateBody {
  name?: string;
  description?: string | null;
  segment_type?: string;
  criteria_json?: Record<string, unknown> | null;
  is_active?: boolean;
}

export function listSegments(
  email: string,
  opts: {
    includeInactive?: boolean;
    q?: string;
    segmentType?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<PatientSegment[]> {
  const params = new URLSearchParams();
  if (opts.includeInactive) params.set("include_inactive", "true");
  if (opts.q) params.set("q", opts.q);
  if (opts.segmentType) params.set("segment_type", opts.segmentType);
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.offset !== undefined) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return request(`/segments${qs ? `?${qs}` : ""}`, { email });
}

export function createSegment(
  email: string,
  body: SegmentCreateBody
): Promise<PatientSegment> {
  return request("/segments", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateSegment(
  email: string,
  segmentId: number,
  body: SegmentUpdateBody
): Promise<PatientSegment> {
  return request(`/segments/${segmentId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function listPatientSegments(
  email: string,
  patientId: number
): Promise<PatientSegmentMembership[]> {
  return request(`/patients/${patientId}/segments`, { email });
}

export function addPatientSegment(
  email: string,
  patientId: number,
  body: { segment_id: number; source: string; reason?: string | null }
): Promise<PatientSegmentMembership> {
  return request(`/patients/${patientId}/segments`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function removePatientSegment(
  email: string,
  patientId: number,
  segmentId: number
): Promise<{ removed: boolean; membership_id: number }> {
  return request(`/patients/${patientId}/segments/${segmentId}`, {
    email,
    method: "DELETE",
  });
}

// ----- patient_tags ------------------------------------------------

export interface PatientTag {
  id: number;
  organization_id: number;
  patient_id: number;
  tag: string;
  color: string | null;
  created_by_user_id: number | null;
  created_at: string;
}

export function listPatientTags(
  email: string,
  patientId: number
): Promise<PatientTag[]> {
  return request(`/patients/${patientId}/tags`, { email });
}

export function addPatientTag(
  email: string,
  patientId: number,
  body: { tag: string; color?: string | null }
): Promise<PatientTag> {
  return request(`/patients/${patientId}/tags`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deletePatientTag(
  email: string,
  patientId: number,
  tagId: number
): Promise<{ removed: boolean; tag_id: number }> {
  return request(`/patients/${patientId}/tags/${tagId}`, {
    email,
    method: "DELETE",
  });
}

// ----- patient_problem_list ---------------------------------------

export interface PatientProblemItem {
  id: number;
  organization_id: number;
  patient_id: number;
  condition_code: string | null;
  condition_label: string;
  specialty: string | null;
  eye: Phase20BEye | null;
  status: ProblemStatus;
  onset_date: string | null;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProblemCreateBody {
  condition_code?: string | null;
  condition_label: string;
  specialty?: string | null;
  eye?: Phase20BEye | null;
  status?: ProblemStatus;
  onset_date?: string | null;
  last_reviewed_at?: string | null;
}

export interface ProblemUpdateBody {
  condition_code?: string | null;
  condition_label?: string;
  specialty?: string | null;
  eye?: Phase20BEye | null;
  status?: ProblemStatus;
  onset_date?: string | null;
  last_reviewed_at?: string | null;
}

export function listProblemList(
  email: string,
  patientId: number,
  opts: {
    specialty?: string;
    status?: ProblemStatus;
    eye?: Phase20BEye;
  } = {}
): Promise<PatientProblemItem[]> {
  const params = new URLSearchParams();
  if (opts.specialty) params.set("specialty", opts.specialty);
  if (opts.status) params.set("status", opts.status);
  if (opts.eye) params.set("eye", opts.eye);
  const qs = params.toString();
  return request(
    `/patients/${patientId}/problem-list${qs ? `?${qs}` : ""}`,
    { email }
  );
}

export function addProblem(
  email: string,
  patientId: number,
  body: ProblemCreateBody
): Promise<PatientProblemItem> {
  return request(`/patients/${patientId}/problem-list`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateProblem(
  email: string,
  patientId: number,
  itemId: number,
  body: ProblemUpdateBody
): Promise<PatientProblemItem> {
  return request(`/patients/${patientId}/problem-list/${itemId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ----- clinic_workflow_templates + stages -------------------------

export interface ClinicWorkflowTemplate {
  id: number;
  organization_id: number;
  name: string;
  specialty: string | null;
  role_owner: WorkflowOwnerRole;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicWorkflowStage {
  id: number;
  organization_id: number;
  template_id: number;
  name: string;
  stage_order: number;
  role_owner: WorkflowOwnerRole;
  sla_minutes: number | null;
  created_at: string;
}

export function listWorkflowTemplates(
  email: string,
  opts: {
    includeInactive?: boolean;
    specialty?: string;
    roleOwner?: WorkflowOwnerRole;
  } = {}
): Promise<ClinicWorkflowTemplate[]> {
  const params = new URLSearchParams();
  if (opts.includeInactive) params.set("include_inactive", "true");
  if (opts.specialty) params.set("specialty", opts.specialty);
  if (opts.roleOwner) params.set("role_owner", opts.roleOwner);
  const qs = params.toString();
  return request(`/workflow-templates${qs ? `?${qs}` : ""}`, { email });
}

export function createWorkflowTemplate(
  email: string,
  body: {
    name: string;
    specialty?: string | null;
    role_owner: WorkflowOwnerRole;
    description?: string | null;
    is_active?: boolean;
  }
): Promise<ClinicWorkflowTemplate> {
  return request("/workflow-templates", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateWorkflowTemplate(
  email: string,
  templateId: number,
  body: Partial<{
    name: string;
    specialty: string | null;
    role_owner: WorkflowOwnerRole;
    description: string | null;
    is_active: boolean;
  }>
): Promise<ClinicWorkflowTemplate> {
  return request(`/workflow-templates/${templateId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function listWorkflowStages(
  email: string,
  templateId: number
): Promise<ClinicWorkflowStage[]> {
  return request(`/workflow-templates/${templateId}/stages`, { email });
}

export function createWorkflowStage(
  email: string,
  templateId: number,
  body: {
    name: string;
    stage_order: number;
    role_owner: WorkflowOwnerRole;
    sla_minutes?: number | null;
  }
): Promise<ClinicWorkflowStage> {
  return request(`/workflow-templates/${templateId}/stages`, {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateWorkflowStage(
  email: string,
  stageId: number,
  body: Partial<{
    name: string;
    stage_order: number;
    role_owner: WorkflowOwnerRole;
    sla_minutes: number | null;
  }>
): Promise<ClinicWorkflowStage> {
  return request(`/workflow-stages/${stageId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ----- work_queue_items -------------------------------------------

export interface WorkQueueItem {
  id: number;
  organization_id: number;
  location_id: number | null;
  patient_id: number | null;
  encounter_id: number | null;
  provider_id: number | null;
  queue_type: string;
  priority: QueuePriority;
  status: QueueStatus;
  assigned_role: string | null;
  assigned_user_id: number | null;
  due_at: string | null;
  source: string;
  payload_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface WorkQueueListOpts {
  locationId?: number;
  patientId?: number;
  encounterId?: number;
  providerId?: number;
  queueType?: string;
  priority?: QueuePriority;
  status?: QueueStatus;
  assignedRole?: string;
  assignedUserId?: number;
  dueBefore?: string;
  dueAfter?: string;
  limit?: number;
  offset?: number;
}

export function listWorkQueue(
  email: string,
  opts: WorkQueueListOpts = {}
): Promise<WorkQueueItem[]> {
  const params = new URLSearchParams();
  if (opts.locationId !== undefined)
    params.set("location_id", String(opts.locationId));
  if (opts.patientId !== undefined)
    params.set("patient_id", String(opts.patientId));
  if (opts.encounterId !== undefined)
    params.set("encounter_id", String(opts.encounterId));
  if (opts.providerId !== undefined)
    params.set("provider_id", String(opts.providerId));
  if (opts.queueType) params.set("queue_type", opts.queueType);
  if (opts.priority) params.set("priority", opts.priority);
  if (opts.status) params.set("status", opts.status);
  if (opts.assignedRole) params.set("assigned_role", opts.assignedRole);
  if (opts.assignedUserId !== undefined)
    params.set("assigned_user_id", String(opts.assignedUserId));
  if (opts.dueBefore) params.set("due_before", opts.dueBefore);
  if (opts.dueAfter) params.set("due_after", opts.dueAfter);
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.offset !== undefined) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return request(`/work-queues${qs ? `?${qs}` : ""}`, { email });
}

export function createWorkQueueItem(
  email: string,
  body: {
    location_id?: number | null;
    patient_id?: number | null;
    encounter_id?: number | null;
    provider_id?: number | null;
    queue_type: string;
    priority?: QueuePriority;
    status?: QueueStatus;
    assigned_role?: string | null;
    assigned_user_id?: number | null;
    due_at?: string | null;
    source?: string;
    payload_json?: Record<string, unknown> | unknown[] | null;
  }
): Promise<WorkQueueItem> {
  return request("/work-queues", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateWorkQueueItem(
  email: string,
  itemId: number,
  body: Partial<{
    priority: QueuePriority;
    status: QueueStatus;
    assigned_role: string | null;
    assigned_user_id: number | null;
    due_at: string | null;
    payload_json: Record<string, unknown> | unknown[] | null;
    completed_at: string | null;
  }>
): Promise<WorkQueueItem> {
  return request(`/work-queues/${itemId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ----- role_view_presets ------------------------------------------

export interface RoleViewPreset {
  id: number;
  organization_id: number;
  role: ViewPresetRole;
  name: string;
  filters_json: Record<string, unknown> | unknown[] | null;
  columns_json: Record<string, unknown> | unknown[] | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export function listRoleViews(
  email: string,
  opts: { role?: ViewPresetRole; includeNonDefault?: boolean } = {}
): Promise<RoleViewPreset[]> {
  const params = new URLSearchParams();
  if (opts.role) params.set("role", opts.role);
  if (opts.includeNonDefault === false)
    params.set("include_non_default", "false");
  const qs = params.toString();
  return request(`/role-views${qs ? `?${qs}` : ""}`, { email });
}

export function createRoleView(
  email: string,
  body: {
    role: ViewPresetRole;
    name: string;
    filters_json?: Record<string, unknown> | unknown[] | null;
    columns_json?: Record<string, unknown> | unknown[] | null;
    is_default?: boolean;
  }
): Promise<RoleViewPreset> {
  return request("/role-views", {
    email,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateRoleView(
  email: string,
  presetId: number,
  body: Partial<{
    role: ViewPresetRole;
    name: string;
    filters_json: Record<string, unknown> | unknown[] | null;
    columns_json: Record<string, unknown> | unknown[] | null;
    is_default: boolean;
  }>
): Promise<RoleViewPreset> {
  return request(`/role-views/${presetId}`, {
    email,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

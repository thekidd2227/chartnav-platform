// Thin API client for the Clinical Coding Intelligence feature.
// Reuses the app's existing fetch posture (X-User-Email header).
import { API_URL } from "../../api";
import type {
  ClinicalCodingVersion,
  CodeDetail,
  FavoriteRow,
  SearchResponse,
  SpecialtyBundle,
  SpecialtyTag,
} from "./types";

async function req<T>(
  path: string,
  email: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "X-User-Email": email,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const d = body?.detail;
    const msg =
      (d && typeof d === "object" && (d.reason || d.error_code)) ||
      res.statusText;
    throw new Error(`${res.status} ${msg}`);
  }
  return body as T;
}

export function getActiveVersion(email: string) {
  return req<ClinicalCodingVersion>("/clinical-coding/version/active", email);
}

export function searchCodes(
  email: string,
  args: {
    q: string;
    dateOfService?: string;
    limit?: number;
    specialtyTag?: SpecialtyTag;
    billableOnly?: boolean;
  }
) {
  const qs = new URLSearchParams();
  qs.set("q", args.q);
  if (args.dateOfService) qs.set("dateOfService", args.dateOfService);
  if (args.limit) qs.set("limit", String(args.limit));
  if (args.specialtyTag) qs.set("specialtyTag", args.specialtyTag);
  if (args.billableOnly) qs.set("billableOnly", "true");
  return req<SearchResponse>(`/clinical-coding/search?${qs}`, email);
}

export function getCodeDetail(
  email: string,
  code: string,
  dateOfService?: string
) {
  const qs = dateOfService ? `?dateOfService=${dateOfService}` : "";
  return req<{ version: any; code: CodeDetail }>(
    `/clinical-coding/code/${encodeURIComponent(code)}${qs}`,
    email
  );
}

export function listSpecialties(email: string) {
  return req<{ specialties: SpecialtyTag[]; bundles: SpecialtyBundle[] }>(
    "/clinical-coding/specialties",
    email
  );
}

export function getSpecialtyCodes(
  email: string,
  tag: SpecialtyTag,
  dateOfService?: string
) {
  const qs = dateOfService ? `?dateOfService=${dateOfService}` : "";
  return req<{
    version: any;
    specialty_tag: SpecialtyTag;
    bundles: SpecialtyBundle[];
  }>(`/clinical-coding/specialty/${tag}/codes${qs}`, email);
}

export function listFavorites(email: string) {
  return req<FavoriteRow[]>("/clinical-coding/favorites", email);
}

export function upsertFavorite(
  email: string,
  body: {
    code: string;
    specialty_tag?: SpecialtyTag;
    is_pinned?: boolean;
    bump_usage?: boolean;
  }
) {
  return req<FavoriteRow>("/clinical-coding/favorites", email, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteFavorite(email: string, id: number) {
  return req<{ deleted: boolean; id: number }>(
    `/clinical-coding/favorites/${id}`,
    email,
    { method: "DELETE" }
  );
}

export function adminSync(
  email: string,
  body: { version_label?: string; allow_network?: boolean } = {}
) {
  return req<any>("/admin/clinical-coding/sync", email, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function adminSyncStatus(email: string) {
  return req<{ active_version: ClinicalCodingVersion; recent_jobs: any[] }>(
    "/admin/clinical-coding/sync/status",
    email
  );
}

export function adminAudit(email: string) {
  return req<{ versions: ClinicalCodingVersion[]; recent_jobs: any[] }>(
    "/admin/clinical-coding/audit",
    email
  );
}

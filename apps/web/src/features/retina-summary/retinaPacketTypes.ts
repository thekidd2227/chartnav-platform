// Phase 77 — Retina Visit Packet response shape.

import type {
  RetinaSummaryArtifactSection,
  RetinaSummaryBlocker,
  RetinaSummaryEvent,
  RetinaSummaryRoleCapabilities,
} from "./retinaSummaryTypes";

export interface RetinaPacketEncounter {
  id: number;
  patient_id: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  status: string;
  started_at: string | null;
}

export interface RetinaPacketReviewSignLock {
  vitals_signed: boolean;
  visit_draft_signed: boolean;
  fundus_signed: boolean;
  all_signed: boolean;
  blockers: RetinaSummaryBlocker[];
}

export interface RetinaPacketArtifactHash {
  section: "intake" | "visit_draft" | "fundus";
  algorithm: string;
  hash: string;
  hash_short: string;
}

export interface RetinaPacketSafetyBoundary {
  key: string;
  asserted: boolean;
  statement: string;
}

export interface RetinaVisitPacket {
  schema_version: string;
  generated_at: string;
  demo_mode: boolean;
  encounter: RetinaPacketEncounter;
  intake: RetinaSummaryArtifactSection;
  visit_draft: RetinaSummaryArtifactSection;
  fundus: RetinaSummaryArtifactSection;
  review_sign_lock: RetinaPacketReviewSignLock;
  evidence_timeline: RetinaSummaryEvent[];
  artifact_hashes: RetinaPacketArtifactHash[];
  role_capabilities: RetinaSummaryRoleCapabilities;
  safety_boundaries: RetinaPacketSafetyBoundary[];
  audit_disclosure: string;
}

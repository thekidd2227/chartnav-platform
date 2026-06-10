// Phase 86 — Workspace Profile Resolver hook + utilities.
//
// Wraps the GET /workspace-profile endpoint and exposes a stable
// React contract: a profile object, a setter that PATCHes the
// server, and helpers the Overview tab uses to decide panel
// ordering.
//
// Hard rule: the resolver never hides a panel that lacks a profile
// assignment. If the API returns a panel code the UI doesn't know
// about, that panel is treated as visible (never collapsed) — the
// safe default.

import { useCallback, useEffect, useState } from "react";

import {
  getWorkspaceProfile,
  patchWorkspaceProfile,
} from "./workspaceProfileApi";
import type {
  EncounterType,
  PanelCode,
  WorkspaceProfileResponse,
} from "./workspaceProfileTypes";

export type PanelDisposition = "prioritized" | "visible" | "collapsed";

export function panelDispositionFor(
  profile: WorkspaceProfileResponse | null,
  panel: PanelCode,
): PanelDisposition {
  if (!profile) return "visible";
  if (profile.profile.prioritized_panels.some((p) => p.code === panel)) {
    return "prioritized";
  }
  if (profile.profile.collapsed_panels.some((p) => p.code === panel)) {
    return "collapsed";
  }
  return "visible";
}

export function panelOrderIndex(
  profile: WorkspaceProfileResponse | null,
  panel: PanelCode,
): number {
  if (!profile) return 0;
  const idx = profile.profile.panel_order.indexOf(panel);
  return idx < 0 ? Number.MAX_SAFE_INTEGER : idx;
}

export interface WorkspaceProfileState {
  profile: WorkspaceProfileResponse | null;
  loading: boolean;
  error: string | null;
  updating: boolean;
  setEncounterType: (typ: EncounterType) => Promise<void>;
  refresh: () => void;
}

export function useWorkspaceProfile(
  encounterId: number | null,
): WorkspaceProfileState {
  const [profile, setProfile] = useState<WorkspaceProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const refresh = useCallback(() => {
    if (encounterId === null) return;
    setLoading(true);
    setError(null);
    getWorkspaceProfile(encounterId)
      .then(setProfile)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setEncounterType = useCallback(
    async (typ: EncounterType) => {
      if (encounterId === null) return;
      setUpdating(true);
      setError(null);
      try {
        const next = await patchWorkspaceProfile(encounterId, typ);
        setProfile(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Update failed");
      } finally {
        setUpdating(false);
      }
    },
    [encounterId],
  );

  return { profile, loading, error, updating, setEncounterType, refresh };
}

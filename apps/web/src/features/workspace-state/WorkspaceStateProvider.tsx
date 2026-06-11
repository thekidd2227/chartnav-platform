// Phase 91 — Unified Workspace State context + hook.
//
// Wraps the GET /workspace-state endpoint in a React context so any
// panel can subscribe to the active visit mode + active laterality +
// emphasis projection. The provider also exposes PATCH helpers used
// by the Visit Mode Ribbon and Eye-Linked Laterality Switcher.
//
// Boundary copy is enforced in the panel and ribbon components; the
// provider itself stores no clinical free text.

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  getWorkspaceState,
  patchActiveLaterality as patchActiveLateralityApi,
  patchVisitMode as patchVisitModeApi,
} from "./workspaceStateApi";
import type {
  ActiveLaterality,
  VisitMode,
  WorkspaceStateResponse,
} from "./workspaceStateTypes";

export interface WorkspaceStateValue {
  state: WorkspaceStateResponse | null;
  loading: boolean;
  error: string | null;
  updating: boolean;
  setVisitMode: (mode: VisitMode) => Promise<void>;
  setActiveLaterality: (lat: ActiveLaterality) => Promise<void>;
  refresh: () => void;
}

const WorkspaceStateContext = createContext<WorkspaceStateValue | null>(null);

interface ProviderProps {
  encounterId: number | null;
  children: React.ReactNode;
}

export function WorkspaceStateProvider({ encounterId, children }: ProviderProps) {
  const [state, setState] = useState<WorkspaceStateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const refresh = useCallback(() => {
    if (encounterId === null) return;
    setLoading(true);
    setError(null);
    getWorkspaceState(encounterId)
      .then(setState)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setVisitMode = useCallback(
    async (mode: VisitMode) => {
      if (encounterId === null) return;
      setUpdating(true);
      setError(null);
      try {
        const next = await patchVisitModeApi(encounterId, mode);
        setState(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Visit mode update failed");
      } finally {
        setUpdating(false);
      }
    },
    [encounterId],
  );

  const setActiveLaterality = useCallback(
    async (lat: ActiveLaterality) => {
      if (encounterId === null) return;
      setUpdating(true);
      setError(null);
      try {
        const next = await patchActiveLateralityApi(encounterId, lat);
        setState(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Laterality update failed");
      } finally {
        setUpdating(false);
      }
    },
    [encounterId],
  );

  const value: WorkspaceStateValue = {
    state,
    loading,
    error,
    updating,
    setVisitMode,
    setActiveLaterality,
    refresh,
  };

  return (
    <WorkspaceStateContext.Provider value={value}>
      {children}
    </WorkspaceStateContext.Provider>
  );
}

export function useWorkspaceState(): WorkspaceStateValue | null {
  return useContext(WorkspaceStateContext);
}

export function panelIsEmphasised(
  state: WorkspaceStateResponse | null,
  panel: string,
): boolean {
  if (!state) return false;
  return state.emphasis.emphasised_panels.includes(panel as never);
}

export function panelIsLateralityLinked(
  state: WorkspaceStateResponse | null,
  panel: string,
): boolean {
  if (!state) return false;
  return state.laterality_linked_panels.includes(panel);
}

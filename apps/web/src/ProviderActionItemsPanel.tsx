// ProviderActionItemsPanel — Phase 11.
//
// Provider-reviewable action queue. ChartNav surfaces deterministic
// review tasks; the provider Accepts, Dismisses, or Completes each
// one. The panel renders no order, coding, referral, or patient-
// messaging button — every action is a review prompt only.

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  ProviderActionItem,
  ProviderActionItemListFilters,
  ProviderActionPriority,
  ProviderActionStatus,
  acceptProviderActionItem,
  completeProviderActionItem,
  dismissProviderActionItem,
  generateProviderActionItems,
  listProviderActionItems,
} from "./api";

interface Props {
  identity: string;
  patientId: number;
  encounterId: number | null;
}

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | null;

const STATUS_LABEL: Record<ProviderActionStatus, string> = {
  suggested: "Suggested",
  accepted: "Accepted",
  dismissed: "Dismissed",
  completed: "Completed",
};

const PRIORITY_LABEL: Record<ProviderActionPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

export function ProviderActionItemsPanel({ identity, patientId }: Props) {
  const [items, setItems] = useState<ProviderActionItem[]>([]);
  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

  // Filters.
  const [statusFilter, setStatusFilter] = useState<"" | ProviderActionStatus>("");
  const [priorityFilter, setPriorityFilter] = useState<"" | ProviderActionPriority>("");
  const [actionTypeFilter, setActionTypeFilter] = useState<string>("");

  const filters: ProviderActionItemListFilters = useMemo(() => {
    const f: ProviderActionItemListFilters = {};
    if (statusFilter) f.status = statusFilter;
    if (priorityFilter) f.priority = priorityFilter;
    if (actionTypeFilter) f.action_type = actionTypeFilter;
    return f;
  }, [statusFilter, priorityFilter, actionTypeFilter]);

  const refresh = useCallback(async () => {
    try {
      setBusy(true);
      const res = await listProviderActionItems(identity, patientId, filters);
      setItems(res.items);
    } catch (err) {
      setBanner({
        kind: "error",
        msg: `Could not load action items: ${friendly(err)}`,
      });
    } finally {
      setBusy(false);
    }
  }, [identity, patientId, filters]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onGenerate = useCallback(async () => {
    try {
      setBusy(true);
      const res = await generateProviderActionItems(identity, patientId);
      setBanner({
        kind: "ok",
        msg: `Generated ${res.created_count} new (reused ${res.reused_count}).`,
      });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Generate failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [identity, patientId, refresh]);

  const onAccept = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        await acceptProviderActionItem(identity, patientId, id);
        setBanner({ kind: "ok", msg: `Action #${id} accepted.` });
        await refresh();
      } catch (err) {
        setBanner({ kind: "error", msg: `Accept failed: ${friendly(err)}` });
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId, refresh]
  );

  const onDismiss = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        await dismissProviderActionItem(identity, patientId, id);
        setBanner({ kind: "ok", msg: `Action #${id} dismissed.` });
        await refresh();
      } catch (err) {
        setBanner({ kind: "error", msg: `Dismiss failed: ${friendly(err)}` });
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId, refresh]
  );

  const onComplete = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        await completeProviderActionItem(identity, patientId, id);
        setBanner({ kind: "ok", msg: `Action #${id} completed.` });
        await refresh();
      } catch (err) {
        setBanner({ kind: "error", msg: `Complete failed: ${friendly(err)}` });
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId, refresh]
  );

  return (
    <div
      className="provider-action-items-panel"
      data-testid="provider-action-items-panel"
    >
      <header className="provider-action-items-panel__header">
        <h3>Provider action queue</h3>
        <p
          className="provider-action-items-panel__hint"
          data-testid="provider-action-items-banner-copy"
        >
          Provider action suggestions — review required. ChartNav does not
          create orders, send referrals, message patients, or take action
          automatically.
        </p>
      </header>

      {banner && (
        <div
          role="status"
          data-testid="provider-action-items-banner"
          className={`flash flash--${banner.kind}`}
        >
          {banner.msg}
        </div>
      )}

      <div className="provider-action-items-panel__controls">
        <button
          type="button"
          onClick={onGenerate}
          disabled={busy}
          data-testid="provider-action-items-generate"
        >
          Generate action suggestions
        </button>
        <label>
          <span>Status</span>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as "" | ProviderActionStatus)
            }
            disabled={busy}
            data-testid="provider-action-items-filter-status"
          >
            <option value="">All</option>
            <option value="suggested">Suggested</option>
            <option value="accepted">Accepted</option>
            <option value="dismissed">Dismissed</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label>
          <span>Priority</span>
          <select
            value={priorityFilter}
            onChange={(e) =>
              setPriorityFilter(e.target.value as "" | ProviderActionPriority)
            }
            disabled={busy}
            data-testid="provider-action-items-filter-priority"
          >
            <option value="">All</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label>
          <span>Action type</span>
          <input
            type="text"
            value={actionTypeFilter}
            onChange={(e) => setActionTypeFilter(e.target.value.trim())}
            placeholder="e.g. review_scribe_session"
            disabled={busy}
            data-testid="provider-action-items-filter-action-type"
          />
        </label>
      </div>

      {items.length === 0 ? (
        <p className="muted" data-testid="provider-action-items-empty">
          No action items match the current filters.
        </p>
      ) : (
        <ul
          className="provider-action-items-panel__list"
          data-testid="provider-action-items-list"
        >
          {items.map((item) => {
            const tid = `provider-action-item-${item.id}`;
            const showAccept = item.status === "suggested";
            const showDismiss =
              item.status === "suggested" || item.status === "accepted";
            const showComplete = item.status === "accepted";
            return (
              <li
                key={item.id}
                className={`provider-action-items-panel__item provider-action-items-panel__item--${item.status}`}
                data-testid={tid}
              >
                <div className="provider-action-items-panel__row">
                  <span
                    className={`provider-action-items-panel__priority provider-action-items-panel__priority--${item.priority}`}
                    data-testid={`${tid}-priority`}
                  >
                    {PRIORITY_LABEL[item.priority]}
                  </span>
                  <strong data-testid={`${tid}-title`}>{item.title}</strong>
                  <span
                    className={`provider-action-items-panel__status provider-action-items-panel__status--${item.status}`}
                    data-testid={`${tid}-status`}
                  >
                    {STATUS_LABEL[item.status]}
                  </span>
                </div>
                <p
                  className="provider-action-items-panel__reason"
                  data-testid={`${tid}-reason`}
                >
                  {item.reason}
                </p>
                <p className="muted">
                  Type: <code>{item.action_type}</code>
                  {item.source_type !== null && (
                    <>
                      {" · "}Source:{" "}
                      <code>
                        {item.source_type}
                        {item.source_id !== null && ` #${item.source_id}`}
                      </code>
                    </>
                  )}
                </p>
                <div className="provider-action-items-panel__item-actions">
                  {showAccept && (
                    <button
                      type="button"
                      onClick={() => onAccept(item.id)}
                      disabled={busy}
                      data-testid={`${tid}-accept`}
                    >
                      Accept
                    </button>
                  )}
                  {showComplete && (
                    <button
                      type="button"
                      onClick={() => onComplete(item.id)}
                      disabled={busy}
                      data-testid={`${tid}-complete`}
                    >
                      Complete
                    </button>
                  )}
                  {showDismiss && (
                    <button
                      type="button"
                      onClick={() => onDismiss(item.id)}
                      disabled={busy}
                      data-testid={`${tid}-dismiss`}
                    >
                      Dismiss
                    </button>
                  )}
                  {item.is_terminal && (
                    <span
                      className="muted"
                      data-testid={`${tid}-readonly`}
                    >
                      Read-only — {STATUS_LABEL[item.status]}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

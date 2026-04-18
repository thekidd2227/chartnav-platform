import { useCallback, useEffect, useMemo, useState } from "react";
import {
  API_URL,
  ALLOWED_STATUSES,
  ApiError,
  Encounter,
  EncounterFilters,
  Me,
  Role,
  WorkflowEvent,
  allowedNextStatuses,
  canCreateEvent,
  createEncounterEvent,
  getEncounter,
  getEncounterEvents,
  getMe,
  listEncounters,
  updateEncounterStatus,
} from "./api";
import { SEEDED_IDENTITIES, loadIdentity, saveIdentity } from "./identity";

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | { kind: "info"; msg: string }
  | null;

export default function App() {
  const [identity, setIdentity] = useState<string>(() => loadIdentity());
  const [me, setMe] = useState<Me | null>(null);
  const [meError, setMeError] = useState<string | null>(null);

  const [filters, setFilters] = useState<EncounterFilters>({});
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [banner, setBanner] = useState<Banner>(null);

  // ---- data loaders ----------------------------------------------------

  const refreshMe = useCallback(async () => {
    setMe(null);
    setMeError(null);
    try {
      const m = await getMe(identity);
      setMe(m);
    } catch (e) {
      setMeError(friendly(e));
    }
  }, [identity]);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const rows = await listEncounters(identity, filters);
      setEncounters(rows);
      // If the selected encounter disappeared from the list, clear detail.
      if (selectedId && !rows.some((r) => r.id === selectedId)) {
        setSelectedId(null);
        setEncounter(null);
        setEvents([]);
      }
    } catch (e) {
      setEncounters([]);
      setListError(friendly(e));
    } finally {
      setListLoading(false);
    }
  }, [identity, filters, selectedId]);

  const refreshDetail = useCallback(
    async (id: number | null) => {
      if (id == null) {
        setEncounter(null);
        setEvents([]);
        setDetailError(null);
        return;
      }
      setDetailLoading(true);
      setDetailError(null);
      try {
        const [enc, evs] = await Promise.all([
          getEncounter(identity, id),
          getEncounterEvents(identity, id),
        ]);
        setEncounter(enc);
        setEvents(evs);
      } catch (e) {
        setEncounter(null);
        setEvents([]);
        setDetailError(friendly(e));
      } finally {
        setDetailLoading(false);
      }
    },
    [identity]
  );

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    refreshDetail(selectedId);
  }, [selectedId, refreshDetail]);

  // ---- handlers --------------------------------------------------------

  const onIdentityChange = (email: string) => {
    setIdentity(email);
    saveIdentity(email);
    setSelectedId(null);
    setEncounter(null);
    setEvents([]);
    setBanner({ kind: "info", msg: `Identity switched to ${email}` });
  };

  const onFilterChange = (next: EncounterFilters) => setFilters(next);

  const onStatusTransition = async (status: string) => {
    if (!encounter) return;
    setBanner(null);
    try {
      const updated = await updateEncounterStatus(identity, encounter.id, status);
      setEncounter(updated);
      await Promise.all([
        getEncounterEvents(identity, encounter.id).then(setEvents),
        refreshList(),
      ]);
      setBanner({ kind: "ok", msg: `Status → ${status}` });
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  };

  const onAddEvent = async (type: string, raw: string) => {
    if (!encounter) return;
    setBanner(null);
    let data: unknown = undefined;
    const trimmed = raw.trim();
    if (trimmed) {
      try {
        data = JSON.parse(trimmed);
      } catch {
        data = trimmed; // pass through as a string
      }
    }
    try {
      await createEncounterEvent(identity, encounter.id, {
        event_type: type,
        event_data: data,
      });
      setEvents(await getEncounterEvents(identity, encounter.id));
      setBanner({ kind: "ok", msg: `Event '${type}' added` });
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    }
  };

  // ---- render ----------------------------------------------------------

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <span className="mark-a">Chart</span>
          <span className="mark-b">Nav</span>
          <span className="sub">Workflow</span>
        </div>
        <div className="header-meta">
          <IdentityBadge me={me} meError={meError} />
          <span className="chip">API {API_URL}</span>
          <IdentityPicker value={identity} onChange={onIdentityChange} />
        </div>
      </header>

      <div className="layout">
        <aside className="layout__list">
          <FilterBar value={filters} onChange={onFilterChange} />
          <EncounterList
            rows={encounters}
            loading={listLoading}
            error={listError}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>

        <section className="layout__detail">
          {banner && (
            <div className={`banner banner--${banner.kind}`}>{banner.msg}</div>
          )}
          {selectedId == null ? (
            <div className="empty">
              Select an encounter from the list to see details, events, and allowed actions.
            </div>
          ) : (
            <EncounterDetail
              loading={detailLoading}
              error={detailError}
              encounter={encounter}
              events={events}
              me={me}
              onTransition={onStatusTransition}
              onAddEvent={onAddEvent}
            />
          )}
        </section>
      </div>
    </div>
  );
}

// ---------- subcomponents -------------------------------------------------

function IdentityBadge({ me, meError }: { me: Me | null; meError: string | null }) {
  if (meError) {
    return <span className="chip" style={{ color: "var(--danger)" }}>auth: {meError}</span>;
  }
  if (!me) return <span className="chip">resolving identity…</span>;
  return (
    <span className="chip">
      {me.email} · {me.role} · org {me.organization_id}
    </span>
  );
}

function IdentityPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (email: string) => void;
}) {
  const isSeeded = SEEDED_IDENTITIES.some((s) => s.email === value);
  const [custom, setCustom] = useState(isSeeded ? "" : value);
  const [mode, setMode] = useState<"seeded" | "custom">(
    isSeeded ? "seeded" : "custom"
  );
  return (
    <div className="identity-picker">
      <label className="subtle-note" htmlFor="dev-identity">
        identity
      </label>
      {mode === "seeded" ? (
        <select
          id="dev-identity"
          value={value}
          onChange={(e) => {
            if (e.target.value === "__custom__") {
              setMode("custom");
              return;
            }
            onChange(e.target.value);
          }}
        >
          {SEEDED_IDENTITIES.map((s) => (
            <option key={s.email} value={s.email}>
              {s.label} · {s.email}
            </option>
          ))}
          <option value="__custom__">Custom email…</option>
        </select>
      ) : (
        <>
          <input
            type="email"
            value={custom}
            placeholder="user@example.com"
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && custom.trim()) onChange(custom.trim());
            }}
          />
          <button
            className="btn"
            onClick={() => custom.trim() && onChange(custom.trim())}
          >
            use
          </button>
          <button className="btn btn--muted" onClick={() => setMode("seeded")}>
            seeded
          </button>
        </>
      )}
    </div>
  );
}

function FilterBar({
  value,
  onChange,
}: {
  value: EncounterFilters;
  onChange: (next: EncounterFilters) => void;
}) {
  const update = <K extends keyof EncounterFilters>(
    key: K,
    v: EncounterFilters[K] | undefined
  ) => {
    const next = { ...value };
    if (v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v))) {
      delete (next as any)[key];
    } else {
      (next as any)[key] = v;
    }
    onChange(next);
  };

  return (
    <div className="filters">
      <label>
        Status
        <select
          value={value.status ?? ""}
          onChange={(e) => update("status", e.target.value || undefined)}
        >
          <option value="">Any</option>
          {ALLOWED_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label>
        Provider
        <input
          type="text"
          placeholder="Dr. Carter"
          value={value.provider_name ?? ""}
          onChange={(e) => update("provider_name", e.target.value || undefined)}
        />
      </label>
      <label>
        Location ID
        <input
          type="number"
          min={1}
          placeholder="—"
          value={value.location_id ?? ""}
          onChange={(e) => {
            const n = e.target.value ? parseInt(e.target.value, 10) : undefined;
            update("location_id", Number.isNaN(n) ? undefined : n);
          }}
        />
      </label>
      {Object.keys(value).length > 0 && (
        <button className="filter-clear" onClick={() => onChange({})}>
          clear
        </button>
      )}
    </div>
  );
}

function EncounterList({
  rows,
  loading,
  error,
  selectedId,
  onSelect,
}: {
  rows: Encounter[];
  loading: boolean;
  error: string | null;
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  if (loading) return <div className="empty">Loading…</div>;
  if (error)
    return (
      <div className="empty" style={{ color: "var(--danger)" }}>
        {error}
      </div>
    );
  if (!rows.length)
    return <div className="empty">No encounters match these filters.</div>;

  return (
    <div className="enc-list">
      {rows.map((e) => (
        <div
          key={e.id}
          className={"enc-row" + (selectedId === e.id ? " is-active" : "")}
          onClick={() => onSelect(e.id)}
          role="button"
          tabIndex={0}
          onKeyDown={(ev) => {
            if (ev.key === "Enter" || ev.key === " ") onSelect(e.id);
          }}
        >
          <div>
            <div className="enc-row__pid">
              #{e.id} · {e.patient_identifier}
            </div>
            <div className="enc-row__name">{e.patient_name ?? "—"}</div>
            <div className="enc-row__provider">{e.provider_name}</div>
          </div>
          <span className="status-pill" data-status={e.status}>
            {e.status.replace(/_/g, " ")}
          </span>
        </div>
      ))}
    </div>
  );
}

function EncounterDetail({
  loading,
  error,
  encounter,
  events,
  me,
  onTransition,
  onAddEvent,
}: {
  loading: boolean;
  error: string | null;
  encounter: Encounter | null;
  events: WorkflowEvent[];
  me: Me | null;
  onTransition: (status: string) => void;
  onAddEvent: (type: string, data: string) => void;
}) {
  if (loading) return <div className="empty">Loading…</div>;
  if (error) return <div className="banner banner--error">{error}</div>;
  if (!encounter) return null;

  const role: Role | null = me?.role ?? null;
  const nextStatuses = role ? allowedNextStatuses(role, encounter.status) : [];
  const eventAllowed = role ? canCreateEvent(role) : false;

  return (
    <div>
      <div className="detail__head">
        <div>
          <h2>
            #{encounter.id} · {encounter.patient_name ?? encounter.patient_identifier}
          </h2>
          <div className="sub">
            {encounter.patient_identifier} · {encounter.provider_name}
          </div>
        </div>
        <span className="status-pill" data-status={encounter.status}>
          {encounter.status.replace(/_/g, " ")}
        </span>
      </div>

      <dl className="detail__facts">
        <div><dt>Organization</dt><dd>#{encounter.organization_id}</dd></div>
        <div><dt>Location</dt><dd>#{encounter.location_id}</dd></div>
        <div><dt>Scheduled</dt><dd>{fmt(encounter.scheduled_at)}</dd></div>
        <div><dt>Started</dt><dd>{fmt(encounter.started_at)}</dd></div>
        <div><dt>Completed</dt><dd>{fmt(encounter.completed_at)}</dd></div>
        <div><dt>Created</dt><dd>{fmt(encounter.created_at)}</dd></div>
      </dl>

      <section className="section">
        <h3>Allowed transitions ({role ?? "—"})</h3>
        {nextStatuses.length ? (
          <div className="actions">
            {nextStatuses.map((s) => (
              <button
                key={s}
                className="btn btn--primary"
                onClick={() => onTransition(s)}
              >
                Move to {s.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        ) : (
          <div className="subtle-note">
            No transitions available from <code>{encounter.status}</code> for role{" "}
            <code>{role}</code>. (The backend is the source of truth — it will
            reject anything it disallows.)
          </div>
        )}
      </section>

      <section className="section">
        <h3>Timeline ({events.length})</h3>
        {events.map((ev) => (
          <div className="event-item" key={ev.id}>
            <div className="event-item__head">
              <span className="event-item__type">{ev.event_type}</span>
              <span className="event-item__when">{fmt(ev.created_at)}</span>
            </div>
            <div className="event-item__data">{renderEventData(ev)}</div>
          </div>
        ))}
      </section>

      <section className="section">
        <h3>Add event</h3>
        {eventAllowed ? (
          <EventComposer onSubmit={onAddEvent} />
        ) : (
          <div className="subtle-note">
            Your role (<code>{role}</code>) cannot add workflow events. Switch
            to an admin or clinician identity to write.
          </div>
        )}
      </section>
    </div>
  );
}

function EventComposer({ onSubmit }: { onSubmit: (type: string, data: string) => void }) {
  const [type, setType] = useState("");
  const [data, setData] = useState("");
  const disabled = !type.trim();
  return (
    <form
      className="event-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!disabled) {
          onSubmit(type.trim(), data);
          setType("");
          setData("");
        }
      }}
    >
      <input
        type="text"
        placeholder="event_type (e.g. note_reviewed)"
        value={type}
        onChange={(e) => setType(e.target.value)}
        required
      />
      <textarea
        placeholder='event_data (optional JSON, e.g. {"comment":"..."})'
        value={data}
        onChange={(e) => setData(e.target.value)}
      />
      <div className="row">
        <button type="submit" className="btn btn--primary" disabled={disabled}>
          Append event
        </button>
        <span className="subtle-note">
          JSON is parsed if valid; otherwise sent as a string.
        </span>
      </div>
    </form>
  );
}

// ---------- pure helpers --------------------------------------------------

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

const MEMO_RENDERERS = new WeakMap<object, string>();
function renderEventData(ev: WorkflowEvent): string {
  const d = ev.event_data;
  if (d == null) return "—";
  if (typeof d === "string") return d;
  if (typeof d === "object") {
    if (MEMO_RENDERERS.has(d as object))
      return MEMO_RENDERERS.get(d as object)!;
    const s = Object.entries(d as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
      .join("  ·  ");
    MEMO_RENDERERS.set(d as object, s);
    return s;
  }
  return String(d);
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) {
    return `${e.status} ${e.errorCode} — ${e.reason}`;
  }
  if (e instanceof Error) return e.message;
  return String(e);
}

// memo-useful nothing for now; keeps eslint happy about unused imports
void useMemo;

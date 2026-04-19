import { useCallback, useEffect, useState } from "react";
import {
  API_URL,
  ALLOWED_STATUSES,
  ApiError,
  Encounter,
  EncounterFilters,
  EVENT_TYPES,
  Me,
  NewEncounterInput,
  Role,
  WorkflowEvent,
  allowedNextStatuses,
  canCreateEncounter,
  canCreateEvent,
  createEncounter,
  createEncounterEvent,
  encounterIsNative,
  encounterSourceLabel,
  getEncounter,
  getEncounterEvents,
  getMe,
  isAdmin,
  listEncountersPage,
  listLocations,
  updateEncounterStatus,
} from "./api";
import { AdminPanel } from "./AdminPanel";
import { NoteWorkspace } from "./NoteWorkspace";
import { SEEDED_IDENTITIES, loadIdentity, saveIdentity } from "./identity";

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | { kind: "info"; msg: string }
  | null;

export default function App() {
  const [identity, setIdentity] = useState<string>(() => loadIdentity());
  const [me, setMe] = useState<Me | null>(null);
  const [meLoading, setMeLoading] = useState(true);
  const [meError, setMeError] = useState<string | null>(null);

  const [filters, setFilters] = useState<EncounterFilters>({});
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);

  const [selectedId, setSelectedId] = useState<number | string | null>(null);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [banner, setBanner] = useState<Banner>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  // Pagination
  const PAGE_SIZE = 25;
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  // ---- loaders ---------------------------------------------------------

  const refreshMe = useCallback(async () => {
    setMeLoading(true);
    setMeError(null);
    try {
      setMe(await getMe(identity));
    } catch (e) {
      setMe(null);
      setMeError(friendly(e));
    } finally {
      setMeLoading(false);
    }
  }, [identity]);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const { items, total: t } = await listEncountersPage(
        identity,
        filters,
        { limit: PAGE_SIZE, offset }
      );
      setEncounters(items);
      setTotal(t);
      if (selectedId && !items.some((r) => r.id === selectedId)) {
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
  }, [identity, filters, selectedId, offset]);

  const refreshDetail = useCallback(
    async (id: number | string | null) => {
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
    if (email === identity) return;
    setIdentity(email);
    saveIdentity(email);
    setSelectedId(null);
    setEncounter(null);
    setEvents([]);
    setShowCreate(false);
    setShowAdmin(false);
    setOffset(0);
    setBanner({ kind: "info", msg: `Identity switched to ${email}` });
  };

  const onTransition = async (status: string) => {
    if (!encounter) return;
    setBanner(null);
    try {
      const updated = await updateEncounterStatus(identity, encounter.id, status);
      setEncounter(updated);
      setEvents(await getEncounterEvents(identity, encounter.id));
      await refreshList();
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
        data = trimmed;
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

  const onCreateEncounter = async (input: NewEncounterInput) => {
    setBanner(null);
    const created = await createEncounter(identity, input);
    await refreshList();
    setSelectedId(created.id);
    setShowCreate(false);
    setBanner({
      kind: "ok",
      msg: `Encounter #${created.id} created (${created.patient_identifier})`,
    });
  };

  // ---- render ----------------------------------------------------------

  const canCreate = me ? canCreateEncounter(me.role) : false;
  const canAdmin = me ? isAdmin(me.role) : false;

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <img
            className="brand__logo"
            src="/brand/chartnav-logo.svg"
            alt="ChartNav"
            width="140"
            height="32"
          />
          <span className="sub">Workflow</span>
        </div>
        <div className="header-meta">
          <IdentityBadge me={me} meError={meError} meLoading={meLoading} />
          <span className="chip">API {API_URL}</span>
          {canCreate && (
            <button
              className="btn btn--primary"
              onClick={() => setShowCreate(true)}
              data-testid="open-create-encounter"
            >
              + New encounter
            </button>
          )}
          {canAdmin && (
            <button
              className="btn"
              onClick={() => setShowAdmin(true)}
              data-testid="open-admin-panel"
            >
              Admin
            </button>
          )}
          <IdentityPicker value={identity} onChange={onIdentityChange} />
        </div>
      </header>

      <div className="layout">
        <aside className="layout__list">
          <FilterBar
            value={filters}
            onChange={(next) => {
              setFilters(next);
              setOffset(0);
            }}
          />
          <EncounterList
            rows={encounters}
            loading={listLoading}
            error={listError}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          {total > PAGE_SIZE && (
            <div className="pagination" data-testid="pagination">
              <button
                className="btn"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                data-testid="page-prev"
              >
                ← Prev
              </button>
              <span className="subtle-note" data-testid="page-status">
                {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <button
                className="btn"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                data-testid="page-next"
              >
                Next →
              </button>
            </div>
          )}
        </aside>

        <section className="layout__detail">
          {banner && (
            <div
              className={`banner banner--${banner.kind}`}
              role={banner.kind === "error" ? "alert" : "status"}
              data-testid={`banner-${banner.kind}`}
            >
              {banner.msg}
            </div>
          )}
          {selectedId == null ? (
            <div className="empty">
              Select an encounter from the list to see details, events, and allowed actions.
              {canCreate && (
                <>
                  {" "}
                  Or click <strong>+ New encounter</strong> above to create one.
                </>
              )}
            </div>
          ) : (
            <EncounterDetail
              loading={detailLoading}
              error={detailError}
              encounter={encounter}
              events={events}
              me={me}
              identity={identity}
              onTransition={onTransition}
              onAddEvent={onAddEvent}
            />
          )}
        </section>
      </div>

      {showCreate && me && (
        <CreateEncounterModal
          identity={identity}
          me={me}
          onCancel={() => setShowCreate(false)}
          onSubmit={onCreateEncounter}
        />
      )}
      {showAdmin && me && isAdmin(me.role) && (
        <AdminPanel
          identity={identity}
          me={me}
          onClose={() => setShowAdmin(false)}
        />
      )}

      <footer
        className="app-footer"
        role="contentinfo"
        data-testid="app-footer"
      >
        <span className="app-footer__brand">
          <strong>ChartNav</strong>
          <span aria-hidden="true"> · </span>
          <span>Clinical workflow platform</span>
        </span>
        <span
          className="app-footer__powered"
          data-testid="app-footer-arcg"
        >
          Powered by <strong>ARCG Systems</strong>
        </span>
      </footer>
    </>
  );
}

// ---------- subcomponents -------------------------------------------------

function IdentityBadge({
  me,
  meError,
  meLoading,
}: {
  me: Me | null;
  meError: string | null;
  meLoading: boolean;
}) {
  if (meLoading && !me)
    return (
      <span className="chip" data-testid="identity-loading">
        resolving identity…
      </span>
    );
  if (meError)
    return (
      <span
        className="chip"
        style={{ color: "var(--danger)" }}
        data-testid="identity-error"
      >
        auth: {meError}
      </span>
    );
  if (!me) return <span className="chip">—</span>;
  return (
    <span className="chip" data-testid="identity-badge">
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
          data-testid="identity-select"
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
          data-testid="filter-status"
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
          data-testid="filter-provider"
          placeholder="Dr. Carter"
          value={value.provider_name ?? ""}
          onChange={(e) => update("provider_name", e.target.value || undefined)}
        />
      </label>
      <label>
        Location ID
        <input
          type="number"
          data-testid="filter-location"
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
  selectedId: number | string | null;
  onSelect: (id: number | string) => void;
}) {
  if (loading && rows.length === 0)
    return (
      <div className="empty" data-testid="list-loading">
        Loading…
      </div>
    );
  if (error)
    return (
      <div
        className="empty"
        style={{ color: "var(--danger)" }}
        data-testid="list-error"
      >
        {error}
      </div>
    );
  if (!rows.length)
    return (
      <div className="empty" data-testid="list-empty">
        No encounters match these filters.
      </div>
    );

  return (
    <div className="enc-list" data-testid="enc-list">
      {rows.map((e) => (
        <div
          key={e.id}
          className={"enc-row" + (selectedId === e.id ? " is-active" : "")}
          onClick={() => onSelect(e.id)}
          role="button"
          tabIndex={0}
          data-testid={`enc-row-${e.id}`}
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
  identity,
  onTransition,
  onAddEvent,
}: {
  loading: boolean;
  error: string | null;
  encounter: Encounter | null;
  events: WorkflowEvent[];
  me: Me | null;
  identity: string;
  onTransition: (status: string) => Promise<void> | void;
  onAddEvent: (type: string, data: string) => Promise<void> | void;
}) {
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [pendingEvent, setPendingEvent] = useState(false);

  if (loading) return <div className="empty">Loading…</div>;
  if (error)
    return (
      <div className="banner banner--error" role="alert">
        {error}
      </div>
    );
  if (!encounter) return null;

  const role: Role | null = me?.role ?? null;
  const nativeEncounter = encounterIsNative(encounter);
  // Status transitions are only meaningful when ChartNav owns the
  // row. Integrated-mode encounters live in the external EHR; the
  // backend returns `encounter_write_unsupported` when called.
  const nextStatuses =
    role && nativeEncounter ? allowedNextStatuses(role, encounter.status) : [];
  const eventAllowed = role ? canCreateEvent(role) : false;

  return (
    <div data-testid="encounter-detail">
      <div className="detail__head">
        <div>
          <h2>
            #{encounter.id} · {encounter.patient_name ?? encounter.patient_identifier}
          </h2>
          <div className="sub">
            {encounter.patient_identifier} · {encounter.provider_name}
          </div>
        </div>
        <div className="detail__head-right">
          <span
            className="status-pill"
            data-status={encounter.status}
            data-testid="detail-status"
          >
            {encounter.status.replace(/_/g, " ")}
          </span>
          <span
            className="source-chip"
            data-testid="detail-source-chip"
            data-source={encounter._source ?? "chartnav"}
          >
            {encounterSourceLabel(encounter)}
          </span>
        </div>
      </div>

      {!nativeEncounter && (
        <div
          className="banner banner--info"
          data-testid="external-encounter-banner"
          role="note"
        >
          <strong>This encounter lives in the external EHR.</strong>{" "}
          Status transitions and encounter-level edits are disabled in this
          mode. ChartNav's workflow events, transcript ingestion, and note
          drafting remain available — those are ChartNav-native.
        </div>
      )}

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
          <div className="actions" data-testid="transitions">
            {nextStatuses.map((s) => (
              <button
                key={s}
                className="btn btn--primary"
                data-testid={`transition-${s}`}
                disabled={pendingStatus !== null}
                onClick={async () => {
                  setPendingStatus(s);
                  try {
                    await onTransition(s);
                  } finally {
                    setPendingStatus(null);
                  }
                }}
              >
                {pendingStatus === s ? "…" : `Move to ${s.replace(/_/g, " ")}`}
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

      {me && nativeEncounter && typeof encounter.id === "number" && (
        <section className="section">
          <NoteWorkspace
            identity={identity}
            me={me}
            encounterId={encounter.id}
            patientDisplay={
              encounter.patient_name ?? encounter.patient_identifier
            }
            providerDisplay={encounter.provider_name}
          />
        </section>
      )}
      {me && !nativeEncounter && (
        <section className="section" data-testid="note-workspace-external-note">
          <div className="subtle-note">
            Note drafting is available on ChartNav-native encounters today.
            For externally-sourced encounters, ingest via the workflow
            once the encounter is mirrored into ChartNav.
          </div>
        </section>
      )}

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
          <EventComposer
            pending={pendingEvent}
            onSubmit={async (type, data) => {
              setPendingEvent(true);
              try {
                await onAddEvent(type, data);
              } finally {
                setPendingEvent(false);
              }
            }}
          />
        ) : (
          <div className="subtle-note" data-testid="event-denied">
            Your role (<code>{role}</code>) cannot add workflow events. Switch
            to an admin or clinician identity to write.
          </div>
        )}
      </section>
    </div>
  );
}

function EventComposer({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (type: string, data: string) => void | Promise<void>;
}) {
  const [type, setType] = useState("");
  const [data, setData] = useState("");
  const disabled = !type.trim() || pending;
  return (
    <form
      className="event-form"
      data-testid="event-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (disabled) return;
        await onSubmit(type.trim(), data);
        setType("");
        setData("");
      }}
    >
      <select
        aria-label="Event type"
        data-testid="event-type"
        value={type}
        onChange={(e) => setType(e.target.value)}
        required
      >
        <option value="" disabled>Select event type…</option>
        {EVENT_TYPES.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <textarea
        data-testid="event-data"
        placeholder='event_data (optional JSON, e.g. {"comment":"..."})'
        value={data}
        onChange={(e) => setData(e.target.value)}
      />
      <div className="row">
        <button
          type="submit"
          className="btn btn--primary"
          disabled={disabled}
          data-testid="event-submit"
        >
          {pending ? "Appending…" : "Append event"}
        </button>
        <span className="subtle-note">
          JSON is parsed if valid; otherwise sent as a string.
        </span>
      </div>
    </form>
  );
}

function CreateEncounterModal({
  identity,
  me,
  onCancel,
  onSubmit,
}: {
  identity: string;
  me: Me;
  onCancel: () => void;
  onSubmit: (input: NewEncounterInput) => Promise<void>;
}) {
  const [patientId, setPatientId] = useState("");
  const [patientName, setPatientName] = useState("");
  const [provider, setProvider] = useState("");
  const [locationId, setLocationId] = useState<number | "">("");
  const [status, setStatus] =
    useState<"scheduled" | "in_progress">("scheduled");

  const [locations, setLocations] = useState<
    { id: number; organization_id: number; name: string }[]
  >([]);
  const [locLoading, setLocLoading] = useState(true);
  const [locError, setLocError] = useState<string | null>(null);

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLocLoading(true);
      setLocError(null);
      try {
        const rows = await listLocations(identity);
        setLocations(rows);
        if (rows.length === 1) setLocationId(rows[0].id);
      } catch (e) {
        setLocError(friendly(e));
      } finally {
        setLocLoading(false);
      }
    })();
  }, [identity]);

  const canSubmit =
    !pending &&
    patientId.trim() !== "" &&
    provider.trim() !== "" &&
    typeof locationId === "number";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setPending(true);
    setError(null);
    try {
      await onSubmit({
        organization_id: me.organization_id,
        location_id: locationId as number,
        patient_identifier: patientId.trim(),
        patient_name: patientName.trim() || null,
        provider_name: provider.trim(),
        status,
      });
      // parent closes the modal on success
    } catch (err) {
      setError(friendly(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-title"
      data-testid="create-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget && !pending) onCancel();
      }}
    >
      <div className="modal">
        <div className="modal__head">
          <h2 id="create-title">New encounter</h2>
          <button
            className="btn btn--muted"
            onClick={onCancel}
            disabled={pending}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <form className="modal__body event-form" onSubmit={submit}>
          <label>
            Patient ID *
            <input
              data-testid="create-patient-id"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              required
              placeholder="PT-1234"
            />
          </label>
          <label>
            Patient name
            <input
              data-testid="create-patient-name"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              placeholder="Jane Doe"
            />
          </label>
          <label>
            Provider *
            <input
              data-testid="create-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              required
              placeholder="Dr. Carter"
            />
          </label>
          <label>
            Location *
            {locLoading ? (
              <span className="subtle-note">loading locations…</span>
            ) : locError ? (
              <span style={{ color: "var(--danger)" }}>{locError}</span>
            ) : (
              <select
                data-testid="create-location"
                value={locationId === "" ? "" : String(locationId)}
                onChange={(e) =>
                  setLocationId(e.target.value ? parseInt(e.target.value, 10) : "")
                }
                required
              >
                <option value="">Select a location</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    #{l.id} · {l.name}
                  </option>
                ))}
              </select>
            )}
          </label>
          <label>
            Initial status
            <select
              data-testid="create-status"
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as "scheduled" | "in_progress")
              }
            >
              <option value="scheduled">scheduled</option>
              <option value="in_progress">in_progress</option>
            </select>
          </label>
          {error && (
            <div className="banner banner--error" role="alert" data-testid="create-error">
              {error}
            </div>
          )}
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn--muted"
              onClick={onCancel}
              disabled={pending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              data-testid="create-submit"
              disabled={!canSubmit}
            >
              {pending ? "Creating…" : "Create encounter"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------- pure helpers --------------------------------------------------

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function renderEventData(ev: WorkflowEvent): string {
  const d = ev.event_data;
  if (d == null) return "—";
  if (typeof d === "string") return d;
  if (typeof d === "object") {
    return Object.entries(d as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
      .join("  ·  ");
  }
  return String(d);
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

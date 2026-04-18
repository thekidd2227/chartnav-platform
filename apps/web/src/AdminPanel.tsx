import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  AuditFilters,
  Location,
  Me,
  Organization,
  Role,
  SecurityAuditEvent,
  User,
  createLocation,
  createUser,
  deactivateLocation,
  deactivateUser,
  getOrganization,
  listAuditEvents,
  listLocations,
  listUsers,
  updateLocation,
  updateOrganization,
  updateUser,
} from "./api";

type Tab = "users" | "locations" | "organization" | "audit";

export function AdminPanel({ identity, me, onClose }: {
  identity: string;
  me: Me;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("users");
  const [banner, setBanner] = useState<{ kind: "ok" | "error"; msg: string } | null>(null);

  const flash = (kind: "ok" | "error", msg: string) =>
    setBanner({ kind, msg });

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-title"
      data-testid="admin-panel"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal admin-modal">
        <div className="modal__head">
          <h2 id="admin-title">Org administration</h2>
          <button
            className="btn btn--muted"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="admin-tabs">
          <button
            className={"btn " + (tab === "users" ? "btn--primary" : "")}
            data-testid="admin-tab-users"
            onClick={() => setTab("users")}
          >
            Users
          </button>
          <button
            className={"btn " + (tab === "locations" ? "btn--primary" : "")}
            data-testid="admin-tab-locations"
            onClick={() => setTab("locations")}
          >
            Locations
          </button>
          <button
            className={"btn " + (tab === "organization" ? "btn--primary" : "")}
            data-testid="admin-tab-organization"
            onClick={() => setTab("organization")}
          >
            Organization
          </button>
          <button
            className={"btn " + (tab === "audit" ? "btn--primary" : "")}
            data-testid="admin-tab-audit"
            onClick={() => setTab("audit")}
          >
            Audit log
          </button>
        </div>
        {banner && (
          <div
            className={`banner banner--${banner.kind}`}
            role={banner.kind === "error" ? "alert" : "status"}
            data-testid={`admin-banner-${banner.kind}`}
          >
            {banner.msg}
          </div>
        )}
        <div className="modal__body">
          {tab === "users" && <UsersPane identity={identity} me={me} flash={flash} />}
          {tab === "locations" && <LocationsPane identity={identity} flash={flash} />}
          {tab === "organization" && <OrganizationPane identity={identity} flash={flash} />}
          {tab === "audit" && <AuditPane identity={identity} flash={flash} />}
        </div>
      </div>
    </div>
  );
}

// ---------- Users ---------------------------------------------------------

function UsersPane({
  identity,
  me,
  flash,
}: {
  identity: string;
  me: Me;
  flash: (kind: "ok" | "error", msg: string) => void;
}) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [creating, setCreating] = useState(false);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("clinician");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await listUsers(identity, { includeInactive }));
    } catch (e) {
      flash("error", friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, includeInactive, flash]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setCreating(true);
    try {
      await createUser(identity, {
        email: email.trim(),
        full_name: fullName.trim() || null,
        role,
      });
      setEmail("");
      setFullName("");
      setRole("clinician");
      flash("ok", `User ${email.trim()} created`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    } finally {
      setCreating(false);
    }
  };

  const onRoleChange = async (u: User, next: Role) => {
    try {
      await updateUser(identity, u.id, { role: next });
      flash("ok", `${u.email} role → ${next}`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    }
  };

  const onDeactivate = async (u: User) => {
    try {
      await deactivateUser(identity, u.id);
      flash("ok", `${u.email} deactivated`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    }
  };

  const onReactivate = async (u: User) => {
    try {
      await updateUser(identity, u.id, { is_active: true });
      flash("ok", `${u.email} reactivated`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    }
  };

  return (
    <div>
      <form className="event-form" data-testid="admin-user-form" onSubmit={onCreate}>
        <label>
          Email *
          <input
            type="email"
            data-testid="admin-user-email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="new@chartnav.local"
          />
        </label>
        <label>
          Full name
          <input
            data-testid="admin-user-name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Jane Doe"
          />
        </label>
        <label>
          Role *
          <select
            data-testid="admin-user-role"
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
          >
            <option value="admin">admin</option>
            <option value="clinician">clinician</option>
            <option value="reviewer">reviewer</option>
          </select>
        </label>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button
            type="submit"
            className="btn btn--primary"
            data-testid="admin-user-submit"
            disabled={creating || !email.trim()}
          >
            {creating ? "Creating…" : "Create user"}
          </button>
        </div>
      </form>

      <div className="admin-list-head">
        <h3>Users ({users.length})</h3>
        <label className="subtle-note">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />{" "}
          include inactive
        </label>
      </div>
      {loading ? (
        <div className="subtle-note">Loading…</div>
      ) : (
        <table className="admin-table" data-testid="admin-users-table">
          <thead>
            <tr><th>Email</th><th>Name</th><th>Role</th><th>Active</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} data-testid={`admin-user-row-${u.id}`}>
                <td>{u.email}</td>
                <td>{u.full_name ?? "—"}</td>
                <td>
                  <select
                    value={u.role}
                    disabled={u.id === me.user_id}
                    data-testid={`admin-user-role-${u.id}`}
                    onChange={(e) => onRoleChange(u, e.target.value as Role)}
                  >
                    <option value="admin">admin</option>
                    <option value="clinician">clinician</option>
                    <option value="reviewer">reviewer</option>
                  </select>
                </td>
                <td>{u.is_active ? "yes" : "no"}</td>
                <td data-testid={`admin-user-status-${u.id}`}>
                  {u.invited_at && u.is_active
                    ? <span title={`Invited ${u.invited_at}`} style={{ color: "var(--warn)" }}>Invited</span>
                    : (u.is_active ? "Active" : "Deactivated")}
                </td>
                <td>
                  {u.is_active ? (
                    <button
                      className="btn btn--muted"
                      onClick={() => onDeactivate(u)}
                      disabled={u.id === me.user_id}
                      data-testid={`admin-user-deactivate-${u.id}`}
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button className="btn" onClick={() => onReactivate(u)}>
                      Reactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---------- Organization --------------------------------------------------

function OrganizationPane({
  identity,
  flash,
}: {
  identity: string;
  flash: (kind: "ok" | "error", msg: string) => void;
}) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [settingsText, setSettingsText] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const o = await getOrganization(identity);
      setOrg(o);
      setName(o.name);
      setSettingsText(o.settings ? JSON.stringify(o.settings, null, 2) : "{}");
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!org) return;
    setSaving(true);
    try {
      let settings: Record<string, unknown> | null = null;
      const trimmed = settingsText.trim();
      if (trimmed) {
        try {
          const parsed = JSON.parse(trimmed);
          if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
            throw new Error("settings must be a JSON object");
          }
          settings = parsed as Record<string, unknown>;
        } catch (parseErr) {
          flash("error", `settings JSON: ${(parseErr as Error).message}`);
          setSaving(false);
          return;
        }
      } else {
        settings = null;
      }

      const patch: { name?: string; settings?: Record<string, unknown> | null } = {};
      if (name.trim() && name !== org.name) patch.name = name.trim();
      if (JSON.stringify(settings) !== JSON.stringify(org.settings || null)) {
        patch.settings = settings ?? {};
      }
      if (Object.keys(patch).length === 0) {
        flash("ok", "No changes");
        setSaving(false);
        return;
      }
      const updated = await updateOrganization(identity, patch);
      setOrg(updated);
      flash("ok", `Organization saved`);
    } catch (err) {
      flash("error", friendly(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="subtle-note">Loading…</div>;
  if (error) return <div className="banner banner--error" role="alert">{error}</div>;
  if (!org) return null;

  return (
    <form
      className="event-form"
      data-testid="admin-org-form"
      onSubmit={onSave}
    >
      <label>
        Slug (immutable)
        <input value={org.slug} readOnly disabled data-testid="admin-org-slug" />
      </label>
      <label>
        Name *
        <input
          data-testid="admin-org-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </label>
      <label>
        Settings (JSON object, ≤16 KB)
        <textarea
          data-testid="admin-org-settings"
          value={settingsText}
          onChange={(e) => setSettingsText(e.target.value)}
          style={{ minHeight: 160 }}
        />
      </label>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button
          type="submit"
          className="btn btn--primary"
          data-testid="admin-org-submit"
          disabled={saving}
        >
          {saving ? "Saving…" : "Save organization"}
        </button>
      </div>
    </form>
  );
}

// ---------- Audit log -----------------------------------------------------

function AuditPane({
  identity,
  flash,
}: {
  identity: string;
  flash: (kind: "ok" | "error", msg: string) => void;
}) {
  const [rows, setRows] = useState<SecurityAuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const PAGE_SIZE = 25;
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<AuditFilters>({});

  const filterKey = useMemo(() => JSON.stringify(filters), [filters]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { items, total } = await listAuditEvents(identity, filters, {
        limit: PAGE_SIZE,
        offset,
      });
      setRows(items);
      setTotal(total);
    } catch (e) {
      flash("error", friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, offset, filterKey, flash]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refresh();
  }, [refresh]);

  const update = (k: keyof AuditFilters, v: string) => {
    const next = { ...filters };
    if (v.trim()) (next as any)[k] = v.trim();
    else delete (next as any)[k];
    setFilters(next);
    setOffset(0);
  };

  return (
    <div>
      <div className="filters" data-testid="admin-audit-filters" style={{ position: "static", padding: 0 }}>
        <label>
          Event type
          <input
            data-testid="admin-audit-event-type"
            placeholder="cross_org_access_forbidden"
            value={filters.event_type ?? ""}
            onChange={(e) => update("event_type", e.target.value)}
          />
        </label>
        <label>
          Actor email
          <input
            data-testid="admin-audit-actor-email"
            placeholder="admin@chartnav.local"
            value={filters.actor_email ?? ""}
            onChange={(e) => update("actor_email", e.target.value)}
          />
        </label>
        <label>
          Path / detail contains
          <input
            data-testid="admin-audit-q"
            placeholder="/encounters"
            value={filters.q ?? ""}
            onChange={(e) => update("q", e.target.value)}
          />
        </label>
      </div>
      <div className="admin-list-head">
        <h3>
          Audit events ({total}
          {total > PAGE_SIZE ? `, showing ${offset + 1}-${Math.min(offset + PAGE_SIZE, total)}` : ""})
        </h3>
        <button className="btn" onClick={refresh} data-testid="admin-audit-refresh">
          Refresh
        </button>
      </div>
      {loading ? (
        <div className="subtle-note">Loading…</div>
      ) : (
        <table className="admin-table" data-testid="admin-audit-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Event</th>
              <th>Actor</th>
              <th>Path</th>
              <th>Error</th>
              <th>Request</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid={`admin-audit-row-${r.id}`}>
                <td>{fmtTs(r.created_at)}</td>
                <td><code>{r.event_type}</code></td>
                <td>{r.actor_email ?? "—"}</td>
                <td>
                  <code>{r.method ?? ""} {r.path ?? ""}</code>
                </td>
                <td>{r.error_code ?? "—"}</td>
                <td>
                  <code style={{ fontSize: 11 }}>
                    {r.request_id ? r.request_id.slice(0, 8) : "—"}
                  </code>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="subtle-note" style={{ padding: 16, textAlign: "center" }}>
                  No audit events match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {total > PAGE_SIZE && (
        <div className="pagination" data-testid="admin-audit-pagination" style={{ marginTop: 10 }}>
          <button
            className="btn"
            disabled={offset === 0}
            data-testid="admin-audit-prev"
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            ← Prev
          </button>
          <span className="subtle-note">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <button
            className="btn"
            disabled={offset + PAGE_SIZE >= total}
            data-testid="admin-audit-next"
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

function fmtTs(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

// ---------- Locations -----------------------------------------------------

function LocationsPane({
  identity,
  flash,
}: {
  identity: string;
  flash: (kind: "ok" | "error", msg: string) => void;
}) {
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setLocations(await listLocations(identity, { includeInactive }));
    } catch (e) {
      flash("error", friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity, includeInactive, flash]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createLocation(identity, name.trim());
      setName("");
      flash("ok", `Location created`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    } finally {
      setCreating(false);
    }
  };

  const onRename = async (l: Location, newName: string) => {
    try {
      await updateLocation(identity, l.id, { name: newName });
      flash("ok", `Location renamed`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    }
  };

  const onDeactivate = async (l: Location) => {
    try {
      await deactivateLocation(identity, l.id);
      flash("ok", `Location deactivated`);
      await refresh();
    } catch (e) {
      flash("error", friendly(e));
    }
  };

  return (
    <div>
      <form className="event-form" data-testid="admin-loc-form" onSubmit={onCreate}>
        <label>
          Name *
          <input
            data-testid="admin-loc-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Main Clinic"
          />
        </label>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button
            type="submit"
            className="btn btn--primary"
            data-testid="admin-loc-submit"
            disabled={creating || !name.trim()}
          >
            {creating ? "Creating…" : "Create location"}
          </button>
        </div>
      </form>

      <div className="admin-list-head">
        <h3>Locations ({locations.length})</h3>
        <label className="subtle-note">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />{" "}
          include inactive
        </label>
      </div>
      {loading ? (
        <div className="subtle-note">Loading…</div>
      ) : (
        <table className="admin-table" data-testid="admin-locations-table">
          <thead>
            <tr><th>ID</th><th>Name</th><th>Active</th><th></th></tr>
          </thead>
          <tbody>
            {locations.map((l) => (
              <tr key={l.id} data-testid={`admin-loc-row-${l.id}`}>
                <td>#{l.id}</td>
                <td>
                  <InlineEdit
                    initial={l.name}
                    onSave={(v) => onRename(l, v)}
                    testid={`admin-loc-name-${l.id}`}
                  />
                </td>
                <td>{l.is_active ? "yes" : "no"}</td>
                <td>
                  {l.is_active && (
                    <button
                      className="btn btn--muted"
                      onClick={() => onDeactivate(l)}
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function InlineEdit({
  initial,
  onSave,
  testid,
}: {
  initial: string;
  onSave: (v: string) => void;
  testid?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initial);
  useEffect(() => setValue(initial), [initial]);
  if (!editing)
    return (
      <span
        onClick={() => setEditing(true)}
        style={{ cursor: "pointer" }}
        data-testid={testid}
      >
        {initial}
      </span>
    );
  return (
    <span style={{ display: "inline-flex", gap: 6 }}>
      <input
        value={value}
        autoFocus
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim() && value !== initial) {
            onSave(value.trim());
            setEditing(false);
          }
          if (e.key === "Escape") {
            setValue(initial);
            setEditing(false);
          }
        }}
      />
      <button
        className="btn btn--primary"
        onClick={() => {
          if (value.trim() && value !== initial) onSave(value.trim());
          setEditing(false);
        }}
      >
        Save
      </button>
    </span>
  );
}

// ---------- helpers -------------------------------------------------------

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

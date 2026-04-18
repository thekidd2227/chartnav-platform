import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  Location,
  Me,
  Role,
  User,
  createLocation,
  createUser,
  deactivateLocation,
  deactivateUser,
  listLocations,
  listUsers,
  updateLocation,
  updateUser,
} from "./api";

type Tab = "users" | "locations";

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
          {tab === "users" ? (
            <UsersPane identity={identity} me={me} flash={flash} />
          ) : (
            <LocationsPane identity={identity} flash={flash} />
          )}
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
            <tr><th>Email</th><th>Name</th><th>Role</th><th>Active</th><th></th></tr>
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

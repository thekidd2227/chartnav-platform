import { useState } from "react";
import { acceptInvite, ApiError } from "./api";

/**
 * Minimal invite-accept screen.
 *
 * Hit via `/invite?invite=<token>` or any URL ending in `/accept`.
 * No auth required — the token IS the credential. Success stores the
 * caller's email in localStorage so the main app can use it in header
 * auth mode immediately after acceptance.
 */
export function InviteAccept({ defaultToken = "" }: { defaultToken?: string }) {
  const [token, setToken] = useState(defaultToken);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<null | {
    email: string;
    organization_id: number;
    role: string;
  }>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;
    setPending(true);
    setError(null);
    try {
      const res = await acceptInvite(token.trim());
      setResult({
        email: res.email,
        organization_id: res.organization_id,
        role: res.role,
      });
      try {
        localStorage.setItem("chartnav.devIdentity", res.email);
      } catch {
        // localStorage may be unavailable; not fatal for accept flow
      }
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`${e.status} ${e.errorCode} — ${e.reason}`);
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setPending(false);
    }
  };

  return (
    <main style={{ maxWidth: 520, margin: "80px auto", padding: "0 20px", fontFamily: "-apple-system, sans-serif" }}>
      <h1 style={{ marginBottom: 4 }}>
        <span style={{ color: "#0F172A" }}>Chart</span>
        <span style={{ color: "#0B6E79" }}>Nav</span>{" "}
        <span style={{ fontSize: 14, color: "#475569" }}>· accept invitation</span>
      </h1>
      <p className="subtle-note" style={{ color: "#475569" }}>
        Paste the invitation token you received from your admin.
      </p>
      {result ? (
        <div className="banner banner--ok" role="status" data-testid="invite-accepted">
          Welcome, <strong>{result.email}</strong> — your account is active
          in organization #{result.organization_id} with role{" "}
          <code>{result.role}</code>. You can close this tab and return to the
          main app.
        </div>
      ) : (
        <form onSubmit={submit} style={{ display: "grid", gap: 10, marginTop: 16 }}>
          <label style={{ fontSize: 12, color: "#475569" }}>
            Invitation token
            <textarea
              data-testid="invite-token-input"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              style={{ width: "100%", minHeight: 72, fontFamily: "ui-monospace, monospace", padding: 8 }}
              required
            />
          </label>
          {error && (
            <div className="banner banner--error" role="alert" data-testid="invite-error">
              {error}
            </div>
          )}
          <button
            type="submit"
            className="btn btn--primary"
            data-testid="invite-submit"
            disabled={pending || !token.trim()}
            style={{ justifySelf: "start" }}
          >
            {pending ? "Accepting…" : "Accept invitation"}
          </button>
        </form>
      )}
    </main>
  );
}

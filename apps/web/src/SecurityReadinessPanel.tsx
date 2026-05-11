// Phase 23 — Security Readiness panel.
//
// Admin-only readiness checklist. Renders metadata-only status
// labels from /admin/security/readiness. Explicitly does NOT
// claim HIPAA compliance or certification. Labels are
// informational — passing every "configured" does not approve
// ChartNav for real PHI.

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  Me,
  SecurityReadinessLabel,
  SecurityReadinessSummary,
  getSecurityReadiness,
  isAdmin,
} from "./api";

interface Props {
  identity: string;
  me: Me;
}

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

const CHECKS: Array<{ key: keyof SecurityReadinessSummary; label: string; description: string }> = [
  {
    key: "auth_mode",
    label: "Production auth mode",
    description: "CHARTNAV_AUTH_MODE=bearer required for real PHI; header mode is dev-only.",
  },
  {
    key: "database_kind",
    label: "Database backend",
    description: "Postgres required for real PHI; SQLite is dev/CI only.",
  },
  {
    key: "jwt_issuer_configured",
    label: "JWT issuer (OIDC)",
    description: "CHARTNAV_JWT_ISSUER must point at the practice's identity provider.",
  },
  {
    key: "jwt_audience_configured",
    label: "JWT audience",
    description: "CHARTNAV_JWT_AUDIENCE must be set.",
  },
  {
    key: "jwt_jwks_url_configured",
    label: "JWKS URL",
    description: "CHARTNAV_JWT_JWKS_URL must be set for signature validation.",
  },
  {
    key: "cors_explicit_configured",
    label: "CORS allow-origins",
    description: "CHARTNAV_CORS_ALLOW_ORIGINS must list the practice's origins (no wildcard).",
  },
  {
    key: "audit_retention_configured",
    label: "Audit retention",
    description: "CHARTNAV_AUDIT_RETENTION_DAYS must match the practice's agreed retention.",
  },
  {
    key: "stt_provider",
    label: "STT provider",
    description: "Default is disabled. Enabling OpenAI Whisper requires practice approval + BAA.",
  },
  {
    key: "backup_config_documented",
    label: "Backup configuration",
    description: "External_required — documented in chartnav-backup-disaster-recovery-policy.md and verified at hosting layer.",
  },
  {
    key: "logging_config_documented",
    label: "Logging configuration",
    description: "External_required — log forwarding configured at hosting layer.",
  },
  {
    key: "monitoring_config_documented",
    label: "Monitoring configuration",
    description: "External_required — alerting configured at hosting layer.",
  },
  {
    key: "incident_contacts_documented",
    label: "Incident contacts",
    description: "External_required — practice security owner contact captured during Gate 8.",
  },
  {
    key: "baa_status_configured",
    label: "BAA execution status",
    description: "External_required — see chartnav-baa-vendor-readiness-checklist.md.",
  },
  {
    key: "vendor_review_status_configured",
    label: "Vendor / subprocessor review",
    description: "External_required — see chartnav-subprocessor-inventory.md.",
  },
  {
    key: "real_phi_go_live_gate_status",
    label: "Real-PHI go-live gate",
    description: "External_required — every gate in chartnav-real-phi-go-live-gate.md must close before real PHI starts.",
  },
];

function labelTone(label: SecurityReadinessLabel): string {
  switch (label) {
    case "configured":
      return "ok";
    case "disabled":
      return "ok";
    case "external_required":
      return "warn";
    case "required":
      return "warn";
    case "missing":
      return "fail";
  }
}

export function SecurityReadinessPanel({ identity, me }: Props) {
  const canRead = isAdmin(me.role);

  if (!canRead) {
    return (
      <section
        className="security-readiness security-readiness--blocked"
        data-testid="security-readiness-blocked"
        aria-label="Security readiness checklist"
      >
        <h2 className="security-readiness__title">Security Readiness</h2>
        <p className="security-readiness__empty">
          Admin role required to view the readiness checklist.
        </p>
      </section>
    );
  }

  return <SecurityReadinessForAdmin identity={identity} />;
}

function SecurityReadinessForAdmin({ identity }: { identity: string }) {
  const [data, setData] = useState<SecurityReadinessSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getSecurityReadiness(identity));
    } catch (e) {
      setError(friendly(e));
    } finally {
      setLoading(false);
    }
  }, [identity]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section
      className="security-readiness"
      data-testid="security-readiness"
      aria-label="Security readiness checklist"
    >
      <header className="security-readiness__header">
        <div>
          <h2 className="security-readiness__title">
            Security Readiness — Real-PHI Go-Live Checklist
          </h2>
          <p className="security-readiness__subtitle subtle-note">
            Metadata-only environment shape. Status labels reflect
            the runtime configuration; passing every check does
            <strong> not</strong> make ChartNav HIPAA-certified or
            approved for real PHI by default. The full gate lives in
            <code> docs/security/chartnav-real-phi-go-live-gate.md</code>.
          </p>
        </div>
        <button
          type="button"
          className="btn"
          data-testid="security-readiness-refresh"
          onClick={() => void refresh()}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="security-readiness-error"
        >
          {error}
        </div>
      )}

      {!data && loading && (
        <p
          className="security-readiness__empty"
          data-testid="security-readiness-loading"
        >
          Loading readiness summary…
        </p>
      )}

      {data && (
        <>
          <ul
            className="security-readiness__list"
            data-testid="security-readiness-list"
          >
            {CHECKS.map((c) => {
              const value = data[c.key] as SecurityReadinessLabel;
              const tone = labelTone(value);
              return (
                <li
                  key={c.key}
                  className={`security-readiness__row security-readiness__row--${tone}`}
                  data-testid={`readiness-row-${c.key}`}
                >
                  <div className="security-readiness__row-label">
                    {c.label}
                  </div>
                  <div className="security-readiness__row-status">
                    <span
                      className={`security-readiness__pill security-readiness__pill--${tone}`}
                    >
                      {value.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="security-readiness__row-description subtle-note">
                    {c.description}
                  </div>
                </li>
              );
            })}
          </ul>

          <p
            className="security-readiness__disclaimer subtle-note"
            data-testid="security-readiness-disclaimer"
          >
            {data.compliance_attestation}
          </p>
        </>
      )}
    </section>
  );
}

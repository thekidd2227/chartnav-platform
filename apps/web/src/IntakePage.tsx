// Phase 2 item 3 — Public unauthenticated patient intake form.
//
// Spec: docs/chartnav/closure/PHASE_B_Digital_Intake.md
//
// Renders at /intake/{token} with NO app shell, NO auth header. The
// form is server-driven (we render the schema returned by
// GET /intakes/{token}). PHI is never displayed back from the
// response — we render the operator-supplied label set only.
import { useEffect, useState } from "react";
import {
  ApiError,
  IntakeFormSchemaField,
  IntakePublicView,
  getIntakeForm,
  submitIntake,
} from "./api";

export interface IntakePageProps {
  token: string;
}

type FieldValue = string | string[] | boolean;

function defaultValue(field: IntakeFormSchemaField): FieldValue {
  if (field.type === "checkbox") return false;
  if (field.type === "list-textarea") return [];
  return "";
}

export function IntakePage({ token }: IntakePageProps) {
  const [view, setView] = useState<IntakePublicView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, FieldValue>>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getIntakeForm(token)
      .then((v) => {
        if (cancelled) return;
        setView(v);
        const init: Record<string, FieldValue> = {};
        for (const f of v.form_schema.fields) init[f.name] = defaultValue(f);
        setValues(init);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError) {
          setError(e.reason || "intake unavailable");
          setErrorCode(e.errorCode);
        } else {
          setError("Could not load the intake form. The link may have expired.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error) {
    return (
      <div className="intake-page" data-testid="intake-error">
        <h1>Intake unavailable</h1>
        <p>{error}</p>
        {errorCode && <p data-testid="intake-error-code">{errorCode}</p>}
        <p>
          Please contact your clinic if you believe this is a mistake.
        </p>
      </div>
    );
  }
  if (!view) {
    return <div className="intake-page">Loading…</div>;
  }
  if (submitted) {
    return (
      <div className="intake-page" data-testid="intake-submitted">
        <h1>Thank you</h1>
        <p>
          Your intake form has been received. Our front-desk staff
          will confirm the details with you when you arrive.
        </p>
      </div>
    );
  }

  function setField(name: string, v: FieldValue) {
    setValues((prev) => ({ ...prev, [name]: v }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await submitIntake(token, values as Record<string, unknown>);
      setSubmitted(true);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.reason);
        setErrorCode(err.errorCode);
      } else {
        setError("Could not submit the form. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="intake-page" data-testid="intake-page">
      <header>
        <h1>{view.organization_branding.name} — Intake</h1>
        <p className="intake-page__advisory">{view.advisory}</p>
      </header>
      <form onSubmit={onSubmit} data-testid="intake-form">
        {view.form_schema.fields.map((f) => (
          <div className="intake-page__field" key={f.name}>
            <label>
              {f.label}
              {f.required ? " *" : ""}
            </label>
            {f.type === "checkbox" ? (
              <input
                type="checkbox"
                checked={Boolean(values[f.name])}
                onChange={(e) => setField(f.name, e.target.checked)}
                required={f.required}
                data-testid={f.name === "consent" ? "intake-consent-checkbox" : undefined}
              />
            ) : f.type === "textarea" ? (
              <textarea
                value={String(values[f.name] || "")}
                maxLength={f.max_length}
                onChange={(e) => setField(f.name, e.target.value)}
                required={f.required}
              />
            ) : f.type === "list-textarea" ? (
              <textarea
                value={
                  Array.isArray(values[f.name])
                    ? (values[f.name] as string[]).join("\n")
                    : String(values[f.name] || "")
                }
                placeholder="One per line"
                onChange={(e) =>
                  setField(
                    f.name,
                    e.target.value
                      .split("\n")
                      .map((s) => s.trim())
                      .filter(Boolean)
                  )
                }
              />
            ) : (
              <input
                type={f.type === "date" ? "date" : "text"}
                value={String(values[f.name] || "")}
                maxLength={f.max_length}
                onChange={(e) => setField(f.name, e.target.value)}
                required={f.required}
              />
            )}
          </div>
        ))}
        <button
          type="submit"
          disabled={submitting}
          data-testid="intake-submit"
        >
          {submitting ? "Submitting…" : "Submit"}
        </button>
        {error && (
          <div role="alert" data-testid="intake-form-error">
            {error}
          </div>
        )}
      </form>
    </div>
  );
}

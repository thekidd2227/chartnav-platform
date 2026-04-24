// Phase 38 — B5 — printable encounter slip.
//
// Renders a single-page slip the front desk hands to the provider.
// Uses @media print styles from styles.css to hide chrome. No PHI
// in audit logs — slip content is locally rendered from data the
// caller already has.

import { Encounter, Location } from "./api";
import { patientDisplayName, patientMrnSecondary } from "./labels";

interface Props {
  encounter: Encounter;
  location: Location | null;
  onClose: () => void;
}

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function EncounterSlip({ encounter, location, onClose }: Props) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" data-testid="encounter-slip-modal">
      <div className="modal" style={{ maxWidth: 740 }}>
        <div className="modal__head">
          <h2>Encounter slip</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn--primary"
              onClick={() => window.print()}
              data-testid="slip-print"
            >
              Print
            </button>
            <button
              className="btn btn--muted"
              onClick={onClose}
              data-testid="slip-close"
            >
              ✕
            </button>
          </div>
        </div>
        <div className="modal__body">
          <div className="slip" data-testid="encounter-slip">
            <div className="slip__head">
              <div>
                <h2>{patientDisplayName(encounter)}</h2>
                <div className="subtle-note">
                  {patientMrnSecondary(encounter) || `Encounter #${encounter.id}`}
                </div>
              </div>
              <div className="subtle-note" style={{ textAlign: "right" }}>
                Printed {new Date().toLocaleString()}
              </div>
            </div>
            <dl>
              <div className="slip__row">
                <dt>Provider</dt>
                <dd>{encounter.provider_name}</dd>
              </div>
              <div className="slip__row">
                <dt>Location</dt>
                <dd>{location ? location.name : `#${encounter.location_id ?? "—"}`}</dd>
              </div>
              <div className="slip__row">
                <dt>Scheduled</dt>
                <dd>{fmt(encounter.scheduled_at)}</dd>
              </div>
              <div className="slip__row">
                <dt>Checked in</dt>
                <dd>{fmt(encounter.started_at)}</dd>
              </div>
              <div className="slip__row">
                <dt>Status</dt>
                <dd>{encounter.status.replace(/_/g, " ")}</dd>
              </div>
              <div className="slip__row">
                <dt>Source</dt>
                <dd>{encounter._source ?? "chartnav"}</dd>
              </div>
              <div className="slip__row">
                <dt>Today's notes</dt>
                <dd style={{ minHeight: "3em" }}>&nbsp;</dd>
              </div>
              <div className="slip__row">
                <dt>Allergies</dt>
                <dd style={{ minHeight: "2em" }}>&nbsp;</dd>
              </div>
              <div className="slip__row">
                <dt>Signature</dt>
                <dd style={{ minHeight: "2em" }}>&nbsp;</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

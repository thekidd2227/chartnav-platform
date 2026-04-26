// Phase A item 5 — MRN input.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.2.
//
// MRN: `autocapitalize="off"`, `autocorrect="off"`, `spellcheck="false"`.
// MRNs are case-sensitive identifiers from the practice's PM/EHR; we
// must never auto-uppercase or auto-correct them. iPad Safari is the
// primary target.
import { ChangeEvent } from "react";

export interface MrnInputProps {
  value: string;
  onChange: (next: string) => void;
  id?: string;
  name?: string;
  placeholder?: string;
  ariaLabel?: string;
  disabled?: boolean;
  testId?: string;
}

export function MrnInput(props: MrnInputProps) {
  const {
    value,
    onChange,
    id,
    name,
    placeholder = "MRN",
    ariaLabel = "Medical record number",
    disabled,
    testId = "mrn-input",
  } = props;

  const handle = (e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value);

  return (
    <input
      type="text"
      inputMode="text"
      id={id}
      name={name}
      value={value}
      onChange={handle}
      placeholder={placeholder}
      aria-label={ariaLabel}
      disabled={disabled}
      autoComplete="off"
      autoCapitalize="off"
      autoCorrect="off"
      spellCheck={false}
      data-testid={testId}
      data-tablet-input="true"
      className="tablet-input"
    />
  );
}

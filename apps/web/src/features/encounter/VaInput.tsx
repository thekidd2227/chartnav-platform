// Phase A item 5 — Visual acuity input.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.2.
//
// VA: `autocomplete="off"`, no auto-capitalize, slash form supported
// (e.g. "20/40", "20/25-2"). Numeric+symbol keypad via
// `inputmode="text"` (slash-separator forms break a strict numeric
// keypad on iOS Safari). Spell-check off so "OS" / "OD" notation is
// not flagged.
import { ChangeEvent } from "react";

export interface VaInputProps {
  value: string;
  onChange: (next: string) => void;
  id?: string;
  name?: string;
  placeholder?: string;
  ariaLabel?: string;
  disabled?: boolean;
  testId?: string;
}

export function VaInput(props: VaInputProps) {
  const {
    value,
    onChange,
    id,
    name,
    placeholder = "20/40",
    ariaLabel = "Visual acuity (Snellen)",
    disabled,
    testId = "va-input",
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

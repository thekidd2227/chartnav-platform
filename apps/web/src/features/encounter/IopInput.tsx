// Phase A item 5 — IOP input.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.2.
//
// IOP fields: `inputmode="decimal"` so iPad Safari surfaces the numeric
// keypad by default. Slash separator between OD and OS values is
// preserved verbatim (we do not auto-format — clinicians type
// "16/14" and we keep it). The mm-Hg suffix is a visual hint only.
//
// What this component is NOT:
//   - It is not a unit converter.
//   - It does not validate ranges (clinicians frequently log
//     post-op IOP that would look out-of-range to a generic schema).
//   - It does not autocorrect, autocapitalize, or spellcheck.
import { ChangeEvent } from "react";

export interface IopInputProps {
  value: string;
  onChange: (next: string) => void;
  id?: string;
  name?: string;
  placeholder?: string;
  ariaLabel?: string;
  disabled?: boolean;
  testId?: string;
}

export function IopInput(props: IopInputProps) {
  const {
    value,
    onChange,
    id,
    name,
    placeholder = "OD/OS, e.g. 16/14",
    ariaLabel = "Intraocular pressure (mm Hg)",
    disabled,
    testId = "iop-input",
  } = props;

  const handle = (e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value);

  return (
    <span className="iop-input-wrap">
      <input
        type="text"
        inputMode="decimal"
        id={id}
        name={name}
        value={value}
        onChange={handle}
        placeholder={placeholder}
        aria-label={ariaLabel}
        disabled={disabled}
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        data-testid={testId}
        data-tablet-input="true"
        className="tablet-input"
      />
      <span className="iop-input-suffix" aria-hidden="true">
        mm Hg
      </span>
    </span>
  );
}

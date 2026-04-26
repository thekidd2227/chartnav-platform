// Phase A item 5 — vitest coverage for the specialized tablet inputs.
// Verifies the input attributes the spec calls for in §3.2.
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IopInput } from "../features/encounter/IopInput";
import { VaInput } from "../features/encounter/VaInput";
import { MrnInput } from "../features/encounter/MrnInput";

describe("IopInput", () => {
  it("renders with inputmode=decimal and the mm Hg suffix", () => {
    render(<IopInput value="" onChange={() => {}} />);
    const input = screen.getByTestId("iop-input") as HTMLInputElement;
    expect(input.inputMode).toBe("decimal");
    expect(input.getAttribute("autocapitalize")).toBe("off");
    expect(input.getAttribute("autocorrect")).toBe("off");
    expect(input.getAttribute("spellcheck")).toBe("false");
    expect(screen.getByText(/mm Hg/i)).toBeInTheDocument();
  });

  it("preserves the slash separator the clinician types", () => {
    const onChange = vi.fn();
    render(<IopInput value="" onChange={onChange} />);
    const input = screen.getByTestId("iop-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "16/14" } });
    expect(onChange).toHaveBeenCalledWith("16/14");
  });
});

describe("VaInput", () => {
  it("disables autocomplete and autocapitalize", () => {
    render(<VaInput value="" onChange={() => {}} />);
    const input = screen.getByTestId("va-input") as HTMLInputElement;
    expect(input.getAttribute("autocomplete")).toBe("off");
    expect(input.getAttribute("autocapitalize")).toBe("off");
    expect(input.getAttribute("spellcheck")).toBe("false");
  });

  it("accepts the slash form (20/25-2)", () => {
    const onChange = vi.fn();
    render(<VaInput value="" onChange={onChange} />);
    const input = screen.getByTestId("va-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "20/25-2" } });
    expect(onChange).toHaveBeenCalledWith("20/25-2");
  });
});

describe("MrnInput", () => {
  it("turns off autocapitalize, autocorrect, and spellcheck", () => {
    render(<MrnInput value="" onChange={() => {}} />);
    const input = screen.getByTestId("mrn-input") as HTMLInputElement;
    expect(input.getAttribute("autocapitalize")).toBe("off");
    expect(input.getAttribute("autocorrect")).toBe("off");
    expect(input.getAttribute("spellcheck")).toBe("false");
  });
});

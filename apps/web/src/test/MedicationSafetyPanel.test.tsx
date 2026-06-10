// Phase 85 — Medication Safety Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/medications/medicationsApi", () => ({
  getMedications: vi.fn(),
  postMedication: vi.fn(),
  postRefill: vi.fn(),
  postAllergy: vi.fn(),
  patchMedicationDiscontinue: vi.fn(),
}));

import {
  getMedications,
  patchMedicationDiscontinue,
  postAllergy,
  postMedication,
  postRefill,
} from "../features/medications/medicationsApi";
import { MedicationSafetyPanel } from "../features/medications/MedicationSafetyPanel";
import type {
  MedicationRecord,
  MedicationsPanelResponse,
} from "../features/medications/medicationsTypes";

const SUPPORTED_CLASSES = [
  { code: "pgf2_analog" as const, label: "Prostaglandin F2α analog" },
  { code: "beta_blocker" as const, label: "Beta blocker" },
  { code: "alpha_agonist" as const, label: "Alpha agonist" },
  {
    code: "carbonic_anhydrase_inhibitor" as const,
    label: "Carbonic anhydrase inhibitor",
  },
  { code: "rho_kinase_inhibitor" as const, label: "Rho-kinase inhibitor" },
  { code: "combination_drop" as const, label: "Combination drop" },
  { code: "steroid_drop" as const, label: "Steroid drop" },
  { code: "nsaid_drop" as const, label: "NSAID drop" },
  { code: "antibiotic_drop" as const, label: "Antibiotic drop" },
  {
    code: "anti_vegf_intravitreal" as const,
    label: "Anti-VEGF intravitreal",
  },
  { code: "lubricant" as const, label: "Lubricant" },
  { code: "oral_systemic_other" as const, label: "Oral / systemic — other" },
];

const REACTION_TYPES = [
  { code: "rash" as const, label: "Rash" },
  { code: "swelling" as const, label: "Swelling" },
  { code: "anaphylaxis" as const, label: "Anaphylaxis" },
  { code: "gi_distress" as const, label: "GI distress" },
  { code: "respiratory" as const, label: "Respiratory" },
  { code: "other" as const, label: "Other" },
];

const DISCLOSURE =
  "Provider-entered medication safety surface. ChartNav does not " +
  "prescribe, does not refill, does not dose, does not contact the " +
  "pharmacy, does not recommend medication changes, and does not " +
  "perform autonomous drug-interaction checking.";

function medRecord(over: Partial<MedicationRecord> = {}): MedicationRecord {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: 1,
    medication_name: "Latanoprost 0.005% drops",
    medication_class: "pgf2_analog",
    medication_class_label: "Prostaglandin F2α analog",
    route: "drops",
    laterality: "OU",
    dose_per_day: 1,
    preservative_flag: true,
    started_on: null,
    discontinued_on: null,
    prescriber_user_id: null,
    prescriber_display_name: null,
    recorded_by_user_id: 5,
    recorded_by_display_name: "Casey Clinician",
    recorded_by_role: "clinician",
    recorded_at: "2026-06-10T10:00:00Z",
    created_at: "2026-06-10T10:00:00Z",
    updated_at: "2026-06-10T10:00:00Z",
    is_active: true,
    refill_count: 0,
    refill_gap: {
      has_history: false,
      last_refill_date: null,
      expected_days_supply: null,
      supply_through: null,
      gap_days: null,
      status: "no_history",
    },
    ...over,
  };
}

function emptyResponse(): MedicationsPanelResponse {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-10T10:00:00Z",
    demo_mode: true,
    medications: [],
    refills: [],
    allergies: [],
    supported_medication_classes: SUPPORTED_CLASSES,
    supported_routes: ["drops", "intravitreal", "oral"],
    supported_lateralities: ["NA", "OD", "OS", "OU"],
    supported_reaction_types: REACTION_TYPES,
    supported_severities: ["mild", "moderate", "severe"],
    signals: {
      polypharmacy_count: 0,
      preservative_burden: 0,
      refill_gaps: [],
      allergy_matches: [],
      insufficient_data: true,
    },
    disclosure: DISCLOSURE,
  };
}

function populatedResponse(): MedicationsPanelResponse {
  const onTrack = medRecord({
    id: 1,
    medication_name: "Latanoprost 0.005% drops",
    refill_count: 1,
    refill_gap: {
      has_history: true,
      last_refill_date: "2026-06-05",
      expected_days_supply: 30,
      supply_through: "2026-07-05",
      gap_days: 0,
      status: "on_track",
    },
  });
  const gap = medRecord({
    id: 2,
    medication_name: "Timolol 0.5% drops",
    medication_class: "beta_blocker",
    medication_class_label: "Beta blocker",
    dose_per_day: 2,
    refill_count: 1,
    refill_gap: {
      has_history: true,
      last_refill_date: "2026-03-01",
      expected_days_supply: 30,
      supply_through: "2026-03-31",
      gap_days: 71,
      status: "gap",
    },
  });
  return {
    ...emptyResponse(),
    medications: [onTrack, gap],
    refills: [],
    allergies: [
      {
        id: 1,
        organization_id: 1,
        patient_id: 1,
        substance: "Penicillin",
        reaction_type: "rash",
        reaction_type_label: "Rash",
        severity: "moderate",
        recorded_by_user_id: 5,
        recorded_at: "2026-06-10T10:00:00Z",
        created_at: "2026-06-10T10:00:00Z",
        updated_at: "2026-06-10T10:00:00Z",
      },
    ],
    signals: {
      polypharmacy_count: 2,
      preservative_burden: 3,
      refill_gaps: [
        {
          medication_id: 2,
          medication_name: "Timolol 0.5% drops",
          gap_days: 71,
          last_refill_date: "2026-03-01",
          supply_through: "2026-03-31",
        },
      ],
      allergy_matches: [],
      insufficient_data: false,
    },
  };
}

function allergyMatchResponse(): MedicationsPanelResponse {
  const base = populatedResponse();
  base.signals.allergy_matches = [
    {
      medication_id: 1,
      medication_name: "Latanoprost 0.005% drops",
      allergy_id: 1,
      allergy_substance: "latanoprost",
      allergy_severity: "severe",
    },
  ];
  return base;
}

beforeEach(() => {
  vi.mocked(getMedications).mockReset();
  vi.mocked(postMedication).mockReset();
  vi.mocked(postRefill).mockReset();
  vi.mocked(postAllergy).mockReset();
  vi.mocked(patchMedicationDiscontinue).mockReset();
});

describe("MedicationSafetyPanel — base render", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(emptyResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-panel"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("medication-banner").textContent).toMatch(
      /Provider-entered medication safety surface/i,
    );
    expect(screen.getByTestId("medication-banner").textContent).toMatch(
      /does not prescribe/i,
    );
    expect(screen.getByTestId("medication-banner").textContent).toMatch(
      /does not refill/i,
    );
    expect(screen.getByTestId("medication-banner").textContent).toMatch(
      /does not contact the pharmacy/i,
    );
    expect(
      screen.getByTestId("medication-refresh-btn"),
    ).toBeInTheDocument();
  });

  it("renders signal counters", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-signals")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-signal-polypharmacy").textContent,
    ).toMatch(/Active meds:\s*2/);
    expect(
      screen.getByTestId("medication-signal-preservative").textContent,
    ).toMatch(/Preservative burden:\s*3/);
    expect(
      screen.getByTestId("medication-signal-refill-gaps").textContent,
    ).toMatch(/Refill gaps:\s*1/);
    expect(
      screen.getByTestId("medication-signal-allergies").textContent,
    ).toMatch(/Allergies on file:\s*1/);
  });
});

describe("MedicationSafetyPanel — empty state", () => {
  it("shows empty callout and never-blocks-signing copy", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(emptyResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("medication-empty").textContent).toMatch(
      /never blocks signing/i,
    );
  });
});

describe("MedicationSafetyPanel — populated rendering", () => {
  it("renders on-track and gap medication rows with the right pill tone", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-row-1")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-refill-gap-1").textContent,
    ).toMatch(/On track/i);
    expect(
      screen.getByTestId("medication-refill-gap-2").textContent,
    ).toMatch(/Refill gap · 71d/);
    expect(screen.getByTestId("medication-class-2").textContent).toBe(
      "Beta blocker",
    );
    expect(screen.getByTestId("medication-dose-2").textContent).toBe("2");
    expect(screen.getByTestId("medication-actor-1").textContent).toMatch(
      /Casey Clinician/,
    );
  });

  it("renders allergy-match callout when matches present", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(allergyMatchResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-allergy-match-callout"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-allergy-match-0").textContent,
    ).toMatch(/Latanoprost/);
    expect(
      screen.getByTestId("medication-allergy-match-callout").textContent,
    ).toMatch(/literal name\/class match only/i);
  });
});

describe("MedicationSafetyPanel — form interactions", () => {
  it("POSTs medication payload and refetches on success", async () => {
    vi.mocked(getMedications)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postMedication).mockResolvedValueOnce(medRecord());

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-empty")).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("medication-name-input"),
      "Latanoprost 0.005% drops",
    );
    await userEvent.click(screen.getByTestId("medication-submit-btn"));

    await waitFor(() => expect(postMedication).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postMedication).mock.calls[0]![0]).toBe(1);
    const payload = vi.mocked(postMedication).mock.calls[0]![1];
    expect(payload.medication_name).toBe("Latanoprost 0.005% drops");
    expect(payload.medication_class).toBe("pgf2_analog");
    expect(payload.route).toBe("drops");
    expect(getMedications).toHaveBeenCalledTimes(2);
  });

  it("POSTs refill payload and refetches on success", async () => {
    vi.mocked(getMedications)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postRefill).mockResolvedValueOnce({
      id: 1,
      organization_id: 1,
      patient_id: 1,
      medication_id: 1,
      encounter_id: 1,
      refill_date: "2026-06-10",
      expected_days_supply: 30,
      recorded_by_user_id: 5,
      recorded_at: "2026-06-10T10:00:00Z",
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("refill-form")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("refill-submit-btn"));

    await waitFor(() => expect(postRefill).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postRefill).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(postRefill).mock.calls[0]![1].expected_days_supply).toBe(
      30,
    );
  });

  it("POSTs allergy payload and refetches on success", async () => {
    vi.mocked(getMedications)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postAllergy).mockResolvedValueOnce({
      id: 1,
      organization_id: 1,
      patient_id: 1,
      substance: "Penicillin",
      reaction_type: "rash",
      reaction_type_label: "Rash",
      severity: "moderate",
      recorded_by_user_id: 5,
      recorded_at: "2026-06-10T10:00:00Z",
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("allergy-form")).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("allergy-substance-input"),
      "Penicillin",
    );
    await userEvent.click(screen.getByTestId("allergy-submit-btn"));

    await waitFor(() => expect(postAllergy).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postAllergy).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(postAllergy).mock.calls[0]![1].substance).toBe(
      "Penicillin",
    );
  });

  it("PATCHes discontinue and refetches", async () => {
    vi.mocked(getMedications)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(patchMedicationDiscontinue).mockResolvedValueOnce(
      medRecord({ is_active: false, discontinued_on: "2026-06-10" }),
    );

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-discontinue-1"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("medication-discontinue-1"));

    await waitFor(() =>
      expect(patchMedicationDiscontinue).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(patchMedicationDiscontinue).mock.calls[0]![0]).toBe(1);
  });

  it("surfaces submit errors in inline banner", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(emptyResponse());
    vi.mocked(postMedication).mockRejectedValueOnce(
      new Error("invalid_medication_class"),
    );

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-submit-btn"),
      ).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("medication-name-input"),
      "Latanoprost",
    );
    await userEvent.click(screen.getByTestId("medication-submit-btn"));

    await waitFor(() =>
      expect(
        screen.getByTestId("medication-submit-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-submit-error").textContent,
    ).toMatch(/invalid_medication_class/);
  });
});

describe("MedicationSafetyPanel — interaction + safety", () => {
  it("refresh button refetches the panel", async () => {
    vi.mocked(getMedications)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-empty")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("medication-refresh-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("medication-row-1")).toBeInTheDocument(),
    );
    expect(getMedications).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getMedications).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("medication-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("renders disclosure with explicit boundary language", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("medication-disclosure");
    expect(d.textContent).toMatch(/does not prescribe/i);
    expect(d.textContent).toMatch(/does not refill/i);
    expect(d.textContent).toMatch(/does not dose/i);
    expect(d.textContent).toMatch(/does not contact the pharmacy/i);
    expect(d.textContent).toMatch(/does not recommend medication changes/i);
  });

  it("does NOT render forbidden autonomous-medicine phrases", async () => {
    vi.mocked(getMedications).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-row-1")).toBeInTheDocument(),
    );
    const disclosure = (
      screen.getByTestId("medication-disclosure").textContent ?? ""
    ).toLowerCase();
    const allergy = screen.queryByTestId("medication-allergy-match-callout");
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(disclosure, "")
      .replace((allergy?.textContent ?? "").toLowerCase(), "");
    for (const forbidden of [
      "auto-refill",
      "auto-prescribed",
      "auto-dose",
      "pharmacy contacted",
      "prescription sent",
      "drug interaction detected by chartnav",
      "increase dose to",
      "decrease dose to",
      "switch medication to",
      "stop medication",
      "order placed",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});

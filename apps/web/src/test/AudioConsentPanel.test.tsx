/**
 * Phase 25A / GH-001 — AudioConsentPanel unit tests.
 *
 * Verifies:
 *  - Initial fetch and badge rendering.
 *  - Write roles see the form; reviewer sees a read-only note.
 *  - Submit flips status and propagates `recording_permitted` via
 *    the onConsentChange callback the parent uses to disable the
 *    Record button.
 *  - Error from the API renders a visible alert.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchAudioConsent: vi.fn(),
    setAudioConsent: vi.fn(),
  };
});

import {
  fetchAudioConsent,
  setAudioConsent,
  type AudioConsent,
} from "../api";
import { AudioConsentPanel } from "../AudioConsentPanel";

const fetchMock = vi.mocked(fetchAudioConsent);
const setMock = vi.mocked(setAudioConsent);

const NOT_RECORDED: AudioConsent = {
  encounter_id: 42,
  organization_id: 1,
  status: "not_recorded",
  method: "unknown",
  actor_user_id: null,
  note: null,
  recording_permitted: false,
  created_at: "2026-05-16T00:00:00+00:00",
  updated_at: "2026-05-16T00:00:00+00:00",
};

const GRANTED: AudioConsent = {
  ...NOT_RECORDED,
  status: "granted",
  method: "verbal",
  actor_user_id: 7,
  note: "verbal consent at intake",
  recording_permitted: true,
  updated_at: "2026-05-16T00:05:00+00:00",
};

beforeEach(() => {
  fetchMock.mockReset();
  setMock.mockReset();
});

describe("AudioConsentPanel", () => {
  it("renders the not-recorded state and reports it via onConsentChange", async () => {
    fetchMock.mockResolvedValueOnce(NOT_RECORDED);
    const onChange = vi.fn();
    render(
      <AudioConsentPanel
        identity="clin@chartnav.local"
        encounterId={42}
        role="clinician"
        onConsentChange={onChange}
      />,
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const badge = await screen.findByTestId(
      "audio-consent-status-badge",
    );
    expect(badge).toHaveTextContent(/not captured/i);
    expect(
      screen.getByTestId("audio-consent-blocked"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith(NOT_RECORDED),
    );
  });

  it("clinician can submit consent and the parent receives the granted state", async () => {
    fetchMock.mockResolvedValueOnce(NOT_RECORDED);
    setMock.mockResolvedValueOnce(GRANTED);
    const onChange = vi.fn();

    render(
      <AudioConsentPanel
        identity="clin@chartnav.local"
        encounterId={42}
        role="clinician"
        onConsentChange={onChange}
      />,
    );

    await screen.findByTestId("audio-consent-form");
    const user = userEvent.setup();
    await user.click(screen.getByTestId("audio-consent-submit"));

    await waitFor(() => expect(setMock).toHaveBeenCalledTimes(1));
    // Default form selections from the component are granted/verbal.
    expect(setMock).toHaveBeenCalledWith(
      "clin@chartnav.local",
      42,
      expect.objectContaining({ status: "granted", method: "verbal" }),
    );

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith(GRANTED),
    );

    // Blocked banner clears once permitted.
    expect(
      screen.queryByTestId("audio-consent-blocked"),
    ).not.toBeInTheDocument();
  });

  it("reviewer sees a read-only note, no form, and no submit button", async () => {
    fetchMock.mockResolvedValueOnce(NOT_RECORDED);
    render(
      <AudioConsentPanel
        identity="rev@chartnav.local"
        encounterId={42}
        role="reviewer"
      />,
    );
    await screen.findByTestId("audio-consent-status-badge");
    expect(
      screen.getByTestId("audio-consent-readonly-note"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("audio-consent-form"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("audio-consent-submit"),
    ).not.toBeInTheDocument();
  });

  it("renders the API error when fetch fails", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network down"));
    const onChange = vi.fn();
    render(
      <AudioConsentPanel
        identity="clin@chartnav.local"
        encounterId={42}
        role="clinician"
        onConsentChange={onChange}
      />,
    );
    const err = await screen.findByTestId("audio-consent-error");
    expect(err).toHaveTextContent(/network down/);
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(null));
  });
});

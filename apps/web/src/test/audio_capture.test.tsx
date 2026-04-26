// Phase A item 5 — vitest coverage for AudioCapture.
//
// Drives the recorder shim end-to-end and exercises the
// `visibilitychange` background-tab pause path documented in §3.4.
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { AudioCapture, AudioCaptureRecorderShim } from "../features/encounter/AudioCapture";

function makeShim(): AudioCaptureRecorderShim & {
  paused: number;
  resumed: number;
  stopped: number;
} {
  let paused = 0;
  let resumed = 0;
  let stopped = 0;
  const shim: AudioCaptureRecorderShim & {
    paused: number;
    resumed: number;
    stopped: number;
  } = {
    async start() {},
    pause() { paused++; (shim as any).paused = paused; },
    resume() { resumed++; (shim as any).resumed = resumed; },
    async stop() { stopped++; (shim as any).stopped = stopped; return new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm" }); },
    paused: 0,
    resumed: 0,
    stopped: 0,
  };
  return shim;
}

describe("AudioCapture", () => {
  it("starts in idle state and exposes the start button", () => {
    render(<AudioCapture />);
    expect(screen.getByTestId("audio-capture-state").textContent).toBe("idle");
    expect(screen.getByTestId("audio-capture-start")).toBeInTheDocument();
  });

  it("transitions to recording on start", async () => {
    const shim = makeShim();
    render(<AudioCapture recorderShim={shim} />);
    await act(async () => { fireEvent.click(screen.getByTestId("audio-capture-start")); });
    expect(screen.getByTestId("audio-capture-state").textContent).toBe("recording");
    expect(screen.getByTestId("audio-capture-stop")).toBeInTheDocument();
  });

  it("pauses to paused-backgrounded when the tab is hidden", async () => {
    const shim = makeShim();
    const onBg = vi.fn();
    render(<AudioCapture recorderShim={shim} onBackgroundPause={onBg} />);
    await act(async () => { fireEvent.click(screen.getByTestId("audio-capture-start")); });
    // Force document.visibilityState to "hidden" and emit the event.
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(screen.getByTestId("audio-capture-state").textContent).toBe("paused-backgrounded");
    expect(shim.paused).toBeGreaterThan(0);
    expect(onBg).toHaveBeenCalled();
    expect(screen.getByTestId("audio-capture-paused-reason").textContent).toMatch(/background/i);
    // Resume is explicit per spec.
    expect(screen.getByTestId("audio-capture-resume")).toBeInTheDocument();
  });

  it("stop yields the captured blob", async () => {
    const shim = makeShim();
    const onStopped = vi.fn();
    render(<AudioCapture recorderShim={shim} onStopped={onStopped} />);
    await act(async () => { fireEvent.click(screen.getByTestId("audio-capture-start")); });
    await act(async () => { fireEvent.click(screen.getByTestId("audio-capture-stop")); });
    expect(onStopped).toHaveBeenCalledTimes(1);
    const blob = onStopped.mock.calls[0][0] as Blob;
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBe(3);
  });
});

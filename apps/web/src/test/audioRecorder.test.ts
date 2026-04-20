import { describe, expect, it, vi } from "vitest";
import {
  BrowserCaptureError,
  detectBrowserCapture,
  startBrowserRecording,
} from "../audioRecorder";

// Phase 36 — recorder unit tests. jsdom doesn't ship MediaRecorder
// or navigator.mediaDevices.getUserMedia, so we drive the recorder
// via the deps injection points its public surface exposes.

function makeFakeStream(): MediaStream {
  const tracks = [{ stop: vi.fn() }];
  return {
    getTracks: () => tracks,
  } as unknown as MediaStream;
}

function makeFakeRecorderClass(opts: {
  isTypeSupported?: (m: string) => boolean;
} = {}) {
  const isTypeSupported =
    opts.isTypeSupported ?? ((m: string) => m.startsWith("audio/webm"));
  // Track every constructed instance so tests can drive lifecycle.
  const instances: any[] = [];

  class FakeRecorder {
    static isTypeSupported = isTypeSupported;
    state: "inactive" | "recording" | "paused" = "inactive";
    mimeType: string;
    ondataavailable: ((e: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    onerror: ((e: { error?: { message?: string } }) => void) | null = null;
    constructor(_stream: MediaStream, options?: { mimeType?: string }) {
      this.mimeType = options?.mimeType ?? "audio/webm";
      instances.push(this);
    }
    start(_timeslice?: number) {
      this.state = "recording";
    }
    stop() {
      this.state = "inactive";
      // Defer firing so the controller can attach its onstop after
      // calling `.stop()` — matches real-browser semantics.
      setTimeout(() => this.onstop?.(), 0);
    }
    /** Test helper: simulate a data chunk arriving from the OS. */
    _emitData(data: Blob) {
      this.ondataavailable?.({ data });
    }
  }
  return { FakeRecorder, instances };
}

describe("detectBrowserCapture", () => {
  it("reports unsupported when navigator.mediaDevices is missing", () => {
    const support = detectBrowserCapture({
      navigator: {} as any,
      MediaRecorderCls: undefined as any,
    });
    expect(support.supported).toBe(false);
    expect(support.reason).toBe("browser_capture_unsupported");
  });

  it("reports unsupported when MediaRecorder is missing", () => {
    const support = detectBrowserCapture({
      navigator: { mediaDevices: { getUserMedia: vi.fn() } } as any,
      MediaRecorderCls: undefined as any,
    });
    expect(support.supported).toBe(false);
    expect(support.reason).toBe("browser_capture_unsupported");
  });

  it("reports no_supported_mime when MediaRecorder rejects every container", () => {
    const { FakeRecorder } = makeFakeRecorderClass({
      isTypeSupported: () => false,
    });
    const support = detectBrowserCapture({
      navigator: { mediaDevices: { getUserMedia: vi.fn() } } as any,
      MediaRecorderCls: FakeRecorder as any,
    });
    expect(support.supported).toBe(false);
    expect(support.reason).toBe("browser_capture_no_supported_mime");
  });

  it("picks the first supported MIME when present", () => {
    const { FakeRecorder } = makeFakeRecorderClass({
      isTypeSupported: (m) => m === "audio/webm;codecs=opus",
    });
    const support = detectBrowserCapture({
      navigator: { mediaDevices: { getUserMedia: vi.fn() } } as any,
      MediaRecorderCls: FakeRecorder as any,
    });
    expect(support.supported).toBe(true);
    expect(support.pickedMime).toBe("audio/webm;codecs=opus");
    expect(support.pickedExt).toBe(".webm");
  });
});

describe("startBrowserRecording", () => {
  it("throws BrowserCaptureError(permission_denied) on NotAllowedError", async () => {
    const denied = new Error("denied");
    (denied as any).name = "NotAllowedError";
    const { FakeRecorder } = makeFakeRecorderClass();
    await expect(
      startBrowserRecording({
        navigator: {
          mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(denied) },
        } as any,
        MediaRecorderCls: FakeRecorder as any,
      })
    ).rejects.toMatchObject({
      code: "browser_capture_permission_denied",
    });
  });

  it("throws BrowserCaptureError(unsupported) when no recorder API is available", async () => {
    await expect(
      startBrowserRecording({
        navigator: {} as any,
        MediaRecorderCls: undefined as any,
      })
    ).rejects.toBeInstanceOf(BrowserCaptureError);
  });

  it("happy path: start, emit chunks, stop → resolves with a File of the correct mime", async () => {
    const stream = makeFakeStream();
    const { FakeRecorder, instances } = makeFakeRecorderClass();
    const fixedDate = new Date("2026-04-19T22:15:00Z");
    const controller = await startBrowserRecording({
      navigator: {
        mediaDevices: {
          getUserMedia: vi.fn().mockResolvedValue(stream),
        },
      } as any,
      MediaRecorderCls: FakeRecorder as any,
      now: () => fixedDate,
    });
    expect(instances.length).toBe(1);
    const rec = instances[0];
    rec._emitData(new Blob(["abc"], { type: "audio/webm" }));
    rec._emitData(new Blob(["def"], { type: "audio/webm" }));
    const file = await controller.stop();
    expect(file).toBeInstanceOf(File);
    expect(file.type).toBe("audio/webm;codecs=opus");
    expect(file.name).toMatch(/^chartnav-dictation-.*\.webm$/);
    // Tracks must be released so the OS recording indicator goes away.
    expect((stream.getTracks() as any)[0].stop).toHaveBeenCalled();
  });

  it("rejects with no_audio_data when stop fires before any chunk arrives", async () => {
    const stream = makeFakeStream();
    const { FakeRecorder, instances } = makeFakeRecorderClass();
    const controller = await startBrowserRecording({
      navigator: {
        mediaDevices: {
          getUserMedia: vi.fn().mockResolvedValue(stream),
        },
      } as any,
      MediaRecorderCls: FakeRecorder as any,
    });
    const stopPromise = controller.stop();
    // Don't emit any data; stop has been called → onstop fires → no chunks.
    await expect(stopPromise).rejects.toMatchObject({
      code: "browser_capture_no_audio_data",
    });
    expect(instances.length).toBe(1);
  });

  it("cancel() releases the mic and is idempotent", async () => {
    const stream = makeFakeStream();
    const { FakeRecorder } = makeFakeRecorderClass();
    const controller = await startBrowserRecording({
      navigator: {
        mediaDevices: {
          getUserMedia: vi.fn().mockResolvedValue(stream),
        },
      } as any,
      MediaRecorderCls: FakeRecorder as any,
    });
    controller.cancel();
    controller.cancel(); // idempotent — must not throw
    expect((stream.getTracks() as any)[0].stop).toHaveBeenCalled();
  });
});

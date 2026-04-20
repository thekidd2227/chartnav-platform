// Browser microphone capture wedge — phase 36.
//
// Honest, narrow wrapper around the only browser primitives that
// actually exist for this:
//
//   - `navigator.mediaDevices.getUserMedia({ audio: true })`
//   - `MediaRecorder`
//
// What this module is NOT:
//
//   - It does NOT pretend to be a native mobile app.
//   - It does NOT enumerate or pair Bluetooth devices. The browser
//     and OS handle audio routing (AirPods / wired headset / built-in
//     mic) — when the user picks AirPods at the OS level, the
//     browser's mic-permission dialog sees AirPods as the input.
//     We don't try to fake device-picker UI we couldn't honestly
//     build in a web context.
//   - It does NOT do ambient always-on listening. Recording starts
//     on an explicit user click, stops on an explicit user click,
//     and the resulting Blob is handed back synchronously.
//   - It does NOT do real-time streaming to STT. The blob lands as
//     a single multi-format file, hits the existing
//     `/encounters/{id}/inputs/audio` endpoint, and flows through
//     the phase-33/35 ingestion pipeline like any other upload.
//
// The recorder takes injectable shims for `getUserMedia` and the
// `MediaRecorder` class so jsdom tests can drive deterministic
// behaviour without polluting the global. Production code passes
// nothing and the runtime picks up the real browser globals.

export const RECORDER_FILENAME_PREFIX = "chartnav-dictation";

/**
 * Stable error codes the UI keys off when surfacing a capture
 * failure. Every code is a real, distinguishable failure mode —
 * none are aspirational.
 */
export type BrowserCaptureErrorCode =
  | "browser_capture_unsupported"      // navigator/MediaRecorder absent
  | "browser_capture_permission_denied" // user said no, or the OS blocks
  | "browser_capture_no_supported_mime" // no compatible audio container
  | "browser_capture_no_audio_data"    // mic produced 0 bytes
  | "browser_capture_failed";          // anything else, with the reason

export class BrowserCaptureError extends Error {
  code: BrowserCaptureErrorCode;
  constructor(code: BrowserCaptureErrorCode, message: string) {
    super(`${code}: ${message}`);
    this.code = code;
  }
}

/** Audio container candidates in preference order. WEBM/Opus is
 *  the cleanest cross-browser default; MP4/AAC is the iOS Safari
 *  path; OGG/Opus is the Firefox fallback. Every candidate is
 *  in our backend's allowlist (phase 33 `AUDIO_ALLOWED_CONTENT_TYPES`).
 */
const RECORDER_MIME_CANDIDATES: { mime: string; ext: string }[] = [
  { mime: "audio/webm;codecs=opus", ext: ".webm" },
  { mime: "audio/webm", ext: ".webm" },
  { mime: "audio/mp4;codecs=mp4a.40.2", ext: ".mp4" },
  { mime: "audio/mp4", ext: ".mp4" },
  { mime: "audio/ogg;codecs=opus", ext: ".ogg" },
  { mime: "audio/ogg", ext: ".ogg" },
];

interface MinimalGetUserMedia {
  (constraints: MediaStreamConstraints): Promise<MediaStream>;
}

interface MinimalMediaRecorderCtor {
  new (stream: MediaStream, options?: { mimeType?: string }): MinimalMediaRecorder;
  isTypeSupported(mimeType: string): boolean;
}

interface MinimalMediaRecorder {
  start(timeslice?: number): void;
  stop(): void;
  ondataavailable: ((event: { data: Blob }) => void) | null;
  onstop: (() => void) | null;
  onerror: ((event: { error?: { message?: string } }) => void) | null;
  state: "inactive" | "recording" | "paused";
  mimeType: string;
}

export interface BrowserCaptureSupport {
  supported: boolean;
  reason?: BrowserCaptureErrorCode;
  pickedMime?: string;
  pickedExt?: string;
}

/** Cheap synchronous feature-detect. Used by the UI to decide
 *  whether to render the Record button at all. Returning the picked
 *  MIME type so the UI can also surface what container the
 *  recording will be in (some clinicians ask). */
export function detectBrowserCapture(deps?: {
  navigator?: typeof globalThis.navigator;
  MediaRecorderCls?: MinimalMediaRecorderCtor;
}): BrowserCaptureSupport {
  const nav: any = deps?.navigator ?? (globalThis as any).navigator;
  const Rec: any =
    deps?.MediaRecorderCls ?? (globalThis as any).MediaRecorder;

  if (!nav?.mediaDevices?.getUserMedia) {
    return {
      supported: false,
      reason: "browser_capture_unsupported",
    };
  }
  if (typeof Rec !== "function") {
    return {
      supported: false,
      reason: "browser_capture_unsupported",
    };
  }
  const isSupported = (m: string): boolean => {
    try {
      return Rec.isTypeSupported && Rec.isTypeSupported(m);
    } catch {
      return false;
    }
  };
  const picked = RECORDER_MIME_CANDIDATES.find((c) => isSupported(c.mime));
  if (!picked) {
    // Some browsers expose MediaRecorder but with `isTypeSupported`
    // returning false for every audio container we accept. Treat as
    // unsupported rather than letting the recorder explode mid-stream.
    return {
      supported: false,
      reason: "browser_capture_no_supported_mime",
    };
  }
  return {
    supported: true,
    pickedMime: picked.mime,
    pickedExt: picked.ext,
  };
}

export interface BrowserRecording {
  /** Stop recording and resolve with a File ready for upload via
   *  `uploadEncounterAudio()`. */
  stop(): Promise<File>;
  /** Discard any in-progress capture and release the mic. Idempotent. */
  cancel(): void;
  /** The MIME type the recorder is actually writing in. */
  mimeType: string;
  /** The file extension that pairs with the MIME type. */
  ext: string;
}

/** Start microphone capture. Resolves once the user has granted mic
 *  permission and the recorder is actually running. The returned
 *  controller is the only way to stop and get a File back.
 *
 *  This is a side-effecting function — it asks the browser for the
 *  mic. Callers should only invoke it from a user gesture (button
 *  click), or browsers will refuse the prompt.
 */
export async function startBrowserRecording(deps?: {
  navigator?: typeof globalThis.navigator;
  MediaRecorderCls?: MinimalMediaRecorderCtor;
  now?: () => Date;
}): Promise<BrowserRecording> {
  const nav: any = deps?.navigator ?? (globalThis as any).navigator;
  const Rec: any =
    deps?.MediaRecorderCls ?? (globalThis as any).MediaRecorder;
  const now = deps?.now ?? (() => new Date());

  const support = detectBrowserCapture({ navigator: nav, MediaRecorderCls: Rec });
  if (!support.supported || !support.pickedMime || !support.pickedExt) {
    throw new BrowserCaptureError(
      support.reason ?? "browser_capture_unsupported",
      "browser microphone capture isn't available in this environment",
    );
  }

  // Permission prompt. Wrapped so we can map the standard browser
  // exceptions onto stable codes the UI keys off.
  let stream: MediaStream;
  try {
    stream = await nav.mediaDevices.getUserMedia({ audio: true });
  } catch (e: any) {
    const name = e?.name || "";
    if (
      name === "NotAllowedError" ||
      name === "SecurityError" ||
      name === "PermissionDeniedError"
    ) {
      throw new BrowserCaptureError(
        "browser_capture_permission_denied",
        "microphone permission was denied",
      );
    }
    throw new BrowserCaptureError(
      "browser_capture_failed",
      `getUserMedia failed: ${name || e?.message || e}`,
    );
  }

  let recorder: MinimalMediaRecorder;
  try {
    recorder = new Rec(stream, { mimeType: support.pickedMime });
  } catch (e: any) {
    // If construction fails, release the mic immediately so the
    // OS-level recording indicator goes away.
    try {
      stream.getTracks().forEach((t) => t.stop());
    } catch {
      /* noop */
    }
    throw new BrowserCaptureError(
      "browser_capture_failed",
      `MediaRecorder construction failed: ${e?.message || e}`,
    );
  }

  const chunks: Blob[] = [];
  let stopResolve: ((file: File) => void) | null = null;
  let stopReject: ((err: Error) => void) | null = null;
  let cancelled = false;

  recorder.ondataavailable = (event) => {
    if (event.data && (event.data as Blob).size > 0) {
      chunks.push(event.data);
    }
  };
  recorder.onerror = (event) => {
    const msg = event?.error?.message || "MediaRecorder onerror fired";
    if (stopReject) {
      stopReject(new BrowserCaptureError("browser_capture_failed", msg));
      stopReject = null;
      stopResolve = null;
    }
  };
  recorder.onstop = () => {
    try {
      stream.getTracks().forEach((t) => t.stop());
    } catch {
      /* noop */
    }
    if (cancelled) return;
    if (chunks.length === 0) {
      if (stopReject) {
        stopReject(
          new BrowserCaptureError(
            "browser_capture_no_audio_data",
            "recorder produced no audio data",
          ),
        );
      }
      return;
    }
    const blob = new Blob(chunks, { type: support.pickedMime });
    const ts = now()
      .toISOString()
      .replace(/[:.]/g, "-")
      .replace("T", "-")
      .slice(0, 19);
    const filename = `${RECORDER_FILENAME_PREFIX}-${ts}${support.pickedExt}`;
    const file = new File([blob], filename, {
      type: support.pickedMime,
    });
    if (stopResolve) stopResolve(file);
  };

  // 1-second timeslice gives `ondataavailable` regular chunks even
  // for short recordings, which avoids a quirk in some browsers
  // where stop() before any data event fires returns nothing.
  recorder.start(1000);

  return {
    mimeType: support.pickedMime,
    ext: support.pickedExt,
    stop(): Promise<File> {
      return new Promise<File>((resolve, reject) => {
        stopResolve = resolve;
        stopReject = reject;
        try {
          recorder.stop();
        } catch (e: any) {
          reject(
            new BrowserCaptureError(
              "browser_capture_failed",
              `MediaRecorder.stop() failed: ${e?.message || e}`,
            ),
          );
        }
      });
    },
    cancel() {
      cancelled = true;
      try {
        if (recorder.state !== "inactive") recorder.stop();
      } catch {
        /* noop */
      }
      try {
        stream.getTracks().forEach((t) => t.stop());
      } catch {
        /* noop */
      }
    },
  };
}

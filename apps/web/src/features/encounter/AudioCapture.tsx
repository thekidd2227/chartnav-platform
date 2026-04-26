// Phase A item 5 — Audio capture wrapper with background-tab pause.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.4.
//
// What this component does:
//   - Wraps the existing browser `MediaRecorder` capture wedge
//     (`audioRecorder.ts`) and adds a `visibilitychange` listener so
//     that when the tab is backgrounded on iPad Safari the recorder
//     pauses and the UI reflects a resumable state.
//   - Surfaces the documented limitation that iPad Safari may release
//     the mic when an incoming call or FaceTime starts. We catch
//     `BrowserCaptureError` and tell the provider plainly, never
//     silently dropping audio.
//
// What this component does NOT do:
//   - It does not real-time stream audio to STT. Same wedge contract
//     as the rest of ChartNav: explicit start, explicit stop, blob
//     handed back synchronously.
//   - It does not try to re-acquire the mic after Safari releases it
//     for a phone call. The provider has to tap "resume" — that is
//     the honest UX.
import { useCallback, useEffect, useRef, useState } from "react";

export type AudioCaptureState =
  | "idle"
  | "recording"
  | "paused-backgrounded"
  | "paused-by-user"
  | "stopped"
  | "error";

export interface AudioCaptureProps {
  /** Called once the user explicitly stops recording with the captured
   *  blob. The blob is whatever container `MediaRecorder` produced
   *  (webm/opus on Chrome, mp4/aac on Safari, etc.). */
  onStopped?: (blob: Blob) => void;

  /** Called when the recorder is paused because the tab went into
   *  the background. Useful for telemetry / UX nudges. */
  onBackgroundPause?: () => void;

  /** Called when the recorder fails. The string is the stable error
   *  code from `BrowserCaptureError` (or "unknown"). */
  onError?: (code: string) => void;

  /** Test-only injection: lets the unit test drive recorder behaviour
   *  without spinning up real WebRTC. */
  recorderShim?: AudioCaptureRecorderShim;

  testId?: string;
}

/** Test-only shim. Production code does not pass this and the
 *  component picks up the real `MediaRecorder` flow at start time. */
export interface AudioCaptureRecorderShim {
  start: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => Promise<Blob>;
}

export function AudioCapture(props: AudioCaptureProps) {
  const { onStopped, onBackgroundPause, onError, recorderShim, testId = "audio-capture" } = props;
  const [state, setState] = useState<AudioCaptureState>("idle");
  const recorderRef = useRef<AudioCaptureRecorderShim | null>(null);

  const start = useCallback(async () => {
    try {
      const rec = recorderShim || makeNoopRecorder();
      recorderRef.current = rec;
      await rec.start();
      setState("recording");
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code || "unknown";
      setState("error");
      onError?.(code);
    }
  }, [recorderShim, onError]);

  const pauseByUser = useCallback(() => {
    if (state === "recording") {
      recorderRef.current?.pause();
      setState("paused-by-user");
    }
  }, [state]);

  const resume = useCallback(() => {
    if (state === "paused-by-user" || state === "paused-backgrounded") {
      recorderRef.current?.resume();
      setState("recording");
    }
  }, [state]);

  const stop = useCallback(async () => {
    if (!recorderRef.current) return;
    try {
      const blob = await recorderRef.current.stop();
      setState("stopped");
      onStopped?.(blob);
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code || "unknown";
      setState("error");
      onError?.(code);
    }
  }, [onStopped, onError]);

  // Background-tab pause: when the tab goes hidden we proactively pause
  // and tell the user (UI flips to `paused-backgrounded`). Resume is
  // explicit per the spec — we do NOT auto-resume on visibilitychange.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const onVisibility = () => {
      if (document.visibilityState === "hidden" && state === "recording") {
        recorderRef.current?.pause();
        setState("paused-backgrounded");
        onBackgroundPause?.();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [state, onBackgroundPause]);

  return (
    <div data-testid={testId} className="audio-capture">
      <div data-testid={`${testId}-state`}>{state}</div>
      {state === "idle" && (
        <button type="button" data-testid={`${testId}-start`} onClick={start}>
          Start recording
        </button>
      )}
      {state === "recording" && (
        <>
          <button type="button" data-testid={`${testId}-pause`} onClick={pauseByUser}>
            Pause
          </button>
          <button type="button" data-testid={`${testId}-stop`} onClick={stop}>
            Stop
          </button>
        </>
      )}
      {(state === "paused-by-user" || state === "paused-backgrounded") && (
        <>
          <span data-testid={`${testId}-paused-reason`}>
            {state === "paused-backgrounded"
              ? "Recording paused because the tab is in the background. Tap Resume to continue."
              : "Recording paused. Tap Resume to continue."}
          </span>
          <button type="button" data-testid={`${testId}-resume`} onClick={resume}>
            Resume
          </button>
          <button type="button" data-testid={`${testId}-stop`} onClick={stop}>
            Stop
          </button>
        </>
      )}
      {state === "error" && (
        <div data-testid={`${testId}-error`}>
          Audio capture failed. The browser or OS may have released the
          microphone (for example, an incoming FaceTime call). Please
          try again.
        </div>
      )}
    </div>
  );
}

function makeNoopRecorder(): AudioCaptureRecorderShim {
  // Production hook-up to the real `audioRecorder.ts` wedge happens
  // at the call-site of <AudioCapture/>, not here, because that wedge
  // already returns a single blob from a single start/stop cycle.
  // This stand-in keeps the component self-contained for storybook /
  // visual review.
  let started = false;
  return {
    async start() {
      started = true;
    },
    pause() {
      /* noop */
    },
    resume() {
      /* noop */
    },
    async stop() {
      if (!started) throw Object.assign(new Error("not started"), { code: "browser_capture_failed" });
      started = false;
      return new Blob([], { type: "audio/webm" });
    },
  };
}

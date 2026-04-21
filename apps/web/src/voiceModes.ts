// Phase 38 — A4 — voice capture modes.
//
// Separates two distinct recording ergonomics:
//
//   ambient  — full-encounter capture, review the transcript tier,
//              let the generator produce a draft. This is what
//              `NoteWorkspace` already uses today.
//
//   targeted — push-to-talk, 10-second cap, drops the transcribed
//              text directly at the current draft cursor. Intended
//              to fill shortcut blanks (`___`) or produce a single
//              phrase the clinician is already writing.
//
// The modes share the browser capture primitive in `audioRecorder.ts`;
// this module only owns the mode discriminator + helper predicates
// so both App.tsx and NoteWorkspace.tsx can key off it.

export type VoiceMode = "ambient" | "targeted";

export const VOICE_MODES: VoiceMode[] = ["ambient", "targeted"];

export interface VoiceModeDescriptor {
  mode: VoiceMode;
  label: string;
  hint: string;
  /** Upper bound in seconds. Ambient gets a soft cap; targeted a hard cap. */
  maxSeconds: number;
  /** Whether this mode inserts the text at the draft cursor on completion. */
  insertAtCursor: boolean;
}

export const VOICE_MODE_REGISTRY: Record<VoiceMode, VoiceModeDescriptor> = {
  ambient: {
    mode: "ambient",
    label: "Ambient",
    hint: "Full-encounter capture — transcript tier, review before draft.",
    maxSeconds: 30 * 60,
    insertAtCursor: false,
  },
  targeted: {
    mode: "targeted",
    label: "Targeted",
    hint: "Push-to-talk phrase — dropped at the cursor, max 10s.",
    maxSeconds: 10,
    insertAtCursor: true,
  },
};

export function voiceModeHint(mode: VoiceMode): string {
  return VOICE_MODE_REGISTRY[mode].hint;
}

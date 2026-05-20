// Phase 63C — event_data shaping for the encounter timeline
// composer.
//
// The backend (apps/api/app/api/routes.py) requires
// `manual_note.event_data` to be a JSON object containing
// at least a `note` field. Previously the composer parsed the raw
// text as JSON and silently sent the raw string when parse failed
// — the backend then rejected with `invalid_event_data`.
//
// This helper centralises the policy:
//
//   - manual_note + empty input → { error: "empty" }
//   - manual_note + non-empty raw that isn't valid JSON object →
//     { ok: { note: raw } }
//   - manual_note + valid JSON object → { ok: parsed }
//   - any other event_type → existing behaviour (parse, fall back
//     to raw string for opaque types) so we don't regress events
//     that intentionally carry a freeform string payload.

export type ShapeEventResult =
  | { ok: unknown | undefined }
  | { error: "empty" };

export function shapeEventData(
  eventType: string,
  rawInput: string,
): ShapeEventResult {
  const trimmed = rawInput.trim();
  if (!trimmed) {
    if (eventType === "manual_note") {
      return { error: "empty" };
    }
    return { ok: undefined };
  }

  let parsed: unknown;
  let parseOk = true;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    parseOk = false;
  }

  if (eventType === "manual_note") {
    const isObject =
      parseOk &&
      parsed !== null &&
      typeof parsed === "object" &&
      !Array.isArray(parsed);
    if (isObject) {
      return { ok: parsed };
    }
    return { ok: { note: trimmed } };
  }

  return { ok: parseOk ? parsed : trimmed };
}

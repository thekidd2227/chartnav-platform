// Phase 29 — Clinical Shortcuts (doctor-only specialist shorthand pack).
//
// Separate from the phase-27 Quick Comments pad on purpose. Quick
// Comments are a clinician clipboard for free-form short phrases;
// Clinical Shortcuts are a **curated shorthand phrase bank** of
// structured note fragments that subspecialists actually write.
//
// These phrases are clinician-inserted charting content — NOT:
//   - transcript-derived findings
//   - extracted structured findings
//   - AI-generated draft text
//
// They are shared UI content, identical for every clinician, so they
// ship with the frontend bundle. No per-user persistence, no DB seed.
//
// The abbreviation reference is a *curated* subset of the Spokane
// Eye Clinic common ophthalmic abbreviations sheet, narrowed to the
// terms that appear in or are adjacent to the shipped shortcuts.
// We intentionally do NOT dump the full sheet into the UI.

export interface ClinicalShortcut {
  /** Stable string id; never a DB id. Used as the `shortcut_id`
   *  passed to the usage-audit endpoint. */
  id: string;
  /** Display group header. */
  group: ClinicalShortcutGroup;
  /** The note fragment inserted verbatim into the draft. Blanks like
   *  `___` are preserved so the clinician fills them in after
   *  insertion — they are intentional, not a template bug. */
  body: string;
  /** Free-text tags used for search matching alongside body + group.
   *  Include abbreviations that don't necessarily appear in `body`
   *  so a search for, e.g., "RD" surfaces PVD scleral-depressed-exam
   *  phrasing that rules it out. */
  tags: string[];
}

export type ClinicalShortcutGroup = "PVD" | "Retinal detachment" | "Wet/Dry AMD";

export const CLINICAL_SHORTCUT_GROUPS: ClinicalShortcutGroup[] = [
  "PVD",
  "Retinal detachment",
  "Wet/Dry AMD",
];

export const CLINICAL_SHORTCUTS: ClinicalShortcut[] = [
  // ---------- PVD ----------
  {
    id: "pvd-01",
    group: "PVD",
    body:
      "Acute PVD noted with vitreous syneresis. Negative Shafer sign. " +
      "No retinal tear or retinal detachment on scleral depressed exam.",
    tags: [
      "pvd", "acute", "retina", "exam", "shafer", "syneresis",
      "retinal tear", "rt", "retinal detachment", "rd",
      "scleral depressed", "scleral depression",
    ],
  },
  {
    id: "pvd-02",
    group: "PVD",
    body:
      "Symptomatic PVD with flashes/floaters. Peripheral retina examined " +
      "to far periphery; no holes, tears, or RD seen today.",
    tags: [
      "pvd", "retina", "exam", "flashes", "floaters",
      "peripheral retina", "holes", "tears", "rd",
      "retinal detachment",
    ],
  },
  {
    id: "pvd-03",
    group: "PVD",
    body:
      "Chronic PVD, stable. Retinal detachment precautions reviewed.",
    tags: [
      "pvd", "chronic", "stable", "counseling",
      "retinal detachment", "rd", "precautions", "postop",
    ],
  },

  // ---------- Retinal detachment ----------
  {
    id: "rd-01",
    group: "Retinal detachment",
    body:
      "Rhegmatogenous retinal detachment involving ___ quadrants, " +
      "macula on / macula off.",
    tags: [
      "rd", "retinal detachment", "rhegmatogenous",
      "macula on", "macula off", "mac on", "mac off",
      "retina", "preop",
    ],
  },
  {
    id: "rd-02",
    group: "Retinal detachment",
    body:
      "Localized subretinal fluid extending from ___ to ___ o\u2019clock.",
    tags: [
      "srf", "subretinal fluid", "localized", "rd",
      "retinal detachment", "retina", "exam",
    ],
  },
  {
    id: "rd-03",
    group: "Retinal detachment",
    body:
      "Retina attached under oil / gas with good laser barricade.",
    tags: [
      "rd", "retinal detachment", "retina attached",
      "silicone oil", "gas", "laser", "barricade", "retinopexy",
      "postop", "ppv", "sb", "scleral buckle", "pr",
    ],
  },
  {
    id: "rd-04",
    group: "Retinal detachment",
    body:
      "Post-op retina remains attached; no recurrent SRF noted.",
    tags: [
      "rd", "retinal detachment", "postop", "post-op",
      "retina attached", "srf", "subretinal fluid",
      "recurrent", "ppv", "sb", "scleral buckle", "pr",
    ],
  },

  // ---------- Wet/Dry AMD ----------
  {
    id: "amd-01",
    group: "Wet/Dry AMD",
    body:
      "Dry AMD with drusen and RPE mottling, no fluid or hemorrhage.",
    tags: [
      "amd", "armd", "dry", "drusen", "rpe", "rpe mottling",
      "nonexudative", "macula", "no fluid", "no hemorrhage",
    ],
  },
  {
    id: "amd-02",
    group: "Wet/Dry AMD",
    body:
      "Intermediate nonexudative AMD with large confluent drusen and " +
      "pigmentary change.",
    tags: [
      "amd", "armd", "intermediate", "nonexudative",
      "drusen", "confluent", "pigmentary", "rpe", "macula",
    ],
  },
  {
    id: "amd-03",
    group: "Wet/Dry AMD",
    body:
      "Exudative AMD with persistent / improved / worsened intraretinal " +
      "fluid, subretinal fluid, and/or PED. No new macular hemorrhage " +
      "on exam today.",
    tags: [
      "amd", "armd", "exudative", "wet amd", "wet",
      "irf", "intraretinal fluid", "srf", "subretinal fluid",
      "ped", "pigment epithelial detachment",
      "macular hemorrhage", "macula", "oct", "injection",
    ],
  },
];

/**
 * Curated abbreviation reference.
 *
 * Narrowed from the Spokane Eye Clinic common-ophthalmic sheet to
 * the terms that appear in — or are likely-searched alongside —
 * the shipped shortcuts. The UI uses this for:
 *   1. subtle hover hints on highlighted abbreviations inside the
 *      shortcut body (via `<abbr title>`),
 *   2. abbreviation-aware search: typing "SRF" finds shortcuts
 *      whose tags include "srf" even if the body spells out
 *      "subretinal fluid".
 *
 * Keep this list short. Adding every term in the sheet would clutter
 * the UI; add an entry here only when a live shortcut uses it or a
 * clinician is likely to search for it.
 */
export const ABBREVIATION_HINTS: Record<string, string> = {
  AMD: "Age-related macular degeneration",
  ARMD: "Age-related macular degeneration",
  CME: "Cystoid macular edema",
  "C/D": "Cup-to-disc ratio",
  DFE: "Dilated fundus exam",
  "D&Q": "Deep and quiet (anterior chamber)",
  ERM: "Epiretinal membrane",
  IOP: "Intraocular pressure",
  IRF: "Intraretinal fluid",
  OCT: "Optical coherence tomography",
  ONH: "Optic nerve head",
  OD: "Right eye (oculus dexter)",
  OS: "Left eye (oculus sinister)",
  OU: "Both eyes (oculus uterque)",
  PED: "Pigment epithelial detachment",
  PDR: "Proliferative diabetic retinopathy",
  NPDR: "Non-proliferative diabetic retinopathy",
  PPV: "Pars plana vitrectomy",
  PR: "Pneumatic retinopexy",
  PRP: "Pan-retinal photocoagulation",
  PVD: "Posterior vitreous detachment",
  RAPD: "Relative afferent pupillary defect",
  RD: "Retinal detachment",
  RPE: "Retinal pigment epithelium",
  RT: "Retinal tear",
  SB: "Scleral buckle",
  SLE: "Slit lamp exam",
  SRF: "Subretinal fluid",
  VMT: "Vitreomacular traction",
};

/** Ordered list of abbreviation tokens, longest-first, so a body
 *  containing e.g. "NPDR" isn't split as "N" + "PDR" when we scan
 *  for hover-help targets. */
export const ABBREVIATION_TOKENS: string[] = Object.keys(ABBREVIATION_HINTS)
  .slice()
  .sort((a, b) => b.length - a.length);

/** Abbreviation-aware search.
 *
 *  Matches against the union of: the shortcut body, the group name,
 *  the tag list, and — crucially — the expanded meaning of any
 *  abbreviation whose token appears in the search query. So typing
 *  "retinal detachment" hits everything tagged "rd", and typing "rd"
 *  hits everything whose tags include "rd" OR whose body contains
 *  the phrase "retinal detachment".
 *
 *  Pure function: no DOM, no state — safe to call in filters + tests.
 */
export function clinicalShortcutMatches(
  s: ClinicalShortcut,
  rawQuery: string
): boolean {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return true;

  const haystack =
    (s.body + "\n" + s.group + "\n" + s.tags.join(" ")).toLowerCase();

  if (haystack.includes(query)) return true;

  // If the query is (or contains) an abbreviation we know, also
  // match against its expanded meaning. E.g. `rd` ↔ "retinal
  // detachment".
  for (const abbr of ABBREVIATION_TOKENS) {
    const lowerAbbr = abbr.toLowerCase();
    if (query.includes(lowerAbbr) || lowerAbbr.includes(query)) {
      const meaning = ABBREVIATION_HINTS[abbr].toLowerCase();
      if (haystack.includes(meaning)) return true;
      // Also match if any tag token equals the abbreviation itself.
      if (s.tags.map((t) => t.toLowerCase()).includes(lowerAbbr)) return true;
    }
  }
  return false;
}

/**
 * Split a shortcut body into tokens, wrapping any abbreviation token
 * found in `ABBREVIATION_HINTS` so the UI can render it as
 * `<abbr title="...">` for subtle hover help. Returns a flat array of
 * either plain strings (inert text) or {abbr, meaning} markers.
 *
 * Word-boundary guard: we only wrap when the abbreviation appears as
 * its own token, not as a substring of a longer word (so "IRF" in
 * "INTRAOCULAR IRFACE" — which doesn't exist but defensively — would
 * not match). Case-sensitive because these abbreviations are always
 * uppercase in clinical notes.
 */
export type AbbrSegment = string | { abbr: string; meaning: string };

export function segmentAbbreviations(body: string): AbbrSegment[] {
  // Build a single regex that matches any abbreviation token on a
  // word boundary. We escape a few chars that appear in the sheet
  // (slash, ampersand) so `C/D` and `D&Q` survive.
  const escaped = ABBREVIATION_TOKENS.map((t) =>
    t.replace(/[.*+?^${}()|[\]\\/&]/g, "\\$&")
  );
  // Use lookarounds to avoid matching inside longer alpha tokens;
  // allow trailing punctuation/whitespace. `\b` alone doesn't work
  // for tokens that contain a slash like `C/D`.
  const pattern = new RegExp(
    `(^|[^A-Za-z0-9])(${escaped.join("|")})(?=[^A-Za-z0-9]|$)`,
    "g"
  );

  const out: AbbrSegment[] = [];
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(body)) !== null) {
    const [, leading, token] = m;
    const matchStart = m.index + leading.length;
    if (matchStart > lastIndex) out.push(body.slice(lastIndex, matchStart));
    const meaning = ABBREVIATION_HINTS[token];
    out.push({ abbr: token, meaning });
    lastIndex = matchStart + token.length;
  }
  if (lastIndex < body.length) out.push(body.slice(lastIndex));
  return out;
}

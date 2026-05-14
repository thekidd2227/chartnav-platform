// apps/web/src/specialtyTemplates.ts
//
// Specialty note skeletons that compose existing CLINICAL_SHORTCUTS
// into a multi-section first-draft block a clinician can drop into a
// note in one gesture, then fill in the `___` blanks.
//
// Design intent:
//   - These are NOT diagnostic suggestions, treatment recommendations,
//     or generated content. They are **operator-authored bundles** of
//     existing shortcuts identified by stable id.
//   - A template references CLINICAL_SHORTCUTS by `id`. If a referenced
//     id is removed or renamed, `resolveSpecialtyTemplate()` returns a
//     warning entry so the UI can surface the gap without crashing.
//   - The output is always a deterministic plain-text block. No AI,
//     no network, no per-user state. Pure function.
//   - Templates carry a `role` hint (`clinician` today) so future
//     role-aware surfacing can filter them per dashboard.
//   - Templates carry a `visitType` ("follow-up" / "new-patient" /
//     "post-op" / "monitoring") so the picker can group them by
//     visit kind without hard-coding labels in the UI.
//
// Adding a template:
//   1. Add an entry to SPECIALTY_TEMPLATES below.
//   2. Reference shortcut ids that exist in clinicalShortcuts.ts.
//   3. Add a test in specialtyTemplates.test.ts asserting that every
//      referenced shortcut id resolves (no orphan ids).
//
// What this file does NOT do:
//   - does not call any API
//   - does not persist user-specific state
//   - does not generate or recommend treatment

import {
  CLINICAL_SHORTCUTS,
  type ClinicalShortcut,
  type ClinicalShortcutGroup,
} from "./clinicalShortcuts";

export type SpecialtyTemplateRole = "clinician";

export type SpecialtyTemplateVisitType =
  | "follow-up"
  | "new-patient"
  | "post-op"
  | "monitoring";

export type SpecialtyTemplateSpecialty =
  | "retina"
  | "glaucoma"
  | "cornea"
  | "cataract"
  | "oculoplastics";

export interface SpecialtyTemplate {
  /** Stable string id — used in tests + audit-log payloads. Never a
   *  DB id. */
  id: string;
  /** Display label rendered in the picker. */
  label: string;
  /** Short operator-facing description. */
  description: string;
  /** Specialty grouping for the picker filter chips. */
  specialty: SpecialtyTemplateSpecialty;
  /** Visit-kind grouping for the picker filter chips. */
  visitType: SpecialtyTemplateVisitType;
  /** Role this template is exposed to. The Phase 20C role-aware
   *  dashboards treat front-desk / technician / reviewer / admin
   *  differently from clinician; for now every template is
   *  clinician-only. */
  role: SpecialtyTemplateRole;
  /** Ordered list of section headers + referenced shortcut ids.
   *  Each section header renders as a markdown-style line and is
   *  followed by the body of the referenced shortcuts, in order.
   *  Empty sections are allowed (rendered as a header only) so the
   *  clinician can drop free-form text underneath. */
  sections: { header: string; shortcutIds: string[] }[];
  /** Optional default trailing line that closes the template (e.g.,
   *  "Follow-up scheduled in ___ weeks per provider plan."). */
  trailer?: string;
}

/**
 * Library of specialty templates. Ordered so the picker can render
 * them in a stable sequence. Every shortcut id below is asserted to
 * exist by `specialtyTemplates.test.ts`.
 */
export const SPECIALTY_TEMPLATES: SpecialtyTemplate[] = [
  // -------- Retina --------
  {
    id: "retina-dr-followup",
    label: "Diabetic retinopathy follow-up",
    description:
      "Skeleton for an established DR / DME monitoring follow-up "
      + "visit. Compose with retina tracking + imaging metadata as "
      + "needed.",
    specialty: "retina",
    visitType: "follow-up",
    role: "clinician",
    sections: [
      { header: "Findings", shortcutIds: ["dm-01", "dm-02"] },
      { header: "Imaging review", shortcutIds: ["dm-03"] },
      { header: "Plan", shortcutIds: ["dm-04", "dm-05"] },
    ],
    trailer:
      "Patient-friendly summary draft pending provider review. "
      + "Follow-up window ___ weeks.",
  },
  {
    id: "retina-pvd-acute",
    label: "Acute PVD evaluation",
    description:
      "Skeleton for an acute symptomatic PVD evaluation — flashes / "
      + "floaters work-up with scleral depressed exam.",
    specialty: "retina",
    visitType: "new-patient",
    role: "clinician",
    sections: [
      { header: "History / context", shortcutIds: ["pvd-01"] },
      { header: "Exam findings", shortcutIds: ["pvd-02", "pvd-03"] },
    ],
    trailer:
      "Return precautions reviewed. Follow-up in ___ weeks unless new "
      + "symptoms.",
  },
  {
    id: "retina-amd-followup",
    label: "Wet/Dry AMD monitoring follow-up",
    description:
      "Skeleton for an AMD follow-up — compose with anti-VEGF "
      + "history captured elsewhere; this template never sets "
      + "dosing or frequency.",
    specialty: "retina",
    visitType: "monitoring",
    role: "clinician",
    sections: [
      { header: "Findings", shortcutIds: ["amd-01", "amd-02"] },
      { header: "Imaging review", shortcutIds: ["amd-03"] },
    ],
    trailer:
      "Anti-VEGF dosing remains provider-determined. Next visit ___ "
      + "weeks per provider plan.",
  },
  {
    id: "retina-postop-injection",
    label: "Post-injection / post-vitrectomy visit",
    description:
      "Skeleton for a post-procedure check after intravitreal "
      + "injection or vitrectomy.",
    specialty: "retina",
    visitType: "post-op",
    role: "clinician",
    sections: [
      { header: "Post-procedure status", shortcutIds: ["post-01", "post-02"] },
      { header: "Exam", shortcutIds: ["post-03", "post-04"] },
      { header: "Plan", shortcutIds: ["post-05"] },
    ],
    trailer: "Patient instructed on return precautions.",
  },

  // -------- Glaucoma --------
  {
    id: "glaucoma-oag-monitoring",
    label: "Open-angle glaucoma monitoring follow-up",
    description:
      "Skeleton for an OAG monitoring visit — IOP trend, exam, "
      + "imaging review. Does not adjust medications.",
    specialty: "glaucoma",
    visitType: "follow-up",
    role: "clinician",
    sections: [
      { header: "Interval history", shortcutIds: ["glc-01"] },
      { header: "Exam", shortcutIds: ["glc-02", "glc-03"] },
      { header: "Imaging / VF review", shortcutIds: ["glc-04", "glc-05"] },
      { header: "Plan", shortcutIds: ["glc-06"] },
    ],
    trailer:
      "IOP target, medication regimen, and surgical decisions remain "
      + "provider-determined.",
  },

  // -------- Cornea --------
  {
    id: "cornea-anterior-segment-eval",
    label: "Cornea / anterior segment evaluation",
    description:
      "Skeleton for a cornea or anterior segment evaluation. Compose "
      + "with slit-lamp findings; this template never grades severity.",
    specialty: "cornea",
    visitType: "new-patient",
    role: "clinician",
    sections: [
      { header: "Exam", shortcutIds: ["cor-01", "cor-02", "cor-03"] },
      { header: "Impression / plan", shortcutIds: ["cor-04"] },
    ],
    trailer:
      "Severity grading and treatment plan remain provider-determined.",
  },
  {
    id: "cornea-postop-followup",
    label: "Cornea post-op follow-up",
    description:
      "Skeleton for a cornea post-procedure follow-up — graft / "
      + "PKP / DSAEK / CXL.",
    specialty: "cornea",
    visitType: "post-op",
    role: "clinician",
    sections: [
      { header: "Post-procedure status", shortcutIds: ["cor-05"] },
      { header: "Plan", shortcutIds: ["cor-06"] },
    ],
  },

  // -------- Cataract --------
  {
    id: "cataract-postop-pseudophakia",
    label: "Cataract post-op pseudophakia follow-up",
    description:
      "Skeleton for a routine post-cataract-surgery follow-up. "
      + "Does not select IOL power or set anti-inflammatory regimen.",
    specialty: "cataract",
    visitType: "post-op",
    role: "clinician",
    // Cataract follow-up shortcuts live under the cornea/anterior-
    // segment group today; compose two cornea entries that capture
    // anterior-segment status without overlapping retina work.
    sections: [
      { header: "Post-op status", shortcutIds: ["cor-05", "cor-06"] },
    ],
    trailer:
      "IOL position stable per exam. Post-op drop regimen remains "
      + "provider-determined.",
  },

  // -------- Oculoplastics --------
  {
    id: "oculoplastics-lid-eval",
    label: "Oculoplastics lid / adnexa evaluation",
    description:
      "Skeleton for a lid / adnexa evaluation visit — entropion, "
      + "ectropion, ptosis, chalazion, dermatochalasis.",
    specialty: "oculoplastics",
    visitType: "new-patient",
    role: "clinician",
    sections: [
      { header: "Exam", shortcutIds: ["ocp-01", "ocp-02", "ocp-03"] },
      { header: "Impression / plan", shortcutIds: ["ocp-04"] },
    ],
    trailer:
      "Surgical candidacy and timing remain provider-determined.",
  },
  {
    id: "oculoplastics-postop-blepharoplasty",
    label: "Oculoplastics post-op follow-up",
    description:
      "Skeleton for a post-blepharoplasty or lid procedure "
      + "follow-up.",
    specialty: "oculoplastics",
    visitType: "post-op",
    role: "clinician",
    sections: [
      { header: "Post-procedure status", shortcutIds: ["ocp-05", "ocp-06"] },
    ],
  },
];

export const SPECIALTY_TEMPLATE_SPECIALTIES: SpecialtyTemplateSpecialty[] = [
  "retina",
  "glaucoma",
  "cornea",
  "cataract",
  "oculoplastics",
];

export const SPECIALTY_TEMPLATE_VISIT_TYPES: SpecialtyTemplateVisitType[] = [
  "follow-up",
  "new-patient",
  "post-op",
  "monitoring",
];

export interface ResolvedSpecialtyTemplate {
  template: SpecialtyTemplate;
  sections: {
    header: string;
    shortcuts: ClinicalShortcut[];
    /** ids that could not be resolved against the live shortcut
     *  library. UI should surface this as a warning chip; never as
     *  a silent omission. */
    missingIds: string[];
  }[];
}

const SHORTCUT_BY_ID = new Map<string, ClinicalShortcut>(
  CLINICAL_SHORTCUTS.map((s) => [s.id, s]),
);

/** Resolve a template against the live shortcut library. Pure
 *  function. The returned object preserves the template ordering and
 *  surfaces any missing-id gaps for the UI to render. */
export function resolveSpecialtyTemplate(
  template: SpecialtyTemplate,
): ResolvedSpecialtyTemplate {
  const sections = template.sections.map((s) => {
    const shortcuts: ClinicalShortcut[] = [];
    const missingIds: string[] = [];
    for (const id of s.shortcutIds) {
      const found = SHORTCUT_BY_ID.get(id);
      if (found) shortcuts.push(found);
      else missingIds.push(id);
    }
    return { header: s.header, shortcuts, missingIds };
  });
  return { template, sections };
}

/** Render a resolved template into the plain-text block the clinician
 *  drops into the note draft. Each section becomes a header line
 *  followed by the joined shortcut bodies; `___` blanks are preserved
 *  so the clinician fills them in after insertion (handled by the
 *  existing `firstBlankOffset` / `nextBlankAfter` helpers). */
export function renderSpecialtyTemplate(
  resolved: ResolvedSpecialtyTemplate,
): string {
  const out: string[] = [];
  for (const section of resolved.sections) {
    if (section.shortcuts.length === 0 && section.missingIds.length === 0) {
      // Empty section: still render the header so the clinician has
      // a labelled placeholder to type into.
      out.push(section.header + ":");
      out.push("___");
      out.push("");
      continue;
    }
    out.push(section.header + ":");
    for (const s of section.shortcuts) {
      out.push(s.body);
    }
    if (section.missingIds.length > 0) {
      // Surface the gap inline so the clinician (and any reviewer)
      // can see exactly which shortcut id failed to resolve.
      out.push(
        "[template gap — unresolved shortcut id(s): "
          + section.missingIds.join(", ")
          + "]",
      );
    }
    out.push("");
  }
  if (resolved.template.trailer) {
    out.push(resolved.template.trailer);
  }
  // Trim trailing blank lines so the inserted block doesn't push a
  // stack of empty lines into the draft.
  while (out.length > 0 && out[out.length - 1] === "") out.pop();
  return out.join("\n");
}

/** Filter templates by specialty + visit type. Either filter is
 *  optional. Used by the picker. */
export function filterSpecialtyTemplates(
  templates: SpecialtyTemplate[],
  filters: {
    specialty?: SpecialtyTemplateSpecialty;
    visitType?: SpecialtyTemplateVisitType;
    role?: SpecialtyTemplateRole;
  },
): SpecialtyTemplate[] {
  return templates.filter((t) => {
    if (filters.specialty && t.specialty !== filters.specialty) return false;
    if (filters.visitType && t.visitType !== filters.visitType) return false;
    if (filters.role && t.role !== filters.role) return false;
    return true;
  });
}

/** Reverse map: which specialty groups in the underlying shortcut
 *  library does a template touch? Useful for the picker to show
 *  "uses: Glaucoma, Cornea / anterior segment" so the clinician
 *  knows what they're about to drop in. */
export function specialtyTemplateShortcutGroups(
  template: SpecialtyTemplate,
): ClinicalShortcutGroup[] {
  const resolved = resolveSpecialtyTemplate(template);
  const groups = new Set<ClinicalShortcutGroup>();
  for (const section of resolved.sections) {
    for (const s of section.shortcuts) groups.add(s.group);
  }
  return Array.from(groups);
}

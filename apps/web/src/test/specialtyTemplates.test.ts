// specialtyTemplates.test.ts
//
// Pure-function tests for the specialty-template module. Verifies:
//   1. every template references shortcut ids that exist in the
//      live CLINICAL_SHORTCUTS library (no orphan ids in the
//      shipped templates);
//   2. resolveSpecialtyTemplate() surfaces missing-id gaps without
//      crashing when an id is renamed;
//   3. renderSpecialtyTemplate() produces a deterministic plain-
//      text block, preserves __underscore__ blanks, and trims
//      trailing whitespace;
//   4. filterSpecialtyTemplates() respects specialty + visitType +
//      role filters;
//   5. every shipped template uses the clinician role + a known
//      specialty + a known visit type (no drift in the enums);
//   6. specialtyTemplateShortcutGroups() returns the set of
//      underlying shortcut groups touched.

import { describe, expect, it } from "vitest";
import { CLINICAL_SHORTCUTS } from "../clinicalShortcuts";
import {
  filterSpecialtyTemplates,
  renderSpecialtyTemplate,
  resolveSpecialtyTemplate,
  SPECIALTY_TEMPLATES,
  SPECIALTY_TEMPLATE_SPECIALTIES,
  SPECIALTY_TEMPLATE_VISIT_TYPES,
  specialtyTemplateShortcutGroups,
  type SpecialtyTemplate,
} from "../specialtyTemplates";

const KNOWN_SHORTCUT_IDS = new Set(CLINICAL_SHORTCUTS.map((s) => s.id));

describe("specialtyTemplates — shape + integrity", () => {
  it("ships at least one template per specialty", () => {
    for (const sp of SPECIALTY_TEMPLATE_SPECIALTIES) {
      const found = SPECIALTY_TEMPLATES.filter((t) => t.specialty === sp);
      expect(found.length).toBeGreaterThanOrEqual(1);
    }
  });

  it("every template uses a known specialty + visitType + clinician role", () => {
    for (const t of SPECIALTY_TEMPLATES) {
      expect(SPECIALTY_TEMPLATE_SPECIALTIES).toContain(t.specialty);
      expect(SPECIALTY_TEMPLATE_VISIT_TYPES).toContain(t.visitType);
      expect(t.role).toBe("clinician");
      expect(t.label.length).toBeGreaterThan(0);
      expect(t.description.length).toBeGreaterThan(0);
      expect(t.sections.length).toBeGreaterThanOrEqual(1);
    }
  });

  it("every shortcut id referenced by every template resolves", () => {
    const orphans: { templateId: string; missingId: string }[] = [];
    for (const t of SPECIALTY_TEMPLATES) {
      for (const section of t.sections) {
        for (const sid of section.shortcutIds) {
          if (!KNOWN_SHORTCUT_IDS.has(sid)) {
            orphans.push({ templateId: t.id, missingId: sid });
          }
        }
      }
    }
    expect(orphans).toEqual([]);
  });

  it("every template has a unique stable id", () => {
    const ids = SPECIALTY_TEMPLATES.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("specialtyTemplates — resolveSpecialtyTemplate", () => {
  it("resolves all referenced ids when every id exists", () => {
    const sample = SPECIALTY_TEMPLATES[0];
    const resolved = resolveSpecialtyTemplate(sample);
    expect(resolved.template).toBe(sample);
    for (const section of resolved.sections) {
      expect(section.missingIds).toEqual([]);
      expect(section.shortcuts.length).toBe(
        sample.sections.find((s) => s.header === section.header)!.shortcutIds.length,
      );
    }
  });

  it("surfaces missing ids without dropping the section", () => {
    const fake: SpecialtyTemplate = {
      id: "test-orphan",
      label: "Test orphan",
      description: "test",
      specialty: "retina",
      visitType: "follow-up",
      role: "clinician",
      sections: [
        { header: "Findings", shortcutIds: ["dm-01", "nope-99"] },
      ],
    };
    const resolved = resolveSpecialtyTemplate(fake);
    expect(resolved.sections).toHaveLength(1);
    expect(resolved.sections[0].shortcuts.map((s) => s.id)).toEqual(["dm-01"]);
    expect(resolved.sections[0].missingIds).toEqual(["nope-99"]);
  });
});

describe("specialtyTemplates — renderSpecialtyTemplate", () => {
  it("renders headers + bodies + trailer in order, preserving blanks", () => {
    const fake: SpecialtyTemplate = {
      id: "test-render",
      label: "Test render",
      description: "test",
      specialty: "retina",
      visitType: "follow-up",
      role: "clinician",
      sections: [
        { header: "Findings", shortcutIds: ["pvd-01"] },
        { header: "Plan", shortcutIds: [] },
      ],
      trailer: "Follow-up in ___ weeks.",
    };
    const resolved = resolveSpecialtyTemplate(fake);
    const out = renderSpecialtyTemplate(resolved);
    expect(out).toMatch(/^Findings:/m);
    expect(out).toMatch(/^Plan:/m);
    expect(out).toContain("Acute PVD"); // pvd-01 body
    expect(out).toContain("___"); // blank preserved
    expect(out.endsWith(".")).toBe(true); // trailer line is the last
    expect(out).toMatch(/Follow-up in ___ weeks\.\s*$/);
  });

  it("annotates missing ids inline rather than failing silently", () => {
    const fake: SpecialtyTemplate = {
      id: "test-missing-render",
      label: "x",
      description: "x",
      specialty: "retina",
      visitType: "follow-up",
      role: "clinician",
      sections: [
        { header: "Findings", shortcutIds: ["pvd-01", "ghost-01"] },
      ],
    };
    const out = renderSpecialtyTemplate(resolveSpecialtyTemplate(fake));
    expect(out).toContain("ghost-01");
    expect(out).toMatch(/template gap/i);
  });
});

describe("specialtyTemplates — filterSpecialtyTemplates", () => {
  it("filters by specialty", () => {
    const retina = filterSpecialtyTemplates(SPECIALTY_TEMPLATES, {
      specialty: "retina",
    });
    expect(retina.every((t) => t.specialty === "retina")).toBe(true);
    expect(retina.length).toBeGreaterThanOrEqual(1);
  });
  it("filters by visit type", () => {
    const postOp = filterSpecialtyTemplates(SPECIALTY_TEMPLATES, {
      visitType: "post-op",
    });
    expect(postOp.every((t) => t.visitType === "post-op")).toBe(true);
    expect(postOp.length).toBeGreaterThanOrEqual(1);
  });
  it("combines specialty + visitType + role filters", () => {
    const out = filterSpecialtyTemplates(SPECIALTY_TEMPLATES, {
      specialty: "retina",
      visitType: "follow-up",
      role: "clinician",
    });
    expect(out.every((t) =>
      t.specialty === "retina" && t.visitType === "follow-up" && t.role === "clinician"
    )).toBe(true);
  });
  it("returns an empty array for an unknown combination", () => {
    // No "retina + new-patient" in the seeded set besides the acute
    // PVD evaluation; this asserts the filter is exact, not fuzzy.
    const out = filterSpecialtyTemplates(SPECIALTY_TEMPLATES, {
      specialty: "cataract",
      visitType: "new-patient",
    });
    expect(out).toEqual([]);
  });
});

describe("specialtyTemplates — specialtyTemplateShortcutGroups", () => {
  it("returns the distinct shortcut groups a template touches", () => {
    const retina = SPECIALTY_TEMPLATES.find((t) => t.id === "retina-dr-followup")!;
    const groups = specialtyTemplateShortcutGroups(retina);
    // DR / DME shortcuts (`dm-*`) all live in the
    // "Diabetic retinopathy / DME" group.
    expect(groups).toContain("Diabetic retinopathy / DME");
    expect(groups.length).toBeGreaterThanOrEqual(1);
  });
});

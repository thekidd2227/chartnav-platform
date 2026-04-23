"""Ophthalmology specialty bundles + support-rule seed.

Bundles are ICD-10-CM code *patterns* that the UI surfaces as quick-
picks inside each subspecialty. Patterns use LIKE semantics (``%``
wildcard). The SQL query expands a pattern into concrete codes at
search time against the currently-active version.

Support rules are advisory workflow hints surfaced alongside a
selected code. They are explicitly NOT reimbursement rules, coverage
rules, or payer policy. The source_reference column captures where
the specificity prompt originates; we use CDC Official Guidelines +
AAO Coding Coach-style clinical consensus language without reproducing
proprietary text.
"""
from __future__ import annotations

from typing import Iterable


ALL_SPECIALTY_TAGS: list[str] = [
    "retina",
    "glaucoma",
    "cataract",
    "cornea",
    "oculoplastics",
    "general",
]


# Each bundle lists the ICD-10-CM pattern + a short label shown in UI.
# The patterns are bulk-expanded at query time via a LIKE clause
# against normalized_code.
SPECIALTY_BUNDLES: dict[str, list[dict]] = {
    "retina": [
        {"label": "Age-related macular degeneration", "pattern": "H35.3%"},
        {"label": "Diabetic retinopathy",             "pattern": "E11.3%"},
        {"label": "Retinal detachment / break",       "pattern": "H33%"},
        {"label": "Retinal vein occlusion",           "pattern": "H34.8%"},
        {"label": "Retinal artery occlusion",         "pattern": "H34.0%"},
        {"label": "Macular hole",                     "pattern": "H35.34%"},
        {"label": "Epiretinal membrane",              "pattern": "H35.37%"},
    ],
    "glaucoma": [
        {"label": "Primary open-angle glaucoma",      "pattern": "H40.11%"},
        {"label": "Primary angle-closure glaucoma",   "pattern": "H40.2%"},
        {"label": "Glaucoma suspect",                 "pattern": "H40.0%"},
        {"label": "Pigmentary glaucoma",              "pattern": "H40.13%"},
        {"label": "Capsular glaucoma (pseudoexfoliation)", "pattern": "H40.14%"},
        {"label": "Secondary glaucoma",               "pattern": "H40.5%"},
        {"label": "Ocular hypertension",              "pattern": "H40.05%"},
    ],
    "cataract": [
        {"label": "Senile (age-related) cataract",    "pattern": "H25%"},
        {"label": "Other cataract",                   "pattern": "H26%"},
        {"label": "Aphakia",                          "pattern": "H27.0%"},
        {"label": "Pseudophakia (status)",            "pattern": "Z96.1"},
    ],
    "cornea": [
        {"label": "Keratitis",                        "pattern": "H16%"},
        {"label": "Corneal ulcer",                    "pattern": "H16.0%"},
        {"label": "Corneal scars / opacities",        "pattern": "H17%"},
        {"label": "Keratoconus",                      "pattern": "H18.6%"},
        {"label": "Corneal edema",                    "pattern": "H18.2%"},
        {"label": "Dry eye syndrome",                 "pattern": "H04.12%"},
    ],
    "oculoplastics": [
        {"label": "Ptosis of eyelid",                 "pattern": "H02.40%"},
        {"label": "Ectropion of eyelid",              "pattern": "H02.1%"},
        {"label": "Entropion of eyelid",              "pattern": "H02.0%"},
        {"label": "Dermatochalasis",                  "pattern": "H02.83%"},
        {"label": "Dacryocystitis",                   "pattern": "H04.3%"},
        {"label": "Nasolacrimal duct obstruction",    "pattern": "H04.55%"},
    ],
    "general": [
        {"label": "Refractive error",                 "pattern": "H52%"},
        {"label": "Visual disturbance",               "pattern": "H53%"},
        {"label": "Blindness / low vision",           "pattern": "H54%"},
        {"label": "Conjunctivitis",                   "pattern": "H10%"},
        {"label": "Blepharitis",                      "pattern": "H01.0%"},
        {"label": "Encounter for eye exam",           "pattern": "Z01.0%"},
    ],
}


# Seed rules installed on first ingestion. The `workflow_area` takes
# one of: specificity_prompt, claim_support_hint.
DEFAULT_SUPPORT_RULES: list[dict] = [
    # -------- GLAUCOMA ------------------------------------------------
    {
        "specialty_tag": "glaucoma",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "H40.11%",
        "advisory_hint": "Primary open-angle glaucoma: document laterality (right/left/bilateral) and severity stage (mild, moderate, severe, or indeterminate) to reach the billable 7-character code.",
        "specificity_prompt": "Laterality: OD / OS / bilateral\nStage: mild / moderate / severe / indeterminate",
        "source_reference": "CDC Official ICD-10-CM Guidelines, Section I.C.7.a",
    },
    {
        "specialty_tag": "glaucoma",
        "workflow_area": "claim_support_hint",
        "diagnosis_code_pattern": "H40%",
        "advisory_hint": "If visual fields (92083) or SCODI/OCT optic nerve (92133) were performed at this visit, ensure the medical-necessity link between glaucoma diagnosis and the testing is captured in the assessment or plan.",
        "specificity_prompt": None,
        "source_reference": "CMS Local Coverage Determinations for 92083/92133 (see payer policy for exact criteria)",
    },
    # -------- RETINA --------------------------------------------------
    {
        "specialty_tag": "retina",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "H35.3%",
        "advisory_hint": "Age-related macular degeneration: specify dry/wet, stage (early, intermediate, advanced), and laterality (right, left, or bilateral).",
        "specificity_prompt": "Form: dry (nonexudative) / wet (exudative)\nStage: early / intermediate / advanced atrophic / advanced neovascular\nLaterality: OD / OS / bilateral",
        "source_reference": "CDC Official ICD-10-CM Guidelines, Section I.C.7",
    },
    {
        "specialty_tag": "retina",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "E11.3%",
        "advisory_hint": "Diabetes with ophthalmic manifestations: specify the retinopathy manifestation (non-proliferative with severity, proliferative, or macular edema) and laterality.",
        "specificity_prompt": "Manifestation: NPDR mild / moderate / severe / PDR / macular edema\nLaterality: OD / OS / bilateral",
        "source_reference": "CDC Official ICD-10-CM Guidelines, Section I.C.4",
    },
    # -------- CATARACT ------------------------------------------------
    {
        "specialty_tag": "cataract",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "H25%",
        "advisory_hint": "Senile cataract: specify the cataract type (nuclear sclerotic, cortical, posterior subcapsular, combined) and laterality.",
        "specificity_prompt": "Type: nuclear sclerotic / cortical / posterior subcapsular / combined\nLaterality: OD / OS / bilateral",
        "source_reference": "CDC Official ICD-10-CM Guidelines",
    },
    # -------- CORNEA --------------------------------------------------
    {
        "specialty_tag": "cornea",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "H16.0%",
        "advisory_hint": "Corneal ulcer: specify ulcer type (central, marginal, ring, with hypopyon, perforated) and laterality.",
        "specificity_prompt": "Type: central / marginal / ring / with hypopyon / perforated\nLaterality: OD / OS / bilateral",
        "source_reference": "CDC Official ICD-10-CM Guidelines",
    },
    # -------- OCULOPLASTICS -------------------------------------------
    {
        "specialty_tag": "oculoplastics",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "H02.40%",
        "advisory_hint": "Ptosis of eyelid: specify severity (mechanical, myogenic, paralytic, neurogenic) and laterality. If surgical repair is planned, documentation should also capture margin-reflex distance and visual-field obstruction measurements.",
        "specificity_prompt": "Type: mechanical / myogenic / paralytic / neurogenic\nLaterality: right / left / bilateral\nFunctional impact: MRD1, visual-field obstruction",
        "source_reference": "CDC Official ICD-10-CM Guidelines; AAO clinical coding guidance",
    },
    # -------- GENERAL -------------------------------------------------
    {
        "specialty_tag": "general",
        "workflow_area": "specificity_prompt",
        "diagnosis_code_pattern": "Z01.0%",
        "advisory_hint": "Encounter for examination of eyes and vision: pick the encounter subtype (routine, with abnormal findings, following failed vision screening) and document whether dilation was performed for level of exam.",
        "specificity_prompt": "Subtype: routine / with abnormal findings / following failed vision screening\nExam level: intermediate / comprehensive (document dilation if comprehensive)",
        "source_reference": "CDC Official ICD-10-CM Guidelines, Section IV",
    },
]


def list_specialty_bundles() -> list[dict]:
    """Return the full set of specialty bundles as a list of
    ``{tag, label, pattern}`` triples. Stable output shape for the
    ``GET /clinical-coding/specialties`` endpoint."""
    out: list[dict] = []
    for tag in ALL_SPECIALTY_TAGS:
        for entry in SPECIALTY_BUNDLES.get(tag, []):
            out.append({
                "specialty_tag": tag,
                "label": entry["label"],
                "pattern": entry["pattern"],
            })
    return out


def specialty_bundle_codes(tag: str) -> list[dict]:
    """Return bundle entries for one specialty tag."""
    return [
        {"specialty_tag": tag, "label": e["label"], "pattern": e["pattern"]}
        for e in SPECIALTY_BUNDLES.get(tag, [])
    ]


def seed_support_rules(conn) -> int:
    """Idempotent seed of the advisory support rules. Returns the
    number of rows inserted on this call (0 if already seeded)."""
    from sqlalchemy import text
    existing = conn.execute(
        text("SELECT COUNT(*) FROM ophthalmology_support_rules")
    ).scalar() or 0
    if existing >= len(DEFAULT_SUPPORT_RULES):
        return 0
    inserted = 0
    for rule in DEFAULT_SUPPORT_RULES:
        dup = conn.execute(
            text(
                "SELECT id FROM ophthalmology_support_rules "
                "WHERE specialty_tag = :t AND workflow_area = :w "
                "AND diagnosis_code_pattern = :p"
            ),
            {
                "t": rule["specialty_tag"],
                "w": rule["workflow_area"],
                "p": rule["diagnosis_code_pattern"],
            },
        ).first()
        if dup:
            continue
        conn.execute(
            text(
                "INSERT INTO ophthalmology_support_rules "
                "(specialty_tag, workflow_area, diagnosis_code_pattern, "
                "advisory_hint, specificity_prompt, source_reference, is_active) "
                "VALUES (:t, :w, :p, :a, :s, :r, 1)"
            ),
            {
                "t": rule["specialty_tag"],
                "w": rule["workflow_area"],
                "p": rule["diagnosis_code_pattern"],
                "a": rule["advisory_hint"],
                "s": rule["specificity_prompt"],
                "r": rule["source_reference"],
            },
        )
        inserted += 1
    return inserted


def hints_for_code(conn, code: str, *, version_id: int | None = None) -> list[dict]:
    """Return advisory support hints matching the given code. Uses
    simple pattern matching (``H40.11%`` style). Multiple hints are
    allowed per code; the UI renders all of them."""
    from sqlalchemy import text
    rows = conn.execute(
        text(
            "SELECT id, specialty_tag, workflow_area, diagnosis_code_pattern, "
            "advisory_hint, specificity_prompt, source_reference "
            "FROM ophthalmology_support_rules WHERE is_active = 1"
        )
    ).mappings().all()
    out: list[dict] = []
    for r in rows:
        pattern = r["diagnosis_code_pattern"]
        # SQL-like pattern → python regex-ish match. % ≡ any suffix.
        if pattern.endswith("%"):
            if code.startswith(pattern[:-1]):
                out.append(dict(r))
        elif code == pattern:
            out.append(dict(r))
    return out

"""Phase A item 1 — Ophthalmology encounter templates.

Spec: docs/chartnav/closure/PHASE_A_Ophthalmology_Encounter_Templates.md

This module is the single source of truth for the four first-party
templates ChartNav ships in Phase A. Every consumer (the create-
encounter route, the SOAP extractor's missing-findings logic, the
PM/RCM handoff export, the frontend selector) reads from
``TEMPLATES`` via the helpers below.

Truth limitations (kept verbatim from the spec):
- Templates are NOT clinically validated until the practicing-
  ophthalmologist advisor sign-off is recorded under
  ``docs/chartnav/clinical/template_review.md``. UI surfaces an
  advisor-review banner until then.
- No CPT is auto-assigned. ``suggested_cpt`` is a list the provider
  picks from; nothing is auto-billed.
- Templates cover medical retina, primary open-angle glaucoma
  patterns, routine cataract evaluation, and comprehensive exam.
  They do NOT cover surgical operative notes, pediatric strabismus,
  neuro-ophthalmic pattern VEP, or oculoplastics.
- No E/M level scoring; level selection remains the provider's call.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


DEFAULT_TEMPLATE_KEY = "general_ophthalmology"


@dataclass(frozen=True)
class Template:
    """One ChartNav-curated encounter template definition."""
    key: str
    display_name: str
    sections: list[str]
    required_findings: list[str]
    suggested_cpt: list[str]
    icd10_relevance: list[str]
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------
# Template catalog
# ---------------------------------------------------------------------
# Each `sections` list defines the order the draft note renders sections.
# `required_findings` drives the `missing_data_flags` list emitted by the
# SOAP extractor when an expected field is absent at sign time.
# `suggested_cpt` and `icd10_relevance` are read-only suggestions the
# provider picks from in the handoff bundle; they are never auto-billed.

TEMPLATES: dict[str, Template] = {
    "retina": Template(
        key="retina",
        display_name="Retina",
        sections=[
            "cc", "hpi",
            "exam.va", "exam.iop", "exam.pupils",
            "exam.slit_lamp", "exam.fundus",
            "imaging.oct_macula",
            "assessment", "plan", "follow_up",
        ],
        required_findings=[
            "va_od", "va_os",
            "iop_od", "iop_os",
            "fundus_od", "fundus_os",
            "oct_macula",
        ],
        suggested_cpt=["92014", "92134", "92250"],
        icd10_relevance=["H35.3", "H35.81", "E11.3"],
        description=(
            "Medical retina focus — AMD, diabetic retinopathy, retinal "
            "vein occlusion, macular edema."
        ),
    ),
    "glaucoma": Template(
        key="glaucoma",
        display_name="Glaucoma",
        sections=[
            "cc", "hpi",
            "exam.va", "exam.iop", "exam.pupils",
            "exam.slit_lamp", "exam.gonioscopy",
            "exam.disc", "imaging.oct_rnfl",
            "imaging.visual_field",
            "assessment", "plan", "follow_up",
        ],
        required_findings=[
            "va_od", "va_os",
            "iop_od", "iop_os",
            "disc_od", "disc_os",
            "oct_rnfl",
        ],
        suggested_cpt=["92014", "92133", "92083"],
        icd10_relevance=["H40.11", "H40.12", "H40.05"],
        description=(
            "Glaucoma evaluation — IOP, optic disc, OCT RNFL, "
            "and visual field emphasis."
        ),
    ),
    "anterior_segment_cataract": Template(
        key="anterior_segment_cataract",
        display_name="Anterior Segment / Cataract",
        sections=[
            "cc", "hpi",
            "exam.va", "exam.iop", "exam.pupils",
            "exam.refraction", "exam.slit_lamp",
            "exam.lens_grading",
            "iol_planning",
            "assessment", "plan", "follow_up",
        ],
        required_findings=[
            "va_od", "va_os",
            "iop_od", "iop_os",
            "lens_grade_od", "lens_grade_os",
            "refraction_od", "refraction_os",
        ],
        suggested_cpt=["92014", "92020", "92136"],
        icd10_relevance=["H25.13", "H25.11", "H26.49"],
        description=(
            "Anterior segment evaluation focused on cataract grading, "
            "refraction, and IOL planning."
        ),
    ),
    "general_ophthalmology": Template(
        key="general_ophthalmology",
        display_name="General Ophthalmology",
        sections=[
            "cc", "hpi",
            "exam.va", "exam.iop", "exam.pupils",
            "exam.slit_lamp", "exam.fundus",
            "assessment", "plan", "follow_up",
        ],
        required_findings=[
            "va_od", "va_os",
            "iop_od", "iop_os",
        ],
        suggested_cpt=["92014", "92012", "92002", "92004"],
        icd10_relevance=["H52.4", "H53.9", "H40.05"],
        description=(
            "Routine comprehensive ophthalmology exam. Default template "
            "when no specialty focus is selected."
        ),
    ),
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def list_templates() -> list[dict]:
    """Return all templates as serializable dicts in stable order."""
    return [TEMPLATES[k].to_dict() for k in sorted(TEMPLATES.keys())]


def get_template(key: str) -> Optional[Template]:
    """Return the template by key. None if unknown."""
    return TEMPLATES.get(key)


def is_valid_template_key(key: str | None) -> bool:
    """True iff key is one of the registered templates."""
    return key in TEMPLATES


def required_findings_for(key: str) -> list[str]:
    """Required-findings list for the given template, or the general
    template's list if the key is unknown (caller decides whether to
    flag the unknown-key as a separate missing flag)."""
    t = TEMPLATES.get(key) or TEMPLATES[DEFAULT_TEMPLATE_KEY]
    return list(t.required_findings)

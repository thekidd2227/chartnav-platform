"""Phase 60 — Structured Vitals & Technician Workup intake service.

This is a *structured intake* surface:

- The technician (or clinician) types vitals + workup fields into a
  form. ChartNav normalises values, calculates BMI if both height and
  weight are present, and emits **review-required warnings** for
  partial / out-of-typical-range data.
- It is **not** diagnosis. Warnings are review prompts, never
  conclusions. The service never emits "hypertensive crisis",
  "fever", "hypoxia", or any treatment / order / referral language.
- It is **not** device integration. Every value is entered by a
  human; no live device sync.
- It is **not** remote patient monitoring.
- Provider review is required. Sign requires explicit attestation.
  Signed rows are immutable (PATCH returns 409).

Lifecycle
---------
draft → entered → reviewed → signed (`superseded` reserved for a
future correction / versioning flow).

- **draft** — created, possibly empty fields; mid-edit.
- **entered** — the technician has captured what they intend to
  capture. Clinician review is now possible.
- **reviewed** — clinician has marked the workup reviewed.
- **signed** — clinician has attested and signed. Immutable.

Audit
-----
The route is responsible for keeping body content out of audit
`detail` strings. This service exposes `build_audit_detail(...)` so
the route emits a metadata-only string (id, status, encounter id,
patient id, warning count). The service itself never writes audit
events.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger("chartnav.vitals")


# ---------------------------------------------------------------------------
# Public lifecycle constants
# ---------------------------------------------------------------------------


class VitalsStatus:
    DRAFT = "draft"
    ENTERED = "entered"
    REVIEWED = "reviewed"
    SIGNED = "signed"
    SUPERSEDED = "superseded"


TERMINAL_STATUSES = frozenset({VitalsStatus.SIGNED, VitalsStatus.SUPERSEDED})

# Allowed inbound transitions for the route-level actions.
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "enter": frozenset({VitalsStatus.DRAFT}),
    "review": frozenset({VitalsStatus.ENTERED}),
    "sign": frozenset({VitalsStatus.REVIEWED}),
}


class VitalsTransitionError(Exception):
    def __init__(self, action: str, current: str) -> None:
        super().__init__(f"action {action!r} not valid from status {current!r}")
        self.action = action
        self.current = current


class VitalsImmutable(Exception):
    def __init__(self, current: str) -> None:
        super().__init__(f"workup is {current!r} and cannot be modified")
        self.current = current


# ---------------------------------------------------------------------------
# Valid enum sets (server-side validation; the route layer also enforces
# these through Pydantic patterns, but defense-in-depth lives here).
# ---------------------------------------------------------------------------


VALID_BP_POSITION = frozenset({"sitting", "standing", "supine", "unknown"})
VALID_BP_SITE = frozenset({"left_arm", "right_arm", "wrist", "other", "unknown"})
VALID_TEMP_UNIT = frozenset({"F", "C"})
VALID_TEMP_SITE = frozenset(
    {"oral", "temporal", "tympanic", "axillary", "rectal", "other", "unknown"}
)
VALID_HEIGHT_UNIT = frozenset({"in", "cm"})
VALID_WEIGHT_UNIT = frozenset({"lb", "kg"})
VALID_IOP_METHOD = frozenset(
    {"applanation", "tonopen", "icare", "other", "unknown"}
)
VALID_DILATION_STATUS = frozenset(
    {"not_dilated", "dilated", "declined", "contraindicated", "unknown"}
)
VALID_SOURCE_TYPES = frozenset(
    {"technician_entry", "clinician_entry", "imported", "demo"}
)


# ---------------------------------------------------------------------------
# BMI calculation
# ---------------------------------------------------------------------------


def calculate_bmi(
    height_value: Optional[float],
    height_unit: Optional[str],
    weight_value: Optional[float],
    weight_unit: Optional[str],
) -> Optional[float]:
    """Return BMI in kg/m^2 rounded to one decimal, or None.

    Accepts (in, cm) for height and (lb, kg) for weight. Returns None
    if either value is missing or non-positive.
    """
    if height_value is None or weight_value is None:
        return None
    try:
        h = float(height_value)
        w = float(weight_value)
    except (TypeError, ValueError):
        return None
    if h <= 0 or w <= 0:
        return None
    hu = (height_unit or "in").lower()
    wu = (weight_unit or "lb").lower()
    # Normalise to metres and kilograms.
    if hu == "in":
        height_m = h * 0.0254
    elif hu == "cm":
        height_m = h * 0.01
    else:
        return None
    if wu == "lb":
        weight_kg = w * 0.45359237
    elif wu == "kg":
        weight_kg = w
    else:
        return None
    if height_m <= 0:
        return None
    bmi = weight_kg / (height_m * height_m)
    return round(bmi, 1)


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------


# Plain "out of typical range" thresholds. These are **review prompts**,
# not clinical thresholds and not diagnoses. The service intentionally
# does NOT say "hypertensive crisis", "fever", "hypoxia" — it says
# "review required".
_BP_SYS_LOW = 80
_BP_SYS_HIGH = 180
_BP_DIA_LOW = 50
_BP_DIA_HIGH = 110
_PULSE_LOW = 40
_PULSE_HIGH = 130
_RR_LOW = 8
_RR_HIGH = 30
_SPO2_LOW = 90
_TEMP_F_LOW = 95.0
_TEMP_F_HIGH = 100.4
_TEMP_C_LOW = 35.0
_TEMP_C_HIGH = 38.0
_PAIN_LOW = 0
_PAIN_HIGH = 10


def _maybe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _maybe_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def generate_warnings(payload: dict[str, Any]) -> list[str]:
    """Produce review-required warnings for partial / out-of-range data.

    Warning messages NEVER include diagnostic language. Each warning
    is a "please confirm" or "please add" or "value outside typical
    range; provider review required" prompt.
    """
    warnings: list[str] = []

    sys = _maybe_int(payload.get("bp_systolic"))
    dia = _maybe_int(payload.get("bp_diastolic"))
    if sys is not None and dia is None:
        warnings.append(
            "Blood pressure systolic captured but diastolic missing; "
            "please add diastolic before signing."
        )
    if dia is not None and sys is None:
        warnings.append(
            "Blood pressure diastolic captured but systolic missing; "
            "please add systolic before signing."
        )
    if (sys is not None or dia is not None) and not payload.get("bp_site"):
        warnings.append(
            "Blood pressure recorded without a site; please specify "
            "site (left_arm / right_arm / wrist / other) before signing."
        )
    if (sys is not None or dia is not None) and not payload.get("bp_position"):
        warnings.append(
            "Blood pressure recorded without a position; please "
            "specify position (sitting / standing / supine) before signing."
        )
    if sys is not None and (sys < _BP_SYS_LOW or sys > _BP_SYS_HIGH):
        warnings.append(
            f"Systolic blood pressure ({sys}) is outside the typical "
            "range; provider review required."
        )
    if dia is not None and (dia < _BP_DIA_LOW or dia > _BP_DIA_HIGH):
        warnings.append(
            f"Diastolic blood pressure ({dia}) is outside the typical "
            "range; provider review required."
        )

    pulse = _maybe_int(payload.get("pulse"))
    if pulse is not None and (pulse < _PULSE_LOW or pulse > _PULSE_HIGH):
        warnings.append(
            f"Pulse ({pulse}) is outside the typical range; provider "
            "review required."
        )

    rr = _maybe_int(payload.get("respiratory_rate"))
    if rr is not None and (rr < _RR_LOW or rr > _RR_HIGH):
        warnings.append(
            f"Respiratory rate ({rr}) is outside the typical range; "
            "provider review required."
        )

    spo2 = _maybe_int(payload.get("oxygen_saturation"))
    if spo2 is not None and (spo2 < 0 or spo2 > 100):
        warnings.append(
            f"Oxygen saturation ({spo2}) is outside the valid 0-100 "
            "range; please re-enter."
        )
    elif spo2 is not None and spo2 < _SPO2_LOW:
        warnings.append(
            f"Oxygen saturation ({spo2}) is below the typical range; "
            "provider review required."
        )

    temp = _maybe_float(payload.get("temperature_value"))
    unit = (payload.get("temperature_unit") or "F").upper()
    if temp is not None:
        if unit == "F" and (temp < _TEMP_F_LOW or temp > _TEMP_F_HIGH):
            warnings.append(
                f"Temperature ({temp}°F) is outside the typical "
                "range; provider review required."
            )
        elif unit == "C" and (temp < _TEMP_C_LOW or temp > _TEMP_C_HIGH):
            warnings.append(
                f"Temperature ({temp}°C) is outside the typical "
                "range; provider review required."
            )

    h = _maybe_float(payload.get("height_value"))
    w = _maybe_float(payload.get("weight_value"))
    if h is not None and w is None:
        warnings.append(
            "Height captured but weight missing; BMI cannot be "
            "calculated until both are entered."
        )
    if w is not None and h is None:
        warnings.append(
            "Weight captured but height missing; BMI cannot be "
            "calculated until both are entered."
        )

    pain = _maybe_int(payload.get("pain_score"))
    if pain is not None and (pain < _PAIN_LOW or pain > _PAIN_HIGH):
        warnings.append(
            f"Pain score ({pain}) is outside the 0-10 scale; please "
            "re-enter."
        )

    iop_od = _maybe_float(payload.get("iop_od"))
    iop_os = _maybe_float(payload.get("iop_os"))
    if iop_od is not None and iop_os is None:
        warnings.append(
            "IOP captured for OD but not OS; please add IOP OS or "
            "confirm intent before signing."
        )
    if iop_os is not None and iop_od is None:
        warnings.append(
            "IOP captured for OS but not OD; please add IOP OD or "
            "confirm intent before signing."
        )
    if (iop_od is not None or iop_os is not None) and not payload.get(
        "iop_method"
    ):
        warnings.append(
            "IOP recorded without a method; please specify method "
            "(applanation / tonopen / icare / other) before signing."
        )

    va_od = payload.get("visual_acuity_od")
    va_os = payload.get("visual_acuity_os")
    if va_od and not va_os and not payload.get("visual_acuity_ou"):
        warnings.append(
            "Visual acuity captured for OD but not OS; please add VA "
            "OS or confirm intent before signing."
        )
    if va_os and not va_od and not payload.get("visual_acuity_ou"):
        warnings.append(
            "Visual acuity captured for OS but not OD; please add VA "
            "OD or confirm intent before signing."
        )

    return warnings


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def assert_can_modify(status: str) -> None:
    """Raise if the workup is in a terminal state."""
    if is_terminal(status):
        raise VitalsImmutable(status)


def assert_can_transition(action: str, current: str) -> None:
    """Raise if the action is not legal from the current status."""
    valid = _VALID_TRANSITIONS.get(action)
    if valid is None:
        raise VitalsTransitionError(action, current)
    if current not in valid:
        if is_terminal(current):
            raise VitalsImmutable(current)
        raise VitalsTransitionError(action, current)


# ---------------------------------------------------------------------------
# Audit metadata helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditMetadata:
    workup_id: int
    encounter_id: int
    patient_id: Optional[int]
    status: str
    warning_count: int
    action: str


def build_audit_detail(meta: AuditMetadata) -> str:
    """Build the metadata-only `detail` string for audit.record(...).

    NEVER include vitals values, technician notes, VA, IOP, or any
    free-text field here. Phase 60 tests will scan audit rows for a
    canary value to prove this contract.
    """
    return (
        f"workup_id={meta.workup_id} "
        f"encounter_id={meta.encounter_id} "
        f"patient_id={meta.patient_id} "
        f"status={meta.status} "
        f"warning_count={meta.warning_count} "
        f"action={meta.action}"
    )

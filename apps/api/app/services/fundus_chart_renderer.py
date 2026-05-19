"""Deterministic SVG renderer for fundus charts.

Produces a self-contained SVG string from drawing_json produced by
fundus_chart_ai.generate_chart_from_findings().
"""
from __future__ import annotations

import math
from typing import Any

_CX = 100.0
_CY = 100.0
_R_POSTERIOR = 28.0
_R_EQUATOR = 55.0
_R_ORA = 80.0
_R_LABEL = 93.0

_ZONE_RADIUS: dict[str, float] = {
    "posterior_pole": (_R_POSTERIOR + _R_EQUATOR) / 2,
    "equator": (_R_EQUATOR + _R_ORA) / 2,
    "ora_serrata": (_R_ORA + _R_LABEL) / 2,
}


def _clock_to_rad(h: float) -> float:
    deg = (h * 30.0 - 90.0) % 360.0
    return math.radians(deg)


def _clock_to_xy(h: float, r: float) -> tuple[float, float]:
    angle = _clock_to_rad(h)
    return _CX + r * math.cos(angle), _CY + r * math.sin(angle)


def _arc_path(h_start: float, h_end: float, r: float) -> str:
    x1, y1 = _clock_to_xy(h_start, r)
    x2, y2 = _clock_to_xy(h_end, r)
    span = (h_end - h_start) % 12
    large_arc = 1 if span > 6 else 0
    return (
        f"M {x1:.2f} {y1:.2f} "
        f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f}"
    )


def _circle(r: float, stroke: str, stroke_width: float = 0.5) -> str:
    return (
        f'<circle cx="{_CX}" cy="{_CY}" r="{r:.2f}" '
        f'fill="none" stroke="{stroke}" stroke-width="{stroke_width:.2f}"/>'
    )


def _render_element(el: dict[str, Any]) -> str:
    zone = el.get("zone", "equator")
    r = _ZONE_RADIUS.get(zone, _ZONE_RADIUS["equator"])
    color = el.get("color", "#718096")
    clock_start = el.get("clock_start")
    clock_end = el.get("clock_end")
    label = el.get("label", "")

    parts: list[str] = []

    if clock_start is not None and clock_end is not None:
        path = _arc_path(clock_start, clock_end, r)
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" '
            f'stroke-width="4" stroke-linecap="round" opacity="0.85"/>'
        )
        mid_h = clock_start + (clock_end - clock_start) / 2.0
        lx, ly = _clock_to_xy(mid_h, r)
        parts.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="5" fill="{color}" '
            f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
        )
    elif clock_start is not None:
        px, py = _clock_to_xy(clock_start, r)
        parts.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" '
            f'fill="{color}" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{px:.2f}" y="{py + 7:.2f}" font-size="5" fill="{color}" '
            f'text-anchor="middle">{label}</text>'
        )
    else:
        px, py = _clock_to_xy(12.0, r)
        parts.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" '
            f'fill="{color}" opacity="0.5" stroke-dasharray="2,2"/>'
        )

    return "\n".join(parts)


def render_fundus_svg(drawing_json: dict[str, Any], laterality: str = "OD") -> str:
    """Return a self-contained SVG string for the given drawing data."""
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
        'width="400" height="400">',
        f'<title>Fundus Chart — {laterality}</title>',
        '<rect width="200" height="200" fill="#f9f9f9"/>',
    ]

    lines.append(_circle(_R_POSTERIOR, "#aaa", 0.6))
    lines.append(_circle(_R_EQUATOR, "#aaa", 0.6))
    lines.append(_circle(_R_ORA, "#bbb", 1.0))

    lines.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="5" fill="#fff" '
        'stroke="#888" stroke-width="0.5"/>'
    )

    for h in range(1, 13):
        angle = _clock_to_rad(float(h))
        xi = _CX + _R_POSTERIOR * math.cos(angle)
        yi = _CY + _R_POSTERIOR * math.sin(angle)
        xo = _CX + _R_ORA * math.cos(angle)
        yo = _CY + _R_ORA * math.sin(angle)
        lines.append(
            f'<line x1="{xi:.2f}" y1="{yi:.2f}" x2="{xo:.2f}" y2="{yo:.2f}" '
            'stroke="#ddd" stroke-width="0.4"/>'
        )
        lx = _CX + _R_LABEL * math.cos(angle)
        ly = _CY + _R_LABEL * math.sin(angle)
        lines.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="6" fill="#666" '
            f'text-anchor="middle" dominant-baseline="middle">{h}</text>'
        )

    lines.append(
        f'<text x="{_CX:.2f}" y="{_CY + _R_POSTERIOR + 8:.2f}" '
        'font-size="4.5" fill="#999" text-anchor="middle">Posterior Pole</text>'
    )
    lines.append(
        f'<text x="{_CX:.2f}" y="{_CY + _R_EQUATOR + 5:.2f}" '
        'font-size="4" fill="#bbb" text-anchor="middle">Equator</text>'
    )
    lines.append(
        f'<text x="4" y="10" font-size="7" fill="#555" '
        f'font-weight="bold">{laterality}</text>'
    )

    for el in drawing_json.get("elements", []):
        lines.append(_render_element(el))

    lines.append("</svg>")
    return "\n".join(lines)

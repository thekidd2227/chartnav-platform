import React from "react";
import type { FundusDrawingJson, FundusDrawingElement } from "./fundusTypes";

const CX = 100;
const CY = 100;
const R_POSTERIOR = 28;
const R_EQUATOR = 55;
const R_ORA = 80;
const R_LABEL = 93;

const ZONE_RADIUS: Record<string, number> = {
  posterior_pole: (R_POSTERIOR + R_EQUATOR) / 2,
  equator: (R_EQUATOR + R_ORA) / 2,
  ora_serrata: (R_ORA + R_LABEL) / 2,
};

function clockToRad(h: number): number {
  const deg = ((h * 30 - 90) % 360 + 360) % 360;
  return (deg * Math.PI) / 180;
}

function clockToXY(h: number, r: number): [number, number] {
  const a = clockToRad(h);
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
}

function arcPath(hStart: number, hEnd: number, r: number): string {
  const [x1, y1] = clockToXY(hStart, r);
  const [x2, y2] = clockToXY(hEnd, r);
  const span = ((hEnd - hStart) % 12 + 12) % 12;
  const largeArc = span > 6 ? 1 : 0;
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

function ElementOverlay({ el }: { el: FundusDrawingElement }) {
  const r = ZONE_RADIUS[el.zone] ?? ZONE_RADIUS["equator"];
  const color = el.color ?? "#718096";

  if (el.clock_start !== null && el.clock_end !== null) {
    const path = arcPath(el.clock_start, el.clock_end, r);
    const mid = el.clock_start + (el.clock_end - el.clock_start) / 2;
    const [lx, ly] = clockToXY(mid, r);
    return (
      <g>
        <path d={path} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" opacity={0.85} />
        <text x={lx} y={ly} fontSize={5} fill={color} textAnchor="middle" dominantBaseline="middle">
          {el.label}
        </text>
      </g>
    );
  }

  if (el.clock_start !== null) {
    const [px, py] = clockToXY(el.clock_start, r);
    return (
      <g>
        <circle cx={px} cy={py} r={4} fill={color} opacity={0.85} />
        <text x={px} y={py + 7} fontSize={5} fill={color} textAnchor="middle">
          {el.label}
        </text>
      </g>
    );
  }

  const [px, py] = clockToXY(12, r);
  return <circle cx={px} cy={py} r={4} fill={color} opacity={0.5} strokeDasharray="2,2" />;
}

interface Props {
  drawing: FundusDrawingJson | null;
  laterality: string;
  size?: number;
}

export function FundusChartRenderer({ drawing, laterality, size = 400 }: Props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 200"
      width={size}
      height={size}
      style={{ background: "#f9f9f9", borderRadius: 8 }}
    >
      <circle cx={CX} cy={CY} r={R_POSTERIOR} fill="none" stroke="#aaa" strokeWidth={0.6} />
      <circle cx={CX} cy={CY} r={R_EQUATOR} fill="none" stroke="#aaa" strokeWidth={0.6} />
      <circle cx={CX} cy={CY} r={R_ORA} fill="none" stroke="#bbb" strokeWidth={1} />
      <circle cx={CX} cy={CY} r={5} fill="#fff" stroke="#888" strokeWidth={0.5} />

      {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => {
        const a = clockToRad(h);
        const [xI, yI] = [CX + R_POSTERIOR * Math.cos(a), CY + R_POSTERIOR * Math.sin(a)];
        const [xO, yO] = [CX + R_ORA * Math.cos(a), CY + R_ORA * Math.sin(a)];
        const [lx, ly] = [CX + R_LABEL * Math.cos(a), CY + R_LABEL * Math.sin(a)];
        return (
          <g key={h}>
            <line x1={xI} y1={yI} x2={xO} y2={yO} stroke="#ddd" strokeWidth={0.4} />
            <text x={lx} y={ly} fontSize={6} fill="#666" textAnchor="middle" dominantBaseline="middle">
              {h}
            </text>
          </g>
        );
      })}

      <text x={CX} y={CY + R_POSTERIOR + 8} fontSize={4.5} fill="#999" textAnchor="middle">
        Posterior Pole
      </text>
      <text x={CX} y={CY + R_EQUATOR + 5} fontSize={4} fill="#bbb" textAnchor="middle">
        Equator
      </text>
      <text x={4} y={10} fontSize={7} fill="#555" fontWeight="bold">
        {laterality}
      </text>

      {drawing?.elements?.map((el, i) => (
        <ElementOverlay key={i} el={el} />
      ))}
    </svg>
  );
}

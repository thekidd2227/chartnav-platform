// ROI wave 1 · item 5
//
// QueuePresets — compact row of preset chips that sit above the
// filter bar. Each chip applies a client-side predicate over the
// encounter list to produce a focused queue view. Role-scoped via
// `audience` so front desk sees scheduling presets, clinical
// support sees workflow presets.

import { QueuePreset, QueuePresetDescriptor } from "./readiness";

interface Props {
  presets: QueuePresetDescriptor[];
  value: QueuePreset;
  counts: Partial<Record<QueuePreset, number>>;
  onChange: (next: QueuePreset) => void;
}

export function QueuePresets({ presets, value, counts, onChange }: Props) {
  return (
    <div
      className="queue-presets"
      role="tablist"
      aria-label="Queue presets"
      data-testid="queue-presets"
    >
      {presets.map((p) => {
        const active = p.key === value;
        const n = counts[p.key];
        return (
          <button
            key={p.key}
            type="button"
            role="tab"
            aria-selected={active}
            aria-pressed={active}
            title={p.tooltip}
            className="queue-presets__chip"
            data-active={active}
            data-testid={`queue-preset-${p.key}`}
            onClick={() => onChange(p.key)}
          >
            <span>{p.label}</span>
            {n !== undefined && (
              <span
                className="queue-presets__count"
                data-testid={`queue-preset-count-${p.key}`}
              >
                {n}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

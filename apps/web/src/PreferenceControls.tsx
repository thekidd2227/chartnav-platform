// Phase 38 — density + theme picker shown in the app header.

import { Density, ThemeMode } from "./preferences";

interface Props {
  density: Density;
  theme: ThemeMode;
  onDensity: (d: Density) => void;
  onTheme: (t: ThemeMode) => void;
}

export function PreferenceControls({
  density,
  theme,
  onDensity,
  onTheme,
}: Props) {
  return (
    <>
      <div
        className="pref-picker"
        role="radiogroup"
        aria-label="Density"
        data-testid="density-picker"
      >
        {(["compact", "default", "comfortable"] as Density[]).map((d) => (
          <button
            key={d}
            type="button"
            className="pref-picker__btn"
            role="radio"
            aria-checked={density === d}
            aria-pressed={density === d}
            data-testid={`density-${d}`}
            onClick={() => onDensity(d)}
            title={`Density · ${d}`}
          >
            {d === "compact" ? "A" : d === "default" ? "A" : "A"}
            <span style={{ display: "none" }}>{d}</span>
          </button>
        ))}
      </div>
      <div
        className="pref-picker"
        role="radiogroup"
        aria-label="Theme"
        data-testid="theme-picker"
      >
        {(["system", "light", "dark"] as ThemeMode[]).map((t) => (
          <button
            key={t}
            type="button"
            className="pref-picker__btn"
            role="radio"
            aria-checked={theme === t}
            aria-pressed={theme === t}
            data-testid={`theme-${t}`}
            onClick={() => onTheme(t)}
            title={`Theme · ${t}`}
          >
            {t === "system" ? "auto" : t === "light" ? "lt" : "dk"}
          </button>
        ))}
      </div>
    </>
  );
}

// Phase 38 — user-facing visual preferences (density + theme).
//
// These preferences are purely client-side. They do not change any
// backend contract, do not mutate RBAC, and do not alter the audit
// model. They are expressed as `data-*` attributes on <html>/<body>
// which the CSS reads to override the existing token set. The token
// values themselves stay the single source of visual truth.
//
// Persistence model: localStorage, same discipline as identity.ts.
// Graceful fallback when localStorage is unavailable (SSR / strict
// sandbox). All values are validated against a fixed allowlist so
// a bogus localStorage value can never render an unknown state.

export type Density = "compact" | "default" | "comfortable";
export type ThemeMode = "system" | "light" | "dark";

export const DENSITIES: Density[] = ["compact", "default", "comfortable"];
export const THEME_MODES: ThemeMode[] = ["system", "light", "dark"];

const DENSITY_KEY = "chartnav.density";
const THEME_KEY = "chartnav.theme";

function safeRead(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeWrite(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // best effort
  }
}

export function loadDensity(): Density {
  const v = safeRead(DENSITY_KEY);
  return DENSITIES.includes(v as Density) ? (v as Density) : "default";
}

export function saveDensity(d: Density): void {
  safeWrite(DENSITY_KEY, d);
}

export function loadTheme(): ThemeMode {
  const v = safeRead(THEME_KEY);
  return THEME_MODES.includes(v as ThemeMode) ? (v as ThemeMode) : "system";
}

export function saveTheme(t: ThemeMode): void {
  safeWrite(THEME_KEY, t);
}

/**
 * Apply density + theme to the document root. Safe to call on every
 * change; idempotent. Keeps `data-density` on <html> and `data-theme`
 * resolved to the effective concrete value ("light" | "dark") on
 * <html> so the CSS selector surface stays trivial.
 */
export function applyPreferences(density: Density, theme: ThemeMode): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.setAttribute("data-density", density);

  let effective: "light" | "dark" = "light";
  if (theme === "dark") effective = "dark";
  else if (theme === "light") effective = "light";
  else {
    // "system" — follow prefers-color-scheme at apply time.
    try {
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        effective = "dark";
      }
    } catch {
      effective = "light";
    }
  }
  root.setAttribute("data-theme", effective);
  root.setAttribute("data-theme-mode", theme);
}

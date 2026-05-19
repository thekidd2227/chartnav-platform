// apps/web/src/i18n/index.ts
//
// Tiny dependency-free i18n layer for the ChartNav public landing
// page. Resolves the active language from (in priority order):
//   1. an explicit `?lang=es` / `?lang=en` query string,
//   2. a path prefix (`/es/...`),
//   3. a previously-persisted choice in `localStorage`,
//   4. the default ("en").
//
// Persistence: when a user clicks the switcher, the choice is
// written to localStorage under `chartnav.language` so the next
// page load remembers it. URL-driven language always wins on the
// current page render.
//
// Why this is bespoke (no i18next / react-intl): the public
// website currently has exactly one route family (the landing
// page) and one user surface. Shipping a heavyweight i18n runtime
// would increase the public bundle for ~50 strings of copy.

import { APP_EN } from "./app.en";
import { APP_ES } from "./app.es";
import { LANDING_EN } from "./landing.en";
import { LANDING_ES } from "./landing.es";
import type { AppCopy, Language, LandingCopy } from "./types";

export type { AppCopy, Language, LandingCopy } from "./types";

export const SUPPORTED_LANGUAGES: { code: Language; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
];

const DEFAULT_LANGUAGE: Language = "en";
const LANG_STORAGE_KEY = "chartnav.language";

function isLanguage(value: string | null): value is Language {
  return value === "en" || value === "es";
}

function readLanguageFromUrl(): Language | null {
  if (typeof window === "undefined") return null;
  try {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("lang");
    if (isLanguage(q)) return q;
    const path = window.location.pathname;
    // Recognise /es, /es/, /es/landing, /es/anything as Spanish.
    if (
      path === "/es"
      || path.startsWith("/es/")
      || path.endsWith("/es")
      || path.endsWith("/es/landing")
    ) {
      return "es";
    }
    if (
      path === "/en"
      || path.startsWith("/en/")
      || path.endsWith("/en")
      || path.endsWith("/en/landing")
    ) {
      return "en";
    }
    return null;
  } catch {
    return null;
  }
}

function readLanguageFromStorage(): Language | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.localStorage.getItem(LANG_STORAGE_KEY);
    return isLanguage(v) ? v : null;
  } catch {
    return null;
  }
}

export function getCurrentLanguage(): Language {
  return (
    readLanguageFromUrl()
    ?? readLanguageFromStorage()
    ?? DEFAULT_LANGUAGE
  );
}

export function persistLanguage(lang: Language): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // best effort — non-localStorage environments fall back to URL.
  }
}

export function getLandingCopy(lang: Language): LandingCopy {
  return lang === "es" ? LANDING_ES : LANDING_EN;
}

/** Phase A — authenticated workspace chrome copy. Larger panels
 *  (RoleDashboard, NoteWorkspace, AdminPanel, etc.) will get their
 *  own typed slices in Phase B/C. */
export function getAppCopy(lang: Language): AppCopy {
  return lang === "es" ? APP_ES : APP_EN;
}

/**
 * Build a URL for the requested language that preserves the current
 * pathname's "landing-ness" and clears any conflicting language
 * markers. Pure function (takes location bits as args) so it stays
 * testable without a DOM.
 */
export function buildLanguageHref(
  lang: Language,
  loc: { pathname: string; search: string },
): string {
  const params = new URLSearchParams(loc.search);
  if (lang === DEFAULT_LANGUAGE) {
    params.delete("lang");
  } else {
    params.set("lang", lang);
  }
  const qs = params.toString();
  // Strip leading /es or /en path prefix if present so the URL is
  // disambiguated by the query string only. Keeps the routing
  // surface tiny and consistent with main.tsx's hash-free path
  // matching.
  let pathname = loc.pathname;
  if (pathname === "/es" || pathname === "/en") {
    pathname = "/";
  } else if (pathname.startsWith("/es/")) {
    pathname = pathname.slice(3) || "/";
  } else if (pathname.startsWith("/en/")) {
    pathname = pathname.slice(3) || "/";
  }
  return qs ? `${pathname}?${qs}` : pathname;
}

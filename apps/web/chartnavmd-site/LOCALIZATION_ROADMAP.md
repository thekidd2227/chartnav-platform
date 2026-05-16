# ChartNav — multi-language localization roadmap

> Multi-language strategy for **both** ChartNav language surfaces:
> 1. the static public-marketing site at `chartnavmd.com`
>    (source: `apps/web/chartnavmd-site/`)
> 2. the authenticated clinical platform SPA
>    (source: `chartnav-platform/apps/web/src/i18n/`,
>    landed under PR #43 with English + Spanish)
>
> Phase 19K shipped Spanish to surface (1).
> Phase 19L will ship French + German + Simplified Chinese to **both**
> surfaces in a single coordinated effort.

## Current state (Phase 19K)

- **Languages shipped:** English (default) + Spanish (Latin American, neutral, formal *usted*).
- **Toggle:** `[ English | Español ]` segmented pill mounted into every public-page footer by `/lang-toggle.js`.
- **Persistence:** `localStorage.chartnav.language`.
- **Query-param override:** `?lang=en` and `?lang=es`. Query-param takes precedence over `localStorage` and writes back.
- **`<html lang>`:** updated on toggle.
- **Pages covered:** `/`, `/ehr/`, `/platform/`, `/ophthalmology/`, `/implementation/`, `/ai-security/`, `/security/`.
- **Mechanism:** each page ships a page-local `window.__CN_I18N__ = { en: {...}, es: {...} }` map. `lang-toggle.js` reads the map and swaps every `[data-i18n="key"]` text content and `[data-i18n-attr-<attr>="key"]` attribute on toggle, plus `document.title` and `meta[name="description"]` via the special keys `__document_title` and `__meta_description`.
- **Video showcase captions:** homepage shows additional `__vshow_manifest` per-language array consumed by the inline rotator script; emits the `chartnav:languagechange` event so the rotator repaints active captions.
- **Hreflang alternates:** `en`, `es`, and `x-default` declared in every page's `<head>`.

## Phase 19L — French, German, Simplified Chinese (planned, NOT YET IMPLEMENTED)

Phase 19L ships three new languages to **both** the public static site and the authenticated clinical platform in one coordinated phase.

| Code | Language | Notes |
|---|---|---|
| `fr` | French (Canadian neutral; aligns with QC ophthalmology buyers) | full translation, both surfaces |
| `de` | German (DACH neutral; sales-formal *Sie*) | full translation, both surfaces |
| `zh` | Simplified Chinese (Mandarin, simplified script, mainland sales register) | full translation, both surfaces |

### Surface 1 — public static site (`apps/web/chartnavmd-site/`)

The shared `/lang-toggle.js` already accepts an arbitrary `SUPPORTED` list. Adding a language is purely a content task plus one line in the script's `SUPPORTED` array.

1. Add `fr`, `de`, `zh` to `SUPPORTED` in `/lang-toggle.js`.
2. Add translation maps for each language under each page's inline `window.__CN_I18N__`. Maps must cover **every** key already present in `en` and `es` across all 7 pages.
3. Extend the footer toggle from a 2-button pill into a compact 5-language dropdown OR a wider segmented pill at desktop with a `<select>` fallback at mobile — pick whichever ages better visually with 5 entries.
4. Add hreflang `<link rel="alternate">` tags for each new language to every page's `<head>`.
5. Extend `scripts/check_public_site_claims.sh` with the equivalent forbidden-positive-claim list in French / German / Chinese.
6. Extend `scripts/check_public_site_not_platform.sh` if any platform-marker phrasing changes meaningfully across languages.
7. Update `__document_title` and `__meta_description` keys per language.

### Surface 2 — authenticated clinical platform (`chartnav-platform/apps/web/src/i18n/`)

PR #43 landed Spanish for the SPA-rendered LandingPage using a TypeScript i18n module (`landing.en.ts`, `landing.es.ts`, `types.ts`, `index.ts`) and added `<button>` switchers + `hreflang` alternates. Phase 19L extends that same module:

1. Add `fr`, `de`, `zh` to the `LangCode` union in `apps/web/src/i18n/types.ts`.
2. Author `apps/web/src/i18n/landing.fr.ts`, `landing.de.ts`, `landing.zh.ts` translation files. Each must export the exact same shape as `landing.en.ts` and `landing.es.ts` — no missing keys, no extra keys.
3. Extend the `LANGS` registry in `apps/web/src/i18n/index.ts` so the platform-side toggle exposes 5 languages.
4. Audit `apps/web/src/LandingPage.tsx` for the switcher rendering — extend from 2-button pair to a 5-language control (same layout decision as the public-site toggle).
5. Add hreflang `<link rel="alternate" hreflang="fr|de|zh">` to `apps/web/index.html`.
6. Extend `scripts/check_website_claims.sh` (the platform-side claims guard) with French / German / Chinese forbidden-phrase blocks. The existing Spanish forbidden-phrase scan stays as the reference.
7. Add `apps/web/src/test/LandingPageFrench.test.tsx`, `…German.test.tsx`, `…Chinese.test.tsx` mirroring the existing `LandingPageSpanish.test.tsx` (14 cases each: hero / CTAs / workflow / non-goals / footer / doc-title swap / switcher state + toggle + persistence / forbidden-phrase contract / English-default-intact).

### Coordination

Both surfaces should land in the same Phase 19L PR so:

- the language switch is consistent between marketing and product (same supported codes, same labels, same persistence key — `chartnav.language`),
- a buyer who toggles to French on `chartnavmd.com` and then signs into the platform stays in French,
- the claims guard for each language ships everywhere it's spoken, not just on one surface.

### Translation quality standard (applies to both surfaces)

- **No machine-only output.** Every translation must be reviewed by a qualified medical / business translator native to the target locale.
- **No stronger claims than English.** Translators may not introduce regulatory claims, certifications, or autonomy claims that the English source intentionally avoids.
- **Safety-section parity.** The `non_goals.*` keys (or per-page / per-component equivalents) must remain 1:1 with the English source.

### Translation quality standard

- **No machine-only output.** Every translation must be reviewed by a qualified medical / business translator native to the target locale.
- **No stronger claims than English.** Translators may not introduce regulatory claims, certifications, or autonomy claims that the English source intentionally avoids.
- **Safety-section parity.** The `non_goals.*` keys (or per-page equivalents) must remain 1:1 with the English source.

## Forbidden claims across all language variants

These positive claims are banned everywhere, regardless of language:

- HIPAA compliance / certification
- Certified EHR replacement
- Autonomous diagnosis
- Autonomous image interpretation
- Automatic OCT interpretation
- Automatic orders / referrals / patient messaging
- Automatic coding / billing
- Claims submission / insurance/payment handling
- EHR replacement
- Device integration / DICOM ingestion
- "The note writes itself" as a positive, standalone claim

Negative/safety contexts (e.g. *"ChartNav does not diagnose"*, *"No automatic claims submission"*) remain explicitly allowed and required.

## Adding a new key

1. Identify the visible text and pick a stable dot-namespaced key (e.g. `hero.cta_primary`).
2. Add the key to **every** language map on **every** page that uses it. Missing keys fall back to the English version per `lang-toggle.js`; missing entirely → fallback to the raw HTML text content (a `data-i18n-fallback="..."` attribute can override that).
3. Wire the DOM element with `data-i18n="<key>"` (text content) or `data-i18n-attr-<attr>="<key>"` (attribute value).

## Out of scope (Phase 19K specifically)

- Phase 19K Spanish work intentionally stopped at the public static site. The authenticated platform already has its own Spanish (PR #43) and didn't need re-translation.
- Server-side localized HTML emission (e.g. a Vite build that ships `/index.html`, `/es/index.html`, `/fr/index.html`) is intentionally not used on the public site. The static-HTML + client-side swap approach keeps deploys lightweight and lets a single CDN cache the same file regardless of language.

## Phase 19K (Spanish — public-site footer toggle) — done

This is the work this commit ships. See PR #28 for the full diff. Spanish is live on the public static site source under `apps/web/chartnavmd-site/`; production rollout pending operator approval.

# ChartNav public site — localization roadmap

> Owns the multi-language strategy for the static public-marketing site at
> `chartnavmd.com`. The authenticated clinical platform under
> `chartnav-platform/apps/web/src/i18n/` is a separate surface and is not
> covered by this document.

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

## Phase 19L — French, German, Chinese (planned, NOT YET IMPLEMENTED)

The shared `/lang-toggle.js` already accepts an arbitrary `SUPPORTED` list. Adding a language is purely a content task plus one line in the script's `SUPPORTED` array.

| Code | Language | Phase 19L scope |
|---|---|---|
| `fr` | French (Canadian neutral; aligns with QC ophthalmology buyers) | full marketing translation |
| `de` | German (DACH neutral; sales-formal *Sie*) | full marketing translation |
| `zh` | Simplified Chinese (Mandarin, simplified script, mainland sales register) | full marketing translation |

When Phase 19L lands:

1. Add `fr`, `de`, `zh` to `SUPPORTED` in `/lang-toggle.js`.
2. Add translation maps for each language under each page's inline `window.__CN_I18N__`. Maps must cover **every** key already present in `en` and `es`.
3. Extend the footer toggle from a 2-button pill into a compact 5-language dropdown OR a wider segmented pill at desktop with a `<select>` fallback at mobile — pick whichever ages better visually with 5 entries.
4. Add hreflang `<link rel="alternate">` tags for each new language to every page `<head>`.
5. Extend `scripts/check_public_site_claims.sh` with the equivalent forbidden-positive-claim list in French / German / Chinese.
6. Extend `scripts/check_public_site_not_platform.sh` if any platform-marker phrasing changes meaningfully across languages.
7. Update `__document_title` and `__meta_description` keys per language.

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

## Out of scope

- The authenticated clinical platform's React-based i18n module (`chartnav-platform/apps/web/src/i18n/`) is a separate surface.
- Server-side localized HTML emission (e.g. a Vite build that ships `/index.html`, `/es/index.html`, `/fr/index.html`) is intentionally not used. The static-HTML + client-side swap approach keeps deploys lightweight and lets a single CDN cache the same file regardless of language.

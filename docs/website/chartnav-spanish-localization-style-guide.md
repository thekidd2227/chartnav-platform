# ChartNav Spanish Localization Style Guide

> **Audience:** anyone editing Spanish copy on the public ChartNav
> website. Treat this as the source of truth for tone, terminology,
> and claim discipline. The English copy at `apps/web/src/i18n/landing.en.ts`
> is the source of truth for content; this guide is the source of
> truth for **how** that content is translated.

## Tone

- **Professional, clinical, and conservative.** ChartNav talks to
  ophthalmology practice owners, retina physicians, practice
  administrators, and IT / compliance staff. The Spanish copy reads
  like a clinic operations document, not a consumer ad.
- **Clear and direct.** Short sentences. Subject + verb + object.
  Resist the temptation to add ornamental qualifiers ("solución
  innovadora líder", "tecnología vanguardista") that the English
  version doesn't have.
- **Buyer-safe, never hype-y.** Spanish must never imply a
  capability the English version doesn't. If a claim is missing in
  English, it does not get added in Spanish — and vice versa.
- **Ophthalmology-specific, not generic.** Lean into eye-care
  vocabulary (OCT, fundus, PIO, refracción, OD/OS, anti-VEGF) and
  away from generic AI-scribe framing.

## Spanish variant

Use **neutral Latin American Spanish**, suitable for:

- U.S. Spanish-speaking clinics
- Mexico
- Colombia
- Dominican Republic
- Puerto Rico
- Central America
- the broader Latin American market

Avoid Spain-only phrasing where possible:

- **Use** "computadora" or just "equipo" instead of "ordenador."
- **Use** "Pasa lo siguiente" instead of "Vale, ocurre lo siguiente."
- **Use** "usted" — never "tú" — for buyer-facing copy. ChartNav
  speaks to professional decision-makers, and "usted" is the only
  appropriate register for that audience across the Latin American
  market.

## Approved terminology

| English (source of truth) | Spanish (use verbatim) |
|---|---|
| Ophthalmology clinic workflow layer | capa de flujo operativo para clínicas oftalmológicas |
| Provider-reviewed documentation | documentación revisada por el proveedor clínico |
| Imaging metadata review | revisión de metadatos de imágenes |
| Retina workflow | flujo de retina |
| Glaucoma tracking | seguimiento de glaucoma |
| Role-based dashboards | paneles por rol |
| Technician workup | evaluación técnica inicial |
| Front desk readiness | preparación administrativa |
| Internal coordination | coordinación interna |
| Controlled pilot | piloto controlado |
| Real PHI | información médica protegida real (use "PHI real" inside parentheses on first mention if helpful: "información médica protegida real (PHI real)") |
| OD/OS retinal diagram | diagrama retiniano OD/OS |
| Imaging metadata pipeline | canalización de metadatos de imágenes |
| Pre-visit clinical brief | resumen clínico previo a la visita |
| Provider action review queue | cola de revisión de acciones del proveedor |
| Guided demo mode | modo demo guiado |
| Pilot-readiness package | paquete de preparación para piloto |
| Sign-off | cierre (or "firma del proveedor" when the literal signature is meant) |
| Provider | proveedor (clínico) |
| Fake demo data / synthetic patient | datos de demostración ficticios / paciente ficticio |
| BAA (Business Associate Agreement) | BAA (Acuerdo de Asociado Comercial) on first mention; "BAA" thereafter |

## Compliance terminology

- **Keep `HIPAA` as `HIPAA`** — it is a U.S. statute. Do not
  translate or expand it. Spanish copy may say "**no cuenta con
  certificación HIPAA**" but never "**cumple con HIPAA**" or
  "**certificado HIPAA**."
- **Keep `EHR` as `EHR`** for consistency with the buyer's
  vocabulary. (Some practices localise to "expediente médico
  electrónico" — that's fine in body copy, but EHR remains the
  primary noun.)
- **`PHI`** is U.S.-statute terminology. In Spanish copy, write
  "**información médica protegida real**" or "**PHI real /
  información médica protegida real**" on first mention; "PHI" can
  be used as a shorthand thereafter.
- **`SOC 2`, `FDA`, `HITRUST`** — keep as English acronyms; do not
  imply ChartNav holds any of those certifications.

## Negative-assertion contract

Every English non-goal has a Spanish counterpart with **identical
claim strength**. The Spanish list must never be softer or stronger
than the English list. If the English copy says "Not autonomous
diagnosis", the Spanish copy says "No realiza diagnóstico
autónomo" — not "no recomendado para diagnóstico" (softer) and not
"prohibido diagnosticar de forma autónoma" (stronger).

## Forbidden phrasings (Spanish)

These positive-claim phrasings are **banned** from any user-facing
Spanish surface. The negative form is allowed (and required, in
the non-goals section).

| Forbidden Spanish positive | Equivalent English banned phrase |
|---|---|
| `cumple con HIPAA` | HIPAA-compliant |
| `certificado HIPAA` / `certificación HIPAA` | HIPAA-certified |
| `EHR certificado` (as a positive ChartNav claim) | certified EHR (positive) |
| `reemplaza su EHR` / `reemplaza el EHR` | replaces your EHR |
| `reemplaza su EMR` / `reemplaza el EMR` | replaces your EMR |
| `diagnóstico autónomo` / `diagnóstico automático` (positive) | autonomous diagnosis / automatic diagnosis |
| `interpretación autónoma de imágenes` / `interpretación automática de imágenes` | autonomous / automatic image interpretation |
| `interpretación automática de OCT` | automatic OCT interpretation |
| `calificación automática de retinopatía diabética` | auto-grade DR |
| `recomendaciones de tratamiento` | treatment recommendation |
| `recomienda anti-VEGF` | recommends anti-VEGF |
| `selecciona potencia de lente intraocular` | selects IOL power |
| `órdenes automáticas` | automatic orders |
| `referencias automáticas` | automatic referrals |
| `mensajes automáticos al paciente` / `mensajería al paciente` | automatic patient messaging |
| `codificación automática` | automatic coding |
| `facturación automática` | automatic billing |
| `envío de reclamaciones` / `presentación de reclamaciones` | claims submission |
| `procesamiento de seguros` / `gestión de seguros` | insurance handling |
| `integración con dispositivos` (positive, day-one) | device integration |
| `DICOM` (as a positive integration claim) | DICOM ingestion |
| `PHI real listo` / `información médica protegida real lista` | real PHI ready |
| `la nota se escribe sola` | the note writes itself |
| `la historia clínica se completa sola` | the chart fills itself |
| `manos libres` (as a primary scribing claim) | hands-free scribing |

These phrases are allowed **only** in:

- explicit negative assertions ("ChartNav no realiza diagnóstico
  autónomo")
- "what not to say" enumerations / forbidden lists
- safety disclaimers
- future / planned caveats (clearly marked as roadmap)
- claim-safety catalog documents like this one

## Non-goals — verbatim Spanish block

The landing page renders this list under "Lo que ChartNav no hace."
Use exactly these strings; the claim-safety scanner depends on the
contract being identical to the English non-goals list.

```
- No es un EHR certificado. ChartNav funciona junto a su EHR
  existente; no lo reemplaza.
- No cuenta con certificación HIPAA. Un piloto con PHI real
  (información médica protegida real) requiere BAA, revisión de
  seguridad, autenticación de producción, hosting aprobado,
  monitoreo, respaldos, contactos de incidente y aprobación
  escrita de la práctica.
- No realiza diagnóstico autónomo. La interpretación clínica
  permanece con el proveedor.
- No completa automáticamente la PIO (presión intraocular), la
  refracción ni la relación copa-disco.
- No interpreta exámenes de OCT, fotografías de fondo de ojo ni
  campos visuales.
- No selecciona la potencia de la lente intraocular ni la dosis
  de anti-VEGF.
- No coloca órdenes, no envía referencias, no presenta
  reclamaciones ni gestiona seguros.
- No envía mensajes automáticos al paciente. No hay superficie
  orientada al paciente.
- No es una integración actual con ningún proveedor específico
  de dispositivos de imagen.
```

## Brand and identifiers

- **Never translate "ChartNav."** It is the product name. Do not
  capitalize it differently, do not space it out, do not localize
  it.
- **Never translate "Morgan Lee."** Morgan Lee is the seeded fake
  demo patient name (PT-1001). The name is part of the demo
  contract.
- **Never translate technical identifiers, test IDs, code
  references, or file paths.** Spanish copy may mention
  `apps/api/scripts_seed.py` without translation.
- **Keep "ARCG"** (operator entity) unchanged.

## SEO / metadata

Spanish `<title>` (default):

```
ChartNav MD — Flujo clínico oftalmológico y documentación revisada por proveedores
```

Spanish `<meta name="description">` (default):

```
ChartNav ayuda a coordinar flujos de trabajo oftalmológicos:
preparación administrativa, evaluación técnica inicial, revisión
de metadatos de imágenes, seguimiento de retina y glaucoma,
documentación revisada por proveedores y coordinación interna.
No es un EHR certificado. No cuenta con certificación HIPAA por
defecto.
```

Spanish OG tags follow the same translations as the visible page
copy. Avoid generative phrasing — keep parity with the English OG
tags, which describe what ChartNav **is** (clinical workflow
layer) and what it **isn't** (certified EHR, HIPAA-certified by
default).

## Reviewing a new Spanish string

1. Confirm it has an English counterpart at `apps/web/src/i18n/landing.en.ts`.
2. Confirm the claim strength matches the English exactly.
3. Run `bash scripts/check_website_claims.sh` to ensure no
   forbidden Spanish positive phrase appears outside a negative
   context.
4. Run `cd apps/web && npx vitest run` to ensure the existing
   English assertions still hold and the new Spanish assertions
   pass.
5. Update this style guide if you introduce a new term that future
   translations should reuse.

## What this guide does NOT cover

- **Investor or partner emails.** Those are operator-side; they're
  not gated by the website claim-safety scripts.
- **Buyer decks** under `docs/decks/`. Those have their own claim
  contract enforced by `scripts/check_commercial_claims.sh`.
- **Demo runbooks / shot lists** under `docs/demo/`. Those are
  operator-internal; the relevant gate is `scripts/check_demo_claims.sh`.
- **Live-site HTML capture from `chartnavmd.com`.** That's the
  Phase 24A drift detector's job
  (`scripts/check_live_site_claims.sh`).

## References

- `apps/web/src/i18n/landing.en.ts` — English source of truth.
- `apps/web/src/i18n/landing.es.ts` — Spanish translation.
- `apps/web/src/i18n/index.ts` — language resolver + switcher
  utilities.
- `apps/web/src/LandingPage.tsx` — consumer of both.
- `scripts/check_website_claims.sh` — landing-page gate (extended
  in this phase to scan Spanish).
- `docs/website/chartnav-public-claims-drift-policy.md` — Phase 24A
  drift policy. Spanish copy must comply with the same policy.
- `docs/commercial/chartnav-approved-claims-language.md` — master
  approved-language list (English). When the master list changes,
  this style guide must be updated to add the Spanish equivalent.

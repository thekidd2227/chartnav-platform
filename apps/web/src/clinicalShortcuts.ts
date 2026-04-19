// Phase 29 — Clinical Shortcuts (doctor-only specialist shorthand pack).
//
// Separate from the phase-27 Quick Comments pad on purpose. Quick
// Comments are a clinician clipboard for free-form short phrases;
// Clinical Shortcuts are a **curated shorthand phrase bank** of
// structured note fragments that subspecialists actually write.
//
// These phrases are clinician-inserted charting content — NOT:
//   - transcript-derived findings
//   - extracted structured findings
//   - AI-generated draft text
//
// They are shared UI content, identical for every clinician, so they
// ship with the frontend bundle. No per-user persistence, no DB seed.
//
// The abbreviation reference is a *curated* subset of the Spokane
// Eye Clinic common ophthalmic abbreviations sheet, narrowed to the
// terms that appear in or are adjacent to the shipped shortcuts.
// We intentionally do NOT dump the full sheet into the UI.

export interface ClinicalShortcut {
  /** Stable string id; never a DB id. Used as the `shortcut_id`
   *  passed to the usage-audit endpoint. */
  id: string;
  /** Display group header. */
  group: ClinicalShortcutGroup;
  /** The note fragment inserted verbatim into the draft. Blanks like
   *  `___` are preserved so the clinician fills them in after
   *  insertion — they are intentional, not a template bug. */
  body: string;
  /** Free-text tags used for search matching alongside body + group.
   *  Include abbreviations that don't necessarily appear in `body`
   *  so a search for, e.g., "RD" surfaces PVD scleral-depressed-exam
   *  phrasing that rules it out. */
  tags: string[];
}

export type ClinicalShortcutGroup =
  | "PVD"
  | "Retinal detachment"
  | "Wet/Dry AMD"
  | "Diabetic retinopathy / DME"
  | "ERM / VMT / macular hole"
  | "BRVO / CRVO / retinal vascular"
  | "Post-injection / post-vitrectomy / post-op"
  | "Glaucoma"
  | "Cornea / anterior segment";

export const CLINICAL_SHORTCUT_GROUPS: ClinicalShortcutGroup[] = [
  "PVD",
  "Retinal detachment",
  "Wet/Dry AMD",
  "Diabetic retinopathy / DME",
  "ERM / VMT / macular hole",
  "BRVO / CRVO / retinal vascular",
  "Post-injection / post-vitrectomy / post-op",
  "Glaucoma",
  "Cornea / anterior segment",
];

export const CLINICAL_SHORTCUTS: ClinicalShortcut[] = [
  // ---------- PVD ----------
  {
    id: "pvd-01",
    group: "PVD",
    body:
      "Acute PVD noted with vitreous syneresis. Negative Shafer sign. " +
      "No retinal tear or retinal detachment on scleral depressed exam.",
    tags: [
      "pvd", "acute", "retina", "exam", "shafer", "syneresis",
      "retinal tear", "rt", "retinal detachment", "rd",
      "scleral depressed", "scleral depression",
    ],
  },
  {
    id: "pvd-02",
    group: "PVD",
    body:
      "Symptomatic PVD with flashes/floaters. Peripheral retina examined " +
      "to far periphery; no holes, tears, or RD seen today.",
    tags: [
      "pvd", "retina", "exam", "flashes", "floaters",
      "peripheral retina", "holes", "tears", "rd",
      "retinal detachment",
    ],
  },
  {
    id: "pvd-03",
    group: "PVD",
    body:
      "Chronic PVD, stable. Retinal detachment precautions reviewed.",
    tags: [
      "pvd", "chronic", "stable", "counseling",
      "retinal detachment", "rd", "precautions", "postop",
    ],
  },

  // ---------- Retinal detachment ----------
  {
    id: "rd-01",
    group: "Retinal detachment",
    body:
      "Rhegmatogenous retinal detachment involving ___ quadrants, " +
      "macula on / macula off.",
    tags: [
      "rd", "retinal detachment", "rhegmatogenous",
      "macula on", "macula off", "mac on", "mac off",
      "retina", "preop",
    ],
  },
  {
    id: "rd-02",
    group: "Retinal detachment",
    body:
      "Localized subretinal fluid extending from ___ to ___ o\u2019clock.",
    tags: [
      "srf", "subretinal fluid", "localized", "rd",
      "retinal detachment", "retina", "exam",
    ],
  },
  {
    id: "rd-03",
    group: "Retinal detachment",
    body:
      "Retina attached under oil / gas with good laser barricade.",
    tags: [
      "rd", "retinal detachment", "retina attached",
      "silicone oil", "gas", "laser", "barricade", "retinopexy",
      "postop", "ppv", "sb", "scleral buckle", "pr",
    ],
  },
  {
    id: "rd-04",
    group: "Retinal detachment",
    body:
      "Post-op retina remains attached; no recurrent SRF noted.",
    tags: [
      "rd", "retinal detachment", "postop", "post-op",
      "retina attached", "srf", "subretinal fluid",
      "recurrent", "ppv", "sb", "scleral buckle", "pr",
    ],
  },

  // ---------- Wet/Dry AMD ----------
  {
    id: "amd-01",
    group: "Wet/Dry AMD",
    body:
      "Dry AMD with drusen and RPE mottling, no fluid or hemorrhage.",
    tags: [
      "amd", "armd", "dry", "drusen", "rpe", "rpe mottling",
      "nonexudative", "macula", "no fluid", "no hemorrhage",
    ],
  },
  {
    id: "amd-02",
    group: "Wet/Dry AMD",
    body:
      "Intermediate nonexudative AMD with large confluent drusen and " +
      "pigmentary change.",
    tags: [
      "amd", "armd", "intermediate", "nonexudative",
      "drusen", "confluent", "pigmentary", "rpe", "macula",
    ],
  },
  {
    id: "amd-03",
    group: "Wet/Dry AMD",
    body:
      "Exudative AMD with persistent / improved / worsened intraretinal " +
      "fluid, subretinal fluid, and/or PED. No new macular hemorrhage " +
      "on exam today.",
    tags: [
      "amd", "armd", "exudative", "wet amd", "wet",
      "irf", "intraretinal fluid", "srf", "subretinal fluid",
      "ped", "pigment epithelial detachment",
      "macular hemorrhage", "macula", "oct", "injection",
    ],
  },

  // ---------- Diabetic retinopathy / DME ----------
  // Conservative clinician shorthand; stage-language is stable across
  // the ETDRS / ICDRS vocabularies that AAO documentation uses.
  {
    id: "dm-01",
    group: "Diabetic retinopathy / DME",
    body:
      "NPDR without DME in both eyes; stable. Continue yearly DFE and " +
      "systemic glycemic control.",
    tags: [
      "npdr", "dm", "dme", "diabetic retinopathy", "diabetic",
      "dfe", "yearly", "observation",
    ],
  },
  {
    id: "dm-02",
    group: "Diabetic retinopathy / DME",
    body:
      "Moderate NPDR with center-involving DME on OCT; recommend " +
      "intravitreal anti-VEGF injection ___.",
    tags: [
      "npdr", "dme", "macular edema", "anti-vegf", "injection",
      "diabetic retinopathy", "oct", "csdme",
    ],
  },
  {
    id: "dm-03",
    group: "Diabetic retinopathy / DME",
    body:
      "PDR s/p PRP, stable without new NVD or NVE. Continue close " +
      "interval follow-up.",
    tags: [
      "pdr", "prp", "panretinal photocoagulation", "nvd", "nve",
      "neovascularization", "diabetic retinopathy", "s/p",
    ],
  },
  {
    id: "dm-04",
    group: "Diabetic retinopathy / DME",
    body:
      "Active PDR with NVD / NVE on exam; recommend completion of " +
      "PRP ___ sessions. Anti-VEGF considered as adjunct.",
    tags: [
      "pdr", "nvd", "nve", "neovascularization", "prp",
      "panretinal photocoagulation", "anti-vegf", "active",
    ],
  },
  {
    id: "dm-05",
    group: "Diabetic retinopathy / DME",
    body:
      "Center-involved DME on OCT with central subfield thickness ___ " +
      "microns; plan anti-VEGF.",
    tags: [
      "dme", "cme", "macular edema", "oct", "csdme",
      "anti-vegf", "central subfield", "microns", "injection",
    ],
  },

  // ---------- ERM / VMT / macular hole ----------
  {
    id: "mac-01",
    group: "ERM / VMT / macular hole",
    body:
      "ERM with mild metamorphopsia, VA ___. Observation vs. PPV with " +
      "membrane peel discussed; patient elected ___.",
    tags: [
      "erm", "epiretinal membrane", "metamorphopsia", "ppv",
      "membrane peel", "macula", "vitrectomy", "va",
    ],
  },
  {
    id: "mac-02",
    group: "ERM / VMT / macular hole",
    body:
      "VMT on OCT with foveal distortion, VA ___; observation vs. PPV " +
      "discussed.",
    tags: [
      "vmt", "vitreomacular traction", "oct", "foveal",
      "ppv", "vitrectomy", "macula", "va",
    ],
  },
  {
    id: "mac-03",
    group: "ERM / VMT / macular hole",
    body:
      "Full-thickness macular hole, stage ___, aperture size ___ microns; " +
      "recommend PPV with ILM peel and gas tamponade.",
    tags: [
      "ftmh", "macular hole", "mh", "ppv", "vitrectomy",
      "ilm", "internal limiting membrane", "gas", "tamponade",
      "microns", "stage",
    ],
  },
  {
    id: "mac-04",
    group: "ERM / VMT / macular hole",
    body:
      "Post-op s/p PPV + ILM peel for FTMH; macular hole closed on OCT, " +
      "VA improving.",
    tags: [
      "ftmh", "macular hole", "postop", "post-op", "s/p",
      "ppv", "ilm", "oct", "closed", "va",
    ],
  },
  {
    id: "mac-05",
    group: "ERM / VMT / macular hole",
    body:
      "Lamellar macular hole, stable on OCT, no surgical indication today. " +
      "Reassess in ___ months.",
    tags: [
      "lamellar", "macular hole", "mh", "oct", "stable",
      "observation",
    ],
  },

  // ---------- BRVO / CRVO / retinal vascular ----------
  {
    id: "vasc-01",
    group: "BRVO / CRVO / retinal vascular",
    body:
      "BRVO involving the ___ quadrant with intraretinal hemorrhage and " +
      "cotton-wool spots; macular edema on OCT. Plan anti-VEGF.",
    tags: [
      "brvo", "branch retinal vein occlusion", "intraretinal hemorrhage",
      "cotton-wool spots", "macular edema", "me", "oct", "anti-vegf",
      "injection",
    ],
  },
  {
    id: "vasc-02",
    group: "BRVO / CRVO / retinal vascular",
    body:
      "Non-ischemic CRVO with diffuse intraretinal hemorrhage in 4 " +
      "quadrants; macular edema on OCT. Plan anti-VEGF and monitor " +
      "conversion to ischemic.",
    tags: [
      "crvo", "central retinal vein occlusion", "non-ischemic",
      "intraretinal hemorrhage", "macular edema", "me", "oct",
      "anti-vegf", "injection",
    ],
  },
  {
    id: "vasc-03",
    group: "BRVO / CRVO / retinal vascular",
    body:
      "Ischemic CRVO with extensive capillary non-perfusion on FA; monitor " +
      "closely for anterior segment neovascularization and neovascular " +
      "glaucoma.",
    tags: [
      "crvo", "central retinal vein occlusion", "ischemic",
      "capillary non-perfusion", "fa", "fluorescein angiography",
      "nvg", "neovascular glaucoma", "nvi",
      "anterior segment neovascularization",
    ],
  },
  {
    id: "vasc-04",
    group: "BRVO / CRVO / retinal vascular",
    body:
      "BRAO with segmental retinal whitening along the distribution of " +
      "the ___ arteriole; workup for embolic source initiated.",
    tags: [
      "brao", "branch retinal artery occlusion",
      "retinal whitening", "embolic", "arteriole", "workup",
    ],
  },
  {
    id: "vasc-05",
    group: "BRVO / CRVO / retinal vascular",
    body:
      "Hypertensive retinopathy with AV nicking and scattered cotton-wool " +
      "spots; blood pressure control counseled with PCP.",
    tags: [
      "hypertensive retinopathy", "htn", "av nicking",
      "cotton-wool spots", "pcp", "counseling",
    ],
  },

  // ---------- Post-injection / post-vitrectomy / post-op ----------
  {
    id: "post-01",
    group: "Post-injection / post-vitrectomy / post-op",
    body:
      "Intravitreal ___ injection OS performed under sterile technique " +
      "with 5% povidone-iodine and lid speculum; patient tolerated well, " +
      "no immediate complications.",
    tags: [
      "injection", "anti-vegf", "intravitreal", "ivt",
      "postop", "procedure", "os", "povidone",
    ],
  },
  {
    id: "post-02",
    group: "Post-injection / post-vitrectomy / post-op",
    body:
      "Post-injection return precautions reviewed in detail: pain, " +
      "redness, worsening vision, or increasing floaters warrant urgent " +
      "contact to r/o endophthalmitis or RD.",
    tags: [
      "injection", "postop", "counseling", "precautions",
      "endophthalmitis", "rd", "retinal detachment", "r/o",
    ],
  },
  {
    id: "post-03",
    group: "Post-injection / post-vitrectomy / post-op",
    body:
      "Post-op day ___ s/p PPV: retina attached, IOP ___ mmHg, AC quiet, " +
      "no evidence of endophthalmitis. Continue topical steroid / " +
      "antibiotic taper.",
    tags: [
      "postop", "post-op", "s/p", "ppv", "vitrectomy",
      "iop", "ac", "endophthalmitis", "steroid", "antibiotic",
    ],
  },
  {
    id: "post-04",
    group: "Post-injection / post-vitrectomy / post-op",
    body:
      "Post-op week ___ s/p scleral buckle: buckle in good position, " +
      "retina attached 360°, no SRF on exam.",
    tags: [
      "postop", "post-op", "s/p", "sb", "scleral buckle",
      "retina attached", "srf", "subretinal fluid",
    ],
  },
  {
    id: "post-05",
    group: "Post-injection / post-vitrectomy / post-op",
    body:
      "Post-op s/p PRP with good laser uptake; no progression of PDR or " +
      "new NVE on exam today.",
    tags: [
      "postop", "post-op", "s/p", "prp", "panretinal photocoagulation",
      "pdr", "nve", "neovascularization", "laser",
    ],
  },

  // ---------- Glaucoma ----------
  // Conservative AAO-style phrasing. C/D, RNFL, VF, target-IOP
  // language is stable across AOA/ICO glaucoma documentation.
  {
    id: "glc-01",
    group: "Glaucoma",
    body:
      "POAG, ___ severity, OD C/D ___ / OS C/D ___; VF ___ and RNFL ___ " +
      "on OCT; currently on ___ drops. Target IOP ___.",
    tags: [
      "poag", "open angle glaucoma", "glc", "c/d", "vf", "rnfl",
      "oct", "target iop", "iop", "drops",
    ],
  },
  {
    id: "glc-02",
    group: "Glaucoma",
    body:
      "Ocular hypertension without glaucomatous optic neuropathy; C/D ___, " +
      "IOP ___, CCT ___ microns. Continue monitoring; target IOP ___.",
    tags: [
      "oht", "ocular hypertension", "c/d", "iop", "cct", "pachymetry",
      "target iop", "glc",
    ],
  },
  {
    id: "glc-03",
    group: "Glaucoma",
    body:
      "Pseudoexfoliation / pigment dispersion on gonioscopy with " +
      "secondary open-angle glaucoma; on ___ drops, target IOP ___.",
    tags: [
      "pxf", "pseudoexfoliation", "pds", "pigment dispersion",
      "pdg", "pxfg", "gonioscopy", "iop", "glc", "drops",
    ],
  },
  {
    id: "glc-04",
    group: "Glaucoma",
    body:
      "Narrow angles on gonioscopy OU without evidence of angle-closure; " +
      "recommend prophylactic LPI ___.",
    tags: [
      "nag", "narrow angles", "gonioscopy", "lpi",
      "angle closure", "acg", "glc",
    ],
  },
  {
    id: "glc-05",
    group: "Glaucoma",
    body:
      "Post-op s/p trabeculectomy: bleb diffuse and functional, AC deep, " +
      "IOP ___; continue topical steroid taper, strict no-rubbing.",
    tags: [
      "postop", "post-op", "s/p", "trab", "trabeculectomy", "bleb",
      "iop", "ac", "glc", "steroid",
    ],
  },
  {
    id: "glc-06",
    group: "Glaucoma",
    body:
      "Post-op s/p glaucoma drainage device: tube in good position in AC, " +
      "no conjunctival erosion over plate; IOP ___.",
    tags: [
      "postop", "post-op", "s/p", "tube shunt", "gdd", "ahmed", "baerveldt",
      "tube", "iop", "glc",
    ],
  },

  // ---------- Cornea / anterior segment ----------
  {
    id: "cor-01",
    group: "Cornea / anterior segment",
    body:
      "Dry eye disease with punctate epithelial staining OU and reduced " +
      "tear break-up time; Schirmer ___ mm. Start / continue artificial " +
      "tears, warm compresses, and lid hygiene.",
    tags: [
      "ded", "dry eye", "kcs", "spk", "punctate",
      "tbu", "tear break-up", "schirmer", "at", "artificial tears",
      "warm compress", "lid hygiene",
    ],
  },
  {
    id: "cor-02",
    group: "Cornea / anterior segment",
    body:
      "Meibomian gland dysfunction with inspissated glands, lid-margin " +
      "telangiectasia, and posterior blepharitis.",
    tags: [
      "mgd", "meibomian gland dysfunction", "img", "blepharitis",
      "lid hygiene", "lids", "ded",
    ],
  },
  {
    id: "cor-03",
    group: "Cornea / anterior segment",
    body:
      "Keratoconus with inferior steepening on topography; K-max ___, " +
      "thinnest pachymetry ___ microns. Discussed observation vs. CXL.",
    tags: [
      "kc", "keratoconus", "topography", "topo", "k-max",
      "pachymetry", "cxl", "corneal cross-linking",
    ],
  },
  {
    id: "cor-04",
    group: "Cornea / anterior segment",
    body:
      "Recurrent corneal erosion OS with epithelial loosening; start " +
      "BSCL and aggressive lubrication, consider debridement or PTK if " +
      "refractory.",
    tags: [
      "rce", "recurrent corneal erosion", "corab", "erosion",
      "bscl", "bsl", "bandage contact lens", "lubrication",
      "ptk", "debridement",
    ],
  },
  {
    id: "cor-05",
    group: "Cornea / anterior segment",
    body:
      "Fuchs endothelial dystrophy with central guttae and mild stromal " +
      "edema; pachymetry ___ microns. Monitor with pachymetry + " +
      "specular microscopy; counsel regarding DSEK when visually " +
      "significant.",
    tags: [
      "fuchs", "endothelial dystrophy", "guttae", "stromal edema",
      "pachymetry", "specular microscopy", "dsek", "cornea",
    ],
  },
  {
    id: "cor-06",
    group: "Cornea / anterior segment",
    body:
      "Post-op s/p DSEK: graft well-adhered, no interface fluid on OCT, " +
      "AC quiet; continue steroid taper and no-rub precautions.",
    tags: [
      "postop", "post-op", "s/p", "dsek", "graft", "oct",
      "ac", "steroid", "cornea",
    ],
  },
];

/**
 * Curated abbreviation reference.
 *
 * Narrowed from the Spokane Eye Clinic common-ophthalmic sheet to
 * the terms that appear in — or are likely-searched alongside —
 * the shipped shortcuts. The UI uses this for:
 *   1. subtle hover hints on highlighted abbreviations inside the
 *      shortcut body (via `<abbr title>`),
 *   2. abbreviation-aware search: typing "SRF" finds shortcuts
 *      whose tags include "srf" even if the body spells out
 *      "subretinal fluid".
 *
 * Keep this list short. Adding every term in the sheet would clutter
 * the UI; add an entry here only when a live shortcut uses it or a
 * clinician is likely to search for it.
 */
export const ABBREVIATION_HINTS: Record<string, string> = {
  AC: "Anterior chamber",
  AMD: "Age-related macular degeneration",
  ARMD: "Age-related macular degeneration",
  BRAO: "Branch retinal artery occlusion",
  BRVO: "Branch retinal vein occlusion",
  CME: "Cystoid macular edema",
  "C/D": "Cup-to-disc ratio",
  CRAO: "Central retinal artery occlusion",
  CRVO: "Central retinal vein occlusion",
  DFE: "Dilated fundus exam",
  DM: "Diabetes mellitus",
  DME: "Diabetic macular edema",
  "D&Q": "Deep and quiet (anterior chamber)",
  ERM: "Epiretinal membrane",
  FA: "Fluorescein angiography",
  FTMH: "Full-thickness macular hole",
  ILM: "Internal limiting membrane",
  IOP: "Intraocular pressure",
  IRF: "Intraretinal fluid",
  IVT: "Intravitreal injection",
  ME: "Macular edema",
  MH: "Macular hole",
  NPDR: "Non-proliferative diabetic retinopathy",
  NV: "Neovascularization",
  NVD: "Neovascularization of the disc",
  NVE: "Neovascularization elsewhere",
  NVG: "Neovascular glaucoma",
  NVI: "Neovascularization of the iris",
  OCT: "Optical coherence tomography",
  ONH: "Optic nerve head",
  OD: "Right eye (oculus dexter)",
  OS: "Left eye (oculus sinister)",
  OU: "Both eyes (oculus uterque)",
  PCP: "Primary care physician",
  PED: "Pigment epithelial detachment",
  PDR: "Proliferative diabetic retinopathy",
  PPV: "Pars plana vitrectomy",
  PR: "Pneumatic retinopexy",
  PRP: "Pan-retinal photocoagulation",
  PVD: "Posterior vitreous detachment",
  RAPD: "Relative afferent pupillary defect",
  RD: "Retinal detachment",
  RPE: "Retinal pigment epithelium",
  RT: "Retinal tear",
  SB: "Scleral buckle",
  SLE: "Slit lamp exam",
  SRF: "Subretinal fluid",
  "S/P": "Status post",
  VA: "Visual acuity",
  VMT: "Vitreomacular traction",
  // ---- Glaucoma ----
  ACG: "Angle-closure glaucoma",
  CCT: "Central corneal thickness",
  GDD: "Glaucoma drainage device",
  LPI: "Laser peripheral iridotomy",
  NAG: "Narrow-angle glaucoma",
  OHT: "Ocular hypertension",
  PDG: "Pigmentary dispersion glaucoma",
  PDS: "Pigment dispersion syndrome",
  POAG: "Primary open-angle glaucoma",
  PXF: "Pseudoexfoliation",
  PXFG: "Pseudoexfoliative glaucoma",
  RNFL: "Retinal nerve fiber layer",
  SLT: "Selective laser trabeculoplasty",
  Trab: "Trabeculectomy",
  VF: "Visual field",
  // ---- Cornea / anterior segment ----
  AT: "Artificial tears",
  BSCL: "Bandage soft contact lens",
  CXL: "Corneal cross-linking",
  DED: "Dry eye disease",
  DSEK: "Descemet stripping endothelial keratoplasty",
  KC: "Keratoconus",
  KCS: "Keratoconjunctivitis sicca",
  MGD: "Meibomian gland dysfunction",
  PTK: "Phototherapeutic keratectomy",
  RCE: "Recurrent corneal erosion",
  SPK: "Superficial punctate keratitis",
  TBU: "Tear break-up time",
};

/** Ordered list of abbreviation tokens, longest-first, so a body
 *  containing e.g. "NPDR" isn't split as "N" + "PDR" when we scan
 *  for hover-help targets. */
export const ABBREVIATION_TOKENS: string[] = Object.keys(ABBREVIATION_HINTS)
  .slice()
  .sort((a, b) => b.length - a.length);

/** Abbreviation-aware search.
 *
 *  Matches against the union of: the shortcut body, the group name,
 *  the tag list, and — crucially — the expanded meaning of any
 *  abbreviation whose token appears in the search query. So typing
 *  "retinal detachment" hits everything tagged "rd", and typing "rd"
 *  hits everything whose tags include "rd" OR whose body contains
 *  the phrase "retinal detachment".
 *
 *  Pure function: no DOM, no state — safe to call in filters + tests.
 */
export function clinicalShortcutMatches(
  s: ClinicalShortcut,
  rawQuery: string
): boolean {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return true;

  const haystack =
    (s.body + "\n" + s.group + "\n" + s.tags.join(" ")).toLowerCase();

  if (haystack.includes(query)) return true;

  // If the query is (or contains) an abbreviation we know, also
  // match against its expanded meaning. E.g. `rd` ↔ "retinal
  // detachment".
  for (const abbr of ABBREVIATION_TOKENS) {
    const lowerAbbr = abbr.toLowerCase();
    if (query.includes(lowerAbbr) || lowerAbbr.includes(query)) {
      const meaning = ABBREVIATION_HINTS[abbr].toLowerCase();
      if (haystack.includes(meaning)) return true;
      // Also match if any tag token equals the abbreviation itself.
      if (s.tags.map((t) => t.toLowerCase()).includes(lowerAbbr)) return true;
    }
  }
  return false;
}

/**
 * Split a shortcut body into tokens, wrapping any abbreviation token
 * found in `ABBREVIATION_HINTS` so the UI can render it as
 * `<abbr title="...">` for subtle hover help. Returns a flat array of
 * either plain strings (inert text) or {abbr, meaning} markers.
 *
 * Word-boundary guard: we only wrap when the abbreviation appears as
 * its own token, not as a substring of a longer word (so "IRF" in
 * "INTRAOCULAR IRFACE" — which doesn't exist but defensively — would
 * not match). Case-sensitive because these abbreviations are always
 * uppercase in clinical notes.
 */
export type AbbrSegment = string | { abbr: string; meaning: string };

export function segmentAbbreviations(body: string): AbbrSegment[] {
  // Build a single regex that matches any abbreviation token on a
  // word boundary. We escape a few chars that appear in the sheet
  // (slash, ampersand) so `C/D` and `D&Q` survive.
  const escaped = ABBREVIATION_TOKENS.map((t) =>
    t.replace(/[.*+?^${}()|[\]\\/&]/g, "\\$&")
  );
  // Use lookarounds to avoid matching inside longer alpha tokens;
  // `\b` alone doesn't work for tokens that contain a slash like
  // `C/D` or `S/P`. The `i` flag lets us pick up the lowercase
  // shorthand clinicians actually write ("s/p PPV" etc.) while the
  // hint lookup uses the canonical uppercase key. The word-boundary
  // lookaround prevents false positives on substrings inside ordinary
  // prose ("macula" does not match AC, "vasopressor" does not match
  // VA, etc.).
  const pattern = new RegExp(
    `(^|[^A-Za-z0-9])(${escaped.join("|")})(?=[^A-Za-z0-9]|$)`,
    "gi"
  );

  const out: AbbrSegment[] = [];
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(body)) !== null) {
    const [, leading, token] = m;
    const matchStart = m.index + leading.length;
    if (matchStart > lastIndex) out.push(body.slice(lastIndex, matchStart));
    const key = token.toUpperCase();
    const meaning = ABBREVIATION_HINTS[key] ?? ABBREVIATION_HINTS[token];
    // Preserve the source capitalization in the rendered `<abbr>` so
    // the note fragment reads as the clinician wrote it, not as the
    // canonical key.
    out.push({ abbr: token, meaning });
    lastIndex = matchStart + token.length;
  }
  if (lastIndex < body.length) out.push(body.slice(lastIndex));
  return out;
}

/**
 * Placeholder token used inside shortcut bodies to mark a
 * fill-in-the-blank target. Clinical phrasing like
 * `involving ___ quadrants` or `from ___ to ___ o'clock` signals the
 * doctor needs to land the caret on the first `___` right after
 * insertion so they can type over it immediately.
 */
export const SHORTCUT_BLANK_TOKEN = "___";

/**
 * Return the zero-based offset of the first `___` placeholder inside
 * `body`, or `-1` if none exists. Callers use this to jump the caret
 * (and optionally select the placeholder) after insertion so typing
 * replaces it in one gesture.
 */
export function firstBlankOffset(body: string): number {
  return body.indexOf(SHORTCUT_BLANK_TOKEN);
}

/**
 * Return the zero-based offset of the NEXT `___` placeholder at or
 * after `fromOffset`, or `-1` if none remains. Used by the Tab
 * handler in the draft textarea to walk from one blank to the next
 * without leaving the field.
 */
export function nextBlankAfter(body: string, fromOffset: number): number {
  const safeFrom = Math.max(0, fromOffset | 0);
  return body.indexOf(SHORTCUT_BLANK_TOKEN, safeFrom);
}

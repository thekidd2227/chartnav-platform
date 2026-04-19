// Phase 27 — clinician quick-comment pad.
//
// The preloaded ophthalmology pack is pure UI content, shipped with
// the frontend bundle. It lives here (not in the backend) because:
//
// 1. It is not per-user (everyone sees the same preloaded picks), so
//    a DB seed would add persistence machinery for no gain.
// 2. It never needs to be edited at runtime — only the doctor's
//    custom comments do, and those go through `/me/quick-comments`.
// 3. Keeping it as a static import means zero-latency render on
//    every NoteWorkspace mount.
//
// Provenance: these are clinician-selected snippets. They are NOT
// AI-generated findings and they are NOT transcript-derived. The UI
// surfaces that distinction prominently.

export interface PreloadedQuickComment {
  id: string;
  category: QuickCommentCategory;
  body: string;
}

export type QuickCommentCategory =
  | "Symptoms / HPI"
  | "Visual function / basic exam"
  | "External / anterior segment"
  | "Posterior segment"
  | "Assessment / plan / counseling";

export const QUICK_COMMENT_CATEGORIES: QuickCommentCategory[] = [
  "Symptoms / HPI",
  "Visual function / basic exam",
  "External / anterior segment",
  "Posterior segment",
  "Assessment / plan / counseling",
];

// Each entry is a verbatim preloaded pick per the product brief.
// IDs are stable strings (not indexes) so saving a favorite later
// doesn't break if the list is reordered.
export const PRELOADED_QUICK_COMMENTS: PreloadedQuickComment[] = [
  // 1–20 Symptoms / HPI
  { id: "sx-01", category: "Symptoms / HPI", body: "Vision stable since last visit." },
  { id: "sx-02", category: "Symptoms / HPI", body: "Reports gradual blur at distance." },
  { id: "sx-03", category: "Symptoms / HPI", body: "Reports gradual blur at near." },
  { id: "sx-04", category: "Symptoms / HPI", body: "Denies flashes." },
  { id: "sx-05", category: "Symptoms / HPI", body: "Reports intermittent flashes." },
  { id: "sx-06", category: "Symptoms / HPI", body: "Denies new floaters." },
  { id: "sx-07", category: "Symptoms / HPI", body: "Reports new floaters." },
  { id: "sx-08", category: "Symptoms / HPI", body: "Denies curtain or shadow in vision." },
  { id: "sx-09", category: "Symptoms / HPI", body: "Reports glare, worse at night." },
  { id: "sx-10", category: "Symptoms / HPI", body: "Reports halos around lights." },
  { id: "sx-11", category: "Symptoms / HPI", body: "Reports photophobia." },
  { id: "sx-12", category: "Symptoms / HPI", body: "Denies eye pain." },
  { id: "sx-13", category: "Symptoms / HPI", body: "Reports foreign body sensation." },
  { id: "sx-14", category: "Symptoms / HPI", body: "Reports burning and dryness." },
  { id: "sx-15", category: "Symptoms / HPI", body: "Reports tearing/watering." },
  { id: "sx-16", category: "Symptoms / HPI", body: "Reports intermittent redness." },
  { id: "sx-17", category: "Symptoms / HPI", body: "Reports itching." },
  { id: "sx-18", category: "Symptoms / HPI", body: "Denies diplopia." },
  { id: "sx-19", category: "Symptoms / HPI", body: "Reports intermittent diplopia." },
  { id: "sx-20", category: "Symptoms / HPI", body: "Symptoms improved with artificial tears." },

  // 21–30 Visual function / basic exam
  { id: "vf-21", category: "Visual function / basic exam", body: "Visual acuity reviewed and documented." },
  { id: "vf-22", category: "Visual function / basic exam", body: "Pinhole improves vision." },
  { id: "vf-23", category: "Visual function / basic exam", body: "No improvement with pinhole." },
  { id: "vf-24", category: "Visual function / basic exam", body: "Pupils round and reactive." },
  { id: "vf-25", category: "Visual function / basic exam", body: "No RAPD." },
  { id: "vf-26", category: "Visual function / basic exam", body: "EOM full." },
  { id: "vf-27", category: "Visual function / basic exam", body: "Confrontation fields full." },
  { id: "vf-28", category: "Visual function / basic exam", body: "Color vision not formally tested today." },
  { id: "vf-29", category: "Visual function / basic exam", body: "IOP reviewed and documented." },
  { id: "vf-30", category: "Visual function / basic exam", body: "IOP acceptable today." },

  // 31–40 External / anterior segment
  { id: "ant-31", category: "External / anterior segment", body: "Lids/lashes with mild blepharitis changes." },
  { id: "ant-32", category: "External / anterior segment", body: "Lids/lashes without acute abnormality." },
  { id: "ant-33", category: "External / anterior segment", body: "Conjunctiva with mild injection." },
  { id: "ant-34", category: "External / anterior segment", body: "Conjunctiva quiet." },
  { id: "ant-35", category: "External / anterior segment", body: "Cornea clear." },
  { id: "ant-36", category: "External / anterior segment", body: "Mild punctate epithelial staining present." },
  { id: "ant-37", category: "External / anterior segment", body: "No epithelial defect." },
  { id: "ant-38", category: "External / anterior segment", body: "Anterior chamber deep and quiet." },
  { id: "ant-39", category: "External / anterior segment", body: "Iris architecture normal." },
  { id: "ant-40", category: "External / anterior segment", body: "Lens changes consistent with cataract progression." },

  // 41–47 Posterior segment
  { id: "post-41", category: "Posterior segment", body: "Dilated fundus exam performed today." },
  { id: "post-42", category: "Posterior segment", body: "Optic nerve appearance stable." },
  { id: "post-43", category: "Posterior segment", body: "Cup-to-disc ratio stable from prior." },
  { id: "post-44", category: "Posterior segment", body: "Macula flat and dry." },
  { id: "post-45", category: "Posterior segment", body: "No retinal tear or detachment seen on exam." },
  { id: "post-46", category: "Posterior segment", body: "Peripheral retina attached 360 degrees." },
  { id: "post-47", category: "Posterior segment", body: "No acute posterior segment finding identified today." },

  // 48–50 Assessment / plan / counseling
  { id: "plan-48", category: "Assessment / plan / counseling", body: "Findings reviewed with patient." },
  { id: "plan-49", category: "Assessment / plan / counseling", body: "Return precautions reviewed in detail." },
  { id: "plan-50", category: "Assessment / plan / counseling", body: "Follow-up interval reviewed and agreed upon." },
];

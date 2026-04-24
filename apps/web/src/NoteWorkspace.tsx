/**
 * Provider review workspace (phase 19).
 *
 * Renders the encounter's transcript-to-note pipeline in three
 * visibly-distinct tiers so the trust model stays legible:
 *
 *   1. TRANSCRIPT  — raw operator input. Source of record for
 *                    what actually came out of the encounter.
 *   2. FINDINGS    — structured facts the generator extracted.
 *                    Read-only in the UI; surfaces confidence +
 *                    missing-data flags.
 *   3. DRAFT       — provider-editable narrative. `revised`
 *                    state and `generated_by: manual` label
 *                    whenever the provider has touched it.
 *
 * The component is intentionally NOT a generic "notes form." It
 * forces the operator through verify → submit → sign → export and
 * refuses edits once the note is signed.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  ClinicalShortcutFavorite,
  ClinicianQuickComment,
  ClinicianQuickCommentFavorite,
  EncounterInput,
  ExtractedFindings,
  Me,
  MISSING_FLAG_LABELS,
  NoteVersion,
  ArtifactFormat,
  NoteTransmission,
  createEncounterInput,
  createMyQuickComment,
  patchEncounterInputTranscript,
  uploadEncounterAudio,
  deleteMyQuickComment,
  downloadNoteArtifact,
  exportNoteVersion,
  favoriteClinicalShortcut,
  favoriteQuickComment,
  generateNoteVersion,
  getPlatform,
  listMyClinicalShortcutFavorites,
  listMyQuickComments,
  listMyQuickCommentFavorites,
  listNoteTransmissions,
  recordClinicalShortcutUsage,
  recordQuickCommentUsage,
  transmitNoteVersion,
  unfavoriteClinicalShortcut,
  unfavoriteQuickComment,
  updateMyQuickComment,
  getNoteVersion,
  listEncounterInputs,
  listEncounterNotes,
  patchNoteVersion,
  processEncounterInput,
  retryEncounterInput,
  signNoteVersion,
  submitNoteForReview,
} from "./api";
import {
  PRELOADED_QUICK_COMMENTS,
  QUICK_COMMENT_CATEGORIES,
  type QuickCommentCategory,
} from "./quickComments";
import {
  BrowserCaptureError,
  type BrowserRecording,
  type BrowserCaptureSupport,
  detectBrowserCapture,
  startBrowserRecording,
} from "./audioRecorder";
import {
  ABBREVIATION_HINTS,
  CLINICAL_SHORTCUTS,
  CLINICAL_SHORTCUT_GROUPS,
  SHORTCUT_BLANK_TOKEN,
  clinicalShortcutMatches,
  firstBlankOffset,
  nextBlankAfter,
  prevBlankBefore,
  segmentAbbreviations,
  type ClinicalShortcut,
} from "./clinicalShortcuts";

// Phase 38 — doctor expansion.
import {
  CustomShortcut,
  listMyCustomShortcuts,
  createMyCustomShortcut,
  deleteMyCustomShortcut,
} from "./api";
import { TrustBadge, trustKindForNote } from "./TrustBadge";
import { NoteDiff } from "./NoteDiff";
import { DualView } from "./DualView";
import { VOICE_MODE_REGISTRY, VOICE_MODES, VoiceMode } from "./voiceModes";

// ROI wave 1 — doctor-side additions (ExamSummary, NextBestAction,
// PreSignCheckpoint). Implementation details live inside each
// component; NoteWorkspace only owns the wiring.
import { ExamSummary } from "./ExamSummary";
import { NextBestAction } from "./NextBestAction";
import { PreSignCheckpoint, shouldCheckpoint } from "./PreSignCheckpoint";

// ---------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------

interface Props {
  identity: string;
  me: Me;
  encounterId: number;
  patientDisplay: string;
  providerDisplay: string;
}

interface Flash {
  kind: "ok" | "error" | "info";
  msg: string;
}

// ---------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------

export function NoteWorkspace({
  identity,
  me,
  encounterId,
  patientDisplay,
  providerDisplay,
}: Props) {
  const [inputs, setInputs] = useState<EncounterInput[]>([]);
  const [notes, setNotes] = useState<NoteVersion[]>([]);
  const [activeNoteId, setActiveNoteId] = useState<number | null>(null);
  const [activeNote, setActiveNote] = useState<NoteVersion | null>(null);
  const [activeFindings, setActiveFindings] =
    useState<ExtractedFindings | null>(null);
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState<Flash | null>(null);
  const [editBody, setEditBody] = useState<string | null>(null);
  const [newTranscript, setNewTranscript] = useState("");
  // Phase 33 — audio intake + transcript review. `audioFile` holds the
  // selected File object while the doctor reviews size/name before
  // submitting; `audioUploading` drives the spinner. Transcript edits
  // are a separate, modal-ish buffer so the clinician can revert
  // without losing the original placeholder.
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioUploading, setAudioUploading] = useState(false);

  // Phase 36 — browser microphone capture state. Detected once per
  // mount because the browser's MediaRecorder support doesn't change
  // mid-session. The recorder controller is held in a ref so a
  // re-render doesn't drop the in-flight `MediaRecorder`.
  const captureSupport = useMemo<BrowserCaptureSupport>(
    () => detectBrowserCapture(),
    []
  );
  type RecorderState =
    | { kind: "idle" }
    | { kind: "recording"; controller: BrowserRecording; startedAt: number }
    | { kind: "recorded"; file: File }
    | { kind: "uploading"; file: File };
  const [recorderState, setRecorderState] = useState<RecorderState>({
    kind: "idle",
  });
  const [recordedElapsedSec, setRecordedElapsedSec] = useState(0);
  // Forces the elapsed-time display to tick. We keep the source of
  // truth in the recorder controller; this is just a UI nudge.
  useEffect(() => {
    if (recorderState.kind !== "recording") return;
    const id = setInterval(() => {
      setRecordedElapsedSec(
        Math.floor((Date.now() - recorderState.startedAt) / 1000)
      );
    }, 250);
    return () => clearInterval(id);
  }, [recorderState]);
  const [transcriptEditInputId, setTranscriptEditInputId] = useState<
    number | null
  >(null);
  const [transcriptEditValue, setTranscriptEditValue] = useState("");
  // Phase 26 — signed-note transmission surface. The transmit button
  // only renders when the backend advertises `document_transmit: true`
  // via `GET /platform`. We fetch once per mount; platform config
  // doesn't change at runtime.
  const [transmitSupported, setTransmitSupported] = useState(false);
  const [transmissions, setTransmissions] = useState<NoteTransmission[]>([]);

  // Phase 27 — doctor-only quick-comment pad. Preloaded pack is static
  // UI content (ships with the bundle); custom comments live on the
  // backend under `/me/quick-comments`. All state is per-user.
  const [customComments, setCustomComments] = useState<
    ClinicianQuickComment[]
  >([]);
  const [qcSearch, setQcSearch] = useState("");
  const [qcModalOpen, setQcModalOpen] = useState(false);
  const [qcDraft, setQcDraft] = useState("");
  const [qcEditingId, setQcEditingId] = useState<number | null>(null);

  // Phase 28 — favorites + cursor-insertion. The textarea ref lets the
  // click handler splice at selectionStart rather than always
  // appending to the end.
  const [favorites, setFavorites] = useState<
    ClinicianQuickCommentFavorite[]
  >([]);
  const draftTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Phase 29 — Clinical Shortcuts. Static content, separate search
  // state so the specialist pack doesn't fight the quick-comments
  // filter. Abbreviation-aware matching lives in
  // `clinicalShortcutMatches` (see clinicalShortcuts.ts).
  const [shortcutSearch, setShortcutSearch] = useState("");

  // Phase 38 — doctor expansion state:
  //   - customShortcuts: the doctor's authored "my patterns" list.
  //     Lives in `clinician_custom_shortcuts`; loaded per-identity.
  //   - showDiff: toggles the NoteDiff comparator (A5).
  //   - showDualView: toggles the DualView transcript↔draft split (A2).
  //   - voiceMode: "ambient" (default) vs "targeted" push-to-talk (A4).
  const [customShortcuts, setCustomShortcuts] = useState<CustomShortcut[]>([]);
  const [newPatternBody, setNewPatternBody] = useState("");
  const [newPatternPending, setNewPatternPending] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [showDualView, setShowDualView] = useState(false);
  const [voiceMode, setVoiceMode] = useState<VoiceMode>("ambient");

  // Load custom shortcuts once per identity; refresh when the
  // list changes (create/delete).
  const refreshCustomShortcuts = useCallback(async () => {
    try {
      const rows = await listMyCustomShortcuts(identity);
      setCustomShortcuts(rows);
    } catch {
      setCustomShortcuts([]);
    }
  }, [identity]);
  useEffect(() => { refreshCustomShortcuts(); }, [refreshCustomShortcuts]);

  const [patternError, setPatternError] = useState<string | null>(null);

  // ROI wave 1 — pre-sign checkpoint gate. When the note's
  // findings confidence is not "high" or missing-data flags exist,
  // the doctor acknowledges a compact review modal before the
  // existing signNoteVersion call fires. The backend still
  // enforces role + state; this is UI discipline, not a new rule.
  const [presignOpen, setPresignOpen] = useState(false);
  const addCustomPattern = async () => {
    const body = newPatternBody.trim();
    if (!body || newPatternPending) return;
    setNewPatternPending(true);
    setPatternError(null);
    try {
      await createMyCustomShortcut(identity, { body });
      setNewPatternBody("");
      await refreshCustomShortcuts();
    } catch (e) {
      setPatternError(friendly(e));
    } finally {
      setNewPatternPending(false);
    }
  };

  const removeCustomPattern = async (id: number) => {
    setPatternError(null);
    try {
      await deleteMyCustomShortcut(identity, id);
      await refreshCustomShortcuts();
    } catch (e) {
      setPatternError(friendly(e));
    }
  };

  // Phase 30 — per-doctor shortcut favorites. Persisted separately
  // from quick-comment favorites (different URL + different table)
  // so the two favoritism models evolve independently.
  const [shortcutFavorites, setShortcutFavorites] = useState<
    ClinicalShortcutFavorite[]
  >([]);

  // Phase 34 — explicit favorites loading state on both surfaces
  // (Quick-Comment Favorites + Clinical-Shortcut Favorites). The
  // strips previously rendered nothing while the network round-trip
  // ran, which made the absence of pins indistinguishable from "the
  // fetch hasn't returned yet". We initialise true so the first
  // paint shows the skeleton; the loaders flip false in their
  // `finally` blocks.
  const [favoritesLoading, setFavoritesLoading] = useState(true);
  const [shortcutFavoritesLoading, setShortcutFavoritesLoading] =
    useState(true);

  const canSign = me.role === "admin" || me.role === "clinician";
  const canEdit = canSign; // same set today
  const noteSigned =
    activeNote?.draft_status === "signed" ||
    activeNote?.draft_status === "exported";
  const noteExported = activeNote?.draft_status === "exported";
  const providerEdited =
    activeNote?.generated_by === "manual" ||
    activeNote?.draft_status === "revised";

  const showFlash = useCallback(
    (kind: Flash["kind"], msg: string) => setFlash({ kind, msg }),
    []
  );

  // ---- loaders ----------------------------------------------------
  const loadInputs = useCallback(async () => {
    try {
      setInputs(await listEncounterInputs(identity, encounterId));
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, encounterId, showFlash]);

  const loadNotes = useCallback(async () => {
    try {
      const list = await listEncounterNotes(identity, encounterId);
      setNotes(list);
      if (list.length && activeNoteId === null) {
        setActiveNoteId(list[0].id);
      }
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, encounterId, activeNoteId, showFlash]);

  const loadActive = useCallback(async () => {
    if (activeNoteId === null) {
      setActiveNote(null);
      setActiveFindings(null);
      setEditBody(null);
      return;
    }
    try {
      const data = await getNoteVersion(identity, activeNoteId);
      setActiveNote(data.note);
      setActiveFindings(data.findings);
      setEditBody(data.note.note_text);
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, activeNoteId, showFlash]);

  useEffect(() => {
    loadInputs();
    loadNotes();
  }, [loadInputs, loadNotes]);

  useEffect(() => {
    loadActive();
  }, [loadActive]);

  // One-shot: is the deployment in a mode + adapter that supports
  // signed-note transmission? The Transmit button + history pane hinge
  // on this. A platform fetch failure (offline / 403) just hides the
  // row — we never show a button that will 100% 409.
  useEffect(() => {
    let cancelled = false;
    getPlatform(identity)
      .then((p) => {
        if (cancelled) return;
        setTransmitSupported(!!p.adapter?.supports?.document_transmit);
      })
      .catch(() => {
        if (!cancelled) setTransmitSupported(false);
      });
    return () => {
      cancelled = true;
    };
  }, [identity]);

  // Transmission history for the active signed note.
  const loadTransmissions = useCallback(async () => {
    if (!activeNoteId || !noteSigned || !transmitSupported) {
      setTransmissions([]);
      return;
    }
    try {
      setTransmissions(await listNoteTransmissions(identity, activeNoteId));
    } catch {
      setTransmissions([]);
    }
  }, [identity, activeNoteId, noteSigned, transmitSupported]);

  useEffect(() => {
    loadTransmissions();
  }, [loadTransmissions]);

  // -------- Quick-comment pad (phase 27) --------
  // Only clinicians + admins can author quick comments, so only they
  // see the panel + list. Reviewers never see it — they cannot edit
  // the note anyway, and the backend would 403 their reads.
  const canUseQuickComments = canEdit;

  const loadCustomComments = useCallback(async () => {
    if (!canUseQuickComments) {
      setCustomComments([]);
      return;
    }
    try {
      setCustomComments(await listMyQuickComments(identity));
    } catch {
      // Silent: the panel just renders empty. A network error here
      // shouldn't block the main workspace.
      setCustomComments([]);
    }
  }, [identity, canUseQuickComments]);

  useEffect(() => {
    loadCustomComments();
  }, [loadCustomComments]);

  const loadFavorites = useCallback(async () => {
    if (!canUseQuickComments) {
      setFavorites([]);
      setFavoritesLoading(false);
      return;
    }
    setFavoritesLoading(true);
    try {
      setFavorites(await listMyQuickCommentFavorites(identity));
    } catch {
      setFavorites([]);
    } finally {
      setFavoritesLoading(false);
    }
  }, [identity, canUseQuickComments]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  // Phase 30 — Clinical Shortcut favorites.
  const loadShortcutFavorites = useCallback(async () => {
    if (!canUseQuickComments) {
      setShortcutFavorites([]);
      setShortcutFavoritesLoading(false);
      return;
    }
    setShortcutFavoritesLoading(true);
    try {
      setShortcutFavorites(await listMyClinicalShortcutFavorites(identity));
    } catch {
      setShortcutFavorites([]);
    } finally {
      setShortcutFavoritesLoading(false);
    }
  }, [identity, canUseQuickComments]);

  useEffect(() => {
    loadShortcutFavorites();
  }, [loadShortcutFavorites]);

  const favoriteShortcutSet = useMemo(
    () => new Set(shortcutFavorites.map((f) => f.shortcut_ref)),
    [shortcutFavorites]
  );

  const toggleShortcutFavorite = useCallback(
    async (shortcutRef: string) => {
      try {
        if (favoriteShortcutSet.has(shortcutRef)) {
          await unfavoriteClinicalShortcut(identity, shortcutRef);
        } else {
          await favoriteClinicalShortcut(identity, shortcutRef);
        }
        await loadShortcutFavorites();
      } catch (e) {
        showFlash("error", friendly(e));
      }
    },
    [identity, favoriteShortcutSet, loadShortcutFavorites, showFlash]
  );

  const favoritePreloadedSet = useMemo(
    () =>
      new Set(
        favorites
          .map((f) => f.preloaded_ref)
          .filter((r): r is string => typeof r === "string" && r.length > 0)
      ),
    [favorites]
  );
  const favoriteCustomSet = useMemo(
    () =>
      new Set(
        favorites
          .map((f) => f.custom_comment_id)
          .filter((v): v is number => typeof v === "number")
      ),
    [favorites]
  );

  const filteredPreloaded = useMemo(() => {
    const q = qcSearch.trim().toLowerCase();
    if (!q) return PRELOADED_QUICK_COMMENTS;
    return PRELOADED_QUICK_COMMENTS.filter((c) =>
      c.body.toLowerCase().includes(q)
    );
  }, [qcSearch]);

  const filteredCustom = useMemo(() => {
    const q = qcSearch.trim().toLowerCase();
    if (!q) return customComments;
    return customComments.filter((c) => c.body.toLowerCase().includes(q));
  }, [qcSearch, customComments]);

  /** Cursor-aware splice of `body` into the current draft buffer.
   *
   *  Shared by phase-27/28 Quick Comments and phase-29 Clinical
   *  Shortcuts so both insertion paths behave identically with
   *  respect to cursor placement, newline handling, and undo.
   *  Returns `true` when the splice actually landed; returns
   *  `false` when the note is not in an editable state so callers
   *  can skip telemetry.
   */
  const spliceIntoDraft = useCallback(
    (body: string, flashLabel: string): boolean => {
      if (!canEdit || noteSigned || !activeNote) {
        showFlash(
          "error",
          `${flashLabel} can only be inserted into an editable draft.`
        );
        return false;
      }

      const textarea = draftTextareaRef.current;
      const current = editBody ?? "";
      let next: string;
      let caretAfter: number | null = null;

      // Newline-sane splice: insert a leading newline only if the
      // character immediately before the caret isn't already a
      // newline, and always finish with one trailing newline so the
      // next insertion lands on its own row.
      const padded = (before: string, phrase: string, after: string) => {
        const leading = before.length === 0 || before.endsWith("\n") ? "" : "\n";
        const trailing = after.startsWith("\n") || after.length === 0 ? "" : "\n";
        return {
          text: `${before}${leading}${phrase}${trailing}${after}`,
          caret: before.length + leading.length + phrase.length + trailing.length,
        };
      };

      const hasValidSelection =
        textarea !== null &&
        typeof textarea.selectionStart === "number" &&
        typeof textarea.selectionEnd === "number" &&
        textarea.selectionStart >= 0 &&
        textarea.selectionEnd >= textarea.selectionStart &&
        textarea.selectionEnd <= current.length;

      if (hasValidSelection && textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const before = current.slice(0, start);
        const after = current.slice(end);
        const spliced = padded(before, body, after);
        next = spliced.text;
        caretAfter = spliced.caret;
      } else {
        // Fallback: append at end, preserving historical behaviour.
        const spliced = padded(current, body, "");
        next = spliced.text;
        caretAfter = spliced.caret;
      }

      setEditBody(next);

      // Phase 30 — if the inserted phrase carries a `___` placeholder,
      // land the caret on the first one and select the 3 chars so the
      // clinician can type straight over it. Falls through to the
      // end-of-insertion caret when no placeholder is present, which
      // preserves the phase-28 behaviour for free-form quick comments.
      let selStart = caretAfter;
      let selEnd = caretAfter;
      const blankOffsetInBody = firstBlankOffset(body);
      if (blankOffsetInBody >= 0 && caretAfter !== null) {
        // `caretAfter` points to just past the inserted phrase; the
        // phrase itself started `body.length + trailingLen` chars
        // earlier. Recover the insertion start by subtracting the
        // pad-adjusted phrase length.
        const insertionEnd = caretAfter;
        const trailingLen = next.length - insertionEnd;  // chars after the caret
        // insertionStart == position in `next` where the phrase began.
        const insertionStart =
          insertionEnd - (body.length + /* trailing newline we added */ 0);
        // We don't need insertionStart precisely when we can just
        // search for the placeholder forward from the start of `next`
        // — the first `___` in `next` is guaranteed to be inside the
        // fragment we just spliced (drafts can't contain `___`
        // naturally in clinical text; if they do, landing on the
        // earliest one is still the right UX).
        void insertionStart;
        void trailingLen;
        const blankIdxInNext = next.indexOf(SHORTCUT_BLANK_TOKEN);
        if (blankIdxInNext >= 0) {
          selStart = blankIdxInNext;
          selEnd = blankIdxInNext + SHORTCUT_BLANK_TOKEN.length;
        }
      }

      if (textarea !== null && selStart !== null && selEnd !== null) {
        const start = selStart;
        const end = selEnd;
        requestAnimationFrame(() => {
          try {
            textarea.focus();
            textarea.setSelectionRange(start, end);
          } catch {
            /* jsdom / detached DOM tolerant */
          }
        });
      }

      showFlash("ok", `Inserted ${flashLabel.toLowerCase()} into draft.`);
      return true;
    },
    [canEdit, noteSigned, activeNote, editBody, showFlash]
  );

  /** Phase 27/28 Quick-Comment insert: splice + Quick-Comment usage audit. */
  const insertQuickComment = useCallback(
    (
      body: string,
      ref:
        | { kind: "preloaded"; preloaded_ref: string }
        | { kind: "custom"; custom_comment_id: number }
    ) => {
      if (!spliceIntoDraft(body, "Quick comment")) return;
      // Fire-and-forget usage audit.
      recordQuickCommentUsage(
        identity,
        ref.kind === "preloaded"
          ? {
              preloaded_ref: ref.preloaded_ref,
              note_version_id: activeNote?.id ?? null,
              encounter_id: encounterId,
            }
          : {
              custom_comment_id: ref.custom_comment_id,
              note_version_id: activeNote?.id ?? null,
              encounter_id: encounterId,
            }
      );
    },
    [spliceIntoDraft, identity, activeNote, encounterId]
  );

  /** Phase 29 Clinical Shortcut insert: splice + separate usage audit. */
  const insertClinicalShortcut = useCallback(
    (shortcut: ClinicalShortcut) => {
      if (!spliceIntoDraft(shortcut.body, "Clinical shortcut")) return;
      recordClinicalShortcutUsage(identity, {
        shortcut_id: shortcut.id,
        note_version_id: activeNote?.id ?? null,
        encounter_id: encounterId,
      });
    },
    [spliceIntoDraft, identity, activeNote, encounterId]
  );

  const togglePreloadedFavorite = useCallback(
    async (preloadedRef: string) => {
      try {
        if (favoritePreloadedSet.has(preloadedRef)) {
          await unfavoriteQuickComment(identity, { preloaded_ref: preloadedRef });
        } else {
          await favoriteQuickComment(identity, { preloaded_ref: preloadedRef });
        }
        await loadFavorites();
      } catch (e) {
        showFlash("error", friendly(e));
      }
    },
    [identity, favoritePreloadedSet, loadFavorites, showFlash]
  );

  const toggleCustomFavorite = useCallback(
    async (customId: number) => {
      try {
        if (favoriteCustomSet.has(customId)) {
          await unfavoriteQuickComment(identity, { custom_comment_id: customId });
        } else {
          await favoriteQuickComment(identity, { custom_comment_id: customId });
        }
        await loadFavorites();
      } catch (e) {
        showFlash("error", friendly(e));
      }
    },
    [identity, favoriteCustomSet, loadFavorites, showFlash]
  );

  const openQcModal = (comment?: ClinicianQuickComment) => {
    if (comment) {
      setQcEditingId(comment.id);
      setQcDraft(comment.body);
    } else {
      setQcEditingId(null);
      setQcDraft("");
    }
    setQcModalOpen(true);
  };

  const closeQcModal = () => {
    setQcModalOpen(false);
    setQcEditingId(null);
    setQcDraft("");
  };

  const saveQcDraft = async () => {
    const body = qcDraft.trim();
    if (!body) {
      showFlash("error", "Comment body cannot be empty.");
      return;
    }
    setLoading(true);
    try {
      if (qcEditingId !== null) {
        await updateMyQuickComment(identity, qcEditingId, { body });
        showFlash("ok", "Custom comment updated.");
      } else {
        await createMyQuickComment(identity, body);
        showFlash("ok", "Custom comment saved.");
      }
      closeQcModal();
      await loadCustomComments();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const deleteCustomComment = async (id: number) => {
    setLoading(true);
    try {
      await deleteMyQuickComment(identity, id);
      showFlash("ok", "Custom comment deleted.");
      await loadCustomComments();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  // ---- actions ----------------------------------------------------

  const onIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTranscript.trim()) {
      showFlash("error", "paste or type a transcript first");
      return;
    }
    setLoading(true);
    try {
      await createEncounterInput(identity, encounterId, {
        input_type: "text_paste",
        transcript_text: newTranscript.trim(),
      });
      showFlash("ok", "Transcript ingested.");
      setNewTranscript("");
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onAudioUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioFile) {
      showFlash("error", "Choose an audio file first.");
      return;
    }
    setAudioUploading(true);
    try {
      await uploadEncounterAudio(identity, encounterId, audioFile, {
        captureSource: "file-upload",
      });
      showFlash(
        "ok",
        `Audio uploaded: ${audioFile.name}. Running transcription…`
      );
      setAudioFile(null);
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setAudioUploading(false);
    }
  };

  // ---- Phase 36 — browser microphone capture handlers ------------

  const onStartRecording = async () => {
    if (recorderState.kind !== "idle") return;
    if (!captureSupport.supported) {
      showFlash(
        "error",
        "This browser doesn't support microphone capture. Use the file-upload form instead."
      );
      return;
    }
    try {
      const controller = await startBrowserRecording();
      setRecordedElapsedSec(0);
      setRecorderState({
        kind: "recording",
        controller,
        startedAt: Date.now(),
      });
    } catch (err) {
      // BrowserCaptureError carries a stable code for the UI copy.
      if (err instanceof BrowserCaptureError) {
        if (err.code === "browser_capture_permission_denied") {
          showFlash(
            "error",
            "Microphone access denied. Allow it in your browser, or use the file-upload form below."
          );
        } else if (err.code === "browser_capture_unsupported") {
          showFlash(
            "error",
            "Browser microphone capture isn't available. Use the file-upload form below."
          );
        } else {
          showFlash("error", `Recording failed: ${err.message}`);
        }
      } else {
        showFlash("error", friendly(err));
      }
    }
  };

  const onStopRecording = async () => {
    if (recorderState.kind !== "recording") return;
    try {
      const file = await recorderState.controller.stop();
      setRecorderState({ kind: "recorded", file });
    } catch (err) {
      if (err instanceof BrowserCaptureError) {
        showFlash("error", `Recording stop failed: ${err.message}`);
      } else {
        showFlash("error", friendly(err));
      }
      setRecorderState({ kind: "idle" });
    }
  };

  const onDiscardRecording = () => {
    if (recorderState.kind === "recording") {
      try {
        recorderState.controller.cancel();
      } catch {
        /* noop */
      }
    }
    setRecorderState({ kind: "idle" });
    setRecordedElapsedSec(0);
  };

  const onUploadRecording = async () => {
    if (recorderState.kind !== "recorded") return;
    const file = recorderState.file;
    setRecorderState({ kind: "uploading", file });
    try {
      await uploadEncounterAudio(identity, encounterId, file, {
        captureSource: "browser-mic",
      });
      showFlash(
        "ok",
        `Recording uploaded (${file.name}). Running transcription…`
      );
      setRecorderState({ kind: "idle" });
      setRecordedElapsedSec(0);
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
      // Keep the recorded blob so the doctor can retry without
      // re-recording.
      setRecorderState({ kind: "recorded", file });
    }
  };

  const openTranscriptEditor = (input: EncounterInput) => {
    setTranscriptEditInputId(input.id);
    setTranscriptEditValue(input.transcript_text ?? "");
  };

  const closeTranscriptEditor = () => {
    setTranscriptEditInputId(null);
    setTranscriptEditValue("");
  };

  const saveTranscriptEdit = async () => {
    if (transcriptEditInputId === null) return;
    const text = transcriptEditValue.trim();
    if (text.length < 10) {
      showFlash(
        "error",
        "Transcript must be at least 10 characters after trimming."
      );
      return;
    }
    setLoading(true);
    try {
      await patchEncounterInputTranscript(
        identity,
        transcriptEditInputId,
        text
      );
      showFlash("ok", "Transcript updated.");
      closeTranscriptEditor();
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onRetry = async (inputId: number) => {
    setLoading(true);
    try {
      await retryEncounterInput(identity, inputId);
      // After retry flips the row to `queued`, re-run the pipeline.
      await processEncounterInput(identity, inputId);
      showFlash("ok", "Retry complete. Check the updated status.");
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onProcess = async (inputId: number) => {
    setLoading(true);
    try {
      const res = await processEncounterInput(identity, inputId);
      if (res.ingestion_error) {
        showFlash(
          "error",
          `${res.ingestion_error.error_code}: ${res.ingestion_error.reason}`
        );
      } else {
        showFlash("ok", "Input processed.");
      }
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateNoteVersion(identity, encounterId, {});
      showFlash(
        "ok",
        `Draft v${data.note.version_number} generated. ${data.note.missing_data_flags.length} items for provider to verify.`
      );
      await loadNotes();
      setActiveNoteId(data.note.id);
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSaveEdit = async () => {
    if (activeNote === null || editBody === null) return;
    setLoading(true);
    try {
      const updated = await patchNoteVersion(identity, activeNote.id, {
        note_text: editBody,
      });
      setActiveNote(updated);
      showFlash("ok", "Provider edit saved.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSubmitReview = async () => {
    if (!activeNote) return;
    setLoading(true);
    try {
      const updated = await submitNoteForReview(identity, activeNote.id);
      setActiveNote(updated);
      showFlash("ok", "Submitted for provider review.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSign = async () => {
    if (!activeNote) return;
    if (!canSign) {
      showFlash("error", "your role cannot sign notes");
      return;
    }
    setLoading(true);
    try {
      const updated = await signNoteVersion(identity, activeNote.id);
      setActiveNote(updated);
      showFlash("ok", "Note signed.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onExport = async () => {
    if (!activeNote) return;
    setLoading(true);
    try {
      const updated = await exportNoteVersion(identity, activeNote.id);
      setActiveNote(updated);
      await loadNotes();
      downloadTextFile(
        `chartnav-note-${activeNote.encounter_id}-v${activeNote.version_number}.txt`,
        activeNote.note_text
      );
      showFlash("ok", "Note marked exported and downloaded.");
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onCopy = async () => {
    if (!activeNote) return;
    try {
      await navigator.clipboard?.writeText(activeNote.note_text);
      showFlash("ok", "Note copied to clipboard.");
    } catch {
      showFlash("info", "clipboard unavailable; use the download button");
    }
  };

  // ---- render -----------------------------------------------------

  return (
    <div className="workspace" data-testid="note-workspace">
      <div className="workspace__header">
        <h3>{patientDisplay} — visit workspace</h3>
        <div className="workspace__meta subtle-note">
          Provider: <strong>{providerDisplay}</strong>
        </div>
        <p className="workspace__trust subtle-note">
          <strong>Trust model:</strong>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--transcript">
            transcript
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--findings">
            extracted facts
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--draft">
            AI draft
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--signed">
            provider signed
          </span>
        </p>
      </div>

      {flash && (
        <div
          className={`banner banner--${flash.kind === "info" ? "info" : flash.kind === "ok" ? "ok" : "error"}`}
          role={flash.kind === "error" ? "alert" : "status"}
          data-testid="workspace-banner"
        >
          {flash.msg}
        </div>
      )}

      {/* ROI wave 1 — item 1+4: one-glance exam summary + ophthalmology
          structured exam block. Sits at the top so a doctor's first
          clinically meaningful block is one dense card. */}
      <ExamSummary
        findings={activeFindings}
        note={activeNote}
        patientDisplay={patientDisplay}
        providerDisplay={providerDisplay}
      />

      {/* ROI wave 1 — item 2: next best action rail. */}
      <NextBestAction
        inputs={inputs}
        activeNote={activeNote}
        transmitSupported={transmitSupported}
        canSign={canSign}
        loading={loading}
        handlers={{
          onFocusIngest: () => {
            document
              .querySelector('[data-testid="workspace-tier-transcript"]')
              ?.scrollIntoView({ behavior: "smooth", block: "start" });
          },
          onProcessLatest: async () => {
            const target =
              [...inputs]
                .filter(
                  (i) =>
                    i.processing_status === "queued" ||
                    i.processing_status === "processing"
                )
                .sort((a, b) => b.id - a.id)[0] ?? null;
            if (!target) return;
            await onProcess(target.id);
          },
          onRetryLatest: async () => {
            const target =
              [...inputs]
                .filter((i) => i.processing_status === "failed")
                .sort((a, b) => b.id - a.id)[0] ?? null;
            if (!target) return;
            await onRetry(target.id);
          },
          onGenerate: onGenerate,
          onFocusReview: () => {
            document
              .querySelector('[data-testid="workspace-tier-draft"]')
              ?.scrollIntoView({ behavior: "smooth", block: "start" });
          },
          onRequestSign: () => {
            if (!activeNote) return;
            if (shouldCheckpoint(activeNote, activeFindings)) {
              setPresignOpen(true);
            } else {
              onSign();
            }
          },
          onExport: onExport,
          onTransmit: async () => {
            if (!activeNote || !transmitSupported) return;
            setLoading(true);
            try {
              const row = await transmitNoteVersion(identity, activeNote.id, {
                force: transmissions.some(
                  (t) => t.transport_status === "succeeded"
                ),
              });
              if (row.transport_status === "succeeded") {
                showFlash(
                  "ok",
                  `Transmitted to ${row.adapter_key}` +
                    (row.remote_id ? ` (remote id ${row.remote_id})` : "")
                );
              } else {
                showFlash(
                  "error",
                  `Transmit ${row.transport_status}: ${
                    row.last_error || row.last_error_code || "no detail"
                  }`
                );
              }
              await loadTransmissions();
            } catch (err) {
              showFlash("error", friendly(err));
            } finally {
              setLoading(false);
            }
          },
        }}
      />

      {/* Tier 1 — transcripts */}
      <section
        className="workspace__tier workspace__tier--transcript"
        data-testid="workspace-tier-transcript"
      >
        <div className="workspace__tier-head">
          <h4>1. Transcript input</h4>
          {inputs.length > 0 && (
            <button
              type="button"
              className="btn btn--muted"
              onClick={loadInputs}
              disabled={loading}
              data-testid="transcript-refresh"
              title="Re-fetch input list from the server"
            >
              ↻ Refresh
            </button>
          )}
        </div>
        <p className="subtle-note">
          Raw operator input. Source of record for what was said.
        </p>
        {inputs.some(
          (i) =>
            i.processing_status === "queued" ||
            i.processing_status === "processing"
        ) && (
          <div
            className="banner banner--info"
            role="note"
            data-testid="workspace-queue-banner"
          >
            {inputs.some((i) => i.processing_status === "processing") ? (
              <>
                <strong>Transcript is processing in the background.</strong>{" "}
                A worker picked up the input and is extracting text. Draft
                generation will unlock automatically once processing
                finishes — click <strong>Refresh</strong> to pull the
                latest status, or step away and come back.
              </>
            ) : (
              <>
                <strong>Transcript is queued in the background.</strong>{" "}
                It's waiting for a worker to pick it up. Click{" "}
                <strong>Process now</strong> on the queued row to run it
                immediately, or wait for the next worker tick.
              </>
            )}
          </div>
        )}
        {inputs.length === 0 && (
          <p className="empty">No transcript ingested yet.</p>
        )}
        {inputs.map((inp) => (
          <div
            key={inp.id}
            className="event-item"
            data-testid={`transcript-${inp.id}`}
          >
            <div className="event-item__head">
              <span className="event-item__type">{inp.input_type}</span>
              <span
                className="status-pill"
                data-status={inp.processing_status}
                data-testid={`transcript-status-${inp.id}`}
                title={transcriptStatusHelp(inp.processing_status)}
                aria-label={`Transcript state: ${inp.processing_status.replace(
                  /_/g,
                  " "
                )} — ${transcriptStatusHelp(inp.processing_status)}`}
              >
                {inp.processing_status.replace(/_/g, " ")}
                {typeof inp.retry_count === "number" && inp.retry_count > 0 && (
                  <span
                    className="workspace__retry-count"
                    aria-label="retry count"
                    data-testid={`transcript-retry-count-${inp.id}`}
                  >
                    · retries {inp.retry_count}
                  </span>
                )}
              </span>
            </div>
            {(inp.processing_status === "failed" ||
              inp.processing_status === "needs_review") && inp.last_error && (
              <div
                className="banner banner--error"
                data-testid={`transcript-error-${inp.id}`}
                role="alert"
              >
                <strong>{inp.last_error_code ?? "ingestion_failed"}:</strong>{" "}
                {inp.last_error}
              </div>
            )}
            {inp.transcript_text && (
              <pre className="workspace__transcript">{inp.transcript_text}</pre>
            )}
            {canEdit && inp.processing_status === "completed" && (
              <div className="actions" style={{ marginTop: 6 }}>
                <button
                  type="button"
                  className="btn"
                  disabled={loading}
                  onClick={() => openTranscriptEditor(inp)}
                  data-testid={`transcript-edit-${inp.id}`}
                >
                  Edit transcript
                </button>
              </div>
            )}
            {canEdit &&
              (inp.processing_status === "failed" ||
                inp.processing_status === "needs_review" ||
                inp.processing_status === "queued") && (
                <div className="actions" style={{ marginTop: 6 }}>
                  {(inp.processing_status === "failed" ||
                    inp.processing_status === "needs_review") && (
                    <button
                      type="button"
                      className="btn"
                      disabled={loading}
                      onClick={() => onRetry(inp.id)}
                      data-testid={`transcript-retry-${inp.id}`}
                    >
                      Retry
                    </button>
                  )}
                  {inp.processing_status === "queued" && (
                    <button
                      type="button"
                      className="btn"
                      disabled={loading}
                      onClick={() => onProcess(inp.id)}
                      data-testid={`transcript-process-${inp.id}`}
                    >
                      Process now
                    </button>
                  )}
                </div>
              )}
          </div>
        ))}
        {canEdit && (
          <div
            className="event-form workspace__audio-record"
            data-testid="audio-record-panel"
          >
            <div className="workspace__audio-record-head">
              <strong>Record dictation</strong>
              <span
                className="subtle-note"
                data-testid="audio-record-mode"
              >
                {captureSupport.supported
                  ? `Browser capture (${captureSupport.pickedExt?.replace(".", "") ?? "webm"})`
                  : "Browser capture unavailable"}
              </span>
            </div>
            {!captureSupport.supported && (
              <p
                className="subtle-note"
                data-testid="audio-record-unsupported"
              >
                This browser doesn&apos;t expose a usable microphone +
                MediaRecorder API. Use the file-upload form below;
                pick AirPods or your preferred mic at the OS level
                and any recorder app will produce a file ChartNav can
                ingest.
              </p>
            )}
            {captureSupport.supported && (
              <p className="subtle-note">
                Click <strong>Start</strong> to record from whichever
                input the OS routes to your browser
                (AirPods / wired headset / built-in mic). The
                browser will prompt for microphone permission on
                first use.
              </p>
            )}
            <div className="row workspace__audio-record-actions">
              {recorderState.kind === "idle" && (
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={onStartRecording}
                  disabled={!captureSupport.supported}
                  data-testid="audio-record-start"
                >
                  Start recording
                </button>
              )}
              {recorderState.kind === "recording" && (
                <>
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={onStopRecording}
                    data-testid="audio-record-stop"
                  >
                    Stop ({recordedElapsedSec}s)
                  </button>
                  <span
                    className="workspace__audio-record-indicator"
                    aria-live="polite"
                    data-testid="audio-record-indicator"
                  >
                    ● recording
                  </span>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={onDiscardRecording}
                    data-testid="audio-record-cancel"
                  >
                    Cancel
                  </button>
                </>
              )}
              {recorderState.kind === "recorded" && (
                <>
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={onUploadRecording}
                    data-testid="audio-record-upload"
                  >
                    Upload recording
                  </button>
                  <button
                    type="button"
                    className="btn"
                    onClick={onDiscardRecording}
                    data-testid="audio-record-discard"
                  >
                    Discard
                  </button>
                  <span
                    className="subtle-note"
                    data-testid="audio-record-filename"
                  >
                    {recorderState.file.name} ·{" "}
                    {Math.round(recorderState.file.size / 1024)} KB
                  </span>
                </>
              )}
              {recorderState.kind === "uploading" && (
                <span
                  className="subtle-note"
                  data-testid="audio-record-uploading"
                  aria-live="polite"
                >
                  Uploading {recorderState.file.name}…
                </span>
              )}
            </div>
          </div>
        )}
        {canEdit && (
          <form
            className="event-form"
            onSubmit={onAudioUpload}
            data-testid="audio-upload-form"
          >
            <label>
              Upload a dictation audio file
              <input
                type="file"
                accept="audio/*,.wav,.mp3,.m4a,.mp4,.ogg,.webm,.flac,.aac"
                onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                data-testid="audio-upload-input"
                disabled={audioUploading}
              />
            </label>
            <p className="subtle-note">
              Doctor-only. A stub transcriber emits a clearly-labeled
              placeholder until a production STT provider is wired.
              Edit the transcript below after it lands before generating
              a draft.
            </p>
            <div className="row">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={audioUploading || !audioFile}
                data-testid="audio-upload-submit"
              >
                {audioUploading ? "Uploading…" : "Upload audio"}
              </button>
              {audioFile && (
                <span
                  className="subtle-note"
                  data-testid="audio-upload-filename"
                >
                  {audioFile.name} · {Math.round(audioFile.size / 1024)} KB
                </span>
              )}
            </div>
          </form>
        )}
        {canEdit && (
          <form
            className="event-form"
            onSubmit={onIngest}
            data-testid="transcript-ingest-form"
          >
            <label>
              Paste or type a new transcript
              <textarea
                value={newTranscript}
                onChange={(e) => setNewTranscript(e.target.value)}
                data-testid="transcript-ingest-textarea"
                placeholder="Chief complaint: …&#10;OD 20/40, OS 20/20.&#10;IOP 15/17.&#10;Plan: YAG capsulotomy.&#10;Follow-up in 4 weeks."
              />
            </label>
            <div className="row">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={loading}
                data-testid="transcript-ingest-submit"
              >
                Ingest transcript
              </button>
              <button
                type="button"
                className="btn"
                disabled={
                  loading ||
                  !inputs.some((i) => i.processing_status === "completed")
                }
                onClick={onGenerate}
                data-testid="generate-draft"
                title={
                  inputs.some((i) => i.processing_status === "completed")
                    ? "Generate a draft from the most recent completed input"
                    : "Waiting for a completed input — process or retry one first"
                }
              >
                Generate draft
              </button>
            </div>
            {/* Honest "why is Generate disabled" hint. Appears only
                when no completed input exists; differentiates the
                "still processing" case from the "nothing ingested
                yet" case so operators know whether to wait, retry,
                or paste something fresh. */}
            {!inputs.some((i) => i.processing_status === "completed") && (
              <p
                className="subtle-note workspace__generate-blocked"
                data-testid="generate-blocked-note"
              >
                {inputs.length === 0
                  ? "Generation unlocks once a transcript has been ingested and finished processing."
                  : inputs.some(
                      (i) =>
                        i.processing_status === "queued" ||
                        i.processing_status === "processing"
                    )
                  ? "Generation is waiting on transcript processing. Background work continues — use Refresh to pull the latest status."
                  : inputs.some(
                      (i) =>
                        i.processing_status === "failed" ||
                        i.processing_status === "needs_review"
                    )
                  ? "The most recent input failed or needs review. Retry it, or ingest a fresh transcript before generating."
                  : "No completed input is available yet."}
              </p>
            )}
          </form>
        )}
      </section>

      {/* Tier 2 — findings */}
      <section
        className="workspace__tier workspace__tier--findings"
        data-testid="workspace-tier-findings"
      >
        <h4>2. Extracted findings</h4>
        <p className="subtle-note">
          Structured facts the generator saw. Read-only — provider verifies.
        </p>
        {activeFindings ? (
          <FindingsBlock findings={activeFindings} />
        ) : (
          <p className="empty">
            No findings yet. Generate a draft from a transcript.
          </p>
        )}
        {activeNote && activeNote.missing_data_flags.length > 0 && (
          <div
            className="banner banner--info"
            data-testid="missing-flags-banner"
          >
            <strong>Items for provider to verify:</strong>
            <ul>
              {activeNote.missing_data_flags.map((f) => (
                <li key={f}>{MISSING_FLAG_LABELS[f] ?? f}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Tier 3 — draft / signoff */}
      <section
        className="workspace__tier workspace__tier--draft"
        data-testid="workspace-tier-draft"
      >
        <div className="workspace__tier-head">
          <h4>3. Note draft</h4>
          {activeNote && (
            <span
              className={`status-pill`}
              data-status={mapNoteStatus(activeNote.draft_status)}
              data-testid="note-draft-status"
            >
              {activeNote.draft_status} · v{activeNote.version_number}
            </span>
          )}
        </div>
        {activeNote ? (
          <>
            <div className="workspace__meta subtle-note">
              Generated by:{" "}
              <strong data-testid="note-generated-by">
                {providerEdited ? "provider (edited)" : activeNote.generated_by}
              </strong>
              {activeNote.signed_at && (
                <>
                  {" · Signed at "}
                  <strong>{activeNote.signed_at}</strong>
                </>
              )}
              {noteExported && (
                <>
                  {" · Exported at "}
                  <strong>{activeNote.exported_at}</strong>
                </>
              )}
            </div>
            {canEdit && !noteSigned ? (
              <textarea
                ref={draftTextareaRef}
                className="workspace__draft"
                value={editBody ?? ""}
                onChange={(e) => setEditBody(e.target.value)}
                // Phase 31 — Tab-to-next-blank / Phase 32 — Shift+Tab
                // walks backward. When the doctor has just inserted a
                // shortcut containing `___ to ___ o'clock` the
                // caret-to-first-blank already selected the first
                // placeholder; Tab advances to the next one, Shift+Tab
                // returns to the previous one, both without leaving the
                // field. We forward the default Tab / Shift+Tab to the
                // usual focus-cycle behaviour once every blank has been
                // consumed in the relevant direction. Ctrl / Meta / Alt
                // are left untouched so OS keybindings still work.
                onKeyDown={(e) => {
                  if (
                    e.key !== "Tab" ||
                    e.ctrlKey ||
                    e.metaKey ||
                    e.altKey
                  )
                    return;
                  const ta = e.currentTarget;
                  const body = ta.value ?? "";
                  if (e.shiftKey) {
                    // Walk to the previous `___`, strictly before the
                    // current selection's start so sitting on a blank
                    // + Shift+Tab hops BACK, not to the same blank.
                    const startFrom = ta.selectionStart ?? 0;
                    const prev = prevBlankBefore(body, startFrom);
                    if (prev >= 0) {
                      e.preventDefault();
                      ta.setSelectionRange(
                        prev,
                        prev + SHORTCUT_BLANK_TOKEN.length
                      );
                    }
                    // else: default Shift+Tab → focus previous element.
                    return;
                  }
                  const startFrom = ta.selectionEnd ?? 0;
                  const next = nextBlankAfter(body, startFrom);
                  if (next >= 0) {
                    e.preventDefault();
                    ta.setSelectionRange(
                      next,
                      next + SHORTCUT_BLANK_TOKEN.length
                    );
                  }
                  // else: no placeholder left → default Tab behaviour
                  // (caret leaves the textarea for the next element).
                }}
                data-testid="note-draft-textarea"
                rows={18}
              />
            ) : (
              <pre
                className="workspace__draft workspace__draft--readonly"
                data-testid="note-draft-readonly"
              >
                {activeNote.note_text}
              </pre>
            )}
            <div className="actions">
              {canEdit && !noteSigned && (
                <>
                  <button
                    className="btn"
                    onClick={onSaveEdit}
                    disabled={loading || editBody === activeNote.note_text}
                    data-testid="note-save-edit"
                  >
                    Save provider edit
                  </button>
                  <button
                    className="btn"
                    onClick={onSubmitReview}
                    disabled={
                      loading ||
                      activeNote.draft_status === "provider_review"
                    }
                    data-testid="note-submit-review"
                  >
                    Submit for review
                  </button>
                </>
              )}
              {canSign && !noteSigned && (
                <button
                  className="btn btn--primary"
                  onClick={() => {
                    if (!activeNote) return;
                    if (shouldCheckpoint(activeNote, activeFindings)) {
                      setPresignOpen(true);
                    } else {
                      onSign();
                    }
                  }}
                  disabled={loading}
                  data-testid="note-sign"
                >
                  Sign note
                </button>
              )}
              {noteSigned && !noteExported && (
                <button
                  className="btn btn--primary"
                  onClick={onExport}
                  disabled={loading}
                  data-testid="note-export"
                >
                  Export note
                </button>
              )}
              {/* Export-before-sign guard messaging (hardening lane).
                  Only rendered when the active clinician has not
                  signed yet. Keeps the doctor from hunting for a
                  missing button and documents the contract. */}
              {canSign && activeNote && !noteSigned && (
                <span
                  className="subtle-note"
                  data-testid="note-export-disabled-hint"
                  title="Export unlocks after sign"
                  aria-live="polite"
                >
                  Export unlocks once the note is signed.
                </span>
              )}
              {noteSigned && (
                <button
                  className="btn"
                  onClick={onCopy}
                  data-testid="note-copy"
                >
                  Copy to clipboard
                </button>
              )}
              {noteSigned && activeNote && transmitSupported && canSign && (
                <button
                  className="btn btn--primary"
                  onClick={async () => {
                    setLoading(true);
                    try {
                      const row = await transmitNoteVersion(
                        identity,
                        activeNote.id,
                        { force: transmissions.some((t) => t.transport_status === "succeeded") }
                      );
                      if (row.transport_status === "succeeded") {
                        showFlash(
                          "ok",
                          `Transmitted to ${row.adapter_key}` +
                            (row.remote_id ? ` (remote id ${row.remote_id})` : "")
                        );
                      } else {
                        showFlash(
                          "error",
                          `Transmit ${row.transport_status}: ${
                            row.last_error || row.last_error_code || "no detail"
                          }`
                        );
                      }
                      await loadTransmissions();
                    } catch (err: any) {
                      showFlash("error", friendly(err));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  data-testid="note-transmit"
                  title="Hand the signed DocumentReference to the active adapter"
                >
                  {transmissions.some((t) => t.transport_status === "succeeded")
                    ? "Re-transmit"
                    : "Transmit to EHR"}
                </button>
              )}
              {noteSigned && activeNote && (
                <div
                  className="workspace__artifact-actions"
                  data-testid="note-artifact-actions"
                >
                  {(["json", "text", "fhir"] as ArtifactFormat[]).map(
                    (fmt) => (
                      <button
                        key={fmt}
                        className="btn btn--ghost"
                        onClick={async () => {
                          try {
                            const { filename, variant } =
                              await downloadNoteArtifact(
                                identity,
                                activeNote.id,
                                fmt
                              );
                            showFlash(
                              "ok",
                              `Downloaded ${filename} (${variant})`
                            );
                          } catch (e: any) {
                            showFlash(
                              "error",
                              `Artifact download failed: ${
                                e?.reason || e?.message || e
                              }`
                            );
                          }
                        }}
                        data-testid={`note-artifact-${fmt}`}
                        title={
                          fmt === "json"
                            ? "ChartNav canonical signed-note artifact"
                            : fmt === "text"
                              ? "Plain text with metadata header (EHR paste)"
                              : "FHIR R4 DocumentReference (packaging shape)"
                        }
                      >
                        Download {fmt.toUpperCase()}
                      </button>
                    )
                  )}
                </div>
              )}
            </div>
            {!canSign && (
              <p
                className="subtle-note"
                data-testid="note-sign-disabled-note"
              >
                Reviewer role cannot sign. Clinician or admin attestation
                is required.
              </p>
            )}
          </>
        ) : (
          <p className="empty">
            No note yet. Generate a draft to start the review workflow.
          </p>
        )}
        {noteSigned && transmitSupported && transmissions.length > 0 && (
          <div
            className="workspace__transmissions subtle-note"
            data-testid="note-transmissions"
          >
            <strong>Transmission history:</strong>
            <ul>
              {transmissions.map((t) => (
                <li key={t.id} data-testid={`note-transmission-${t.id}`}>
                  attempt {t.attempt_number} · {t.adapter_key} ·{" "}
                  <span
                    className={`tx-status tx-status--${t.transport_status}`}
                  >
                    {t.transport_status}
                  </span>
                  {t.response_code != null && ` · HTTP ${t.response_code}`}
                  {t.remote_id && ` · remote id ${t.remote_id}`}
                  {t.last_error_code && ` · ${t.last_error_code}`}
                </li>
              ))}
            </ul>
          </div>
        )}
        {notes.length > 1 && (
          <div
            className="workspace__versions subtle-note"
            data-testid="note-version-list"
          >
            <strong>Versions:</strong>{" "}
            {notes.map((n) => (
              <button
                key={n.id}
                className={
                  "btn " +
                  (activeNoteId === n.id ? "btn--primary" : "btn--muted")
                }
                onClick={() => setActiveNoteId(n.id)}
                data-testid={`note-version-${n.version_number}`}
              >
                v{n.version_number} · {n.draft_status}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Phase 27 — Quick-comment pad. Clinician-only surface.
          Rendered as its own section under the workspace so it never
          overlaps any patient-facing area (there isn't one in this
          app today, but the isolation is explicit).

          The panel labels itself as *clinician-entered* content to
          keep provenance obvious — these are not AI findings, they
          are doctor quick-picks. */}
      {canUseQuickComments && (
        <section
          className="workspace workspace__quick-comments"
          data-testid="quick-comments-panel"
          aria-label="Clinician quick comments"
        >
          <header className="workspace__hdr">
            <h3>Quick Comments</h3>
            <span
              className="workspace__trust-pill workspace__trust-pill--clinician"
              title="Clinician-entered, not AI-generated"
            >
              clinician-entered
            </span>
          </header>
          <p className="subtle-note" data-testid="quick-comments-help">
            Click a phrase to insert it into the draft. These are
            clinician quick-picks, not transcript findings or
            AI-generated content.
          </p>

          <div className="workspace__qc-toolbar">
            <input
              type="search"
              placeholder="Search quick comments…"
              value={qcSearch}
              onChange={(e) => setQcSearch(e.target.value)}
              data-testid="quick-comments-search"
              aria-label="Search quick comments"
            />
            <button
              className="btn btn--primary"
              onClick={() => openQcModal()}
              data-testid="quick-comments-add"
              disabled={loading}
            >
              Add Custom Comment
            </button>
          </div>

          {/* Favorites strip — surfaces the doctor's pinned picks
              (preloaded or custom) above the main library so the
              phrases they actually use every day are one click away.
              Phase 34: explicit loading + empty states so the strip
              never silently disappears while data is in flight. */}
          {(() => {
            const q = qcSearch.trim().toLowerCase();
            const favRows: {
              key: string;
              body: string;
              testid: string;
              ref:
                | { kind: "preloaded"; preloaded_ref: string }
                | { kind: "custom"; custom_comment_id: number };
            }[] = [];
            for (const f of favorites) {
              if (f.preloaded_ref) {
                const pre = PRELOADED_QUICK_COMMENTS.find(
                  (c) => c.id === f.preloaded_ref
                );
                if (!pre) continue;
                if (q && !pre.body.toLowerCase().includes(q)) continue;
                favRows.push({
                  key: `pre-${pre.id}`,
                  body: pre.body,
                  testid: `quick-comment-favorite-preloaded-${pre.id}`,
                  ref: { kind: "preloaded", preloaded_ref: pre.id },
                });
              } else if (f.custom_comment_id != null) {
                const custom = customComments.find(
                  (c) => c.id === f.custom_comment_id
                );
                if (!custom) continue;
                if (q && !custom.body.toLowerCase().includes(q)) continue;
                favRows.push({
                  key: `custom-${custom.id}`,
                  body: custom.body,
                  testid: `quick-comment-favorite-custom-${custom.id}`,
                  ref: { kind: "custom", custom_comment_id: custom.id },
                });
              }
            }
            if (favoritesLoading) {
              return (
                <div
                  className="workspace__qc-favorites workspace__qc-favorites--loading"
                  data-testid="quick-comments-favorites-loading"
                  aria-busy="true"
                >
                  <div className="workspace__qc-group-title">★ Favorites</div>
                  <p className="subtle-note">Loading pinned comments…</p>
                </div>
              );
            }
            if (favRows.length === 0) {
              // Two distinct empty paths: nothing pinned at all, or
              // nothing pinned matched the search. Both surface a
              // calm, doctor-friendly hint instead of the strip just
              // vanishing.
              const hint = q
                ? `No pinned comments match "${q}".`
                : "Pin a comment with ☆ on any preloaded or custom row to see it here.";
              return (
                <div
                  className="workspace__qc-favorites workspace__qc-favorites--empty"
                  data-testid="quick-comments-favorites-empty"
                >
                  <div className="workspace__qc-group-title">★ Favorites</div>
                  <p className="subtle-note">{hint}</p>
                </div>
              );
            }
            return (
              <div
                className="workspace__qc-favorites"
                data-testid="quick-comments-favorites"
              >
                <div className="workspace__qc-group-title">★ Favorites</div>
                <ul className="workspace__qc-list">
                  {favRows.map((row) => (
                    <li key={row.key}>
                      <button
                        className="btn btn--muted btn--qc"
                        onClick={() => insertQuickComment(row.body, row.ref)}
                        data-testid={row.testid}
                        disabled={!canEdit || noteSigned || !activeNote}
                        title="Click to insert pinned comment"
                      >
                        {row.body}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })()}

          {/* Preloaded pack, grouped by category. Each item has a
              star toggle to pin/unpin into the Favorites strip. */}
          <div
            className="workspace__qc-preloaded"
            data-testid="quick-comments-preloaded"
          >
            {QUICK_COMMENT_CATEGORIES.map((cat) => {
              const items = filteredPreloaded.filter((c) => c.category === cat);
              if (items.length === 0) return null;
              return (
                <div
                  key={cat}
                  className="workspace__qc-group"
                  data-testid={`quick-comments-group-${cat
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, "-")}`}
                >
                  <div className="workspace__qc-group-title">{cat}</div>
                  <ul className="workspace__qc-list">
                    {items.map((c) => {
                      const isFav = favoritePreloadedSet.has(c.id);
                      return (
                        <li key={c.id} className="workspace__qc-row">
                          <button
                            className="btn btn--muted btn--qc"
                            onClick={() =>
                              insertQuickComment(c.body, {
                                kind: "preloaded",
                                preloaded_ref: c.id,
                              })
                            }
                            data-testid={`quick-comment-${c.id}`}
                            disabled={!canEdit || noteSigned || !activeNote}
                            title={
                              !activeNote
                                ? "Generate a draft first"
                                : noteSigned
                                  ? "Note is signed — cannot insert"
                                  : "Click to insert into draft"
                            }
                          >
                            {c.body}
                          </button>
                          <button
                            className={
                              "btn btn--ghost btn--qc-star" +
                              (isFav ? " btn--qc-star--on" : "")
                            }
                            onClick={() => togglePreloadedFavorite(c.id)}
                            data-testid={`quick-comment-star-${c.id}`}
                            aria-pressed={isFav}
                            aria-label={
                              isFav
                                ? `Unpin ${c.body}`
                                : `Pin ${c.body}`
                            }
                            title={isFav ? "Unpin from Favorites" : "Pin to Favorites"}
                          >
                            {isFav ? "★" : "☆"}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
            {filteredPreloaded.length === 0 && (
              <p className="empty" data-testid="quick-comments-preloaded-empty">
                No preloaded comments match your search.
              </p>
            )}
          </div>

          {/* Per-doctor custom comments. Always a separate section so
              nobody confuses "my saved clinician comments" with the
              shared ophthalmology pack. */}
          <div
            className="workspace__qc-custom"
            data-testid="quick-comments-custom"
          >
            <div className="workspace__qc-group-title">My Custom Comments</div>
            {filteredCustom.length === 0 ? (
              <p className="empty" data-testid="quick-comments-custom-empty">
                You haven&apos;t saved any custom comments yet. Use
                <strong> Add Custom Comment</strong> above.
              </p>
            ) : (
              <ul className="workspace__qc-list">
                {filteredCustom.map((c) => {
                  const isFav = favoriteCustomSet.has(c.id);
                  return (
                    <li
                      key={c.id}
                      className="workspace__qc-custom-row"
                      data-testid={`quick-comment-custom-${c.id}`}
                    >
                      <button
                        className="btn btn--muted btn--qc"
                        onClick={() =>
                          insertQuickComment(c.body, {
                            kind: "custom",
                            custom_comment_id: c.id,
                          })
                        }
                        disabled={!canEdit || noteSigned || !activeNote}
                        title="Click to insert your custom comment"
                      >
                        {c.body}
                      </button>
                      <span className="workspace__qc-custom-actions">
                        <button
                          className={
                            "btn btn--ghost btn--qc-star" +
                            (isFav ? " btn--qc-star--on" : "")
                          }
                          onClick={() => toggleCustomFavorite(c.id)}
                          data-testid={`quick-comment-custom-star-${c.id}`}
                          aria-pressed={isFav}
                          aria-label={
                            isFav ? "Unpin custom comment" : "Pin custom comment"
                          }
                          title={isFav ? "Unpin from Favorites" : "Pin to Favorites"}
                        >
                          {isFav ? "★" : "☆"}
                        </button>
                        <button
                          className="btn btn--ghost"
                          onClick={() => openQcModal(c)}
                          data-testid={`quick-comment-custom-edit-${c.id}`}
                          title="Edit"
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn--ghost"
                          onClick={() => deleteCustomComment(c.id)}
                          data-testid={`quick-comment-custom-delete-${c.id}`}
                          title="Delete"
                        >
                          Delete
                        </button>
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>
      )}

      {/* Phase 29 — Clinical Shortcuts (specialist shorthand pack).
          Separate section from Quick Comments on purpose. Same role
          gate (admin + clinician); same provenance label
          ("clinician-entered, not AI-generated"). Static content so
          the catalog renders with zero round-trips. */}
      {canUseQuickComments && (
        <section
          className="workspace workspace__clinical-shortcuts"
          data-testid="clinical-shortcuts-panel"
          aria-label="Clinical Shortcuts"
        >
          <header className="workspace__hdr">
            <h3>Clinical Shortcuts</h3>
            <span
              className="workspace__trust-pill workspace__trust-pill--clinician"
              title="Clinician-inserted specialist shorthand, not AI-generated"
            >
              clinician-entered
            </span>
          </header>
          <p
            className="subtle-note"
            data-testid="clinical-shortcuts-help"
          >
            Specialty shorthand note fragments for clinician use. These
            are doctor-inserted shortcuts, not transcript findings or
            AI-generated content.
          </p>

          <div className="workspace__qc-toolbar">
            <input
              type="search"
              placeholder="Search by phrase, group, or abbreviation (e.g. RD, SRF, AMD)…"
              value={shortcutSearch}
              onChange={(e) => setShortcutSearch(e.target.value)}
              data-testid="clinical-shortcuts-search"
              aria-label="Search clinical shortcuts"
            />
          </div>

          {/* Phase 30 — Favorites strip. Phase 34: explicit loading +
              empty UX so the strip never silently disappears while
              data is in flight, and so a doctor with no pins sees an
              honest "click ☆ to pin" hint instead of nothing. */}
          {(() => {
            const q = shortcutSearch.trim().toLowerCase();
            const favRows = shortcutFavorites
              .map((fav) =>
                CLINICAL_SHORTCUTS.find((s) => s.id === fav.shortcut_ref)
              )
              .filter((s): s is ClinicalShortcut => !!s)
              .filter((s) =>
                !q ? true : clinicalShortcutMatches(s, shortcutSearch)
              );
            if (shortcutFavoritesLoading) {
              return (
                <div
                  className="workspace__qc-favorites workspace__qc-favorites--loading"
                  data-testid="clinical-shortcuts-favorites-loading"
                  aria-busy="true"
                >
                  <div className="workspace__qc-group-title">★ Favorites</div>
                  <p className="subtle-note">Loading pinned shortcuts…</p>
                </div>
              );
            }
            if (favRows.length === 0) {
              const hint = q
                ? `No pinned shortcuts match "${q}".`
                : "Pin a shortcut with ☆ on any catalog row to see it here.";
              return (
                <div
                  className="workspace__qc-favorites workspace__qc-favorites--empty"
                  data-testid="clinical-shortcuts-favorites-empty"
                >
                  <div className="workspace__qc-group-title">★ Favorites</div>
                  <p className="subtle-note">{hint}</p>
                </div>
              );
            }
            return (
              <div
                className="workspace__qc-favorites"
                data-testid="clinical-shortcuts-favorites"
              >
                <div className="workspace__qc-group-title">★ Favorites</div>
                <ul className="workspace__qc-list">
                  {favRows.map((s) => (
                    <li key={s.id}>
                      <button
                        className="btn btn--muted btn--qc"
                        onClick={() => insertClinicalShortcut(s)}
                        data-testid={`clinical-shortcut-favorite-${s.id}`}
                        disabled={!canEdit || noteSigned || !activeNote}
                        title="Click to insert pinned shortcut"
                      >
                        {segmentAbbreviations(s.body).map((seg, i) =>
                          typeof seg === "string" ? (
                            <span key={i}>{seg}</span>
                          ) : (
                            <abbr
                              key={i}
                              title={seg.meaning}
                              className="cn-abbr"
                              tabIndex={0}
                              aria-label={`${seg.abbr}: ${seg.meaning ?? "abbreviation"}`}
                            >
                              {seg.abbr}
                            </abbr>
                          )
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })()}

          <div
            className="workspace__qc-preloaded"
            data-testid="clinical-shortcuts-list"
          >
            {CLINICAL_SHORTCUT_GROUPS.map((group) => {
              const items = CLINICAL_SHORTCUTS.filter(
                (s) =>
                  s.group === group &&
                  clinicalShortcutMatches(s, shortcutSearch)
              );
              if (items.length === 0) return null;
              return (
                <div
                  key={group}
                  className="workspace__qc-group"
                  data-testid={`clinical-shortcuts-group-${group
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, "-")}`}
                >
                  <div className="workspace__qc-group-title">{group}</div>
                  <ul className="workspace__qc-list">
                    {items.map((shortcut) => {
                      const isFav = favoriteShortcutSet.has(shortcut.id);
                      return (
                        <li key={shortcut.id} className="workspace__qc-row">
                          <button
                            className="btn btn--muted btn--qc"
                            onClick={() => insertClinicalShortcut(shortcut)}
                            data-testid={`clinical-shortcut-${shortcut.id}`}
                            disabled={!canEdit || noteSigned || !activeNote}
                            title={
                              !activeNote
                                ? "Generate a draft first"
                                : noteSigned
                                  ? "Note is signed — cannot insert"
                                  : "Click to insert into draft"
                            }
                          >
                            {segmentAbbreviations(shortcut.body).map(
                              (seg, i) =>
                                typeof seg === "string" ? (
                                  <span key={i}>{seg}</span>
                                ) : (
                                  <abbr
                                    key={i}
                                    title={seg.meaning}
                                    className="cn-abbr"
                                    tabIndex={0}
                                    aria-label={`${seg.abbr}: ${seg.meaning ?? "abbreviation"}`}
                                    data-testid={`clinical-shortcut-abbr-${seg.abbr}`}
                                  >
                                    {seg.abbr}
                                  </abbr>
                                )
                            )}
                          </button>
                          <button
                            className={
                              "btn btn--ghost btn--qc-star" +
                              (isFav ? " btn--qc-star--on" : "")
                            }
                            onClick={() => toggleShortcutFavorite(shortcut.id)}
                            data-testid={`clinical-shortcut-star-${shortcut.id}`}
                            aria-pressed={isFav}
                            aria-label={
                              isFav
                                ? `Unpin ${shortcut.id}`
                                : `Pin ${shortcut.id}`
                            }
                            title={
                              isFav
                                ? "Unpin from Favorites"
                                : "Pin to Favorites"
                            }
                          >
                            {isFav ? "★" : "☆"}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
            {shortcutSearch.trim() &&
              CLINICAL_SHORTCUTS.every(
                (s) => !clinicalShortcutMatches(s, shortcutSearch)
              ) && (
                <div
                  className="empty workspace__qc-empty"
                  role="status"
                  data-testid="clinical-shortcuts-empty"
                >
                  <p>
                    No clinical shortcuts match{" "}
                    <strong>&ldquo;{shortcutSearch.trim()}&rdquo;</strong>.
                  </p>
                  <p className="subtle-note">
                    Try an abbreviation (e.g. <code>RD</code>,{" "}
                    <code>SRF</code>, <code>POAG</code>, <code>MGD</code>) or
                    clear the search.
                  </p>
                </div>
              )}
          </div>
        </section>
      )}

      {/* Phase 27 — custom-comment editor modal. */}
      {canUseQuickComments && qcModalOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label={
            qcEditingId !== null ? "Edit custom comment" : "Add custom comment"
          }
          data-testid="quick-comments-modal"
        >
          <div className="modal">
            <h3>
              {qcEditingId !== null ? "Edit custom comment" : "New custom comment"}
            </h3>
            <p className="subtle-note">
              Saved per clinician. Not shared with other users. Insert into
              a draft by clicking it in the Quick Comments panel.
            </p>
            <textarea
              value={qcDraft}
              onChange={(e) => setQcDraft(e.target.value)}
              rows={5}
              data-testid="quick-comments-modal-textarea"
              placeholder="e.g. Refraction deferred per patient request."
              autoFocus
            />
            <div className="modal__actions">
              <button
                className="btn"
                onClick={closeQcModal}
                disabled={loading}
                data-testid="quick-comments-modal-cancel"
              >
                Cancel
              </button>
              <button
                className="btn btn--primary"
                onClick={saveQcDraft}
                disabled={loading || qcDraft.trim().length === 0}
                data-testid="quick-comments-modal-save"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Phase 33 — clinician transcript review/edit modal. Opens
          from the "Edit transcript" button on any completed input.
          Keeps provenance obvious: source audio row is preserved,
          only the text body is replaced. */}
      {canEdit && transcriptEditInputId !== null && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Edit transcript"
          data-testid="transcript-edit-modal"
        >
          <div className="modal">
            <h3>Edit transcript</h3>
            <p className="subtle-note">
              Clinician review of the transcript. The source audio
              input is preserved; only the transcript body is
              replaced. Quick Comments and Clinical Shortcuts stay
              separate from transcript provenance.
            </p>
            <textarea
              value={transcriptEditValue}
              onChange={(e) => setTranscriptEditValue(e.target.value)}
              rows={10}
              data-testid="transcript-edit-textarea"
              placeholder="Hand-correct the transcript before draft generation."
              autoFocus
            />
            <div className="modal__actions">
              <button
                className="btn"
                onClick={closeTranscriptEditor}
                disabled={loading}
                data-testid="transcript-edit-cancel"
              >
                Cancel
              </button>
              <button
                className="btn btn--primary"
                onClick={saveTranscriptEdit}
                disabled={
                  loading || transcriptEditValue.trim().length < 10
                }
                data-testid="transcript-edit-save"
              >
                Save transcript
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================
          Phase 38 — doctor expansion surfaces.
          ------------------------------------------------------------
          A single additive section that aggregates the doctor-side
          improvements without disturbing the existing tier layout
          above:
            · Trust badges across transcript / findings / draft
            · My patterns (per-user custom shortcuts, backend-backed)
            · Voice mode toggle (ambient vs targeted)
            · Dual-view transcript ↔ draft
            · Notes-version diff + delta digest
          ============================================================ */}
      <section
        className="workspace__tier"
        style={{ marginTop: 16 }}
        data-testid="workspace-phase38"
        aria-label="Doctor tools"
      >
        <div className="workspace__tier-head">
          <h4>Doctor tools</h4>
          <span className="subtle-note">
            Provenance badges · my patterns · dual view · note diff ·
            voice modes
          </span>
        </div>

        {/* Trust badges — one badge per tier, each calibrated to the
            strongest signal available at render time. */}
        <div
          style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}
          data-testid="trust-badge-row"
        >
          <TrustBadge kind="external" label="Transcript" title="Operator input; source of record" />
          {activeFindings && (
            <TrustBadge
              kind={
                activeFindings.extraction_confidence === "high"
                  ? "ai-high"
                  : activeFindings.extraction_confidence === "low"
                  ? "ai-low"
                  : "ai-medium"
              }
              label={`Findings · ${activeFindings.extraction_confidence ?? "unknown"}`}
              title="Structured facts extracted by the generator"
            />
          )}
          {activeNote && (
            <TrustBadge
              kind={trustKindForNote(activeNote, activeFindings)}
              label={`Draft · v${activeNote.version_number}`}
              title={`generated_by=${activeNote.generated_by}; status=${activeNote.draft_status}`}
            />
          )}
        </div>

        {/* Voice mode toggle (A4). This is a client-side affordance;
            existing audio intake always lands in the "ambient" path
            today. The "targeted" path is the on-ramp for the
            push-to-talk / phrase-into-cursor workflow once the
            transcriber seam exposes a short-capture API. */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <span className="subtle-note">Voice mode</span>
          <div className="voicemode" role="radiogroup" aria-label="Voice mode" data-testid="voicemode">
            {VOICE_MODES.map((m) => (
              <button
                key={m}
                type="button"
                className="voicemode__btn"
                role="radio"
                aria-checked={voiceMode === m}
                aria-pressed={voiceMode === m}
                data-testid={`voicemode-${m}`}
                onClick={() => setVoiceMode(m)}
                title={VOICE_MODE_REGISTRY[m].hint}
              >
                {VOICE_MODE_REGISTRY[m].label}
              </button>
            ))}
          </div>
          <span className="subtle-note">
            {VOICE_MODE_REGISTRY[voiceMode].hint}
          </span>
        </div>

        {/* Toggles for dual-view + note diff. Rendered as subtle
            chevrons so they don't compete with the primary sign /
            export actions. */}
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <button
            type="button"
            className="btn btn--muted"
            onClick={() => setShowDualView((v) => !v)}
            data-testid="toggle-dualview"
            aria-pressed={showDualView}
          >
            {showDualView ? "Hide" : "Show"} dual view
          </button>
          <button
            type="button"
            className="btn btn--muted"
            onClick={() => setShowDiff((v) => !v)}
            data-testid="toggle-notediff"
            aria-pressed={showDiff}
            disabled={notes.length < 2}
            title={notes.length < 2 ? "Needs 2 note versions" : "Compare versions"}
          >
            {showDiff ? "Hide" : "Show"} note diff
          </button>
        </div>

        {/* Dual-view transcript ↔ draft (A2). Reads the transcript
            from the most recent completed input and the draft from
            the active note. Cross-highlight is substring-heuristic
            until generator-emitted spans land. */}
        {showDualView && (() => {
          const latestTranscriptInput =
            [...inputs]
              .filter((i) => i.transcript_text && i.transcript_text.trim())
              .sort((a, b) =>
                (b.updated_at || "").localeCompare(a.updated_at || "")
              )[0] ?? null;
          const transcript = latestTranscriptInput?.transcript_text ?? "";
          const draft = activeNote?.note_text ?? "";
          if (!transcript && !draft) {
            return (
              <div className="subtle-note" data-testid="dualview-empty">
                Dual view needs both a transcript and a draft on this encounter.
              </div>
            );
          }
          return <DualView transcript={transcript} draft={draft} />;
        })()}

        {/* Notes-level diff + digest (A5). */}
        {showDiff && notes.length >= 2 && (
          <div style={{ marginTop: 10 }}>
            <NoteDiff versions={notes} />
          </div>
        )}

        {/* My patterns — per-user custom shortcuts (A3). */}
        <div style={{ marginTop: 14 }} data-testid="my-patterns">
          <h4 style={{ margin: "0 0 6px", fontSize: 13, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--cn-muted)" }}>
            My patterns
          </h4>
          <p className="subtle-note" style={{ margin: "0 0 8px" }}>
            Your own authored shortcut fragments. Separate from the
            shared Clinical Shortcuts catalog above.
          </p>
          {patternError && (
            <div className="banner banner--error" role="alert" data-testid="my-patterns-error">
              {patternError}
            </div>
          )}
          <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
            <input
              type="text"
              value={newPatternBody}
              onChange={(e) => setNewPatternBody(e.target.value)}
              placeholder="Author a new pattern — inserted verbatim into the draft"
              data-testid="my-pattern-input"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomPattern();
                }
              }}
              style={{
                flex: 1,
                padding: "6px 8px",
                border: "1px solid var(--cn-line-strong)",
                borderRadius: "var(--cn-radius-md)",
                background: "var(--cn-surface)",
                color: "var(--cn-fg)",
                font: "inherit",
              }}
            />
            <button
              type="button"
              className="btn btn--primary"
              onClick={addCustomPattern}
              disabled={newPatternPending || !newPatternBody.trim()}
              data-testid="my-pattern-add"
            >
              {newPatternPending ? "…" : "Add"}
            </button>
          </div>
          {customShortcuts.length === 0 ? (
            <div className="subtle-note" data-testid="my-patterns-empty">
              No custom patterns yet. Author one above and it will
              appear here for every encounter.
            </div>
          ) : (
            <ul
              style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}
              data-testid="my-patterns-list"
            >
              {customShortcuts.map((p) => (
                <li
                  key={p.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 8,
                    padding: "8px 10px",
                    border: "1px solid var(--cn-line)",
                    borderRadius: "var(--cn-radius-sm)",
                    background: "var(--cn-surface)",
                  }}
                  data-testid={`my-pattern-row-${p.id}`}
                >
                  <span style={{ flex: 1, whiteSpace: "pre-wrap" }}>{p.body}</span>
                  <button
                    type="button"
                    className="btn btn--muted"
                    onClick={() => removeCustomPattern(p.id)}
                    data-testid={`my-pattern-delete-${p.id}`}
                    title="Delete this pattern"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* ROI wave 1 — item 3: pre-sign safety checkpoint modal. */}
      <PreSignCheckpoint
        open={presignOpen}
        note={activeNote}
        findings={activeFindings}
        pending={loading}
        onCancel={() => setPresignOpen(false)}
        onConfirm={async () => {
          setPresignOpen(false);
          await onSign();
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function FindingsBlock({ findings }: { findings: ExtractedFindings }) {
  const s = findings.structured_json || {};
  const confidence = findings.extraction_confidence ?? "unknown";
  return (
    <dl className="detail__facts" data-testid="findings-block">
      <div>
        <dt>Chief complaint</dt>
        <dd data-testid="findings-cc">{findings.chief_complaint || "—"}</dd>
      </div>
      <div>
        <dt>HPI</dt>
        <dd>{findings.hpi_summary || "—"}</dd>
      </div>
      <div>
        <dt>Visual acuity OD / OS</dt>
        <dd data-testid="findings-va">
          {findings.visual_acuity_od || "—"} / {findings.visual_acuity_os || "—"}
        </dd>
      </div>
      <div>
        <dt>IOP OD / OS</dt>
        <dd data-testid="findings-iop">
          {findings.iop_od || "—"} / {findings.iop_os || "—"}
        </dd>
      </div>
      <div>
        <dt>Diagnoses</dt>
        <dd>{(s.diagnoses ?? []).join("; ") || "—"}</dd>
      </div>
      <div>
        <dt>Plan</dt>
        <dd>{s.plan || "—"}</dd>
      </div>
      <div>
        <dt>Follow-up</dt>
        <dd>{s.follow_up_interval || "—"}</dd>
      </div>
      <div>
        <dt>Extraction confidence</dt>
        <dd
          data-testid="findings-confidence"
          data-confidence={confidence}
        >
          {confidence}
        </dd>
      </div>
    </dl>
  );
}

function mapNoteStatus(s: string): string {
  // Reuse encounter status-pill palette for draft-status coloring.
  switch (s) {
    case "draft":
      return "in_progress";
    case "provider_review":
      return "review_needed";
    case "revised":
      return "draft_ready";
    case "signed":
    case "exported":
      return "completed";
    default:
      return "scheduled";
  }
}

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

/** Human-readable explanation for each transcript processing state.
 *  Surfaced via the status pill's `title` + `aria-label`. Hardening
 *  lane: state clarity without changing the state machine. */
export function transcriptStatusHelp(status: string): string {
  switch (status) {
    case "queued":
      return "Waiting for a worker to pick up the input.";
    case "processing":
      return "A worker is extracting text from the input.";
    case "completed":
      return "Transcript is ready; a draft can be generated.";
    case "failed":
      return "Ingestion failed. Retry, edit the transcript, or remove this input.";
    case "needs_review":
      return "Ingestion finished with low confidence; review required before drafting.";
    default:
      return `Transcript state: ${status.replace(/_/g, " ")}.`;
  }
}

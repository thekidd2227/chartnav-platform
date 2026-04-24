// Phase 64 — Clinical Coding Intelligence UI module.
//
// Layout:
//   LEFT RAIL : specialty quick-picks · favorites · recent searches
//   CENTER    : diagnosis search box + results list
//   RIGHT PANEL: code detail · specificity prompts · laterality prompts ·
//                claim-support hints · source/version audit chip
//
// Safety banner is persistent at the top. Source/version/effective-date
// label is persistent at the top-right.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  adminAudit,
  deleteFavorite,
  getActiveVersion,
  getCodeDetail,
  getSpecialtyCodes,
  listFavorites,
  listSpecialties,
  searchCodes,
  upsertFavorite,
} from "./api";
import type {
  ClinicalCodingVersion,
  CodeDetail,
  CodeRow,
  FavoriteRow,
  SearchResponse,
  SpecialtyBundle,
  SpecialtyTag,
} from "./types";

interface Props {
  identity: string;
  role: string; // 'admin' | 'clinician' | 'reviewer' | 'front_desk'
  /** Optional date of service for version resolution. If omitted, uses the active version. */
  dateOfService?: string;
}

export function ClinicalCodingPanel({ identity, role, dateOfService }: Props) {
  const [version, setVersion] = useState<ClinicalCodingVersion | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CodeRow[]>([]);
  const [searchMeta, setSearchMeta] = useState<SearchResponse | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<CodeDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteRow[]>([]);
  const [specialtyTag, setSpecialtyTag] = useState<SpecialtyTag | null>(null);
  const [bundles, setBundles] = useState<SpecialtyBundle[]>([]);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [billableOnly, setBillableOnly] = useState(true);
  const canWriteFavorites = role === "admin" || role === "clinician";

  // Version bootstrap
  useEffect(() => {
    let cancelled = false;
    getActiveVersion(identity)
      .then((v) => !cancelled && setVersion(v))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [identity]);

  // Favorites bootstrap
  const reloadFavorites = useCallback(async () => {
    try {
      setFavorites(await listFavorites(identity));
    } catch (e) {
      setError(String(e));
    }
  }, [identity]);
  useEffect(() => {
    void reloadFavorites();
  }, [reloadFavorites]);

  // Specialty bundles bootstrap
  useEffect(() => {
    let cancelled = false;
    listSpecialties(identity)
      .then((s) => !cancelled && setBundles(s.bundles))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [identity]);

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setResults([]);
        setSearchMeta(null);
        return;
      }
      setLoadingSearch(true);
      setError(null);
      try {
        const data = await searchCodes(identity, {
          q,
          dateOfService,
          limit: 30,
          billableOnly,
        });
        setSearchMeta(data);
        setResults(data.results);
        setRecentSearches((r) => [q, ...r.filter((x) => x !== q)].slice(0, 5));
      } catch (e) {
        setError(String(e));
      } finally {
        setLoadingSearch(false);
      }
    },
    [identity, dateOfService, billableOnly]
  );

  const loadDetail = useCallback(
    async (code: string) => {
      setSelectedCode(code);
      setLoadingDetail(true);
      setDetail(null);
      try {
        const r = await getCodeDetail(identity, code, dateOfService);
        setDetail(r.code);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoadingDetail(false);
      }
    },
    [identity, dateOfService]
  );

  const pickBundle = useCallback(
    async (tag: SpecialtyTag) => {
      setSpecialtyTag(tag);
      try {
        const data = await getSpecialtyCodes(identity, tag, dateOfService);
        setBundles(data.bundles);
        // Auto-fill the search input with the specialty tag so the
        // audit trail knows what the clinician was looking for.
        setQuery("");
        setSearchMeta(null);
        setResults([]);
      } catch (e) {
        setError(String(e));
      }
    },
    [identity, dateOfService]
  );

  const bundlesByTag = useMemo(() => {
    const m: Record<string, SpecialtyBundle[]> = {};
    for (const b of bundles) {
      (m[b.specialty_tag] ||= []).push(b);
    }
    return m;
  }, [bundles]);

  const onToggleFavorite = async (code: string) => {
    if (!canWriteFavorites) return;
    const existing = favorites.find((f) => f.code === code);
    try {
      if (existing) {
        await deleteFavorite(identity, existing.id);
      } else {
        await upsertFavorite(identity, {
          code,
          specialty_tag: (specialtyTag || "general") as SpecialtyTag,
          is_pinned: true,
          bump_usage: true,
        });
      }
      await reloadFavorites();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <section
      className="clinical-coding"
      data-testid="clinical-coding-panel"
      aria-label="Clinical Coding Intelligence"
    >
      {/* Safety banner */}
      <div
        className="cc-safety"
        role="note"
        data-testid="cc-safety-banner"
      >
        <strong>Advisory workflow support.</strong>{" "}
        Clinical Coding Intelligence supports your charting workflow. It does
        not replace clinician judgment, guarantee reimbursement, or replace
        payer policy review. You own every code attached to this chart.
      </div>

      <div className="cc-layout">
        {/* LEFT RAIL */}
        <aside className="cc-rail" data-testid="cc-rail">
          <section className="cc-rail__block">
            <h4>Specialty quick-picks</h4>
            <ul className="cc-specialty-list" role="tablist">
              {(
                [
                  "retina",
                  "glaucoma",
                  "cataract",
                  "cornea",
                  "oculoplastics",
                  "general",
                ] as SpecialtyTag[]
              ).map((tag) => (
                <li key={tag}>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={specialtyTag === tag}
                    onClick={() => pickBundle(tag)}
                    data-testid={`cc-specialty-${tag}`}
                    className={specialtyTag === tag ? "active" : ""}
                  >
                    {tag}
                  </button>
                </li>
              ))}
            </ul>
            {specialtyTag && bundlesByTag[specialtyTag] && (
              <ul
                className="cc-bundle-list"
                data-testid={`cc-bundle-${specialtyTag}`}
              >
                {bundlesByTag[specialtyTag].map((b) => (
                  <li key={b.label}>
                    <div className="cc-bundle__label">{b.label}</div>
                    <ul className="cc-bundle__codes">
                      {(b.codes || []).slice(0, 6).map((c) => (
                        <li key={c.code}>
                          <button
                            type="button"
                            onClick={() => loadDetail(c.code)}
                            data-testid={`cc-bundle-code-${c.code}`}
                          >
                            <code>{c.code}</code>
                            <span>{c.short_description}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="cc-rail__block">
            <h4>Favorites</h4>
            {favorites.length === 0 ? (
              <p className="subtle-note" data-testid="cc-favorites-empty">
                No pinned codes yet.
              </p>
            ) : (
              <ul data-testid="cc-favorites-list">
                {favorites.map((f) => (
                  <li key={f.id}>
                    <button
                      type="button"
                      onClick={() => loadDetail(f.code)}
                      data-testid={`cc-favorite-${f.code}`}
                    >
                      <code>{f.code}</code>
                      {f.is_pinned ? (
                        <span className="cc-pin">pinned</span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="cc-rail__block">
            <h4>Recent searches</h4>
            <ul data-testid="cc-recent-searches">
              {recentSearches.map((r) => (
                <li key={r}>
                  <button
                    type="button"
                    onClick={() => {
                      setQuery(r);
                      void doSearch(r);
                    }}
                  >
                    {r}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        {/* CENTER */}
        <div className="cc-center" data-testid="cc-center">
          <header className="cc-version-bar" data-testid="cc-version-bar">
            {version ? (
              <>
                <span className="cc-version__label">
                  {version.version_label}
                </span>
                <span>
                  · source: <strong>{version.source_authority}</strong>
                </span>
                <span>
                  · effective {version.effective_start_date}
                  {version.effective_end_date
                    ? ` → ${version.effective_end_date}`
                    : " → open"}
                </span>
                <span>· last sync {fmt(version.downloaded_at)}</span>
              </>
            ) : (
              <span>Loading version…</span>
            )}
          </header>

          <form
            className="cc-search-form"
            onSubmit={(e) => {
              e.preventDefault();
              void doSearch(query);
            }}
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by code (H40.11) or description (macular degeneration)"
              data-testid="cc-search-input"
              aria-label="ICD-10-CM search"
              autoComplete="off"
              maxLength={120}
            />
            <label
              className="cc-search-billable"
              data-testid="cc-search-billable"
            >
              <input
                type="checkbox"
                checked={billableOnly}
                onChange={(e) => setBillableOnly(e.target.checked)}
              />
              Billable only
            </label>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={loadingSearch || !query.trim()}
              data-testid="cc-search-submit"
            >
              {loadingSearch ? "Searching…" : "Search"}
            </button>
          </form>

          {error && (
            <div
              className="banner banner--error"
              role="alert"
              data-testid="cc-error"
            >
              {error}
            </div>
          )}

          {!loadingSearch && searchMeta && (
            <div
              className="subtle-note"
              data-testid="cc-result-count"
              aria-live="polite"
            >
              {searchMeta.result_count} result
              {searchMeta.result_count === 1 ? "" : "s"} from{" "}
              {searchMeta.version.version_label}
            </div>
          )}

          <ul className="cc-results" data-testid="cc-results">
            {results.map((r) => (
              <li
                key={r.id}
                className={`cc-result${
                  selectedCode === r.code ? " cc-result--selected" : ""
                }`}
                data-testid={`cc-result-${r.code}`}
              >
                <button
                  type="button"
                  className="cc-result__body"
                  onClick={() => loadDetail(r.code)}
                >
                  <div className="cc-result__head">
                    <code>{r.code}</code>
                    {r.is_billable ? (
                      <span className="cc-chip cc-chip--ok">billable</span>
                    ) : (
                      <span className="cc-chip">header</span>
                    )}
                    {r.specificity_flags ? (
                      <span
                        className="cc-chip cc-chip--warn"
                        title={r.specificity_flags}
                      >
                        {r.specificity_flags.replace(/,/g, " · ")}
                      </span>
                    ) : null}
                  </div>
                  <div className="cc-result__short">
                    {r.short_description}
                  </div>
                  <div className="cc-result__long subtle-note">
                    {r.long_description}
                  </div>
                </button>
                {canWriteFavorites && (
                  <button
                    type="button"
                    className="cc-fav-btn"
                    onClick={() => onToggleFavorite(r.code)}
                    data-testid={`cc-fav-toggle-${r.code}`}
                    aria-pressed={favorites.some((f) => f.code === r.code)}
                  >
                    {favorites.some((f) => f.code === r.code) ? "★" : "☆"}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>

        {/* RIGHT PANEL */}
        <aside className="cc-detail" data-testid="cc-detail">
          {loadingDetail ? (
            <div className="subtle-note">Loading detail…</div>
          ) : !detail ? (
            <div className="subtle-note" data-testid="cc-detail-empty">
              Select a code to see its detail, specificity prompts, and
              advisory support hints.
            </div>
          ) : (
            <>
              <header className="cc-detail__head">
                <div className="cc-detail__code-row">
                  <code>{detail.code}</code>
                  {detail.is_billable ? (
                    <span className="cc-chip cc-chip--ok">billable</span>
                  ) : (
                    <span className="cc-chip">header</span>
                  )}
                </div>
                <div className="cc-detail__short">
                  {detail.short_description}
                </div>
                <div className="cc-detail__long subtle-note">
                  {detail.long_description}
                </div>
                <div className="cc-detail__meta subtle-note">
                  Chapter {detail.chapter_code} · {detail.chapter_title}
                </div>
              </header>

              {detail.specificity_flags && (
                <section
                  className="cc-detail__block cc-detail__block--warn"
                  data-testid="cc-specificity-flags"
                >
                  <h5>Specificity required</h5>
                  <ul>
                    {detail.specificity_flags.split(",").map((f) => (
                      <li key={f}>{humanFlag(f.trim())}</li>
                    ))}
                  </ul>
                </section>
              )}

              {detail.support_hints.length > 0 && (
                <section
                  className="cc-detail__block"
                  data-testid="cc-support-hints"
                >
                  <h5>Advisory support hints</h5>
                  <ul>
                    {detail.support_hints.map((h) => (
                      <li key={h.id} data-testid={`cc-hint-${h.id}`}>
                        <div>
                          <strong>{labelFor(h.workflow_area)}</strong>{" "}
                          <span className="subtle-note">
                            [{h.specialty_tag}]
                          </span>
                        </div>
                        <div>{h.advisory_hint}</div>
                        {h.specificity_prompt && (
                          <pre className="cc-prompt-pre">
                            {h.specificity_prompt}
                          </pre>
                        )}
                        {h.source_reference && (
                          <div className="subtle-note">
                            Source: {h.source_reference}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {detail.children.length > 0 && (
                <section
                  className="cc-detail__block"
                  data-testid="cc-detail-children"
                >
                  <h5>More specific codes</h5>
                  <ul>
                    {detail.children.map((c) => (
                      <li key={c.code}>
                        <button
                          type="button"
                          onClick={() => loadDetail(c.code)}
                        >
                          <code>{c.code}</code> — {c.short_description}
                          {c.is_billable ? (
                            <span className="cc-chip cc-chip--ok">
                              billable
                            </span>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <footer
                className="cc-detail__audit subtle-note"
                data-testid="cc-detail-audit"
              >
                Source file: <code>{detail.source_file || "—"}</code> ·
                line {detail.source_line_no ?? "—"} · version {version?.version_label}
              </footer>
            </>
          )}
        </aside>
      </div>

      {role === "admin" && (
        <AdminAuditStrip identity={identity} />
      )}
    </section>
  );
}

function AdminAuditStrip({ identity }: { identity: string }) {
  const [data, setData] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    adminAudit(identity)
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, [identity]);
  return (
    <section className="cc-admin-audit" data-testid="cc-admin-audit">
      <h4>Admin audit — code-set versions and sync history</h4>
      {err && (
        <div className="banner banner--error" role="alert">
          {err}
        </div>
      )}
      {data && (
        <div>
          <p className="subtle-note">
            {data.versions.length} version
            {data.versions.length === 1 ? "" : "s"} loaded ·{" "}
            {data.recent_jobs.length} sync job
            {data.recent_jobs.length === 1 ? "" : "s"}
          </p>
          <table className="cc-admin-audit__table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Source</th>
                <th>Effective</th>
                <th>Active</th>
                <th>Checksum (first 16)</th>
                <th>Downloaded</th>
              </tr>
            </thead>
            <tbody>
              {data.versions.map((v: ClinicalCodingVersion) => (
                <tr key={v.id} data-testid={`cc-admin-version-${v.id}`}>
                  <td>{v.version_label}</td>
                  <td>{v.source_authority}</td>
                  <td>
                    {v.effective_start_date} →{" "}
                    {v.effective_end_date || "open"}
                  </td>
                  <td>{v.is_active ? "yes" : "no"}</td>
                  <td>
                    <code>{v.checksum_sha256.slice(0, 16)}</code>
                  </td>
                  <td>{fmt(v.downloaded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.replace(" ", "T"));
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
}

function humanFlag(token: string): string {
  const map: Record<string, string> = {
    laterality_required: "Document laterality (right / left / bilateral)",
    stage_required: "Document stage (mild / moderate / severe / indeterminate)",
    manifestation_detail_required:
      "Document manifestation detail (e.g. with / without macular edema)",
  };
  return map[token] || token;
}

function labelFor(
  area:
    | "specificity_prompt"
    | "claim_support_hint"
    | "search"
    | "favorites"
): string {
  switch (area) {
    case "specificity_prompt":
      return "Specificity prompt";
    case "claim_support_hint":
      return "Claim-support hint";
    case "search":
      return "Search tip";
    case "favorites":
      return "Favorites tip";
    default:
      return area;
  }
}

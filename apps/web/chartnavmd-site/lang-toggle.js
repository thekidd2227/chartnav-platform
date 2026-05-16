/**
 * lang-toggle.js — Phase 19K shared language toggle for the public
 * chartnavmd.com static marketing site.
 *
 * Auto-mounts an English / Español segmented pill into every page
 * footer (`.site-footer__inner`), applies the resolved language to
 * the document, swaps every `[data-i18n]`/`[data-i18n-attr-*]`
 * element via the page-local `window.__CN_I18N__` map, and persists
 * the choice in `localStorage["chartnav.language"]`.
 *
 * Resolution order:
 *   1. `?lang=es` or `?lang=en` query parameter (forced; persisted).
 *   2. localStorage["chartnav.language"] from a prior visit.
 *   3. "en" default.
 *
 * Footer placement only — no header chrome, no floating widget, no
 * banner. Accessible: keyboard focus visible, aria-pressed reflects
 * active language, aria-labelledby pairs the segmented control with
 * its "Language / Idioma" label.
 *
 * No external dependencies. Pure ES5/ES2015 — runs as a single
 * `<script src="/lang-toggle.js" defer>` on every public page.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "chartnav.language";
  var SUPPORTED = ["en", "es"];

  // ---- Toggle markup -------------------------------------------------
  // Produces the same DOM on every page so styles can target it once.
  function buildToggle(active) {
    var wrap = document.createElement("div");
    wrap.className = "site-footer__lang";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-labelledby", "cn-lang-label");

    var label = document.createElement("span");
    label.id = "cn-lang-label";
    label.className = "site-footer__lang-label";
    label.textContent = "Language / Idioma";
    wrap.appendChild(label);

    var pill = document.createElement("div");
    pill.className = "site-footer__lang-pill";
    pill.setAttribute("role", "radiogroup");
    pill.setAttribute("aria-label", "Language / Idioma");

    SUPPORTED.forEach(function (code) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.lang = code;
      btn.textContent = code === "es" ? "Español" : "English";
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", String(code === active));
      btn.setAttribute("aria-pressed", String(code === active));
      btn.setAttribute("lang", code);
      btn.className = "site-footer__lang-btn" + (code === active ? " is-active" : "");
      btn.addEventListener("click", function () { apply(code, /*persist*/ true); });
      pill.appendChild(btn);
    });
    wrap.appendChild(pill);
    return wrap;
  }

  // ---- String swap ---------------------------------------------------
  // Apply the resolved language: update <html lang>, swap every
  // `[data-i18n]` text node, swap every `[data-i18n-attr-<attr>]`
  // attribute, swap meta description if the page exposes one, mark the
  // active pill, persist the choice (if requested).
  function apply(next, persist) {
    if (SUPPORTED.indexOf(next) === -1) next = "en";
    var map = (window.__CN_I18N__ || {})[next] || null;

    document.documentElement.setAttribute("lang", next);
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* SSR / no-localStorage */ }
    }

    // Text content swap.
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (!key) return;
      var fallback = el.getAttribute("data-i18n-fallback");
      var value = (map && map[key] != null) ? map[key] : fallback;
      if (value != null) el.textContent = value;
    });

    // Attribute swaps: data-i18n-attr-title="key", data-i18n-attr-alt="key",
    // data-i18n-attr-aria-label="key", data-i18n-attr-placeholder="key".
    var ATTRS = ["title", "alt", "aria-label", "placeholder"];
    ATTRS.forEach(function (attr) {
      var sel = "[data-i18n-attr-" + attr.replace(/-/g, "\\-") + "]";
      document.querySelectorAll(sel).forEach(function (el) {
        var key = el.getAttribute("data-i18n-attr-" + attr);
        if (!key) return;
        if (map && map[key] != null) el.setAttribute(attr, map[key]);
      });
    });

    // Title + meta description swap (if the page registered one).
    if (map && map["__document_title"]) document.title = map["__document_title"];
    if (map && map["__meta_description"]) {
      var md = document.querySelector('meta[name="description"]');
      if (md) md.setAttribute("content", map["__meta_description"]);
    }

    // Pill state.
    document.querySelectorAll(".site-footer__lang-btn").forEach(function (btn) {
      var on = btn.dataset.lang === next;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-checked", String(on));
      btn.setAttribute("aria-pressed", String(on));
    });

    // Notify other in-page scripts that may want to react (e.g. the
    // video showcase rotator's caption manifest).
    try {
      window.dispatchEvent(new CustomEvent("chartnav:languagechange", { detail: { lang: next } }));
    } catch (e) { /* IE / no CustomEvent */ }
  }

  // ---- Resolve initial language --------------------------------------
  function resolve() {
    try {
      var params = new URLSearchParams(window.location.search);
      var q = params.get("lang");
      if (q && SUPPORTED.indexOf(q) !== -1) {
        // Query param wins and persists so subsequent visits remember.
        try { localStorage.setItem(STORAGE_KEY, q); } catch (e) { /* ignore */ }
        return q;
      }
    } catch (e) { /* old browser / no URLSearchParams */ }

    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored && SUPPORTED.indexOf(stored) !== -1) return stored;
    } catch (e) { /* ignore */ }

    return "en";
  }

  // ---- Mount + apply -------------------------------------------------
  function mount() {
    var lang = resolve();

    // Auto-mount the toggle into every `.site-footer__inner` so a page
    // that has multiple footer regions (unlikely, but harmless) still
    // gets one toggle per region.
    var footers = document.querySelectorAll(".site-footer__inner");
    if (!footers.length) {
      // Fallback: mount before the closing </body> so the toggle is
      // never invisible just because a page forgot a footer.
      var fallback = document.createElement("footer");
      fallback.className = "site-footer site-footer--lang-only";
      var inner = document.createElement("div");
      inner.className = "site-footer__inner";
      fallback.appendChild(inner);
      document.body.appendChild(fallback);
      footers = [inner];
    }
    footers.forEach(function (footer) {
      if (footer.querySelector(".site-footer__lang")) return; // idempotent
      footer.appendChild(buildToggle(lang));
    });

    // Apply the resolved language without forcing a re-persist.
    apply(lang, /*persist*/ false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }

  // Re-export `apply` for in-page scripts that need to flip language
  // programmatically (e.g. a test harness or a banner CTA in a future
  // phase). The toggle itself is self-contained — page code does not
  // need to import anything.
  window.ChartNavLang = {
    apply: function (code) { apply(code, /*persist*/ true); },
    current: function () { return document.documentElement.getAttribute("lang") || "en"; },
    supported: SUPPORTED.slice()
  };
})();

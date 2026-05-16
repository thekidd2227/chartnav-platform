// reveal.js — tiny scroll-reveal helper. No deps, motion-safe.
// Auto-tags common content elements with [data-reveal] then observes them.
(function () {
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("[data-reveal]").forEach(function (el) { el.setAttribute("data-revealed", "true"); });
    return;
  }
  // Auto-tag headings, paragraphs, cards, columns inside <section> blocks.
  var sel = "section h1, section h2, section .section-sub, section p:not(.eyebrow), .card, .ba-col, .vshow__copy, .vshow__frame, .hero__chips, .hero__ctas, .feature-card, .ehr-card";
  document.querySelectorAll(sel).forEach(function (el) {
    if (!el.hasAttribute("data-reveal") && !el.hasAttribute("data-no-reveal")) el.setAttribute("data-reveal", "");
  });
  var els = document.querySelectorAll("[data-reveal]");
  if (!els.length) return;
  if (!("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.setAttribute("data-revealed", "true"); });
    return;
  }
  // Reveal anything already in viewport on first paint.
  var vh = window.innerHeight || document.documentElement.clientHeight;
  els.forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.top < vh && r.bottom > 0) el.setAttribute("data-revealed", "true");
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.setAttribute("data-revealed", "true");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: "0px 0px -5% 0px" });
  els.forEach(function (el) { if (el.getAttribute("data-revealed") !== "true") io.observe(el); });
  // Safety: reveal anything still hidden after 700ms.
  window.setTimeout(function () {
    document.querySelectorAll("[data-reveal]:not([data-revealed])").forEach(function (el) {
      el.setAttribute("data-revealed", "true");
    });
  }, 700);
})();

// Card parallax — every card/column on every page subtly floats with scroll.
// Drives --cn-card-parallax (px). Reduced-motion users get nothing.
(function () {
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var cards = document.querySelectorAll(".card, .ba-col, .noclaim-card, .vgallery__card");
  if (!cards.length) return;
  var raf = null;
  function update() {
    raf = null;
    var vh = window.innerHeight || document.documentElement.clientHeight;
    var range = window.innerWidth <= 720 ? 3 : 5;
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var rect = c.getBoundingClientRect();
      // Skip cards far off-screen — saves work, no visible effect.
      if (rect.bottom < -200 || rect.top > vh + 200) continue;
      var center = rect.top + rect.height / 2;
      var progress = (center - vh / 2) / vh;
      if (progress < -1.2) progress = -1.2;
      else if (progress > 1.2) progress = 1.2;
      // Per-card phase offset so adjacent cards drift slightly differently.
      var phase = ((i % 3) - 1) * 0.18;
      var ty = -(progress + phase) * range;
      c.style.setProperty("--cn-card-parallax", ty.toFixed(2) + "px");
    }
  }
  function onScroll() { if (!raf) raf = requestAnimationFrame(update); }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();
})();

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { InviteAccept } from "./InviteAccept";
import { IntakePage } from "./IntakePage";
import { applyPreferences, loadDensity, loadTheme } from "./preferences";
import "./styles.css";
// Phase A item 5 — tablet hardening sheet (safe-area + 44pt targets +
// banner styling). Loaded after styles.css so the narrower-viewport
// rules win.
import "./styles/tablet.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element not found");
}

// Phase 38 — apply persisted density + theme before the first paint
// so the root element never flashes the default styling.
try {
  applyPreferences(loadDensity(), loadTheme());
} catch {
  // non-fatal; the app still renders with defaults
}
// Follow system theme changes while `theme === "system"`. The
// individual components re-apply on user action; this listener only
// handles the system-follows case.
if (typeof window !== "undefined" && window.matchMedia) {
  try {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyPreferences(loadDensity(), loadTheme());
    if (typeof mq.addEventListener === "function") mq.addEventListener("change", onChange);
    else if (typeof (mq as any).addListener === "function") (mq as any).addListener(onChange);
  } catch {
    /* non-fatal */
  }
}

// Tiny hash-based route split: /accept and ?invite=... → minimal accept
// screen; everything else renders the main App. Keeps us from adding a
// router dependency.
function Root() {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  if (path.endsWith("/accept") || path.endsWith("/invite") || params.has("invite")) {
    return <InviteAccept defaultToken={params.get("invite") || ""} />;
  }
  // Phase 2 item 3 — public unauthenticated patient intake.
  // Match /intake/<token> (token is the rest of the path after the
  // first slash). No app shell, no auth header.
  const intakeMatch = path.match(/^\/intake\/([^/?#]+)/);
  if (intakeMatch) {
    return <IntakePage token={intakeMatch[1]} />;
  }
  return <App />;
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { InviteAccept } from "./InviteAccept";
import { LandingPage } from "./LandingPage";
import { resolveRootView } from "./resolveRootView";
import "./styles.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element not found");
}

// Hotfix — `/` on the public marketing host (chartnavmd.com) now
// resolves to the LandingPage instead of the authenticated App.
// Routing logic lives in apps/web/src/resolveRootView.ts so vitest
// can pin the full mapping without importing this bootstrap module.
function Root() {
  const view = resolveRootView(
    window.location.pathname,
    window.location.search,
    window.location.hostname,
  );
  if (view === "accept") {
    const params = new URLSearchParams(window.location.search);
    return <InviteAccept defaultToken={params.get("invite") || ""} />;
  }
  if (view === "landing") {
    return <LandingPage />;
  }
  return <App />;
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

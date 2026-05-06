import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { InviteAccept } from "./InviteAccept";
import { LandingPage } from "./LandingPage";
import "./styles.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element not found");
}

// Tiny hash-based route split: /accept and ?invite=... → minimal accept
// screen; /landing or ?intro=1 → public landing / proof page (Phase
// 16); everything else renders the main App. Keeps us from adding a
// router dependency.
function Root() {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  if (path.endsWith("/accept") || path.endsWith("/invite") || params.has("invite")) {
    return <InviteAccept defaultToken={params.get("invite") || ""} />;
  }
  if (path.endsWith("/landing") || params.get("intro") === "1") {
    return <LandingPage />;
  }
  return <App />;
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

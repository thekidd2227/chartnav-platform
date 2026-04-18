import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { InviteAccept } from "./InviteAccept";
import "./styles.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element not found");
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
  return <App />;
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

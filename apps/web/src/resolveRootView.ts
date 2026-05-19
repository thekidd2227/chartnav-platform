// apps/web/src/resolveRootView.ts
//
// Pure routing helper. Decides which top-level surface (App,
// LandingPage, or InviteAccept) renders for a given pathname +
// search + hostname triple. Pulled out of main.tsx so vitest can
// import it without triggering main.tsx's bootstrap side effects
// (`document.getElementById("root")` etc.).
//
// Why this exists:
//   The repo's apps/web/dist/ is now uploaded to chartnavmd.com/.
//   Without a marketing-host guard, a buyer hitting
//   chartnavmd.com/ saw the empty authenticated workspace
//   ("auth: Failed to fetch" + the CORE / CLINICAL / OPERATIONS
//   / ADMIN sidebar) instead of the marketing page. The right
//   buyer-facing default for the public marketing hostname is
//   the LandingPage.
//
// Behavior:
//   - /accept | /invite | ?invite=...  → InviteAccept (every host)
//   - /landing | ?intro=1              → LandingPage  (every host)
//   - /app | /app/* | ?app=1           → App          (every host)
//   - / (or empty) on chartnavmd.com / www.chartnavmd.com
//                                       → LandingPage
//   - / (or empty) on anything else    → App
//                                       (localhost, Vercel preview,
//                                        any host that hasn't opted
//                                        in)
//
// Localhost + Playwright E2E default still resolves to App so
// existing dev flow + E2E baseline are byte-stable.

export type RootView = "landing" | "app" | "accept";

const PUBLIC_MARKETING_HOSTS = new Set([
  "chartnavmd.com",
  "www.chartnavmd.com",
]);

function hostIsPublicMarketing(host: string): boolean {
  return PUBLIC_MARKETING_HOSTS.has(host.toLowerCase());
}

export function resolveRootView(
  pathname: string,
  search: string,
  hostname: string,
): RootView {
  const params = new URLSearchParams(search);
  if (
    pathname.endsWith("/accept")
    || pathname.endsWith("/invite")
    || params.has("invite")
  ) {
    return "accept";
  }
  if (pathname.endsWith("/landing") || params.get("intro") === "1") {
    return "landing";
  }
  if (
    pathname === "/app"
    || pathname.startsWith("/app/")
    || pathname.startsWith("/app?")
    || params.get("app") === "1"
  ) {
    return "app";
  }
  if (
    (pathname === "/" || pathname === "")
    && hostIsPublicMarketing(hostname)
  ) {
    return "landing";
  }
  return "app";
}

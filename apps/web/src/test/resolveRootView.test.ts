// resolveRootView.test.ts — hotfix coverage for the public-marketing
// hostname default. The repo's dist/ is now uploaded to
// chartnavmd.com/; without this routing guard, `/` rendered the
// authenticated App on the marketing domain. This file pins the
// full mapping so a future change can't silently regress.

import { describe, expect, it } from "vitest";
import { resolveRootView } from "../resolveRootView";

describe("resolveRootView — public marketing host default", () => {
  it("chartnavmd.com / → landing", () => {
    expect(resolveRootView("/", "", "chartnavmd.com")).toBe("landing");
  });
  it("www.chartnavmd.com / → landing", () => {
    expect(resolveRootView("/", "", "www.chartnavmd.com")).toBe("landing");
  });
  it("hostname case is normalized", () => {
    expect(resolveRootView("/", "", "ChartNavMD.com")).toBe("landing");
  });

  it("chartnavmd.com /app → app (explicit opt-out reaches workspace)", () => {
    expect(resolveRootView("/app", "", "chartnavmd.com")).toBe("app");
  });
  it("chartnavmd.com /app/something → app", () => {
    expect(resolveRootView("/app/encounters", "", "chartnavmd.com")).toBe(
      "app",
    );
  });
  it("chartnavmd.com /?app=1 → app", () => {
    expect(resolveRootView("/", "?app=1", "chartnavmd.com")).toBe("app");
  });
});

describe("resolveRootView — non-marketing hosts default to App", () => {
  it("localhost / → app (dev flow unchanged)", () => {
    expect(resolveRootView("/", "", "localhost")).toBe("app");
  });
  it("127.0.0.1 / → app", () => {
    expect(resolveRootView("/", "", "127.0.0.1")).toBe("app");
  });
  it("Vercel preview host / → app (preview never auto-redirects to landing)", () => {
    expect(
      resolveRootView(
        "/",
        "",
        "chartnav-platform-git-main-jeanmaxcharles-3486s-projects.vercel.app",
      ),
    ).toBe("app");
  });
});

describe("resolveRootView — explicit landing routes win on any host", () => {
  it("/landing on localhost → landing", () => {
    expect(resolveRootView("/landing", "", "localhost")).toBe("landing");
  });
  it("?intro=1 on localhost → landing", () => {
    expect(resolveRootView("/", "?intro=1", "localhost")).toBe("landing");
  });
  it("?intro=1 on chartnavmd.com → landing (same path the buyer demo uses)", () => {
    expect(
      resolveRootView("/", "?intro=1", "chartnavmd.com"),
    ).toBe("landing");
  });
});

describe("resolveRootView — invite accept path always wins", () => {
  it("/accept on marketing host → accept", () => {
    expect(resolveRootView("/accept", "", "chartnavmd.com")).toBe("accept");
  });
  it("/invite on localhost → accept", () => {
    expect(resolveRootView("/invite", "", "localhost")).toBe("accept");
  });
  it("?invite=... on marketing host → accept", () => {
    expect(
      resolveRootView("/", "?invite=abc123", "chartnavmd.com"),
    ).toBe("accept");
  });
});

describe("resolveRootView — empty pathname is treated as root", () => {
  it("empty path on marketing host → landing", () => {
    expect(resolveRootView("", "", "chartnavmd.com")).toBe("landing");
  });
  it("empty path on localhost → app", () => {
    expect(resolveRootView("", "", "localhost")).toBe("app");
  });
});

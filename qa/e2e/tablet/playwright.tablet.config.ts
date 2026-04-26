// Phase A item 5 — Playwright tablet projects.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §4.
//
// Acceptance criteria require Playwright runs against:
//   - iPad Pro 12.9   1024x1366 portrait, 1366x1024 landscape
//   - iPad Air 11      834x1194 portrait, 1194x834 landscape
//
// We compose the device profiles from `@playwright/test`'s built-in
// `iPad Pro 11` profile (closest match) and override viewport so the
// numbers are exactly the ones the spec calls out. Webkit engine is
// the right choice because that is what iPadOS Safari uses.
//
// This config is OPT-IN. The default `apps/web/playwright.config.ts`
// stays desktop-only so existing CI is not changed by this commit.
// Run with:
//
//   npx playwright test --config=qa/e2e/tablet/playwright.tablet.config.ts
//
import { defineConfig, devices } from "@playwright/test";

const REPO_ROOT = new URL("../../..", import.meta.url).pathname;
const API_PORT = 8002;
const WEB_PORT = 5175;
const E2E_DB = `${REPO_ROOT}apps/api/.e2e.tablet.chartnav.db`;

const iPadPro12Portrait = {
  ...devices["iPad Pro 11"],
  viewport: { width: 1024, height: 1366 },
};
const iPadPro12Landscape = {
  ...devices["iPad Pro 11 landscape"],
  viewport: { width: 1366, height: 1024 },
};
const iPadAir11Portrait = {
  ...devices["iPad Pro 11"],
  viewport: { width: 834, height: 1194 },
};
const iPadAir11Landscape = {
  ...devices["iPad Pro 11 landscape"],
  viewport: { width: 1194, height: 834 },
};

export default defineConfig({
  testDir: "./",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",

  use: {
    baseURL: process.env.E2E_BASE_URL || `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "iPad Pro 12.9 portrait",  use: iPadPro12Portrait },
    { name: "iPad Pro 12.9 landscape", use: iPadPro12Landscape },
    { name: "iPad Air 11 portrait",    use: iPadAir11Portrait },
    { name: "iPad Air 11 landscape",   use: iPadAir11Landscape },
  ],

  webServer: [
    {
      command: [
        `bash -c`,
        `'rm -f ${E2E_DB} && `
        + `cd ${REPO_ROOT}apps/api && `
        + `DATABASE_URL="sqlite:///${E2E_DB}" `
        + `PATH="$PWD/.venv/bin:$PATH" `
        + `alembic upgrade head && `
        + `DATABASE_URL="sqlite:///${E2E_DB}" `
        + `PATH="$PWD/.venv/bin:$PATH" `
        + `python scripts_seed.py && `
        + `DATABASE_URL="sqlite:///${E2E_DB}" `
        + `CHARTNAV_RATE_LIMIT_PER_MINUTE=0 `
        + `PATH="$PWD/.venv/bin:$PATH" `
        + `uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT} --log-level warning'`,
      ].join(" "),
      url: `http://127.0.0.1:${API_PORT}/health`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `cd ${REPO_ROOT}apps/web && npm run dev -- --host 127.0.0.1 --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      env: {
        VITE_API_URL: process.env.E2E_API_URL || `http://127.0.0.1:${API_PORT}`,
      },
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});

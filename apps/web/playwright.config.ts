import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config — boots both backend and frontend via Playwright's webServer.
 * Backend runs on :8001 against an ephemeral SQLite file so the operator's
 * dev DB is never touched; frontend runs on :5174 pointed at that backend.
 *
 * CI overrides the hosts via env if needed (`E2E_BASE_URL`, `E2E_API_URL`).
 */

const API_PORT = 8001;
const WEB_PORT = 5174;
const REPO_ROOT = new URL("../..", import.meta.url).pathname;
const E2E_DB = `${REPO_ROOT}apps/api/.e2e.chartnav.db`;

export default defineConfig({
  testDir: "./tests/e2e",
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
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Boot backend then frontend. Playwright waits for each URL to respond
  // before running tests, and tears both down on exit.
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
      command: `npm run dev -- --host 127.0.0.1 --port ${WEB_PORT}`,
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

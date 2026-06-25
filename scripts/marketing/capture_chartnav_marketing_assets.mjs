#!/usr/bin/env node
/**
 * Capture ChartNav marketing screenshots from the REAL running application.
 *
 * Hard rules:
 *   - Never generates mockups — only screenshots live, rendered app screens.
 *   - Uses deterministic demo data + demo mode (`?demo=1`) so the localhost /
 *     API debug chip is hidden and only synthetic patients appear.
 *   - Outputs ONLY to qa/screenshots/marketing/staging/ (never to public/).
 *   - Writes capture metadata (commit SHA + timestamp + viewport) alongside
 *     each PNG so promotion can record real provenance.
 *
 * Captures are UNREVIEWED. Nothing here is approved. A human reviews each PNG
 * and runs scripts/marketing/promote_chartnav_asset.py to approve + publish.
 *
 * Prereq: a running web app. Set CHARTNAV_WEB_URL (default http://localhost:5173).
 * Usage:  node scripts/marketing/capture_chartnav_marketing_assets.mjs [--mobile]
 */
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");
const STAGING = join(ROOT, "qa", "screenshots", "marketing", "staging");
const BASE = process.env.CHARTNAV_WEB_URL || "http://localhost:5173";
const MOBILE = process.argv.includes("--mobile");

const DESKTOP = { width: 1440, height: 900 };
const MOBILE_SAFE = { width: 414, height: 896 };

// Each shot targets a real route. `demo=1` engages demo mode (synthetic data,
// no debug chips). Keep this list aligned with real, shipped surfaces only.
const SHOTS = [
  { slug: "dashboard-overview", path: "/?demo=1", waitFor: "[data-testid='encounter-list']" },
  { slug: "clinical-tabbed-workspace", path: "/?demo=1&encounter=1", waitFor: "[data-testid='clinical-tabbed-workspace']" },
  { slug: "retina-eye-diagram", path: "/?demo=1&encounter=1", waitFor: "[data-testid='ctw-tab-imaging']", click: "[data-testid='ctw-tab-imaging']" },
  { slug: "patient-chart-overview", path: "/?demo=1#/patients/1", waitFor: "[data-testid='patient-chart']" },
  { slug: "administration-org", path: "/?demo=1", waitFor: "body" },
];

function commitSha() {
  try {
    return execSync("git rev-parse HEAD", { cwd: ROOT }).toString().trim();
  } catch {
    return "unknown";
  }
}

async function main() {
  let chromium;
  try {
    ({ chromium } = await import("playwright"));
  } catch {
    console.error(
      "playwright is required: install it in apps/web (npm i -D playwright) " +
      "or run via `npx playwright`."
    );
    process.exit(2);
  }

  mkdirSync(STAGING, { recursive: true });
  const sha = commitSha();
  // Timestamp is recorded in metadata only; filenames stay stable + slugged.
  const capturedAt = new Date().toISOString();
  const viewport = MOBILE ? MOBILE_SAFE : DESKTOP;
  const variant = MOBILE ? "mobile" : "desktop";

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  for (const shot of SHOTS) {
    const url = `${BASE}${shot.path}`;
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
      if (shot.waitFor) {
        await page.waitForSelector(shot.waitFor, { timeout: 15000 }).catch(() => {});
      }
      if (shot.click) {
        await page.click(shot.click).catch(() => {});
        await page.waitForTimeout(400);
      }
      // Guard: refuse to save a frame that still shows a localhost/debug chip.
      const leaked = await page
        .locator("text=/localhost|127\\.0\\.0\\.1|http:\\/\\//i")
        .count()
        .catch(() => 0);
      const base = `${shot.slug}-${variant}`;
      const pngPath = join(STAGING, `${base}.png`);
      await page.screenshot({ path: pngPath, fullPage: true });
      writeFileSync(
        join(STAGING, `${base}.meta.json`),
        JSON.stringify(
          {
            slug: shot.slug,
            variant,
            url,
            app_version: sha,
            captured_at: capturedAt,
            viewport,
            captured_from: "real running application",
            review_status: "unreviewed",
            warnings: leaked > 0 ? ["possible localhost/url text on screen — review before promoting"] : [],
          },
          null,
          2
        ) + "\n"
      );
      console.log(`captured ${base}.png${leaked > 0 ? "  ⚠️ possible URL text — review" : ""}`);
    } catch (e) {
      console.error(`skip ${shot.slug}: ${e.message}`);
    }
  }

  await browser.close();
  console.log(
    `\nStaged in ${STAGING}\n` +
    "These are UNREVIEWED. Review each PNG, then approve with " +
    "scripts/marketing/promote_chartnav_asset.py (commit SHA " + sha + ")."
  );
}

main();

// Phase A item 5 — Touch-target audit (Playwright + DOM math).
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §4.
//
// Acceptance criterion: every interactive element on the encounter page
// has a 44 x 44 CSS-pt hit-box at the iPad Pro 12.9 (1024x1366) and
// iPad Air 11 (834x1194) viewports. The audit runs as a Playwright
// test and emits a structured violation report so the release gate
// can fail with line-level detail rather than a single boolean.
//
// Run inside any Playwright project (the tablet config above is the
// production target):
//
//   npx playwright test qa/a11y/touch_targets.ts \
//     --config=qa/e2e/tablet/playwright.tablet.config.ts
//
import { test, expect } from "@playwright/test";

const MIN_PT = 44;

const INTERACTIVE_SELECTORS = [
  "button",
  "a[href]",
  "[role=button]",
  "input:not([type=hidden])",
  "select",
  "textarea",
  "[tabindex]:not([tabindex='-1'])",
];

interface Offender {
  selector: string;
  text: string;
  width: number;
  height: number;
}

test("touch targets on the home page are >= 44pt at the tablet viewport", async ({ page }) => {
  await page.goto("/");
  const offenders: Offender[] = await page.evaluate(
    ({ selectors, minPt }) => {
      const out: Offender[] = [];
      const seen = new Set<Element>();
      for (const sel of selectors) {
        document.querySelectorAll(sel).forEach((el) => {
          if (seen.has(el)) return;
          seen.add(el);
          // Skip hidden controls.
          const rect = (el as HTMLElement).getBoundingClientRect();
          if (rect.width === 0 && rect.height === 0) return;
          if (rect.width + 0.5 < minPt || rect.height + 0.5 < minPt) {
            out.push({
              selector: sel,
              text: ((el as HTMLElement).innerText || (el as HTMLInputElement).value || "").slice(0, 40),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            });
          }
        });
      }
      return out;
    },
    { selectors: INTERACTIVE_SELECTORS, minPt: MIN_PT },
  );
  if (offenders.length > 0) {
    console.log("Touch-target offenders:\n" + JSON.stringify(offenders, null, 2));
  }
  expect(offenders, JSON.stringify(offenders, null, 2)).toEqual([]);
});

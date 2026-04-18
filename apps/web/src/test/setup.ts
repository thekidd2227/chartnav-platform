import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// React Testing Library doesn't auto-cleanup under Vitest globals mode;
// wire it up explicitly so tests don't bleed DOM state into each other.
afterEach(() => {
  cleanup();
  // Clear our dev-identity persistence between tests.
  try {
    window.localStorage.clear();
  } catch {
    // localStorage may not be available in some environments
  }
});

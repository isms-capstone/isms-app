import { defineConfig } from "@playwright/test";

const python = process.env.WRK_QA_PYTHON || "python";
process.env.WRK_LEGACY_QA = "0";
export default defineConfig({
  testDir: "./tests",
  testMatch: [
    "similarity.spec.ts",
    "sim-live.spec.ts",
    "work-category.spec.ts",
    "worklog-canonical.spec.ts",
    "worklog-contract.spec.ts",
    "frontend.spec.ts",
  ],
  workers: 1,
  timeout: 60000,
  outputDir: "test-results/sim-latest",
  reporter: "list",
  use: {
    baseURL: "http://localhost:3147",
    channel:
      process.env.PLAYWRIGHT_CHANNEL ||
      (process.platform === "win32" ? "msedge" : undefined),
    headless: true,
    viewport: { width: 1440, height: 1050 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn preview_registry:app --app-dir ../backend/tests --host 127.0.0.1 --port 8878`,
      url: "http://127.0.0.1:8878/openapi.json",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command:
        "node node_modules/next/dist/bin/next dev --hostname localhost --port 3147",
      url: "http://localhost:3147/login",
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        BACKEND_URL: "http://127.0.0.1:8878",
        NEXT_DIST_DIR: process.env.NEXT_DIST_DIR || ".next-sim-latest-qa",
        WRK_LEGACY_QA: "0",
      },
    },
  ],
});

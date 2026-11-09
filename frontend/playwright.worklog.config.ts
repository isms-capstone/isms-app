import { defineConfig } from "@playwright/test";

const legacy = process.env.WRK_QA_FORMAT !== "canonical";
process.env.WRK_LEGACY_QA = legacy ? "1" : "0";
const python = process.env.WRK_QA_PYTHON || "python";
export default defineConfig({
  testDir: "./tests",
  testMatch: legacy
    ? ["worklog-legacy.spec.ts", "worklog-contract.spec.ts"]
    : process.env.CAT_QA_MARIADB === "1"
      ? [
          "cat-acceptance.spec.ts",
          "worklog-canonical.spec.ts",
          "worklog-contract.spec.ts",
        ]
      : ["worklog-canonical.spec.ts", "worklog-contract.spec.ts"],
  workers: 1,
  timeout: 120000,
  expect: { timeout: 15000 },
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3102",
    channel:
      process.env.PLAYWRIGHT_CHANNEL ||
      (process.platform === "win32" ? "msedge" : undefined),
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1440, height: 1050 },
    hasTouch: process.env.CAT_QA_MARIADB === "1",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn ${legacy ? "preview_legacy_worklogs" : process.env.CAT_QA_MARIADB === "1" ? "qa_mariadb_server" : "preview_registry"}:app --app-dir ../backend/tests --host 127.0.0.1 --port 8878`,
      url: "http://127.0.0.1:8878/openapi.json",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command:
        "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3102",
      url: "http://127.0.0.1:3102/login",
      env: {
        BACKEND_URL: "http://127.0.0.1:8878",
        NEXT_DIST_DIR: ".next-wrk-qa",
        WRK_LEGACY_QA: legacy ? "1" : "0",
      },
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});

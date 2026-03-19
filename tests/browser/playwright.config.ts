import { defineConfig } from "@playwright/test";

const frontendUrl = process.env.FRONTEND_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: frontendUrl,
    viewport: { width: 1920, height: 1068 },
    trace: "retain-on-failure",
    video: "on",
    screenshot: "only-on-failure",
  },
  outputDir: "./artifacts/test-results",
  reporter: [
    ["list"],
    ["json", { outputFile: "./artifacts/playwright-results.json" }],
    ["html", { outputFolder: "./artifacts/html-report", open: "never" }],
    ["junit", { outputFile: "./artifacts/junit.xml" }],
  ],
});

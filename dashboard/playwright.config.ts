import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://127.0.0.1:4173", trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Servidor simulado (Prism) generado del contrato OpenAPI.
      command: "../backend/scripts/mock-api.sh",
      url: "http://127.0.0.1:4010/v1/replay",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run build && npm run preview",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { VITE_API_URL: "http://127.0.0.1:4010", VITE_MAP_STYLE: "empty" },
    },
  ],
});

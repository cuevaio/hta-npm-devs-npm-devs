import { defineConfig, devices } from "@playwright/test";

// El e2e corre contra los despliegues públicos. Cada URL se configura por
// variable de entorno; los tests de una superficie sin URL se saltan.
export const urls = {
  api: process.env.E2E_API_URL,
  dashboard: process.env.E2E_DASHBOARD_URL,
  landing: process.env.E2E_LANDING_URL,
};

export default defineConfig({
  testDir: "tests",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: { trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});

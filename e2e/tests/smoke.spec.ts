import { expect, test } from "@playwright/test";
import { urls } from "../playwright.config";

test("la Domain API responde /health con PostGIS", async ({ request }) => {
  test.skip(!urls.api, "E2E_API_URL no configurada");

  const response = await request.get(`${urls.api}/health`);

  expect(response.status()).toBe(200);
  expect((await response.json()).postgis).toBeTruthy();
});

test("el dashboard público carga", async ({ page }) => {
  test.skip(!urls.dashboard, "E2E_DASHBOARD_URL no configurada");

  await page.goto(urls.dashboard!);

  await expect(page.getByRole("heading", { name: "Fleet Intelligence" })).toBeVisible();
});

test("la landing pública carga", async ({ page }) => {
  test.skip(!urls.landing, "E2E_LANDING_URL no configurada");

  await page.goto(urls.landing!);

  await expect(page).toHaveTitle(/Fleet Intelligence/);
});

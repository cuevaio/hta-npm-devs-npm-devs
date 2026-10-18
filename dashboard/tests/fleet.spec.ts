import { expect, test } from "@playwright/test";

const ALIAS = ["T03", "T07", "T28", "T04", "T22", "T09"];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Cargando…")).toBeHidden();
});

test("lista los vehículos del replay con su estado en palabras", async ({ page }) => {
  for (const a of ALIAS) await expect(page.locator(`button.vehicle[data-alias="${a}"]`)).toBeVisible();
  const t03 = page.locator('button.vehicle[data-alias="T03"]');
  await expect(t03).toContainText("En viaje");
  await expect(page.locator('button.vehicle[data-alias="T28"]')).toContainText("Detenido");
  await expect(page.locator('button.vehicle[data-alias="T04"]')).toContainText("Ralentí");
  await expect(t03).toContainText("hora de Lima");
});

test("el viaje V-001 muestra corredor y sentido", async ({ page }) => {
  const t03 = page.locator('button.vehicle[data-alias="T03"]');
  await expect(t03).toContainText("V-001");
  await expect(t03).toContainText("LIM-AQP");
  await expect(t03).toContainText("sentido ida");
});

test("el mapa tiene un marcador por vehículo y la selección lo resalta", async ({ page }) => {
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  for (const a of ALIAS) await expect(page.locator(`.marker[aria-label="${a}"]`)).toHaveCount(1);
  await page.locator('button.vehicle[data-alias="T03"]').click();
  await expect(page.locator('.marker[aria-label="T03"]')).toHaveClass(/is-selected/);
  await expect(page.locator('.marker[aria-label="T07"]')).not.toHaveClass(/is-selected/);
});

test("muestra la procedencia y el aviso de replay", async ({ page }) => {
  await expect(page.getByText("Calculado por el sistema")).toBeVisible();
  await expect(page.getByText("Sintético", { exact: true })).toBeVisible();
  await expect(page.getByRole("note")).toContainText("No es tiempo real");
});

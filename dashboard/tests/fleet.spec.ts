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

test("cada vehículo muestra la altitud de su última posición en msnm", async ({ page }) => {
  await expect(page.locator('button.vehicle[data-alias="T03"]')).toContainText("575 msnm"); // costa, LIM-AQP
  await expect(page.locator('button.vehicle[data-alias="T28"]')).toContainText(/3[\s.,]?831 msnm/); // altiplano, AQP-JUL
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

test("cada vehículo es un tractocamión en el mapa que gira hacia donde avanza", async ({ page }) => {
  let n = 0;
  await page.route("http://127.0.0.1:4010/v1/fleet", async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    n++;
    const t03 = body.data.vehiculos.find((v: { alias: string }) => v.alias === "T03");
    t03.posicion.lat -= 0.01 * n; // hacia el sureste
    t03.posicion.lon += 0.01 * n;
    await route.fulfill({ response: res, json: body });
  });
  await page.goto("/");
  const marker = page.locator('.marker[aria-label="T03"]');
  await expect(marker.locator("svg.camion")).toHaveCount(1);
  await expect(marker).toHaveAttribute("data-estado", "en_viaje");
  await expect
    .poll(async () => parseFloat(await marker.evaluate((el) => el.style.getPropertyValue("--rumbo"))), { timeout: 10_000 })
    .toBeGreaterThan(90);
  const rumbo = parseFloat(await marker.evaluate((el) => el.style.getPropertyValue("--rumbo")));
  expect(rumbo).toBeLessThan(180);
});

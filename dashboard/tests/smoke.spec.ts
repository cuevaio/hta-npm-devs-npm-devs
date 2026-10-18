import { expect, test } from "@playwright/test";

test("el dashboard carga sin errores de consola", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Certera" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("tiene el favicon de Certera", async ({ page, request }) => {
  await page.goto("/");
  const href = await page.locator('link[rel="icon"]').getAttribute("href");
  expect((await request.get(href!)).status()).toBe(200);
});

test.describe("con movimiento reducido", () => {
  test.use({ reducedMotion: "reduce" });

  test("los números se muestran sin animar", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Fletes" }).click();
    // sin animación el valor final está desde el primer pintado: no hace falta esperar al conteo
    await expect(page.getByRole("region", { name: "Resumen de fletes finalizados" })).toContainText("S/ 4,190", { timeout: 1000 });
  });
});

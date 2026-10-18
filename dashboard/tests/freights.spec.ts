import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Fletes" }).click();
  await expect(page.getByRole("main", { name: "Fletes" })).toBeVisible();
});

test("resume ingresos, combustible y margen de los fletes finalizados en soles", async ({ page }) => {
  const kpis = page.getByRole("region", { name: "Resumen de fletes finalizados" });
  await expect(kpis).toContainText("S/ 4,190");
  await expect(kpis).toContainText("S/ 2,062");
  await expect(kpis).toContainText("50.8 % de los ingresos");
  await expect(kpis).toContainText("47.5 L/100 km");
  await expect(kpis).toContainText("1 en curso");
});

test("un flete en curso no muestra combustible ni margen todavía", async ({ page }) => {
  const curso = page.locator('tr[data-flete="F-102"]');
  await expect(curso).toContainText("En curso");
  await expect(curso.locator("td").last()).toHaveText("–");
  const fin = page.locator('tr[data-flete="F-101"]');
  await expect(fin).toContainText("Finalizado");
  await expect(fin).toContainText("V001-00000101");
  await expect(fin).toContainText("RUC 20481234565");
});

test("los gráficos por corredor y por día tienen leyenda y tooltip", async ({ page }) => {
  const corredor = page.getByRole("figure", { name: "Ingresos por corredor" });
  await expect(corredor).toContainText("Combustible");
  await expect(corredor).toContainText("Margen");
  await corredor.locator('.bar[data-clave="LIM-AQP"]').hover();
  await expect(page.getByRole("tooltip")).toContainText("Margen S/ 2,128 (50.8 %)");
  await expect(page.getByRole("figure", { name: "Ingresos por día de llegada" }).locator(".bar")).toHaveCount(1);
});

test("la tabla por vehículo resume cada tractocamión", async ({ page }) => {
  await expect(page.locator('table[data-table="vehiculos"] tbody tr')).toHaveCount(1);
  await expect(page.locator('table[data-table="vehiculos"]')).toContainText("T07");
});

test("el detalle muestra primero los fletes en curso", async ({ page }) => {
  await expect(page.locator('table[data-table="fletes"] tbody tr').first()).toHaveAttribute("data-flete", "F-102");
});

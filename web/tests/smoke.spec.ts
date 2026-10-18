import { expect, test } from "@playwright/test";

const SECCIONES = ["hero", "problema", "como-funciona", "ejemplo", "arquitectura", "mcp", "procedencia", "cta"];

test("describe Fleet Intelligence con el titular y las ocho secciones", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.goto("/");

  await expect(page).toHaveTitle(/Fleet Intelligence/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Un agente de IA que lee la montaña antes de que tu flota la suba.",
  );
  for (const id of SECCIONES) await expect(page.locator(`section#${id}`)).toHaveCount(1);
  await expect(page.locator("#problema")).toContainText("4.800 msnm");
  await expect(page.locator("#ejemplo")).toContainText("T04");
  await expect(page.locator("#ejemplo")).toContainText("Ticlio");
  await expect(page.locator("#como-funciona")).toContainText("WhatsApp");
  await expect(page.locator("#arquitectura")).toContainText("LangGraph");
  await expect(page.locator("#mcp")).toContainText("solo lectura");
  expect(errors).toEqual([]);
});

test("no usa el nombre ni el logo de Cuadra y carga tokens.css", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).not.toContainText(/cuadra/i);
  const refs = await page.evaluate(() =>
    Array.from(document.querySelectorAll("img[src],use,link[href],script[src],source[src]"))
      .map((e) => e.getAttribute("src") ?? e.getAttribute("href") ?? e.getAttribute("xlink:href") ?? "")
      .filter((u) => /cuadra-/i.test(u)),
  );
  expect(refs).toEqual([]);
  expect(await page.locator('link[rel="stylesheet"][href="assets/tokens.css"]').count()).toBe(1);
  const tinta = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(tinta).toBe("rgb(7, 9, 15)");
});

test("declara la procedencia de los datos y enlaza al dashboard", async ({ page }) => {
  await page.goto("/");
  const proc = page.locator("#procedencia");
  await expect(proc).toContainText("FEAD");
  await expect(proc).toContainText("sintéticos");
  const link = page.getByRole("link", { name: /dashboard/i }).first();
  await expect(link).toHaveAttribute("href", /^https?:\/\//);
});

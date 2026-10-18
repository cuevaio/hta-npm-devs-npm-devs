import { expect, test } from "@playwright/test";

const SECCIONES = ["hero", "problema", "simulador", "como-funciona", "diferenciador", "torre", "procedencia", "cta"];

test("describe Certera con el titular y sus secciones", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.goto("/");

  await expect(page).toHaveTitle(/Certera/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Señales claras. Decisiones certeras.");
  for (const id of SECCIONES) await expect(page.locator(`section#${id}`)).toHaveCount(1);
  await expect(page.locator("#problema")).toContainText("4 800 msnm");
  await expect(page.locator("#diferenciador")).toContainText("Ticlio");
  await expect(page.locator("#como-funciona")).toContainText("WhatsApp");
  await expect(page.locator("#torre")).toContainText("solo lectura");
  expect(errors).toEqual([]);
});

test("no usa la marca ni el logo de Cuadra y carga tokens.css", async ({ page }) => {
  await page.goto("/");
  // "cuadra" en minúscula es el verbo ("si una parada no cuadra"); la marca va con mayúscula.
  await expect(page.locator("body")).not.toContainText("Cuadra");
  const refs = await page.evaluate(() =>
    Array.from(document.querySelectorAll("img[src],use,link[href],script[src],source[src],iframe[src]"))
      .map((e) => e.getAttribute("src") ?? e.getAttribute("href") ?? e.getAttribute("xlink:href") ?? "")
      .filter((u) => /cuadra-/i.test(u)),
  );
  expect(refs).toEqual([]);
  expect(await page.locator('link[rel="stylesheet"][href="assets/tokens.css"]').count()).toBe(1);
  const tinta = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(tinta).toBe("rgb(5, 7, 6)");
});

test("el simulador del viaje real se carga en su sección", async ({ page }) => {
  await page.goto("/");
  await page.locator("#simulador").scrollIntoViewIfNeeded();
  const sim = page.frameLocator("#simuladorFrame");
  await expect(sim.locator(".iso-stage svg")).toBeVisible();
  await expect(sim.locator("[data-play]")).toBeVisible();
  await expect(sim.locator("[data-lkm]")).not.toHaveText("–");
});

test("enlaza al dashboard y avisa que las cifras son ilustrativas", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#procedencia .aviso")).toContainText("estimaciones");
  const link = page.getByRole("link", { name: /dashboard/i }).first();
  await expect(link).toHaveAttribute("href", /^https?:\/\//);
});

test("tiene favicon y la vista previa para compartir en redes", async ({ page, request }) => {
  await page.goto("/");
  const meta = (sel: string) => page.locator(sel).first().getAttribute("content");
  expect(await meta('meta[property="og:title"]')).toMatch(/Certera/);
  expect(await meta('meta[property="og:description"]')).toBeTruthy();
  expect(await meta('meta[name="twitter:card"]')).toBe("summary_large_image");
  const og = await meta('meta[property="og:image"]');
  expect(og).toMatch(/^https:\/\/.+\/assets\/og-certera\.png$/);

  // Los archivos existen en el sitio (las URLs absolutas apuntan al dominio de Vercel).
  const rutas = [
    new URL(og!).pathname,
    ...(await page.locator('link[rel="icon"], link[rel="apple-touch-icon"], link[rel="manifest"]').evaluateAll(
      (els) => els.map((e) => "/" + e.getAttribute("href")),
    )),
  ];
  for (const ruta of rutas) expect((await request.get(ruta)).status(), ruta).toBe(200);
});

test("los enlaces y metadatos apuntan a los dominios desplegados, ninguno con certera", async ({ page }) => {
  await page.goto("/");
  const urls = await page.evaluate(() =>
    [
      ...Array.from(document.querySelectorAll("a[href], link[href]")).map((e) => e.getAttribute("href") ?? ""),
      ...Array.from(document.querySelectorAll("meta[content]")).map((e) => e.getAttribute("content") ?? ""),
    ].filter((u) => /^https?:\/\//.test(u)),
  );
  for (const u of urls) expect(new URL(u).hostname, u).not.toMatch(/certera/i);
  for (const a of await page.locator("a.dashboard-link").all())
    await expect(a).toHaveAttribute("href", "https://fleet-intelligence-dashboard.vercel.app");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://fleet-intelligence-ashy.vercel.app/");
});

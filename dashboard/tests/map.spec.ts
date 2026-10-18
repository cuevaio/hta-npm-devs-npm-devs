import { expect, test, type Page } from "@playwright/test";

/**
 * Mapa: los camiones van sobre la vía real (no en línea recta entre lecturas) y al elegir uno la cámara
 * vuela, se inclina y lo sigue. Corre con MapLibre y estilo vacío (sin token ni red); el código del
 * movimiento y de la cámara es el mismo que con Mapbox.
 */

const API = "http://127.0.0.1:4010";
// Serpentín: media vuelta de ~1 km de radio alrededor de (-76, -12), como una curva de la Carretera Central.
const CENTRO = [-76, -12] as const;
const R_GRADOS = 1 / 111.195;
const K = Math.cos((12 * Math.PI) / 180);
const curva = Array.from({ length: 181 }, (_, i) => {
  const a = (i * Math.PI) / 180;
  return [CENTRO[0] + (R_GRADOS * Math.sin(a)) / K, CENTRO[1] + R_GRADOS * Math.cos(a)];
});
const enCurva = (km: number) => {
  const a = Math.min(km, Math.PI); // radio 1 km: el ángulo en radianes es el km recorrido
  return { lon: CENTRO[0] + (R_GRADOS * Math.sin(a)) / K, lat: CENTRO[1] + R_GRADOS * Math.cos(a) };
};
/** Distancia (m) de un punto a la curva: |distancia al centro − radio|. */
const aLaCurvaM = (lon: number, lat: number) =>
  Math.abs(Math.hypot((lon - CENTRO[0]) * K, lat - CENTRO[1]) * 111_195 - 1000);

/** T03 recorre el serpentín: el replay va a 20x y cada lectura lo deja ~0,9 km más adelante. */
async function serpentin(page: Page) {
  let n = 0;
  await page.route(`${API}/v1/corridors`, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body.data.corredores = [{ corredor: "LIM-AQP", via: "Prueba", origen: "LIM", destino: "AQP", largo_km: Math.PI, coordenadas: curva }];
    await route.fulfill({ response: res, json: body });
  });
  await page.route(`${API}/v1/replay`, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body.data.estado = "playing";
    body.data.velocidad = 20;
    await route.fulfill({ response: res, json: body });
  });
  await page.route(`${API}/v1/fleet`, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    const t03 = body.data.vehiculos.find((v: { alias: string }) => v.alias === "T03");
    t03.posicion = enCurva(0.2 + 0.9 * n++);
    t03.velocidad_kmh = 80;
    await route.fulfill({ response: res, json: body });
  });
}

const marcador = (page: Page, alias: string) => page.locator(`.marker[aria-label="${alias}"]`);
const posicion = async (page: Page, alias: string) => {
  const [lng, lat] = await marcador(page, alias).evaluate((el) => [Number((el as HTMLElement).dataset.lng), Number((el as HTMLElement).dataset.lat)]);
  return { lng, lat };
};
const mapa = (page: Page) => page.getByTestId("fleet-map");
const dato = (page: Page, k: string) => mapa(page).evaluate((el, key) => (el as HTMLElement).dataset[key] ?? "", k);

test("entre dos lecturas el camión sigue la curva de la vía, no la recta", async ({ page }) => {
  await serpentin(page);
  await page.goto("/");
  await expect(marcador(page, "T03")).toHaveCount(1);
  await page.waitForTimeout(2500); // que llegue la geometría y la segunda lectura
  let peor = 0;
  const vistos: number[] = [];
  for (let i = 0; i < 40; i++) {
    const p = await posicion(page, "T03");
    peor = Math.max(peor, aLaCurvaM(p.lng, p.lat));
    vistos.push(p.lng);
    await page.waitForTimeout(100);
  }
  expect(peor).toBeLessThan(5); // la cuerda entre dos lecturas pasa a ~100 m por dentro de la curva
  expect(new Set(vistos.map((x) => x.toFixed(5))).size).toBeGreaterThan(10); // se mueve en cada cuadro
});

test("al elegir un tráiler la cámara vuela, se inclina en 3D y lo sigue", async ({ page }) => {
  await serpentin(page);
  await page.goto("/");
  await page.locator('button.vehicle[data-alias="T03"]').click();
  await expect.poll(() => dato(page, "camara"), { timeout: 8000 }).toBe("siguiendo");
  expect(Number(await dato(page, "pitch"))).toBeGreaterThanOrEqual(55);
  expect(Number(await dato(page, "zoom"))).toBeGreaterThan(15);
  await expect(page.getByRole("group", { name: "Cámara" })).toContainText("Siguiendo T03");
  // durante 2 s el centro del mapa acompaña al camión
  for (let i = 0; i < 10; i++) {
    // centro y camión del mismo cuadro: a 20x el camión avanza ~440 m por segundo
    const [lng, lat, plng, plat] = await page.evaluate(() => {
      const m = document.querySelector<HTMLElement>('[data-testid="fleet-map"]')!.dataset;
      const t = document.querySelector<HTMLElement>('.marker[aria-label="T03"]')!.dataset;
      return [...m.centro!.split(",").map(Number), Number(t.lng), Number(t.lat)];
    });
    expect(Math.hypot((lng - plng) * K, lat - plat) * 111_195).toBeLessThan(60);
    await page.waitForTimeout(200);
  }
});

test("mover el mapa deja de seguir; Seguir vuelve y Ver flota regresa a la vista general", async ({ page }) => {
  await serpentin(page);
  await page.goto("/");
  await page.locator('button.vehicle[data-alias="T03"]').click();
  await expect.poll(() => dato(page, "camara"), { timeout: 8000 }).toBe("siguiendo");
  const caja = (await mapa(page).boundingBox())!;
  // lejos del centro: ahí está el camión seguido y un clic sobre él no arrastra el mapa
  const x = caja.x + caja.width * 0.25;
  const y = caja.y + caja.height * 0.3;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 160, y + 60, { steps: 8 });
  await page.mouse.up();
  await expect.poll(() => dato(page, "camara")).toBe("libre");
  const grupo = page.getByRole("group", { name: "Cámara" });
  await grupo.getByRole("button", { name: "Seguir" }).click();
  await expect.poll(() => dato(page, "camara"), { timeout: 8000 }).toBe("siguiendo");
  await grupo.getByRole("button", { name: "Ver flota" }).click();
  await expect(grupo).toBeHidden();
  await expect.poll(async () => Number(await dato(page, "pitch")), { timeout: 5000 }).toBeLessThan(1);
  await expect(marcador(page, "T03")).not.toHaveClass(/is-selected/);
});

test("un clic sobre el camión seguido no suelta el seguimiento", async ({ page }) => {
  await serpentin(page);
  await page.goto("/");
  await page.locator('button.vehicle[data-alias="T03"]').click();
  await expect.poll(() => dato(page, "camara"), { timeout: 8000 }).toBe("siguiendo");
  await marcador(page, "T03").click({ force: true });
  await page.waitForTimeout(600);
  expect(await dato(page, "camara")).toBe("siguiendo");
});

test("el camión mide su tamaño real con zoom alto y se achica al alejarse", async ({ page }) => {
  await serpentin(page);
  await page.goto("/");
  const escala = () => mapa(page).evaluate((el) => Number((el as HTMLElement).style.getPropertyValue("--escala")));
  await expect.poll(escala).toBeCloseTo(0.45, 2); // vista de todo Perú: tamaño mínimo legible
  await page.locator('button.vehicle[data-alias="T03"]').click();
  await expect.poll(() => dato(page, "camara"), { timeout: 8000 }).toBe("siguiendo");
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.waitForTimeout(400);
  }
  await expect.poll(escala, { timeout: 5000 }).toBeGreaterThan(1); // zoom ~18,5: 18 m reales ocupan más que el SVG base
  await expect(page.locator('.marker-tag:has-text("T03")')).toHaveCount(1); // la etiqueta sigue de frente
});

test.describe("con movimiento reducido", () => {
  test.use({ reducedMotion: "reduce" });

  test("la cámara salta al camión sin volar y lo deja en 3D", async ({ page }) => {
    await serpentin(page);
    await page.goto("/");
    await expect(marcador(page, "T03")).toHaveCount(1);
    await page.locator('button.vehicle[data-alias="T03"]').click();
    await expect.poll(() => dato(page, "camara"), { timeout: 1000 }).toBe("siguiendo");
    expect(Number(await dato(page, "pitch"))).toBeCloseTo(60, 0);
  });
});

test("el mapa ocupa su panel y entra en la ventana (la lista hace scroll por dentro)", async ({ page }) => {
  await page.goto("/");
  await expect(marcador(page, "T03")).toHaveCount(1);
  const caja = (await mapa(page).boundingBox())!;
  expect(caja.height).toBeGreaterThan(300); // el CSS del motor no lo colapsa
  expect(caja.width).toBeGreaterThan(300);
  expect(caja.y + caja.height).toBeLessThanOrEqual(page.viewportSize()!.height + 1); // la flota se ve entera
  await page.locator('button.vehicle[data-alias="T09"]').click();
  expect(await page.evaluate(() => scrollY)).toBeLessThan(20); // elegir de la lista casi no desplaza la página
});

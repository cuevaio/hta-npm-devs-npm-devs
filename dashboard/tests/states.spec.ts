import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:4010";

/** Parte de la respuesta del simulado y deja que `edit` la modifique. */
async function override(page: Page, path: string, edit: (body: any) => void, delayMs = 0) {
  await page.route(`${API}${path}`, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    edit(body);
    if (delayMs) await new Promise((r) => setTimeout(r, delayMs));
    await route.fulfill({ response: res, json: body });
  });
}

test("flota vacía", async ({ page }) => {
  await override(page, "/v1/fleet", (b) => {
    b.data.vehiculos = [];
    b.data.total_vehiculos = 0;
  });
  await page.goto("/");
  await expect(page.getByText("Sin vehículos en el replay")).toBeVisible();
});

test("carga mientras responde la Domain API", async ({ page }) => {
  await override(page, "/v1/fleet", () => {}, 1500);
  await page.goto("/");
  await expect(page.getByText("Cargando…")).toBeVisible();
  await expect(page.getByText("Cargando…")).toBeHidden();
  await expect(page.locator('button.vehicle[data-alias="T03"]')).toBeVisible();
});

test("vehículo con hora del evento 6 min detrás del replay", async ({ page }) => {
  await override(page, "/v1/replay", (b) => {
    b.data.hora_replay = "2020-04-14T03:36:00Z";
  });
  await override(page, "/v1/fleet", (b) => {
    b.data.vehiculos[0].hora_evento = "2020-04-14T03:30:00Z";
    b.data.vehiculos[1].hora_evento = "2020-04-14T03:35:00Z";
  });
  await page.goto("/");
  await expect(page.locator('button.vehicle[data-alias="T03"]')).toContainText("Desactualizado");
  await expect(page.locator('button.vehicle[data-alias="T07"]')).not.toContainText("Desactualizado");
});

test("error 500 de la Domain API", async ({ page }) => {
  await page.route(`${API}/v1/fleet`, (route) => route.fulfill({ status: 500, json: { detail: "boom" } }));
  await page.goto("/");
  await expect(page.getByText("No se pudo leer la Domain API")).toBeVisible();
});

test("con la Domain API lenta no acumula peticiones: una a la vez", async ({ page }) => {
  let inFlight = 0;
  let max = 0;
  let done = 0;
  await page.route(`${API}/v1/fleet`, async (route) => {
    inFlight++;
    max = Math.max(max, inFlight);
    const res = await route.fetch();
    await new Promise((r) => setTimeout(r, 3000)); // más lento que el intervalo de 2 s
    await route.fulfill({ response: res });
    inFlight--;
    done++;
  });
  await page.goto("/");
  await expect.poll(() => done, { timeout: 15_000 }).toBeGreaterThanOrEqual(2);
  expect(max).toBe(1);
});

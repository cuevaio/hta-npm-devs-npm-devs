import { expect, test } from "@playwright/test";

test("el dashboard carga sin errores de consola", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Fleet Intelligence" })).toBeVisible();
  expect(errors).toEqual([]);
});

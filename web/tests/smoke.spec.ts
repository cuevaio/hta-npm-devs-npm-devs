import { expect, test } from "@playwright/test";

test("la landing carga sin errores y sin la marca anterior", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto("/");

  await expect(page).toHaveTitle(/Fleet Intelligence/);
  await expect(page.getByRole("navigation")).not.toContainText("Cuadra");
  expect(errors).toEqual([]);
});

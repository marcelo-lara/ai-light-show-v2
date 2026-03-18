import { expect, type Locator, type Page } from "@playwright/test";

export async function gotoApp(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Song Analysis" })).toBeVisible();
}

export async function gotoRoute(page: Page, routeLabel: "Show Control" | "Song Analysis" | "Show Builder" | "DMX Control") {
  await gotoApp(page);
  await page.getByRole("button", { name: routeLabel }).click();
}

export function region(page: Page, name: string): Locator {
  return page.getByRole("region", { name });
}

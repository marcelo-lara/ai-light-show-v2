import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

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

export async function collectDmxDiagnostics(page: Page) {
  return page.evaluate(() => {
    const fixtureCards = Array.from(document.querySelectorAll<HTMLElement>(".fixture-card"));
    const targetFixture = document.querySelector<HTMLElement>("[aria-label='Mini Beam Prism (L) fixture']");
    const dmxView = document.querySelector<HTMLElement>("[aria-label='DMX Control view']");
    return {
      wsState: (globalThis as any).__WS_STATE__ ?? null,
      snapshot: (globalThis as any).__LAST_SNAPSHOT_DIAGNOSTICS__ ?? null,
      fixtureCardCount: fixtureCards.length,
      targetFixturePresent: Boolean(targetFixture),
      targetFixtureText: targetFixture?.textContent?.trim() ?? null,
      dmxViewVisible: Boolean(dmxView),
    };
  });
}

export async function attachDmxDiagnostics(page: Page, testInfo: TestInfo) {
  const diagnostics = await collectDmxDiagnostics(page);
  await testInfo.attach("dmx-diagnostics", {
    body: JSON.stringify(diagnostics, null, 2),
    contentType: "application/json",
  });
}

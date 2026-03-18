import { expect, test } from "@playwright/test";
import { gotoRoute } from "./helpers";

test("[DMX-ARM-TOGGLE] toggles a fixture arm state visibly", async ({ page }) => {
  await gotoRoute(page, "DMX Control");

  const fixture = page.getByRole("article", { name: "Mini Beam Prism (L) fixture" });
  await expect(fixture).toBeVisible();

  const armedToggle = fixture.getByRole("checkbox", { name: "Armed" });
  const initialValue = await armedToggle.isChecked();
  await armedToggle.click();
  await expect(armedToggle).toHaveJSProperty("checked", !initialValue);
  await armedToggle.click();
  await expect(armedToggle).toHaveJSProperty("checked", initialValue);
});

test("[DMX-EFFECT-PREVIEW-ENTRY] shows fixture effect preview controls", async ({ page }) => {
  await gotoRoute(page, "DMX Control");

  const fixture = page.getByRole("article", { name: "Mini Beam Prism (L) fixture" });
  await expect(fixture).toBeVisible();

  await expect(fixture.getByLabel("Preview effect type")).toBeVisible();
  await expect(fixture.getByLabel("Duration")).toBeVisible();
  const previewButton = fixture.getByRole("button", { name: "Preview effect" });
  await expect(previewButton).toBeVisible();

  await previewButton.click();
  await page.waitForTimeout(750);
});

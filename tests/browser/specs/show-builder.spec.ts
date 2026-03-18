import { expect, test } from "@playwright/test";
import { gotoRoute, region } from "./helpers";

test("[SB-EFFECT-CUE-EDIT] edits an existing effect cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const cueSheet = region(page, "Cue Sheet panel");
  await expect(cueSheet).toBeVisible();
  await cueSheet.getByRole("button", { name: "Edit cue" }).first().click();

  const effectPicker = region(page, "Effect Picker panel");
  await expect(effectPicker).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Update selected cue" })).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Cancel cue editing" })).toBeEnabled();
});

test("[SB-CHASER-CUE-EDIT] edits an existing chaser cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const chaserRow = page.locator(".cue-sheet-row").filter({ hasText: "Parcans left to right blue" }).first();
  await expect(chaserRow).toBeVisible();
  await chaserRow.getByRole("button", { name: "Edit cue" }).click();

  const chaserPicker = region(page, "Chaser Picker panel");
  await expect(chaserPicker).toBeVisible();
  await expect(chaserPicker.getByRole("button", { name: "Update chaser cue" })).toHaveText(/Update/);
  await expect(chaserPicker.getByLabel("Chaser name")).toHaveValue("blue_parcan_chase");
});

test("[SB-CUE-DELETE-CANCEL] opens delete confirmation and cancels without removing the cue", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const cueSheet = region(page, "Cue Sheet panel");
  const cueCount = await cueSheet.locator(".cue-sheet-row").count();
  await cueSheet.getByRole("button", { name: "Delete cue" }).first().click();

  const dialog = page.locator("dialog.confirm-cancel-prompt");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Delete cue" })).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(cueSheet.locator(".cue-sheet-row")).toHaveCount(cueCount);
});

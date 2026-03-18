import { expect, test, type Page } from "@playwright/test";
import { gotoRoute, region } from "./helpers";

async function waitForCueSheet(page: Page) {
  const cueSheet = region(page, "Cue Sheet panel");
  const rows = cueSheet.locator(".cue-sheet-row");
  await expect(cueSheet).toBeVisible();
  await expect(rows.first()).toBeVisible({ timeout: 20_000 });
  return { cueSheet, rows };
}

function cueRowBySummary(cueSheet: ReturnType<typeof region>, summaryPattern: RegExp) {
  return cueSheet
    .locator("article.cue-sheet-row")
    .filter({ hasText: summaryPattern })
    .first();
}

test("[SB-EFFECT-CUE-EDIT] edits an existing effect cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const { cueSheet } = await waitForCueSheet(page);
  const effectRow = cueRowBySummary(cueSheet, /3\.000\s*parcan l\s*strobe\s*1\.0s/i);
  await expect(effectRow).toBeVisible();
  await effectRow.getByRole("button", { name: "Edit cue" }).click();

  const effectPicker = region(page, "Effect Picker panel");
  await expect(effectPicker).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Update selected cue" })).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Cancel cue editing" })).toBeEnabled();
});

test("[SB-CHASER-CUE-EDIT] edits an existing chaser cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const { cueSheet } = await waitForCueSheet(page);
  const chaserRow = cueRowBySummary(cueSheet, /1\.360\s*Parcans left to right blue\s*2\.0s/i);
  await expect(chaserRow).toBeVisible();
  await chaserRow.getByRole("button", { name: "Edit cue" }).click();

  const chaserPicker = region(page, "Chaser Picker panel");
  await expect(chaserPicker).toBeVisible();
  await expect(chaserPicker.getByRole("button", { name: "Update chaser cue" })).toHaveText(/Update/);
  await expect(chaserPicker.getByLabel("Chaser name")).toHaveValue("blue_parcan_chase");
});

test("[SB-CUE-DELETE-CANCEL] opens delete confirmation and cancels without removing the cue", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const { cueSheet } = await waitForCueSheet(page);
  const cueCount = await cueSheet.locator(".cue-sheet-row").count();
  await cueSheet.getByRole("button", { name: "Delete cue" }).first().click();

  const dialog = page.locator("dialog.confirm-cancel-prompt");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Delete cue" })).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(cueSheet.locator(".cue-sheet-row")).toHaveCount(cueCount);
});

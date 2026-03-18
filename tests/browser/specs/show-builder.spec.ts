import { expect, test, type Page } from "@playwright/test";
import { gotoRoute, region } from "./helpers";

async function ensureAtLeastOneCue(page: Page) {
  const cueSheet = region(page, "Cue Sheet panel");
  const rows = cueSheet.locator(".cue-sheet-row");

  if (await rows.count()) {
    return cueSheet;
  }

  const effectPicker = region(page, "Effect Picker panel");
  await expect(effectPicker).toBeVisible();
  await effectPicker.getByRole("button", { name: "Add cue at the current playback time" }).click();
  await expect(rows.first()).toBeVisible();
  return cueSheet;
}

async function addChaserCue(page: Page) {
  const cueSheet = region(page, "Cue Sheet panel");
  const rows = cueSheet.locator(".cue-sheet-row");
  const initialCount = await rows.count();

  const chaserPicker = region(page, "Chaser Picker panel");
  await expect(chaserPicker).toBeVisible();
  const chaserSelect = chaserPicker.getByLabel("Chaser name");
  const chaserId = await chaserSelect.inputValue();
  const chaserLabel = (await chaserSelect.locator("option:checked").textContent())?.trim() ?? chaserId;
  await expect(chaserPicker.getByRole("button", { name: "Add chaser cue" })).toBeEnabled();
  await chaserPicker.getByRole("button", { name: "Add chaser cue" }).click();

  await expect(rows).toHaveCount(initialCount + 1);
  return { cueSheet, rows, chaserId, chaserLabel };
}

test("[SB-EFFECT-CUE-EDIT] edits an existing effect cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const cueSheet = await ensureAtLeastOneCue(page);
  const effectRow = cueSheet.locator(".cue-sheet-row").filter({
    hasText: /flash|strobe|sweep|full|seek/i,
  }).first();
  await expect(effectRow).toBeVisible();
  await effectRow.getByRole("button", { name: "Edit cue" }).click();

  const effectPicker = region(page, "Effect Picker panel");
  await expect(effectPicker).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Update selected cue" })).toBeVisible();
  await expect(effectPicker.getByRole("button", { name: "Cancel cue editing" })).toBeEnabled();
});

test("[SB-CHASER-CUE-EDIT] edits an existing chaser cue through the cue sheet", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const { rows, chaserId, chaserLabel } = await addChaserCue(page);
  const chaserRow = rows.filter({ hasText: chaserLabel }).last();
  await expect(chaserRow).toBeVisible();
  await chaserRow.getByRole("button", { name: "Edit cue" }).click();

  const chaserPicker = region(page, "Chaser Picker panel");
  await expect(chaserPicker).toBeVisible();
  await expect(chaserPicker.getByRole("button", { name: "Update chaser cue" })).toHaveText(/Update/);
  await expect(chaserPicker.getByLabel("Chaser name")).toHaveValue(chaserId);
});

test("[SB-CUE-DELETE-CANCEL] opens delete confirmation and cancels without removing the cue", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  const cueSheet = await ensureAtLeastOneCue(page);
  const cueCount = await cueSheet.locator(".cue-sheet-row").count();
  await cueSheet.getByRole("button", { name: "Delete cue" }).first().click();

  const dialog = page.locator("dialog.confirm-cancel-prompt");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Delete cue" })).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(cueSheet.locator(".cue-sheet-row")).toHaveCount(cueCount);
});

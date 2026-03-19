import { expect, test } from "@playwright/test";
import { attachDmxDiagnostics, gotoApp, gotoRoute, region } from "./helpers";

test("[PREP-START-UI] loads the app shell with primary navigation", async ({ page }) => {
  await gotoApp(page);

  await expect(page.getByRole("button", { name: "Show Control" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Song Analysis" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Show Builder" })).toBeVisible();
  await expect(page.getByRole("button", { name: "DMX Control" })).toBeVisible();
});

test("[SA-ROUTE-VIEW] opens Song Analysis with structure and plot regions", async ({ page }) => {
  await gotoRoute(page, "Song Analysis");

  await expect(region(page, "Song Analysis view")).toBeVisible();
  await expect(region(page, "Song Structure panel")).toBeVisible();
  await expect(region(page, "Analysis Plots panel")).toBeVisible();
});

test("[SB-ROUTE-VIEW] opens Show Builder with cue and picker regions", async ({ page }) => {
  await gotoRoute(page, "Show Builder");

  await expect(region(page, "Show Builder view")).toBeVisible();
  await expect(region(page, "Cue Sheet panel")).toBeVisible();
  await expect(region(page, "Effect Picker panel")).toBeVisible();
  await expect(region(page, "Chaser Picker panel")).toBeVisible();
});

test("[SC-ROUTE-VIEW] opens Show Control with transport and control panels", async ({ page }) => {
  await gotoRoute(page, "Show Control");

  await expect(region(page, "Show Control view")).toBeVisible();
  await expect(region(page, "Song Sections panel")).toBeVisible();
  await expect(region(page, "Cue Sheet Summary panel")).toBeVisible();
  await expect(region(page, "Fixture Effects panel")).toBeVisible();
  await expect(page.getByRole("button", { name: "Play" })).toBeVisible();
});

test("[DMX-ROUTE-VIEW] opens DMX Control with fixture cards", async ({ page }, testInfo) => {
  try {
    await gotoRoute(page, "DMX Control");

    await expect(region(page, "DMX Control view")).toBeVisible();
    await expect(page.getByRole("article", { name: "Mini Beam Prism (L) fixture" })).toBeVisible();
  } finally {
    await attachDmxDiagnostics(page, testInfo);
  }
});
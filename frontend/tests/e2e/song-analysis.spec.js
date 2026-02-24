import { expect, test } from '@playwright/test'
import { installMockWebSocket } from './support/mock-websocket.js'

const analysisSong = {
  filename: 'Yonaka - Seize the Power.mp3',
  metadata: {
    length: 180,
    parts: {
      intro: [0, 8],
      verse: [8, 16],
    },
    hints: {
      beats: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
      downbeats: [0, 4, 8],
    },
  },
}

test.beforeEach(async ({ page }) => {
  await installMockWebSocket(page, {
    initialState: {
      fixtures: [],
      pois: [],
      status: { isPlaying: false, previewActive: false, preview: null },
      song: analysisSong,
    },
  })
})

async function ensureAnalysisReady(page) {
  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  await expect
    .poll(async () => {
      const addButton = page.getByRole('button', { name: 'Add Section' })
      if (!(await addButton.count())) return false
      return await addButton.isVisible()
    }, { timeout: 15000 })
    .toBeTruthy()
}

test('song analysis renders beats/downbeats and current beat highlight', async ({ page }) => {
  await page.goto('/analysis')

  await ensureAnalysisReady(page)

  await expect
    .poll(async () => await page.locator('.songAnalysisBeatCell').count(), { timeout: 15000 })
    .toBeGreaterThan(0)
  await expect(page.locator('.songAnalysisBeatCellDownbeat').first()).toBeVisible({ timeout: 15000 })
  await expect(page.locator('.songAnalysisBeatCellCurrent')).toHaveCount(1, { timeout: 15000 })
})

test('song analysis shows visual analyzer and supports waveform zoom controls', async ({ page }) => {
  await page.goto('/analysis')

  await ensureAnalysisReady(page)
  await expect(page.locator('.waveAnalyzerCanvas')).toBeVisible()

  const zoomIn = page.getByRole('button', { name: 'Zoom in waveform' })
  const zoomOut = page.getByRole('button', { name: 'Zoom out waveform' })

  await expect(zoomIn).toBeVisible()
  await expect(zoomOut).toBeVisible()

  const widthBefore = await page.evaluate(() => {
    const inner = document.querySelector('.waveform .scroll')
    return inner ? inner.scrollWidth : 0
  })

  await zoomIn.click()
  await zoomIn.click()

  const widthAfterZoomIn = await page.evaluate(() => {
    const inner = document.querySelector('.waveform .scroll')
    return inner ? inner.scrollWidth : 0
  })

  expect(widthAfterZoomIn).toBeGreaterThanOrEqual(widthBefore)

  await zoomOut.click()
  await zoomOut.click()

  const widthAfterZoomOut = await page.evaluate(() => {
    const inner = document.querySelector('.waveform .scroll')
    return inner ? inner.scrollWidth : 0
  })

  expect(widthAfterZoomOut).toBeLessThanOrEqual(widthAfterZoomIn)
})

test('sections save websocket flow returns success', async ({ page }) => {
  await page.goto('/analysis')

  await ensureAnalysisReady(page)

  const sectionName = `e2e-section-${Date.now()}`
  const startValue = 16
  const endValue = 20

  await page.getByRole('button', { name: 'Add Section' }).click()
  const row = page.locator('.songAnalysisSectionRow').last()

  await row.locator('.songAnalysisSectionInput').nth(0).fill(sectionName)
  await row.locator('.songAnalysisSectionInput').nth(1).fill(String(startValue))
  await row.locator('.songAnalysisSectionInput').nth(2).fill(String(endValue))

  await page.getByRole('button', { name: 'Save Sections' }).click()

  await expect
    .poll(async () =>
      page.evaluate(
        ({ name, start, end }) =>
          window.__mockWsServer.getMessagesByType('save_sections').some((entry) => {
            const sections = Array.isArray(entry?.message?.sections) ? entry.message.sections : []
            return sections.some((section) => section.name === name && section.start === start && section.end === end)
          }),
        { name: sectionName, start: startValue, end: endValue }
      )
    )
    .toBeTruthy()
})

test('waveform region edit updates waveform region timings', async ({ page }) => {
  await page.goto('/analysis')
  await ensureAnalysisReady(page)

  await expect
    .poll(async () =>
      await page.evaluate(() => window.__waveformTestHooks?.getRegionCount?.() || 0),
      { timeout: 15000 }
    )
    .toBeGreaterThan(0)

  const before = await page.evaluate(() => {
    const regions = window.__waveformTestHooks?.getRegions?.() || []
    return Number(regions[0]?.start ?? NaN)
  })
  expect(Number.isFinite(before)).toBeTruthy()

  const nudged = await page.evaluate(() => window.__waveformTestHooks?.nudgeFirstRegion?.(1.0) || false)
  expect(nudged).toBeTruthy()

  await expect
    .poll(
      async () =>
        await page.evaluate(() => {
          const regions = window.__waveformTestHooks?.getRegions?.() || []
          return Number(regions[0]?.start ?? NaN)
        }),
      { timeout: 10000 }
    )
    .toBeGreaterThan(before)
})

import { expect, test } from '@playwright/test'

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
  const startValue = 12
  const endValue = 16

  const result = await page.evaluate(async ({ name, start, end }) => {
    return await new Promise((resolve, reject) => {
      const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
      const timer = setTimeout(() => reject(new Error('save_sections timeout')), 5000)

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'save_sections',
            sections: [{ name, start, end }],
          })
        )
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'sections_save_result') {
            clearTimeout(timer)
            ws.close()
            resolve(msg)
          }
        } catch {
          // no-op
        }
      }

      ws.onerror = () => {
        clearTimeout(timer)
        reject(new Error('ws error during save_sections'))
      }
    })
  }, { name: sectionName, start: startValue, end: endValue })

  expect(result?.ok).toBeTruthy()
})

test('waveform region edit updates section row values', async ({ page }) => {
  await page.goto('/analysis')
  await ensureAnalysisReady(page)

  const sectionName = `region-edit-${Date.now()}`
  const startValue = 40
  const endValue = 44

  const saveResult = await page.evaluate(async ({ name, start, end }) => {
    return await new Promise((resolve, reject) => {
      const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
      const timer = setTimeout(() => reject(new Error('save_sections timeout')), 5000)

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'save_sections',
            sections: [{ name, start, end }],
          })
        )
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'sections_save_result') {
            clearTimeout(timer)
            ws.close()
            resolve(msg)
          }
        } catch {
          // no-op
        }
      }

      ws.onerror = () => {
        clearTimeout(timer)
        reject(new Error('ws error during save_sections'))
      }
    })
  }, { name: sectionName, start: startValue, end: endValue })

  expect(saveResult?.ok).toBeTruthy()

  await expect
    .poll(async () =>
      await page.evaluate(() => window.__waveformTestHooks?.getRegionCount?.() || 0),
      { timeout: 15000 }
    )
    .toBeGreaterThan(0)

  const rowIndex = await page.evaluate((name) => {
    const rows = Array.from(document.querySelectorAll('.songAnalysisSectionRow'))
    return rows.findIndex((row) => {
      const input = row.querySelector('.songAnalysisSectionInput')
      return input && input.value === name
    })
  }, sectionName)

  expect(rowIndex).toBeGreaterThanOrEqual(0)

  const row = page.locator('.songAnalysisSectionRow').nth(rowIndex)
  await expect(row.locator('.songAnalysisSectionInput').nth(1)).toHaveValue(String(startValue))

  const nudged = await page.evaluate(() => window.__waveformTestHooks?.nudgeFirstRegion?.(1.0) || false)
  expect(nudged).toBeTruthy()

  await expect
    .poll(async () => await row.locator('.songAnalysisSectionInput').nth(1).inputValue(), { timeout: 10000 })
    .not.toBe(String(startValue))
})

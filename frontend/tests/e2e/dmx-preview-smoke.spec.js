import { expect, test } from '@playwright/test'

test('dmx preview controls render and disable during playback', async ({ page }) => {
  await page.goto('/dmx')

  await expect(page.getByRole('heading', { name: 'DMX Control' })).toBeVisible()

  const previewButtons = page.getByRole('button', { name: 'Preview' })
  await expect(previewButtons.first()).toBeVisible()
  await expect(previewButtons).toHaveCount(7)

  const effectSelects = page.locator('.fxSelect')
  await expect(effectSelects).toHaveCount(7)

  await expect(previewButtons.first()).toBeEnabled()
  await expect(effectSelects.first()).toBeEnabled()

  await page.evaluate(async () => {
    await new Promise((resolve, reject) => {
      const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
      const timer = setTimeout(() => {
        try {
          ws.close()
        } catch {
          // no-op
        }
        reject(new Error('timeout sending playback true'))
      }, 3000)

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'playback', playing: true }))
        setTimeout(() => {
          clearTimeout(timer)
          try {
            ws.close()
          } catch {
            // no-op
          }
          resolve(true)
        }, 250)
      }

      ws.onerror = () => {
        clearTimeout(timer)
        reject(new Error('ws error sending playback true'))
      }
    })
  })

  await expect(previewButtons.first()).toBeDisabled()
  await expect(effectSelects.first()).toBeDisabled()
  await expect(page.locator('input[type="range"]').first()).toBeDisabled()

  await page.evaluate(async () => {
    await new Promise((resolve, reject) => {
      const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
      const timer = setTimeout(() => {
        try {
          ws.close()
        } catch {
          // no-op
        }
        reject(new Error('timeout sending playback false'))
      }, 3000)

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'playback', playing: false }))
        setTimeout(() => {
          clearTimeout(timer)
          try {
            ws.close()
          } catch {
            // no-op
          }
          resolve(true)
        }, 250)
      }

      ws.onerror = () => {
        clearTimeout(timer)
        reject(new Error('ws error sending playback false'))
      }
    })
  })

  await expect(previewButtons.first()).toBeEnabled()
  await expect(effectSelects.first()).toBeEnabled()
})

test('dmx parcan_l flash preview triggers temporary preview lifecycle', async ({ page }) => {
  await page.goto('/dmx')

  await expect(page.getByRole('heading', { name: 'DMX Control' })).toBeVisible()

  await page.evaluate(() => {
    window.__previewEvents = []

    const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'preview_status') {
          window.__previewEvents.push(data)
        }
      } catch {
        // no-op
      }
    }

    window.__previewWatcher = ws
  })

  const parcanLCard = page.locator('.dmxCard', {
    has: page.getByRole('heading', { name: 'ParCan L' }),
  })

  await expect(parcanLCard).toBeVisible()
  await parcanLCard.locator('.fxSelect').selectOption('flash')
  await parcanLCard.getByRole('button', { name: 'Preview' }).click()

  await expect
    .poll(async () =>
      page.evaluate(() => window.__previewEvents.some((event) => event.active === true))
    )
    .toBeTruthy()

  await expect
    .poll(async () =>
      page.evaluate(() => window.__previewEvents.some((event) => event.active === false))
    )
    .toBeTruthy()

  await page.evaluate(() => {
    if (window.__previewWatcher) {
      try {
        window.__previewWatcher.close()
      } catch {
        // no-op
      }
    }
  })
})

test('moving head shows all POIs and applies mapped POI target', async ({ page }) => {
  await page.goto('/dmx')

  await expect(page.getByRole('heading', { name: 'DMX Control' })).toBeVisible()

  const headCard = page.locator('.dmxCard', {
    has: page.getByRole('heading', { name: 'Head EL-150' }),
  })
  await expect(headCard).toBeVisible()

  const poiButtons = headCard.locator('.poiGrid .poiButton')
  await expect(poiButtons).toHaveCount(14)

  const tablePoi = headCard.getByRole('button', { name: 'Table' })
  await expect(tablePoi).toHaveClass(/poiButtonUnmapped/)

  const readout = headCard.locator('.xyPadReadout')
  await headCard.getByRole('button', { name: 'Piano' }).click()
  await expect(readout).toContainText('Pan 30755 / Tilt 5131')
})

test('moving head shift+click saves POI target', async ({ page }) => {
  await page.goto('/dmx')

  await expect(page.getByRole('heading', { name: 'DMX Control' })).toBeVisible()

  const headCard = page.locator('.dmxCard', {
    has: page.getByRole('heading', { name: 'Head EL-150' }),
  })
  await expect(headCard).toBeVisible()

  await page.evaluate(() => {
    window.__fixtureUpdateEvents = []

    const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/ws`)
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'fixtures_updated') {
          window.__fixtureUpdateEvents.push(data)
        }
      } catch {
        // no-op
      }
    }

    window.__poiSaveWatcher = ws
  })

  await headCard.getByRole('button', { name: 'Piano' }).click()
  await headCard.getByRole('button', { name: 'Piano' }).click({ modifiers: ['Shift'] })

  await expect
    .poll(async () =>
      page.evaluate(() =>
        window.__fixtureUpdateEvents.some((event) => {
          const fixtures = Array.isArray(event.fixtures) ? event.fixtures : []
          const head = fixtures.find((fixture) => fixture.id === 'head_el150')
          const target = head?.poi_targets?.piano
          return target?.pan === 30755 && target?.tilt === 5131
        })
      )
    )
    .toBeTruthy()

  await page.evaluate(() => {
    if (window.__poiSaveWatcher) {
      try {
        window.__poiSaveWatcher.close()
      } catch {
        // no-op
      }
    }
  })
})

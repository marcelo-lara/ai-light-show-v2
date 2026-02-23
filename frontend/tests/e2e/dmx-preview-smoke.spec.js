import { expect, test } from '@playwright/test'
import { installMockWebSocket } from './support/mock-websocket.js'

const dmxFixtures = [
  {
    id: 'parcan_l',
    name: 'ParCan L',
    type: 'rgb',
    channels: { red: 1, green: 2, blue: 3, dimmer: 4 },
  },
  {
    id: 'parcan_r',
    name: 'ParCan R',
    type: 'rgb',
    channels: { red: 11, green: 12, blue: 13, dimmer: 14 },
  },
  {
    id: 'wash_1',
    name: 'Wash 1',
    type: 'rgb',
    channels: { red: 21, green: 22, blue: 23, dimmer: 24 },
  },
  {
    id: 'wash_2',
    name: 'Wash 2',
    type: 'rgb',
    channels: { red: 31, green: 32, blue: 33, dimmer: 34 },
  },
  {
    id: 'bar_1',
    name: 'Bar 1',
    type: 'rgb',
    channels: { red: 41, green: 42, blue: 43, dimmer: 44 },
  },
  {
    id: 'bar_2',
    name: 'Bar 2',
    type: 'rgb',
    channels: { red: 51, green: 52, blue: 53, dimmer: 54 },
  },
  {
    id: 'head_el150',
    name: 'Head EL-150',
    type: 'moving_head',
    channels: {
      pan_msb: 61,
      pan_lsb: 62,
      tilt_msb: 63,
      tilt_lsb: 64,
      color: 65,
      gobo: 66,
      dimmer: 67,
      shutter: 68,
    },
    poi_targets: {
      piano: { pan: 30755, tilt: 5131 },
    },
  },
]

const dmxPois = [
  { id: 'audience_l', name: 'Audience L' },
  { id: 'audience_r', name: 'Audience R' },
  { id: 'backdrop', name: 'Backdrop' },
  { id: 'center', name: 'Center' },
  { id: 'crowd', name: 'Crowd' },
  { id: 'drums', name: 'Drums' },
  { id: 'floor', name: 'Floor' },
  { id: 'guitar', name: 'Guitar' },
  { id: 'keys', name: 'Keys' },
  { id: 'piano', name: 'Piano' },
  { id: 'riser', name: 'Riser' },
  { id: 'table', name: 'Table' },
  { id: 'vocal_l', name: 'Vocal L' },
  { id: 'vocal_r', name: 'Vocal R' },
]

test.beforeEach(async ({ page }) => {
  await installMockWebSocket(page, {
    initialState: {
      fixtures: dmxFixtures,
      pois: dmxPois,
      status: { isPlaying: false, previewActive: false, preview: null },
      song: {
        filename: 'E2E.mp3',
        metadata: { length: 180, parts: {} },
      },
    },
  })
})

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

  await page.evaluate(() => {
    window.__mockWsServer.broadcast({
      type: 'status',
      status: { isPlaying: true, previewActive: false, preview: null },
    })
  })

  await expect(previewButtons.first()).toBeDisabled()
  await expect(effectSelects.first()).toBeDisabled()
  await expect(page.locator('input[type="range"]').first()).toBeDisabled()

  await page.evaluate(() => {
    window.__mockWsServer.broadcast({
      type: 'status',
      status: { isPlaying: false, previewActive: false, preview: null },
    })
  })

  await expect(previewButtons.first()).toBeEnabled()
  await expect(effectSelects.first()).toBeEnabled()
})

test('dmx parcan_l flash preview triggers temporary preview lifecycle', async ({ page }) => {
  await page.goto('/dmx')

  await expect(page.getByRole('heading', { name: 'DMX Control' })).toBeVisible()

  const parcanLCard = page.locator('.dmxCard', {
    has: page.getByRole('heading', { name: 'ParCan L' }),
  })

  await expect(parcanLCard).toBeVisible()
  await parcanLCard.locator('.fxSelect').selectOption('flash')
  await parcanLCard.getByRole('button', { name: 'Preview' }).click()

  await expect
    .poll(async () => page.evaluate(() => window.__mockWsServer.serverMessages.some((event) => event.type === 'preview_status' && event.active === true)))
    .toBeTruthy()

  await expect
    .poll(async () => page.evaluate(() => window.__mockWsServer.serverMessages.some((event) => event.type === 'preview_status' && event.active === false)))
    .toBeTruthy()
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

  await headCard.getByRole('button', { name: 'Piano' }).click()
  await headCard.getByRole('button', { name: 'Piano' }).click({ modifiers: ['Shift'] })

  await expect
    .poll(async () =>
      page.evaluate(() =>
        window.__mockWsServer.getMessagesByType('save_poi_target').some((entry) => {
          const message = entry?.message || {}
          return (
            message.fixture_id === 'head_el150' &&
            message.poi_id === 'piano' &&
            message.pan === 30755 &&
            message.tilt === 5131
          )
        })
      )
    )
    .toBeTruthy()
})

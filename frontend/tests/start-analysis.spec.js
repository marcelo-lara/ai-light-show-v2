import { test, expect } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'
import { promises as fs } from 'fs'

const STATUS_TIMEOUT = 180_000

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')
const metadataDir = path.join(repoRoot, 'backend', 'metadata')

// Assumes the stack is already running at BASE_URL (default http://localhost:5000)
test('song analysis runs end-to-end and produces metadata', async ({ page }) => {
  // 1) Clear metadata directory to ensure fresh outputs (without removing the mount point)
  await fs.mkdir(metadataDir, { recursive: true })
  const existing = await fs.readdir(metadataDir)
  await Promise.all(
    existing.map((name) => fs.rm(path.join(metadataDir, name), { recursive: true, force: true }))
  )

  // 2) Load analysis page and start analysis
  await page.goto('/analysis')

  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  const startButton = page.getByRole('button', { name: /start analysis/i })
  await expect(startButton).toBeEnabled({ timeout: 30_000 })

  await startButton.click()

  const status = page.getByText(/Status:/i)
  await expect(status).toContainText(/Status:/i)

  // 3) Confirm analyzer steps reached a terminal success state
  await expect(status).toContainText(/SUBMITTED|PENDING|STARTED|PROGRESS|SUCCESS/i, {
    timeout: STATUS_TIMEOUT,
  })

  // Wait for completion (SUCCESS) and 100% progress when available
  await expect
    .poll(async () => (await status.textContent()) || '', {
      timeout: STATUS_TIMEOUT,
      intervals: [1_000, 2_000, 5_000],
    })
    .toMatch(/SUCCESS/i)

  const progressLine = page.getByText(/Progress:/i)
  if (await progressLine.count()) {
    await expect(progressLine).toContainText(/100%/, { timeout: STATUS_TIMEOUT })
  }

  // 4) Verify metadata files were generated
  await expect
    .poll(async () => (await fs.readdir(metadataDir)).length, {
      timeout: 10_000,
      message: 'Expected metadata files to be generated in backend/metadata',
    })
    .toBeGreaterThan(0)
})

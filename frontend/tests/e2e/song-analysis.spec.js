import { expect, test } from '@playwright/test'

test('song analysis renders beats/downbeats and current beat highlight', async ({ page }) => {
  await page.goto('/analysis')

  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()
  await expect(page.locator('.songAnalysisBeatCell').first()).toBeVisible()
  await expect(page.locator('.songAnalysisBeatCellDownbeat').first()).toBeVisible()
  await expect(page.locator('.songAnalysisBeatCellCurrent')).toHaveCount(1)
})

test('sections editor supports add, edit, and remove with backend sync', async ({ page }) => {
  await page.goto('/analysis')

  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  const sectionName = `e2e-section-${Date.now()}`
  const baseStart = await page.evaluate(() => {
    const endInputs = Array.from(document.querySelectorAll('.songAnalysisSectionRow .songAnalysisSectionInput:nth-child(3)'))
    const maxEnd = endInputs.reduce((acc, input) => {
      const value = Number(input.value)
      if (!Number.isFinite(value)) return acc
      return Math.max(acc, value)
    }, 0)
    return Math.ceil(maxEnd) + 5
  })
  const startValue = Number(baseStart)
  const endValue = Number(baseStart) + 4
  const editedEndValue = Number(baseStart) + 5
  const getRowIndexByName = async (name) =>
    page.evaluate((sectionNameArg) => {
      const rows = Array.from(document.querySelectorAll('.songAnalysisSectionRow'))
      return rows.findIndex((row) => {
        const input = row.querySelector('.songAnalysisSectionInput')
        return input && input.value === sectionNameArg
      })
    }, name)

  await page.getByRole('button', { name: 'Add Section' }).click()

  const rows = page.locator('.songAnalysisSectionRow')
  const newRow = rows.last()

  await newRow.locator('.songAnalysisSectionInput').nth(0).fill(sectionName)
  await newRow.locator('.songAnalysisSectionInput').nth(1).fill(`${startValue}.000`)
  await newRow.locator('.songAnalysisSectionInput').nth(2).fill(`${endValue}.000`)
  await page.getByRole('button', { name: 'Save Sections' }).click()

  await expect(page.getByRole('button', { name: 'Save Sections' })).toBeDisabled()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  await expect.poll(async () => getRowIndexByName(sectionName)).toBeGreaterThan(-1)
  const rowIndex = await getRowIndexByName(sectionName)
  const rowForName = page.locator('.songAnalysisSectionRow').nth(rowIndex)
  await expect(rowForName.locator('.songAnalysisSectionInput').nth(1)).toHaveValue(String(startValue))
  await expect(rowForName.locator('.songAnalysisSectionInput').nth(2)).toHaveValue(String(endValue))

  await rowForName.locator('.songAnalysisSectionInput').nth(2).fill(`${editedEndValue}.000`)
  await page.getByRole('button', { name: 'Save Sections' }).click()
  await expect(page.getByRole('button', { name: 'Save Sections' })).toBeDisabled()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  await expect.poll(async () => getRowIndexByName(sectionName)).toBeGreaterThan(-1)
  const editedRowIndex = await getRowIndexByName(sectionName)
  const editedRow = page.locator('.songAnalysisSectionRow').nth(editedRowIndex)
  await expect(editedRow.locator('.songAnalysisSectionInput').nth(2)).toHaveValue(String(editedEndValue))

  await editedRow.getByRole('button', { name: 'Delete' }).click()
  await page.getByRole('button', { name: 'Save Sections' }).click()
  await expect(page.getByRole('button', { name: 'Save Sections' })).toBeDisabled()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Song Analysis' })).toBeVisible()

  await expect.poll(async () => getRowIndexByName(sectionName)).toBe(-1)
})

import { defineConfig } from '@playwright/test'

const baseURL = process.env.BASE_URL || 'http://localhost:5000'

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: {
    timeout: 30_000,
  },
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
})

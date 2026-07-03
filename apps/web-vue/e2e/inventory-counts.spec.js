import { test, expect } from '@playwright/test'

test.describe('Inventory Counts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await page.evaluate(() => {
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
    })
    await page.fill('input[placeholder*="username" i]', 'testuser')
    await page.fill('input[placeholder*="password" i]', 'password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 })
  })

  test('page renders', async ({ page }) => {
    await page.goto('/#/inventory/counts')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('has add button', async ({ page }) => {
    await page.goto('/#/inventory/counts')
    await expect(page.getByRole('button', { name: /new count/i })).toBeVisible({ timeout: 15000 })
  })
})

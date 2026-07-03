import { test, expect } from '@playwright/test'

test.describe('Planning Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
    })
    await page.fill('input[placeholder*="username" i]', 'testuser')
    await page.fill('input[placeholder*="password" i]', 'password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('production plans page renders', async ({ page }) => {
    await page.goto('/#/planning')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('production plans page renders via direct URL', async ({ page }) => {
    await page.goto('/#/planning')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
  })

  test('production plans has add button and table structure', async ({ page }) => {
    await page.goto('/#/planning')
    await expect(page.getByRole('button', { name: /new plan/i })).toBeVisible({ timeout: 15000 })
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const showTable = await table.count() > 0
    const showEmpty = await empty.count() > 0
    if (showTable) {
      await expect(table.locator('thead th')).toHaveCount(7)
    }
    if (showEmpty) {
      await expect(empty.locator('.empty-icon')).toBeVisible()
    }
    expect(showTable || showEmpty).toBe(true)
  })
})

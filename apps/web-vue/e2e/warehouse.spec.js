import { test, expect } from '@playwright/test'

test.describe('Warehouse & Categories', () => {
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

  test('categories page renders', async ({ page }) => {
    await page.locator('[data-id="categories"]').click()
    await expect(page).toHaveURL(/\/categories/)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1500)

    const pageTitle = page.locator('.page-title').first()
    await expect(pageTitle).toBeVisible()

    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')

    // Must render at least one state
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('pick lists page renders', async ({ page }) => {
    await page.goto('/#/warehouse/pick-lists')
    await expect(page).toHaveURL(/\/pick-lists/)
    await page.waitForLoadState('networkidle')

    const pageTitle = page.locator('.page-title').first()
    await expect(pageTitle).toBeVisible()

    const skeleton = page.locator('.skeleton-table')
    const cards = page.locator('.pick-grid')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')

    expect(await skeleton.count() + await cards.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('home dashboard renders', async ({ page }) => {
    await page.locator('[data-id="home"]').click()
    await expect(page).toHaveURL(/\/$/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.app-shell')).toBeVisible()
  })
})

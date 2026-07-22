import { test, expect } from '@playwright/test'

test.describe('Warehouse & Inventory', () => {
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

  test('inventory page renders', async ({ page }) => {
    await page.goto('/inventory')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('warehouses page renders', async ({ page }) => {
    await page.goto('/warehouses')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('warehouses has add button', async ({ page }) => {
    await page.goto('/warehouses')
    await expect(page.getByRole('button', { name: /new warehouse/i })).toBeVisible({ timeout: 15000 })
  })

  test('stock movements page renders', async ({ page }) => {
    await page.goto('/stock-movements')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('stock movements has add button', async ({ page }) => {
    await page.goto('/stock-movements')
    await expect(page.getByRole('button', { name: /new movement/i })).toBeVisible({ timeout: 15000 })
  })

  test('categories page renders', async ({ page }) => {
    await page.goto('/categories')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('pick lists page renders', async ({ page }) => {
    await page.goto('/warehouse/pick-lists')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const card = page.locator('.pick-card')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await card.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('home dashboard renders', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const content = page.locator('.dashboard-grid, .dashboard-cards, .stat-card')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await content.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })
})

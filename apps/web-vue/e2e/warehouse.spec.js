import { test, expect } from '@playwright/test'

function sessionHash(token) {
  let hash = 0
  for (let i = 0; i < token.length; i++) {
    const ch = token.charCodeAt(i)
    hash = ((hash << 5) - hash) + ch
    hash |= 0
  }
  return Math.abs(hash).toString(36).substring(0, 8)
}

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
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/inventory')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('warehouses page renders', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/warehouses')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('warehouses has add button', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/warehouses')
    await expect(page.getByRole('button', { name: /new warehouse/i })).toBeVisible({ timeout: 15000 })
  })

  test('stock movements page renders', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/stock-movements')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('stock movements has add button', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/stock-movements')
    await expect(page.getByRole('button', { name: /new movement/i })).toBeVisible({ timeout: 15000 })
  })

  test('categories page renders', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/categories')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('pick lists page renders', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/warehouse/pick-lists')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const card = page.locator('.pick-card')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await card.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('home dashboard renders', async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    await page.goto('/' + sessionHash(token) + '/dashboard')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const content = page.locator('.dashboard-grid, .dashboard-cards, .stat-card')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await content.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })
})

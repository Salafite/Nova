import { test, expect } from '@playwright/test'

test.describe('Purchasing Module', () => {
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

  test('purchasing overview page renders', async ({ page }) => {
    await page.goto('/#/purchasing')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
  })

  test('purchasing page has navigation cards', async ({ page }) => {
    await page.goto('/#/purchasing')
    await expect(page.locator('.nav-card').first()).toBeVisible({ timeout: 15000 })
  })

  test('purchase requisitions page renders', async ({ page }) => {
    await page.goto('/#/purchasing/requisitions')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('purchase requisitions has add button', async ({ page }) => {
    await page.goto('/#/purchasing/requisitions')
    await expect(page.getByRole('button', { name: /new requisition/i })).toBeVisible({ timeout: 15000 })
  })

  test('RFQ page renders', async ({ page }) => {
    await page.goto('/#/purchasing/rfqs')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('RFQ page has new RFQ button', async ({ page }) => {
    await page.goto('/#/purchasing/rfqs')
    await expect(page.getByRole('button', { name: /new rfq/i })).toBeVisible({ timeout: 15000 })
  })

  test('purchase returns page renders', async ({ page }) => {
    await page.goto('/#/purchasing/returns')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('purchase returns has new return button', async ({ page }) => {
    await page.goto('/#/purchasing/returns')
    await expect(page.getByRole('button', { name: /new return/i })).toBeVisible({ timeout: 15000 })
  })
})

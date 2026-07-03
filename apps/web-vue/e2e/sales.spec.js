import { test, expect } from '@playwright/test'

test.describe('Sales Module', () => {
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

  test('sales orders page renders', async ({ page }) => {
    await page.goto('/#/sales')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('sales orders has add button', async ({ page }) => {
    await page.goto('/#/sales')
    await expect(page.getByRole('button', { name: /new sales order/i })).toBeVisible({ timeout: 15000 })
  })

  test('quotations page renders', async ({ page }) => {
    await page.goto('/#/sales/quotations')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('quotations has add button', async ({ page }) => {
    await page.goto('/#/sales/quotations')
    await expect(page.getByRole('button', { name: /new quotation/i })).toBeVisible({ timeout: 15000 })
  })

  test('deliveries page renders', async ({ page }) => {
    await page.goto('/#/sales/deliveries')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('deliveries has add button', async ({ page }) => {
    await page.goto('/#/sales/deliveries')
    await expect(page.getByRole('button', { name: /new delivery/i })).toBeVisible({ timeout: 15000 })
  })

  test('sales returns page renders', async ({ page }) => {
    await page.goto('/#/sales/returns')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('sales returns has add button', async ({ page }) => {
    await page.goto('/#/sales/returns')
    await expect(page.getByRole('button', { name: /new return/i })).toBeVisible({ timeout: 15000 })
  })

  test('price lists page renders', async ({ page }) => {
    await page.goto('/#/sales/price-lists')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('price lists has add button', async ({ page }) => {
    await page.goto('/#/sales/price-lists')
    await expect(page.getByRole('button', { name: /new price list/i })).toBeVisible({ timeout: 15000 })
  })

  test('tax rates page renders', async ({ page }) => {
    await page.goto('/#/sales/tax-rates')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('tax rates has add button', async ({ page }) => {
    await page.goto('/#/sales/tax-rates')
    await expect(page.getByRole('button', { name: /new tax rate/i })).toBeVisible({ timeout: 15000 })
  })
})

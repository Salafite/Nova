import { test, expect } from '@playwright/test'

test.describe('Finance Module', () => {
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

  test('invoices page renders', async ({ page }) => {
    await page.goto('/#/finance')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('invoices has add button', async ({ page }) => {
    await page.goto('/#/finance')
    await expect(page.getByRole('button', { name: /new invoice/i })).toBeVisible({ timeout: 15000 })
  })

  test('chart of accounts page renders', async ({ page }) => {
    await page.goto('/#/chart-of-accounts')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('chart of accounts has add button', async ({ page }) => {
    await page.goto('/#/chart-of-accounts')
    await expect(page.getByRole('button', { name: /new account/i })).toBeVisible({ timeout: 15000 })
  })

  test('journal entries page renders', async ({ page }) => {
    await page.goto('/#/journal-entries')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('journal entries has add button', async ({ page }) => {
    await page.goto('/#/journal-entries')
    await expect(page.getByRole('button', { name: /new journal entry/i })).toBeVisible({ timeout: 15000 })
  })

  test('payments page renders', async ({ page }) => {
    await page.goto('/#/payments')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('payments has add button', async ({ page }) => {
    await page.goto('/#/payments')
    await expect(page.getByRole('button', { name: /new payment/i })).toBeVisible({ timeout: 15000 })
  })

  test('payment terms page renders', async ({ page }) => {
    await page.goto('/#/payment-terms')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('payment terms has add button', async ({ page }) => {
    await page.goto('/#/payment-terms')
    await expect(page.getByRole('button', { name: /new payment term/i })).toBeVisible({ timeout: 15000 })
  })

  test('payment methods page renders', async ({ page }) => {
    await page.goto('/#/payment-methods')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('payment methods has add button', async ({ page }) => {
    await page.goto('/#/payment-methods')
    await expect(page.getByRole('button', { name: /new payment method/i })).toBeVisible({ timeout: 15000 })
  })
})

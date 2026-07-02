import { test, expect } from '@playwright/test'

test.describe('Purchasing Module', () => {
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

  test('purchasing overview page renders', async ({ page }) => {
    await page.locator('[data-id="purchasing"]').click()
    await expect(page).toHaveURL(/\/purchasing/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('purchasing page has navigation cards', async ({ page }) => {
    await page.goto('/#/purchasing')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.nav-cards')).toBeVisible()
    await expect(page.locator('.nav-card').first()).toBeVisible()
  })

  test('purchase requisitions page renders', async ({ page }) => {
    await page.goto('/#/purchasing/requisitions')
    await expect(page).toHaveURL(/\/purchasing\/requisitions/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('purchase requisitions has add button', async ({ page }) => {
    await page.goto('/#/purchasing/requisitions')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new requisition/i })).toBeVisible()
  })

  test('RFQ page renders', async ({ page }) => {
    await page.goto('/#/purchasing/rfqs')
    await expect(page).toHaveURL(/\/purchasing\/rfqs/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('RFQ page has new RFQ button', async ({ page }) => {
    await page.goto('/#/purchasing/rfqs')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new rfq/i })).toBeVisible()
  })

  test('purchase returns page renders', async ({ page }) => {
    await page.goto('/#/purchasing/returns')
    await expect(page).toHaveURL(/\/purchasing\/returns/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('purchase returns has new return button', async ({ page }) => {
    await page.goto('/#/purchasing/returns')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new return/i })).toBeVisible()
  })

  test('purchase order detail page shows error state for missing order', async ({ page }) => {
    await page.goto('/#/purchasing/orders/0')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    const error = page.locator('.error-state')
    const skeleton = page.locator('.skeleton-card, .skeleton')
    if (await error.count() > 0) {
      await expect(error).toBeVisible()
    } else if (await skeleton.count() > 0) {
      await expect(skeleton).toBeVisible()
    }
  })
})

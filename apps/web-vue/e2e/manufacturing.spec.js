import { test, expect } from '@playwright/test'

test.describe('Manufacturing Module', () => {
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

  test('bill of materials page renders', async ({ page }) => {
    await page.locator('[data-id="mfg-bom"]').click()
    await expect(page).toHaveURL(/\/manufacturing\/bom/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('BOM has new BOM button', async ({ page }) => {
    await page.goto('/#/manufacturing/bom')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new bom/i })).toBeVisible()
  })

  test('manufacturing orders page renders', async ({ page }) => {
    await page.locator('[data-id="mfg-orders"]').click()
    await expect(page).toHaveURL(/\/manufacturing\/orders/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('manufacturing orders has new order button', async ({ page }) => {
    await page.goto('/#/manufacturing/orders')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new manufacturing order/i })).toBeVisible()
  })

  test('QC inspection page renders', async ({ page }) => {
    await page.locator('[data-id="mfg-qc"]').click()
    await expect(page).toHaveURL(/\/manufacturing\/qc/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('QC inspection has new inspection button', async ({ page }) => {
    await page.goto('/#/manufacturing/qc')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new qc inspection/i })).toBeVisible()
  })
})

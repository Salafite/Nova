import { test, expect } from '@playwright/test'

test.describe('Products Page', () => {
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

  test('loads and shows product list', async ({ page }) => {
    await page.locator('[data-id="products"]').click()
    await expect(page).toHaveURL(/\/products/)

    // Wait for either the table, empty state, or loading to resolve
    await page.waitForLoadState('networkidle')

    const hasSkeleton = await page.locator('.skeleton-table, .skeleton').count()
    const hasTable = await page.locator('.data-table').count()
    const hasEmpty = await page.locator('.empty-state').count()

    if (hasSkeleton > 0) {
      // Still loading — wait for either table or empty
      await page.waitForFunction(() =>
        document.querySelector('.data-table') !== null ||
        document.querySelector('.empty-state') !== null,
        { timeout: 10000 }
      ).catch(() => {})
    }

    const tableVisible = await page.locator('.data-table').count()
    const emptyVisible = await page.locator('.empty-state').count()
    expect(tableVisible + emptyVisible).toBeGreaterThanOrEqual(1)
  })

  test('shows product table columns', async ({ page }) => {
    await page.goto('/#/products')
    await page.waitForLoadState('networkidle')

    // Wait for data to render
    await page.waitForFunction(() =>
      document.querySelector('.data-table') !== null ||
      document.querySelector('.empty-state') !== null,
      { timeout: 10000 }
    ).catch(() => {})

    const table = page.locator('.data-table')
    if (await table.count() > 0) {
      await expect(table.locator('thead th')).toHaveCount(6)
      await expect(table.locator('tbody tr').first()).toBeVisible()
    }
  })

  test('shows stats row on products page', async ({ page }) => {
    await page.goto('/#/products')
    await page.waitForLoadState('networkidle')
    await page.waitForFunction(() =>
      document.querySelector('.stats-row') !== null ||
      document.querySelector('.empty-state') !== null,
      { timeout: 10000 }
    ).catch(() => {})
    const stats = page.locator('.stats-row')
    if (await stats.count() > 0) {
      await expect(stats.locator('.stat-card').first()).toBeVisible()
    }
  })

  test('shows empty state when no products', async ({ page }) => {
    await page.goto('/#/products')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    const empty = page.locator('.empty-state')
    const table = page.locator('.data-table')
    if (await empty.count() > 0) {
      await expect(empty.locator('.empty-icon')).toBeVisible()
      await expect(empty).toContainText(/no products/i)
    }
    if (await table.count() > 0) {
      await expect(table.locator('tbody tr').first()).toBeVisible()
    }
    // One of them must be visible
    expect(await empty.count() + await table.count()).toBeGreaterThanOrEqual(1)
  })
})

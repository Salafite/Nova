import { test, expect } from '@playwright/test'

test.describe('BI & Reporting Module', () => {
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

  test('KPI management page renders', async ({ page }) => {
    await page.goto('/#/bi/kpis')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state-card')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('KPI management has add button', async ({ page }) => {
    await page.goto('/#/bi/kpis')
    await expect(page.getByRole('button', { name: /new kpi|add kpi/i })).toBeVisible({ timeout: 15000 })
  })

  test('dashboard builder page renders', async ({ page }) => {
    await page.goto('/#/bi/dashboards')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 15000 })
    const loading = page.locator('.loading-state, .skeleton-table')
    const content = page.locator('.dash-list, .widget-grid, .sidebar-list')
    const empty = page.locator('.empty-state, .empty-section')
    const error = page.locator('.error-state-card')
    expect(await loading.count() + await content.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('dashboard builder has add button', async ({ page }) => {
    await page.goto('/#/bi/dashboards')
    await expect(page.getByRole('button', { name: /new dashboard/i })).toBeVisible({ timeout: 15000 })
  })

  test('report builder page renders', async ({ page }) => {
    await page.goto('/#/bi/reports')
    await expect(page.locator('.page-title').first()).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.report-layout')).toBeVisible({ timeout: 10000 })
  })
})

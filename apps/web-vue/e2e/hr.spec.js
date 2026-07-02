import { test, expect } from '@playwright/test'

test.describe('HR Module', () => {
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

  test('departments page renders', async ({ page }) => {
    await page.locator('[data-id="departments"]').click()
    await expect(page).toHaveURL(/\/departments/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('departments has add button', async ({ page }) => {
    await page.goto('/#/departments')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new department/i })).toBeVisible()
  })

  test('designations page renders', async ({ page }) => {
    await page.locator('[data-id="designations"]').click()
    await expect(page).toHaveURL(/\/designations/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('designations has add button', async ({ page }) => {
    await page.goto('/#/designations')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new designation/i })).toBeVisible()
  })

  test('employees page renders', async ({ page }) => {
    await page.locator('[data-id="employees"]').click()
    await expect(page).toHaveURL(/\/employees/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('employees has add button', async ({ page }) => {
    await page.goto('/#/employees')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new employee/i })).toBeVisible()
  })

  test('attendance page renders', async ({ page }) => {
    await page.locator('[data-id="hr-attendance"]').click()
    await expect(page).toHaveURL(/\/hr\/attendance/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('leave requests page renders', async ({ page }) => {
    await page.locator('[data-id="hr-leaves"]').click()
    await expect(page).toHaveURL(/\/hr\/leaves/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('payroll page renders', async ({ page }) => {
    await page.locator('[data-id="hr-payroll"]').click()
    await expect(page).toHaveURL(/\/hr\/payroll/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('payroll has add button', async ({ page }) => {
    await page.goto('/#/hr/payroll')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /new payroll/i })).toBeVisible()
  })

  test('job openings page renders', async ({ page }) => {
    await page.locator('[data-id="hr-jobs"]').click()
    await expect(page).toHaveURL(/\/hr\/jobs/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })

  test('candidates page renders', async ({ page }) => {
    await page.locator('[data-id="hr-candidates"]').click()
    await expect(page).toHaveURL(/\/hr\/candidates/)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.page-title').first()).toBeVisible()
    const skeleton = page.locator('.skeleton-table')
    const table = page.locator('.data-table')
    const empty = page.locator('.empty-state')
    const error = page.locator('.error-state')
    expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
      .toBeGreaterThanOrEqual(1)
  })
})

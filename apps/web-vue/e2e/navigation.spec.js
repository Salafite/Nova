import { test, expect } from '@playwright/test'

test.describe('Sidebar Navigation', () => {
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

  test('sidebar nav items are visible', async ({ page }) => {
    await expect(page.locator('.sidebar')).toBeVisible()
    await expect(page.locator('[data-id="products"]')).toBeVisible()
    await expect(page.locator('[data-id="customers"]')).toBeVisible()
    await expect(page.locator('[data-id="suppliers"]')).toBeVisible()
    await expect(page.locator('[data-id="pick-lists"]')).toBeVisible()
  })

  test('navigates to products page', async ({ page }) => {
    await page.locator('[data-id="products"]').click()
    await expect(page).toHaveURL(/\/products/)
    await expect(page.locator('.page-title').first()).toContainText(/products/i)
  })

  test('navigates to customers page', async ({ page }) => {
    await page.locator('[data-id="customers"]').click()
    await expect(page).toHaveURL(/\/customers/)
    await expect(page.locator('.page-title').first()).toBeVisible()
  })

  test('navigates to suppliers page', async ({ page }) => {
    await page.locator('[data-id="suppliers"]').click()
    await expect(page).toHaveURL(/\/suppliers/)
    await expect(page.locator('.page-title').first()).toContainText(/suppliers/i)
  })

  test('navigates to categories page', async ({ page }) => {
    await page.locator('[data-id="categories"]').click()
    await expect(page).toHaveURL(/\/categories/)
    await expect(page.locator('.page-title').first()).toBeVisible()
  })

  test('navigates to pick lists page', async ({ page }) => {
    await page.goto('/#/warehouse/pick-lists')
    await expect(page).toHaveURL(/\/pick-lists/)
    await expect(page.locator('.page-title').first()).toContainText(/pick-?lists/i)
  })
})

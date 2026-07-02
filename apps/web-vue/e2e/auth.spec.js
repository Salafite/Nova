import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
    })
  })

  test('redirects to login when unauthenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })

  test('redirects to login from any protected route', async ({ page }) => {
    await page.goto('/#/products')
    await expect(page).toHaveURL(/\/login/)
    await page.goto('/#/customers')
    await expect(page).toHaveURL(/\/login/)
  })

  test('shows login form elements', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.login-card')).toBeVisible()
    await expect(page.locator('input[placeholder*="username" i]')).toBeVisible()
    await expect(page.locator('input[placeholder*="password" i]')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/')
    await page.fill('input[placeholder*="username" i]', 'wronguser')
    await page.fill('input[placeholder*="password" i]', 'wrongpass')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.locator('.alert.error')).toBeVisible()
  })

  test('logs in with valid credentials and redirects to home', async ({ page }) => {
    await page.goto('/')
    await page.fill('input[placeholder*="username" i]', 'testuser')
    await page.fill('input[placeholder*="password" i]', 'password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).not.toHaveURL(/\/login/)
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    expect(token).toBeTruthy()
  })

  test('persists session after page reload', async ({ page }) => {
    await page.goto('/')
    await page.fill('input[placeholder*="username" i]', 'testuser')
    await page.fill('input[placeholder*="password" i]', 'password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).not.toHaveURL(/\/login/)
    await page.reload()
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('logs out and redirects to login', async ({ page }) => {
    await page.goto('/')
    await page.fill('input[placeholder*="username" i]', 'testuser')
    await page.fill('input[placeholder*="password" i]', 'password123')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).not.toHaveURL(/\/login/)
    await page.getByRole('button', { name: /log\s*out/i }).click()
    await expect(page).toHaveURL(/\/login/)
    const token = await page.evaluate(() => localStorage.getItem('nova_token'))
    expect(token).toBeFalsy()
  })
})

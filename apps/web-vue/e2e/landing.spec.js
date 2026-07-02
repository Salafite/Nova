import { test, expect } from '@playwright/test'

test.describe('Landing Page', () => {
  test('loads without authentication', async ({ page }) => {
    await page.goto('/#/landing')
    await expect(page).toHaveURL(/\/landing/)
  })
})

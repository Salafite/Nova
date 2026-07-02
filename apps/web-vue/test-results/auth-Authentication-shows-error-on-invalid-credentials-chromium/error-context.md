# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.js >> Authentication >> shows error on invalid credentials
- Location: e2e\auth.spec.js:32:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.fill: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('input[placeholder*="username" i]')

```

# Page snapshot

```yaml
- main [ref=e2]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - img [ref=e5]
      - heading "Application failed to respond" [level=1] [ref=e8]
    - generic [ref=e9]:
      - paragraph [ref=e10]: This error appears to be caused by the application.
      - paragraph [ref=e11]:
        - text: If this is your project, check out your
        - link "deploy logs" [ref=e12] [cursor=pointer]:
          - /url: https://docs.railway.com/guides/logs
        - text: to see what went wrong. Refer to our
        - link "docs on Fixing Common Errors" [ref=e13] [cursor=pointer]:
          - /url: https://docs.railway.com/guides/fixing-common-errors
        - text: for help, or reach out over our
        - link "Help Station" [ref=e14] [cursor=pointer]:
          - /url: https://station.railway.com
        - text: .
      - paragraph [ref=e15]: If you are a visitor, please contact the application owner or try again later.
      - paragraph [ref=e17]:
        - text: "Request ID:"
        - text: 8kn8CJe5TVSP2j_enpoFkQ
      - link "Go to Railway" [ref=e19] [cursor=pointer]:
        - /url: https://railway.com
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Authentication', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/')
  6  |     await page.evaluate(() => {
  7  |       localStorage.removeItem('nova_token')
  8  |       localStorage.removeItem('nova_user')
  9  |     })
  10 |   })
  11 | 
  12 |   test('redirects to login when unauthenticated', async ({ page }) => {
  13 |     await page.goto('/')
  14 |     await expect(page).toHaveURL(/\/login/)
  15 |   })
  16 | 
  17 |   test('redirects to login from any protected route', async ({ page }) => {
  18 |     await page.goto('/#/products')
  19 |     await expect(page).toHaveURL(/\/login/)
  20 |     await page.goto('/#/customers')
  21 |     await expect(page).toHaveURL(/\/login/)
  22 |   })
  23 | 
  24 |   test('shows login form elements', async ({ page }) => {
  25 |     await page.goto('/')
  26 |     await expect(page.locator('.login-card')).toBeVisible()
  27 |     await expect(page.locator('input[placeholder*="username" i]')).toBeVisible()
  28 |     await expect(page.locator('input[placeholder*="password" i]')).toBeVisible()
  29 |     await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  30 |   })
  31 | 
  32 |   test('shows error on invalid credentials', async ({ page }) => {
  33 |     await page.goto('/')
> 34 |     await page.fill('input[placeholder*="username" i]', 'wronguser')
     |                ^ Error: page.fill: Test timeout of 30000ms exceeded.
  35 |     await page.fill('input[placeholder*="password" i]', 'wrongpass')
  36 |     await page.getByRole('button', { name: /sign in/i }).click()
  37 |     await expect(page.locator('.alert.error')).toBeVisible()
  38 |   })
  39 | 
  40 |   test('logs in with valid credentials and redirects to home', async ({ page }) => {
  41 |     await page.goto('/')
  42 |     await page.fill('input[placeholder*="username" i]', 'testuser')
  43 |     await page.fill('input[placeholder*="password" i]', 'password123')
  44 |     await page.getByRole('button', { name: /sign in/i }).click()
  45 |     await expect(page).not.toHaveURL(/\/login/)
  46 |     const token = await page.evaluate(() => localStorage.getItem('nova_token'))
  47 |     expect(token).toBeTruthy()
  48 |   })
  49 | 
  50 |   test('persists session after page reload', async ({ page }) => {
  51 |     await page.goto('/')
  52 |     await page.fill('input[placeholder*="username" i]', 'testuser')
  53 |     await page.fill('input[placeholder*="password" i]', 'password123')
  54 |     await page.getByRole('button', { name: /sign in/i }).click()
  55 |     await expect(page).not.toHaveURL(/\/login/)
  56 |     await page.reload()
  57 |     await expect(page).not.toHaveURL(/\/login/)
  58 |   })
  59 | 
  60 |   test('logs out and redirects to login', async ({ page }) => {
  61 |     await page.goto('/')
  62 |     await page.fill('input[placeholder*="username" i]', 'testuser')
  63 |     await page.fill('input[placeholder*="password" i]', 'password123')
  64 |     await page.getByRole('button', { name: /sign in/i }).click()
  65 |     await expect(page).not.toHaveURL(/\/login/)
  66 |     await page.getByRole('button', { name: /log\s*out/i }).click()
  67 |     await expect(page).toHaveURL(/\/login/)
  68 |     const token = await page.evaluate(() => localStorage.getItem('nova_token'))
  69 |     expect(token).toBeFalsy()
  70 |   })
  71 | })
  72 | 
```
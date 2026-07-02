# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: hr.spec.js >> HR Module >> employees page renders
- Location: e2e\hr.spec.js:54:3

# Error details

```
Error: expect(page).not.toHaveURL(expected) failed

Expected pattern: not /\/login/
Received string: "http://localhost:5173/#/login"
Timeout: 10000ms

Call log:
  - Expect "not toHaveURL" with timeout 10000ms
    24 × unexpected value "http://localhost:5173/#/login"

```

```yaml
- text: Nova ERP
- paragraph: Sign in to your account
- text: Invalid username or password
- textbox "Username": testuser
- textbox "Password": password123
- button "Sign In"
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | 
  3   | test.describe('HR Module', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/')
  6   |     await page.evaluate(() => {
  7   |       localStorage.removeItem('nova_token')
  8   |       localStorage.removeItem('nova_user')
  9   |     })
  10  |     await page.fill('input[placeholder*="username" i]', 'testuser')
  11  |     await page.fill('input[placeholder*="password" i]', 'password123')
  12  |     await page.getByRole('button', { name: /sign in/i }).click()
> 13  |     await expect(page).not.toHaveURL(/\/login/)
      |                            ^ Error: expect(page).not.toHaveURL(expected) failed
  14  |   })
  15  | 
  16  |   test('departments page renders', async ({ page }) => {
  17  |     await page.locator('[data-id="departments"]').click()
  18  |     await expect(page).toHaveURL(/\/departments/)
  19  |     await page.waitForLoadState('networkidle')
  20  |     await expect(page.locator('.page-title').first()).toBeVisible()
  21  |     const skeleton = page.locator('.skeleton-table')
  22  |     const table = page.locator('.data-table')
  23  |     const empty = page.locator('.empty-state')
  24  |     const error = page.locator('.error-state')
  25  |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  26  |       .toBeGreaterThanOrEqual(1)
  27  |   })
  28  | 
  29  |   test('departments has add button', async ({ page }) => {
  30  |     await page.goto('/#/departments')
  31  |     await page.waitForLoadState('networkidle')
  32  |     await expect(page.getByRole('button', { name: /new department/i })).toBeVisible()
  33  |   })
  34  | 
  35  |   test('designations page renders', async ({ page }) => {
  36  |     await page.locator('[data-id="designations"]').click()
  37  |     await expect(page).toHaveURL(/\/designations/)
  38  |     await page.waitForLoadState('networkidle')
  39  |     await expect(page.locator('.page-title').first()).toBeVisible()
  40  |     const skeleton = page.locator('.skeleton-table')
  41  |     const table = page.locator('.data-table')
  42  |     const empty = page.locator('.empty-state')
  43  |     const error = page.locator('.error-state')
  44  |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  45  |       .toBeGreaterThanOrEqual(1)
  46  |   })
  47  | 
  48  |   test('designations has add button', async ({ page }) => {
  49  |     await page.goto('/#/designations')
  50  |     await page.waitForLoadState('networkidle')
  51  |     await expect(page.getByRole('button', { name: /new designation/i })).toBeVisible()
  52  |   })
  53  | 
  54  |   test('employees page renders', async ({ page }) => {
  55  |     await page.locator('[data-id="employees"]').click()
  56  |     await expect(page).toHaveURL(/\/employees/)
  57  |     await page.waitForLoadState('networkidle')
  58  |     await expect(page.locator('.page-title').first()).toBeVisible()
  59  |     const skeleton = page.locator('.skeleton-table')
  60  |     const table = page.locator('.data-table')
  61  |     const empty = page.locator('.empty-state')
  62  |     const error = page.locator('.error-state')
  63  |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  64  |       .toBeGreaterThanOrEqual(1)
  65  |   })
  66  | 
  67  |   test('employees has add button', async ({ page }) => {
  68  |     await page.goto('/#/employees')
  69  |     await page.waitForLoadState('networkidle')
  70  |     await expect(page.getByRole('button', { name: /new employee/i })).toBeVisible()
  71  |   })
  72  | 
  73  |   test('attendance page renders', async ({ page }) => {
  74  |     await page.locator('[data-id="hr-attendance"]').click()
  75  |     await expect(page).toHaveURL(/\/hr\/attendance/)
  76  |     await page.waitForLoadState('networkidle')
  77  |     await expect(page.locator('.page-title').first()).toBeVisible()
  78  |     const skeleton = page.locator('.skeleton-table')
  79  |     const table = page.locator('.data-table')
  80  |     const empty = page.locator('.empty-state')
  81  |     const error = page.locator('.error-state')
  82  |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  83  |       .toBeGreaterThanOrEqual(1)
  84  |   })
  85  | 
  86  |   test('leave requests page renders', async ({ page }) => {
  87  |     await page.locator('[data-id="hr-leaves"]').click()
  88  |     await expect(page).toHaveURL(/\/hr\/leaves/)
  89  |     await page.waitForLoadState('networkidle')
  90  |     await expect(page.locator('.page-title').first()).toBeVisible()
  91  |     const skeleton = page.locator('.skeleton-table')
  92  |     const table = page.locator('.data-table')
  93  |     const empty = page.locator('.empty-state')
  94  |     const error = page.locator('.error-state')
  95  |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  96  |       .toBeGreaterThanOrEqual(1)
  97  |   })
  98  | 
  99  |   test('payroll page renders', async ({ page }) => {
  100 |     await page.locator('[data-id="hr-payroll"]').click()
  101 |     await expect(page).toHaveURL(/\/hr\/payroll/)
  102 |     await page.waitForLoadState('networkidle')
  103 |     await expect(page.locator('.page-title').first()).toBeVisible()
  104 |     const skeleton = page.locator('.skeleton-table')
  105 |     const table = page.locator('.data-table')
  106 |     const empty = page.locator('.empty-state')
  107 |     const error = page.locator('.error-state')
  108 |     expect(await skeleton.count() + await table.count() + await empty.count() + await error.count())
  109 |       .toBeGreaterThanOrEqual(1)
  110 |   })
  111 | 
  112 |   test('payroll has add button', async ({ page }) => {
  113 |     await page.goto('/#/hr/payroll')
```
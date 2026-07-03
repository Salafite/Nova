# Nova ERP Launch Checklist

- **Product**: Nova ERP — a full-featured Enterprise Resource Planning (ERP) web application
- **Tech stack**: Vue 3 + Vite frontend, Python FastAPI backend, PostgreSQL 16, hosted on Railway
- **Current status**: App is live at `https://nova-production-2e9d.up.railway.app` (Railway, auto-deploys from GitHub master)
- **Estimated monthly cost**: ~$50–120 (PostgreSQL hosting + VPS + optional services)

**Legend:**
- 🧑 **You** — requires your identity, accounts, payment details, or a decision. An agent can't do this for you.
- 🤖 **Agent** — pasting the given prompt into your coding agent will let it do this in the codebase or via command line.
- 🤝 **Together** — the agent prepares it, you click the final button or paste in a value.
- ✅ **Done** — already completed.

## Phase 1: Accounts & Prerequisites (⏱ 30 min)

### 1.1 Create accounts for production services

🧑 **You** — sign up for these services. Pick the free or cheapest tier — you can upgrade later.

| Service | Purpose | Approx. cost/month | Sign-up link |
|---|---|---|---|
| ✅ **Railway.app** | Hosting (Docker-based deploys) | $5–20 | https://railway.app |
| ✅ **Neon.tech** (via Railway) | PostgreSQL 16 database | Included with Railway | https://neon.tech |
| **Stripe** | Payment processing (only if billing enabled) | 2.9% + $0.30/transaction | https://stripe.com |
| **Sentry** | Error tracking (find crashes) | Free (5k events/month) | https://sentry.io |
| **Resend** | Transactional email (password reset, invoices) | Free (100 emails/day) | https://resend.com |
| **PostHog** | Product analytics (see what users do) | Free (1m events/month) | https://posthog.com |
| **Namecheap** or **Cloudflare** | Domain name (e.g., novaerp.com) | $10–15/year | https://namecheap.com |
| **Cloudflare** | DNS, CDN, DDoS protection | Free | https://cloudflare.com |

After each sign-up, save the dashboard URL and any API keys — you'll need them in Phase 2.

**You'll know it worked when:** You can log into each service dashboard.

---

## Phase 2: Secrets & Configuration (⏱ 30 min)

### 2.1 Generate production secrets

🧑 **You** — create a strong random secret for JWT signing and a strong database password.

> Generate a 64-character random string for `SECRET_KEY`:
> ```powershell
> -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
> ```
> Save this somewhere safe (like a password manager). Generate a different 32-character string for the DB password.

**You'll know it worked when:** You have long random strings saved.

### 2.2 Set environment variables on the hosting platform

🤝 **Together** — in Railway dashboard, find your project → Variables tab, and set each of these:

| Variable | What to put | Required? |
|---|---|---|
| `DB_HOST` | Database host URL (from Neon dashboard) | ✅ Yes |
| `DB_PORT` | `5432` | ✅ Yes |
| `DB_NAME` | Database name | ✅ Yes |
| `DB_USER` | Database username | ✅ Yes |
| `DB_PASSWORD` | The strong password from step 2.1 | ✅ Yes |
| `DB_SCHEMA` | `Nova` | ✅ Yes |
| `SECRET_KEY` | The 64-char random string from step 2.1 | ✅ Yes |
| `NOVA_ENV` | `production` | ✅ Yes |
| `ALLOWED_ORIGINS` | Your domain, e.g., `https://novaerp.com` | ✅ Yes |
| `APP_URL` | Your domain, e.g., `https://novaerp.com` | ✅ Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | No |
| `STRIPE_SECRET_KEY` | Stripe live secret (`sk_live_...`) | If billing |
| `STRIPE_PRICE_ID` | Your Stripe price ID | If billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | If billing |
| `POSTHOG_API_KEY` | PostHog project API key | If analytics |
| `SENTRY_DSN` | Sentry DSN URL | If monitoring |
| `RELEASE_VERSION` | `1.0.0` | No |
| `RESEND_API_KEY` | Resend API key | If email |
| `RESEND_FROM_EMAIL` | `noreply@yourdomain.com` | If email |

> **Note:** Railway uses `DB_*` variables (not `DATABASE_URL`). If using Neon standalone (outside Railway), the DB connector auto-detects Railway Neon's internal connection.

**Never paste secrets into chat or commit them to code.** They go directly into the hosting platform's settings panel.

**You'll know it worked when:** The app starts without "missing environment variable" errors.

---

## Phase 3: Production Services (⏱ 1 hour)

### 3.1 Set up the production database

🤝 **Together** — create your database. Railway projects come with a Neon Postgres plugin:
1. In Railway dashboard → New → Database → PostgreSQL (powered by Neon)
2. Railway auto-creates the DB and sets `DB_*` env vars
3. Copy the connection details from Railway's Variables tab if you need them externally

If using standalone Neon: create a project, copy the connection string, and set the `DB_*` vars manually.

**You'll know it worked when:** Railway shows the database as "Running" with green health.

### 3.2 Run database migrations

✅ **Done** — migrations run automatically at startup via `scripts/docker-entrypoint.sh` which calls `scripts/run_migration.py`. There are currently **13 migration files** (`database/migrations/001_*.sql` through `013_*.sql`). Each migration is tracked in the `"Nova"._migrations` table and only applied once.

🤖 **Agent** — to run migrations manually against a given database:
```bash
python scripts/run_migration.py
```

**You'll know it worked when:** The script reports "OK" for all 13 migration files.

### 3.3 Create admin user

🧑 **You** — after the app is deployed, visit your app's URL, go through signup, and verify you can log in as the first user.

> Use the API directly:
> ```bash
> curl -X POST https://yourdomain.com/api/auth/signup \
>   -H "Content-Type: application/json" \
>   -d '{"email":"admin@yourcompany.com","password":"a-strong-password","full_name":"Admin"}'
> ```

**You'll know it worked when:** You can log into the app with that email and password.

### 3.4 Configure Stripe webhooks (only if billing is enabled)

🤝 **Together** — in Stripe Dashboard → Developers → Webhooks → Add endpoint:
- Endpoint URL: `https://yourdomain.com/api/billing/webhook`
- Events: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`
- Copy the webhook signing secret → set as `STRIPE_WEBHOOK_SECRET`

**You'll know it worked when:** Stripe shows the endpoint as "Enabled" with a 200 status.

### 3.5 Verify Resend email delivery (only if email is enabled)

🤝 **Together** — in Resend dashboard, add and verify your sending domain. Add the DNS TXT records at your domain registrar.

**You'll know it worked when:** Resend shows your domain as "Verified".

### 3.6 Seed initial data

🧑 **You** — the app starts empty. You'll need to add core setup data manually:
1. Create UOM (Units of Measure) — e.g., "Each", "Kg", "Hour"
2. Create at least one warehouse
3. Create Chart of Accounts (or use the defaults)
4. Add any payment terms and payment methods
5. Create departments and designations (if using HR)
6. Create the admin user's employee record

**You'll know it worked when:** Dropdowns in the app show your configured options.

---

## Phase 4: Deploy the App (⏱ 1–2 hours)

### 4.1 Build the frontend for production

✅ **Done** — the Dockerfile (`Dockerfile`) uses a multi-stage build:
1. Stage 1 (`node:20-alpine`): `npm ci && npm run build` → creates `apps/web-vue/dist/`
2. Stage 2 (`python:3.11-slim`): copies the dist and runs the FastAPI server

To build manually:
```bash
cd apps/web-vue && npm install && npm run build
```

### 4.2 Deploy to Railway

✅ **Done** — the app is live at `https://nova-production-2e9d.up.railway.app`. Railway:
1. Connects to the GitHub repo (`Salafite/Nova`)
2. Auto-detects the `Dockerfile`
3. Builds and deploys on every push to `master`
4. Runs `scripts/docker-entrypoint.sh` which applies migrations then starts uvicorn

To deploy to a new Railway project:
1. Create a new Railway project → "Deploy from GitHub repo"
2. Point it to your fork of `Salafite/Nova`
3. Set all env vars from Phase 2.2
4. Deploy

### 4.3 Set up a custom domain with SSL

🧑 **You** — Railway handles SSL automatically for custom domains:
1. In Railway dashboard → your project → Settings → Domains
2. Add your custom domain (e.g., `novaerp.com`)
3. Railway generates a TLS certificate via Let's Encrypt
4. At your domain registrar, add a CNAME record pointing your domain to Railway's URL (e.g., `nova-production-2e9d.up.railway.app`)

**You'll know it worked when:** Visiting `https://yourdomain.com` shows your app with a padlock icon.

---

## Phase 5: Continuous Integration (⏱ 1 hour)

### 5.1 Set up GitHub Actions for CI/CD

🤖 **Agent** — create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: nova_erp
          POSTGRES_USER: nova
          POSTGRES_PASSWORD: nova_secret
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r apps/api/requirements.txt
      - env: { DB_HOST: localhost, DB_PORT: 5432, DB_NAME: nova_erp, DB_USER: nova, DB_PASSWORD: nova_secret, DB_SCHEMA: Nova, SECRET_KEY: ci-test-key, ACCESS_TOKEN_EXPIRE_MINUTES: "1440", REFRESH_TOKEN_EXPIRE_DAYS: "7", ALLOWED_ORIGINS: "*" }
        run: python -m pytest --tb=short -x

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd apps/web-vue && npm ci && npm test
```

**You'll know it worked when:** The Actions tab shows green checkmarks on your latest commit.

### 5.2 Run E2E tests against production

🤖 **Agent** — point Playwright at the production URL to smoke-test:

```bash
cd apps/web-vue
PLAYWRIGHT_BASE_URL=https://yourdomain.com npx playwright test --workers=1
```

Current test coverage: **84 tests** across 13 spec files (auth, hr, purchasing, manufacturing, planning, landing, navigation, products, sales, finance, warehouse, bi, inventory-counts, adjustments).

**You'll know it worked when:** All 84 tests pass against the production build.

---

## Phase 6: Pre-Launch Verification (⏱ 1 hour)

### 6.1 Run the E2E smoke test as a real user

🧑 **You** — walk through the core user journey manually in an incognito window:
1. Visit your domain — login page should load
2. Click "Sign Up" and create an account
3. Log out, then log back in
4. Navigate to Purchasing, HR, Manufacturing, Planning pages
5. Create a record (e.g., a department, an employee)
6. Edit and delete a record
7. Test on your phone's browser — does it render reasonably?

**You'll know it worked when:** Every step above works without errors.

### 6.2 Verify error tracking works

🧑 **You** — trigger a deliberate error to confirm Sentry catches it:
1. Visit `https://yourdomain.com/api/nonexistent` — get a 404
2. Log into Sentry → check Issues — confirm the error was captured

**You'll know it worked when:** The error appears in your Sentry dashboard.

### 6.3 Verify email delivery (if configured)

🧑 **You** — trigger a password reset flow. Check your inbox (and spam folder).

**You'll know it worked when:** The email arrives within a few minutes.

### 6.4 Verify the security headers

🤖 **Agent** — check that security headers are properly set:

```bash
curl -sI https://yourdomain.com | findstr "X-Content-Type-Options X-Frame-Options Content-Security-Policy"
```

Expected headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy` (set by `SecurityHeadersMiddleware`)

**You'll know it worked when:** All security headers are present.

---

## Phase 7: After Launch (⏱ 30 min)

### 7.1 Set up database backups

🤖 **Agent** — create a backup script:

> Create `scripts/backup_db.ps1` that runs `pg_dump` using the same `DB_*` env vars and writes to a dated compressed file.

🧑 **You** — schedule it:
- **Railway Neon**: Enable automated daily backups in the Neon dashboard (Settings → Backups)
- **Self-hosted DB**: Schedule via Task Scheduler (Windows) or cron (Linux)

**You'll know it worked when:** A backup file exists with today's date.

### 7.2 Add a privacy policy and terms of service

🧑 **You** — legally required if you have users (especially EU/GDPR):
1. Use a generator like https://privacyterms.io or https://termly.io
2. Or pay a lawyer (~$500–2000)
3. Or adapt an open-source project's policies

🤖 **Agent** — create placeholder legal pages:

> Create `apps/web-vue/src/views/legal/PrivacyView.vue` and `TermsView.vue` with basic layout linking to your external policy. Add unauthenticated routes in `router/index.js` for `/privacy` and `/terms`.

**You'll know it worked when:** Visiting `https://yourdomain.com/#/privacy` shows your policy.

### 7.3 Set up uptime monitoring

🧑 **You** — use a free monitoring service:
- **Better Stack** (betterstack.com) — free, monitors every 30s
- **Uptime Robot** (uptimerobot.com) — free, monitors every 5 min
- **Pingdom** (pingdom.com) — free tier

Point at `https://yourdomain.com/api/health` and set email alerts.

**You'll know it worked when:** You receive the "monitor is up" confirmation email.

### 7.4 Know where to look when something breaks

🧑 **You** — save these links:

| If you need... | Go to... |
|---|---|
| See app errors/crashes | Sentry dashboard |
| See user behavior | PostHog dashboard |
| Check if the server is running | Railway.app dashboard |
| View server logs | Railway → project → Deployments → Logs |
| Restart the app | Railway → project → Settings → Restart |
| Check database health | Neon dashboard (or Railway → Database tab) |
| See payment issues | Stripe dashboard |
| Emergency redeploy | Push to GitHub master → auto-deploys |

---

## Quick Reference: Common Commands

```bash
# Build frontend
cd apps/web-vue && npm run build

# Run backend tests
python -m pytest --tb=short -x

# Run frontend unit tests
cd apps/web-vue && npm test

# Run E2E tests (local)
cd apps/web-vue && npx playwright test --workers=1

# Run E2E tests against production
cd apps/web-vue && PLAYWRIGHT_BASE_URL=https://yourdomain.com npx playwright test --workers=1

# Create database backup
pg_dump -h $env:DB_HOST -U $env:DB_USER -d $env:DB_NAME > backup_$(Get-Date -Format yyyyMMdd).sql

# Apply migrations manually
python scripts/run_migration.py

# View Railway logs
railway logs
```

---

## Summary

- **Total steps:** ~25 across 7 phases
- **🧑 You must do:** ~10 (account sign-ups, DNS, domain setup)
- **🤖 Agent can do:** ~12 (code fixes, config changes, CI setup)
- **🤝 Together:** ~3 (env vars, webhook config)
- **✅ Already done:** Hosting on Railway, Dockerfile, migrations auto-apply, frontend build, auth, billing infrastructure
- **Estimated monthly cost:** $50–120 (varies based on scale)
- **Biggest risk:** DNS propagation delay (hours) and forgetting to enable Neon automated backups

**Recommended first step:** Sign up for the optional services you need (Sentry, Resend, Stripe) and set their API keys as Railway env vars.

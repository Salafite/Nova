# Nova ERP Launch Checklist

- **Product**: Nova ERP — a full-featured Enterprise Resource Planning (ERP) web application
- **Tech stack**: Vue 3 frontend + Python FastAPI backend + PostgreSQL 16 database
- **Estimated total time**: 5–8 hours for a single person
- **Estimated monthly cost**: ~$50–120 (PostgreSQL hosting + VPS + optional services)

**Legend:**
- 🧑 **You** — requires your identity, accounts, payment details, or a decision. An agent can't do this for you.
- 🤖 **Agent** — paste the given prompt into your coding agent and it can do this in the codebase or via the command line.
- 🤝 **Together** — the agent prepares it, you click the final button or paste in a value.

---

## Phase 0: Fix Launch Blockers (⏱ 2–3 hours)

Before anything else, these must be fixed — they will prevent the app from running in production or expose it to security risks.

### 0.1 Remove hardcoded database passwords from debug files

🧑 **You** — these 17 debug scripts contain your database password as plain text and must be deleted before production:

- `apps/api/_db_check.py`
- `apps/api/_db_check2.py`
- `apps/api/_db_check3.py`
- `apps/api/_db_check4.py`
- `apps/api/_db_check_all.py`
- `apps/api/_db_check_case.py`
- `apps/api/_db_check_nova.py`
- `apps/api/_db_check_tables.py`
- `apps/api/_db_list.py`
- `apps/api/_db_list2.py`
- `apps/api/_db_setup_schema.py`
- `apps/api/_db_verify.py`
- `apps/api/set_passwords.py`
- `scripts/run_migration.py`
- `scripts/init_db.py`
- `scripts/seed_demo.py`
- `scripts/fix_t0010.py`

Delete each file (the `Remove-Item` PowerShell command works on Windows). **You'll know it worked when:** `git status` shows no more `_db_` prefixed files in `apps/api/`.

### 0.2 Fix JWT secret key name mismatch

🤖 **Agent** — there's a mismatch: `packages/auth/jwt.py` reads `SECRET_KEY` from environment but `apps/api/.env` uses `JWT_SECRET`. Make them consistent.

Update `apps/api/.env.example` and `apps/api/.env` to use `SECRET_KEY` instead of `JWT_SECRET`, matching what `packages/auth/jwt.py` expects:

> Edit `apps/api/.env` and `apps/api/.env.example`: find `JWT_SECRET=...` and change it to `SECRET_KEY=...` with a strong random value (at least 32 characters). Then verify `SECRET_KEY` is the only name used in `packages/auth/jwt.py` on line 5.

**You'll know it worked when:** `Select-String "JWT_SECRET" apps/api/.env` returns no matches, and `Select-String "SECRET_KEY" packages/auth/jwt.py` shows the env var read.

### 0.3 Add missing production SDKs to requirements.txt

🤖 **Agent** — `apps/api/requirements.txt` is missing several packages that production relies on:

> Add these lines to `apps/api/requirements.txt`:
> ```
> stripe>=8.0
> resend>=0.8
> posthog>=3.0
> sentry-sdk>=2.0
> ```
> Then run `pip install -r apps/api/requirements.txt` to verify they install cleanly.

**You'll know it worked when:** `python -c "import stripe; import resend; import posthog; import sentry_sdk; print('OK')"` runs without errors.

### 0.4 Initialize Sentry at app startup

🤖 **Agent** — `packages/analytics/sentry.py` has `init_sentry()` but it's never called from the main app. Add the call:

> In `apps/api/main.py`, add `from packages.analytics.sentry import init_sentry` at the top. Then call `init_sentry()` right after the `app = FastAPI(...)` line (before any middleware). Only call it when `SENTRY_DSN` env var is set.

**You'll know it worked when:** Starting the app with `SENTRY_DSN` set prints no Sentry-related errors.

### 0.5 Fix `reload=True` in production startup

🤖 **Agent** — `apps/api/main.py` runs uvicorn with `reload=True` which is a development-only feature:

> Change `uvicorn.run('main:app', host='0.0.0.0', port=8070, reload=True)` to use `reload=False`. Better yet, make it conditional: `reload=os.getenv('NOVA_ENV') != 'production'`. Also add `workers=4` for multi-process serving.

**You'll know it worked when:** The app starts without the "auto-reload" message in the logs.

### 0.6 Remove `.env` from Git tracking

🧑 **You** — `apps/api/.env` is checked into Git, which means your secrets are in version history. This is a security risk.

> Run `git rm --cached apps/api/.env` to stop tracking it (this removes it from Git but keeps the file on disk). Then add `.env` to the root `.gitignore`. Rotate any secrets that were in that file (database password, JWT secret).

**You'll know it worked when:** `git status` shows `apps/api/.env` as deleted (staged) without actually deleting the file from disk.

---

## Phase 1: Accounts & Prerequisites (⏱ 30 min)

### 1.1 Create accounts for production services

🧑 **You** — sign up for these services. Pick the free or cheapest tier that works — you can upgrade later.

| Service | Purpose | Approx. cost/month | Sign-up link |
|---|---|---|---|
| **Railway.app** or **Fly.io** | Host the app (deploy the Docker container) | $5–20 | https://railway.app or https://fly.io |
| **Neon.tech** or **Supabase** | PostgreSQL 16 database (managed, with backups) | $0–19 (free tier available) | https://neon.tech or https://supabase.com |
| **Stripe** | Payment processing (only if billing is enabled) | 2.9% + $0.30 per transaction | https://stripe.com |
| **Sentry** | Error tracking (find crashes) | Free (5k events/month) | https://sentry.io |
| **Resend** | Transactional email (password reset, invoices) | Free (100 emails/day) | https://resend.com |
| **PostHog** | Product analytics (see what users do) | Free (1m events/month) | https://posthog.com |
| **Namecheap** or **Cloudflare** | Domain name (e.g., novaerp.com) | $10–15/year | https://namecheap.com or https://cloudflare.com |
| **Cloudflare** | DNS, CDN, DDoS protection | Free (free tier is excellent) | https://cloudflare.com |

After each sign-up, save the dashboard URL and any API keys — you'll need them in Phase 2.

**You'll know it worked when:** You can log into each service dashboard and see the "getting started" screen.

---

## Phase 2: Secrets & Configuration (⏱ 30 min)

### 2.1 Generate production secrets

🧑 **You** — create a strong random secret for JWT token signing, and a strong database password.

> Generate a 64-character random string for `SECRET_KEY`. On Windows PowerShell, run:
> ```
> -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
> ```
> Save this somewhere safe (like a password manager). Generate a different 32-character random string for the database password.

**You'll know it worked when:** You have a long random string saved that you can paste into the hosting platform's settings.

### 2.2 Set environment variables on the hosting platform

🤝 **Together** — go to your hosting platform's dashboard (Railway.app, Fly.io, or wherever you deployed), find the environment variables / secrets section, and set each of these:

| Variable | What to put |
|---|---|
| `DB_HOST` | Your database host URL (from Neon/Supabase dashboard) |
| `DB_PORT` | `5432` |
| `DB_NAME` | Your database name |
| `DB_USER` | Your database username |
| `DB_PASSWORD` | The strong password you generated in step 2.1 |
| `DB_SCHEMA` | `Nova` |
| `SECRET_KEY` | The 64-char random string from step 2.1 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
| `ALLOWED_ORIGINS` | Your domain, e.g., `https://novaerp.com` |
| `NOVA_ENV` | `production` |
| `APP_URL` | Your domain, e.g., `https://novaerp.com` |
| `STRIPE_SECRET_KEY` | Your Stripe live secret key (starts with `sk_live_`) — skip if not using payments |
| `STRIPE_PRICE_ID` | Your Stripe price ID — skip if not using payments |
| `STRIPE_WEBHOOK_SECRET` | Your Stripe webhook signing secret — skip if not using payments |
| `POSTHOG_API_KEY` | Your PostHog project API key — skip if not using analytics |
| `SENTRY_DSN` | Your Sentry DSN URL — skip if not using error tracking |
| `RESEND_API_KEY` | Your Resend API key — skip if not using email |
| `RESEND_FROM_EMAIL` | `noreply@yourdomain.com` — skip if not using email |
| `RELEASE_VERSION` | `1.0.0` |

🤖 **Agent** — then run this to verify the production app starts without crashing:
> ```
> $env:NOVA_ENV="production"
> uvicorn apps.api.main:app --host 0.0.0.0 --port 8070
> ```

**Never paste secrets into chat or commit them to code.** They go directly into the hosting platform's settings panel.

**You'll know it worked when:** The app starts without "missing environment variable" errors.

---

## Phase 3: Production Services (⏱ 1 hour)

### 3.1 Set up the production database

🤝 **Together** — create your database on Neon/Supabase. They'll give you a connection string that looks like `postgresql://user:password@host:5432/dbname`.

> Copy the connection details (host, port, name, user, password) from the database provider's dashboard. You'll paste them as the `DB_*` environment variables in step 2.2.

**You'll know it worked when:** You can connect from a database tool (like pgAdmin or DBeaver) using those credentials.

### 3.2 Run database migrations on the production database

🤖 **Agent** — once the database is created and the environment variables are set, apply the schema to create all tables:

> Create a migration script that runs all SQL migration files in order from `database/migrations/` against the production database, using the `DB_*` environment variables for connection. Handle errors gracefully and report which migrations succeeded or failed.

**You'll know it worked when:** The script reports all 9 migration files applied successfully.

### 3.3 Create admin user

🧑 **You** — after the database is ready and the app is deployed (Phase 4), visit your app's URL, go through signup, and verify you can log in as the first user. If signup is disabled in production, use the API directly:

> Use a tool like Postman or curl to POST to `https://yourdomain.com/api/auth/signup` with `{"email": "admin@yourcompany.com", "password": "a-strong-password-you-will-remember", "full_name": "Admin"}`.

**You'll know it worked when:** You can log into the app with that email and password.

### 3.4 Configure Stripe webhooks (only if billing is enabled)

🤝 **Together** — in the Stripe dashboard, go to Developers > Webhooks and add an endpoint:

> Endpoint URL: `https://yourdomain.com/api/billing/webhook`
> Events to listen for: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
> Copy the webhook signing secret and set it as the `STRIPE_WEBHOOK_SECRET` environment variable.

**You'll know it worked when:** Stripe shows the webhook endpoint as "Enabled" with a 200 status on the latest ping attempt.

### 3.5 Verify Resend email delivery (only if email is enabled)

🤝 **Together** — in the Resend dashboard, add and verify your sending domain (e.g., `novaerp.com`). You'll need to add DNS TXT records at your domain provider to prove you own the domain.

**You'll know it worked when:** Resend shows your domain as "Verified" with a green checkmark.

---

## Phase 4: Deploy the App (⏱ 1–2 hours)

### 4.1 Build the frontend for production

🤖 **Agent** — build the Vue 3 frontend into static files that the backend can serve:

> In `apps/web-vue/`, run `npm install` then `npm run build`. Verify the `dist/` folder is created with an `index.html` and compiled JS/CSS files. Check that the build doesn't have any errors.

**You'll know it worked when:** `apps/web-vue/dist/` exists with files inside and no errors in the build output.

### 4.2 Fix the Dockerfile for production

🤖 **Agent** — the current Dockerfile has several issues: no multi-stage build, no frontend build, copies everything, runs as root.

> Rewrite `Dockerfile` as a multi-stage build:
> - **Stage 1 (node)**: Build the Vue frontend using `node:20-alpine`. Copy `apps/web-vue/`, run `npm ci && npm run build`.
> - **Stage 2 (python)**: Start from `python:3.11-slim`. Copy only `apps/api/requirements.txt`, install deps. Copy the built frontend from stage 1. Copy only the `apps/api/` and `packages/` directories. Add a non-root user (`adduser --disabled-password appuser`), switch to it. Set `CMD` with `--workers 4` on uvicorn.

Also create a `.dockerignore` file that excludes everything except what's needed.

**You'll know it worked when:** `docker build -t nova-erp . && docker run nova-erp python -c "import app; print('OK')"` succeeds quickly (under 2 minutes) and the image is under 500MB.

### 4.3 Deploy to the hosting platform

🧑 **You** — follow your hosting platform's instructions to deploy. The general flow:

1. **Push to a Git repo** (GitHub, GitLab, etc.)
2. **Connect the repo** to your hosting platform
3. **Set all environment variables** from step 2.2 in the platform's dashboard
4. **Trigger a deploy** — the platform reads the Dockerfile, builds the image, and runs it

**For Railway.app:** Create a new project → "Deploy from GitHub repo" → add your repo → Railway auto-detects the Dockerfile → add env vars → deploy.
**For Fly.io:** Run `fly launch` in the project root → `fly secrets set KEY=VALUE` for each env var → `fly deploy`.

**You'll know it worked when:** The hosting platform shows a green "healthy" or "running" status and you can visit the URL it gives you.

### 4.4 Set up a reverse proxy with SSL

🧑 **You** — if your hosting platform doesn't handle SSL automatically, you need a reverse proxy. Cloudflare is the easiest option (and free):

1. Sign up at Cloudflare.com, add your domain
2. Change your domain's nameservers at your domain registrar to Cloudflare's (they'll show you which ones)
3. In Cloudflare DNS, create an A record pointing your domain to your server's IP
4. Enable "Proxy" (orange cloud) — this gives you free SSL, CDN, and DDoS protection
5. Enable "Always Use HTTPS" in Cloudflare's SSL/TLS settings

**If you need your own nginx config:**

🤖 **Agent** — create `infrastructure/nginx.conf`:

> Write an nginx config that:
> - Listens on port 80 and 443
> - SSL certificate paths as placeholders (or use Let's Encrypt via Certbot)
> - Proxies `/api/` and `/` to `http://127.0.0.1:8070`
> - Sets proper `X-Forwarded-For`, `X-Forwarded-Proto` headers
> - Enables gzip compression for static assets
> - Sets a reasonable `client_max_body_size` (e.g., 10M)

**You'll know it worked when:** Visiting `https://yourdomain.com` shows your app with a padlock icon in the browser.

---

## Phase 5: Domain (⏱ 30 min + DNS propagation)

### 5.1 Buy your domain

🧑 **You** — if you don't have one already, buy a domain from Namecheap, Cloudflare, or your preferred registrar. Something short and memorable like `novaerp.com` or your company name.

**Cost:** ~$10–15 per year.

**You'll know it worked when:** You get a confirmation email and can log into the registrar's dashboard showing your new domain.

### 5.2 Point the domain to your app

🧑 **You** — in your domain registrar's DNS settings, create records that point your domain to your hosting platform:

- **For Railway.app:** They provide a `*.railway.app` URL. Add a CNAME record pointing `yourdomain.com` to that URL.
- **For Fly.io:** They provide a `*.fly.dev` URL. Same — add a CNAME record.
- **For a VPS (DigitalOcean, Linode, etc.):** Add an A record pointing to your server's IP address.

**DNS propagation can take up to 24 hours**, but usually happens within 1–2 hours.

**You'll know it worked when:** `ping yourdomain.com` returns an IP address (or CNAME), and visiting `https://yourdomain.com` in a browser shows your app.

---

## Phase 6: Pre-Launch Verification (⏱ 1 hour)

### 6.1 Run the E2E smoke test as a real user

🧑 **You** — walk through the core user journey manually, just like a customer would:

1. Open an incognito/private browser window
2. Visit your domain — you should see the login page
3. Click "Sign Up" and create an account
4. Log out, then log back in with your new account
5. Navigate to a few pages (Purchasing, HR, Manufacturing, Planning)
6. Try creating a record (e.g., a department, an employee)
7. Edit and delete a record
8. Try on your phone's browser — does it render reasonably?

**You'll know it worked when:** Every step above works without errors.

### 6.2 Run the automated test suite

🤖 **Agent** — run the test suite to make sure nothing is broken by the production build:

> ```
> cd apps/web-vue && npm test
> cd ../.. && pytest --tb=short -x
> ```

**You'll know it worked when:** All unit tests pass (Vitest and pytest).

### 6.3 Verify error tracking works

🧑 **You** — deliberately trigger an error to confirm Sentry catches it:

> Visit `https://yourdomain.com/api/nonexistent` — you should get a 404 JSON response. Log into Sentry and check that an error was captured (even 404s may show up depending on configuration).

**You'll know it worked when:** The error appears in your Sentry dashboard.

### 6.4 Verify email delivery (if configured)

🧑 **You** — trigger a password reset flow (or any email-generating action) and confirm the email arrives in your inbox (check spam folder too).

**You'll know it worked when:** The email arrives within a few minutes.

---

## Phase 7: After Launch (⏱ 30 min)

### 7.1 Set up database backups

🤖 **Agent** — create a database backup script and schedule:

> Create `scripts/backup_db.sh` (or `.ps1` for Windows) that runs `pg_dump` using the same `DB_*` environment variables and writes to a dated file. The backup should be compressed (`.gz`).

🧑 **You** — then schedule it to run daily:
- **On a Linux server:** `crontab -e` and add `0 3 * * * /path/to/backup_db.sh`
- **On Railway.app or managed DB:** Use the provider's built-in backup feature (they often have daily backups automatically)

**You'll know it worked when:** A backup file exists in your backup directory with today's date.

### 7.2 Add a privacy policy and terms of service

🧑 **You** — these are legally required if you have users (especially in the EU/GDPR). You have options:

1. **Free template:** Use a generator like https://privacyterms.io or https://termly.io
2. **Pay a lawyer:** ~$500–2000 for custom documents
3. **Copy an open-source project's policies** (modify for your use case)

Add the resulting pages at `/privacy` and `/terms` routes.

🤖 **Agent** — create placeholder legal pages that link to your external privacy policy and terms:

> Create `apps/web-vue/src/views/legal/PrivacyView.vue` and `TermsView.vue` with basic layout. Add routes in `apps/web-vue/src/router/index.js` for `/privacy` and `/terms` (no auth required). Include a link to your full policy hosted elsewhere, or embed the text.

**You'll know it worked when:** Visiting `https://yourdomain.com/#/privacy` shows your privacy policy content.

### 7.3 Set up uptime monitoring

🧑 **You** — use a free monitoring service to get alerted if your site goes down:

- **Better Stack** (betterstack.com) — free, monitors every 30 seconds
- **Uptime Robot** (uptimerobot.com) — free, monitors every 5 minutes
- **Pingdom** (pingdom.com) — free tier available

Point it at `https://yourdomain.com/api/health` and set it to alert you via email.

**You'll know it worked when:** You receive the "monitor is up" confirmation email.

### 7.4 Know where to look when something breaks

🧑 **You** — save these links for troubleshooting:

| If you need... | Go to... |
|---|---|
| See app errors/crashes | Sentry dashboard |
| See user behavior | PostHog dashboard |
| Check if the server is running | Hosting platform dashboard |
| View server logs | Hosting platform logs tab (or `fly logs` / `railway logs`) |
| Check database health | Database provider dashboard |
| See payment issues | Stripe dashboard |
| Emergency restart | Hosting platform "Restart" button |

---

## Quick Reference: Common Commands

```bash
# Build frontend
cd apps/web-vue && npm run build

# Run backend tests
pytest --tb=short

# Run frontend tests
cd apps/web-vue && npm test

# Run E2E tests
cd apps/web-vue && npx playwright test

# Create database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup_$(date +%Y%m%d).dump

# Apply migrations
python scripts/run_migration.py
```

---

## Summary

- **Total steps:** ~25
- **🧑 You must do:** ~10 (mostly account sign-ups, DNS, and verification)
- **🤖 Agent can do:** ~12 (code fixes, config changes, build)
- **🤝 Together:** ~3 (setting env vars, webhook setup)
- **Estimated monthly cost:** $50–120 (varies based on scale)
- **Biggest risk:** DNS propagation delay (can take hours) and store review if you ever launch a mobile app

**Recommended first step:** Start with Phase 0 (0.1–0.6) to fix the critical security and configuration issues, then move to Phase 1 to create accounts.

Want me to start on any of the 🤖 steps now?

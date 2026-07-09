# Nova ERP Deployment Guide

## Prerequisites

- **Python 3.11+** (backend)
- **Node.js 20+** (frontend build)
- **PostgreSQL 16+** (database)
- **Docker + Docker Compose** (optional, containerized deployment)

## Quick Start (Development)

### 1. Database Setup

```bash
# Create the database and schema
createdb nova_erp
psql -d nova_erp -f database/schema.sql
```

### 2. Backend

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env    # edit with your settings
python main.py          # starts on port 8070
```

### 3. Frontend

```bash
cd apps/web-vue
npm install
npm run dev             # starts on port 5173
```

The frontend dev server proxies API requests to port 8070. Open `http://localhost:5173` and log in with the default admin credentials.

## Docker Compose (Production)

```bash
docker compose up -d
```

Services:
- `db` — PostgreSQL 16 on port 5432
- `api` — FastAPI on port 8070 (serves both API + built frontend)

Build the frontend before running Compose:

```bash
cd apps/web-vue && npm run build && cd ../..
docker compose up -d
```

Open `http://localhost:8070`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `Stage` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `` | Database password |
| `DB_SCHEMA` | `Nova` | Database schema |
| `SECRET_KEY` | *(required)* | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT access token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token expiry |
| `ALLOWED_ORIGINS` | `*` | CORS origins |
| `NOVA_ENV` | *(none)* | Set to `production` for prod mode |

## Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain
- [ ] Set up PostgreSQL backup (pg_dump cron job)
- [ ] Configure SSL (reverse proxy with nginx/caddy + Let's Encrypt)
- [ ] Build frontend and serve from the API static file mount
- [ ] Set `DB_PASSWORD` to a strong value

## On-Premise Deployment

For on-premise, use Podman Compose:

```bash
podman compose up -d
```

The same `docker-compose.yml` works with Podman — no changes needed.

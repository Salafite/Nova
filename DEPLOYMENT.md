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
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `nova_erp` | Database name |
| `POSTGRES_USER` | `nova` | Database user |
| `POSTGRES_PASSWORD` | `nova_secret` | Database password |
| `JWT_SECRET` | `change-me` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token expiry |
| `ALLOWED_ORIGINS` | `*` | CORS origins |
| `DB_SCHEMA` | `Nova` | Database schema |

## Production Checklist

- [ ] Change `JWT_SECRET` to a strong random value
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain
- [ ] Set up PostgreSQL backup (pg_dump cron job)
- [ ] Configure SSL (reverse proxy with nginx/caddy + Let's Encrypt)
- [ ] Build frontend and serve from the API static file mount
- [ ] Set `POSTGRES_PASSWORD` to a strong value

## On-Premise Deployment

For on-premise, use Podman Compose:

```bash
podman compose up -d
```

The same `docker-compose.yml` works with Podman — no changes needed.

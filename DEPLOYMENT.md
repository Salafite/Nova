# Nova ERP Deployment Guide

## Prerequisites

- **Python 3.11+** (backend)
- **Node.js 20+** (frontend build)
- **PostgreSQL 16+** (relational database)
- **Redis 7+** (distributed state, MCP Tier 2 action storage & sliding window rate limiting)
- **Docker + Docker Compose** or **Podman + Podman Compose** (containerized deployment)

## Quick Start (Development)

### 1. Database & Redis Setup

```bash
# PostgreSQL
createdb nova_erp
psql -d nova_erp -f database/schema.sql

# Redis (optional for standalone dev — falls back to thread-safe in-memory store if offline)
docker run -d --name nova-redis -p 6379:6379 redis:7-alpine
```

### 2. Backend

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env    # edit with your database, redis, and auth settings
python main.py          # starts on port 8070 (single worker with reload in dev)
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
- `db` — PostgreSQL 16 on port 5432 with health check and persistent volume `pgdata`
- `redis` — Redis 7 on port 6379 with persistent volume `redisdata`, `volatile-ttl` eviction policy, and 256MB memory cap
- `api` — FastAPI on port 8070 running 4 uvicorn workers (serves REST API, MCP SSE, and built Vue 3 frontend)

Build the frontend before running Compose:

```bash
cd apps/web-vue && npm run build && cd ../..
docker compose up -d
```

Open `http://localhost:8070`.

## Multi-Worker Uvicorn Architecture

In production (`NOVA_ENV=production`), the API server runs 4 concurrent Uvicorn worker processes to maximize CPU utilization and throughput:

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8070 --workers 4
```

### Shared Distributed State via Redis

- **Tier 2 MCP Pending Actions**: Actions requiring user confirmation (such as order confirmation, cancellation, and product deletion) are stored in Redis under `nova:mcp:action:{action_id}` with a strict 5-minute (300s) TTL. A user or agent can propose an action on Worker 1 and confirm it on Worker 2, 3, or 4 with atomic single-execution guarantees (`GETDEL` pipeline).
- **Distributed Sliding Window Rate Limiting**: Request rate limits (for `auth`, `read`, `write`, and `ai` endpoints) use Redis Sorted Sets (`ZSET`) keyed by client IP (`nova:ratelimit:{client_ip}:{category}`). All worker processes update and enforce shared sliding window counters, with automatic TTL eviction preventing memory leaks.
- **Proxy Header Support**: Client IP extraction inspects `X-Forwarded-For` and `X-Real-IP` headers from trusted reverse proxies (`TRUSTED_PROXIES`), ensuring client devices behind corporate gateways or load balancers are accurately differentiated.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `nova_erp` | Database name |
| `DB_USER` | `nova` | Database user |
| `DB_PASSWORD` | `nova_secret` | Database password |
| `DB_SCHEMA` | `Nova` | Database schema |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | `` | Redis password (optional) |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_URL` | *(none)* | Optional complete Redis connection URL (overrides host/port/db/password) |
| `TRUSTED_PROXIES` | `127.0.0.1,::1` | Comma-separated list of trusted reverse proxy IPs or CIDR subnets |
| `SECRET_KEY` | *(required)* | JWT signing key (minimum 32 characters in production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT access token expiry (minutes) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token expiry (days) |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `NOVA_ENV` | *(none)* | Set to `production` for multi-worker production mode |

## Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value (at least 32 characters)
- [ ] Set `NOVA_ENV=production` to enable 4-worker uvicorn process scaling
- [ ] Ensure Redis container is running and healthy with persistent `redisdata` volume
- [ ] Set `TRUSTED_PROXIES` to your reverse proxy / load balancer IP or subnet (e.g. `10.0.0.0/8`, `172.16.0.0/12`)
- [ ] Set `ALLOWED_ORIGINS` to your production frontend domain
- [ ] Set up PostgreSQL backup (pg_dump cron job)
- [ ] Configure SSL termination (reverse proxy with Nginx, Caddy, or Traefik + Let's Encrypt)
- [ ] Set `DB_PASSWORD` and `REDIS_PASSWORD` to strong values

## On-Premise & Podman Deployment

For on-premise deployments or environments requiring daemonless / rootless containers, use **Podman Compose**:

### 1. Start Services with Podman Compose

```bash
podman compose up -d
```

The standard `docker-compose.yml` is fully compatible with Podman Compose.

### 2. Verify Container Health

```bash
podman ps
# Check db, redis, and api health status
podman healthcheck run nova-redis
```

### 3. Persistent Volumes

Podman automatically manages local named volumes:
- `pgdata`: PostgreSQL data directory (`/var/lib/postgresql/data`)
- `redisdata`: Redis appendonly and dump files (`/data`)

### 4. Systemd Integration (Optional)

Generate systemd service units for automatic restart on boot:

```bash
cd /etc/systemd/system/
podman generate systemd --name nova-api --files
systemctl daemon-reload
systemctl enable --now container-nova-api.service
```

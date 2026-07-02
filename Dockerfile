FROM node:20-alpine AS frontend
WORKDIR /build
COPY apps/web-vue/package*.json ./
RUN npm ci
COPY apps/web-vue/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    adduser --disabled-password --gecos '' appuser

COPY apps/api/ apps/api/
COPY controllers/ controllers/
COPY database/ database/
COPY modules/ modules/
COPY packages/ packages/
COPY scripts/docker-entrypoint.sh scripts/run_migration.py scripts/
COPY --from=frontend /build/dist/ apps/web-vue/dist/

EXPOSE 8070

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

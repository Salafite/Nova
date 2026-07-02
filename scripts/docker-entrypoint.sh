#!/bin/sh
set -e

echo "=== Nova ERP Docker Entrypoint ==="

echo "Running database migrations..."
cd /app
python scripts/run_migration.py || echo "Migration warning (non-fatal)"

echo "Starting uvicorn on 0.0.0.0:${PORT:-8070}..."
exec uvicorn apps.api.main:app --host 0.0.0.0 --port "${PORT:-8070}" --workers 4

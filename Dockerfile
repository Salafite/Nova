FROM node:20-alpine AS frontend
WORKDIR /build
COPY apps/web-vue/package*.json ./
RUN npm ci
COPY apps/web-vue/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    adduser --disabled-password --gecos '' appuser
COPY apps/api/ apps/api/
COPY packages/ packages/
COPY --from=frontend /build/dist/ apps/web-vue/dist/
EXPOSE 8070
USER appuser
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8070", "--workers", "4"]

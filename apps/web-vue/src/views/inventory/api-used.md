# API Endpoints — Stock Levels (Inventory)

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0009I/` | List all stock levels | — | `StockLevelResponse[]` |
| 2 | GET | `/api/T0009I/{id}` | Get single stock level | `id` (path) | `StockLevelResponse` |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookups:** Products from `/api/T0003I/`, Warehouses from `/api/T0008I/`.

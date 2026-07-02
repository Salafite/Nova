# API Endpoints — Stock Movements

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0064I/` | List all movements | — | `StockMovementResponse[]` |
| 2 | GET | `/api/T0064I/{id}` | Get single movement | `id` (path) | `StockMovementResponse` |
| 3 | POST | `/api/T0064I/` | Create movement | `StockMovementCreate` body | `StockMovementResponse` |
| 4 | PUT | `/api/T0064I/{id}` | Update movement | `id` (path) + body | `StockMovementResponse` |
| 5 | DELETE | `/api/T0064I/{id}` | Delete movement | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookups:** Products from `/api/T0003I/`, Warehouses from `/api/T0008I/`.

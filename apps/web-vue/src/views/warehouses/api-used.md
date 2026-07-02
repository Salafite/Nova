# API Endpoints — Warehouses

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0008I/` | List all warehouses | — | `WarehouseResponse[]` |
| 2 | GET | `/api/T0008I/{id}` | Get single warehouse | `id` (path) | `WarehouseResponse` |
| 3 | POST | `/api/T0008I/` | Create warehouse | `WarehouseCreate` body | `WarehouseResponse` |
| 4 | PUT | `/api/T0008I/{id}` | Update warehouse | `id` (path) + `WarehouseUpdate` body | `WarehouseResponse` |
| 5 | DELETE | `/api/T0008I/{id}` | Delete warehouse | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

# API Endpoints — Suppliers

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0011I/` | List all suppliers | — | `SupplierResponse[]` |
| 2 | GET | `/api/T0011I/{id}` | Get single supplier | `id` (path) | `SupplierResponse` |
| 3 | POST | `/api/T0011I/` | Create supplier | `SupplierCreate` body | `SupplierResponse` |
| 4 | PUT | `/api/T0011I/{id}` | Update supplier | `id` (path) + `SupplierUpdate` body | `SupplierResponse` |
| 5 | DELETE | `/api/T0011I/{id}` | Delete supplier | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

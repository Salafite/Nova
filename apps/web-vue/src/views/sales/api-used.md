# API Endpoints — Sales Orders

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0012I/` | List all sales orders | — | `SalesOrderResponse[]` |
| 2 | GET | `/api/T0012I/{id}` | Get single order | `id` (path) | `SalesOrderResponse` |
| 3 | POST | `/api/T0012I/` | Create order | `SalesOrderCreate` body | `SalesOrderResponse` |
| 4 | PUT | `/api/T0012I/{id}` | Update order | `id` (path) + `SalesOrderUpdate` body | `SalesOrderResponse` |
| 5 | DELETE | `/api/T0012I/{id}` | Delete order | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

**Lookup:** Customers loaded from `/api/T0010I/` for customer dropdown.

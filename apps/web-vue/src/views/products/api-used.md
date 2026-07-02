# API Endpoints — Products

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0003I/` | List all products | — | `ProductResponse[]` |
| 2 | GET | `/api/T0003I/{id}` | Get single product | `id` (path) | `ProductResponse` |
| 3 | POST | `/api/T0003I/` | Create a product | `ProductCreate` body | `ProductResponse` |
| 4 | PUT | `/api/T0003I/{id}` | Update a product | `id` (path) + `ProductUpdate` body | `ProductResponse` |
| 5 | DELETE | `/api/T0003I/{id}` | Delete a product | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

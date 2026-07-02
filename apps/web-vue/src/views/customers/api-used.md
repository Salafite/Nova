# API Endpoints — Customers

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0010I/` | List all customers | — | `CustomerResponse[]` |
| 2 | GET | `/api/T0010I/{id}` | Get single customer | `id` (path) | `CustomerResponse` |
| 3 | POST | `/api/T0010I/` | Create customer | `CustomerCreate` body | `CustomerResponse` |
| 4 | PUT | `/api/T0010I/{id}` | Update customer | `id` (path) + `CustomerUpdate` body | `CustomerResponse` |
| 5 | DELETE | `/api/T0010I/{id}` | Delete customer | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

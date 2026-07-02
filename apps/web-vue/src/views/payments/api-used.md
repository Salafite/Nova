# API Endpoints — Payments

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0091I/` | List all payments | — | `PaymentResponse[]` |
| 2 | GET | `/api/T0091I/{id}` | Get single payment | `id` (path) | `PaymentResponse` |
| 3 | POST | `/api/T0091I/` | Create payment | `PaymentCreate` body | `PaymentResponse` |
| 4 | PUT | `/api/T0091I/{id}` | Update payment | `id` (path) + `PaymentUpdate` body | `PaymentResponse` |
| 5 | DELETE | `/api/T0091I/{id}` | Delete payment | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

# API Endpoints — Payment Terms

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0096I/` | List all payment terms | — | `PaymentTermResponse[]` |
| 2 | GET | `/api/T0096I/{id}` | Get single term | `id` (path) | `PaymentTermResponse` |
| 3 | POST | `/api/T0096I/` | Create term | `PaymentTermCreate` body | `PaymentTermResponse` |
| 4 | PUT | `/api/T0096I/{id}` | Update term | `id` (path) + `PaymentTermUpdate` body | `PaymentTermResponse` |
| 5 | DELETE | `/api/T0096I/{id}` | Delete term | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token.

**Base URL:** `http://localhost:8070/api`

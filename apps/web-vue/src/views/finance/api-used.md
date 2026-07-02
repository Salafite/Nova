# API Endpoints — Invoices

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0090I/` | List all invoices | — | `InvoiceResponse[]` |
| 2 | GET | `/api/T0090I/{id}` | Get single invoice | `id` (path) | `InvoiceResponse` |
| 3 | POST | `/api/T0090I/` | Create invoice | `InvoiceCreate` body | `InvoiceResponse` |
| 4 | PUT | `/api/T0090I/{id}` | Update invoice | `id` (path) + `InvoiceUpdate` body | `InvoiceResponse` |
| 5 | DELETE | `/api/T0090I/{id}` | Delete invoice | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token.

**Base URL:** `http://localhost:8070/api`

**Note:** The T0090 controller returns 500 error (table may be missing from DB). The frontend shows an error state gracefully.

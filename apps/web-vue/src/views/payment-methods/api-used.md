# API Endpoints — Payment Methods

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0097I/` | List all payment methods | — | `PaymentMethodResponse[]` |
| 2 | GET | `/api/T0097I/{id}` | Get single method | `id` (path) | `PaymentMethodResponse` |
| 3 | POST | `/api/T0097I/` | Create method | `PaymentMethodCreate` body | `PaymentMethodResponse` |
| 4 | PUT | `/api/T0097I/{id}` | Update method | `id` (path) + `PaymentMethodUpdate` body | `PaymentMethodResponse` |
| 5 | DELETE | `/api/T0097I/{id}` | Delete method | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token.

**Base URL:** `http://localhost:8070/api`

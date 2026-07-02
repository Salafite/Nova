# API Endpoints — Chart of Accounts

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0026I/` | List all accounts | — | `COAResponse[]` |
| 2 | GET | `/api/T0026I/{id}` | Get single account | `id` (path) | `COAResponse` |
| 3 | POST | `/api/T0026I/` | Create account | `COACreate` body | `COAResponse` |
| 4 | PUT | `/api/T0026I/{id}` | Update account | `id` (path) + `COAUpdate` body | `COAResponse` |
| 5 | DELETE | `/api/T0026I/{id}` | Delete account | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

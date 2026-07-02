# API Endpoints — Designations

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0029I/` | List all designations | — | `DesignationResponse[]` |
| 2 | GET | `/api/T0029I/{id}` | Get single designation | `id` (path) | `DesignationResponse` |
| 3 | POST | `/api/T0029I/` | Create designation | `DesignationCreate` body | `DesignationResponse` |
| 4 | PUT | `/api/T0029I/{id}` | Update designation | `id` (path) + `DesignationUpdate` body | `DesignationResponse` |
| 5 | DELETE | `/api/T0029I/{id}` | Delete designation | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

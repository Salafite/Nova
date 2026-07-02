# API Endpoints — Departments

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0028I/` | List all departments | — | `DepartmentResponse[]` |
| 2 | GET | `/api/T0028I/{id}` | Get single department | `id` (path) | `DepartmentResponse` |
| 3 | POST | `/api/T0028I/` | Create department | `DepartmentCreate` body | `DepartmentResponse` |
| 4 | PUT | `/api/T0028I/{id}` | Update department | `id` (path) + `DepartmentUpdate` body | `DepartmentResponse` |
| 5 | DELETE | `/api/T0028I/{id}` | Delete department | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token.

**Base URL:** `http://localhost:8070/api`

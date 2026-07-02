# API Endpoints — Employees

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0030I/` | List all employees | — | `EmployeeResponse[]` |
| 2 | GET | `/api/T0030I/{id}` | Get single employee | `id` (path) | `EmployeeResponse` |
| 3 | POST | `/api/T0030I/` | Create employee | `EmployeeCreate` body | `EmployeeResponse` |
| 4 | PUT | `/api/T0030I/{id}` | Update employee | `id` (path) + `EmployeeUpdate` body | `EmployeeResponse` |
| 5 | DELETE | `/api/T0030I/{id}` | Delete employee | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

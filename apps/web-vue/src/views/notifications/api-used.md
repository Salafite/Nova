# API Endpoints — User Notifications

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/T0098I/` | List all notifications | — | `NotificationResponse[]` |
| 2 | GET | `/api/T0098I/{id}` | Get single notification | `id` (path) | `NotificationResponse` |
| 3 | POST | `/api/T0098I/` | Create notification | `NotificationCreate` body | `NotificationResponse` |
| 4 | PUT | `/api/T0098I/{id}` | Update notification | `id` (path) + `NotificationUpdate` body | `NotificationResponse` |
| 5 | DELETE | `/api/T0098I/{id}` | Delete notification | `id` (path) | 204 |
| 6 | PUT | `/api/T0098I/{id}/read` | Mark single notification as read | `id` (path) | `{ok: bool}` |
| 7 | PUT | `/api/T0098I/read-all/{user_id}` | Mark all notifications as read for user | `user_id` (path) | `{ok: bool}` |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`

# AdminView — Field Reference

## UserResponse (API response)

| Field | Type | Max Length | Notes |
|---|---|---|---|
| id | int | — | Primary key |
| username | string | 50 | Required; unique |
| full_name | string? | 200 | Optional |
| email | string? | 200 | Optional |
| role | string | — | One of: Admin, Manager, Viewer |
| permissions | string[] | — | Array of permission keys |
| status | string | — | Active or Inactive |
| last_login | datetime? | — | Null if never logged in |

## UserCreate (POST payload)

| Field | Type | Required | Default |
|---|---|---|---|
| username | string | Yes | — |
| password_hash | string | Yes | — |
| full_name | string? | No | null |
| email | string? | No | null |
| role | string | No | Viewer |
| permissions | string[] | No | [] |
| status | string | No | Active |

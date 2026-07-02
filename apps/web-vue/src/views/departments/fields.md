# Fields — Departments

## Database columns (`Nova.T0028`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| department_code | `VARCHAR(20)` | Yes | — | Unique department code |
| department_name | `VARCHAR(100)` | Yes | — | Department display name |
| parent_id | `INT` | No | — | Reference to parent department |
| manager_id | `INT` | No | — | Reference to employee (manager) |
| is_active | `BOOLEAN` | No | TRUE | Soft-delete flag |

## Pydantic models

### `DepartmentCreate`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| department_code | `str` | Yes | Max 20 |
| department_name | `str` | Yes | Max 100 |
| parent_id | `int?` | No | — |
| manager_id | `int?` | No | — |

### `DepartmentUpdate`
All fields Optional.

### `DepartmentResponse`
Extends `AuditMixin`.

# Fields — Employees

## Database columns (`Nova.T0030`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| employee_code | `VARCHAR(30)` | Yes | — | Unique employee code |
| full_name | `VARCHAR(200)` | Yes | — | Full name (English) |
| arabic_name | `VARCHAR(200)` | No | — | Name in Arabic |
| email | `VARCHAR(100)` | No | — | Work email |
| phone | `VARCHAR(30)` | No | — | Phone number |
| address | `TEXT` | No | — | Residential address |
| national_id | `VARCHAR(30)` | No | — | National ID / SSN |
| passport_no | `VARCHAR(30)` | No | — | Passport number |
| gender | `VARCHAR(10)` | No | — | Male / Female |
| marital_status | `VARCHAR(20)` | No | — | Single, Married, Divorced, Widowed |
| birth_date | `DATE` | No | — | Date of birth |
| hire_date | `DATE` | No | — | Date of hire |
| termination_date | `DATE` | No | — | Date of termination |
| employment_status | `VARCHAR(20)` | No | `'Active'` | Active, Terminated, Suspended, Resigned |
| department_id | `INT` | No | — | FK to T0028 (Department) |
| designation_id | `INT` | No | — | FK to T0029 (Designation) |
| manager_id | `INT` | No | — | FK to T0030 (Manager) |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### EmployeeCreate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| employee_code | `str` | Yes | Max 30 chars |
| full_name | `str` | Yes | Max 200 chars |
| arabic_name | `Optional[str]` | No | Max 200 chars |
| email | `Optional[str]` | No | Max 100 chars |
| phone | `Optional[str]` | No | Max 30 chars |
| address | `Optional[str]` | No | Free text |
| national_id | `Optional[str]` | No | Max 30 chars |
| passport_no | `Optional[str]` | No | Max 30 chars |
| gender | `Optional[str]` | No | Max 10 chars |
| marital_status | `Optional[str]` | No | Max 20 chars |
| birth_date | `Optional[date]` | No | — |
| hire_date | `Optional[date]` | No | — |
| termination_date | `Optional[date]` | No | — |
| employment_status | `str` | No | Default: `'Active'` |
| department_id | `Optional[int]` | No | FK to T0028 |
| designation_id | `Optional[int]` | No | FK to T0029 |
| manager_id | `Optional[int]` | No | FK to T0030 |
| is_active | `bool` | No | Default: `True` |

### EmployeeUpdate
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| All fields | `Optional` | No | Partial update supported |

### EmployeeResponse
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.

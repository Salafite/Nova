# Employees

**Program code:** `T0030` (Employee)

## Purpose
Manage employee records — personal information, employment details, and organizational assignments. Supports bilingual names (English/Arabic), document tracking, and contract management.

## How to access
1. Log in to Nova ERP
2. Navigate to **HR & Organization > Employees** in the sidebar
3. The screen loads at `#/employees`

## Backing table
`Nova.T0030` — stores all employee records.

## API prefix
`/api/T0030I`

## Permissions
- **Full access**: Admin, HR Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: Departments (T0028), Designations (T0029)
- Used by: Payroll, Attendance, Leave Management

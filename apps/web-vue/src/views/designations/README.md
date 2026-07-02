# Designations

**Program code:** `T0029` (Designation)

## Purpose
Manage job designations/titles used across the organization. Each designation belongs to a department and defines a position hierarchy.

## How to access
1. Log in to Nova ERP
2. Navigate to **HR & Organization > Designations** in the sidebar
3. The screen loads at `#/designations`

## Backing table
`Nova.T0029` — stores all designation records.

## API prefix
`/api/T0029I`

## Permissions
- **Full access**: Admin, HR Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: Departments (T0028)
- Used by: Employees (T0030)

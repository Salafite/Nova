# Departments

**Program code:** `T0028` — Departments

## Purpose
Manage organizational departments and hierarchy, with parent department and manager assignments.

## How to access
1. Log in to Nova ERP
2. Navigate to **HR & Organization > Departments** in the sidebar
3. The screen loads at `#/departments`

## Backing table
`Nova.T0028` — stores all department records.

## API prefix
`/api/T0028I`

## Permissions
- **Full access**: Admin, Manager
- **Read only**: Viewer

## Dependencies
- Depends on: Employees (for manager assignment)
- Used by: Employees, Job Openings

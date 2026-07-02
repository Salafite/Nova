# Suppliers

**Program code:** `T0011` (Suppliers)

## Purpose
Manage supplier information including contact details, payment terms, and ratings. Suppliers are used in purchase orders and procurement.

## How to access
1. Log in to Nova ERP
2. Navigate to **CRM & Procurement > Suppliers** in the sidebar
3. The screen loads at `#/suppliers`

## Backing table
`Nova.T0011` — stores all supplier records.

## API prefix
`/api/T0011I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Referenced by: T0014 (Purchase Orders)

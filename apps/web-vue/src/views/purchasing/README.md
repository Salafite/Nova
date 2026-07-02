# Purchase Orders

**Program code:** `T0014` (Purchase Orders)

## Purpose
Manage purchase orders to suppliers. Track PO status, amounts, and expected delivery dates.

## How to access
1. Log in to Nova ERP
2. Navigate to **CRM & Procurement > Purchasing** in the sidebar
3. The screen loads at `#/purchasing`

## Backing table
`Nova.T0014` — stores all purchase order records.

## API prefix
`/api/T0014I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: T0011 (Suppliers)
- Contains: T0015 (Purchase Order Lines)

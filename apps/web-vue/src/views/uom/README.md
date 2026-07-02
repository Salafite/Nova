# Units of Measure

**Program code:** `T0001` — UOM

## Purpose
Manage units of measure used across the system — define UOM codes, names, categories, and designate base units for each category. UOMs are used in product definitions, inventory transactions, and purchasing.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > UOM** in the sidebar
3. The screen loads at `#/uom`

## Backing table
`Nova.T0001` — stores all UOM records.

## API prefix
`/api/T0001I`

## Permissions
- **Full access**: Admin, Inventory Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: None (standalone reference table)
- Used by: Products, Inventory transactions

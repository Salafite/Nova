# Stock Levels (Inventory)

**Program code:** `T0009` (Stock Levels)

## Purpose
View current stock levels for every product in every warehouse. Shows quantity on hand, reorder levels, and stock status (OK, Low, Out). Highlighted rows indicate products that need reordering.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > Stock Levels** in the sidebar
3. The screen loads at `#/inventory`

## Backing table
`Nova.T0009` — stores current stock level per product per warehouse.

## API prefix
`/api/T0009I`

## Permissions
- **Full access**: Admin, Manager (can view and manage)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: T0003 (Products), T0008 (Warehouses)
- Updated by: T0064 (Stock Movements) via `StockMovementService`

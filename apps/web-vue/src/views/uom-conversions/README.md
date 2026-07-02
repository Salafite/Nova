# UOM Conversions

**Program code:** `T0002` (UOM Conversion)

## Purpose
Manage conversion factors between units of measure (e.g., 1 kg = 1000 g). Each conversion links a `from_uom` to a `to_uom` with a multiplicative factor. Used throughout the system for automatic unit conversion in purchasing, sales, and inventory.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > UOM Conversions** in the sidebar
3. The screen loads at `#/uom-conversions`

## Backing table
`Nova.T0002` — stores all UOM conversion factor records.

## API prefix
`/api/T0002I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Depends on: T0001 (UOM)

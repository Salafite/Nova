# Attributes

**Program code:** `T0005` (Attribute Definitions)

## Purpose
Define product attributes such as size, color, material, etc. Each attribute has a type (Text, Number, Date, Boolean, Select) that determines how values are entered for each product.

## How to access
1. Log in to Nova ERP
2. Navigate to **Foundation > Attributes** in the sidebar
3. The screen loads at `#/attributes`

## Backing table
`Nova.T0005` — stores attribute definition records.

## API prefix
`/api/T0005I`

## Permissions
- **Full access**: Admin, Manager (can create, edit, delete)
- **Read only**: Viewer (can view only)

## Dependencies
- Used by: T0006 (Attribute Values) — linked to products via EAV pattern

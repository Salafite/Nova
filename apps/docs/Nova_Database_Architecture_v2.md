# Nova Database Architecture v2

## Goals

-   Single PostgreSQL database
-   Modular schemas per business domain
-   UUID primary keys
-   Multi-tenant ready
-   Audit columns on business tables

## Schemas

core, auth, admin, inventory, warehouse, purchasing, suppliers, crm,
sales, accounting, manufacturing, quality, maintenance, hr, projects,
analytics, audit

## Conventions

-   PK: UUID
-   FK with ON UPDATE CASCADE
-   Soft delete (`is_deleted`)
-   `created_at`, `updated_at`, `created_by`, `updated_by`
-   Version column for optimistic locking

## Database Objects

-   Tables
-   Views
-   Materialized Views
-   Stored Procedures
-   Functions
-   Triggers
-   Indexes
-   Partitions (audit/history)

## Migration Layout

database/ - migrations/ - seeds/ - functions/ - views/ - triggers/ -
indexes/

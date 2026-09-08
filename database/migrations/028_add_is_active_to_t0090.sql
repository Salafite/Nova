-- Nova ERP — Add is_active column to T0090 (Invoices / Debit Memos)
-- The CrudRepository for T0090 expects is_active in business_columns,
-- which causes queries to filter on it. This migration ensures the column exists.
BEGIN;

ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

COMMIT;

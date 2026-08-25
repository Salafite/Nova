-- Nova ERP — Automated Customer Credit Limits & Financial Hold Workflows Migration
-- Migration 022: Add 'Credit Hold' to order_status enum and hold tracking columns to Sales Orders (t0012)
BEGIN;

-- 1. Add 'Credit Hold' to order_status enum
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Credit Hold';

-- 2. Add credit hold tracking columns to Sales Orders (t0012)
ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS hold_reason TEXT,
    ADD COLUMN IF NOT EXISTS hold_released_by INT REFERENCES "Nova".t0021(id),
    ADD COLUMN IF NOT EXISTS hold_released_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS hold_release_reason TEXT;

-- 3. Comments describing credit hold workflow columns
COMMENT ON COLUMN "Nova".t0012.hold_reason IS 'Reason why sales order was placed on credit hold (e.g. credit limit exceeded, overdue invoices)';
COMMENT ON COLUMN "Nova".t0012.hold_released_by IS 'Authorized manager who approved/released credit hold override (FK to t0021)';
COMMENT ON COLUMN "Nova".t0012.hold_released_at IS 'Timestamp when credit hold was overridden and released';
COMMENT ON COLUMN "Nova".t0012.hold_release_reason IS 'Manager rationale / reason for releasing the credit hold';

-- 4. Indexes for hold tracking and reporting
CREATE INDEX IF NOT EXISTS idx_t0012_hold_released_by ON "Nova".t0012(hold_released_by);

-- 5. Grant permissions to nova_readonly role if present
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT (hold_reason, hold_released_by, hold_released_at, hold_release_reason) ON "Nova".t0012 TO nova_readonly;
    END IF;
END $$;

COMMIT;

-- Nova ERP — Field Sales Representative Mobile & Offline Order Entry Migration
BEGIN;

-- 1. Add offline synchronization and sales rep tracking columns to Sales Orders (t0012)
ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS client_order_uuid VARCHAR(64) UNIQUE,
    ADD COLUMN IF NOT EXISTS is_offline_sync BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(30) NOT NULL DEFAULT 'Synced',
    ADD COLUMN IF NOT EXISTS offline_created_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS sales_rep_id INT REFERENCES "Nova".t0021(id);

COMMENT ON COLUMN "Nova".t0012.client_order_uuid IS 'Client-generated UUID for offline order creation, duplicate prevention, and idempotency';
COMMENT ON COLUMN "Nova".t0012.is_offline_sync IS 'Flag indicating if order was created offline and synced later';
COMMENT ON COLUMN "Nova".t0012.sync_status IS 'Synchronization status: Synced, Pending, Conflict, Failed';
COMMENT ON COLUMN "Nova".t0012.offline_created_at IS 'Device timestamp when order was created while offline';
COMMENT ON COLUMN "Nova".t0012.sales_rep_id IS 'Field sales representative who created the order (FK to t0021)';

-- 2. Indexes for fast sync queries, UUID lookup, and rep filtering
CREATE UNIQUE INDEX IF NOT EXISTS idx_t0012_client_order_uuid ON "Nova".t0012(client_order_uuid);
CREATE INDEX IF NOT EXISTS idx_t0012_sales_rep ON "Nova".t0012(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0012_sync_status ON "Nova".t0012(sync_status);

COMMIT;

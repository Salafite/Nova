-- Nova ERP — Legacy Database Connector & Migration Engine Schema Extensions
BEGIN;

-- 1. Extend Nova.t0104 with source_type, connection_config, dry_run_completed, reconciliation_summary, execution_log, and error_details
ALTER TABLE "Nova".t0104
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) NOT NULL DEFAULT 'csv_dump',
    ADD COLUMN IF NOT EXISTS connection_config JSONB,
    ADD COLUMN IF NOT EXISTS dry_run_completed BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS reconciliation_summary JSONB,
    ADD COLUMN IF NOT EXISTS execution_log JSONB,
    ADD COLUMN IF NOT EXISTS error_details JSONB;

COMMENT ON COLUMN "Nova".t0104.source_type IS 'Source connector type: sqlserver | csv_dump | mysql | postgres';
COMMENT ON COLUMN "Nova".t0104.connection_config IS 'Legacy connection parameters and dataset metadata (JSON)';
COMMENT ON COLUMN "Nova".t0104.dry_run_completed IS 'Flag indicating if dry run simulation passed';
COMMENT ON COLUMN "Nova".t0104.reconciliation_summary IS 'Opening balance, inventory, and entity reconciliation metrics (JSON)';
COMMENT ON COLUMN "Nova".t0104.execution_log IS 'Step-by-step execution and timing logs (JSON)';
COMMENT ON COLUMN "Nova".t0104.error_details IS 'Row-level and schema translation error details (JSON)';

CREATE INDEX IF NOT EXISTS idx_t0104_source_type ON "Nova".t0104(source_type);

-- 2. Create Nova.t0104_items to track individual migrated records for safe atomic rollback
CREATE TABLE IF NOT EXISTS "Nova".t0104_items (
    id              SERIAL PRIMARY KEY,
    batch_id        INT NOT NULL REFERENCES "Nova".t0104(id) ON DELETE CASCADE,
    entity_type     VARCHAR(50) NOT NULL,
    target_table    VARCHAR(50) NOT NULL,
    target_id       INT NOT NULL,
    source_key      VARCHAR(255),
    status          VARCHAR(30) NOT NULL DEFAULT 'Inserted',
    business_id     INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE "Nova".t0104_items IS 'Individual migrated records per batch for safe atomic rollback';
COMMENT ON COLUMN "Nova".t0104_items.batch_id IS 'Migration batch identifier (FK to T0104)';
COMMENT ON COLUMN "Nova".t0104_items.entity_type IS 'Logical entity name (e.g. products, customers, invoices)';
COMMENT ON COLUMN "Nova".t0104_items.target_table IS 'Target Nova table name (e.g. t0003, t0010)';
COMMENT ON COLUMN "Nova".t0104_items.target_id IS 'Primary key of inserted record in target table';
COMMENT ON COLUMN "Nova".t0104_items.source_key IS 'Original identifier or PK from legacy database/file';
COMMENT ON COLUMN "Nova".t0104_items.status IS 'Status of migrated item: Inserted | RolledBack';
COMMENT ON COLUMN "Nova".t0104_items.business_id IS 'Tenant / business organization identifier (FK to T0059)';

CREATE INDEX IF NOT EXISTS idx_t0104_items_batch_id ON "Nova".t0104_items(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_batch_target ON "Nova".t0104_items(batch_id, target_table, target_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_business_id ON "Nova".t0104_items(business_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_business_id_id ON "Nova".t0104_items(business_id, id);

COMMIT;

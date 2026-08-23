-- T0098 - User Notifications
CREATE TABLE IF NOT EXISTS "Nova".T0098 (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "Nova".T0021(id),
    title VARCHAR(200) NOT NULL,
    message TEXT,
    notification_type VARCHAR(30) NOT NULL DEFAULT 'Info',
    reference_type VARCHAR(30),
    reference_id INT,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE "Nova".T0098 IS 'User Notifications - in-app notification system';
COMMENT ON COLUMN "Nova".T0098.id IS 'Primary key';
COMMENT ON COLUMN "Nova".T0098.user_id IS 'Recipient user (FK to T0021)';
COMMENT ON COLUMN "Nova".T0098.title IS 'Notification title';
COMMENT ON COLUMN "Nova".T0098.message IS 'Detailed notification message';
COMMENT ON COLUMN "Nova".T0098.notification_type IS 'Info, Success, Warning, Error';
COMMENT ON COLUMN "Nova".T0098.reference_type IS 'Related entity type (e.g. SalesOrder)';
COMMENT ON COLUMN "Nova".T0098.reference_id IS 'Related entity ID';
COMMENT ON COLUMN "Nova".T0098.is_read IS 'Read status flag';
COMMENT ON COLUMN "Nova".T0098.created_at IS 'Creation timestamp';
CREATE INDEX IF NOT EXISTS idx_T0098_user ON "Nova".T0098(user_id);
CREATE INDEX IF NOT EXISTS idx_T0098_read ON "Nova".T0098(is_read);

-- T0099 - Scheduled Tasks
CREATE TABLE IF NOT EXISTS "Nova".T0099 (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    cron_expression VARCHAR(50) NOT NULL,
    description TEXT,
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'Idle',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ,
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".T0099 IS 'Scheduled Tasks - cron-based job scheduling';
COMMENT ON COLUMN "Nova".T0099.id IS 'Primary key';
COMMENT ON COLUMN "Nova".T0099.task_name IS 'Human-readable task name';
COMMENT ON COLUMN "Nova".T0099.task_type IS 'Task type (EmailReport, CleanupLogs, SyncData, GenerateInvoice)';
COMMENT ON COLUMN "Nova".T0099.cron_expression IS 'Standard cron expression (e.g. 0 0 * * *)';
COMMENT ON COLUMN "Nova".T0099.description IS 'Task description';
COMMENT ON COLUMN "Nova".T0099.config IS 'Task configuration as JSON';
COMMENT ON COLUMN "Nova".T0099.is_active IS 'Enable/disable the task schedule';
COMMENT ON COLUMN "Nova".T0099.last_run_at IS 'Timestamp of last execution';
COMMENT ON COLUMN "Nova".T0099.next_run_at IS 'Scheduled next execution';
COMMENT ON COLUMN "Nova".T0099.status IS 'Idle, Running, Failed, Completed';
CREATE INDEX IF NOT EXISTS idx_T0099_active ON "Nova".T0099(is_active);
CREATE INDEX IF NOT EXISTS idx_T0099_status ON "Nova".T0099(status);
CREATE INDEX IF NOT EXISTS idx_T0099_next_run ON "Nova".T0099(next_run_at);

-- T0100 - Module Registry
CREATE TABLE IF NOT EXISTS "Nova".t0100 (
    id SERIAL PRIMARY KEY,
    module_key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100),
    description TEXT,
    description_ar TEXT,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    author VARCHAR(200),
    icon VARCHAR(50),
    category VARCHAR(50),
    is_core BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    installed_at TIMESTAMPTZ,
    dependencies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT REFERENCES "Nova".t0021(id),
    updated_at TIMESTAMPTZ,
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0100 IS 'Module Registry - tracks installed/enabled modules';
COMMENT ON COLUMN "Nova".t0100.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0100.module_key IS 'Unique module key (directory name)';
COMMENT ON COLUMN "Nova".t0100.name IS 'Display name in English';
COMMENT ON COLUMN "Nova".t0100.name_ar IS 'Display name in Arabic';
COMMENT ON COLUMN "Nova".t0100.description IS 'Module description in English';
COMMENT ON COLUMN "Nova".t0100.description_ar IS 'Module description in Arabic';
COMMENT ON COLUMN "Nova".t0100.version IS 'Semantic version';
COMMENT ON COLUMN "Nova".t0100.author IS 'Module author';
COMMENT ON COLUMN "Nova".t0100.icon IS 'Material Symbols icon name';
COMMENT ON COLUMN "Nova".t0100.category IS 'Functional category (P0, P1, P2, supporting)';
COMMENT ON COLUMN "Nova".t0100.is_core IS 'Core module cannot be uninstalled/disabled';
COMMENT ON COLUMN "Nova".t0100.is_active IS 'Module is currently enabled';
COMMENT ON COLUMN "Nova".t0100.installed_at IS 'When the module was installed';
COMMENT ON COLUMN "Nova".t0100.dependencies IS 'List of module_key dependencies';
CREATE INDEX IF NOT EXISTS idx_t0100_key ON "Nova".t0100(module_key);
CREATE INDEX IF NOT EXISTS idx_t0100_active ON "Nova".t0100(is_active);
CREATE INDEX IF NOT EXISTS idx_t0100_category ON "Nova".t0100(category);

-- T0104 - Legacy Migration Batches
CREATE TABLE IF NOT EXISTS "Nova".t0104 (
    id                     SERIAL PRIMARY KEY,
    batch_key              VARCHAR(64) NOT NULL UNIQUE,
    entity_type            VARCHAR(30) NOT NULL,
    source_type            VARCHAR(50) NOT NULL DEFAULT 'csv_dump',
    total_rows             INT NOT NULL DEFAULT 0,
    inserted_rows          INT NOT NULL DEFAULT 0,
    status                 VARCHAR(20) NOT NULL DEFAULT 'Preview',
    dry_run_completed      BOOLEAN NOT NULL DEFAULT false,
    connection_config      JSONB,
    reconciliation_summary JSONB,
    execution_log          JSONB,
    error_details          JSONB,
    business_id            INT REFERENCES "Nova".t0059(id),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             INT REFERENCES "Nova".t0021(id),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by             INT REFERENCES "Nova".t0021(id),
    update_number          INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0104 IS 'Migration batches for tracking legacy migrations and CSV imports';
COMMENT ON COLUMN "Nova".t0104.id                     IS 'Primary key';
COMMENT ON COLUMN "Nova".t0104.batch_key              IS 'Unique batch identifier / UUID';
COMMENT ON COLUMN "Nova".t0104.entity_type            IS 'Logical entity or dataset type';
COMMENT ON COLUMN "Nova".t0104.source_type            IS 'Source connector type: sqlserver | csv_dump | mysql | postgres';
COMMENT ON COLUMN "Nova".t0104.total_rows             IS 'Total number of extracted rows';
COMMENT ON COLUMN "Nova".t0104.inserted_rows          IS 'Count of successfully committed rows';
COMMENT ON COLUMN "Nova".t0104.status                 IS 'Preview | Committed | RolledBack';
COMMENT ON COLUMN "Nova".t0104.dry_run_completed      IS 'Flag indicating if dry-run simulation passed';
COMMENT ON COLUMN "Nova".t0104.connection_config      IS 'Legacy connection parameters and dataset metadata (JSON)';
COMMENT ON COLUMN "Nova".t0104.reconciliation_summary IS 'Opening balance, inventory, and entity reconciliation metrics (JSON)';
COMMENT ON COLUMN "Nova".t0104.execution_log          IS 'Step-by-step execution and timing logs (JSON)';
COMMENT ON COLUMN "Nova".t0104.error_details          IS 'Row-level and schema translation error details (JSON)';
COMMENT ON COLUMN "Nova".t0104.business_id            IS 'Tenant / business organization identifier (FK to T0059)';
COMMENT ON COLUMN "Nova".t0104.created_at             IS 'Record creation timestamp';
COMMENT ON COLUMN "Nova".t0104.created_by             IS 'User who created this batch (FK to T0021)';
COMMENT ON COLUMN "Nova".t0104.updated_at             IS 'Last modification timestamp';
COMMENT ON COLUMN "Nova".t0104.updated_by             IS 'User who last modified this batch (FK to T0021)';
COMMENT ON COLUMN "Nova".t0104.update_number          IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX IF NOT EXISTS idx_t0104_batch_key ON "Nova".t0104(batch_key);
CREATE INDEX IF NOT EXISTS idx_t0104_business_id ON "Nova".t0104(business_id);
CREATE INDEX IF NOT EXISTS idx_t0104_business_id_id ON "Nova".t0104(business_id, id);
CREATE INDEX IF NOT EXISTS idx_t0104_source_type ON "Nova".t0104(source_type);

-- T0104_items - Migration Batch Items
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
COMMENT ON COLUMN "Nova".t0104_items.id           IS 'Primary key';
COMMENT ON COLUMN "Nova".t0104_items.batch_id     IS 'Migration batch identifier (FK to T0104)';
COMMENT ON COLUMN "Nova".t0104_items.entity_type  IS 'Logical entity name (e.g. products, customers, invoices)';
COMMENT ON COLUMN "Nova".t0104_items.target_table IS 'Target Nova table name (e.g. t0003, t0010)';
COMMENT ON COLUMN "Nova".t0104_items.target_id    IS 'Primary key of inserted record in target table';
COMMENT ON COLUMN "Nova".t0104_items.source_key   IS 'Original identifier or PK from legacy database/file';
COMMENT ON COLUMN "Nova".t0104_items.status       IS 'Status of migrated item: Inserted | RolledBack';
COMMENT ON COLUMN "Nova".t0104_items.business_id  IS 'Tenant / business organization identifier (FK to T0059)';
COMMENT ON COLUMN "Nova".t0104_items.created_at   IS 'Record creation timestamp';

CREATE INDEX IF NOT EXISTS idx_t0104_items_batch_id ON "Nova".t0104_items(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_batch_target ON "Nova".t0104_items(batch_id, target_table, target_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_business_id ON "Nova".t0104_items(business_id);
CREATE INDEX IF NOT EXISTS idx_t0104_items_business_id_id ON "Nova".t0104_items(business_id, id);


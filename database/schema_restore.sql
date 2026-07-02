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

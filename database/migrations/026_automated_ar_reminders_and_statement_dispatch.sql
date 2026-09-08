-- Nova ERP — Automated AR Collection Reminders & Statement Dispatch via WhatsApp/Email
-- Migration 026: AR Reminder Rules (t0120_ar_reminder_rules),
--                AR Reminder Templates (t0121_ar_reminder_templates),
--                Customer Communication Logs (t0122_customer_communications),
--                Customer Reminders Preference Extension (t0010)
BEGIN;

-- 1. Sequences for Rules and Communication Tracking Numbers
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_ar_reminder_rule_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_ar_reminder_rule_code IS 'Atomic sequence for generating unique AR reminder rule codes (RULE-AR-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_customer_comm_tracking START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_customer_comm_tracking IS 'Atomic sequence for generating unique customer communication tracking IDs (COMM-XXXXX)';

-- 2. AR Reminder Templates Table (t0121_ar_reminder_templates)
CREATE TABLE IF NOT EXISTS "Nova".t0121_ar_reminder_templates (
    id                      SERIAL PRIMARY KEY,
    template_code           VARCHAR(50) NOT NULL UNIQUE,
    template_name           VARCHAR(100) NOT NULL,
    channel                 VARCHAR(30) NOT NULL DEFAULT 'EMAIL',
    subject_template        VARCHAR(255),
    body_template           TEXT NOT NULL,
    whatsapp_template_name  VARCHAR(100),
    whatsapp_namespace      VARCHAR(100),
    language                VARCHAR(10) NOT NULL DEFAULT 'en',
    is_default              BOOLEAN NOT NULL DEFAULT false,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    description             TEXT,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0121_ar_reminder_templates IS 'AR Reminder Templates — Email & WhatsApp message templates with dynamic merge variables';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.template_code IS 'Unique code identifier for template (e.g. TMPL-REMINDER-30D, TMPL-STMT-WEEKLY)';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.template_name IS 'Descriptive name of the template';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.channel IS 'Dispatch channel: EMAIL | WHATSAPP | SMS';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.subject_template IS 'Email subject line template supporting {{variable}} placeholders';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.body_template IS 'Message body template text with merge tags ({{customer_name}}, {{total_balance}}, {{overdue_amount}}, etc.)';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.whatsapp_template_name IS 'Pre-approved WhatsApp Business API template name';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.whatsapp_namespace IS 'WhatsApp Business template namespace';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.language IS 'Template language code (e.g. en, ar, es)';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.is_default IS 'Flag indicating if template is default for its channel and trigger type';
COMMENT ON COLUMN "Nova".t0121_ar_reminder_templates.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0121_template_code ON "Nova".t0121_ar_reminder_templates(template_code);
CREATE INDEX IF NOT EXISTS idx_t0121_channel ON "Nova".t0121_ar_reminder_templates(channel);
CREATE INDEX IF NOT EXISTS idx_t0121_business_id ON "Nova".t0121_ar_reminder_templates(business_id);
CREATE INDEX IF NOT EXISTS idx_t0121_business_id_id ON "Nova".t0121_ar_reminder_templates(business_id, id);

-- 3. AR Reminder Rules Table (t0120_ar_reminder_rules)
CREATE TABLE IF NOT EXISTS "Nova".t0120_ar_reminder_rules (
    id                      SERIAL PRIMARY KEY,
    rule_name               VARCHAR(100) NOT NULL,
    rule_code               VARCHAR(50) NOT NULL UNIQUE,
    trigger_type            VARCHAR(50) NOT NULL DEFAULT 'AGING_THRESHOLD',
    threshold_days          INT NOT NULL DEFAULT 30,
    frequency               VARCHAR(30) NOT NULL DEFAULT 'ONCE',
    schedule_day            VARCHAR(20),
    schedule_time           TIME DEFAULT '09:00:00',
    channel                 VARCHAR(30) NOT NULL DEFAULT 'ALL',
    template_id             INT REFERENCES "Nova".t0121_ar_reminder_templates(id) ON DELETE SET NULL,
    attach_statement_pdf    BOOLEAN NOT NULL DEFAULT true,
    include_payment_link    BOOLEAN NOT NULL DEFAULT true,
    min_overdue_balance     NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    exclude_vip             BOOLEAN NOT NULL DEFAULT true,
    exclude_credit_hold     BOOLEAN NOT NULL DEFAULT false,
    customer_group          VARCHAR(100),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    description             TEXT,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0120_ar_reminder_rules IS 'AR Reminder Rules — Configurable automated reminder evaluation rules and aging schedules';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.rule_name IS 'Descriptive human-readable rule name';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.rule_code IS 'Unique code identifier (e.g. RULE-OVERDUE-30D, RULE-STMT-WEEKLY)';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.trigger_type IS 'Trigger type: AGING_THRESHOLD | DUE_DATE_OFFSET | STATEMENT_SCHEDULE | MANUAL';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.threshold_days IS 'Days threshold for aging trigger (e.g. 30, 60, 90) or offset days relative to due date (-3, 0)';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.frequency IS 'Evaluation/dispatch recurrence: ONCE | DAILY | WEEKLY | MONTHLY';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.schedule_day IS 'Day of week for recurring statement schedule (e.g. MONDAY, FRIDAY)';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.schedule_time IS 'Time of day when the automated dispatch evaluates';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.channel IS 'Communication channel: EMAIL | WHATSAPP | ALL | SMS';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.template_id IS 'Linked default message template (FK to t0121_ar_reminder_templates)';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.attach_statement_pdf IS 'Whether to automatically generate and attach account statement PDF';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.include_payment_link IS 'Whether to interpolate instant online payment checkout link';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.min_overdue_balance IS 'Minimum overdue amount required to qualify for trigger';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.exclude_vip IS 'Whether to suppress automated reminders for VIP customer accounts';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.exclude_credit_hold IS 'Whether to skip customers who are already on credit hold';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.customer_group IS 'Optional filter for customer category / group (NULL applies to all)';
COMMENT ON COLUMN "Nova".t0120_ar_reminder_rules.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0120_rule_code ON "Nova".t0120_ar_reminder_rules(rule_code);
CREATE INDEX IF NOT EXISTS idx_t0120_trigger_type ON "Nova".t0120_ar_reminder_rules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_t0120_threshold_days ON "Nova".t0120_ar_reminder_rules(threshold_days);
CREATE INDEX IF NOT EXISTS idx_t0120_business_id ON "Nova".t0120_ar_reminder_rules(business_id);
CREATE INDEX IF NOT EXISTS idx_t0120_business_id_id ON "Nova".t0120_ar_reminder_rules(business_id, id);

-- 4. Customer Communications Table (t0122_customer_communications)
CREATE TABLE IF NOT EXISTS "Nova".t0122_customer_communications (
    id                      SERIAL PRIMARY KEY,
    tracking_number         VARCHAR(50) NOT NULL UNIQUE,
    customer_id             INT NOT NULL REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    rule_id                 INT REFERENCES "Nova".t0120_ar_reminder_rules(id) ON DELETE SET NULL,
    template_id             INT REFERENCES "Nova".t0121_ar_reminder_templates(id) ON DELETE SET NULL,
    channel                 VARCHAR(30) NOT NULL,
    communication_type      VARCHAR(50) NOT NULL DEFAULT 'REMINDER',
    recipient_address       VARCHAR(255) NOT NULL,
    recipient_name          VARCHAR(200),
    subject                 VARCHAR(255),
    message_body            TEXT NOT NULL,
    status                  VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    delivery_timestamp      TIMESTAMPTZ,
    read_timestamp          TIMESTAMPTZ,
    error_message           TEXT,
    external_message_id     VARCHAR(255),
    statement_pdf_path      VARCHAR(500),
    statement_pdf_size      INT,
    invoice_count           INT DEFAULT 0,
    total_balance           NUMERIC(12,2) DEFAULT 0.00,
    overdue_amount          NUMERIC(12,2) DEFAULT 0.00,
    payment_link            TEXT,
    dispatched_by           INT REFERENCES "Nova".t0021(id),
    is_automated            BOOLEAN NOT NULL DEFAULT true,
    metadata                JSONB,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0122_customer_communications IS 'Customer Communications — Audit timeline log of all dispatched reminders, statements, and delivery statuses';
COMMENT ON COLUMN "Nova".t0122_customer_communications.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0122_customer_communications.tracking_number IS 'Unique communication tracking reference code (COMM-XXXXX)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.customer_id IS 'Target customer account reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.rule_id IS 'Triggering AR reminder rule reference (FK to t0120_ar_reminder_rules, NULL for manual)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.template_id IS 'Message template reference used for rendering (FK to t0121_ar_reminder_templates)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.channel IS 'Delivery channel: EMAIL | WHATSAPP | SMS';
COMMENT ON COLUMN "Nova".t0122_customer_communications.communication_type IS 'Type: REMINDER | STATEMENT | INVOICE_LINK | MANUAL_MESSAGE | PAYMENT_RECEIPT';
COMMENT ON COLUMN "Nova".t0122_customer_communications.recipient_address IS 'Destination email address or E.164 formatted WhatsApp/phone number';
COMMENT ON COLUMN "Nova".t0122_customer_communications.recipient_name IS 'Recipient customer or contact person name';
COMMENT ON COLUMN "Nova".t0122_customer_communications.subject IS 'Email subject line (NULL for WhatsApp)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.message_body IS 'Final rendered message body sent to recipient';
COMMENT ON COLUMN "Nova".t0122_customer_communications.status IS 'Dispatch lifecycle status: PENDING | SENT | DELIVERED | READ | FAILED | CANCELLED';
COMMENT ON COLUMN "Nova".t0122_customer_communications.delivery_timestamp IS 'Timestamp when delivery receipt was confirmed via webhook';
COMMENT ON COLUMN "Nova".t0122_customer_communications.read_timestamp IS 'Timestamp when read receipt was confirmed via webhook';
COMMENT ON COLUMN "Nova".t0122_customer_communications.error_message IS 'Failure or rejection reason if delivery failed';
COMMENT ON COLUMN "Nova".t0122_customer_communications.external_message_id IS 'Third-party gateway ID (SendGrid msg ID, Twilio/WhatsApp SID)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.statement_pdf_path IS 'File storage path to generated statement PDF attachment';
COMMENT ON COLUMN "Nova".t0122_customer_communications.statement_pdf_size IS 'Size of generated statement PDF in bytes';
COMMENT ON COLUMN "Nova".t0122_customer_communications.invoice_count IS 'Number of open invoices included in statement snapshot';
COMMENT ON COLUMN "Nova".t0122_customer_communications.total_balance IS 'Customer total balance at time of dispatch';
COMMENT ON COLUMN "Nova".t0122_customer_communications.overdue_amount IS 'Customer overdue balance at time of dispatch';
COMMENT ON COLUMN "Nova".t0122_customer_communications.payment_link IS 'Direct payment checkout URL included in dispatch';
COMMENT ON COLUMN "Nova".t0122_customer_communications.dispatched_by IS 'User who manually initiated dispatch (NULL if automated background engine)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.is_automated IS 'Flag indicating whether dispatch was triggered automatically by scheduler';
COMMENT ON COLUMN "Nova".t0122_customer_communications.metadata IS 'Additional JSON payload metadata (webhook payloads, provider response, etc.)';
COMMENT ON COLUMN "Nova".t0122_customer_communications.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0122_tracking_number ON "Nova".t0122_customer_communications(tracking_number);
CREATE INDEX IF NOT EXISTS idx_t0122_customer_id ON "Nova".t0122_customer_communications(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0122_rule_id ON "Nova".t0122_customer_communications(rule_id);
CREATE INDEX IF NOT EXISTS idx_t0122_channel ON "Nova".t0122_customer_communications(channel);
CREATE INDEX IF NOT EXISTS idx_t0122_status ON "Nova".t0122_customer_communications(status);
CREATE INDEX IF NOT EXISTS idx_t0122_created_at ON "Nova".t0122_customer_communications(created_at);
CREATE INDEX IF NOT EXISTS idx_t0122_external_msg_id ON "Nova".t0122_customer_communications(external_message_id);
CREATE INDEX IF NOT EXISTS idx_t0122_business_id ON "Nova".t0122_customer_communications(business_id);
CREATE INDEX IF NOT EXISTS idx_t0122_business_id_id ON "Nova".t0122_customer_communications(business_id, id);
CREATE INDEX IF NOT EXISTS idx_t0122_business_customer ON "Nova".t0122_customer_communications(business_id, customer_id);

-- 5. Extend Customers Table (t0010) with Reminder Preferences and Dispatch Tracking
ALTER TABLE "Nova".t0010
    ADD COLUMN IF NOT EXISTS is_vip BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS exclude_from_reminders BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS preferred_reminder_channel VARCHAR(30) NOT NULL DEFAULT 'EMAIL',
    ADD COLUMN IF NOT EXISTS reminder_phone VARCHAR(50),
    ADD COLUMN IF NOT EXISTS reminder_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS last_reminder_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_statement_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN "Nova".t0010.is_vip IS 'Flag indicating VIP customer status to allow special white-glove treatment and rule-based reminder exclusion';
COMMENT ON COLUMN "Nova".t0010.exclude_from_reminders IS 'Flag to unconditionally suppress automated AR reminder dispatches for this customer';
COMMENT ON COLUMN "Nova".t0010.preferred_reminder_channel IS 'Customer preferred reminder channel: EMAIL | WHATSAPP | BOTH | NONE';
COMMENT ON COLUMN "Nova".t0010.reminder_phone IS 'Dedicated billing / WhatsApp mobile phone number for statements and payment reminders';
COMMENT ON COLUMN "Nova".t0010.reminder_email IS 'Dedicated accounts payable email address for statements and payment reminders';
COMMENT ON COLUMN "Nova".t0010.last_reminder_sent_at IS 'Timestamp of most recent collection reminder sent to this customer';
COMMENT ON COLUMN "Nova".t0010.last_statement_sent_at IS 'Timestamp of most recent account statement sent to this customer';

CREATE INDEX IF NOT EXISTS idx_t0010_exclude_reminders ON "Nova".t0010(exclude_from_reminders);
CREATE INDEX IF NOT EXISTS idx_t0010_is_vip ON "Nova".t0010(is_vip);
CREATE INDEX IF NOT EXISTS idx_t0010_pref_channel ON "Nova".t0010(preferred_reminder_channel);

-- 6. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0120_ar_reminder_rules TO nova_readonly;
        GRANT SELECT ON "Nova".t0121_ar_reminder_templates TO nova_readonly;
        GRANT SELECT ON "Nova".t0122_customer_communications TO nova_readonly;
        GRANT SELECT (is_vip, exclude_from_reminders, preferred_reminder_channel, reminder_phone, reminder_email, last_reminder_sent_at, last_statement_sent_at) ON "Nova".t0010 TO nova_readonly;
    END IF;
END $$;

COMMIT;

-- Nova ERP — Full Schema Migration
-- Run against an empty PostgreSQL database with a user that has CREATE privileges.
-- Creates the "Nova" schema and all business tables.

BEGIN;

-- Create the Nova schema if it does not exist
CREATE SCHEMA IF NOT EXISTS "Nova";

-- ============================================================
-- DOMAINS / ENUMS
-- ============================================================
DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('Pending','Paid','Shipped','Cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE po_status    AS ENUM ('Pending','Approved','Received','Cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE mfg_status   AS ENUM ('Pending','In Progress','Completed','On Hold');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE qc_result    AS ENUM ('Pending','Pass','Fail');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE job_status   AS ENUM ('Pending','In Progress','Completed','On Hold');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE user_role    AS ENUM ('Admin','Sales Rep','Viewer','Manager','Cashier');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE user_status  AS ENUM ('Active','Inactive');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE uom_category AS ENUM ('Quantity','Weight','Volume','Length','Area','Time','Other');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE attr_type    AS ENUM ('Text','Number','Select','Date','Boolean');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE installment_status AS ENUM ('Pending','Paid','Overdue','Cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- MASTER DATA TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0001 (
    id            SERIAL PRIMARY KEY,
    uom_code      VARCHAR(10)  NOT NULL UNIQUE,
    uom_name      VARCHAR(50)  NOT NULL,
    category      uom_category NOT NULL DEFAULT 'Quantity',
    is_base_unit  BOOLEAN      NOT NULL DEFAULT false,
    is_active     BOOLEAN      NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT          NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0002 (
    id          SERIAL PRIMARY KEY,
    from_uom_id INT NOT NULL REFERENCES "Nova".t0001(id),
    to_uom_id   INT NOT NULL REFERENCES "Nova".t0001(id),
    factor      NUMERIC(12,6) NOT NULL CHECK (factor > 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0003 (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    price       NUMERIC(12,2) NOT NULL DEFAULT 0,
    cost_price  NUMERIC(12,2) NOT NULL DEFAULT 0,
    category    VARCHAR(100),
    brand       VARCHAR(100),
    tax_rate    NUMERIC(5,2) DEFAULT 0,
    image_url   TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0004 (
    id          SERIAL PRIMARY KEY,
    product_id  INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    barcode     VARCHAR(100) NOT NULL,
    barcode_type VARCHAR(20) DEFAULT 'EAN13',
    is_primary  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0005 (
    id             SERIAL PRIMARY KEY,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_type attr_type NOT NULL DEFAULT 'Text',
    is_required    BOOLEAN NOT NULL DEFAULT false,
    sort_order     INT NOT NULL DEFAULT 0,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by     INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     INT,
    update_number  INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0006 (
    id            SERIAL PRIMARY KEY,
    product_id    INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    attribute_id  INT NOT NULL REFERENCES "Nova".t0005(id) ON DELETE CASCADE,
    value_text    VARCHAR(500),
    value_number  NUMERIC(12,4),
    value_date    DATE,
    value_boolean BOOLEAN,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0007 (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    base_uom_id     INT NOT NULL REFERENCES "Nova".t0001(id),
    purchase_uom_id INT REFERENCES "Nova".t0001(id),
    sales_uom_id    INT REFERENCES "Nova".t0001(id),
    purchase_factor NUMERIC(12,6) NOT NULL DEFAULT 1,
    sales_factor    NUMERIC(12,6) NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0008 (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    location    VARCHAR(200),
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0009 (
    id             SERIAL PRIMARY KEY,
    product_id     INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    warehouse_id   INT NOT NULL REFERENCES "Nova".t0008(id),
    qty            NUMERIC(12,2) NOT NULL DEFAULT 0,
    reorder_level  NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by     INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     INT,
    update_number  INT NOT NULL DEFAULT 1
);

-- ============================================================
-- CRM TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0010 (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    group_name          VARCHAR(100) DEFAULT 'Retail',
    phone               VARCHAR(30),
    email               VARCHAR(200),
    credit_limit        NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    balance             NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    default_price_list_id INT,
    default_tax_rate_id   INT,
    payment_term_id       INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0011 (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    category      VARCHAR(100),
    phone         VARCHAR(30),
    email         VARCHAR(200),
    payment_terms VARCHAR(100),
    rating        INT DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- SALES ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0012 (
    id              SERIAL PRIMARY KEY,
    order_number    VARCHAR(50) NOT NULL UNIQUE,
    customer_id     INT NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax             NUMERIC(12,2) NOT NULL DEFAULT 0,
    grand_total     NUMERIC(12,2) NOT NULL DEFAULT 0,
    status          order_status NOT NULL DEFAULT 'Pending',
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    price_list_id   INT,
    tax_rate_id     INT,
    payment_term_id INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0013 (
    id              SERIAL PRIMARY KEY,
    sales_order_id  INT NOT NULL REFERENCES "Nova".t0012(id) ON DELETE CASCADE,
    product_id      INT NOT NULL,
    product_name    VARCHAR(200),
    uom_id          INT,
    qty             NUMERIC(12,2) NOT NULL DEFAULT 0,
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number     INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

-- ============================================================
-- PURCHASE ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0014 (
    id              SERIAL PRIMARY KEY,
    order_number    VARCHAR(50) NOT NULL UNIQUE,
    supplier_id     INT NOT NULL,
    total           NUMERIC(12,2) NOT NULL DEFAULT 0,
    status          po_status NOT NULL DEFAULT 'Pending',
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_date   DATE,
    notes           TEXT,
    converted_rfq_id INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0015 (
    id                SERIAL PRIMARY KEY,
    purchase_order_id INT NOT NULL REFERENCES "Nova".t0014(id) ON DELETE CASCADE,
    product_id        INT NOT NULL,
    product_name      VARCHAR(200),
    uom_id            INT,
    qty               NUMERIC(12,2) NOT NULL DEFAULT 0,
    unit_price        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number       INT NOT NULL DEFAULT 1,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);

-- ============================================================
-- INSTALLMENTS (Sales)
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0016 (
    id              SERIAL PRIMARY KEY,
    sales_order_id  INT NOT NULL,
    plan_name       VARCHAR(100),
    total_amount    NUMERIC(12,2) NOT NULL DEFAULT 0,
    num_installments INT NOT NULL DEFAULT 1,
    frequency_days  INT NOT NULL DEFAULT 30,
    first_due_date  DATE,
    status          installment_status NOT NULL DEFAULT 'Pending',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0017 (
    id                SERIAL PRIMARY KEY,
    installment_plan_id INT NOT NULL REFERENCES "Nova".t0016(id) ON DELETE CASCADE,
    installment_number  INT NOT NULL,
    due_date            DATE NOT NULL,
    amount_due          NUMERIC(12,2) NOT NULL DEFAULT 0,
    amount_paid         NUMERIC(12,2) NOT NULL DEFAULT 0,
    paid_date           DATE,
    payment_method      VARCHAR(50),
    status              installment_status NOT NULL DEFAULT 'Pending',
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

-- ============================================================
-- MANUFACTURING
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0018 (
    id            SERIAL PRIMARY KEY,
    order_number  VARCHAR(50) NOT NULL UNIQUE,
    product_id    INT NOT NULL,
    product_name  VARCHAR(200),
    quantity      NUMERIC(12,2) NOT NULL DEFAULT 0,
    status        mfg_status NOT NULL DEFAULT 'Pending',
    due_date      DATE,
    priority      INT DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0019 (
    id              SERIAL PRIMARY KEY,
    inspection_no   VARCHAR(50) NOT NULL UNIQUE,
    product_id      INT NOT NULL,
    product_name    VARCHAR(200),
    batch_no        VARCHAR(50),
    result          qc_result NOT NULL DEFAULT 'Pending',
    inspector       VARCHAR(100),
    inspection_date DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0020 (
    id            SERIAL PRIMARY KEY,
    job_number    VARCHAR(50) NOT NULL UNIQUE,
    product_id    INT NOT NULL,
    product_name  VARCHAR(200),
    quantity      NUMERIC(12,2) NOT NULL DEFAULT 0,
    workstation   VARCHAR(100),
    status        job_status NOT NULL DEFAULT 'Pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- ADMINISTRATION
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0021 (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(200),
    email         VARCHAR(200),
    role          VARCHAR(30) NOT NULL DEFAULT 'Viewer',
    permissions   TEXT[] DEFAULT '{}',
    business_id   INT,
    status        VARCHAR(20) NOT NULL DEFAULT 'Active',
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0022 (
    id            SERIAL PRIMARY KEY,
    module_key    VARCHAR(50) NOT NULL,
    label         VARCHAR(100) NOT NULL,
    label_ar      VARCHAR(100),
    icon          VARCHAR(50),
    section       VARCHAR(100),
    permission_key VARCHAR(50),
    sort_order    INT NOT NULL DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0023 (
    id            SERIAL PRIMARY KEY,
    table_name    VARCHAR(10) NOT NULL,
    record_id     INT NOT NULL,
    action        VARCHAR(20) NOT NULL,
    changed_data  JSONB,
    changed_by    INT,
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- ACCOUNTING
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0026 (
    id            SERIAL PRIMARY KEY,
    account_code  VARCHAR(20) NOT NULL UNIQUE,
    account_name  VARCHAR(100) NOT NULL,
    account_type  VARCHAR(50) NOT NULL,
    parent_id     INT,
    currency      VARCHAR(3) NOT NULL DEFAULT 'USD',
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0027 (
    id            SERIAL PRIMARY KEY,
    entry_date    DATE NOT NULL,
    reference     VARCHAR(100),
    description   VARCHAR(255) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'Draft',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- HR
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0028 (
    id              SERIAL PRIMARY KEY,
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(100) NOT NULL,
    parent_id       INT,
    manager_id      INT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0029 (
    id               SERIAL PRIMARY KEY,
    designation_code VARCHAR(20) NOT NULL UNIQUE,
    designation_name VARCHAR(100) NOT NULL,
    department_id    INT,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       INT,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by       INT,
    update_number    INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0030 (
    id                SERIAL PRIMARY KEY,
    employee_code     VARCHAR(20) NOT NULL UNIQUE,
    full_name         VARCHAR(200) NOT NULL,
    arabic_name       VARCHAR(200),
    email             VARCHAR(200),
    phone             VARCHAR(30),
    address           TEXT,
    national_id       VARCHAR(50),
    passport_no       VARCHAR(50),
    gender            VARCHAR(10),
    marital_status    VARCHAR(20),
    birth_date        DATE,
    hire_date         DATE,
    termination_date  DATE,
    employment_status VARCHAR(30) DEFAULT 'Active',
    department_id     INT,
    designation_id    INT,
    manager_id        INT,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);

-- ============================================================
-- INVOICES & PAYMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0090 (
    id              SERIAL PRIMARY KEY,
    invoice_number  VARCHAR(50) NOT NULL UNIQUE,
    invoice_type    VARCHAR(10) NOT NULL DEFAULT 'Sales',
    partner_id      INT NOT NULL,
    issue_date      DATE NOT NULL,
    due_date        DATE NOT NULL,
    total_amount    NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0091 (
    id              SERIAL PRIMARY KEY,
    payment_date    DATE NOT NULL,
    invoice_id      INT,
    partner_id      INT NOT NULL,
    amount          NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_method  VARCHAR(50) NOT NULL,
    reference       VARCHAR(100),
    status          VARCHAR(20) NOT NULL DEFAULT 'Completed',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0096 (
    id                 SERIAL PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    code               VARCHAR(20) NOT NULL UNIQUE,
    description        TEXT,
    due_days           INT NOT NULL DEFAULT 30,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
    discount_days      INT NOT NULL DEFAULT 0,
    is_active          BOOLEAN NOT NULL DEFAULT true,
    is_default         BOOLEAN NOT NULL DEFAULT false,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by         INT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by         INT,
    update_number      INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0097 (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    code          VARCHAR(20) NOT NULL UNIQUE,
    description   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    is_default    BOOLEAN NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- NOTIFICATIONS, SCHEDULER, MODULE REGISTRY
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0098 (
    id                SERIAL PRIMARY KEY,
    user_id           INT NOT NULL,
    title             VARCHAR(200) NOT NULL,
    message           TEXT,
    notification_type VARCHAR(30) NOT NULL DEFAULT 'Info',
    reference_type    VARCHAR(30),
    reference_id      INT,
    is_read           BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Nova".t0099 (
    id              SERIAL PRIMARY KEY,
    task_name       VARCHAR(200) NOT NULL,
    task_type       VARCHAR(50) NOT NULL,
    cron_expression VARCHAR(50) NOT NULL,
    description     TEXT,
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'Idle',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ,
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Nova".t0100 (
    id            SERIAL PRIMARY KEY,
    module_key    VARCHAR(50) NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_ar       VARCHAR(100),
    description   TEXT,
    description_ar TEXT,
    version       VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    author        VARCHAR(200),
    icon          VARCHAR(50),
    category      VARCHAR(50),
    is_core       BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    installed_at  TIMESTAMPTZ,
    dependencies  JSONB DEFAULT '[]'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ,
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_t0010_name ON "Nova".t0010(name);
CREATE INDEX IF NOT EXISTS idx_t0012_customer ON "Nova".t0012(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0012_status ON "Nova".t0012(status);
CREATE INDEX IF NOT EXISTS idx_t0014_supplier ON "Nova".t0014(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0014_status ON "Nova".t0014(status);
CREATE INDEX IF NOT EXISTS idx_t0026_type ON "Nova".t0026(account_type);
CREATE INDEX IF NOT EXISTS idx_t0027_date ON "Nova".t0027(entry_date);
CREATE INDEX IF NOT EXISTS idx_t0027_status ON "Nova".t0027(status);
CREATE INDEX IF NOT EXISTS idx_t0090_partner ON "Nova".t0090(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0090_status ON "Nova".t0090(status);
CREATE INDEX IF NOT EXISTS idx_t0091_invoice ON "Nova".t0091(invoice_id);
CREATE INDEX IF NOT EXISTS idx_t0091_partner ON "Nova".t0091(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0096_default ON "Nova".t0096(is_default);
CREATE INDEX IF NOT EXISTS idx_t0098_user ON "Nova".t0098(user_id);
CREATE INDEX IF NOT EXISTS idx_t0098_read ON "Nova".t0098(is_read);
CREATE INDEX IF NOT EXISTS idx_t0099_active ON "Nova".t0099(is_active);
CREATE INDEX IF NOT EXISTS idx_t0099_status ON "Nova".t0099(status);
CREATE INDEX IF NOT EXISTS idx_t0099_next_run ON "Nova".t0099(next_run_at);
CREATE INDEX IF NOT EXISTS idx_t0100_key ON "Nova".t0100(module_key);
CREATE INDEX IF NOT EXISTS idx_t0100_active ON "Nova".t0100(is_active);
CREATE INDEX IF NOT EXISTS idx_t0100_category ON "Nova".t0100(category);

COMMIT;

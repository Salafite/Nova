-- Nova ERP ï؟½ Consolidated Full Schema
-- Combines 001_full_schema.sql + 002_missing_tables.sql
-- Run against an empty PostgreSQL database.
-- Creates the "Nova" schema and ALL business tables (T0001ï؟½T0100).

BEGIN;

-- Nova ERP â€” Full Schema Migration
-- Run against an empty PostgreSQL database with a user that has CREATE privileges.
-- Creates the "Nova" schema and all business tables.



-- Create the Nova schema if it does not exist
CREATE SCHEMA IF NOT EXISTS "Nova";

-- ============================================================
-- DOMAINS / ENUMS
-- ============================================================
DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('Draft','Pending','Confirmed','Processing','Shipped','Delivered','Invoiced','Paid','Cancelled');
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
  CREATE TYPE user_role    AS ENUM ('Admin','Sales Rep','Viewer','Manager','Cashier','Salesman','Warehouse','Accountant');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE user_status  AS ENUM ('Active','Inactive','Invited');
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
-- SEQUENCES
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_invoice_number START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_pick_list_number START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_stock_transfer_number START WITH 1 INCREMENT BY 1;

COMMENT ON SEQUENCE "Nova".seq_invoice_number IS 'Concurrency-safe atomic sequence for generating unique invoice numbers (INV-XXXXX)';
COMMENT ON SEQUENCE "Nova".seq_pick_list_number IS 'Concurrency-safe atomic sequence for generating unique pick list numbers (PKL-XXXXX)';
COMMENT ON SEQUENCE "Nova".seq_stock_transfer_number IS 'Concurrency-safe atomic sequence for generating unique stock transfer numbers (TRF-XXXXX)';

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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0001.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0001_business_id ON "Nova".t0001(business_id);
CREATE INDEX IF NOT EXISTS idx_t0001_business_id_id ON "Nova".t0001(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0002 (
    id          SERIAL PRIMARY KEY,
    from_uom_id INT NOT NULL REFERENCES "Nova".t0001(id),
    to_uom_id   INT NOT NULL REFERENCES "Nova".t0001(id),
    factor      NUMERIC(12,6) NOT NULL CHECK (factor > 0),
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0002.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0002_business_id ON "Nova".t0002(business_id);
CREATE INDEX IF NOT EXISTS idx_t0002_business_id_id ON "Nova".t0002(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0003 (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    sku         VARCHAR(50)  NOT NULL UNIQUE,
    barcode     VARCHAR(100),
    description TEXT,
    type        VARCHAR(20) NOT NULL DEFAULT 'stockable',
    price       NUMERIC(12,2) NOT NULL DEFAULT 0,
    cost_price  NUMERIC(12,2) NOT NULL DEFAULT 0,
    category    VARCHAR(100),
    brand       VARCHAR(100),
    tax_rate    NUMERIC(5,2) DEFAULT 0,
    weight      NUMERIC(10,3) NOT NULL DEFAULT 0,
    volume      NUMERIC(10,3) NOT NULL DEFAULT 0,
    image_url   TEXT,
    is_purchasable BOOLEAN NOT NULL DEFAULT true,
    is_saleable    BOOLEAN NOT NULL DEFAULT true,
    is_phantom     BOOLEAN NOT NULL DEFAULT false,
    last_transaction_date TIMESTAMPTZ,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0003.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0003_business_id ON "Nova".t0003(business_id);
CREATE INDEX IF NOT EXISTS idx_t0003_business_id_id ON "Nova".t0003(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0004 (
    id          SERIAL PRIMARY KEY,
    product_id  INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    barcode     VARCHAR(100) NOT NULL,
    barcode_type VARCHAR(20) DEFAULT 'EAN13',
    is_primary  BOOLEAN NOT NULL DEFAULT false,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  INT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0004.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0004_business_id ON "Nova".t0004(business_id);
CREATE INDEX IF NOT EXISTS idx_t0004_business_id_id ON "Nova".t0004(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0005 (
    id             SERIAL PRIMARY KEY,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_type attr_type NOT NULL DEFAULT 'Text',
    display_type   VARCHAR(20) NOT NULL DEFAULT 'select',
    description    TEXT,
    create_variant BOOLEAN NOT NULL DEFAULT true,
    attribute_group VARCHAR(100),
    is_required    BOOLEAN NOT NULL DEFAULT false,
    sort_order     INT NOT NULL DEFAULT 0,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by     INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     INT,
    update_number  INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0005.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0005_business_id ON "Nova".t0005(business_id);
CREATE INDEX IF NOT EXISTS idx_t0005_business_id_id ON "Nova".t0005(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0006 (
    id            SERIAL PRIMARY KEY,
    product_id    INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    attribute_id  INT NOT NULL REFERENCES "Nova".t0005(id) ON DELETE CASCADE,
    value_text    VARCHAR(500),
    value_number  NUMERIC(12,4),
    value_date    DATE,
    value_boolean BOOLEAN,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0006.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0006_business_id ON "Nova".t0006(business_id);
CREATE INDEX IF NOT EXISTS idx_t0006_business_id_id ON "Nova".t0006(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0007 (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    base_uom_id     INT NOT NULL REFERENCES "Nova".t0001(id),
    purchase_uom_id INT REFERENCES "Nova".t0001(id),
    sales_uom_id    INT REFERENCES "Nova".t0001(id),
    purchase_factor NUMERIC(12,6) NOT NULL DEFAULT 1,
    sales_factor    NUMERIC(12,6) NOT NULL DEFAULT 1,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0007.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0007_business_id ON "Nova".t0007(business_id);
CREATE INDEX IF NOT EXISTS idx_t0007_business_id_id ON "Nova".t0007(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0008 (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    location      VARCHAR(200),
    warehouse_type VARCHAR(50) DEFAULT 'Standard',
    is_virtual    BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0008.warehouse_type IS 'Warehouse classification: Central Hub | Regional DC | Retail Branch | In-Transit Virtual | Standard';
COMMENT ON COLUMN "Nova".t0008.is_virtual IS 'Flag indicating if warehouse is a virtual location (e.g. In-Transit virtual warehouse)';
COMMENT ON COLUMN "Nova".t0008.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0008_warehouse_type ON "Nova".t0008(warehouse_type);
CREATE INDEX IF NOT EXISTS idx_t0008_is_virtual ON "Nova".t0008(is_virtual);
CREATE INDEX IF NOT EXISTS idx_t0008_business_id ON "Nova".t0008(business_id);
CREATE INDEX IF NOT EXISTS idx_t0008_business_id_id ON "Nova".t0008(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0009 (
    id             SERIAL PRIMARY KEY,
    product_id     INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    warehouse_id   INT NOT NULL REFERENCES "Nova".t0008(id),
    qty            NUMERIC(12,2) NOT NULL DEFAULT 0,
    reserved_qty   NUMERIC(12,2) NOT NULL DEFAULT 0,
    in_transit_qty NUMERIC(12,2) NOT NULL DEFAULT 0,
    reorder_level  NUMERIC(12,2) NOT NULL DEFAULT 0,
    business_id    INT REFERENCES "Nova".t0059(id),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by     INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     INT,
    update_number  INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0009.in_transit_qty IS 'Quantity of inventory currently in-transit to/from this warehouse';
COMMENT ON COLUMN "Nova".t0009.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0009_in_transit_qty ON "Nova".t0009(in_transit_qty);
CREATE INDEX IF NOT EXISTS idx_t0009_business_id ON "Nova".t0009(business_id);
CREATE INDEX IF NOT EXISTS idx_t0009_business_id_id ON "Nova".t0009(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1,
    allow_reorders      BOOLEAN NOT NULL DEFAULT true,
    min_order_amount    NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (min_order_amount >= 0),
    order_cutoff_time   TIME,
);
COMMENT ON COLUMN "Nova".t0010.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0010_business_id ON "Nova".t0010(business_id);
CREATE INDEX IF NOT EXISTS idx_t0010_business_id_id ON "Nova".t0010(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0011 (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    category      VARCHAR(100),
    phone         VARCHAR(30),
    email         VARCHAR(200),
    payment_terms VARCHAR(100),
    rating        INT DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0011.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0011_business_id ON "Nova".t0011(business_id);
CREATE INDEX IF NOT EXISTS idx_t0011_business_id_id ON "Nova".t0011(business_id, id);



-- ============================================================
-- SALES ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0012 (
    id              SERIAL PRIMARY KEY,
    order_number    VARCHAR(50) NOT NULL UNIQUE,
    customer_id     INT NOT NULL,
    warehouse_id    INT REFERENCES "Nova".t0008(id),
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax             NUMERIC(12,2) NOT NULL DEFAULT 0,
    grand_total     NUMERIC(12,2) NOT NULL DEFAULT 0,
    freight_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    sales_rep_id    INT REFERENCES "Nova".t0021(id),
    status          order_status NOT NULL DEFAULT 'Pending',
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    price_list_id   INT,
    tax_rate_id     INT,
    payment_term_id INT,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0012.freight_amount IS 'Freight / shipping charges applied to sales order';
COMMENT ON COLUMN "Nova".t0012.discount_amount IS 'Header-level discount amount applied to sales order';
COMMENT ON COLUMN "Nova".t0012.sales_rep_id IS 'Assigned sales representative (User ID)';
COMMENT ON COLUMN "Nova".t0012.business_id IS 'Tenant / business organization identifier (FK to T0059)';

ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS on_credit_hold BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS hold_reason TEXT;

COMMENT ON COLUMN "Nova".t0012.on_credit_hold IS 'Whether sales order is on credit hold pending approval';
COMMENT ON COLUMN "Nova".t0012.hold_reason IS 'Reason why sales order was placed on credit hold';

CREATE INDEX IF NOT EXISTS idx_t0012_on_credit_hold ON "Nova".t0012(on_credit_hold);


ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS client_order_uuid VARCHAR(64) UNIQUE,
    ADD COLUMN IF NOT EXISTS is_offline_sync BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(30) NOT NULL DEFAULT 'Synced',
    ADD COLUMN IF NOT EXISTS offline_created_at TIMESTAMPTZ;

COMMENT ON COLUMN "Nova".t0012.client_order_uuid IS 'Client-generated UUID for offline order creation, duplicate prevention, and idempotency';
COMMENT ON COLUMN "Nova".t0012.is_offline_sync IS 'Flag indicating if order was created offline and synced later';
COMMENT ON COLUMN "Nova".t0012.sync_status IS 'Synchronization status: Synced, Pending, Conflict, Failed';
COMMENT ON COLUMN "Nova".t0012.offline_created_at IS 'Device timestamp when order was created while offline';

CREATE UNIQUE INDEX IF NOT EXISTS idx_t0012_client_order_uuid ON "Nova".t0012(client_order_uuid);
CREATE INDEX IF NOT EXISTS idx_t0012_sync_status ON "Nova".t0012(sync_status);

CREATE INDEX IF NOT EXISTS idx_t0012_business_id ON "Nova".t0012(business_id);
CREATE INDEX IF NOT EXISTS idx_t0012_business_id_id ON "Nova".t0012(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0013 (
    id              SERIAL PRIMARY KEY,
    sales_order_id  INT NOT NULL REFERENCES "Nova".t0012(id) ON DELETE CASCADE,
    product_id      INT NOT NULL,
    product_name    VARCHAR(200),
    uom_id          INT,
    qty             NUMERIC(12,2) NOT NULL DEFAULT 0,
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    cost_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number     INT NOT NULL DEFAULT 1,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0013.cost_price IS 'Unit cost price / COGS at time of order';
COMMENT ON COLUMN "Nova".t0013.discount IS 'Line-level discount amount';
COMMENT ON COLUMN "Nova".t0013.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0013_business_id ON "Nova".t0013(business_id);
CREATE INDEX IF NOT EXISTS idx_t0013_business_id_id ON "Nova".t0013(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0014.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0014_business_id ON "Nova".t0014(business_id);
CREATE INDEX IF NOT EXISTS idx_t0014_business_id_id ON "Nova".t0014(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0015.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0015_business_id ON "Nova".t0015(business_id);
CREATE INDEX IF NOT EXISTS idx_t0015_business_id_id ON "Nova".t0015(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0016.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0016_business_id ON "Nova".t0016(business_id);
CREATE INDEX IF NOT EXISTS idx_t0016_business_id_id ON "Nova".t0016(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0017.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0017_business_id ON "Nova".t0017(business_id);
CREATE INDEX IF NOT EXISTS idx_t0017_business_id_id ON "Nova".t0017(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0018.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0018_business_id ON "Nova".t0018(business_id);
CREATE INDEX IF NOT EXISTS idx_t0018_business_id_id ON "Nova".t0018(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0019.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0019_business_id ON "Nova".t0019(business_id);
CREATE INDEX IF NOT EXISTS idx_t0019_business_id_id ON "Nova".t0019(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0020 (
    id            SERIAL PRIMARY KEY,
    job_number    VARCHAR(50) NOT NULL UNIQUE,
    product_id    INT NOT NULL,
    product_name  VARCHAR(200),
    quantity      NUMERIC(12,2) NOT NULL DEFAULT 0,
    workstation   VARCHAR(100),
    status        job_status NOT NULL DEFAULT 'Pending',
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0020.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0020_business_id ON "Nova".t0020(business_id);
CREATE INDEX IF NOT EXISTS idx_t0020_business_id_id ON "Nova".t0020(business_id, id);



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
    status        VARCHAR(20) NOT NULL DEFAULT 'Active',
    business_id   INT REFERENCES "Nova".t0059(id),
    invite_token  VARCHAR(100),
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0021.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0021_business_id ON "Nova".t0021(business_id);
CREATE INDEX IF NOT EXISTS idx_t0021_business_id_id ON "Nova".t0021(business_id, id);

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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0022.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0022_business_id ON "Nova".t0022(business_id);
CREATE INDEX IF NOT EXISTS idx_t0022_business_id_id ON "Nova".t0022(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0023 (
    id            SERIAL PRIMARY KEY,
    table_name    VARCHAR(10) NOT NULL,
    record_id     INT NOT NULL,
    action        VARCHAR(20) NOT NULL,
    changed_data  JSONB,
    changed_by    INT,
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0023.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0023_business_id ON "Nova".t0023(business_id);
CREATE INDEX IF NOT EXISTS idx_t0023_business_id_id ON "Nova".t0023(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0026.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0026_business_id ON "Nova".t0026(business_id);
CREATE INDEX IF NOT EXISTS idx_t0026_business_id_id ON "Nova".t0026(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0027 (
    id            SERIAL PRIMARY KEY,
    entry_date    DATE NOT NULL,
    reference     VARCHAR(100),
    description   VARCHAR(255) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'Draft',
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0027.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0027_business_id ON "Nova".t0027(business_id);
CREATE INDEX IF NOT EXISTS idx_t0027_business_id_id ON "Nova".t0027(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0028.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0028_business_id ON "Nova".t0028(business_id);
CREATE INDEX IF NOT EXISTS idx_t0028_business_id_id ON "Nova".t0028(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0029 (
    id               SERIAL PRIMARY KEY,
    designation_code VARCHAR(20) NOT NULL UNIQUE,
    designation_name VARCHAR(100) NOT NULL,
    department_id    INT,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       INT,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by       INT,
    update_number    INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0029.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0029_business_id ON "Nova".t0029(business_id);
CREATE INDEX IF NOT EXISTS idx_t0029_business_id_id ON "Nova".t0029(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0030.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0030_business_id ON "Nova".t0030(business_id);
CREATE INDEX IF NOT EXISTS idx_t0030_business_id_id ON "Nova".t0030(business_id, id);



-- ============================================================
-- INVOICES & PAYMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0090 (
    id              SERIAL PRIMARY KEY,
    invoice_number  VARCHAR(50) NOT NULL UNIQUE,
    invoice_type    VARCHAR(10) NOT NULL DEFAULT 'Sales',
    partner_id      INT NOT NULL,
    sales_order_id  INT REFERENCES "Nova".t0012(id),
    issue_date      DATE NOT NULL,
    due_date        DATE NOT NULL,
    total_amount    NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    freight_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    sales_rep_id    INT REFERENCES "Nova".t0021(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes           TEXT,
    payment_term_id INT REFERENCES "Nova".t0096(id),
    discount_due_date DATE DEFAULT NULL,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
    discount_days   INT NOT NULL DEFAULT 0,
    early_discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0090.freight_amount IS 'Freight / shipping charges billed on invoice';
COMMENT ON COLUMN "Nova".t0090.discount_amount IS 'Customer discount deducted on invoice';
COMMENT ON COLUMN "Nova".t0090.sales_rep_id IS 'Assigned sales representative (User ID)';
COMMENT ON COLUMN "Nova".t0090.payment_term_id IS 'Assigned payment term identifier (FK to T0096)';
COMMENT ON COLUMN "Nova".t0090.discount_due_date IS 'Cutoff date for early payment discount eligibility';
COMMENT ON COLUMN "Nova".t0090.discount_percentage IS 'Early payment discount percentage applicable before cutoff';
COMMENT ON COLUMN "Nova".t0090.discount_days IS 'Number of days within which early payment discount is valid';
COMMENT ON COLUMN "Nova".t0090.early_discount_amount IS 'Calculated maximum early discount amount if paid within discount period';
COMMENT ON COLUMN "Nova".t0090.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0090_business_id ON "Nova".t0090(business_id);
CREATE INDEX IF NOT EXISTS idx_t0090_business_id_id ON "Nova".t0090(business_id, id);
CREATE INDEX IF NOT EXISTS idx_t0090_payment_term_id ON "Nova".t0090(payment_term_id);
CREATE INDEX IF NOT EXISTS idx_t0090_discount_due_date ON "Nova".t0090(discount_due_date);
CREATE INDEX IF NOT EXISTS idx_t0090_due_date ON "Nova".t0090(due_date);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0091.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0091_business_id ON "Nova".t0091(business_id);
CREATE INDEX IF NOT EXISTS idx_t0091_business_id_id ON "Nova".t0091(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by         INT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by         INT,
    update_number      INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0096.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0096_business_id ON "Nova".t0096(business_id);
CREATE INDEX IF NOT EXISTS idx_t0096_business_id_id ON "Nova".t0096(business_id, id);



CREATE TABLE IF NOT EXISTS "Nova".t0097 (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    code          VARCHAR(20) NOT NULL UNIQUE,
    description   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    is_default    BOOLEAN NOT NULL DEFAULT false,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0097.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0097_business_id ON "Nova".t0097(business_id);
CREATE INDEX IF NOT EXISTS idx_t0097_business_id_id ON "Nova".t0097(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN "Nova".t0098.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0098_business_id ON "Nova".t0098(business_id);
CREATE INDEX IF NOT EXISTS idx_t0098_business_id_id ON "Nova".t0098(business_id, id);



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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ,
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0099.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0099_business_id ON "Nova".t0099(business_id);
CREATE INDEX IF NOT EXISTS idx_t0099_business_id_id ON "Nova".t0099(business_id, id);



INSERT INTO "Nova".t0099 (task_name, task_type, cron_expression, description, config, is_active, status)
SELECT 'Demand Forecasting & Restock Requisitions', 'DemandForecastRestock', '0 6 * * *', 'Daily morning demand velocity analysis, stockout risk projection, and proactive restock digest notification', '{"days": 30, "safety_margin_days": 7, "target_coverage_days": 30}'::jsonb, true, 'Idle'
WHERE NOT EXISTS (
    SELECT 1 FROM "Nova".t0099 WHERE task_type = 'DemandForecastRestock'
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
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ,
    updated_by    INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0100.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0100_business_id ON "Nova".t0100(business_id);
CREATE INDEX IF NOT EXISTS idx_t0100_business_id_id ON "Nova".t0100(business_id, id);



-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_t0010_name ON "Nova".t0010(name);
CREATE INDEX IF NOT EXISTS idx_t0012_customer ON "Nova".t0012(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0012_status ON "Nova".t0012(status);
CREATE INDEX IF NOT EXISTS idx_t0012_sales_rep_id ON "Nova".t0012(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0014_supplier ON "Nova".t0014(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0014_status ON "Nova".t0014(status);
CREATE INDEX IF NOT EXISTS idx_t0026_type ON "Nova".t0026(account_type);
CREATE INDEX IF NOT EXISTS idx_t0027_date ON "Nova".t0027(entry_date);
CREATE INDEX IF NOT EXISTS idx_t0027_status ON "Nova".t0027(status);
CREATE INDEX IF NOT EXISTS idx_t0090_partner ON "Nova".t0090(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0090_status ON "Nova".t0090(status);
CREATE INDEX IF NOT EXISTS idx_t0090_sales_rep_id ON "Nova".t0090(sales_rep_id);
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

-- Nova ERP â€” Missing Tables Migration (002)
-- Generated from controller business_columns and Pydantic models
-- Run against a PostgreSQL database with the Nova schema already created



-- Employee Contracts
CREATE TABLE IF NOT EXISTS "Nova".t0031 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    contract_type VARCHAR(30),
    start_date DATE,
    end_date DATE,
    basic_salary NUMERIC(12,2),
    housing_allowance NUMERIC(12,2),
    transport_allowance NUMERIC(12,2),
    other_allowances NUMERIC(12,2),
    currency VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0031.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0031_business_id ON "Nova".t0031(business_id);
CREATE INDEX IF NOT EXISTS idx_t0031_business_id_id ON "Nova".t0031(business_id, id);


COMMENT ON TABLE "Nova".t0031 IS 'Employee Contracts';
COMMENT ON COLUMN "Nova".t0031.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0031.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0031.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0031_employee_id ON "Nova".t0031(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0031_active ON "Nova".t0031(is_active);

-- Employee Documents
CREATE TABLE IF NOT EXISTS "Nova".t0032 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    document_type VARCHAR(30),
    document_name VARCHAR(200),
    file_path TEXT,
    expiry_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0032.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0032_business_id ON "Nova".t0032(business_id);
CREATE INDEX IF NOT EXISTS idx_t0032_business_id_id ON "Nova".t0032(business_id, id);


COMMENT ON TABLE "Nova".t0032 IS 'Employee Documents';
COMMENT ON COLUMN "Nova".t0032.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0032.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0032.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0032_employee_id ON "Nova".t0032(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0032_active ON "Nova".t0032(is_active);

-- Work Shifts
CREATE TABLE IF NOT EXISTS "Nova".t0033 (
    id SERIAL PRIMARY KEY,
    shift_code VARCHAR(30),
    shift_name VARCHAR(200),
    start_time TIME,
    end_time TIME,
    grace_minutes NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0033.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0033_business_id ON "Nova".t0033(business_id);
CREATE INDEX IF NOT EXISTS idx_t0033_business_id_id ON "Nova".t0033(business_id, id);


COMMENT ON TABLE "Nova".t0033 IS 'Work Shifts';
COMMENT ON COLUMN "Nova".t0033.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0033.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0033_active ON "Nova".t0033(is_active);

-- Employee Attendance Records
CREATE TABLE IF NOT EXISTS "Nova".t0034 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    date DATE,
    shift_id INT,
    clock_in TIME,
    clock_out TIME,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0034.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0034_business_id ON "Nova".t0034(business_id);
CREATE INDEX IF NOT EXISTS idx_t0034_business_id_id ON "Nova".t0034(business_id, id);


COMMENT ON TABLE "Nova".t0034 IS 'Employee Attendance Records';
COMMENT ON COLUMN "Nova".t0034.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0034.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0034.shift_id IS 'Reference to Shift';
COMMENT ON COLUMN "Nova".t0034.status IS 'Status';
COMMENT ON COLUMN "Nova".t0034.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0034_employee_id ON "Nova".t0034(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0034_shift_id ON "Nova".t0034(shift_id);
CREATE INDEX IF NOT EXISTS idx_t0034_status ON "Nova".t0034(status);
CREATE INDEX IF NOT EXISTS idx_t0034_active ON "Nova".t0034(is_active);

-- Leave Types
CREATE TABLE IF NOT EXISTS "Nova".t0035 (
    id SERIAL PRIMARY KEY,
    leave_code VARCHAR(30),
    leave_name VARCHAR(200),
    days_per_year VARCHAR(200),
    is_paid VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0035.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0035_business_id ON "Nova".t0035(business_id);
CREATE INDEX IF NOT EXISTS idx_t0035_business_id_id ON "Nova".t0035(business_id, id);


COMMENT ON TABLE "Nova".t0035 IS 'Leave Types';
COMMENT ON COLUMN "Nova".t0035.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0035.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0035_active ON "Nova".t0035(is_active);

-- Leave Requests
CREATE TABLE IF NOT EXISTS "Nova".t0036 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    leave_type_id INT,
    start_date DATE,
    end_date DATE,
    days NUMERIC(5,1),
    reason VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    approved_by VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0036.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0036_business_id ON "Nova".t0036(business_id);
CREATE INDEX IF NOT EXISTS idx_t0036_business_id_id ON "Nova".t0036(business_id, id);


COMMENT ON TABLE "Nova".t0036 IS 'Leave Requests';
COMMENT ON COLUMN "Nova".t0036.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0036.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0036.leave_type_id IS 'Reference to Leave_Type';
COMMENT ON COLUMN "Nova".t0036.status IS 'Status';
COMMENT ON COLUMN "Nova".t0036.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0036_employee_id ON "Nova".t0036(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0036_leave_type_id ON "Nova".t0036(leave_type_id);
CREATE INDEX IF NOT EXISTS idx_t0036_status ON "Nova".t0036(status);
CREATE INDEX IF NOT EXISTS idx_t0036_active ON "Nova".t0036(is_active);

-- Payroll Periods
CREATE TABLE IF NOT EXISTS "Nova".t0037 (
    id SERIAL PRIMARY KEY,
    period_code VARCHAR(30),
    period_name VARCHAR(200),
    start_date DATE,
    end_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0037.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0037_business_id ON "Nova".t0037(business_id);
CREATE INDEX IF NOT EXISTS idx_t0037_business_id_id ON "Nova".t0037(business_id, id);


COMMENT ON TABLE "Nova".t0037 IS 'Payroll Periods';
COMMENT ON COLUMN "Nova".t0037.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0037.status IS 'Status';
COMMENT ON COLUMN "Nova".t0037.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0037_status ON "Nova".t0037(status);
CREATE INDEX IF NOT EXISTS idx_t0037_active ON "Nova".t0037(is_active);

-- Payroll Entries
CREATE TABLE IF NOT EXISTS "Nova".t0038 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    payroll_period_id INT,
    basic_salary NUMERIC(12,2),
    housing_allowance NUMERIC(12,2),
    transport_allowance NUMERIC(12,2),
    other_allowances NUMERIC(12,2),
    overtime NUMERIC(12,2),
    deductions NUMERIC(12,2),
    tax NUMERIC(12,2),
    gross_pay NUMERIC(12,2),
    net_pay NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    payment_date DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0038.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0038_business_id ON "Nova".t0038(business_id);
CREATE INDEX IF NOT EXISTS idx_t0038_business_id_id ON "Nova".t0038(business_id, id);


COMMENT ON TABLE "Nova".t0038 IS 'Payroll Entries';
COMMENT ON COLUMN "Nova".t0038.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0038.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0038.payroll_period_id IS 'Reference to Payroll_Period';
COMMENT ON COLUMN "Nova".t0038.status IS 'Status';
COMMENT ON COLUMN "Nova".t0038.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0038_employee_id ON "Nova".t0038(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0038_payroll_period_id ON "Nova".t0038(payroll_period_id);
CREATE INDEX IF NOT EXISTS idx_t0038_status ON "Nova".t0038(status);
CREATE INDEX IF NOT EXISTS idx_t0038_active ON "Nova".t0038(is_active);

-- Job Openings
CREATE TABLE IF NOT EXISTS "Nova".t0039 (
    id SERIAL PRIMARY KEY,
    job_code VARCHAR(30),
    job_title VARCHAR(200),
    department_id INT,
    designation_id INT,
    openings INT,
    description TEXT,
    requirements TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    posted_date DATE,
    closing_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0039.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0039_business_id ON "Nova".t0039(business_id);
CREATE INDEX IF NOT EXISTS idx_t0039_business_id_id ON "Nova".t0039(business_id, id);


COMMENT ON TABLE "Nova".t0039 IS 'Job Openings';
COMMENT ON COLUMN "Nova".t0039.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0039.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0039.designation_id IS 'Reference to Designation';
COMMENT ON COLUMN "Nova".t0039.status IS 'Status';
COMMENT ON COLUMN "Nova".t0039.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0039_department_id ON "Nova".t0039(department_id);
CREATE INDEX IF NOT EXISTS idx_t0039_designation_id ON "Nova".t0039(designation_id);
CREATE INDEX IF NOT EXISTS idx_t0039_status ON "Nova".t0039(status);
CREATE INDEX IF NOT EXISTS idx_t0039_active ON "Nova".t0039(is_active);

-- Job Candidates
CREATE TABLE IF NOT EXISTS "Nova".t0040 (
    id SERIAL PRIMARY KEY,
    candidate_code VARCHAR(30),
    full_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(200),
    job_opening_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    resume_path TEXT,
    notes TEXT,
    applied_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0040.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0040_business_id ON "Nova".t0040(business_id);
CREATE INDEX IF NOT EXISTS idx_t0040_business_id_id ON "Nova".t0040(business_id, id);


COMMENT ON TABLE "Nova".t0040 IS 'Job Candidates';
COMMENT ON COLUMN "Nova".t0040.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0040.job_opening_id IS 'Reference to Job_Opening';
COMMENT ON COLUMN "Nova".t0040.status IS 'Status';
COMMENT ON COLUMN "Nova".t0040.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0040_job_opening_id ON "Nova".t0040(job_opening_id);
CREATE INDEX IF NOT EXISTS idx_t0040_status ON "Nova".t0040(status);
CREATE INDEX IF NOT EXISTS idx_t0040_active ON "Nova".t0040(is_active);

-- Maintenance Assets
CREATE TABLE IF NOT EXISTS "Nova".t0041 (
    id SERIAL PRIMARY KEY,
    asset_code VARCHAR(30),
    asset_name VARCHAR(200),
    asset_type VARCHAR(30),
    asset_model VARCHAR(200),
    serial_no VARCHAR(200),
    location VARCHAR(200),
    department_id INT,
    purchase_date DATE,
    purchase_cost NUMERIC(12,2),
    useful_life INT,
    warranty_expiry VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0041.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0041_business_id ON "Nova".t0041(business_id);
CREATE INDEX IF NOT EXISTS idx_t0041_business_id_id ON "Nova".t0041(business_id, id);


COMMENT ON TABLE "Nova".t0041 IS 'Maintenance Assets';
COMMENT ON COLUMN "Nova".t0041.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0041.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0041.status IS 'Status';
COMMENT ON COLUMN "Nova".t0041.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0041_department_id ON "Nova".t0041(department_id);
CREATE INDEX IF NOT EXISTS idx_t0041_status ON "Nova".t0041(status);
CREATE INDEX IF NOT EXISTS idx_t0041_active ON "Nova".t0041(is_active);

-- Maintenance Schedules
CREATE TABLE IF NOT EXISTS "Nova".t0042 (
    id SERIAL PRIMARY KEY,
    asset_id INT,
    schedule_code VARCHAR(30),
    schedule_name VARCHAR(200),
    frequency_type VARCHAR(30),
    frequency_value NUMERIC(12,2),
    last_maintenance DATE,
    next_maintenance DATE,
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0042.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0042_business_id ON "Nova".t0042(business_id);
CREATE INDEX IF NOT EXISTS idx_t0042_business_id_id ON "Nova".t0042(business_id, id);


COMMENT ON TABLE "Nova".t0042 IS 'Maintenance Schedules';
COMMENT ON COLUMN "Nova".t0042.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0042.asset_id IS 'Reference to Asset';
COMMENT ON COLUMN "Nova".t0042.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0042_asset_id ON "Nova".t0042(asset_id);
CREATE INDEX IF NOT EXISTS idx_t0042_active ON "Nova".t0042(is_active);

-- Maintenance Work Orders
CREATE TABLE IF NOT EXISTS "Nova".t0043 (
    id SERIAL PRIMARY KEY,
    asset_id INT,
    schedule_id INT,
    work_order_code VARCHAR(30),
    description TEXT,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    scheduled_date DATE,
    completed_date DATE,
    cost NUMERIC(12,2),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0043.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0043_business_id ON "Nova".t0043(business_id);
CREATE INDEX IF NOT EXISTS idx_t0043_business_id_id ON "Nova".t0043(business_id, id);


COMMENT ON TABLE "Nova".t0043 IS 'Maintenance Work Orders';
COMMENT ON COLUMN "Nova".t0043.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0043.asset_id IS 'Reference to Asset';
COMMENT ON COLUMN "Nova".t0043.schedule_id IS 'Reference to Schedule';
COMMENT ON COLUMN "Nova".t0043.status IS 'Status';
COMMENT ON COLUMN "Nova".t0043.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0043_asset_id ON "Nova".t0043(asset_id);
CREATE INDEX IF NOT EXISTS idx_t0043_schedule_id ON "Nova".t0043(schedule_id);
CREATE INDEX IF NOT EXISTS idx_t0043_status ON "Nova".t0043(status);
CREATE INDEX IF NOT EXISTS idx_t0043_active ON "Nova".t0043(is_active);

-- Projects
CREATE TABLE IF NOT EXISTS "Nova".t0044 (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(30),
    project_name VARCHAR(200),
    description TEXT,
    department_id INT,
    manager_id INT,
    start_date DATE,
    end_date DATE,
    budget NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0044.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0044_business_id ON "Nova".t0044(business_id);
CREATE INDEX IF NOT EXISTS idx_t0044_business_id_id ON "Nova".t0044(business_id, id);


COMMENT ON TABLE "Nova".t0044 IS 'Projects';
COMMENT ON COLUMN "Nova".t0044.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0044.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0044.manager_id IS 'Reference to Manager';
COMMENT ON COLUMN "Nova".t0044.status IS 'Status';
COMMENT ON COLUMN "Nova".t0044.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0044_department_id ON "Nova".t0044(department_id);
CREATE INDEX IF NOT EXISTS idx_t0044_manager_id ON "Nova".t0044(manager_id);
CREATE INDEX IF NOT EXISTS idx_t0044_status ON "Nova".t0044(status);
CREATE INDEX IF NOT EXISTS idx_t0044_active ON "Nova".t0044(is_active);

-- Project Tasks
CREATE TABLE IF NOT EXISTS "Nova".t0045 (
    id SERIAL PRIMARY KEY,
    project_id INT,
    task_code VARCHAR(30),
    task_name VARCHAR(200),
    description TEXT,
    assigned_to VARCHAR(200),
    start_date DATE,
    end_date DATE,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    estimated_hours NUMERIC(8,2),
    actual_hours NUMERIC(8,2),
    parent_task_id INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0045.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0045_business_id ON "Nova".t0045(business_id);
CREATE INDEX IF NOT EXISTS idx_t0045_business_id_id ON "Nova".t0045(business_id, id);


COMMENT ON TABLE "Nova".t0045 IS 'Project Tasks';
COMMENT ON COLUMN "Nova".t0045.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0045.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0045.status IS 'Status';
COMMENT ON COLUMN "Nova".t0045.parent_task_id IS 'Reference to Parent_Task';
COMMENT ON COLUMN "Nova".t0045.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0045_project_id ON "Nova".t0045(project_id);
CREATE INDEX IF NOT EXISTS idx_t0045_status ON "Nova".t0045(status);
CREATE INDEX IF NOT EXISTS idx_t0045_parent_task_id ON "Nova".t0045(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_t0045_active ON "Nova".t0045(is_active);

-- Project Resource Allocations
CREATE TABLE IF NOT EXISTS "Nova".t0046 (
    id SERIAL PRIMARY KEY,
    project_id INT,
    employee_id INT,
    allocation_pct NUMERIC(5,2),
    start_date DATE,
    end_date DATE,
    role VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0046.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0046_business_id ON "Nova".t0046(business_id);
CREATE INDEX IF NOT EXISTS idx_t0046_business_id_id ON "Nova".t0046(business_id, id);


COMMENT ON TABLE "Nova".t0046 IS 'Project Resource Allocations';
COMMENT ON COLUMN "Nova".t0046.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0046.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0046.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0046.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0046_project_id ON "Nova".t0046(project_id);
CREATE INDEX IF NOT EXISTS idx_t0046_employee_id ON "Nova".t0046(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0046_active ON "Nova".t0046(is_active);

-- Project Timesheets
CREATE TABLE IF NOT EXISTS "Nova".t0047 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    project_id INT,
    task_id INT,
    date DATE,
    hours NUMERIC(8,2),
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    approved_by VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0047.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0047_business_id ON "Nova".t0047(business_id);
CREATE INDEX IF NOT EXISTS idx_t0047_business_id_id ON "Nova".t0047(business_id, id);


COMMENT ON TABLE "Nova".t0047 IS 'Project Timesheets';
COMMENT ON COLUMN "Nova".t0047.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0047.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0047.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0047.task_id IS 'Reference to Task';
COMMENT ON COLUMN "Nova".t0047.status IS 'Status';
COMMENT ON COLUMN "Nova".t0047.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0047_employee_id ON "Nova".t0047(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0047_project_id ON "Nova".t0047(project_id);
CREATE INDEX IF NOT EXISTS idx_t0047_task_id ON "Nova".t0047(task_id);
CREATE INDEX IF NOT EXISTS idx_t0047_status ON "Nova".t0047(status);
CREATE INDEX IF NOT EXISTS idx_t0047_active ON "Nova".t0047(is_active);

-- Service Requests
CREATE TABLE IF NOT EXISTS "Nova".t0048 (
    id SERIAL PRIMARY KEY,
    request_code VARCHAR(30),
    subject VARCHAR(200),
    description TEXT,
    customer_id INT,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    resolution TEXT,
    resolved_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0048.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0048_business_id ON "Nova".t0048(business_id);
CREATE INDEX IF NOT EXISTS idx_t0048_business_id_id ON "Nova".t0048(business_id, id);


COMMENT ON TABLE "Nova".t0048 IS 'Service Requests';
COMMENT ON COLUMN "Nova".t0048.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0048.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0048.status IS 'Status';
COMMENT ON COLUMN "Nova".t0048.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0048_customer_id ON "Nova".t0048(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0048_status ON "Nova".t0048(status);
CREATE INDEX IF NOT EXISTS idx_t0048_active ON "Nova".t0048(is_active);

-- Customer Contracts
CREATE TABLE IF NOT EXISTS "Nova".t0049 (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(30),
    contract_name VARCHAR(200),
    customer_id INT,
    contract_type VARCHAR(30),
    start_date DATE,
    end_date DATE,
    value NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0049.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0049_business_id ON "Nova".t0049(business_id);
CREATE INDEX IF NOT EXISTS idx_t0049_business_id_id ON "Nova".t0049(business_id, id);


COMMENT ON TABLE "Nova".t0049 IS 'Customer Contracts';
COMMENT ON COLUMN "Nova".t0049.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0049.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0049.status IS 'Status';
COMMENT ON COLUMN "Nova".t0049.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0049_customer_id ON "Nova".t0049(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0049_status ON "Nova".t0049(status);
CREATE INDEX IF NOT EXISTS idx_t0049_active ON "Nova".t0049(is_active);

-- SLA Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0050 (
    id SERIAL PRIMARY KEY,
    contract_id INT,
    sla_code VARCHAR(30),
    sla_name VARCHAR(200),
    response_time NUMERIC(12,2),
    resolution_time NUMERIC(12,2),
    penalty_rate NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0050.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0050_business_id ON "Nova".t0050(business_id);
CREATE INDEX IF NOT EXISTS idx_t0050_business_id_id ON "Nova".t0050(business_id, id);


COMMENT ON TABLE "Nova".t0050 IS 'SLA Definitions';
COMMENT ON COLUMN "Nova".t0050.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0050.contract_id IS 'Reference to Contract';
COMMENT ON COLUMN "Nova".t0050.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0050_contract_id ON "Nova".t0050(contract_id);
CREATE INDEX IF NOT EXISTS idx_t0050_active ON "Nova".t0050(is_active);

-- Search Index
CREATE TABLE IF NOT EXISTS "Nova".t0051 (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(30),
    entity_id INT,
    keywords TEXT,
    search_content TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0051.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0051_business_id ON "Nova".t0051(business_id);
CREATE INDEX IF NOT EXISTS idx_t0051_business_id_id ON "Nova".t0051(business_id, id);


COMMENT ON TABLE "Nova".t0051 IS 'Search Index';
COMMENT ON COLUMN "Nova".t0051.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0051.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0051.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0051_entity_id ON "Nova".t0051(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0051_active ON "Nova".t0051(is_active);

-- KPI Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0052 (
    id SERIAL PRIMARY KEY,
    kpi_code VARCHAR(30),
    kpi_name VARCHAR(200),
    category VARCHAR(200),
    metric_unit VARCHAR(200),
    target_value NUMERIC(12,2),
    formula VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0052.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0052_business_id ON "Nova".t0052(business_id);
CREATE INDEX IF NOT EXISTS idx_t0052_business_id_id ON "Nova".t0052(business_id, id);


COMMENT ON TABLE "Nova".t0052 IS 'KPI Definitions';
COMMENT ON COLUMN "Nova".t0052.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0052.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0052_active ON "Nova".t0052(is_active);

-- KPI Values
CREATE TABLE IF NOT EXISTS "Nova".t0053 (
    id SERIAL PRIMARY KEY,
    kpi_id INT,
    period VARCHAR(200),
    period_type VARCHAR(30),
    actual_value NUMERIC(12,2),
    target_value NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0053.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0053_business_id ON "Nova".t0053(business_id);
CREATE INDEX IF NOT EXISTS idx_t0053_business_id_id ON "Nova".t0053(business_id, id);


COMMENT ON TABLE "Nova".t0053 IS 'KPI Values';
COMMENT ON COLUMN "Nova".t0053.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0053.kpi_id IS 'Reference to Kpi';
COMMENT ON COLUMN "Nova".t0053.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0053_kpi_id ON "Nova".t0053(kpi_id);
CREATE INDEX IF NOT EXISTS idx_t0053_active ON "Nova".t0053(is_active);

-- BI Dashboards
CREATE TABLE IF NOT EXISTS "Nova".t0054 (
    id SERIAL PRIMARY KEY,
    dashboard_code VARCHAR(30),
    dashboard_name VARCHAR(200),
    owner_id INT,
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0054.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0054_business_id ON "Nova".t0054(business_id);
CREATE INDEX IF NOT EXISTS idx_t0054_business_id_id ON "Nova".t0054(business_id, id);


COMMENT ON TABLE "Nova".t0054 IS 'BI Dashboards';
COMMENT ON COLUMN "Nova".t0054.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0054.owner_id IS 'Reference to Owner';
COMMENT ON COLUMN "Nova".t0054.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0054_owner_id ON "Nova".t0054(owner_id);
CREATE INDEX IF NOT EXISTS idx_t0054_active ON "Nova".t0054(is_active);

-- Dashboard Widgets
CREATE TABLE IF NOT EXISTS "Nova".t0055 (
    id SERIAL PRIMARY KEY,
    dashboard_id INT,
    widget_type VARCHAR(30),
    title VARCHAR(200),
    config JSONB,
    position INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0055.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0055_business_id ON "Nova".t0055(business_id);
CREATE INDEX IF NOT EXISTS idx_t0055_business_id_id ON "Nova".t0055(business_id, id);


COMMENT ON TABLE "Nova".t0055 IS 'Dashboard Widgets';
COMMENT ON COLUMN "Nova".t0055.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0055.dashboard_id IS 'Reference to Dashboard';
COMMENT ON COLUMN "Nova".t0055.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0055_dashboard_id ON "Nova".t0055(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_t0055_active ON "Nova".t0055(is_active);

-- API Keys
CREATE TABLE IF NOT EXISTS "Nova".t0056 (
    id SERIAL PRIMARY KEY,
    key_name VARCHAR(200),
    api_key VARCHAR(255),
    client_id INT,
    permissions TEXT[],
    expires_at DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0056.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0056_business_id ON "Nova".t0056(business_id);
CREATE INDEX IF NOT EXISTS idx_t0056_business_id_id ON "Nova".t0056(business_id, id);


COMMENT ON TABLE "Nova".t0056 IS 'API Keys';
COMMENT ON COLUMN "Nova".t0056.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0056.client_id IS 'Reference to Client';
COMMENT ON COLUMN "Nova".t0056.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0056_client_id ON "Nova".t0056(client_id);
CREATE INDEX IF NOT EXISTS idx_t0056_active ON "Nova".t0056(is_active);

-- Integration Configurations
CREATE TABLE IF NOT EXISTS "Nova".t0057 (
    id SERIAL PRIMARY KEY,
    integration_code VARCHAR(30),
    integration_name VARCHAR(200),
    provider VARCHAR(200),
    config JSONB,
    credentials JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0057.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0057_business_id ON "Nova".t0057(business_id);
CREATE INDEX IF NOT EXISTS idx_t0057_business_id_id ON "Nova".t0057(business_id, id);


COMMENT ON TABLE "Nova".t0057 IS 'Integration Configurations';
COMMENT ON COLUMN "Nova".t0057.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0057.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0057_active ON "Nova".t0057(is_active);

-- Integration Sync Logs
CREATE TABLE IF NOT EXISTS "Nova".t0058 (
    id SERIAL PRIMARY KEY,
    integration_id INT,
    entity_type VARCHAR(30),
    action VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    message TEXT,
    synced_at DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0058.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0058_business_id ON "Nova".t0058(business_id);
CREATE INDEX IF NOT EXISTS idx_t0058_business_id_id ON "Nova".t0058(business_id, id);


COMMENT ON TABLE "Nova".t0058 IS 'Integration Sync Logs';
COMMENT ON COLUMN "Nova".t0058.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0058.integration_id IS 'Reference to Integration';
COMMENT ON COLUMN "Nova".t0058.status IS 'Status';
COMMENT ON COLUMN "Nova".t0058.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0058_integration_id ON "Nova".t0058(integration_id);
CREATE INDEX IF NOT EXISTS idx_t0058_status ON "Nova".t0058(status);
CREATE INDEX IF NOT EXISTS idx_t0058_active ON "Nova".t0058(is_active);

-- Enterprise Tenants
CREATE TABLE IF NOT EXISTS "Nova".t0059 (
    id SERIAL PRIMARY KEY,
    tenant_code VARCHAR(30),
    tenant_name VARCHAR(200),
    domain VARCHAR(200),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0059 IS 'Enterprise Tenants';
COMMENT ON COLUMN "Nova".t0059.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0059.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0059_active ON "Nova".t0059(is_active);

-- Workflow Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0060 (
    id SERIAL PRIMARY KEY,
    workflow_code VARCHAR(30),
    workflow_name VARCHAR(200),
    entity_type VARCHAR(30),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0060.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0060_business_id ON "Nova".t0060(business_id);
CREATE INDEX IF NOT EXISTS idx_t0060_business_id_id ON "Nova".t0060(business_id, id);


COMMENT ON TABLE "Nova".t0060 IS 'Workflow Definitions';
COMMENT ON COLUMN "Nova".t0060.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0060.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0060_active ON "Nova".t0060(is_active);

-- Workflow Instances
CREATE TABLE IF NOT EXISTS "Nova".t0061 (
    id SERIAL PRIMARY KEY,
    workflow_id INT,
    entity_type VARCHAR(30),
    entity_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    current_step VARCHAR(200),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0061.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0061_business_id ON "Nova".t0061(business_id);
CREATE INDEX IF NOT EXISTS idx_t0061_business_id_id ON "Nova".t0061(business_id, id);


COMMENT ON TABLE "Nova".t0061 IS 'Workflow Instances';
COMMENT ON COLUMN "Nova".t0061.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0061.workflow_id IS 'Reference to Workflow';
COMMENT ON COLUMN "Nova".t0061.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0061.status IS 'Status';
COMMENT ON COLUMN "Nova".t0061.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0061_workflow_id ON "Nova".t0061(workflow_id);
CREATE INDEX IF NOT EXISTS idx_t0061_entity_id ON "Nova".t0061(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0061_status ON "Nova".t0061(status);
CREATE INDEX IF NOT EXISTS idx_t0061_active ON "Nova".t0061(is_active);

-- Enterprise Documents
CREATE TABLE IF NOT EXISTS "Nova".t0062 (
    id SERIAL PRIMARY KEY,
    document_code VARCHAR(30),
    document_name VARCHAR(200),
    entity_type VARCHAR(30),
    entity_id INT,
    file_path TEXT,
    file_type VARCHAR(30),
    file_size NUMERIC(12,2),
    version NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0062.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0062_business_id ON "Nova".t0062(business_id);
CREATE INDEX IF NOT EXISTS idx_t0062_business_id_id ON "Nova".t0062(business_id, id);


COMMENT ON TABLE "Nova".t0062 IS 'Enterprise Documents';
COMMENT ON COLUMN "Nova".t0062.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0062.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0062.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0062_entity_id ON "Nova".t0062(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0062_active ON "Nova".t0062(is_active);

-- Compliance Rules
CREATE TABLE IF NOT EXISTS "Nova".t0063 (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(30),
    rule_name VARCHAR(200),
    category VARCHAR(200),
    description TEXT,
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0063.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0063_business_id ON "Nova".t0063(business_id);
CREATE INDEX IF NOT EXISTS idx_t0063_business_id_id ON "Nova".t0063(business_id, id);


COMMENT ON TABLE "Nova".t0063 IS 'Compliance Rules';
COMMENT ON COLUMN "Nova".t0063.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0063.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0063_active ON "Nova".t0063(is_active);

-- Stock Movements
CREATE TABLE IF NOT EXISTS "Nova".t0064 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    warehouse_id INT,
    movement_type VARCHAR(30),
    reference_type VARCHAR(30),
    reference_id INT,
    qty_change NUMERIC(12,2),
    balance_after NUMERIC(12,2),
    description TEXT,
    movement_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0064.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0064_business_id ON "Nova".t0064(business_id);
CREATE INDEX IF NOT EXISTS idx_t0064_business_id_id ON "Nova".t0064(business_id, id);


COMMENT ON TABLE "Nova".t0064 IS 'Stock Movements';
COMMENT ON COLUMN "Nova".t0064.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0064.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0064.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0064.reference_id IS 'Reference to Reference';
COMMENT ON COLUMN "Nova".t0064.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0064_product_id ON "Nova".t0064(product_id);
CREATE INDEX IF NOT EXISTS idx_t0064_warehouse_id ON "Nova".t0064(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0064_reference_id ON "Nova".t0064(reference_id);
CREATE INDEX IF NOT EXISTS idx_t0064_active ON "Nova".t0064(is_active);

-- Bill of Materials
CREATE TABLE IF NOT EXISTS "Nova".t0065 (
    id SERIAL PRIMARY KEY,
    bom_code VARCHAR(30),
    bom_name VARCHAR(200),
    product_id INT,
    quantity NUMERIC(12,2),
    version NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0065.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0065_business_id ON "Nova".t0065(business_id);
CREATE INDEX IF NOT EXISTS idx_t0065_business_id_id ON "Nova".t0065(business_id, id);


COMMENT ON TABLE "Nova".t0065 IS 'Bill of Materials';
COMMENT ON COLUMN "Nova".t0065.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0065.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0065.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0065_product_id ON "Nova".t0065(product_id);
CREATE INDEX IF NOT EXISTS idx_t0065_active ON "Nova".t0065(is_active);

-- BOM Lines
CREATE TABLE IF NOT EXISTS "Nova".t0066 (
    id SERIAL PRIMARY KEY,
    bom_id INT,
    component_id INT,
    component_name VARCHAR(200),
    quantity NUMERIC(12,2),
    uom_id INT,
    scrap_pct NUMERIC(5,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0066.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0066_business_id ON "Nova".t0066(business_id);
CREATE INDEX IF NOT EXISTS idx_t0066_business_id_id ON "Nova".t0066(business_id, id);


COMMENT ON TABLE "Nova".t0066 IS 'BOM Lines';
COMMENT ON COLUMN "Nova".t0066.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0066.bom_id IS 'Reference to Bom';
COMMENT ON COLUMN "Nova".t0066.component_id IS 'Reference to Component';
COMMENT ON COLUMN "Nova".t0066.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0066.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0066_bom_id ON "Nova".t0066(bom_id);
CREATE INDEX IF NOT EXISTS idx_t0066_component_id ON "Nova".t0066(component_id);
CREATE INDEX IF NOT EXISTS idx_t0066_uom_id ON "Nova".t0066(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0066_active ON "Nova".t0066(is_active);

-- Sales Quotations
CREATE TABLE IF NOT EXISTS "Nova".t0067 (
    id SERIAL PRIMARY KEY,
    quote_number VARCHAR(200),
    customer_id INT,
    quote_date DATE,
    valid_until DATE,
    subtotal NUMERIC(12,2),
    tax NUMERIC(12,2),
    grand_total NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    converted_order_id INT REFERENCES "Nova".t0012(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0067.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0067_business_id ON "Nova".t0067(business_id);
CREATE INDEX IF NOT EXISTS idx_t0067_business_id_id ON "Nova".t0067(business_id, id);


COMMENT ON TABLE "Nova".t0067 IS 'Sales Quotations';
COMMENT ON COLUMN "Nova".t0067.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0067.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0067.status IS 'Status';
COMMENT ON COLUMN "Nova".t0067.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0067_customer_id ON "Nova".t0067(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0067_status ON "Nova".t0067(status);
CREATE INDEX IF NOT EXISTS idx_t0067_active ON "Nova".t0067(is_active);

-- Sales Quotation Lines
CREATE TABLE IF NOT EXISTS "Nova".t0068 (
    id SERIAL PRIMARY KEY,
    quotation_id INT,
    product_id INT,
    product_name VARCHAR(200),
    uom_id INT,
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0068.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0068_business_id ON "Nova".t0068(business_id);
CREATE INDEX IF NOT EXISTS idx_t0068_business_id_id ON "Nova".t0068(business_id, id);


COMMENT ON TABLE "Nova".t0068 IS 'Sales Quotation Lines';
COMMENT ON COLUMN "Nova".t0068.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0068.quotation_id IS 'Reference to Quotation';
COMMENT ON COLUMN "Nova".t0068.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0068.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0068.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0068_quotation_id ON "Nova".t0068(quotation_id);
CREATE INDEX IF NOT EXISTS idx_t0068_product_id ON "Nova".t0068(product_id);
CREATE INDEX IF NOT EXISTS idx_t0068_uom_id ON "Nova".t0068(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0068_active ON "Nova".t0068(is_active);

-- Purchase Requisitions
CREATE TABLE IF NOT EXISTS "Nova".t0069 (
    id SERIAL PRIMARY KEY,
    req_number VARCHAR(200),
    title VARCHAR(200),
    description TEXT,
    department_id INT,
    requested_by VARCHAR(200),
    approved_by VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    priority VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0069.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0069_business_id ON "Nova".t0069(business_id);
CREATE INDEX IF NOT EXISTS idx_t0069_business_id_id ON "Nova".t0069(business_id, id);


COMMENT ON TABLE "Nova".t0069 IS 'Purchase Requisitions';
COMMENT ON COLUMN "Nova".t0069.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0069.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0069.status IS 'Status';
COMMENT ON COLUMN "Nova".t0069.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0069_department_id ON "Nova".t0069(department_id);
CREATE INDEX IF NOT EXISTS idx_t0069_status ON "Nova".t0069(status);
CREATE INDEX IF NOT EXISTS idx_t0069_active ON "Nova".t0069(is_active);

-- Purchase Requisition Lines
CREATE TABLE IF NOT EXISTS "Nova".t0070 (
    id SERIAL PRIMARY KEY,
    requisition_id INT,
    product_id INT,
    description TEXT,
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    uom_id INT,
    expected_date DATE,
    notes TEXT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0070.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0070_business_id ON "Nova".t0070(business_id);
CREATE INDEX IF NOT EXISTS idx_t0070_business_id_id ON "Nova".t0070(business_id, id);


COMMENT ON TABLE "Nova".t0070 IS 'Purchase Requisition Lines';
COMMENT ON COLUMN "Nova".t0070.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0070.requisition_id IS 'Reference to Requisition';
COMMENT ON COLUMN "Nova".t0070.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0070.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0070.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0070_requisition_id ON "Nova".t0070(requisition_id);
CREATE INDEX IF NOT EXISTS idx_t0070_product_id ON "Nova".t0070(product_id);
CREATE INDEX IF NOT EXISTS idx_t0070_uom_id ON "Nova".t0070(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0070_active ON "Nova".t0070(is_active);

-- Request for Quotations (RFQ)
CREATE TABLE IF NOT EXISTS "Nova".t0071 (
    id SERIAL PRIMARY KEY,
    rfq_number VARCHAR(200),
    title VARCHAR(200),
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    due_date DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0071.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0071_business_id ON "Nova".t0071(business_id);
CREATE INDEX IF NOT EXISTS idx_t0071_business_id_id ON "Nova".t0071(business_id, id);


COMMENT ON TABLE "Nova".t0071 IS 'Request for Quotations (RFQ)';
COMMENT ON COLUMN "Nova".t0071.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0071.status IS 'Status';
COMMENT ON COLUMN "Nova".t0071.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0071_status ON "Nova".t0071(status);
CREATE INDEX IF NOT EXISTS idx_t0071_active ON "Nova".t0071(is_active);

-- RFQ Lines
CREATE TABLE IF NOT EXISTS "Nova".t0072 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    product_id INT,
    description TEXT,
    qty NUMERIC(12,2),
    uom_id INT,
    line_number NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0072.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0072_business_id ON "Nova".t0072(business_id);
CREATE INDEX IF NOT EXISTS idx_t0072_business_id_id ON "Nova".t0072(business_id, id);


COMMENT ON TABLE "Nova".t0072 IS 'RFQ Lines';
COMMENT ON COLUMN "Nova".t0072.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0072.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0072.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0072.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0072.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0072_rfq_id ON "Nova".t0072(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0072_product_id ON "Nova".t0072(product_id);
CREATE INDEX IF NOT EXISTS idx_t0072_uom_id ON "Nova".t0072(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0072_active ON "Nova".t0072(is_active);

-- RFQ Vendors
CREATE TABLE IF NOT EXISTS "Nova".t0073 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    vendor_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0073.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0073_business_id ON "Nova".t0073(business_id);
CREATE INDEX IF NOT EXISTS idx_t0073_business_id_id ON "Nova".t0073(business_id, id);


COMMENT ON TABLE "Nova".t0073 IS 'RFQ Vendors';
COMMENT ON COLUMN "Nova".t0073.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0073.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0073.vendor_id IS 'Reference to Vendor';
COMMENT ON COLUMN "Nova".t0073.status IS 'Status';
COMMENT ON COLUMN "Nova".t0073.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0073_rfq_id ON "Nova".t0073(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0073_vendor_id ON "Nova".t0073(vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0073_status ON "Nova".t0073(status);
CREATE INDEX IF NOT EXISTS idx_t0073_active ON "Nova".t0073(is_active);

-- RFQ Vendor Quotes
CREATE TABLE IF NOT EXISTS "Nova".t0074 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    vendor_id INT,
    rfq_vendor_id INT,
    line_id INT,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    delivery_days INT,
    currency VARCHAR(30),
    valid_until DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0074.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0074_business_id ON "Nova".t0074(business_id);
CREATE INDEX IF NOT EXISTS idx_t0074_business_id_id ON "Nova".t0074(business_id, id);


COMMENT ON TABLE "Nova".t0074 IS 'RFQ Vendor Quotes';
COMMENT ON COLUMN "Nova".t0074.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0074.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0074.vendor_id IS 'Reference to Vendor';
COMMENT ON COLUMN "Nova".t0074.rfq_vendor_id IS 'Reference to Rfq_Vendor';
COMMENT ON COLUMN "Nova".t0074.line_id IS 'Reference to Line';
COMMENT ON COLUMN "Nova".t0074.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0074_rfq_id ON "Nova".t0074(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0074_vendor_id ON "Nova".t0074(vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0074_rfq_vendor_id ON "Nova".t0074(rfq_vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0074_line_id ON "Nova".t0074(line_id);
CREATE INDEX IF NOT EXISTS idx_t0074_active ON "Nova".t0074(is_active);

-- Goods Receipts
CREATE TABLE IF NOT EXISTS "Nova".t0075 (
    id SERIAL PRIMARY KEY,
    receipt_number VARCHAR(200),
    purchase_order_id INT,
    receipt_date DATE,
    warehouse_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0075.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0075_business_id ON "Nova".t0075(business_id);
CREATE INDEX IF NOT EXISTS idx_t0075_business_id_id ON "Nova".t0075(business_id, id);


COMMENT ON TABLE "Nova".t0075 IS 'Goods Receipts';
COMMENT ON COLUMN "Nova".t0075.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0075.purchase_order_id IS 'Reference to Purchase_Order';
COMMENT ON COLUMN "Nova".t0075.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0075.status IS 'Status';
COMMENT ON COLUMN "Nova".t0075.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0075_purchase_order_id ON "Nova".t0075(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0075_warehouse_id ON "Nova".t0075(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0075_status ON "Nova".t0075(status);
CREATE INDEX IF NOT EXISTS idx_t0075_active ON "Nova".t0075(is_active);

-- Goods Receipt Lines
CREATE TABLE IF NOT EXISTS "Nova".t0076 (
    id SERIAL PRIMARY KEY,
    receipt_id INT,
    purchase_order_line_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty_received NUMERIC(12,2),
    qty_ordered NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    batch_number VARCHAR(255),
    manufacturing_date DATE,
    expiry_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0076.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0076_business_id ON "Nova".t0076(business_id);
CREATE INDEX IF NOT EXISTS idx_t0076_business_id_id ON "Nova".t0076(business_id, id);


COMMENT ON TABLE "Nova".t0076 IS 'Goods Receipt Lines';
COMMENT ON COLUMN "Nova".t0076.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0076.receipt_id IS 'Reference to Receipt';
COMMENT ON COLUMN "Nova".t0076.purchase_order_line_id IS 'Reference to Purchase_Order_Line';
COMMENT ON COLUMN "Nova".t0076.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0076.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0076.batch_number IS 'Batch or lot number captured at goods receipt';
COMMENT ON COLUMN "Nova".t0076.manufacturing_date IS 'Manufacturing / production date';
COMMENT ON COLUMN "Nova".t0076.expiry_date IS 'Expiration date';
COMMENT ON COLUMN "Nova".t0076.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0076_receipt_id ON "Nova".t0076(receipt_id);
CREATE INDEX IF NOT EXISTS idx_t0076_purchase_order_line_id ON "Nova".t0076(purchase_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0076_product_id ON "Nova".t0076(product_id);
CREATE INDEX IF NOT EXISTS idx_t0076_uom_id ON "Nova".t0076(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0076_batch_number ON "Nova".t0076(batch_number);
CREATE INDEX IF NOT EXISTS idx_t0076_expiry_date ON "Nova".t0076(expiry_date);
CREATE INDEX IF NOT EXISTS idx_t0076_active ON "Nova".t0076(is_active);

-- Sales Deliveries
CREATE TABLE IF NOT EXISTS "Nova".t0077 (
    id SERIAL PRIMARY KEY,
    delivery_number VARCHAR(200),
    sales_order_id INT,
    delivery_date DATE,
    warehouse_id INT,
    freight_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    delivery_route VARCHAR(100),
    actual_delivery_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0077.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0077_business_id ON "Nova".t0077(business_id);
CREATE INDEX IF NOT EXISTS idx_t0077_business_id_id ON "Nova".t0077(business_id, id);


COMMENT ON TABLE "Nova".t0077 IS 'Sales Deliveries';
COMMENT ON COLUMN "Nova".t0077.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0077.sales_order_id IS 'Reference to Sales_Order';
COMMENT ON COLUMN "Nova".t0077.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0077.freight_cost IS 'Actual freight / transport cost incurred for delivery';
COMMENT ON COLUMN "Nova".t0077.delivery_route IS 'Assigned delivery route / zone';
COMMENT ON COLUMN "Nova".t0077.actual_delivery_date IS 'Actual date order delivery completed';
COMMENT ON COLUMN "Nova".t0077.status IS 'Status';
COMMENT ON COLUMN "Nova".t0077.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0077_sales_order_id ON "Nova".t0077(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0077_warehouse_id ON "Nova".t0077(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0077_status ON "Nova".t0077(status);
CREATE INDEX IF NOT EXISTS idx_t0077_active ON "Nova".t0077(is_active);
CREATE INDEX IF NOT EXISTS idx_t0077_delivery_route ON "Nova".t0077(delivery_route);
CREATE INDEX IF NOT EXISTS idx_t0077_actual_delivery_date ON "Nova".t0077(actual_delivery_date);

-- Sales Delivery Lines
CREATE TABLE IF NOT EXISTS "Nova".t0078 (
    id SERIAL PRIMARY KEY,
    delivery_id INT,
    sales_order_line_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty_shipped NUMERIC(12,2),
    qty_ordered NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0078.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0078_business_id ON "Nova".t0078(business_id);
CREATE INDEX IF NOT EXISTS idx_t0078_business_id_id ON "Nova".t0078(business_id, id);


COMMENT ON TABLE "Nova".t0078 IS 'Sales Delivery Lines';
COMMENT ON COLUMN "Nova".t0078.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0078.delivery_id IS 'Reference to Delivery';
COMMENT ON COLUMN "Nova".t0078.sales_order_line_id IS 'Reference to Sales_Order_Line';
COMMENT ON COLUMN "Nova".t0078.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0078.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0078.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0078_delivery_id ON "Nova".t0078(delivery_id);
CREATE INDEX IF NOT EXISTS idx_t0078_sales_order_line_id ON "Nova".t0078(sales_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0078_product_id ON "Nova".t0078(product_id);
CREATE INDEX IF NOT EXISTS idx_t0078_uom_id ON "Nova".t0078(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0078_active ON "Nova".t0078(is_active);

-- Sales Returns
CREATE TABLE IF NOT EXISTS "Nova".t0079 (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(200),
    sales_order_id INT,
    customer_id INT,
    return_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    reason VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0079.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0079_business_id ON "Nova".t0079(business_id);
CREATE INDEX IF NOT EXISTS idx_t0079_business_id_id ON "Nova".t0079(business_id, id);


COMMENT ON TABLE "Nova".t0079 IS 'Sales Returns';
COMMENT ON COLUMN "Nova".t0079.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0079.sales_order_id IS 'Reference to Sales_Order';
COMMENT ON COLUMN "Nova".t0079.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0079.status IS 'Status';
COMMENT ON COLUMN "Nova".t0079.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0079_sales_order_id ON "Nova".t0079(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0079_customer_id ON "Nova".t0079(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0079_status ON "Nova".t0079(status);
CREATE INDEX IF NOT EXISTS idx_t0079_active ON "Nova".t0079(is_active);

-- Sales Return Lines
CREATE TABLE IF NOT EXISTS "Nova".t0080 (
    id SERIAL PRIMARY KEY,
    return_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0080.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0080_business_id ON "Nova".t0080(business_id);
CREATE INDEX IF NOT EXISTS idx_t0080_business_id_id ON "Nova".t0080(business_id, id);


COMMENT ON TABLE "Nova".t0080 IS 'Sales Return Lines';
COMMENT ON COLUMN "Nova".t0080.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0080.return_id IS 'Reference to Return';
COMMENT ON COLUMN "Nova".t0080.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0080.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0080.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0080_return_id ON "Nova".t0080(return_id);
CREATE INDEX IF NOT EXISTS idx_t0080_product_id ON "Nova".t0080(product_id);
CREATE INDEX IF NOT EXISTS idx_t0080_uom_id ON "Nova".t0080(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0080_active ON "Nova".t0080(is_active);

-- Purchase Returns
CREATE TABLE IF NOT EXISTS "Nova".t0081 (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(200),
    purchase_order_id INT,
    supplier_id INT,
    return_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    reason VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0081.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0081_business_id ON "Nova".t0081(business_id);
CREATE INDEX IF NOT EXISTS idx_t0081_business_id_id ON "Nova".t0081(business_id, id);


COMMENT ON TABLE "Nova".t0081 IS 'Purchase Returns';
COMMENT ON COLUMN "Nova".t0081.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0081.purchase_order_id IS 'Reference to Purchase_Order';
COMMENT ON COLUMN "Nova".t0081.supplier_id IS 'Reference to Supplier';
COMMENT ON COLUMN "Nova".t0081.status IS 'Status';
COMMENT ON COLUMN "Nova".t0081.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0081_purchase_order_id ON "Nova".t0081(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0081_supplier_id ON "Nova".t0081(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0081_status ON "Nova".t0081(status);
CREATE INDEX IF NOT EXISTS idx_t0081_active ON "Nova".t0081(is_active);

-- Purchase Return Lines
CREATE TABLE IF NOT EXISTS "Nova".t0082 (
    id SERIAL PRIMARY KEY,
    return_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0082.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0082_business_id ON "Nova".t0082(business_id);
CREATE INDEX IF NOT EXISTS idx_t0082_business_id_id ON "Nova".t0082(business_id, id);


COMMENT ON TABLE "Nova".t0082 IS 'Purchase Return Lines';
COMMENT ON COLUMN "Nova".t0082.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0082.return_id IS 'Reference to Return';
COMMENT ON COLUMN "Nova".t0082.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0082.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0082.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0082_return_id ON "Nova".t0082(return_id);
CREATE INDEX IF NOT EXISTS idx_t0082_product_id ON "Nova".t0082(product_id);
CREATE INDEX IF NOT EXISTS idx_t0082_uom_id ON "Nova".t0082(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0082_active ON "Nova".t0082(is_active);

-- Price List Items
CREATE TABLE IF NOT EXISTS "Nova".t0084 (
    id SERIAL PRIMARY KEY,
    price_list_id INT,
    product_id INT,
    unit_price NUMERIC(12,2),
    min_qty INT,
    uom_id INT,
    effective_from DATE,
    effective_to DATE,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0084.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0084_business_id ON "Nova".t0084(business_id);
CREATE INDEX IF NOT EXISTS idx_t0084_business_id_id ON "Nova".t0084(business_id, id);


COMMENT ON TABLE "Nova".t0084 IS 'Price List Items';
COMMENT ON COLUMN "Nova".t0084.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0084.price_list_id IS 'Reference to Price_List';
COMMENT ON COLUMN "Nova".t0084.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0084.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0084.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0084_price_list_id ON "Nova".t0084(price_list_id);
CREATE INDEX IF NOT EXISTS idx_t0084_product_id ON "Nova".t0084(product_id);
CREATE INDEX IF NOT EXISTS idx_t0084_uom_id ON "Nova".t0084(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0084_active ON "Nova".t0084(is_active);

-- Tax Rules
CREATE TABLE IF NOT EXISTS "Nova".t0086 (
    id SERIAL PRIMARY KEY,
    tax_rate_id INT,
    applies_to VARCHAR(200),
    target_id INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0086.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0086_business_id ON "Nova".t0086(business_id);
CREATE INDEX IF NOT EXISTS idx_t0086_business_id_id ON "Nova".t0086(business_id, id);


COMMENT ON TABLE "Nova".t0086 IS 'Tax Rules';
COMMENT ON COLUMN "Nova".t0086.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0086.tax_rate_id IS 'Reference to Tax_Rate';
COMMENT ON COLUMN "Nova".t0086.target_id IS 'Reference to Target';
COMMENT ON COLUMN "Nova".t0086.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0086_tax_rate_id ON "Nova".t0086(tax_rate_id);
CREATE INDEX IF NOT EXISTS idx_t0086_target_id ON "Nova".t0086(target_id);
CREATE INDEX IF NOT EXISTS idx_t0086_active ON "Nova".t0086(is_active);

-- Serial Numbers
CREATE TABLE IF NOT EXISTS "Nova".t0087 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    serial_number VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    warehouse_id INT,
    purchase_order_line_id INT,
    sales_order_line_id INT,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0087.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0087_business_id ON "Nova".t0087(business_id);
CREATE INDEX IF NOT EXISTS idx_t0087_business_id_id ON "Nova".t0087(business_id, id);


COMMENT ON TABLE "Nova".t0087 IS 'Serial Numbers';
COMMENT ON COLUMN "Nova".t0087.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0087.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0087.status IS 'Status';
COMMENT ON COLUMN "Nova".t0087.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0087.purchase_order_line_id IS 'Reference to Purchase_Order_Line';
COMMENT ON COLUMN "Nova".t0087.sales_order_line_id IS 'Reference to Sales_Order_Line';
COMMENT ON COLUMN "Nova".t0087.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0087_product_id ON "Nova".t0087(product_id);
CREATE INDEX IF NOT EXISTS idx_t0087_status ON "Nova".t0087(status);
CREATE INDEX IF NOT EXISTS idx_t0087_warehouse_id ON "Nova".t0087(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0087_purchase_order_line_id ON "Nova".t0087(purchase_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0087_sales_order_line_id ON "Nova".t0087(sales_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0087_active ON "Nova".t0087(is_active);

-- Batch Numbers
CREATE TABLE IF NOT EXISTS "Nova".t0088 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    batch_number VARCHAR(255),
    expiry_date DATE,
    manufacturing_date DATE,
    quantity NUMERIC(12,2),
    warehouse_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0088.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0088_business_id ON "Nova".t0088(business_id);
CREATE INDEX IF NOT EXISTS idx_t0088_business_id_id ON "Nova".t0088(business_id, id);


COMMENT ON TABLE "Nova".t0088 IS 'Batch Numbers';
COMMENT ON COLUMN "Nova".t0088.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0088.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0088.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0088.status IS 'Status';
COMMENT ON COLUMN "Nova".t0088.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0088_product_id ON "Nova".t0088(product_id);
CREATE INDEX IF NOT EXISTS idx_t0088_warehouse_id ON "Nova".t0088(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0088_status ON "Nova".t0088(status);
CREATE INDEX IF NOT EXISTS idx_t0088_active ON "Nova".t0088(is_active);

-- Journal Entry Lines
CREATE TABLE IF NOT EXISTS "Nova".t0089 (
    id SERIAL PRIMARY KEY,
    journal_entry_id INT,
    account_id INT,
    debit NUMERIC(12,2),
    credit NUMERIC(12,2),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0089.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0089_business_id ON "Nova".t0089(business_id);
CREATE INDEX IF NOT EXISTS idx_t0089_business_id_id ON "Nova".t0089(business_id, id);


COMMENT ON TABLE "Nova".t0089 IS 'Journal Entry Lines';
COMMENT ON COLUMN "Nova".t0089.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0089.journal_entry_id IS 'Reference to Journal_Entry';
COMMENT ON COLUMN "Nova".t0089.account_id IS 'Reference to Account';
COMMENT ON COLUMN "Nova".t0089.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0089_journal_entry_id ON "Nova".t0089(journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_t0089_account_id ON "Nova".t0089(account_id);
CREATE INDEX IF NOT EXISTS idx_t0089_active ON "Nova".t0089(is_active);

-- CRM Leads
CREATE TABLE IF NOT EXISTS "Nova".t0092 (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(200),
    last_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(200),
    company VARCHAR(200),
    title VARCHAR(200),
    source VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0092.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0092_business_id ON "Nova".t0092(business_id);
CREATE INDEX IF NOT EXISTS idx_t0092_business_id_id ON "Nova".t0092(business_id, id);


COMMENT ON TABLE "Nova".t0092 IS 'CRM Leads';
COMMENT ON COLUMN "Nova".t0092.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0092.status IS 'Status';
COMMENT ON COLUMN "Nova".t0092.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0092_status ON "Nova".t0092(status);
CREATE INDEX IF NOT EXISTS idx_t0092_active ON "Nova".t0092(is_active);

-- CRM Lead Activities
CREATE TABLE IF NOT EXISTS "Nova".t0093 (
    id SERIAL PRIMARY KEY,
    lead_id INT,
    activity_type VARCHAR(30),
    subject VARCHAR(200),
    description TEXT,
    activity_date DATE,
    completed VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0093.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0093_business_id ON "Nova".t0093(business_id);
CREATE INDEX IF NOT EXISTS idx_t0093_business_id_id ON "Nova".t0093(business_id, id);


COMMENT ON TABLE "Nova".t0093 IS 'CRM Lead Activities';
COMMENT ON COLUMN "Nova".t0093.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0093.lead_id IS 'Reference to Lead';
COMMENT ON COLUMN "Nova".t0093.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0093_lead_id ON "Nova".t0093(lead_id);
CREATE INDEX IF NOT EXISTS idx_t0093_active ON "Nova".t0093(is_active);

-- CRM Opportunities
CREATE TABLE IF NOT EXISTS "Nova".t0094 (
    id SERIAL PRIMARY KEY,
    opportunity_name VARCHAR(200),
    lead_id INT,
    customer_id INT,
    stage VARCHAR(200),
    amount NUMERIC(12,2),
    probability NUMERIC(5,2),
    expected_close_date DATE,
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0094.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0094_business_id ON "Nova".t0094(business_id);
CREATE INDEX IF NOT EXISTS idx_t0094_business_id_id ON "Nova".t0094(business_id, id);


COMMENT ON TABLE "Nova".t0094 IS 'CRM Opportunities';
COMMENT ON COLUMN "Nova".t0094.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0094.lead_id IS 'Reference to Lead';
COMMENT ON COLUMN "Nova".t0094.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0094.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0094_lead_id ON "Nova".t0094(lead_id);
CREATE INDEX IF NOT EXISTS idx_t0094_customer_id ON "Nova".t0094(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0094_active ON "Nova".t0094(is_active);

-- CRM Opportunity Lines
CREATE TABLE IF NOT EXISTS "Nova".t0095 (
    id SERIAL PRIMARY KEY,
    opportunity_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0095.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0095_business_id ON "Nova".t0095(business_id);
CREATE INDEX IF NOT EXISTS idx_t0095_business_id_id ON "Nova".t0095(business_id, id);


COMMENT ON TABLE "Nova".t0095 IS 'CRM Opportunity Lines';
COMMENT ON COLUMN "Nova".t0095.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0095.opportunity_id IS 'Reference to Opportunity';
COMMENT ON COLUMN "Nova".t0095.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0095.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0095_opportunity_id ON "Nova".t0095(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_t0095_product_id ON "Nova".t0095(product_id);
CREATE INDEX IF NOT EXISTS idx_t0095_active ON "Nova".t0095(is_active);

-- ============================================================
-- BUSINESS SIGN-UP & INVITE MIGRATION
-- ============================================================

-- Add business_id column to users table if not exists
DO $$ BEGIN
  ALTER TABLE "Nova".t0021 ADD COLUMN business_id INT REFERENCES "Nova".t0059(id);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Add invite_link column to users table
DO $$ BEGIN
  ALTER TABLE "Nova".t0021 ADD COLUMN invite_token VARCHAR(100);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Extend user_role enum with new roles
DO $$ BEGIN
  ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'Salesman';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'Warehouse';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'Accountant';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Extend user_status enum
DO $$ BEGIN
  ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'Invited';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON COLUMN "Nova".t0021.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0021_business_id ON "Nova".t0021(business_id);
CREATE INDEX IF NOT EXISTS idx_t0021_business_id_id ON "Nova".t0021(business_id, id);


-- ============================================================
-- PICK LISTS (Order Fulfillment)
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0101 (
    id              SERIAL PRIMARY KEY,
    pick_list_number VARCHAR(50) NOT NULL UNIQUE,
    sales_order_id  INT NOT NULL REFERENCES "Nova".t0012(id),
    warehouse_id    INT REFERENCES "Nova".t0008(id),
    status          VARCHAR(30) NOT NULL DEFAULT 'Pending',
    notes           TEXT,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0101.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0101_business_id ON "Nova".t0101(business_id);
CREATE INDEX IF NOT EXISTS idx_t0101_business_id_id ON "Nova".t0101(business_id, id);


COMMENT ON TABLE "Nova".t0101 IS 'Pick Lists â€” generated from confirmed sales orders';
COMMENT ON COLUMN "Nova".t0101.status IS 'Pending | In Progress | Completed | Cancelled';
CREATE INDEX IF NOT EXISTS idx_t0101_sales_order_id ON "Nova".t0101(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0101_status ON "Nova".t0101(status);

CREATE TABLE IF NOT EXISTS "Nova".t0102 (
    id                SERIAL PRIMARY KEY,
    pick_list_id      INT NOT NULL REFERENCES "Nova".t0101(id) ON DELETE CASCADE,
    sales_order_line_id INT REFERENCES "Nova".t0013(id),
    product_id        INT NOT NULL,
    product_name      VARCHAR(200),
    qty_ordered       NUMERIC(12,2) NOT NULL DEFAULT 0,
    qty_picked        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number       INT NOT NULL DEFAULT 1,
    batch_id          INT REFERENCES "Nova".t0088(id),
    batch_number      VARCHAR(255),
    expiry_date       DATE,
    picked_batch_id   INT REFERENCES "Nova".t0088(id),
    picked_batch_number VARCHAR(255),
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0102.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0102_business_id ON "Nova".t0102(business_id);
CREATE INDEX IF NOT EXISTS idx_t0102_business_id_id ON "Nova".t0102(business_id, id);


COMMENT ON TABLE "Nova".t0102 IS 'Pick List Items';
COMMENT ON COLUMN "Nova".t0102.qty_ordered IS 'Quantity ordered (target to pick)';
COMMENT ON COLUMN "Nova".t0102.qty_picked IS 'Quantity actually picked so far';
COMMENT ON COLUMN "Nova".t0102.batch_id IS 'Suggested lot ID allocated by FEFO engine';
COMMENT ON COLUMN "Nova".t0102.batch_number IS 'Suggested lot number';
COMMENT ON COLUMN "Nova".t0102.expiry_date IS 'Expiration date of suggested lot';
COMMENT ON COLUMN "Nova".t0102.picked_batch_id IS 'Actual picked lot ID (if different from suggested)';
COMMENT ON COLUMN "Nova".t0102.picked_batch_number IS 'Actual picked lot number';
CREATE INDEX IF NOT EXISTS idx_t0102_pick_list_id ON "Nova".t0102(pick_list_id);
CREATE INDEX IF NOT EXISTS idx_t0102_product_id ON "Nova".t0102(product_id);
CREATE INDEX IF NOT EXISTS idx_t0102_batch_id ON "Nova".t0102(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0102_picked_batch_id ON "Nova".t0102(picked_batch_id);
CREATE INDEX IF NOT EXISTS idx_t0102_batch_number ON "Nova".t0102(batch_number);

-- ============================================================
-- PRODUCT-SUPPLIER LINKING
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0103 (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    supplier_id     INT NOT NULL REFERENCES "Nova".t0011(id) ON DELETE CASCADE,
    supplier_sku    VARCHAR(100),
    unit_cost       NUMERIC(12,2) DEFAULT 0,
    lead_time_days  INT DEFAULT 0,
    min_order_qty   NUMERIC(12,2) DEFAULT 1,
    is_preferred    BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1,
    UNIQUE(product_id, supplier_id)
);
COMMENT ON COLUMN "Nova".t0103.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0103_business_id ON "Nova".t0103(business_id);
CREATE INDEX IF NOT EXISTS idx_t0103_business_id_id ON "Nova".t0103(business_id, id);


COMMENT ON TABLE "Nova".t0103 IS 'Product-Supplier linking with supplier SKU and cost';
COMMENT ON COLUMN "Nova".t0103.supplier_sku IS 'Supplier''s SKU for this product';
COMMENT ON COLUMN "Nova".t0103.unit_cost IS 'Cost from this supplier';
COMMENT ON COLUMN "Nova".t0103.lead_time_days IS 'Typical lead time in days';
COMMENT ON COLUMN "Nova".t0103.min_order_qty IS 'Minimum order quantity (MOQ) from this supplier';
COMMENT ON COLUMN "Nova".t0103.is_preferred IS 'Marked as preferred supplier';
CREATE INDEX IF NOT EXISTS idx_t0103_product_id ON "Nova".t0103(product_id);
CREATE INDEX IF NOT EXISTS idx_t0103_supplier_id ON "Nova".t0103(supplier_id);

-- ============================================================
-- MIGRATION BATCH TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0104 (
    id              SERIAL PRIMARY KEY,
    batch_key       VARCHAR(64) NOT NULL UNIQUE,
    entity_type     VARCHAR(30) NOT NULL,
    source_type     VARCHAR(50) NOT NULL DEFAULT 'csv_dump',
    total_rows      INT NOT NULL DEFAULT 0,
    inserted_rows   INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'Preview',
    dry_run_completed BOOLEAN NOT NULL DEFAULT false,
    connection_config JSONB,
    reconciliation_summary JSONB,
    execution_log   JSONB,
    error_details   JSONB,
    business_id   INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN "Nova".t0104.source_type IS 'Source connector type: sqlserver | csv_dump | mysql | postgres';
COMMENT ON COLUMN "Nova".t0104.connection_config IS 'Legacy connection parameters and dataset metadata (JSON)';
COMMENT ON COLUMN "Nova".t0104.dry_run_completed IS 'Flag indicating if dry run simulation passed';
COMMENT ON COLUMN "Nova".t0104.reconciliation_summary IS 'Opening balance, inventory, and entity reconciliation metrics (JSON)';
COMMENT ON COLUMN "Nova".t0104.execution_log IS 'Step-by-step execution and timing logs (JSON)';
COMMENT ON COLUMN "Nova".t0104.error_details IS 'Row-level and schema translation error details (JSON)';
COMMENT ON COLUMN "Nova".t0104.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0104_business_id ON "Nova".t0104(business_id);
CREATE INDEX IF NOT EXISTS idx_t0104_business_id_id ON "Nova".t0104(business_id, id);
CREATE INDEX IF NOT EXISTS idx_t0104_source_type ON "Nova".t0104(source_type);

COMMENT ON TABLE "Nova".t0104 IS 'Migration batches for tracking legacy migrations and CSV imports';
COMMENT ON COLUMN "Nova".t0104.status IS 'Preview | Committed | RolledBack';
CREATE INDEX IF NOT EXISTS idx_t0104_batch_key ON "Nova".t0104(batch_key);

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

-- =====================================================-- SALES COMMISSION CONFIGURATION & PAYOUTS
-- ============================================================

CREATE TABLE IF NOT EXISTS "Nova".t0109 (
    id                     SERIAL PRIMARY KEY,
    rule_name              VARCHAR(100) NOT NULL,
    sales_rep_id           INT REFERENCES "Nova".t0021(id),
    base_commission_rate   NUMERIC(5,2) NOT NULL DEFAULT 5.00,
    min_margin_threshold   NUMERIC(5,2) NOT NULL DEFAULT 15.00,
    tier_rules             JSONB DEFAULT '[]',
    discount_penalty_rate  NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    is_active              BOOLEAN NOT NULL DEFAULT true,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             INT,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by             INT,
    update_number          INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0109 IS 'Sales Commission Rules and Rates';
COMMENT ON COLUMN "Nova".t0109.rule_name IS 'Rule or plan identifier';
COMMENT ON COLUMN "Nova".t0109.sales_rep_id IS 'Specific sales rep or NULL for global default';
COMMENT ON COLUMN "Nova".t0109.base_commission_rate IS 'Base commission percentage on realized gross profit';
COMMENT ON COLUMN "Nova".t0109.min_margin_threshold IS 'Minimum gross margin percentage required to qualify for commission';
COMMENT ON COLUMN "Nova".t0109.tier_rules IS 'Tiered commission rate JSON structure';
COMMENT ON COLUMN "Nova".t0109.discount_penalty_rate IS 'Penalty reduction per discount percentage granted';

CREATE INDEX IF NOT EXISTS idx_t0109_sales_rep_id ON "Nova".t0109(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0109_is_active ON "Nova".t0109(is_active);

CREATE TABLE IF NOT EXISTS "Nova".t0110 (
    id                     SERIAL PRIMARY KEY,
    payout_number          VARCHAR(50) NOT NULL UNIQUE,
    sales_rep_id           INT NOT NULL REFERENCES "Nova".t0021(id),
    invoice_id             INT REFERENCES "Nova".t0090(id),
    payment_id             INT REFERENCES "Nova".t0091(id),
    rule_id                INT REFERENCES "Nova".t0109(id),
    period_start           DATE,
    period_end             DATE,
    collected_amount       NUMERIC(12,2) NOT NULL DEFAULT 0,
    realized_gross_margin  NUMERIC(12,2) NOT NULL DEFAULT 0,
    commission_rate        NUMERIC(5,2) NOT NULL DEFAULT 0,
    commission_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_penalty       NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_commission_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    status                 VARCHAR(20) NOT NULL DEFAULT 'Pending',
    is_active              BOOLEAN NOT NULL DEFAULT true,
    payment_date           DATE,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             INT,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by             INT,
    update_number          INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0110 IS 'Sales Commission Payouts and Realized Ledgers';
COMMENT ON COLUMN "Nova".t0110.payout_number IS 'Unique commission payout or statement reference';
COMMENT ON COLUMN "Nova".t0110.sales_rep_id IS 'Sales representative receiving commission';
COMMENT ON COLUMN "Nova".t0110.invoice_id IS 'Associated sales invoice';
COMMENT ON COLUMN "Nova".t0110.payment_id IS 'Payment collection trigger';
COMMENT ON COLUMN "Nova".t0110.collected_amount IS 'Cash collected amount on invoice';
COMMENT ON COLUMN "Nova".t0110.realized_gross_margin IS 'Gross profit realized on collected cash';
COMMENT ON COLUMN "Nova".t0110.commission_rate IS 'Applied commission percentage';
COMMENT ON COLUMN "Nova".t0110.commission_amount IS 'Gross commission calculated';
COMMENT ON COLUMN "Nova".t0110.discount_penalty IS 'Deduction for excessive discounts granted';
COMMENT ON COLUMN "Nova".t0110.net_commission_amount IS 'Net payable commission amount';
COMMENT ON COLUMN "Nova".t0110.status IS 'Pending | Approved | Paid | Cancelled';
COMMENT ON COLUMN "Nova".t0110.is_active IS 'Soft-delete flag; inactive payouts excluded from commission calculations';

CREATE INDEX IF NOT EXISTS idx_t0110_sales_rep_id ON "Nova".t0110(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0110_invoice_id ON "Nova".t0110(invoice_id);
CREATE INDEX IF NOT EXISTS idx_t0110_payment_id ON "Nova".t0110(payment_id);
CREATE INDEX IF NOT EXISTS idx_t0110_status ON "Nova".t0110(status);

-- ============================================================
-- ROLES & PERMISSIONS
-- ============================================================

-- Create nova_readonly role for secure MCP AI agent queries
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        CREATE ROLE nova_readonly NOLOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA "Nova" TO nova_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA "Nova" TO nova_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA "Nova" GRANT SELECT ON TABLES TO nova_readonly;

-- Column-level restrictions on sensitive credential columns
REVOKE SELECT ON "Nova".t0021 FROM nova_readonly;
GRANT SELECT (id, username, full_name, email, role, permissions, business_id, status, last_login, created_at, created_by, updated_at, updated_by, update_number) ON "Nova".t0021 TO nova_readonly;
REVOKE SELECT (password_hash) ON "Nova".t0021 FROM nova_readonly;

REVOKE SELECT ON "Nova".t0056 FROM nova_readonly;
GRANT SELECT (id, key_name, client_id, permissions, expires_at, is_active, created_at, created_by, updated_at, updated_by, update_number) ON "Nova".t0056 TO nova_readonly;
REVOKE SELECT (api_key) ON "Nova".t0056 FROM nova_readonly;

GRANT nova_readonly TO CURRENT_USER;
=======
-- Production Plans
CREATE TABLE IF NOT EXISTS "Nova".t0024 (
    id SERIAL PRIMARY KEY,
    plan_number VARCHAR(30) NOT NULL,
    product_id INT,
    product_name VARCHAR(200) NOT NULL,
    quantity NUMERIC(12,2) NOT NULL DEFAULT 0,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0024 IS 'Production Plans';
COMMENT ON COLUMN "Nova".t0024.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0024.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0024_status ON "Nova".t0024(status);
CREATE INDEX IF NOT EXISTS idx_t0024_plan_number ON "Nova".t0024(plan_number);
CREATE INDEX IF NOT EXISTS idx_t0024_business_id ON "Nova".t0024(business_id);
CREATE INDEX IF NOT EXISTS idx_t0024_business_id_id ON "Nova".t0024(business_id, id);

-- Global Settings
CREATE TABLE IF NOT EXISTS "Nova".t0025 (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    setting_group VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0025 IS 'Global Settings';
COMMENT ON COLUMN "Nova".t0025.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0025.setting_key IS 'Key identifier for the setting';
COMMENT ON COLUMN "Nova".t0025.setting_group IS 'Group name for UI organisation';
COMMENT ON COLUMN "Nova".t0025.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0025_group ON "Nova".t0025(setting_group);
CREATE INDEX IF NOT EXISTS idx_t0025_key ON "Nova".t0025(setting_key);
CREATE INDEX IF NOT EXISTS idx_t0025_business_id ON "Nova".t0025(business_id);
CREATE INDEX IF NOT EXISTS idx_t0025_business_id_id ON "Nova".t0025(business_id, id);

-- Price Lists
CREATE TABLE IF NOT EXISTS "Nova".t0083 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_default BOOLEAN NOT NULL DEFAULT false,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0083 IS 'Price Lists';
COMMENT ON COLUMN "Nova".t0083.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0083.name IS 'Price list name';
COMMENT ON COLUMN "Nova".t0083.code IS 'Unique price list code';
COMMENT ON COLUMN "Nova".t0083.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0083_code ON "Nova".t0083(code);
CREATE INDEX IF NOT EXISTS idx_t0083_active ON "Nova".t0083(is_active);
CREATE INDEX IF NOT EXISTS idx_t0083_business_id ON "Nova".t0083(business_id);
CREATE INDEX IF NOT EXISTS idx_t0083_business_id_id ON "Nova".t0083(business_id, id);

-- Tax Rates
CREATE TABLE IF NOT EXISTS "Nova".t0085 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    rate NUMERIC(5,2) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'Sales',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_default BOOLEAN NOT NULL DEFAULT false,
    description TEXT,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0085 IS 'Tax Rates';
COMMENT ON COLUMN "Nova".t0085.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0085.code IS 'Tax rate code';
COMMENT ON COLUMN "Nova".t0085.type IS 'Tax type';
COMMENT ON COLUMN "Nova".t0085.is_active IS 'Active status flag';
COMMENT ON COLUMN "Nova".t0085.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0085_code ON "Nova".t0085(code);
CREATE INDEX IF NOT EXISTS idx_t0085_type ON "Nova".t0085(type);
CREATE INDEX IF NOT EXISTS idx_t0085_active ON "Nova".t0085(is_active);
CREATE INDEX IF NOT EXISTS idx_t0085_business_id ON "Nova".t0085(business_id);
CREATE INDEX IF NOT EXISTS idx_t0085_business_id_id ON "Nova".t0085(business_id, id);

-- Inventory Counts
CREATE TABLE IF NOT EXISTS "Nova".t0105 (
    id SERIAL PRIMARY KEY,
    count_number VARCHAR(30) NOT NULL,
    warehouse_id INT REFERENCES "Nova".t0008(id) ON DELETE SET NULL,
    count_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0105 IS 'Inventory Counts';
COMMENT ON COLUMN "Nova".t0105.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0105.count_number IS 'Count identifier number';
COMMENT ON COLUMN "Nova".t0105.status IS 'Status';
COMMENT ON COLUMN "Nova".t0105.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0105_status ON "Nova".t0105(status);
CREATE INDEX IF NOT EXISTS idx_t0105_business_id ON "Nova".t0105(business_id);
CREATE INDEX IF NOT EXISTS idx_t0105_business_id_id ON "Nova".t0105(business_id, id);

-- Inventory Count Lines
CREATE TABLE IF NOT EXISTS "Nova".t0106 (
    id SERIAL PRIMARY KEY,
    count_id INT NOT NULL REFERENCES "Nova".t0105(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    expected_qty NUMERIC(12,4) NOT NULL DEFAULT 0,
    counted_qty NUMERIC(12,4),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0106 IS 'Inventory Count Lines';
COMMENT ON COLUMN "Nova".t0106.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0106.count_id IS 'Reference to Inventory Count';
COMMENT ON COLUMN "Nova".t0106.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0106.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0106_count ON "Nova".t0106(count_id);
CREATE INDEX IF NOT EXISTS idx_t0106_product ON "Nova".t0106(product_id);
CREATE INDEX IF NOT EXISTS idx_t0106_business_id ON "Nova".t0106(business_id);
CREATE INDEX IF NOT EXISTS idx_t0106_business_id_id ON "Nova".t0106(business_id, id);

-- Product Types
CREATE TABLE IF NOT EXISTS "Nova".t0107 (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    description TEXT,
    color VARCHAR(7) DEFAULT '#6b7280',
    is_active BOOLEAN NOT NULL DEFAULT true,
    business_id INT REFERENCES "Nova".t0059(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0107 IS 'Product Types';
COMMENT ON COLUMN "Nova".t0107.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0107.name IS 'Product type name';
COMMENT ON COLUMN "Nova".t0107.code IS 'Product type code';
COMMENT ON COLUMN "Nova".t0107.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0107_code ON "Nova".t0107(code);
CREATE INDEX IF NOT EXISTS idx_t0107_business_id ON "Nova".t0107(business_id);
CREATE INDEX IF NOT EXISTS idx_t0107_business_id_id ON "Nova".t0107(business_id, id);

-- Stock Transfers (Header)
CREATE TABLE IF NOT EXISTS "Nova".t0108 (
    id                       SERIAL PRIMARY KEY,
    transfer_number          VARCHAR(50) NOT NULL UNIQUE,
    source_warehouse_id      INT NOT NULL REFERENCES "Nova".t0008(id),
    destination_warehouse_id INT NOT NULL REFERENCES "Nova".t0008(id),
    status                   VARCHAR(30) NOT NULL DEFAULT 'Draft',
    transfer_date            DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery_date   DATE,
    carrier                  VARCHAR(100),
    tracking_number          VARCHAR(100),
    dispatched_at            TIMESTAMPTZ,
    dispatched_by            INT REFERENCES "Nova".t0021(id),
    received_at              TIMESTAMPTZ,
    received_by              INT REFERENCES "Nova".t0021(id),
    notes                    TEXT,
    is_active                BOOLEAN NOT NULL DEFAULT true,
    business_id              INT REFERENCES "Nova".t0059(id),
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by               INT,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by               INT,
    update_number            INT NOT NULL DEFAULT 1,
    CONSTRAINT chk_t0108_warehouses_differ CHECK (source_warehouse_id <> destination_warehouse_id)
);
COMMENT ON TABLE "Nova".t0108 IS 'Stock Transfer Orders — Inter-warehouse transfers and branch replenishment';
COMMENT ON COLUMN "Nova".t0108.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0108.transfer_number IS 'Unique transfer order reference (TRF-XXXXX)';
COMMENT ON COLUMN "Nova".t0108.source_warehouse_id IS 'Originating dispatch warehouse (FK to t0008)';
COMMENT ON COLUMN "Nova".t0108.destination_warehouse_id IS 'Receiving destination warehouse (FK to t0008)';
COMMENT ON COLUMN "Nova".t0108.status IS 'Transfer status: Draft | Pending | In Transit | Received | Partially Received | Cancelled';
COMMENT ON COLUMN "Nova".t0108.transfer_date IS 'Date transfer order was requested';
COMMENT ON COLUMN "Nova".t0108.expected_delivery_date IS 'Estimated arrival date at destination';
COMMENT ON COLUMN "Nova".t0108.carrier IS 'Logistics carrier or transport provider';
COMMENT ON COLUMN "Nova".t0108.tracking_number IS 'Carrier shipment tracking / waybill number';
COMMENT ON COLUMN "Nova".t0108.dispatched_at IS 'Timestamp when transfer was dispatched from source';
COMMENT ON COLUMN "Nova".t0108.dispatched_by IS 'User who dispatched transfer (FK to t0021)';
COMMENT ON COLUMN "Nova".t0108.received_at IS 'Timestamp when transfer was received at destination';
COMMENT ON COLUMN "Nova".t0108.received_by IS 'User who confirmed receipt (FK to t0021)';
COMMENT ON COLUMN "Nova".t0108.notes IS 'Transfer instructions or notes';
COMMENT ON COLUMN "Nova".t0108.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0108_transfer_number ON "Nova".t0108(transfer_number);
CREATE INDEX IF NOT EXISTS idx_t0108_source_warehouse ON "Nova".t0108(source_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0108_dest_warehouse ON "Nova".t0108(destination_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0108_status ON "Nova".t0108(status);
CREATE INDEX IF NOT EXISTS idx_t0108_transfer_date ON "Nova".t0108(transfer_date);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id ON "Nova".t0108(business_id);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id_id ON "Nova".t0108(business_id, id);

-- Stock Transfer Lines
CREATE TABLE IF NOT EXISTS "Nova".t0109 (
    id             SERIAL PRIMARY KEY,
    transfer_id    INT NOT NULL REFERENCES "Nova".t0108(id) ON DELETE CASCADE,
    product_id     INT NOT NULL REFERENCES "Nova".t0003(id),
    qty_requested  NUMERIC(12,2) NOT NULL CHECK (qty_requested > 0),
    qty_dispatched NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (qty_dispatched >= 0),
    qty_received   NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (qty_received >= 0),
    qty_lost       NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (qty_lost >= 0),
    loss_reason    VARCHAR(100),
    loss_notes     TEXT,
    batch_id       INT REFERENCES "Nova".t0087(id),
    batch_number   VARCHAR(100),
    line_number    INT NOT NULL DEFAULT 1,
    notes          TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    business_id    INT REFERENCES "Nova".t0059(id),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by     INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by     INT,
    update_number  INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0109 IS 'Stock Transfer Lines — Itemized product quantities, transit and loss tracking';
COMMENT ON COLUMN "Nova".t0109.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0109.transfer_id IS 'Reference to Stock Transfer header (FK to t0108)';
COMMENT ON COLUMN "Nova".t0109.product_id IS 'Reference to Product (FK to t0003)';
COMMENT ON COLUMN "Nova".t0109.qty_requested IS 'Quantity requested to transfer';
COMMENT ON COLUMN "Nova".t0109.qty_dispatched IS 'Quantity dispatched from source warehouse';
COMMENT ON COLUMN "Nova".t0109.qty_received IS 'Quantity received at destination warehouse';
COMMENT ON COLUMN "Nova".t0109.qty_lost IS 'Quantity lost, damaged, or unaccounted during transit';
COMMENT ON COLUMN "Nova".t0109.loss_reason IS 'Reason code for discrepancy / loss (e.g. Transit Damage, Spillage, Theft, Expired, Other)';
COMMENT ON COLUMN "Nova".t0109.loss_notes IS 'Notes or explanation regarding transit loss / discrepancy';
COMMENT ON COLUMN "Nova".t0109.batch_id IS 'Batch/lot reference if FEFO/batch-tracked (FK to t0087)';
COMMENT ON COLUMN "Nova".t0109.batch_number IS 'Batch number identifier string';
COMMENT ON COLUMN "Nova".t0109.line_number IS 'Sequential line item number in transfer order';
COMMENT ON COLUMN "Nova".t0109.notes IS 'Line notes';
COMMENT ON COLUMN "Nova".t0109.business_id IS 'Tenant / business organization identifier (FK to T0059)';
CREATE INDEX IF NOT EXISTS idx_t0109_transfer_id ON "Nova".t0109(transfer_id);
CREATE INDEX IF NOT EXISTS idx_t0109_product_id ON "Nova".t0109(product_id);
CREATE INDEX IF NOT EXISTS idx_t0109_batch_id ON "Nova".t0109(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0109_business_id ON "Nova".t0109(business_id);
CREATE INDEX IF NOT EXISTS idx_t0109_business_id_id ON "Nova".t0109(business_id, id);

COMMIT;
CREATE INDEX IF NOT EXISTS idx_t0021_customer_id ON "Nova".t0021(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0090_stripe_intent ON "Nova".t0090(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_t0090_stripe_session ON "Nova".t0090(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_t0091_stripe_intent ON "Nova".t0091(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_t0091_stripe_session ON "Nova".t0091(stripe_checkout_session_id);
COMMENT ON COLUMN "Nova".t0010.allow_reorders IS 'Whether customer is permitted 1-click reorders in portal';
COMMENT ON COLUMN "Nova".t0010.min_order_amount IS 'Minimum order amount required for portal orders';
COMMENT ON COLUMN "Nova".t0010.order_cutoff_time IS 'Daily order cutoff time (e.g. 22:00:00) for next-day fulfillment';
COMMENT ON COLUMN "Nova".t0021.customer_id IS 'Linked customer account for B2B customer portal users (FK to t0010)';
COMMENT ON COLUMN "Nova".t0090.payment_link IS 'Direct hosted Stripe payment URL';
COMMENT ON COLUMN "Nova".t0090.stripe_checkout_session_id IS 'Stripe Checkout Session ID for hosted payment';
COMMENT ON COLUMN "Nova".t0090.stripe_payment_intent_id IS 'Stripe PaymentIntent ID for online settlement';
COMMENT ON COLUMN "Nova".t0091.payment_link IS 'Stripe hosted payment receipt or session link';
COMMENT ON COLUMN "Nova".t0091.stripe_checkout_session_id IS 'Stripe Checkout Session ID for online payment';
COMMENT ON COLUMN "Nova".t0091.stripe_payment_intent_id IS 'Stripe PaymentIntent ID for online payment';

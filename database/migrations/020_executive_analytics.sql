-- Nova ERP — Executive Analytics, Margin Optimization, Delivery Fulfillment & Commission Tracking
-- Migration 020: Executive Margin Analytics & Delivery Tracking
BEGIN;

-- 1. Sales Orders: Add freight_amount, discount_amount, sales_rep_id
ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS freight_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sales_rep_id INT REFERENCES "Nova".t0021(id);

COMMENT ON COLUMN "Nova".t0012.freight_amount IS 'Freight / shipping charges applied to sales order';
COMMENT ON COLUMN "Nova".t0012.discount_amount IS 'Header-level discount amount applied to sales order';
COMMENT ON COLUMN "Nova".t0012.sales_rep_id IS 'Assigned sales representative (User ID)';

CREATE INDEX IF NOT EXISTS idx_t0012_sales_rep_id ON "Nova".t0012(sales_rep_id);

-- 2. Sales Order Lines: Add line-level cost_price and discount
ALTER TABLE "Nova".t0013
    ADD COLUMN IF NOT EXISTS cost_price NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN "Nova".t0013.cost_price IS 'Unit cost price / COGS at time of order';
COMMENT ON COLUMN "Nova".t0013.discount IS 'Line-level discount amount';

-- 3. Invoices: Add freight_amount, discount_amount, sales_rep_id
ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS freight_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sales_rep_id INT REFERENCES "Nova".t0021(id);

COMMENT ON COLUMN "Nova".t0090.freight_amount IS 'Freight / shipping charges billed on invoice';
COMMENT ON COLUMN "Nova".t0090.discount_amount IS 'Customer discount deducted on invoice';
COMMENT ON COLUMN "Nova".t0090.sales_rep_id IS 'Assigned sales representative (User ID)';

CREATE INDEX IF NOT EXISTS idx_t0090_sales_rep_id ON "Nova".t0090(sales_rep_id);

-- 4. Deliveries: Add freight_cost, delivery_route, actual_delivery_date
ALTER TABLE "Nova".t0077
    ADD COLUMN IF NOT EXISTS freight_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS delivery_route VARCHAR(100),
    ADD COLUMN IF NOT EXISTS actual_delivery_date DATE;

COMMENT ON COLUMN "Nova".t0077.freight_cost IS 'Actual freight / transport cost incurred for delivery';
COMMENT ON COLUMN "Nova".t0077.delivery_route IS 'Assigned delivery route / zone';
COMMENT ON COLUMN "Nova".t0077.actual_delivery_date IS 'Actual date order delivery completed';

CREATE INDEX IF NOT EXISTS idx_t0077_delivery_route ON "Nova".t0077(delivery_route);
CREATE INDEX IF NOT EXISTS idx_t0077_actual_delivery_date ON "Nova".t0077(actual_delivery_date);

-- 5. Sales Commission Configuration Rules
CREATE TABLE IF NOT EXISTS "Nova".t0107 (
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

COMMENT ON TABLE "Nova".t0107 IS 'Sales Commission Rules and Rates';
COMMENT ON COLUMN "Nova".t0107.rule_name IS 'Rule or plan identifier';
COMMENT ON COLUMN "Nova".t0107.sales_rep_id IS 'Specific sales rep or NULL for global default';
COMMENT ON COLUMN "Nova".t0107.base_commission_rate IS 'Base commission percentage on realized gross profit';
COMMENT ON COLUMN "Nova".t0107.min_margin_threshold IS 'Minimum gross margin percentage required to qualify for commission';
COMMENT ON COLUMN "Nova".t0107.tier_rules IS 'Tiered commission rate JSON structure';
COMMENT ON COLUMN "Nova".t0107.discount_penalty_rate IS 'Penalty reduction per discount percentage granted';

CREATE INDEX IF NOT EXISTS idx_t0107_sales_rep_id ON "Nova".t0107(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0107_is_active ON "Nova".t0107(is_active);

-- 6. Sales Commission Payouts and Realized Ledgers
CREATE TABLE IF NOT EXISTS "Nova".t0108 (
    id                     SERIAL PRIMARY KEY,
    payout_number          VARCHAR(50) NOT NULL UNIQUE,
    sales_rep_id           INT NOT NULL REFERENCES "Nova".t0021(id),
    invoice_id             INT REFERENCES "Nova".t0090(id),
    payment_id             INT REFERENCES "Nova".t0091(id),
    rule_id                INT REFERENCES "Nova".t0107(id),
    period_start           DATE,
    period_end             DATE,
    collected_amount       NUMERIC(12,2) NOT NULL DEFAULT 0,
    realized_gross_margin  NUMERIC(12,2) NOT NULL DEFAULT 0,
    commission_rate        NUMERIC(5,2) NOT NULL DEFAULT 0,
    commission_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_penalty       NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_commission_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    status                 VARCHAR(20) NOT NULL DEFAULT 'Pending',
    payment_date           DATE,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             INT,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by             INT,
    update_number          INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0108 IS 'Sales Commission Payouts and Realized Ledgers';
COMMENT ON COLUMN "Nova".t0108.payout_number IS 'Unique commission payout or statement reference';
COMMENT ON COLUMN "Nova".t0108.sales_rep_id IS 'Sales representative receiving commission';
COMMENT ON COLUMN "Nova".t0108.invoice_id IS 'Associated sales invoice';
COMMENT ON COLUMN "Nova".t0108.payment_id IS 'Payment collection trigger';
COMMENT ON COLUMN "Nova".t0108.collected_amount IS 'Cash collected amount on invoice';
COMMENT ON COLUMN "Nova".t0108.realized_gross_margin IS 'Gross profit realized on collected cash';
COMMENT ON COLUMN "Nova".t0108.commission_rate IS 'Applied commission percentage';
COMMENT ON COLUMN "Nova".t0108.commission_amount IS 'Gross commission calculated';
COMMENT ON COLUMN "Nova".t0108.discount_penalty IS 'Deduction for excessive discounts granted';
COMMENT ON COLUMN "Nova".t0108.net_commission_amount IS 'Net payable commission amount';
COMMENT ON COLUMN "Nova".t0108.status IS 'Pending | Approved | Paid | Cancelled';

CREATE INDEX IF NOT EXISTS idx_t0108_sales_rep_id ON "Nova".t0108(sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_t0108_invoice_id ON "Nova".t0108(invoice_id);
CREATE INDEX IF NOT EXISTS idx_t0108_payment_id ON "Nova".t0108(payment_id);
CREATE INDEX IF NOT EXISTS idx_t0108_status ON "Nova".t0108(status);

-- 7. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0107 TO nova_readonly;
        GRANT SELECT ON "Nova".t0108 TO nova_readonly;
    END IF;
END $$;

COMMIT;

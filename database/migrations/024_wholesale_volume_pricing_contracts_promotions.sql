-- Nova ERP — Wholesale Volume Pricing, Tiered Discounts & Contract Terms
-- Migration 024: Volume Tier Breaks (T0116), Customer Group Price Lists (T0117), Customer Contracts (T0118), Promotional Rules (T0119)
BEGIN;

-- 1. Sequences for Contract Numbers and Promotional Campaign Codes
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_contract_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_contract_number IS 'Atomic sequence for generating unique contract numbers (CTR-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_promo_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_promo_code IS 'Atomic sequence for generating unique promotion codes (PROMO-XXXXX)';


-- 2. Volume Tier Breaks Table (T0116)
CREATE TABLE IF NOT EXISTS "Nova".t0116 (
    id                  SERIAL PRIMARY KEY,
    price_list_id       INT REFERENCES "Nova".t0083(id) ON DELETE CASCADE,
    product_id          INT REFERENCES "Nova".t0001(id) ON DELETE CASCADE,
    min_quantity        NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    max_quantity        NUMERIC(12,2),
    unit_price          NUMERIC(12,4),
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    discount_type       VARCHAR(30) NOT NULL DEFAULT 'FixedPrice',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0116 IS 'Volume Tier Breaks — Quantity threshold breaks and volume pricing for sales price lists';
COMMENT ON COLUMN "Nova".t0116.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0116.price_list_id IS 'Parent price list reference (FK to t0083)';
COMMENT ON COLUMN "Nova".t0116.product_id IS 'Target product reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0116.min_quantity IS 'Minimum order line threshold quantity to trigger tier break';
COMMENT ON COLUMN "Nova".t0116.max_quantity IS 'Maximum quantity for tier break (NULL for open-ended / infinity)';
COMMENT ON COLUMN "Nova".t0116.unit_price IS 'Tier unit price when discount_type is FixedPrice';
COMMENT ON COLUMN "Nova".t0116.discount_percentage IS 'Discount percentage when discount_type is Percentage';
COMMENT ON COLUMN "Nova".t0116.discount_type IS 'Discount application type: FixedPrice | Percentage';
COMMENT ON COLUMN "Nova".t0116.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0116_price_list_id ON "Nova".t0116(price_list_id);
CREATE INDEX IF NOT EXISTS idx_t0116_product_id ON "Nova".t0116(product_id);
CREATE INDEX IF NOT EXISTS idx_t0116_min_quantity ON "Nova".t0116(min_quantity);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id ON "Nova".t0116(business_id);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id_id ON "Nova".t0116(business_id, id);


-- 3. Customer Group Price Lists Matrix Table (T0117)
CREATE TABLE IF NOT EXISTS "Nova".t0117 (
    id                  SERIAL PRIMARY KEY,
    customer_group      VARCHAR(100) NOT NULL,
    price_list_id       INT NOT NULL REFERENCES "Nova".t0083(id) ON DELETE CASCADE,
    priority            INT NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0117 IS 'Customer Group Price Lists — Default price list matrix assignments by customer group category';
COMMENT ON COLUMN "Nova".t0117.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0117.customer_group IS 'Customer group designation (e.g. Wholesale, HoReCa, Supermarket, Retail)';
COMMENT ON COLUMN "Nova".t0117.price_list_id IS 'Assigned default price list (FK to t0083)';
COMMENT ON COLUMN "Nova".t0117.priority IS 'Priority ranking when resolving overlapping rules (higher = priority)';
COMMENT ON COLUMN "Nova".t0117.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0117_customer_group ON "Nova".t0117(customer_group);
CREATE INDEX IF NOT EXISTS idx_t0117_price_list_id ON "Nova".t0117(price_list_id);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id ON "Nova".t0117(business_id);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id_id ON "Nova".t0117(business_id, id);


-- 4. Customer Contracts & Special Price Overrides Table (T0118)
CREATE TABLE IF NOT EXISTS "Nova".t0118 (
    id                  SERIAL PRIMARY KEY,
    contract_number     VARCHAR(50) NOT NULL,
    customer_id         INT NOT NULL REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    product_id          INT NOT NULL REFERENCES "Nova".t0001(id) ON DELETE CASCADE,
    contracted_price    NUMERIC(12,4) NOT NULL,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    min_order_quantity  NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    start_date          DATE NOT NULL,
    end_date            DATE,
    status              VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0118 IS 'Customer Contracts — Special contracted price overrides and commitment terms for key customer accounts';
COMMENT ON COLUMN "Nova".t0118.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0118.contract_number IS 'Contract agreement reference identifier (CTR-XXXXX)';
COMMENT ON COLUMN "Nova".t0118.customer_id IS 'Contracted customer account reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0118.product_id IS 'Target product item reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0118.contracted_price IS 'Contracted fixed unit price override';
COMMENT ON COLUMN "Nova".t0118.discount_percentage IS 'Contracted discount percentage override';
COMMENT ON COLUMN "Nova".t0118.min_order_quantity IS 'Minimum order threshold to qualify for contract pricing';
COMMENT ON COLUMN "Nova".t0118.start_date IS 'Effective start date of contract agreement';
COMMENT ON COLUMN "Nova".t0118.end_date IS 'Expiration date of contract agreement (NULL if open-ended)';
COMMENT ON COLUMN "Nova".t0118.status IS 'Contract lifecycle status: Draft | Active | Expired | Terminated';
COMMENT ON COLUMN "Nova".t0118.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0118_contract_number ON "Nova".t0118(contract_number);
CREATE INDEX IF NOT EXISTS idx_t0118_customer_id ON "Nova".t0118(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0118_product_id ON "Nova".t0118(product_id);
CREATE INDEX IF NOT EXISTS idx_t0118_dates ON "Nova".t0118(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_t0118_status ON "Nova".t0118(status);
CREATE INDEX IF NOT EXISTS idx_t0118_business_id ON "Nova".t0118(business_id);
CREATE INDEX IF NOT EXISTS idx_t0118_business_id_id ON "Nova".t0118(business_id, id);


-- 5. Promotional Rules / Buy-X-Get-Y Campaigns Table (T0119)
CREATE TABLE IF NOT EXISTS "Nova".t0119 (
    id                      SERIAL PRIMARY KEY,
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    promo_type              VARCHAR(50) NOT NULL DEFAULT 'BuyXGetY',
    buy_product_id          INT REFERENCES "Nova".t0001(id) ON DELETE CASCADE,
    buy_quantity            NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    get_product_id          INT REFERENCES "Nova".t0001(id) ON DELETE CASCADE,
    get_quantity            NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    get_discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 100.00,
    customer_group          VARCHAR(100),
    customer_id             INT REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    start_date              TIMESTAMPTZ NOT NULL,
    end_date                TIMESTAMPTZ NOT NULL,
    usage_limit             INT,
    times_used              INT NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0119 IS 'Promotional Rules — Time-bounded Buy-X-Get-Y promotional campaigns and discount rules';
COMMENT ON COLUMN "Nova".t0119.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0119.code IS 'Unique promotion code identifier (PROMO-XXXXX)';
COMMENT ON COLUMN "Nova".t0119.name IS 'Promotional campaign name';
COMMENT ON COLUMN "Nova".t0119.description IS 'Detailed description of campaign terms';
COMMENT ON COLUMN "Nova".t0119.promo_type IS 'Promotion type: BuyXGetY | PercentageDiscount | FixedDiscount';
COMMENT ON COLUMN "Nova".t0119.buy_product_id IS 'Required trigger product reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0119.buy_quantity IS 'Required trigger quantity threshold';
COMMENT ON COLUMN "Nova".t0119.get_product_id IS 'Reward product item reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0119.get_quantity IS 'Reward item quantity awarded per trigger threshold';
COMMENT ON COLUMN "Nova".t0119.get_discount_percentage IS 'Discount percentage applied to reward item (100.00 = Free)';
COMMENT ON COLUMN "Nova".t0119.customer_group IS 'Target customer group filter (NULL applies to all groups)';
COMMENT ON COLUMN "Nova".t0119.customer_id IS 'Target specific customer filter (NULL applies to all customers)';
COMMENT ON COLUMN "Nova".t0119.start_date IS 'Campaign validity window start timestamp';
COMMENT ON COLUMN "Nova".t0119.end_date IS 'Campaign validity window end timestamp';
COMMENT ON COLUMN "Nova".t0119.usage_limit IS 'Maximum allowed total redemptions (NULL for unlimited)';
COMMENT ON COLUMN "Nova".t0119.times_used IS 'Count of completed campaign redemptions';
COMMENT ON COLUMN "Nova".t0119.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0119_code ON "Nova".t0119(code);
CREATE INDEX IF NOT EXISTS idx_t0119_buy_product_id ON "Nova".t0119(buy_product_id);
CREATE INDEX IF NOT EXISTS idx_t0119_get_product_id ON "Nova".t0119(get_product_id);
CREATE INDEX IF NOT EXISTS idx_t0119_dates ON "Nova".t0119(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_t0119_customer_group ON "Nova".t0119(customer_group);
CREATE INDEX IF NOT EXISTS idx_t0119_customer_id ON "Nova".t0119(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0119_business_id ON "Nova".t0119(business_id);
CREATE INDEX IF NOT EXISTS idx_t0119_business_id_id ON "Nova".t0119(business_id, id);


-- 6. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0116 TO nova_readonly;
        GRANT SELECT ON "Nova".t0117 TO nova_readonly;
        GRANT SELECT ON "Nova".t0118 TO nova_readonly;
        GRANT SELECT ON "Nova".t0119 TO nova_readonly;
    END IF;
END $$;

COMMIT;

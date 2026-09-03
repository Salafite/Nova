-- Nova ERP — Wholesale Volume Pricing, Tiered Discounts & Contract Terms
-- Migration 024: Tier Breaks (T0084), Customer Group Price Lists (T0116), Promotional Campaign Rules (T0117)
BEGIN;

-- 1. Sequences for Promotional Campaign Rules
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_promo_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_promo_code IS 'Atomic sequence for generating unique promotional campaign rule codes (PROMO-XXXXX)';

-- 2. Enhance Price List Items / Tier Breaks Table (T0084)
ALTER TABLE "Nova".t0084
    ADD COLUMN IF NOT EXISTS max_qty INT,
    ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS pricing_type VARCHAR(30) NOT NULL DEFAULT 'Fixed Price';

COMMENT ON COLUMN "Nova".t0084.min_qty IS 'Minimum quantity threshold break point for tier discount';
COMMENT ON COLUMN "Nova".t0084.max_qty IS 'Maximum quantity threshold break point (NULL indicates unlimited / upper bound open)';
COMMENT ON COLUMN "Nova".t0084.discount_percent IS 'Percentage discount applied for this volume tier break';
COMMENT ON COLUMN "Nova".t0084.discount_amount IS 'Fixed dollar discount amount applied per unit for this volume tier break';
COMMENT ON COLUMN "Nova".t0084.pricing_type IS 'Pricing rule type: Fixed Price | Percentage Discount | Fixed Discount';

CREATE INDEX IF NOT EXISTS idx_t0084_tier_lookup ON "Nova".t0084(price_list_id, product_id, min_qty);

-- 3. Customer Group Price List Matrix / Mappings Table (T0116)
CREATE TABLE IF NOT EXISTS "Nova".t0116 (
    id              SERIAL PRIMARY KEY,
    customer_group  VARCHAR(100) NOT NULL,
    price_list_id   INT NOT NULL REFERENCES "Nova".t0083(id) ON DELETE CASCADE,
    priority        INT NOT NULL DEFAULT 10,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    business_id     INT REFERENCES "Nova".t0059(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT,
    update_number   INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0116 IS 'Customer Group Price List Mappings — Default price list matrix per customer segment (e.g., HoReCa Tier A, Wholesale, Supermarket)';
COMMENT ON COLUMN "Nova".t0116.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0116.customer_group IS 'Customer group / segment name (e.g. HoReCa Tier A, Wholesale, Supermarket)';
COMMENT ON COLUMN "Nova".t0116.price_list_id IS 'Assigned default price list (FK to t0083)';
COMMENT ON COLUMN "Nova".t0116.priority IS 'Resolution priority when multiple group rules match (lower number = higher priority)';
COMMENT ON COLUMN "Nova".t0116.business_id IS 'Tenant / business organization identifier (FK to T0059)';

CREATE INDEX IF NOT EXISTS idx_t0116_customer_group ON "Nova".t0116(customer_group);
CREATE INDEX IF NOT EXISTS idx_t0116_price_list_id ON "Nova".t0116(price_list_id);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id ON "Nova".t0116(business_id);
CREATE INDEX IF NOT EXISTS idx_t0116_business_id_id ON "Nova".t0116(business_id, id);

-- 4. Promotional Campaign & Buy-X-Get-Y Rules Master Table (T0117)
CREATE TABLE IF NOT EXISTS "Nova".t0117 (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(50) NOT NULL UNIQUE,
    name                VARCHAR(200) NOT NULL,
    description         TEXT,
    promo_type          VARCHAR(50) NOT NULL DEFAULT 'BUY_X_GET_Y',
    buy_product_id      INT REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    buy_min_qty         NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    get_product_id      INT REFERENCES "Nova".t0003(id) ON DELETE CASCADE,
    get_qty             NUMERIC(12,2) NOT NULL DEFAULT 1.00,
    discount_percent    NUMERIC(5,2) NOT NULL DEFAULT 100.00,
    discount_amount     NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    customer_group      VARCHAR(100),
    price_list_id       INT REFERENCES "Nova".t0083(id) ON DELETE CASCADE,
    start_date          TIMESTAMPTZ NOT NULL,
    end_date            TIMESTAMPTZ NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0117 IS 'Promotional Campaign Rules — Time-bounded promotions and Buy-X-Get-Y campaign rules';
COMMENT ON COLUMN "Nova".t0117.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0117.code IS 'Unique promotion campaign code (PROMO-XXXXX)';
COMMENT ON COLUMN "Nova".t0117.name IS 'Promotion rule name / campaign title';
COMMENT ON COLUMN "Nova".t0117.promo_type IS 'Promotion rule mechanism: BUY_X_GET_Y | PERCENTAGE_DISCOUNT | FLAT_DISCOUNT';
COMMENT ON COLUMN "Nova".t0117.buy_product_id IS 'Required trigger product reference (FK to T0003)';
COMMENT ON COLUMN "Nova".t0117.buy_min_qty IS 'Minimum purchase quantity required to trigger promo';
COMMENT ON COLUMN "Nova".t0117.get_product_id IS 'Bonus / reward item product reference (FK to T0003)';
COMMENT ON COLUMN "Nova".t0117.get_qty IS 'Quantity of reward items provided per trigger unit';
COMMENT ON COLUMN "Nova".t0117.discount_percent IS 'Discount percentage applied to get item (100.00 = 100% Free)';
COMMENT ON COLUMN "Nova".t0117.discount_amount IS 'Fixed monetary discount applied if percentage discount not used';
COMMENT ON COLUMN "Nova".t0117.customer_group IS 'Target customer group filter (NULL = applies to all groups)';
COMMENT ON COLUMN "Nova".t0117.price_list_id IS 'Target price list filter (NULL = applies to all price lists)';
COMMENT ON COLUMN "Nova".t0117.start_date IS 'Promotional campaign validity period start date & time';
COMMENT ON COLUMN "Nova".t0117.end_date IS 'Promotional campaign validity period end date & time';
COMMENT ON COLUMN "Nova".t0117.business_id IS 'Tenant / business organization identifier (FK to T0059)';

CREATE INDEX IF NOT EXISTS idx_t0117_code ON "Nova".t0117(code);
CREATE INDEX IF NOT EXISTS idx_t0117_buy_product_id ON "Nova".t0117(buy_product_id);
CREATE INDEX IF NOT EXISTS idx_t0117_get_product_id ON "Nova".t0117(get_product_id);
CREATE INDEX IF NOT EXISTS idx_t0117_validity ON "Nova".t0117(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_t0117_active ON "Nova".t0117(is_active);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id ON "Nova".t0117(business_id);
CREATE INDEX IF NOT EXISTS idx_t0117_business_id_id ON "Nova".t0117(business_id, id);

-- 5. Add tier & promotion tracking columns to Sales Order Items (T0013)
ALTER TABLE "Nova".t0013
    ADD COLUMN IF NOT EXISTS applied_price_tier VARCHAR(100),
    ADD COLUMN IF NOT EXISTS applied_promotion_id INT REFERENCES "Nova".t0117(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS is_promotional_item BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS original_unit_price NUMERIC(12,2);

-- 6. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0116 TO nova_readonly;
        GRANT SELECT ON "Nova".t0117 TO nova_readonly;
    END IF;
END $$;

COMMIT;

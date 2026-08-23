-- Nova ERP — B2B Self-Service Customer Portal & Stripe Online Settlement Migration
BEGIN;

-- 1. Users Table (Nova.t0021): Add customer_id foreign key for B2B portal user linking
ALTER TABLE "Nova".t0021
    ADD COLUMN IF NOT EXISTS customer_id INT REFERENCES "Nova".t0010(id);

CREATE INDEX IF NOT EXISTS idx_t0021_customer_id ON "Nova".t0021(customer_id);
COMMENT ON COLUMN "Nova".t0021.customer_id IS 'Linked customer account for B2B customer portal users (FK to t0010)';

-- 2. Customers Table (Nova.t0010): Add B2B portal replenishment rules
ALTER TABLE "Nova".t0010
    ADD COLUMN IF NOT EXISTS min_order_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (min_order_amount >= 0),
    ADD COLUMN IF NOT EXISTS order_cutoff_time TIME,
    ADD COLUMN IF NOT EXISTS allow_reorders BOOLEAN NOT NULL DEFAULT true;

COMMENT ON COLUMN "Nova".t0010.min_order_amount IS 'Minimum order amount required for portal orders';
COMMENT ON COLUMN "Nova".t0010.order_cutoff_time IS 'Daily order cutoff time (e.g. 22:00:00) for next-day fulfillment';
COMMENT ON COLUMN "Nova".t0010.allow_reorders IS 'Whether customer is permitted 1-click reorders in portal';

-- 3. Invoices Table (Nova.t0090): Add Stripe checkout and payment tracking columns
ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stripe_checkout_session_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS payment_link TEXT;

CREATE INDEX IF NOT EXISTS idx_t0090_stripe_session ON "Nova".t0090(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_t0090_stripe_intent ON "Nova".t0090(stripe_payment_intent_id);
COMMENT ON COLUMN "Nova".t0090.stripe_payment_intent_id IS 'Stripe PaymentIntent ID for online settlement';
COMMENT ON COLUMN "Nova".t0090.stripe_checkout_session_id IS 'Stripe Checkout Session ID for hosted payment';
COMMENT ON COLUMN "Nova".t0090.payment_link IS 'Direct hosted Stripe payment URL';

-- 4. Payments Table (Nova.t0091): Add Stripe payment tracking columns
ALTER TABLE "Nova".t0091
    ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stripe_checkout_session_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS payment_link TEXT;

CREATE INDEX IF NOT EXISTS idx_t0091_stripe_session ON "Nova".t0091(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS idx_t0091_stripe_intent ON "Nova".t0091(stripe_payment_intent_id);
COMMENT ON COLUMN "Nova".t0091.stripe_payment_intent_id IS 'Stripe PaymentIntent ID for online payment';
COMMENT ON COLUMN "Nova".t0091.stripe_checkout_session_id IS 'Stripe Checkout Session ID for online payment';
COMMENT ON COLUMN "Nova".t0091.payment_link IS 'Stripe hosted payment receipt or session link';

-- 5. Grant permissions to nova_readonly role if present
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT (customer_id) ON "Nova".t0021 TO nova_readonly;
    END IF;
END $$;

COMMIT;

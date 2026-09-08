-- Nova ERP — Vendor Returns (RMA) & Supplier Debit Memo Lifecycle
-- Migration 020: RMA Header (T0081), Line Items (T0082), Debit Memo Links (T0090), and RMA Sequence
BEGIN;

-- ============================================================================
-- 1. Purchase Returns / RMA Headers (T0081)
-- ============================================================================

ALTER TABLE "Nova".t0081
    ADD COLUMN IF NOT EXISTS goods_receipt_id INT REFERENCES "Nova".t0075(id),
    ADD COLUMN IF NOT EXISTS debit_memo_id INT REFERENCES "Nova".t0090(id),
    ADD COLUMN IF NOT EXISTS total_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_by INT REFERENCES "Nova".t0021(id),
    ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);

ALTER TABLE "Nova".t0081 ALTER COLUMN status SET DEFAULT 'Draft';

COMMENT ON TABLE "Nova".t0081 IS 'Purchase Returns / RMA Headers';
COMMENT ON COLUMN "Nova".t0081.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0081.return_number IS 'Unique RMA return reference number (RMA-XXXXX)';
COMMENT ON COLUMN "Nova".t0081.purchase_order_id IS 'Reference to Purchase Order (T0015)';
COMMENT ON COLUMN "Nova".t0081.goods_receipt_id IS 'Reference to Goods Receipt (T0075)';
COMMENT ON COLUMN "Nova".t0081.supplier_id IS 'Reference to Supplier (T0014)';
COMMENT ON COLUMN "Nova".t0081.debit_memo_id IS 'Reference to generated Debit Memo (T0090)';
COMMENT ON COLUMN "Nova".t0081.status IS 'RMA status (Draft, Approved, Returned, Cancelled)';
COMMENT ON COLUMN "Nova".t0081.total_amount IS 'Total return credit value';
COMMENT ON COLUMN "Nova".t0081.attachments IS 'Inspection photos and documentation metadata';
COMMENT ON COLUMN "Nova".t0081.approved_at IS 'Timestamp of RMA approval';
COMMENT ON COLUMN "Nova".t0081.approved_by IS 'User who approved the RMA (T0021)';
COMMENT ON COLUMN "Nova".t0081.business_id IS 'Tenant / business organization identifier (FK to T0059)';
COMMENT ON COLUMN "Nova".t0081.is_active IS 'Active status flag';

CREATE INDEX IF NOT EXISTS idx_t0081_purchase_order_id ON "Nova".t0081(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0081_goods_receipt_id ON "Nova".t0081(goods_receipt_id);
CREATE INDEX IF NOT EXISTS idx_t0081_supplier_id ON "Nova".t0081(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0081_debit_memo_id ON "Nova".t0081(debit_memo_id);
CREATE INDEX IF NOT EXISTS idx_t0081_approved_by ON "Nova".t0081(approved_by);
CREATE INDEX IF NOT EXISTS idx_t0081_status ON "Nova".t0081(status);
CREATE INDEX IF NOT EXISTS idx_t0081_active ON "Nova".t0081(is_active);
CREATE INDEX IF NOT EXISTS idx_t0081_business_id ON "Nova".t0081(business_id);
CREATE INDEX IF NOT EXISTS idx_t0081_business_id_id ON "Nova".t0081(business_id, id);


-- ============================================================================
-- 2. Purchase Return Lines / RMA Line Items (T0082)
-- ============================================================================

ALTER TABLE "Nova".t0082
    ADD COLUMN IF NOT EXISTS batch_id INT REFERENCES "Nova".t0088(id),
    ADD COLUMN IF NOT EXISTS batch_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS expiry_date DATE,
    ADD COLUMN IF NOT EXISTS reason_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS photos JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS quarantine_status VARCHAR(30) DEFAULT 'Quarantine',
    ADD COLUMN IF NOT EXISTS disposition VARCHAR(50) DEFAULT 'Return to Vendor',
    ADD COLUMN IF NOT EXISTS business_id INT REFERENCES "Nova".t0059(id);

COMMENT ON TABLE "Nova".t0082 IS 'Purchase Return Lines / RMA Line Items';
COMMENT ON COLUMN "Nova".t0082.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0082.return_id IS 'Reference to Return (T0081)';
COMMENT ON COLUMN "Nova".t0082.product_id IS 'Reference to Product (T0001)';
COMMENT ON COLUMN "Nova".t0082.uom_id IS 'Reference to Uom (T0007)';
COMMENT ON COLUMN "Nova".t0082.batch_id IS 'Reference to Batch Number (T0088)';
COMMENT ON COLUMN "Nova".t0082.batch_number IS 'Batch or lot number identifier';
COMMENT ON COLUMN "Nova".t0082.expiry_date IS 'Batch expiration date';
COMMENT ON COLUMN "Nova".t0082.reason_code IS 'Return reason code (damaged, expired, rejected, wrong_item, qc_failed)';
COMMENT ON COLUMN "Nova".t0082.photos IS 'Line item inspection photos metadata';
COMMENT ON COLUMN "Nova".t0082.quarantine_status IS 'Quarantine tracking status (Quarantine, Released, Scrapped)';
COMMENT ON COLUMN "Nova".t0082.disposition IS 'Disposition action (Return to Vendor, Scrap, Supplier Credit)';
COMMENT ON COLUMN "Nova".t0082.business_id IS 'Tenant / business organization identifier (FK to T0059)';
COMMENT ON COLUMN "Nova".t0082.is_active IS 'Active status flag';

CREATE INDEX IF NOT EXISTS idx_t0082_return_id ON "Nova".t0082(return_id);
CREATE INDEX IF NOT EXISTS idx_t0082_product_id ON "Nova".t0082(product_id);
CREATE INDEX IF NOT EXISTS idx_t0082_uom_id ON "Nova".t0082(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0082_batch_id ON "Nova".t0082(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0082_batch_number ON "Nova".t0082(batch_number);
CREATE INDEX IF NOT EXISTS idx_t0082_reason_code ON "Nova".t0082(reason_code);
CREATE INDEX IF NOT EXISTS idx_t0082_quarantine_status ON "Nova".t0082(quarantine_status);
CREATE INDEX IF NOT EXISTS idx_t0082_active ON "Nova".t0082(is_active);
CREATE INDEX IF NOT EXISTS idx_t0082_business_id ON "Nova".t0082(business_id);
CREATE INDEX IF NOT EXISTS idx_t0082_business_id_id ON "Nova".t0082(business_id, id);


-- ============================================================================
-- 3. Invoices / Debit Memos (T0090) Cross-References
-- ============================================================================

ALTER TABLE "Nova".t0090
    ADD COLUMN IF NOT EXISTS purchase_order_id INT REFERENCES "Nova".t0015(id),
    ADD COLUMN IF NOT EXISTS purchase_return_id INT REFERENCES "Nova".t0081(id);

ALTER TABLE "Nova".t0090 ALTER COLUMN invoice_type TYPE VARCHAR(30);

COMMENT ON COLUMN "Nova".t0090.purchase_order_id IS 'Purchase order reference for purchase invoices (T0015)';
COMMENT ON COLUMN "Nova".t0090.purchase_return_id IS 'Purchase return / RMA reference for supplier debit memos (T0081)';

CREATE INDEX IF NOT EXISTS idx_t0090_purchase_order_id ON "Nova".t0090(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0090_purchase_return_id ON "Nova".t0090(purchase_return_id);
CREATE INDEX IF NOT EXISTS idx_t0090_invoice_type ON "Nova".t0090(invoice_type);


-- ============================================================================
-- 4. Dedicated Sequence for Purchase Return / RMA Numbering (RMA-XXXXX)
-- ============================================================================

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_purchase_return_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_purchase_return_number IS 'Concurrency-safe atomic sequence for generating unique purchase return / RMA numbers (RMA-XXXXX)';

DO $$
DECLARE
    max_rma_num BIGINT := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'Nova' AND table_name = 't0081'
    ) THEN
        SELECT COALESCE(MAX(
            CASE
                WHEN return_number ~ '^.*-(\d+)$' THEN
                    CASE WHEN LENGTH((regexp_match(return_number, '^.*-(\d+)$'))[1]) <= 18
                         THEN (regexp_match(return_number, '^.*-(\d+)$'))[1]::BIGINT
                         ELSE 0 END
                WHEN return_number ~ '^\d+$' THEN
                    CASE WHEN LENGTH(return_number) <= 18
                         THEN return_number::BIGINT
                         ELSE 0 END
                ELSE 0
            END
        ), 0)
        INTO max_rma_num
        FROM "Nova".t0081;
    END IF;

    IF max_rma_num > 0 THEN
        PERFORM setval('"Nova".seq_purchase_return_number', max_rma_num, true);
    ELSE
        PERFORM setval('"Nova".seq_purchase_return_number', 1, false);
    END IF;
END $$;

COMMIT;

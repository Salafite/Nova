-- Nova ERP — B2B EDI Gateway (EDIFACT / ANSI X12) & Supplier Catalog Sync
-- Migration 026: EDI Trading Partners (T0124), EDI SKU Cross-Reference Matrix (T0125),
--                EDI Transaction / Interchange Logs (T0126), EDI SSCC Pallet Logistics (T0127),
--                Supplier Catalog Sync / 832 PRICAT (T0128)
BEGIN;

-- 1. Sequences
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_edi_control_num START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_edi_control_num IS 'Atomic sequence for generating unique EDI interchange control numbers';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_sscc_pallet_id START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_sscc_pallet_id IS 'Atomic sequence for generating GS1 SSCC-18 serial pallet numbers';

-- 2. EDI Trading Partners Table (T0124)
CREATE TABLE IF NOT EXISTS "Nova".t0124 (
    id                      SERIAL PRIMARY KEY,
    partner_name            VARCHAR(255) NOT NULL,
    partner_code            VARCHAR(50) NOT NULL UNIQUE,
    edi_standard            VARCHAR(20) NOT NULL DEFAULT 'ANSI_X12',
    interchange_sender_id   VARCHAR(50) NOT NULL,
    interchange_receiver_id VARCHAR(50) NOT NULL,
    sender_qualifier        VARCHAR(10) NOT NULL DEFAULT 'ZZ',
    receiver_qualifier      VARCHAR(10) NOT NULL DEFAULT 'ZZ',
    communication_method    VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
    endpoint_url            TEXT,
    customer_id             INT REFERENCES "Nova".t0010(id) ON DELETE SET NULL,
    supplier_id             INT REFERENCES "Nova".t0014(id) ON DELETE SET NULL,
    segment_terminator      VARCHAR(5) NOT NULL DEFAULT '~',
    element_separator       VARCHAR(5) NOT NULL DEFAULT '*',
    subelement_separator    VARCHAR(5) NOT NULL DEFAULT '>',
    release_character       VARCHAR(5) DEFAULT '?',
    auto_confirm_orders     BOOLEAN NOT NULL DEFAULT false,
    price_tolerance_percent NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    gs1_company_prefix      VARCHAR(20),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0124 IS 'EDI Trading Partners — Profiles and delimiter/protocol configurations for B2B electronic trading partners';
COMMENT ON COLUMN "Nova".t0124.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0124.partner_name IS 'Trading partner company name (e.g. Carrefour Hypermarkets, Lulu Group)';
COMMENT ON COLUMN "Nova".t0124.partner_code IS 'Unique trading partner code (e.g. CRF-UAE, LULU-HQ)';
COMMENT ON COLUMN "Nova".t0124.edi_standard IS 'EDI standard format: ANSI_X12 | EDIFACT';
COMMENT ON COLUMN "Nova".t0124.interchange_sender_id IS 'Interchange Sender ID (ISA06 / UNB 0004)';
COMMENT ON COLUMN "Nova".t0124.interchange_receiver_id IS 'Interchange Receiver ID (ISA08 / UNB 0010)';
COMMENT ON COLUMN "Nova".t0124.sender_qualifier IS 'Sender Qualifier (ISA05 / UNB 0007, e.g. ZZ, 01, 14)';
COMMENT ON COLUMN "Nova".t0124.receiver_qualifier IS 'Receiver Qualifier (ISA07 / UNB 0007, e.g. ZZ, 01, 14)';
COMMENT ON COLUMN "Nova".t0124.communication_method IS 'Data transfer protocol: MANUAL | API | AS2 | SFTP';
COMMENT ON COLUMN "Nova".t0124.endpoint_url IS 'AS2 / SFTP / Webhook endpoint URL';
COMMENT ON COLUMN "Nova".t0124.customer_id IS 'Linked Customer account for Sales EDI 850/856/810 (FK to t0010)';
COMMENT ON COLUMN "Nova".t0124.supplier_id IS 'Linked Supplier account for Catalog Sync 832 (FK to t0014)';
COMMENT ON COLUMN "Nova".t0124.segment_terminator IS 'Segment delimiter character (e.g. ~ or ' or \n)';
COMMENT ON COLUMN "Nova".t0124.element_separator IS 'Data element delimiter character (e.g. * or +)';
COMMENT ON COLUMN "Nova".t0124.subelement_separator IS 'Subelement/Component separator (e.g. > or :)';
COMMENT ON COLUMN "Nova".t0124.release_character IS 'Release/escape character for EDIFACT (e.g. ?)';
COMMENT ON COLUMN "Nova".t0124.auto_confirm_orders IS 'Whether clean 850 PO orders are automatically confirmed';
COMMENT ON COLUMN "Nova".t0124.price_tolerance_percent IS 'Allowed price discrepancy threshold percentage before placing order on hold';
COMMENT ON COLUMN "Nova".t0124.gs1_company_prefix IS 'GS1 Company Prefix used for SSCC-18 pallet barcode calculation';
COMMENT ON COLUMN "Nova".t0124.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0124_partner_code ON "Nova".t0124(partner_code);
CREATE INDEX IF NOT EXISTS idx_t0124_customer_id ON "Nova".t0124(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0124_supplier_id ON "Nova".t0124(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id ON "Nova".t0124(business_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_id ON "Nova".t0124(business_id, id);

-- 3. EDI SKU Cross-Reference Matrix Table (T0125)
CREATE TABLE IF NOT EXISTS "Nova".t0125 (
    id                      SERIAL PRIMARY KEY,
    partner_id              INT NOT NULL REFERENCES "Nova".t0124(id) ON DELETE CASCADE,
    product_id              INT NOT NULL REFERENCES "Nova".t0001(id) ON DELETE CASCADE,
    partner_sku             VARCHAR(100) NOT NULL,
    partner_sku_type        VARCHAR(30) NOT NULL DEFAULT 'BUYER_PART_NO',
    gtin                    VARCHAR(20),
    partner_uom             VARCHAR(20) NOT NULL DEFAULT 'EA',
    internal_uom            VARCHAR(20) NOT NULL DEFAULT 'EA',
    uom_conversion_factor   NUMERIC(12,4) NOT NULL DEFAULT 1.0000,
    catalog_price           NUMERIC(12,4),
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0125 IS 'EDI SKU Cross-Reference Matrix — Maps trading partner SKUs, GTIN barcodes, and UOMs to internal Nova products';
COMMENT ON COLUMN "Nova".t0125.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0125.partner_id IS 'Trading partner reference (FK to t0124)';
COMMENT ON COLUMN "Nova".t0125.product_id IS 'Internal product item reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0125.partner_sku IS 'Partner SKU / Buyer Part Number / Vendor Item Code';
COMMENT ON COLUMN "Nova".t0125.partner_sku_type IS 'SKU identifier type: BUYER_PART_NO | GTIN | EAN | UPC | VENDOR_PART_NO';
COMMENT ON COLUMN "Nova".t0125.gtin IS 'Global Trade Item Number / EAN / UPC barcode';
COMMENT ON COLUMN "Nova".t0125.partner_uom IS 'Unit of measure used in partner EDI documents (e.g. CA, EA, BX, PL)';
COMMENT ON COLUMN "Nova".t0125.internal_uom IS 'Unit of measure used internally in Nova (e.g. CASE, PCS, KG)';
COMMENT ON COLUMN "Nova".t0125.uom_conversion_factor IS 'Multiplier to convert partner UOM quantity to internal base quantity';
COMMENT ON COLUMN "Nova".t0125.catalog_price IS 'Contractual or agreed catalog reference price for partner';
COMMENT ON COLUMN "Nova".t0125.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0125_partner_id ON "Nova".t0125(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0125_product_id ON "Nova".t0125(product_id);
CREATE INDEX IF NOT EXISTS idx_t0125_partner_sku ON "Nova".t0125(partner_sku);
CREATE INDEX IF NOT EXISTS idx_t0125_gtin ON "Nova".t0125(gtin);
CREATE INDEX IF NOT EXISTS idx_t0125_lookup ON "Nova".t0125(partner_id, partner_sku);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id ON "Nova".t0125(business_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id_id ON "Nova".t0125(business_id, id);

-- 4. EDI Transaction / Interchange Logs Table (T0126)
CREATE TABLE IF NOT EXISTS "Nova".t0126 (
    id                  SERIAL PRIMARY KEY,
    transaction_number  VARCHAR(50) NOT NULL UNIQUE,
    partner_id          INT REFERENCES "Nova".t0124(id) ON DELETE SET NULL,
    standard            VARCHAR(20) NOT NULL,
    document_type       VARCHAR(20) NOT NULL,
    direction           VARCHAR(10) NOT NULL,
    control_number      VARCHAR(50),
    status              VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    sales_order_id      INT REFERENCES "Nova".t0012(id) ON DELETE SET NULL,
    delivery_id         INT REFERENCES "Nova".t0016(id) ON DELETE SET NULL,
    invoice_id          INT REFERENCES "Nova".t0026(id) ON DELETE SET NULL,
    raw_payload         TEXT NOT NULL,
    parsed_data         JSONB,
    ack_status          VARCHAR(30) DEFAULT 'PENDING',
    ack_payload         TEXT,
    error_details       TEXT,
    processed_at        TIMESTAMPTZ,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0126 IS 'EDI Transaction / Interchange Logs — Audit trail and raw interchange content for all inbound/outbound EDI documents';
COMMENT ON COLUMN "Nova".t0126.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0126.transaction_number IS 'Unique EDI transaction reference (e.g. EDI-TXN-2026-00001)';
COMMENT ON COLUMN "Nova".t0126.partner_id IS 'Trading partner reference (FK to t0124)';
COMMENT ON COLUMN "Nova".t0126.standard IS 'EDI standard format: ANSI_X12 | EDIFACT';
COMMENT ON COLUMN "Nova".t0126.document_type IS 'EDI document transaction set: 850 | 856 | 810 | 832 | 997 | ORDERS | DESADV | INVOIC | PRICAT | CONTRL';
COMMENT ON COLUMN "Nova".t0126.direction IS 'Transmission direction: INBOUND | OUTBOUND';
COMMENT ON COLUMN "Nova".t0126.control_number IS 'Interchange control number (ISA13 / UNB 0020)';
COMMENT ON COLUMN "Nova".t0126.status IS 'Processing status: PENDING | PROCESSED | FAILED | PRICE_DISCREPANCY_HOLD | ACKNOWLEDGED';
COMMENT ON COLUMN "Nova".t0126.sales_order_id IS 'Linked Nova sales order reference (FK to t0012)';
COMMENT ON COLUMN "Nova".t0126.delivery_id IS 'Linked Nova delivery dispatch reference (FK to t0016)';
COMMENT ON COLUMN "Nova".t0126.invoice_id IS 'Linked Nova sales invoice reference (FK to t0026)';
COMMENT ON COLUMN "Nova".t0126.raw_payload IS 'Raw unparsed EDI message interchange text';
COMMENT ON COLUMN "Nova".t0126.parsed_data IS 'Structured JSON representation of segments and parsed loops';
COMMENT ON COLUMN "Nova".t0126.ack_status IS 'Functional acknowledgment state: PENDING | ACCEPTED | REJECTED | ACCEPTED_WITH_ERRORS';
COMMENT ON COLUMN "Nova".t0126.ack_payload IS 'Generated or received 997 FA / CONTRL payload text';
COMMENT ON COLUMN "Nova".t0126.error_details IS 'Validation or ingestion error messages';
COMMENT ON COLUMN "Nova".t0126.processed_at IS 'Timestamp when document processing completed';
COMMENT ON COLUMN "Nova".t0126.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0126_transaction_number ON "Nova".t0126(transaction_number);
CREATE INDEX IF NOT EXISTS idx_t0126_partner_id ON "Nova".t0126(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0126_document_type ON "Nova".t0126(document_type);
CREATE INDEX IF NOT EXISTS idx_t0126_direction ON "Nova".t0126(direction);
CREATE INDEX IF NOT EXISTS idx_t0126_status ON "Nova".t0126(status);
CREATE INDEX IF NOT EXISTS idx_t0126_control_number ON "Nova".t0126(control_number);
CREATE INDEX IF NOT EXISTS idx_t0126_sales_order_id ON "Nova".t0126(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0126_delivery_id ON "Nova".t0126(delivery_id);
CREATE INDEX IF NOT EXISTS idx_t0126_invoice_id ON "Nova".t0126(invoice_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id ON "Nova".t0126(business_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id_id ON "Nova".t0126(business_id, id);

-- 5. EDI SSCC Pallet Logistics Table (T0127)
CREATE TABLE IF NOT EXISTS "Nova".t0127 (
    id                  SERIAL PRIMARY KEY,
    sscc_barcode        VARCHAR(20) NOT NULL UNIQUE,
    delivery_id         INT REFERENCES "Nova".t0016(id) ON DELETE CASCADE,
    sales_order_id      INT REFERENCES "Nova".t0012(id) ON DELETE SET NULL,
    pallet_number       VARCHAR(50),
    package_type        VARCHAR(30) NOT NULL DEFAULT 'PALLET',
    parent_sscc_id      INT REFERENCES "Nova".t0127(id) ON DELETE SET NULL,
    gross_weight_kg     NUMERIC(10,3),
    net_weight_kg       NUMERIC(10,3),
    tare_weight_kg      NUMERIC(10,3),
    volume_cbm          NUMERIC(10,4),
    items_count         INT NOT NULL DEFAULT 0,
    contents_summary    JSONB,
    status              VARCHAR(30) NOT NULL DEFAULT 'PACKED',
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0127 IS 'EDI SSCC Pallet Logistics — GS1 SSCC-18 shipping container codes and hierarchical packaging for ASN';
COMMENT ON COLUMN "Nova".t0127.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0127.sscc_barcode IS '18-digit Serial Shipping Container Code (GS1 SSCC-18)';
COMMENT ON COLUMN "Nova".t0127.delivery_id IS 'Delivery shipment reference (FK to t0016)';
COMMENT ON COLUMN "Nova".t0127.sales_order_id IS 'Sales order reference (FK to t0012)';
COMMENT ON COLUMN "Nova".t0127.pallet_number IS 'Human-readable pallet identifier (e.g. PLT-001)';
COMMENT ON COLUMN "Nova".t0127.package_type IS 'Packaging container level: PALLET | BOX | CONTAINER | CASE';
COMMENT ON COLUMN "Nova".t0127.parent_sscc_id IS 'Parent packaging SSCC reference for nested hierarchies (FK to t0127)';
COMMENT ON COLUMN "Nova".t0127.gross_weight_kg IS 'Total gross weight including pallet/packaging in KG';
COMMENT ON COLUMN "Nova".t0127.net_weight_kg IS 'Net weight of goods in KG';
COMMENT ON COLUMN "Nova".t0127.tare_weight_kg IS 'Weight of empty pallet/container in KG';
COMMENT ON COLUMN "Nova".t0127.volume_cbm IS 'Volume in cubic meters';
COMMENT ON COLUMN "Nova".t0127.items_count IS 'Total unit count packed inside this container';
COMMENT ON COLUMN "Nova".t0127.contents_summary IS 'JSON summary of product items, batch numbers, and quantities packed';
COMMENT ON COLUMN "Nova".t0127.status IS 'Pallet lifecycle status: CREATED | PACKED | STAGED | DISPATCHED | DELIVERED';
COMMENT ON COLUMN "Nova".t0127.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0127_sscc_barcode ON "Nova".t0127(sscc_barcode);
CREATE INDEX IF NOT EXISTS idx_t0127_delivery_id ON "Nova".t0127(delivery_id);
CREATE INDEX IF NOT EXISTS idx_t0127_sales_order_id ON "Nova".t0127(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0127_parent_sscc_id ON "Nova".t0127(parent_sscc_id);
CREATE INDEX IF NOT EXISTS idx_t0127_status ON "Nova".t0127(status);
CREATE INDEX IF NOT EXISTS idx_t0127_business_id ON "Nova".t0127(business_id);
CREATE INDEX IF NOT EXISTS idx_t0127_business_id_id ON "Nova".t0127(business_id, id);

-- 6. Supplier Catalog Sync / 832 PRICAT Table (T0128)
CREATE TABLE IF NOT EXISTS "Nova".t0128 (
    id                  SERIAL PRIMARY KEY,
    partner_id          INT NOT NULL REFERENCES "Nova".t0124(id) ON DELETE CASCADE,
    catalog_code        VARCHAR(50) NOT NULL,
    buyer_sku           VARCHAR(100) NOT NULL,
    supplier_sku        VARCHAR(100),
    gtin                VARCHAR(20),
    product_name        VARCHAR(255) NOT NULL,
    product_description TEXT,
    category            VARCHAR(100),
    brand               VARCHAR(100),
    uom                 VARCHAR(20) NOT NULL DEFAULT 'EA',
    pack_size           INT NOT NULL DEFAULT 1,
    list_price          NUMERIC(12,4) NOT NULL DEFAULT 0.00,
    currency            VARCHAR(10) NOT NULL DEFAULT 'USD',
    effective_start_date DATE,
    effective_end_date  DATE,
    matched_product_id  INT REFERENCES "Nova".t0001(id) ON DELETE SET NULL,
    sync_status         VARCHAR(30) NOT NULL DEFAULT 'SYNCED',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0128 IS 'Supplier Catalog Sync / 832 PRICAT — Electronic product catalog and wholesale price list synchronizations';
COMMENT ON COLUMN "Nova".t0128.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0128.partner_id IS 'Trading partner reference (FK to t0124)';
COMMENT ON COLUMN "Nova".t0128.catalog_code IS 'Catalog identifier / revision batch (e.g. CAT-2026-Q1)';
COMMENT ON COLUMN "Nova".t0128.buyer_sku IS 'Supermarket / Buyer item code';
COMMENT ON COLUMN "Nova".t0128.supplier_sku IS 'Supplier / Manufacturer SKU';
COMMENT ON COLUMN "Nova".t0128.gtin IS 'Global Trade Item Number / EAN barcode';
COMMENT ON COLUMN "Nova".t0128.product_name IS 'Item description / product name';
COMMENT ON COLUMN "Nova".t0128.product_description IS 'Detailed product specs / dimensions';
COMMENT ON COLUMN "Nova".t0128.category IS 'Product category taxonomy';
COMMENT ON COLUMN "Nova".t0128.brand IS 'Product brand name';
COMMENT ON COLUMN "Nova".t0128.uom IS 'Unit of measure';
COMMENT ON COLUMN "Nova".t0128.pack_size IS 'Units per retail packaging';
COMMENT ON COLUMN "Nova".t0128.list_price IS 'Catalog wholesale price';
COMMENT ON COLUMN "Nova".t0128.currency IS 'Currency code (e.g. USD, EUR, AED)';
COMMENT ON COLUMN "Nova".t0128.effective_start_date IS 'Price validity start date';
COMMENT ON COLUMN "Nova".t0128.effective_end_date IS 'Price validity expiration date';
COMMENT ON COLUMN "Nova".t0128.matched_product_id IS 'Matched internal Nova product reference (FK to t0001)';
COMMENT ON COLUMN "Nova".t0128.sync_status IS 'Catalog sync status: SYNCED | PENDING | UNMATCHED | PRICE_CHANGED';
COMMENT ON COLUMN "Nova".t0128.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0128_partner_id ON "Nova".t0128(partner_id);
CREATE INDEX IF NOT EXISTS idx_t0128_catalog_code ON "Nova".t0128(catalog_code);
CREATE INDEX IF NOT EXISTS idx_t0128_buyer_sku ON "Nova".t0128(buyer_sku);
CREATE INDEX IF NOT EXISTS idx_t0128_gtin ON "Nova".t0128(gtin);
CREATE INDEX IF NOT EXISTS idx_t0128_matched_product_id ON "Nova".t0128(matched_product_id);
CREATE INDEX IF NOT EXISTS idx_t0128_sync_status ON "Nova".t0128(sync_status);
CREATE INDEX IF NOT EXISTS idx_t0128_business_id ON "Nova".t0128(business_id);
CREATE INDEX IF NOT EXISTS idx_t0128_business_id_id ON "Nova".t0128(business_id, id);

-- 7. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0124 TO nova_readonly;
        GRANT SELECT ON "Nova".t0125 TO nova_readonly;
        GRANT SELECT ON "Nova".t0126 TO nova_readonly;
        GRANT SELECT ON "Nova".t0127 TO nova_readonly;
        GRANT SELECT ON "Nova".t0128 TO nova_readonly;
    END IF;
END $$;

COMMIT;

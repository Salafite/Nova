-- Nova ERP — Multi-Warehouse Stock Transfers & Inter-Branch Replenishment
-- Migration 022: Stock Transfers (T0108), Transfer Lines (T0109), In-Transit Tracking & Sequences
BEGIN;

-- 1. Warehouses (t0008): Add warehouse_type and is_virtual flag
ALTER TABLE "Nova".t0008
    ADD COLUMN IF NOT EXISTS warehouse_type VARCHAR(50) DEFAULT 'Standard',
    ADD COLUMN IF NOT EXISTS is_virtual BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN "Nova".t0008.warehouse_type IS 'Warehouse classification: Central Hub | Regional DC | Retail Branch | In-Transit Virtual | Standard';
COMMENT ON COLUMN "Nova".t0008.is_virtual IS 'Flag indicating if warehouse is a virtual location (e.g. In-Transit virtual warehouse)';

CREATE INDEX IF NOT EXISTS idx_t0008_warehouse_type ON "Nova".t0008(warehouse_type);
CREATE INDEX IF NOT EXISTS idx_t0008_is_virtual ON "Nova".t0008(is_virtual);

-- 2. Stock Levels (t0009): Add in_transit_qty column
ALTER TABLE "Nova".t0009
    ADD COLUMN IF NOT EXISTS in_transit_qty NUMERIC(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN "Nova".t0009.in_transit_qty IS 'Quantity of inventory currently in-transit to/from this warehouse';

CREATE INDEX IF NOT EXISTS idx_t0009_in_transit_qty ON "Nova".t0009(in_transit_qty);

-- 3. Dedicated Sequence for Stock Transfer Numbering (TRF-XXXXX)
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_stock_transfer_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_stock_transfer_number IS 'Concurrency-safe atomic sequence for generating unique stock transfer numbers (TRF-XXXXX)';

-- 4. Stock Transfers Header Table (T0108)
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
COMMENT ON COLUMN "Nova".t0108.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0108_transfer_number ON "Nova".t0108(transfer_number);
CREATE INDEX IF NOT EXISTS idx_t0108_source_warehouse ON "Nova".t0108(source_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0108_dest_warehouse ON "Nova".t0108(destination_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0108_status ON "Nova".t0108(status);
CREATE INDEX IF NOT EXISTS idx_t0108_transfer_date ON "Nova".t0108(transfer_date);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id ON "Nova".t0108(business_id);
CREATE INDEX IF NOT EXISTS idx_t0108_business_id_id ON "Nova".t0108(business_id, id);

-- Synchronize seq_stock_transfer_number with existing maximum transfer number in T0108
DO $$
DECLARE
    max_trf_num BIGINT := 0;
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'Nova' AND table_name = 't0108'
    ) THEN
        SELECT COALESCE(MAX(
            CASE
                WHEN transfer_number ~ '^.*-(\d+)$' THEN
                    CASE WHEN LENGTH((regexp_match(transfer_number, '^.*-(\d+)$'))[1]) <= 18
                         THEN (regexp_match(transfer_number, '^.*-(\d+)$'))[1]::BIGINT
                         ELSE 0 END
                WHEN transfer_number ~ '^\d+$' THEN
                    CASE WHEN LENGTH(transfer_number) <= 18
                         THEN transfer_number::BIGINT
                         ELSE 0 END
                ELSE 0
            END
        ), 0)
        INTO max_trf_num
        FROM "Nova".t0108;
    END IF;

    IF max_trf_num > 0 THEN
        PERFORM setval('"Nova".seq_stock_transfer_number', max_trf_num, true);
    ELSE
        PERFORM setval('"Nova".seq_stock_transfer_number', 1, false);
    END IF;
END $$;

-- 5. Stock Transfer Lines Table (T0109)
CREATE TABLE IF NOT EXISTS "Nova".t0111 (
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

COMMENT ON TABLE "Nova".t0111 IS 'Stock Transfer Lines — Itemized product quantities, transit and loss tracking';
COMMENT ON COLUMN "Nova".t0111.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0111.transfer_id IS 'Reference to Stock Transfer header (FK to t0108)';
COMMENT ON COLUMN "Nova".t0111.product_id IS 'Reference to Product (FK to t0003)';
COMMENT ON COLUMN "Nova".t0111.qty_requested IS 'Quantity requested to transfer';
COMMENT ON COLUMN "Nova".t0111.qty_dispatched IS 'Quantity dispatched from source warehouse';
COMMENT ON COLUMN "Nova".t0111.qty_received IS 'Quantity received at destination warehouse';
COMMENT ON COLUMN "Nova".t0111.qty_lost IS 'Quantity lost, damaged, or unaccounted during transit';
COMMENT ON COLUMN "Nova".t0111.loss_reason IS 'Reason code for discrepancy / loss (e.g. Transit Damage, Spillage, Theft, Expired, Other)';
COMMENT ON COLUMN "Nova".t0111.loss_notes IS 'Notes or explanation regarding transit loss / discrepancy';
COMMENT ON COLUMN "Nova".t0111.batch_id IS 'Batch/lot reference if FEFO/batch-tracked (FK to t0087)';
COMMENT ON COLUMN "Nova".t0111.batch_number IS 'Batch number identifier string';
COMMENT ON COLUMN "Nova".t0111.line_number IS 'Sequential line item number in transfer order';
COMMENT ON COLUMN "Nova".t0111.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0111_transfer_id ON "Nova".t0111(transfer_id);
CREATE INDEX IF NOT EXISTS idx_t0111_product_id ON "Nova".t0111(product_id);
CREATE INDEX IF NOT EXISTS idx_t0111_batch_id ON "Nova".t0111(batch_id);
CREATE INDEX IF NOT EXISTS idx_t0111_business_id ON "Nova".t0111(business_id);
CREATE INDEX IF NOT EXISTS idx_t0111_business_id_id ON "Nova".t0111(business_id, id);

-- 6. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0108 TO nova_readonly;
        GRANT SELECT ON "Nova".t0111 TO nova_readonly;
    END IF;
END $$;

COMMIT;

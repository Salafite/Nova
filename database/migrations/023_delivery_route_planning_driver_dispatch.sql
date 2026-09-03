-- Nova ERP — Delivery Route Planning & Driver Dispatch Management
-- Migration 023: Delivery Vehicles (T0114), Delivery Runs (T0112), Dispatch Manifests / Run Stops (T0113), Customer Zone Mapping (T0115)
BEGIN;

-- 1. Sequences for Delivery Runs and Vehicle Codes
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_delivery_run_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_delivery_run_number IS 'Atomic sequence for generating unique delivery run numbers (RUN-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_delivery_vehicle_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_delivery_vehicle_code IS 'Atomic sequence for generating unique vehicle codes (VEH-XXXXX)';

-- 2. Delivery Vehicles Master Table (T0114)
CREATE TABLE IF NOT EXISTS "Nova".t0114 (
    id                      SERIAL PRIMARY KEY,
    vehicle_code            VARCHAR(50) NOT NULL UNIQUE,
    name                    VARCHAR(100) NOT NULL,
    license_plate           VARCHAR(30) NOT NULL,
    vehicle_type            VARCHAR(50) NOT NULL DEFAULT 'Van',
    max_weight_capacity_kg  NUMERIC(12,2) NOT NULL DEFAULT 1000.00,
    max_volume_capacity_m3  NUMERIC(12,2) NOT NULL DEFAULT 10.00,
    default_driver_id       INT REFERENCES "Nova".t0021(id),
    status                  VARCHAR(30) NOT NULL DEFAULT 'Available',
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0114 IS 'Delivery Vehicles — Fleet trucks, vans, and transport assets for delivery dispatch';
COMMENT ON COLUMN "Nova".t0114.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0114.vehicle_code IS 'Unique vehicle identification code (VEH-XXXXX)';
COMMENT ON COLUMN "Nova".t0114.name IS 'Vehicle descriptive name / label';
COMMENT ON COLUMN "Nova".t0114.license_plate IS 'Vehicle registration plate number';
COMMENT ON COLUMN "Nova".t0114.vehicle_type IS 'Vehicle category: Van | 5-Ton Truck | 10-Ton Truck | Refrigerated | Motorcycle | Flatbed';
COMMENT ON COLUMN "Nova".t0114.max_weight_capacity_kg IS 'Maximum payload weight capacity in kilograms';
COMMENT ON COLUMN "Nova".t0114.max_volume_capacity_m3 IS 'Maximum payload cargo volume capacity in cubic meters';
COMMENT ON COLUMN "Nova".t0114.default_driver_id IS 'Default assigned driver user (FK to t0021)';
COMMENT ON COLUMN "Nova".t0114.status IS 'Vehicle operational status: Available | In Maintenance | In Use | Inactive';
COMMENT ON COLUMN "Nova".t0114.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0114_vehicle_code ON "Nova".t0114(vehicle_code);
CREATE INDEX IF NOT EXISTS idx_t0114_status ON "Nova".t0114(status);
CREATE INDEX IF NOT EXISTS idx_t0114_vehicle_type ON "Nova".t0114(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_t0114_business_id ON "Nova".t0114(business_id);
CREATE INDEX IF NOT EXISTS idx_t0114_business_id_id ON "Nova".t0114(business_id, id);

-- 3. Delivery Runs Header Table (T0112)
CREATE TABLE IF NOT EXISTS "Nova".t0112 (
    id                SERIAL PRIMARY KEY,
    run_number        VARCHAR(50) NOT NULL UNIQUE,
    run_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    driver_id         INT REFERENCES "Nova".t0021(id),
    vehicle_id        INT REFERENCES "Nova".t0114(id) ON DELETE SET NULL,
    status            VARCHAR(30) NOT NULL DEFAULT 'Draft',
    zone              VARCHAR(100),
    total_stops       INT NOT NULL DEFAULT 0,
    total_weight_kg   NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_volume_m3   NUMERIC(12,2) NOT NULL DEFAULT 0,
    dispatched_at     TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    notes             TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    business_id       INT REFERENCES "Nova".t0059(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT,
    update_number     INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0112 IS 'Delivery Runs Header — Daily delivery routes, vehicle assignments, and dispatch runs';
COMMENT ON COLUMN "Nova".t0112.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0112.run_number IS 'Unique delivery run number (RUN-XXXXX)';
COMMENT ON COLUMN "Nova".t0112.run_date IS 'Scheduled delivery dispatch date';
COMMENT ON COLUMN "Nova".t0112.driver_id IS 'Assigned delivery driver (FK to t0021)';
COMMENT ON COLUMN "Nova".t0112.vehicle_id IS 'Assigned transport vehicle asset (FK to t0114)';
COMMENT ON COLUMN "Nova".t0112.status IS 'Delivery run status: Draft | Planned | Dispatched | In Transit | Completed | Cancelled';
COMMENT ON COLUMN "Nova".t0112.zone IS 'Geographic zone / territory name for this route';
COMMENT ON COLUMN "Nova".t0112.total_stops IS 'Total customer delivery drop-off stops in this run';
COMMENT ON COLUMN "Nova".t0112.total_weight_kg IS 'Calculated total payload weight in kg';
COMMENT ON COLUMN "Nova".t0112.total_volume_m3 IS 'Calculated total payload volume in cubic meters';
COMMENT ON COLUMN "Nova".t0112.dispatched_at IS 'Timestamp when delivery vehicle departed staging dock';
COMMENT ON COLUMN "Nova".t0112.completed_at IS 'Timestamp when all deliveries were completed';
COMMENT ON COLUMN "Nova".t0112.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0112_run_number ON "Nova".t0112(run_number);
CREATE INDEX IF NOT EXISTS idx_t0112_run_date ON "Nova".t0112(run_date);
CREATE INDEX IF NOT EXISTS idx_t0112_driver_id ON "Nova".t0112(driver_id);
CREATE INDEX IF NOT EXISTS idx_t0112_vehicle_id ON "Nova".t0112(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_t0112_status ON "Nova".t0112(status);
CREATE INDEX IF NOT EXISTS idx_t0112_zone ON "Nova".t0112(zone);
CREATE INDEX IF NOT EXISTS idx_t0112_business_id ON "Nova".t0112(business_id);
CREATE INDEX IF NOT EXISTS idx_t0112_business_id_id ON "Nova".t0112(business_id, id);

-- 4. Driver Dispatch Manifest Items / Delivery Run Stops Table (T0113)
CREATE TABLE IF NOT EXISTS "Nova".t0113 (
    id                      SERIAL PRIMARY KEY,
    delivery_run_id         INT NOT NULL REFERENCES "Nova".t0112(id) ON DELETE CASCADE,
    sales_order_id          INT REFERENCES "Nova".t0012(id),
    delivery_id             INT REFERENCES "Nova".t0016(id),
    customer_id             INT NOT NULL REFERENCES "Nova".t0010(id),
    stop_sequence           INT NOT NULL DEFAULT 1,
    lifo_staging_sequence  INT NOT NULL DEFAULT 1,
    delivery_address        TEXT NOT NULL,
    contact_name            VARCHAR(150),
    contact_phone           VARCHAR(50),
    zone                    VARCHAR(100),
    status                  VARCHAR(30) NOT NULL DEFAULT 'Pending',
    special_instructions    TEXT,
    notes                   TEXT,
    loaded_at               TIMESTAMPTZ,
    delivered_at            TIMESTAMPTZ,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0113 IS 'Driver Dispatch Manifest Items — Individual customer drop-off stops and LIFO staging sequences';
COMMENT ON COLUMN "Nova".t0113.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0113.delivery_run_id IS 'Parent delivery run reference (FK to t0112)';
COMMENT ON COLUMN "Nova".t0113.sales_order_id IS 'Associated sales order (FK to t0012)';
COMMENT ON COLUMN "Nova".t0113.delivery_id IS 'Associated delivery note (FK to t0016)';
COMMENT ON COLUMN "Nova".t0113.customer_id IS 'Recipient customer reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0113.stop_sequence IS 'Chronological drop-off sequence number (1 = First stop, N = Last stop)';
COMMENT ON COLUMN "Nova".t0113.lifo_staging_sequence IS 'Warehouse vehicle loading sequence (Last-In, First-Out dock staging sequence)';
COMMENT ON COLUMN "Nova".t0113.delivery_address IS 'Complete physical delivery destination address';
COMMENT ON COLUMN "Nova".t0113.contact_name IS 'Customer contact person name at drop-off location';
COMMENT ON COLUMN "Nova".t0113.contact_phone IS 'Customer telephone / mobile number for driver communication';
COMMENT ON COLUMN "Nova".t0113.zone IS 'Geographic zone / territory identifier';
COMMENT ON COLUMN "Nova".t0113.status IS 'Stop status: Pending | Staged | Loaded | In Transit | Delivered | Failed | Skipped';
COMMENT ON COLUMN "Nova".t0113.special_instructions IS 'Gate codes, dock opening hours, or special delivery instructions';
COMMENT ON COLUMN "Nova".t0113.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0113_delivery_run_id ON "Nova".t0113(delivery_run_id);
CREATE INDEX IF NOT EXISTS idx_t0113_sales_order_id ON "Nova".t0113(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0113_delivery_id ON "Nova".t0113(delivery_id);
CREATE INDEX IF NOT EXISTS idx_t0113_customer_id ON "Nova".t0113(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0113_stop_sequence ON "Nova".t0113(stop_sequence);
CREATE INDEX IF NOT EXISTS idx_t0113_lifo_sequence ON "Nova".t0113(lifo_staging_sequence);
CREATE INDEX IF NOT EXISTS idx_t0113_status ON "Nova".t0113(status);
CREATE INDEX IF NOT EXISTS idx_t0113_business_id ON "Nova".t0113(business_id);
CREATE INDEX IF NOT EXISTS idx_t0113_business_id_id ON "Nova".t0113(business_id, id);

-- 5. Customer Zone Mappings Master Table (T0115)
CREATE TABLE IF NOT EXISTS "Nova".t0115 (
    id                  SERIAL PRIMARY KEY,
    customer_id         INT NOT NULL REFERENCES "Nova".t0010(id) ON DELETE CASCADE,
    zone_name           VARCHAR(100) NOT NULL,
    territory_code      VARCHAR(50),
    postal_code_prefix  VARCHAR(20),
    preferred_driver_id INT REFERENCES "Nova".t0021(id),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0115 IS 'Customer Zone Mappings — Geographic zone and territory mapping for sales customers';
COMMENT ON COLUMN "Nova".t0115.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0115.customer_id IS 'Customer reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0115.zone_name IS 'Geographic region / zone designation';
COMMENT ON COLUMN "Nova".t0115.territory_code IS 'Sales territory / district code';
COMMENT ON COLUMN "Nova".t0115.postal_code_prefix IS 'ZIP / postal code prefix matching rule';
COMMENT ON COLUMN "Nova".t0115.preferred_driver_id IS 'Preferred driver assignment for this customer (FK to t0021)';
COMMENT ON COLUMN "Nova".t0115.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0115_customer_id ON "Nova".t0115(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0115_zone_name ON "Nova".t0115(zone_name);
CREATE INDEX IF NOT EXISTS idx_t0115_business_id ON "Nova".t0115(business_id);
CREATE INDEX IF NOT EXISTS idx_t0115_business_id_id ON "Nova".t0115(business_id, id);

-- 6. Add delivery zone & run columns to existing customer, sales order, and delivery note tables
ALTER TABLE "Nova".t0010
    ADD COLUMN IF NOT EXISTS delivery_zone VARCHAR(100);

ALTER TABLE "Nova".t0012
    ADD COLUMN IF NOT EXISTS delivery_zone VARCHAR(100),
    ADD COLUMN IF NOT EXISTS delivery_run_id INT REFERENCES "Nova".t0112(id) ON DELETE SET NULL;

ALTER TABLE "Nova".t0016
    ADD COLUMN IF NOT EXISTS delivery_zone VARCHAR(100),
    ADD COLUMN IF NOT EXISTS delivery_run_id INT REFERENCES "Nova".t0112(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS lifo_staging_sequence INT;

-- 7. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0112 TO nova_readonly;
        GRANT SELECT ON "Nova".t0113 TO nova_readonly;
        GRANT SELECT ON "Nova".t0114 TO nova_readonly;
        GRANT SELECT ON "Nova".t0115 TO nova_readonly;
    END IF;
END $$;

COMMIT;

-- Nova ERP — Cold-Chain Temperature Zone Management & HACCP Quality Auditing
-- Migration 026: Warehouse Temperature Zones (T0124), Warehouse Bins & Staging Areas (T0125),
--                Vehicle Temperature Compartments (T0126), Temperature Excursion Alerts (T0127),
--                and HACCP Checkpoint Logs (T0128)
BEGIN;

-- 1. Sequences for Cold-Chain Identifiers
CREATE SEQUENCE IF NOT EXISTS "Nova".seq_temp_zone_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_temp_zone_code IS 'Atomic sequence for generating unique warehouse temperature zone codes (ZONE-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_warehouse_bin_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_warehouse_bin_code IS 'Atomic sequence for generating unique warehouse bin codes (BIN-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_vehicle_compartment_code START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_vehicle_compartment_code IS 'Atomic sequence for generating unique vehicle compartment codes (COMP-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_excursion_alert_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_excursion_alert_number IS 'Atomic sequence for generating unique excursion alert numbers (EXC-XXXXX)';

CREATE SEQUENCE IF NOT EXISTS "Nova".seq_haccp_log_number START WITH 1 INCREMENT BY 1;
COMMENT ON SEQUENCE "Nova".seq_haccp_log_number IS 'Atomic sequence for generating unique HACCP checkpoint log numbers (CCP-XXXXX)';

-- 2. Warehouse Temperature Zones Master Table (T0124)
CREATE TABLE IF NOT EXISTS "Nova".t0124 (
    id                  SERIAL PRIMARY KEY,
    zone_code           VARCHAR(50) NOT NULL,
    name                VARCHAR(100) NOT NULL,
    warehouse_id        INT NOT NULL REFERENCES "Nova".t0008(id) ON DELETE CASCADE,
    zone_type           VARCHAR(50) NOT NULL DEFAULT 'Ambient',
    min_temperature     NUMERIC(6,2) NOT NULL DEFAULT 15.00,
    max_temperature     NUMERIC(6,2) NOT NULL DEFAULT 25.00,
    target_temperature  NUMERIC(6,2) NOT NULL DEFAULT 20.00,
    humidity_min        NUMERIC(5,2),
    humidity_max        NUMERIC(5,2),
    current_temperature NUMERIC(6,2),
    current_humidity    NUMERIC(5,2),
    last_monitored_at   TIMESTAMPTZ,
    status              VARCHAR(30) NOT NULL DEFAULT 'Normal',
    sensor_id           VARCHAR(100),
    capacity_m3         NUMERIC(12,2) DEFAULT 0.00,
    notes               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0124 IS 'Warehouse Temperature Zones — Designated thermal control areas (Ambient, Chilled, Frozen, Deep Freeze)';
COMMENT ON COLUMN "Nova".t0124.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0124.zone_code IS 'Unique temperature zone code (ZONE-XXXXX)';
COMMENT ON COLUMN "Nova".t0124.name IS 'Descriptive name of the temperature zone';
COMMENT ON COLUMN "Nova".t0124.warehouse_id IS 'Parent warehouse reference (FK to t0008)';
COMMENT ON COLUMN "Nova".t0124.zone_type IS 'Thermal zone classification: Ambient | Chilled | Frozen | Deep Freeze';
COMMENT ON COLUMN "Nova".t0124.min_temperature IS 'Lower boundary temperature limit in Celsius';
COMMENT ON COLUMN "Nova".t0124.max_temperature IS 'Upper boundary temperature limit in Celsius';
COMMENT ON COLUMN "Nova".t0124.target_temperature IS 'Set-point target operational temperature in Celsius';
COMMENT ON COLUMN "Nova".t0124.status IS 'Zone operational status: Normal | Warning | Excursion | Maintenance | Inactive';
COMMENT ON COLUMN "Nova".t0124.sensor_id IS 'IoT / Telemetry temperature sensor identifier';
COMMENT ON COLUMN "Nova".t0124.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0124_zone_code ON "Nova".t0124(zone_code);
CREATE INDEX IF NOT EXISTS idx_t0124_warehouse_id ON "Nova".t0124(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0124_zone_type ON "Nova".t0124(zone_type);
CREATE INDEX IF NOT EXISTS idx_t0124_status ON "Nova".t0124(status);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id ON "Nova".t0124(business_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_id ON "Nova".t0124(business_id, id);

-- 3. Warehouse Bins & Staging Areas Table (T0125)
CREATE TABLE IF NOT EXISTS "Nova".t0125 (
    id                      SERIAL PRIMARY KEY,
    bin_code                VARCHAR(50) NOT NULL,
    warehouse_id            INT NOT NULL REFERENCES "Nova".t0008(id) ON DELETE CASCADE,
    zone_id                 INT REFERENCES "Nova".t0124(id) ON DELETE SET NULL,
    bin_type                VARCHAR(50) NOT NULL DEFAULT 'Storage',
    temperature_profile     VARCHAR(50) NOT NULL DEFAULT 'Ambient',
    min_temperature         NUMERIC(6,2),
    max_temperature         NUMERIC(6,2),
    aisle                   VARCHAR(20),
    rack                    VARCHAR(20),
    shelf                   VARCHAR(20),
    position                VARCHAR(20),
    max_weight_capacity_kg  NUMERIC(12,2) DEFAULT 1000.00,
    max_volume_capacity_m3  NUMERIC(12,2) DEFAULT 10.00,
    current_weight_kg       NUMERIC(12,2) DEFAULT 0.00,
    current_volume_m3       NUMERIC(12,2) DEFAULT 0.00,
    status                  VARCHAR(30) NOT NULL DEFAULT 'Available',
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0125 IS 'Warehouse Bins & Staging Areas — Storage bins and loading staging docks with thermal profile constraints';
COMMENT ON COLUMN "Nova".t0125.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0125.bin_code IS 'Unique bin / location identifier (BIN-XXXXX)';
COMMENT ON COLUMN "Nova".t0125.warehouse_id IS 'Parent warehouse reference (FK to t0008)';
COMMENT ON COLUMN "Nova".t0125.zone_id IS 'Assigned temperature zone reference (FK to t0124)';
COMMENT ON COLUMN "Nova".t0125.bin_type IS 'Bin category: Storage | Staging Dock | Quarantine | Inspection | Inbound Dock | Outbound Dock';
COMMENT ON COLUMN "Nova".t0125.temperature_profile IS 'Thermal constraint profile: Ambient | Chilled | Frozen | Deep Freeze';
COMMENT ON COLUMN "Nova".t0125.status IS 'Bin status: Available | Occupied | Reserved | Maintenance | Quarantined | Blocked';
COMMENT ON COLUMN "Nova".t0125.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0125_bin_code ON "Nova".t0125(bin_code);
CREATE INDEX IF NOT EXISTS idx_t0125_warehouse_id ON "Nova".t0125(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0125_zone_id ON "Nova".t0125(zone_id);
CREATE INDEX IF NOT EXISTS idx_t0125_bin_type ON "Nova".t0125(bin_type);
CREATE INDEX IF NOT EXISTS idx_t0125_temp_profile ON "Nova".t0125(temperature_profile);
CREATE INDEX IF NOT EXISTS idx_t0125_status ON "Nova".t0125(status);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id ON "Nova".t0125(business_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id_id ON "Nova".t0125(business_id, id);

-- 4. Vehicle Temperature Compartments Table (T0126)
CREATE TABLE IF NOT EXISTS "Nova".t0126 (
    id                      SERIAL PRIMARY KEY,
    vehicle_id              INT NOT NULL REFERENCES "Nova".t0114(id) ON DELETE CASCADE,
    compartment_code        VARCHAR(50) NOT NULL,
    name                    VARCHAR(100) NOT NULL,
    temperature_zone_type   VARCHAR(50) NOT NULL DEFAULT 'Chilled',
    min_temperature         NUMERIC(6,2) NOT NULL DEFAULT 2.00,
    max_temperature         NUMERIC(6,2) NOT NULL DEFAULT 4.00,
    target_temperature      NUMERIC(6,2) NOT NULL DEFAULT 3.00,
    max_weight_capacity_kg  NUMERIC(12,2) NOT NULL DEFAULT 500.00,
    max_volume_capacity_m3  NUMERIC(12,2) NOT NULL DEFAULT 5.00,
    current_temperature     NUMERIC(6,2),
    sensor_id               VARCHAR(100),
    status                  VARCHAR(30) NOT NULL DEFAULT 'Available',
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0126 IS 'Vehicle Temperature Compartments — Multi-temperature partitioned zones on delivery fleet vehicles';
COMMENT ON COLUMN "Nova".t0126.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0126.vehicle_id IS 'Parent transport vehicle reference (FK to t0114)';
COMMENT ON COLUMN "Nova".t0126.compartment_code IS 'Unique compartment code (COMP-XXXXX)';
COMMENT ON COLUMN "Nova".t0126.name IS 'Compartment descriptive label (e.g. Frozen Chamber, Chilled Section)';
COMMENT ON COLUMN "Nova".t0126.temperature_zone_type IS 'Thermal zone classification: Ambient | Chilled | Frozen | Deep Freeze';
COMMENT ON COLUMN "Nova".t0126.status IS 'Compartment status: Available | Loaded | Maintenance | Fault | Inactive';
COMMENT ON COLUMN "Nova".t0126.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0126_vehicle_id ON "Nova".t0126(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_t0126_compartment_code ON "Nova".t0126(compartment_code);
CREATE INDEX IF NOT EXISTS idx_t0126_zone_type ON "Nova".t0126(temperature_zone_type);
CREATE INDEX IF NOT EXISTS idx_t0126_status ON "Nova".t0126(status);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id ON "Nova".t0126(business_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id_id ON "Nova".t0126(business_id, id);

-- 5. Temperature Excursion Alerts Table (T0127)
CREATE TABLE IF NOT EXISTS "Nova".t0127 (
    id                      SERIAL PRIMARY KEY,
    alert_number            VARCHAR(50) NOT NULL UNIQUE,
    alert_type              VARCHAR(50) NOT NULL DEFAULT 'TemperatureExcursion',
    severity                VARCHAR(30) NOT NULL DEFAULT 'Warning',
    status                  VARCHAR(30) NOT NULL DEFAULT 'Open',
    warehouse_id            INT REFERENCES "Nova".t0008(id) ON DELETE SET NULL,
    zone_id                 INT REFERENCES "Nova".t0124(id) ON DELETE SET NULL,
    bin_id                  INT REFERENCES "Nova".t0125(id) ON DELETE SET NULL,
    vehicle_id              INT REFERENCES "Nova".t0114(id) ON DELETE SET NULL,
    compartment_id          INT REFERENCES "Nova".t0126(id) ON DELETE SET NULL,
    delivery_run_id         INT REFERENCES "Nova".t0112(id) ON DELETE SET NULL,
    product_id              INT REFERENCES "Nova".t0003(id) ON DELETE SET NULL,
    batch_number            VARCHAR(100),
    recorded_temperature    NUMERIC(6,2) NOT NULL,
    min_threshold           NUMERIC(6,2),
    max_threshold           NUMERIC(6,2),
    deviation_degrees       NUMERIC(6,2),
    duration_minutes        INT DEFAULT 0,
    haccp_critical_limit    NUMERIC(6,2),
    haccp_violation         BOOLEAN NOT NULL DEFAULT false,
    quarantine_recommended  BOOLEAN NOT NULL DEFAULT false,
    is_quarantined          BOOLEAN NOT NULL DEFAULT false,
    quarantine_notes        TEXT,
    acknowledged_at         TIMESTAMPTZ,
    acknowledged_by         INT REFERENCES "Nova".t0021(id),
    resolved_at             TIMESTAMPTZ,
    resolved_by             INT REFERENCES "Nova".t0021(id),
    resolution_action       TEXT,
    notes                   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0127 IS 'Temperature Excursion Alerts — Real-time cold-chain temperature boundary breach and HACCP violation incidents';
COMMENT ON COLUMN "Nova".t0127.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0127.alert_number IS 'Unique incident alert number (EXC-XXXXX)';
COMMENT ON COLUMN "Nova".t0127.alert_type IS 'Alert type: TemperatureExcursion | IncompatibleZonePutaway | TransitExcursion | SensorFailure | CriticalLimitExceeded';
COMMENT ON COLUMN "Nova".t0127.severity IS 'Alert severity: Warning | Critical | Emergency';
COMMENT ON COLUMN "Nova".t0127.status IS 'Alert status: Open | Acknowledged | Investigating | Resolved | Quarantined | Dismissed';
COMMENT ON COLUMN "Nova".t0127.haccp_violation IS 'Flag indicating whether critical HACCP threshold limit was breached';
COMMENT ON COLUMN "Nova".t0127.quarantine_recommended IS 'Flag indicating automatic recommendation to quarantine batch inventory';
COMMENT ON COLUMN "Nova".t0127.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0127_alert_number ON "Nova".t0127(alert_number);
CREATE INDEX IF NOT EXISTS idx_t0127_alert_type ON "Nova".t0127(alert_type);
CREATE INDEX IF NOT EXISTS idx_t0127_severity ON "Nova".t0127(severity);
CREATE INDEX IF NOT EXISTS idx_t0127_status ON "Nova".t0127(status);
CREATE INDEX IF NOT EXISTS idx_t0127_warehouse_id ON "Nova".t0127(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0127_zone_id ON "Nova".t0127(zone_id);
CREATE INDEX IF NOT EXISTS idx_t0127_product_id ON "Nova".t0127(product_id);
CREATE INDEX IF NOT EXISTS idx_t0127_batch_number ON "Nova".t0127(batch_number);
CREATE INDEX IF NOT EXISTS idx_t0127_delivery_run_id ON "Nova".t0127(delivery_run_id);
CREATE INDEX IF NOT EXISTS idx_t0127_business_id ON "Nova".t0127(business_id);
CREATE INDEX IF NOT EXISTS idx_t0127_business_id_id ON "Nova".t0127(business_id, id);

-- 6. HACCP Checkpoint Logs Master Table (T0128)
CREATE TABLE IF NOT EXISTS "Nova".t0128 (
    id                      SERIAL PRIMARY KEY,
    log_number              VARCHAR(50) NOT NULL UNIQUE,
    checkpoint_stage        VARCHAR(50) NOT NULL,
    checkpoint_name         VARCHAR(150) NOT NULL,
    stage_reference_type    VARCHAR(50),
    stage_reference_id      INT,
    warehouse_id            INT REFERENCES "Nova".t0008(id) ON DELETE SET NULL,
    zone_id                 INT REFERENCES "Nova".t0124(id) ON DELETE SET NULL,
    bin_id                  INT REFERENCES "Nova".t0125(id) ON DELETE SET NULL,
    vehicle_id              INT REFERENCES "Nova".t0114(id) ON DELETE SET NULL,
    compartment_id          INT REFERENCES "Nova".t0126(id) ON DELETE SET NULL,
    delivery_run_id         INT REFERENCES "Nova".t0112(id) ON DELETE SET NULL,
    delivery_stop_id        INT REFERENCES "Nova".t0113(id) ON DELETE SET NULL,
    product_id              INT REFERENCES "Nova".t0003(id) ON DELETE SET NULL,
    batch_number            VARCHAR(100),
    recorded_temperature    NUMERIC(6,2) NOT NULL,
    critical_limit_min      NUMERIC(6,2),
    critical_limit_max      NUMERIC(6,2),
    is_compliant            BOOLEAN NOT NULL DEFAULT true,
    ambient_temperature     NUMERIC(6,2),
    humidity_pct            NUMERIC(5,2),
    logged_by_id            INT REFERENCES "Nova".t0021(id),
    logged_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_by_id          INT REFERENCES "Nova".t0021(id),
    verified_at             TIMESTAMPTZ,
    location_gps            VARCHAR(100),
    sensor_device_id        VARCHAR(100),
    corrective_action       TEXT,
    notes                   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0128 IS 'HACCP Checkpoint Logs — Complete audit trail of temperature readings across supply chain checkpoints';
COMMENT ON COLUMN "Nova".t0128.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0128.log_number IS 'Unique HACCP checkpoint log number (CCP-XXXXX)';
COMMENT ON COLUMN "Nova".t0128.checkpoint_stage IS 'Supply chain stage: GoodsReceipt | WarehouseStorage | StagingDock | VehicleDeparture | TransitCheckpoint | DestinationDelivery | QualityInspection';
COMMENT ON COLUMN "Nova".t0128.recorded_temperature IS 'Measured physical temperature reading in Celsius';
COMMENT ON COLUMN "Nova".t0128.is_compliant IS 'Flag indicating temperature satisfies HACCP critical threshold boundaries';
COMMENT ON COLUMN "Nova".t0128.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0128_log_number ON "Nova".t0128(log_number);
CREATE INDEX IF NOT EXISTS idx_t0128_checkpoint_stage ON "Nova".t0128(checkpoint_stage);
CREATE INDEX IF NOT EXISTS idx_t0128_product_id ON "Nova".t0128(product_id);
CREATE INDEX IF NOT EXISTS idx_t0128_batch_number ON "Nova".t0128(batch_number);
CREATE INDEX IF NOT EXISTS idx_t0128_warehouse_id ON "Nova".t0128(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0128_delivery_run_id ON "Nova".t0128(delivery_run_id);
CREATE INDEX IF NOT EXISTS idx_t0128_delivery_stop_id ON "Nova".t0128(delivery_stop_id);
CREATE INDEX IF NOT EXISTS idx_t0128_logged_at ON "Nova".t0128(logged_at);
CREATE INDEX IF NOT EXISTS idx_t0128_is_compliant ON "Nova".t0128(is_compliant);
CREATE INDEX IF NOT EXISTS idx_t0128_business_id ON "Nova".t0128(business_id);
CREATE INDEX IF NOT EXISTS idx_t0128_business_id_id ON "Nova".t0128(business_id, id);

-- 7. Add Cold-Chain Attributes to Products (T0003) and Vehicles (T0114)
ALTER TABLE "Nova".t0003
    ADD COLUMN IF NOT EXISTS is_cold_chain BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS temp_zone_type VARCHAR(50) DEFAULT 'Ambient',
    ADD COLUMN IF NOT EXISTS min_temperature NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS max_temperature NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS critical_temp_limit NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS thermal_priority_rank INT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS shelf_life_days INT;

COMMENT ON COLUMN "Nova".t0003.is_cold_chain IS 'Flag indicating item requires temperature-controlled handling and storage';
COMMENT ON COLUMN "Nova".t0003.temp_zone_type IS 'Required storage zone type: Ambient | Chilled | Frozen | Deep Freeze';
COMMENT ON COLUMN "Nova".t0003.min_temperature IS 'Minimum safe storage temperature in Celsius';
COMMENT ON COLUMN "Nova".t0003.max_temperature IS 'Maximum safe storage temperature in Celsius';
COMMENT ON COLUMN "Nova".t0003.critical_temp_limit IS 'HACCP critical limit threshold (e.g. -18C for frozen meat)';
COMMENT ON COLUMN "Nova".t0003.thermal_priority_rank IS 'Thermal picking priority (1=Ambient first, 2=Chilled, 3=Frozen, 4=Deep Freeze last)';

CREATE INDEX IF NOT EXISTS idx_t0003_is_cold_chain ON "Nova".t0003(is_cold_chain);
CREATE INDEX IF NOT EXISTS idx_t0003_temp_zone_type ON "Nova".t0003(temp_zone_type);

ALTER TABLE "Nova".t0114
    ADD COLUMN IF NOT EXISTS is_refrigerated BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS has_multi_temperature BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS temperature_monitoring_enabled BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS min_temperature NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS max_temperature NUMERIC(6,2);

COMMENT ON COLUMN "Nova".t0114.is_refrigerated IS 'Flag indicating vehicle possesses active refrigeration / cooling unit';
COMMENT ON COLUMN "Nova".t0114.has_multi_temperature IS 'Flag indicating vehicle contains multiple partitioned temperature compartments';
COMMENT ON COLUMN "Nova".t0114.temperature_monitoring_enabled IS 'Flag indicating real-time IoT temperature logging telemetry is active';

-- 8. Grant Readonly Permissions to AI / MCP Role
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

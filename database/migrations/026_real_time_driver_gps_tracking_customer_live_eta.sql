-- Nova ERP — Real-Time Driver GPS Tracking & Customer Live ETA Notification
-- Migration 026: Driver GPS Telemetry (T0124), Customer Live Tracking Sessions & Tokens (T0125), Geofence Detection Events (T0126)
BEGIN;

-- 1. Driver GPS Telemetry Table (T0124)
CREATE TABLE IF NOT EXISTS "Nova".t0124 (
    id                  SERIAL PRIMARY KEY,
    run_id              INT REFERENCES "Nova".t0112(id) ON DELETE CASCADE,
    driver_id           INT REFERENCES "Nova".t0021(id),
    vehicle_id          INT REFERENCES "Nova".t0114(id) ON DELETE SET NULL,
    latitude            NUMERIC(10,7) NOT NULL,
    longitude           NUMERIC(10,7) NOT NULL,
    speed_kmh           NUMERIC(6,2) NOT NULL DEFAULT 0.0,
    heading             NUMERIC(6,2) NOT NULL DEFAULT 0.0,
    accuracy_meters     NUMERIC(8,2) NOT NULL DEFAULT 5.0,
    battery_level       NUMERIC(5,2),
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0124 IS 'Driver GPS Telemetry — Periodic high-frequency GPS coordinate pings and telemetry streams from driver mobile devices';
COMMENT ON COLUMN "Nova".t0124.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0124.run_id IS 'Active delivery run reference (FK to t0112)';
COMMENT ON COLUMN "Nova".t0124.driver_id IS 'Broadcasting driver user reference (FK to t0021)';
COMMENT ON COLUMN "Nova".t0124.vehicle_id IS 'Assigned delivery vehicle asset (FK to t0114)';
COMMENT ON COLUMN "Nova".t0124.latitude IS 'Current GPS latitude coordinate (-90 to +90 degrees)';
COMMENT ON COLUMN "Nova".t0124.longitude IS 'Current GPS longitude coordinate (-180 to +180 degrees)';
COMMENT ON COLUMN "Nova".t0124.speed_kmh IS 'Instantaneous ground speed in kilometers per hour';
COMMENT ON COLUMN "Nova".t0124.heading IS 'Vehicle compass heading / bearing in degrees (0 = North, 90 = East, 180 = South, 270 = West)';
COMMENT ON COLUMN "Nova".t0124.accuracy_meters IS 'GPS signal horizontal accuracy radius in meters';
COMMENT ON COLUMN "Nova".t0124.battery_level IS 'Driver mobile device battery percentage (0.0 to 100.0)';
COMMENT ON COLUMN "Nova".t0124.recorded_at IS 'Client-side hardware GPS timestamp of the coordinate fix';
COMMENT ON COLUMN "Nova".t0124.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0124_run_id ON "Nova".t0124(run_id);
CREATE INDEX IF NOT EXISTS idx_t0124_driver_id ON "Nova".t0124(driver_id);
CREATE INDEX IF NOT EXISTS idx_t0124_vehicle_id ON "Nova".t0124(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_t0124_recorded_at ON "Nova".t0124(recorded_at);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id ON "Nova".t0124(business_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_run_id ON "Nova".t0124(business_id, run_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_driver_id ON "Nova".t0124(business_id, driver_id);
CREATE INDEX IF NOT EXISTS idx_t0124_business_id_id ON "Nova".t0124(business_id, id);

-- 2. Customer Live Tracking Sessions & Tokens Table (T0125)
CREATE TABLE IF NOT EXISTS "Nova".t0125 (
    id                  SERIAL PRIMARY KEY,
    run_stop_id         INT NOT NULL REFERENCES "Nova".t0113(id) ON DELETE CASCADE,
    sales_order_id      INT REFERENCES "Nova".t0012(id),
    customer_id         INT NOT NULL REFERENCES "Nova".t0010(id),
    tracking_token      VARCHAR(100) NOT NULL UNIQUE,
    token_expires_at    TIMESTAMPTZ NOT NULL,
    notification_sent_at TIMESTAMPTZ,
    notification_channel VARCHAR(30) NOT NULL DEFAULT 'SMS',
    notification_status  VARCHAR(30) NOT NULL DEFAULT 'Pending',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    business_id         INT REFERENCES "Nova".t0059(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT,
    update_number       INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0125 IS 'Customer Live Tracking Sessions — Secure unguessable token-based customer delivery tracking sessions and dispatch alerts';
COMMENT ON COLUMN "Nova".t0125.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0125.run_stop_id IS 'Target delivery run stop / manifest item (FK to t0113)';
COMMENT ON COLUMN "Nova".t0125.sales_order_id IS 'Associated sales order (FK to t0012)';
COMMENT ON COLUMN "Nova".t0125.customer_id IS 'Recipient customer reference (FK to t0010)';
COMMENT ON COLUMN "Nova".t0125.tracking_token IS 'Cryptographically secure public URL access token for customer live tracking';
COMMENT ON COLUMN "Nova".t0125.token_expires_at IS 'Timestamp when the tracking link expires';
COMMENT ON COLUMN "Nova".t0125.notification_sent_at IS 'Timestamp when SMS/WhatsApp customer ETA notification was dispatched';
COMMENT ON COLUMN "Nova".t0125.notification_channel IS 'Delivery alert channel: SMS | WhatsApp | Email';
COMMENT ON COLUMN "Nova".t0125.notification_status IS 'Notification status: Pending | Sent | Delivered | Failed';
COMMENT ON COLUMN "Nova".t0125.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE UNIQUE INDEX IF NOT EXISTS idx_t0125_tracking_token ON "Nova".t0125(tracking_token);
CREATE INDEX IF NOT EXISTS idx_t0125_run_stop_id ON "Nova".t0125(run_stop_id);
CREATE INDEX IF NOT EXISTS idx_t0125_sales_order_id ON "Nova".t0125(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0125_customer_id ON "Nova".t0125(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id ON "Nova".t0125(business_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id_run_stop ON "Nova".t0125(business_id, run_stop_id);
CREATE INDEX IF NOT EXISTS idx_t0125_business_id_id ON "Nova".t0125(business_id, id);

-- 3. Geofence Detection Events Table (T0126)
CREATE TABLE IF NOT EXISTS "Nova".t0126 (
    id                      SERIAL PRIMARY KEY,
    run_stop_id             INT NOT NULL REFERENCES "Nova".t0113(id) ON DELETE CASCADE,
    run_id                  INT NOT NULL REFERENCES "Nova".t0112(id) ON DELETE CASCADE,
    driver_id               INT REFERENCES "Nova".t0021(id),
    event_type              VARCHAR(50) NOT NULL,
    distance_meters         NUMERIC(10,2) NOT NULL DEFAULT 0.0,
    latitude                NUMERIC(10,7) NOT NULL,
    longitude               NUMERIC(10,7) NOT NULL,
    event_timestamp         TIMESTAMPTZ NOT NULL DEFAULT now(),
    dwell_duration_seconds  INT NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    business_id             INT REFERENCES "Nova".t0059(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              INT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              INT,
    update_number           INT NOT NULL DEFAULT 1
);

COMMENT ON TABLE "Nova".t0126 IS 'Geofence Detection Events — Automated boundary crossing events (arrival/departure) around customer delivery addresses';
COMMENT ON COLUMN "Nova".t0126.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0126.run_stop_id IS 'Target delivery stop reference (FK to t0113)';
COMMENT ON COLUMN "Nova".t0126.run_id IS 'Associated delivery run reference (FK to t0112)';
COMMENT ON COLUMN "Nova".t0126.driver_id IS 'Associated driver reference (FK to t0021)';
COMMENT ON COLUMN "Nova".t0126.event_type IS 'Geofence event: ENTER_GEOFENCE | EXIT_GEOFENCE | DWELL_THRESHOLD';
COMMENT ON COLUMN "Nova".t0126.distance_meters IS 'Computed Haversine distance from vehicle to stop target coordinate in meters';
COMMENT ON COLUMN "Nova".t0126.latitude IS 'Vehicle latitude coordinate at detection event';
COMMENT ON COLUMN "Nova".t0126.longitude IS 'Vehicle longitude coordinate at detection event';
COMMENT ON COLUMN "Nova".t0126.event_timestamp IS 'Timestamp when boundary transition occurred';
COMMENT ON COLUMN "Nova".t0126.dwell_duration_seconds IS 'Total dwell duration inside customer geofence perimeter in seconds';
COMMENT ON COLUMN "Nova".t0126.business_id IS 'Tenant / business organization identifier (FK to t0059)';

CREATE INDEX IF NOT EXISTS idx_t0126_run_stop_id ON "Nova".t0126(run_stop_id);
CREATE INDEX IF NOT EXISTS idx_t0126_run_id ON "Nova".t0126(run_id);
CREATE INDEX IF NOT EXISTS idx_t0126_event_type ON "Nova".t0126(event_type);
CREATE INDEX IF NOT EXISTS idx_t0126_event_timestamp ON "Nova".t0126(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id ON "Nova".t0126(business_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id_run_stop ON "Nova".t0126(business_id, run_stop_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id_run ON "Nova".t0126(business_id, run_id);
CREATE INDEX IF NOT EXISTS idx_t0126_business_id_id ON "Nova".t0126(business_id, id);

-- 4. Extend Delivery Run Stops (T0113) and Customers (T0010) with GPS & Geofencing columns
ALTER TABLE "Nova".t0113
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,7),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10,7),
    ADD COLUMN IF NOT EXISTS geofence_radius_meters INT NOT NULL DEFAULT 150,
    ADD COLUMN IF NOT EXISTS geofence_arrived_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS geofence_departed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS live_eta_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS live_remaining_distance_km NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(100);

ALTER TABLE "Nova".t0010
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,7),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(10,7),
    ADD COLUMN IF NOT EXISTS geofence_radius_meters INT NOT NULL DEFAULT 150;

-- 5. Grant Readonly Permissions to AI / MCP Role
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nova_readonly') THEN
        GRANT SELECT ON "Nova".t0124 TO nova_readonly;
        GRANT SELECT ON "Nova".t0125 TO nova_readonly;
        GRANT SELECT ON "Nova".t0126 TO nova_readonly;
    END IF;
END $$;

COMMIT;

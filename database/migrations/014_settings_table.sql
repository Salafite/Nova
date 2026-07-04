-- 014: Add system settings table (T0025)

CREATE TABLE IF NOT EXISTS "Nova".t0025 (
    id            SERIAL PRIMARY KEY,
    setting_key   VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description   TEXT,
    setting_group VARCHAR(50)  NOT NULL DEFAULT 'General',
    is_active     BOOLEAN      NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by    INT,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by    INT,
    update_number INT          NOT NULL DEFAULT 1
);

INSERT INTO "Nova".t0025 (setting_key, setting_value, description, setting_group) VALUES
    ('app_name', 'Nova ERP', 'Application display name', 'General'),
    ('app_description', 'Enterprise Resource Planning System', 'Application description', 'General'),
    ('company_name', '', 'Default company name', 'Company'),
    ('company_address', '', 'Company address', 'Company'),
    ('company_phone', '', 'Company phone number', 'Company'),
    ('company_email', '', 'Company email', 'Company'),
    ('company_website', '', 'Company website', 'Company'),
    ('company_tax_id', '', 'Company tax identification number', 'Company'),
    ('date_format', 'YYYY-MM-DD', 'Global date format', 'Regional'),
    ('time_format', 'HH:mm:ss', 'Global time format', 'Regional'),
    ('default_language', 'en', 'Default system language', 'Regional'),
    ('default_currency', 'USD', 'Default currency code', 'Regional'),
    ('timezone', 'UTC', 'System timezone', 'Regional'),
    ('purchase_order_prefix', 'PO-', 'Purchase order number prefix', 'Purchasing'),
    ('sales_order_prefix', 'SO-', 'Sales order number prefix', 'Sales'),
    ('invoice_prefix', 'INV-', 'Invoice number prefix', 'Finance'),
    ('payment_term_id', '', 'Default payment term ID', 'Finance'),
    ('enable_auto_reorder', 'false', 'Enable automatic reorder point calculation', 'Inventory'),
    ('low_stock_threshold', '10', 'Low stock warning threshold', 'Inventory'),
    ('default_warehouse_id', '', 'Default warehouse ID', 'Inventory'),
    ('enable_multi_currency', 'false', 'Enable multi-currency support', 'Finance'),
    ('enable_debug_mode', 'false', 'Show debug information (development only)', 'System'),
    ('maintenance_mode', 'false', 'Put the system in maintenance mode', 'System')
ON CONFLICT (setting_key) DO NOTHING;

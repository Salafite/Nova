-- T0022 - Navigation Permissions (metadata-driven menu)
COMMENT ON TABLE T0022 IS 'Sidebar navigation items with permission keys for RBAC filtering';
CREATE TABLE T0022 (
    id              SERIAL PRIMARY KEY,
    module_key      VARCHAR(50) NOT NULL UNIQUE,               -- used as module id
    label           VARCHAR(100) NOT NULL,
    label_ar        VARCHAR(100),
    icon            VARCHAR(50),
    section         VARCHAR(100),                              -- group heading in sidebar
    permission_key  VARCHAR(50),                               -- NULL = always visible
    sort_order      SMALLINT    NOT NULL DEFAULT 0,
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    -- audit
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT         REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT         REFERENCES T0021(id),
    update_number   INT         NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0022.id             IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0022.module_key     IS 'Module identifier used in the frontend router (e.g. dashboard)';
COMMENT ON COLUMN T0022.label          IS 'English display name';
COMMENT ON COLUMN T0022.label_ar       IS 'Arabic display name';
COMMENT ON COLUMN T0022.icon           IS 'Emoji or icon identifier for the nav item';
COMMENT ON COLUMN T0022.section        IS 'Group heading in the sidebar (NULL = no group)';
COMMENT ON COLUMN T0022.permission_key IS 'Permission required to see this item (NULL = always visible)';
COMMENT ON COLUMN T0022.sort_order     IS 'Display order within the section';
COMMENT ON COLUMN T0022.is_active      IS 'Soft delete flag: TRUE = active, FALSE = hidden';
COMMENT ON COLUMN T0022.created_at     IS 'Record creation timestamp';
COMMENT ON COLUMN T0022.created_by     IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0022.updated_at     IS 'Last modification timestamp';
COMMENT ON COLUMN T0022.updated_by     IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0022.update_number  IS 'Version counter incremented on each update, starts at 1';

-- T0023 - Audit Log
COMMENT ON TABLE T0023 IS 'Immutable audit trail for all data changes';
CREATE TABLE T0023 (
    id            BIGSERIAL PRIMARY KEY,
    table_name    VARCHAR(10)  NOT NULL,                       -- 'T0003', 'T0012', etc.
    record_id     INT          NOT NULL,                       -- PK of the changed row
    action        VARCHAR(10)  NOT NULL,                       -- INSERT, UPDATE, DELETE
    changed_data  JSONB,                                       -- old & new values
    changed_by    INT          REFERENCES T0021(id),
    changed_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON COLUMN T0023.id           IS 'Primary key (auto-increment, bigint for high volume)';
COMMENT ON COLUMN T0023.table_name   IS 'Affected table identifier';
COMMENT ON COLUMN T0023.record_id    IS 'Primary key value of the changed record';
COMMENT ON COLUMN T0023.action       IS 'DML operation performed: INSERT, UPDATE, DELETE';
COMMENT ON COLUMN T0023.changed_data IS 'JSON diff: {before:{...}, after:{...}}';
COMMENT ON COLUMN T0023.changed_by   IS 'User who performed the change (FK to T0021)';
COMMENT ON COLUMN T0023.changed_at   IS 'Timestamp when the change occurred';

CREATE INDEX idx_T0023_table  ON T0023(table_name, record_id);
CREATE INDEX idx_T0023_date   ON T0023(changed_at);

-- ============================================================
-- TRANSACTIONS: Planning (MRP / Production Plans)
-- ============================================================

-- T0024 - Production Plans
COMMENT ON TABLE T0024 IS 'Production / MRP plans — planned manufacturing runs';
CREATE TABLE T0024 (
    id              SERIAL PRIMARY KEY,
    plan_number     VARCHAR(30) NOT NULL UNIQUE,
    product_id      INT REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    quantity        NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    start_date      DATE,
    end_date        DATE,
    status          VARCHAR(20) DEFAULT 'Draft',
    notes           TEXT,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0024.id           IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0024.plan_number  IS 'Human-readable plan reference (e.g. PLAN-001)';
COMMENT ON COLUMN T0024.product_id   IS 'Product being planned (FK to T0003)';
COMMENT ON COLUMN T0024.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0024.quantity     IS 'Quantity to produce in base UOM';
COMMENT ON COLUMN T0024.start_date   IS 'Planned production start date';
COMMENT ON COLUMN T0024.end_date     IS 'Planned completion date';
COMMENT ON COLUMN T0024.status       IS 'Plan status: Draft, Planned, Released, Completed, Cancelled';
COMMENT ON COLUMN T0024.notes        IS 'Free-text notes or comments';
COMMENT ON COLUMN T0024.created_at   IS 'Record creation timestamp';
COMMENT ON COLUMN T0024.created_by   IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0024.updated_at   IS 'Last modification timestamp';
COMMENT ON COLUMN T0024.updated_by   IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0024.update_number IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0024_status ON T0024(status);

-- ============================================================

-- T0025 - Global Settings
COMMENT ON TABLE T0025 IS 'Global system settings and preferences';
CREATE TABLE T0025 (
    id              SERIAL PRIMARY KEY,
    setting_key     VARCHAR(100) NOT NULL UNIQUE,
    setting_value   TEXT,
    description     TEXT,
    setting_group   VARCHAR(50),
    is_active       BOOLEAN DEFAULT TRUE,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0025.id           IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0025.setting_key  IS 'Unique identifier for the setting (e.g. COMP_NAME)';
COMMENT ON COLUMN T0025.setting_value IS 'Value of the setting';
COMMENT ON COLUMN T0025.description  IS 'Human-readable description';
COMMENT ON COLUMN T0025.setting_group IS 'Grouping category (e.g. System, Sales, UI)';
COMMENT ON COLUMN T0025.is_active    IS 'Is the setting active';
COMMENT ON COLUMN T0025.created_at   IS 'Record creation timestamp';
COMMENT ON COLUMN T0025.created_by   IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0025.updated_at   IS 'Last modification timestamp';
COMMENT ON COLUMN T0025.updated_by   IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0025.update_number IS 'Version counter incremented on each update, starts at 1';

-- ============================================================
-- FINANCE / ACCOUNTING
-- ============================================================

-- T0026 - Chart of Accounts
COMMENT ON TABLE T0026 IS 'Chart of Accounts — hierarchical list of all financial accounts';
CREATE TABLE T0026 (
    id              SERIAL PRIMARY KEY,
    account_code    VARCHAR(20) NOT NULL UNIQUE,
    account_name    VARCHAR(100) NOT NULL,
    account_type    VARCHAR(50) NOT NULL,        -- Asset, Liability, Equity, Revenue, Expense
    parent_id       INT REFERENCES T0026(id),
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0026.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0026.account_code IS 'Account code (e.g. 1000, 1100, 2000)';
COMMENT ON COLUMN T0026.account_name IS 'Account display name (e.g. Cash, Accounts Receivable)';
COMMENT ON COLUMN T0026.account_type IS 'Account classification: Asset, Liability, Equity, Revenue, Expense';
COMMENT ON COLUMN T0026.parent_id IS 'Parent account for hierarchy (FK to self)';
COMMENT ON COLUMN T0026.currency IS 'Base currency for this account (e.g. USD, EUR)';
COMMENT ON COLUMN T0026.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0026.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0026.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0026.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0026.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0026.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0026_type ON T0026(account_type);

-- T0027 - Journal Entries (header)
COMMENT ON TABLE T0027 IS 'Journal Entry header — double-entry journal records';
CREATE TABLE T0027 (
    id              SERIAL PRIMARY KEY,
    entry_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    reference       VARCHAR(100),
    description     VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',  -- Draft, Posted, Cancelled
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0027.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0027.entry_date IS 'Date of the journal entry';
COMMENT ON COLUMN T0027.reference IS 'Human-readable reference (e.g. JE-2024-001)';
COMMENT ON COLUMN T0027.description IS 'Narrative description of the journal entry';
COMMENT ON COLUMN T0027.status IS 'Entry status: Draft, Posted, Cancelled';
COMMENT ON COLUMN T0027.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0027.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0027.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0027.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0027.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0027_date ON T0027(entry_date);
CREATE INDEX idx_T0027_status ON T0027(status);

-- T0089 - Journal Entry Lines
COMMENT ON TABLE T0089 IS 'Journal Entry Lines — individual debit/credit lines within a journal entry';
CREATE TABLE T0089 (
    id                SERIAL PRIMARY KEY,
    journal_entry_id  INT NOT NULL REFERENCES T0027(id) ON DELETE CASCADE,
    account_id        INT NOT NULL REFERENCES T0026(id),
    description       VARCHAR(255),
    debit             NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (debit >= 0),
    credit            NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (credit >= 0),
    line_number       SMALLINT NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT REFERENCES T0021(id),
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0089.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0089.journal_entry_id IS 'Parent journal entry (FK to T0027)';
COMMENT ON COLUMN T0089.account_id IS 'Account being debited/credited (FK to T0026)';
COMMENT ON COLUMN T0089.description IS 'Line-level description';
COMMENT ON COLUMN T0089.debit IS 'Debit amount (must be >= 0)';
COMMENT ON COLUMN T0089.credit IS 'Credit amount (must be >= 0)';
COMMENT ON COLUMN T0089.line_number IS 'Line sequence number for display';
COMMENT ON COLUMN T0089.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0089.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0089.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0089.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0089.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0089_journal ON T0089(journal_entry_id);
CREATE INDEX idx_T0089_account ON T0089(account_id);

-- T0090 - Invoices (AR/AP)
COMMENT ON TABLE T0090 IS 'Invoices — accounts receivable and payable';
CREATE TABLE T0090 (
    id              SERIAL PRIMARY KEY,
    invoice_number  VARCHAR(50) NOT NULL UNIQUE,
    invoice_type    VARCHAR(20) NOT NULL DEFAULT 'Sales',  -- Sales, Purchase
    partner_id      INT NOT NULL,                           -- customer or supplier ID
    issue_date      DATE NOT NULL,
    due_date        DATE NOT NULL,
    total_amount    NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',   -- Draft, Unpaid, Paid, Cancelled
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0090.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0090.invoice_number IS 'Unique invoice reference number';
COMMENT ON COLUMN T0090.invoice_type IS 'Invoice type: Sales or Purchase';
COMMENT ON COLUMN T0090.partner_id IS 'Customer or supplier ID';
COMMENT ON COLUMN T0090.issue_date IS 'Invoice issue date';
COMMENT ON COLUMN T0090.due_date IS 'Payment due date';
COMMENT ON COLUMN T0090.total_amount IS 'Total invoice amount';
COMMENT ON COLUMN T0090.status IS 'Invoice status: Draft, Unpaid, Paid, Cancelled';
COMMENT ON COLUMN T0090.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0090.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0090.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0090.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0090.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0090.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0090_partner ON T0090(partner_id);
CREATE INDEX idx_T0090_status ON T0090(status);

-- T0091 - Payments
COMMENT ON TABLE T0091 IS 'Payments — received from customers or made to suppliers';
CREATE TABLE T0091 (
    id                SERIAL PRIMARY KEY,
    payment_date      DATE NOT NULL,
    invoice_id        INT REFERENCES T0090(id),
    partner_id        INT NOT NULL,
    amount            NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_method    VARCHAR(50) NOT NULL DEFAULT 'Bank Transfer',  -- Cash, Bank Transfer, Card, Check
    reference         VARCHAR(100),
    status            VARCHAR(20) NOT NULL DEFAULT 'Completed',
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT REFERENCES T0021(id),
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0091.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0091.payment_date IS 'Date the payment was made/received';
COMMENT ON COLUMN T0091.invoice_id IS 'Invoice being paid (FK to T0090, NULL if not linked)';
COMMENT ON COLUMN T0091.partner_id IS 'Customer or supplier ID';
COMMENT ON COLUMN T0091.amount IS 'Payment amount (must be > 0)';
COMMENT ON COLUMN T0091.payment_method IS 'Payment method: Cash, Bank Transfer, Card, Check';
COMMENT ON COLUMN T0091.reference IS 'External payment reference or transaction ID';
COMMENT ON COLUMN T0091.status IS 'Payment status (Completed, Pending, Failed, Refunded)';
COMMENT ON COLUMN T0091.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0091.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0091.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0091.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0091.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0091.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0091_invoice ON T0091(invoice_id);
CREATE INDEX idx_T0091_partner ON T0091(partner_id);
CREATE INDEX idx_T0091_date ON T0091(payment_date);

-- ============================================================
-- VIEWS
-- ============================================================

-- V_DASHBOARD_TODAY - Daily operational snapshot
COMMENT ON VIEW V_DASHBOARD_TODAY IS 'Dashboard KPIs for today: revenue, orders, low stock, pending items';
CREATE VIEW V_DASHBOARD_TODAY AS
SELECT
    COALESCE(SUM(CASE WHEN status IN ('Paid','Shipped') THEN grand_total END), 0) AS today_revenue,
    COUNT(DISTINCT T0012.id) FILTER (WHERE T0012.order_date = CURRENT_DATE) AS today_orders,
    (SELECT COUNT(*) FROM T0010 WHERE is_active) AS total_customers,
    (SELECT COUNT(*) FROM T0009 WHERE qty <= reorder_level) AS low_stock_items,
    (SELECT COUNT(*) FROM T0014 WHERE status = 'Pending') AS pending_pos,
    (SELECT COUNT(*) FROM T0019 WHERE result = 'Pending') AS pending_qc
FROM T0012
WHERE T0012.order_date = CURRENT_DATE;

-- V_INVENTORY_SUMMARY - Stock value & reorder status per product
COMMENT ON VIEW V_INVENTORY_SUMMARY IS 'Stock quantities, value, and reorder alerts across all warehouses';
CREATE VIEW V_INVENTORY_SUMMARY AS
SELECT
    T0003.id           AS product_id,
    T0003.name         AS product_name,
    T0003.sku,
    T0003.category,
    COALESCE(SUM(T0009.qty), 0) AS total_qty,
    T0003.price,
    (COALESCE(SUM(T0009.qty), 0) * T0003.price) AS stock_value,
    MIN(T0009.reorder_level) AS reorder_level,
    CASE WHEN COALESCE(SUM(T0009.qty), 0) <= MIN(T0009.reorder_level) THEN 'Reorder' ELSE 'OK' END AS stock_status
FROM T0003
LEFT JOIN T0009 ON T0009.product_id = T0003.id
WHERE T0003.is_active
GROUP BY T0003.id, T0003.name, T0003.sku, T0003.category, T0003.price;

-- V_AR_AGING - Accounts Receivable aging summary
COMMENT ON VIEW V_AR_AGING IS 'Customer outstanding balances with invoice aging';
CREATE VIEW V_AR_AGING AS
SELECT
    T0010.id          AS customer_id,
    T0010.name        AS customer_name,
    T0010.balance     AS outstanding,
    COUNT(T0012.id)   AS open_invoices,
    MAX(T0012.order_date) AS last_order_date
FROM T0010
LEFT JOIN T0012 ON T0012.customer_id = T0010.id AND T0012.status NOT IN ('Cancelled')
WHERE T0010.balance > 0
GROUP BY T0010.id, T0010.name, T0010.balance;

-- V_REVENUE_MONTHLY - Monthly revenue aggregation
COMMENT ON VIEW V_REVENUE_MONTHLY IS 'Monthly sales revenue and tax collected';
CREATE VIEW V_REVENUE_MONTHLY AS
SELECT
    DATE_TRUNC('month', order_date)::DATE AS month,
    COUNT(*)                              AS order_count,
    SUM(grand_total)                      AS revenue,
    SUM(tax)                              AS tax_collected
FROM T0012
WHERE status NOT IN ('Cancelled')
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month DESC;

-- V_EXPENSE_MONTHLY - Monthly purchasing expenses
COMMENT ON VIEW V_EXPENSE_MONTHLY IS 'Monthly purchasing costs from received POs';
CREATE VIEW V_EXPENSE_MONTHLY AS
SELECT
    DATE_TRUNC('month', order_date)::DATE AS month,
    COUNT(*)                              AS po_count,
    SUM(total)                            AS expenses
FROM T0014
WHERE status = 'Received'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month DESC;

-- V_PNL - Profit & Loss summary by month
COMMENT ON VIEW V_PNL IS 'Monthly P&L: revenue minus expenses';
CREATE VIEW V_PNL AS
SELECT
    COALESCE(r.month, e.month) AS month,
    COALESCE(r.revenue, 0)     AS revenue,
    COALESCE(e.expenses, 0)    AS expenses,
    COALESCE(r.revenue, 0) - COALESCE(e.expenses, 0) AS net_profit
FROM V_REVENUE_MONTHLY r
FULL JOIN V_EXPENSE_MONTHLY e ON e.month = r.month
ORDER BY month DESC;

-- V_MFG_SUMMARY - Manufacturing order status summary
COMMENT ON VIEW V_MFG_SUMMARY IS 'Production order counts and nearest due dates by status';
CREATE VIEW V_MFG_SUMMARY AS
SELECT
    status,
    COUNT(*)          AS order_count,
    SUM(quantity)     AS total_quantity,
    MIN(due_date)     AS nearest_due
FROM T0018
GROUP BY status;

-- V_QC_PASS_RATE - Quality pass rates by product
COMMENT ON VIEW V_QC_PASS_RATE IS 'QC pass/fail rates per product name';
CREATE VIEW V_QC_PASS_RATE AS
SELECT
    product_name,
    COUNT(*)                                          AS total_inspections,
    COUNT(*) FILTER (WHERE result = 'Pass')           AS passed,
    ROUND(COUNT(*) FILTER (WHERE result = 'Pass') * 100.0 / GREATEST(COUNT(*), 1)) AS pass_rate_pct
FROM T0019
GROUP BY product_name;

-- V_SHOPFLOOR_ACTIVE - Active shop floor jobs by workstation
COMMENT ON VIEW V_SHOPFLOOR_ACTIVE IS 'Workstation workload: active and pending jobs';
CREATE VIEW V_SHOPFLOOR_ACTIVE AS
SELECT
    workstation,
    COUNT(*)                                         AS active_jobs,
    SUM(quantity)                                    AS total_qty,
    COUNT(*) FILTER (WHERE status = 'In Progress')   AS in_progress,
    COUNT(*) FILTER (WHERE status = 'Pending')       AS pending
FROM T0020
WHERE status IN ('Pending','In Progress')
GROUP BY workstation;

-- V_NAV_ITEMS - Permission-based navigation menu (metadata-driven)
COMMENT ON VIEW V_NAV_ITEMS IS 'Sidebar navigation fed by RBAC: joins permission keys to user roles';
CREATE VIEW V_NAV_ITEMS AS
SELECT
    section,
    module_key  AS id,
    icon,
    label,
    label_ar,
    permission_key AS permission
FROM T0022
WHERE is_active
ORDER BY sort_order;

-- V_INSTALLMENT_STATUS - Installment plan payment tracking
COMMENT ON VIEW V_INSTALLMENT_STATUS IS 'Installment plan progress: paid vs due per sales order';
CREATE VIEW V_INSTALLMENT_STATUS AS
SELECT
    T0016.id,
    T0012.order_number,
    T0010.name                                AS customer_name,
    T0016.total_amount,
    T0016.num_installments,
    COUNT(T0017.id)                           AS payments_made,
    COALESCE(SUM(T0017.amount_paid), 0)       AS total_paid,
    T0016.total_amount - COALESCE(SUM(T0017.amount_paid), 0) AS remaining,
    T0016.status
FROM T0016
JOIN T0012 ON T0012.id = T0016.sales_order_id
JOIN T0010 ON T0010.id = T0012.customer_id
LEFT JOIN T0017 ON T0017.installment_plan_id = T0016.id
GROUP BY T0016.id, T0012.order_number, T0010.name, T0016.total_amount, T0016.num_installments, T0016.status;

-- ============================================================
-- SEED DATA
-- ============================================================

-- UOM base units
INSERT INTO T0001 (uom_code, uom_name, category, is_base_unit) VALUES
    ('pcs', 'Piece',   'Quantity', true),
    ('kg',  'Kilogram','Weight',   true),
    ('g',   'Gram',    'Weight',   false),
    ('lb',  'Pound',   'Weight',   false),
    ('L',   'Liter',   'Volume',   true),
    ('ml',  'Milliliter','Volume', false),
    ('m',   'Meter',   'Length',   true);

-- UOM conversions
INSERT INTO T0002 (from_uom_id, to_uom_id, factor)
SELECT f.id, t.id, 1000 FROM T0001 f, T0001 t WHERE f.uom_code='kg'  AND t.uom_code='g'
UNION ALL
SELECT f.id, t.id, 453.592 FROM T0001 f, T0001 t WHERE f.uom_code='lb' AND t.uom_code='g'
UNION ALL
SELECT f.id, t.id, 1000 FROM T0001 f, T0001 t WHERE f.uom_code='L'   AND t.uom_code='ml';

-- Attribute definitions
INSERT INTO T0005 (attribute_name, attribute_type, sort_order) VALUES
    ('Color',       'Select', 1),
    ('Size',        'Select', 2),
    ('Material',    'Text',   3),
    ('Weight (g)',  'Number', 4);

-- Warehouses
INSERT INTO T0008 (name, location) VALUES
    ('Main',      'Warehouse A - 123 Industrial Blvd'),
    ('Secondary', 'Warehouse B - 456 Commerce Dr');

-- Products (seed matches existing in-memory data)
INSERT INTO T0003 (name, sku, price, category, tax_rate) VALUES
    ('Coffee Beans', 'CB-001', 12.50, 'Beverages', 0.05),
    ('Green Tea',    'GT-002',  8.00, 'Beverages', 0.05),
    ('Basmati Rice', 'BR-003', 15.00, 'Grocery',   0.05),
    ('Olive Oil',    'OO-004', 22.00, 'Grocery',   0.05),
    ('Pasta',        'PA-005',  4.50, 'Grocery',   0.05),
    ('Cake',         'CK-006',  3.00, 'Food',      0.05);

-- Product UOM assignments (base = pcs for all)
INSERT INTO T0007 (product_id, base_uom_id)
SELECT T0003.id, T0001.id FROM T0003, T0001 WHERE T0001.uom_code = 'pcs';

-- Initial stock: 100 each in Main warehouse, base UOM
INSERT INTO T0009 (product_id, warehouse_id, qty, reorder_level)
SELECT T0003.id, T0008.id, 100, 10
FROM T0003 CROSS JOIN T0008
WHERE T0003.is_active AND T0008.id = 1;

-- Customers (matches existing in-memory seed)
INSERT INTO T0010 (name, group_name, phone, credit_limit) VALUES
    ('Alice Johnson', 'Retail',    '+1-555-0101', 5000),
    ('Bob Williams',  'Wholesale', '+1-555-0102', 20000),
    ('Carol Davis',   'Retail',    '+1-555-0103', 3000);

-- Suppliers (matches existing in-memory seed)
INSERT INTO T0011 (name, category, phone, email, rating) VALUES
    ('Global Traders',   'Grocery',   '+1-555-0201', 'info@globaltraders.com', 4),
    ('Fresh Foods Co.',  'Food',      '+1-555-0202', 'orders@freshfoods.co',   5),
    ('TechParts Ltd.',   'Electronics','+1-555-0203', 'sales@techparts.com',   3);

-- Demo users (password hashes to be generated by app on first run)
INSERT INTO T0021 (username, password_hash, full_name, email, role, permissions, status) VALUES
    ('admin',  '', 'Administrator', 'admin@novaerp.com', 'Admin',   ARRAY['*'],                                       'Active'),
    ('sales',  '', 'Sales User',    'sales@novaerp.com', 'Sales Rep', ARRAY['SALES_VIEW','CUSTOMERS_VIEW'],              'Active'),
    ('viewer', '', 'Viewer User',   'viewer@novaerp.com','Viewer', ARRAY['DASHBOARD_VIEW','PRODUCTS_VIEW','CUSTOMERS_VIEW'], 'Active');

-- Navigation items (drives sidebar, matches NavigationData.json)
INSERT INTO T0022 (module_key, label, label_ar, icon, section, permission_key, sort_order) VALUES
    ('home',         'Home',          'الرئيسية',     '🏠', 'Foundation',        NULL,                0),
    ('dashboard',    'Dashboard',    'لوحة القيادة', '📊', 'Foundation',        'DASHBOARD_VIEW',    1),
    ('pos',          'POS',          'نقطة البيع',  '🛒', 'Foundation',        'POS_VIEW',          2),
    ('products',     'Products',     'المنتجات',    '📦', 'Foundation',        'PRODUCTS_VIEW',     3),
    ('inventory',    'Inventory',    'المخزون',     '📋', 'Foundation',        'INVENTORY_VIEW',    4),
    ('warehouse',    'Warehouse',    'المستودع',    '🏭', 'Foundation',        'WAREHOUSE_VIEW',    5),
    ('customers',    'Customers',    'العملاء',     '👥', 'CRM & Procurement', 'CUSTOMERS_VIEW',    6),
    ('suppliers',    'Suppliers',    'الموردين',    '🚚', 'CRM & Procurement', 'SUPPLIERS_VIEW',    7),
    ('purchasing',   'Purchasing',   'المشتريات',   '📑', 'CRM & Procurement', 'PURCHASING_VIEW',   8),
    ('purchase_requisitions', 'Requisitions', 'طلبات الشراء', '📄', 'CRM & Procurement', 'PURCHASING_VIEW',   9),
    ('sales',        'Sales',        'المبيعات',    '💰', 'CRM & Procurement', 'SALES_VIEW',       10),
    ('quotations',   'Quotations',   'عروض الأسعار','📄', 'CRM & Procurement', 'SALES_VIEW',       11),
    ('finance',      'Finance',      'المالية',     '🏦', 'CRM & Procurement', 'FINANCE_VIEW',     12),
    ('settings',     'Settings',     'الإعدادات',   '⚙️', 'CRM & Procurement', 'ADMIN_VIEW',       13),
    ('admin',        'Admin',        'الإدارة',     '🔒', 'CRM & Procurement', 'ADMIN_VIEW',       14),
    ('manufacturing','Manufacturing','التصنيع',    '⚙️', 'Manufacturing',     'MFG_VIEW',         15),
    ('planning',     'Planning',     'التخطيط',    '📅', 'Manufacturing',     'PLANNING_VIEW',    16),
    ('shopfloor',    'Shop Floor',   'أرضية المصنع','🔧', 'Manufacturing',     'SHOPFLOOR_VIEW',   17),
    ('quality',      'Quality',      'الجودة',      '✅', 'Manufacturing',     'QUALITY_VIEW',     18);

-- Additional modules
INSERT INTO T0022 (module_key, label, label_ar, icon, section, permission_key, sort_order) VALUES
    ('hr',           'HRMS',          'الموارد البشرية',    '👤', 'HR Management',      'HR_VIEW',           19),
    ('attendance',   'Attendance',    'الحضور',            '⏰', 'HR Management',      'HR_VIEW',           20),
    ('leave',        'Leave',         'الإجازات',          '🏖️', 'HR Management',      'HR_VIEW',           21),
    ('payroll',      'Payroll',       'الرواتب',           '💰', 'HR Management',      'HR_VIEW',           22),
    ('recruitment',  'Recruitment',   'التوظيف',           '🔍', 'HR Management',      'HR_VIEW',           23),
    ('maintenance',  'Maintenance',   'الصيانة',           '🔧', 'Maintenance',        'MAINTENANCE_VIEW',  24),
    ('project',      'Projects',      'المشاريع',          '📋', 'Projects & Services','PROJECTS_VIEW',     25),
    ('resource',     'Resources',     'الموارد',           '👥', 'Projects & Services','PROJECTS_VIEW',     26),
    ('timesheets',   'Timesheets',    'ساعات العمل',       '⏱️', 'Projects & Services','PROJECTS_VIEW',     27),
    ('service',      'Service',       'الخدمات',           '🎧', 'Projects & Services','PROJECTS_VIEW',     28),
    ('contracts',    'Contracts',     'العقود',            '📄', 'Projects & Services','PROJECTS_VIEW',     29),
    ('bi',           'BI',            'ذكاء الأعمال',      '📊', 'BI & Analytics',     'BI_VIEW',           30),
    ('executive',    'Executive',     'التقارير التنفيذية', '📈', 'BI & Analytics',     'BI_VIEW',           31),
    ('operational',  'Operations',    'التحليلات التشغيلية','🔍', 'BI & Analytics',     'BI_VIEW',           32),
    ('forecast',     'Forecast',      'التوقعات',          '📉', 'BI & Analytics',     'BI_VIEW',           33),
    ('insights',     'Insights',      'الرؤى',             '💡', 'BI & Analytics',     'BI_VIEW',           34),
    ('mobile',       'Mobile',        'الجوال',            '📱', 'Mobile & E-Commerce','INTEGRATIONS_VIEW', 35),
    ('mobilepos',    'Mobile POS',    'نقاط البيع المتنقلة','📲', 'Mobile & E-Commerce','INTEGRATIONS_VIEW', 36),
    ('ecommerce',    'E-Commerce',    'التجارة الإلكترونية','🛒', 'Mobile & E-Commerce','INTEGRATIONS_VIEW', 37),
    ('integrations', 'Integrations',  'التكاملات',         '🔗', 'Mobile & E-Commerce','INTEGRATIONS_VIEW', 38),
    ('api',          'API Platform',  'منصة API',          '🔌', 'Mobile & E-Commerce','INTEGRATIONS_VIEW', 39),
    ('tenant',       'Tenants',       'المستأجرون',        '🏢', 'Enterprise',         'ENTERPRISE_VIEW',   40),
    ('workflow',     'Workflow',      'سير العمل',         '🔄', 'Enterprise',         'ENTERPRISE_VIEW',   41),
    ('documents',    'Documents',     'المستندات',         '📁', 'Enterprise',         'ENTERPRISE_VIEW',   42),
    ('governance',   'Governance',    'الحوكمة',           '⚖️', 'Enterprise',         'ENTERPRISE_VIEW',   43),
    ('platform',     'Platform',      'المنصة',            '☁️', 'Enterprise',         'ENTERPRISE_VIEW',   44);

-- Global Settings (T0025)
INSERT INTO T0025 (setting_key, setting_value, setting_group, description) VALUES
    ('COMPANY_NAME', 'Global Manufacturing Corp', 'Company Profile', 'Company Name'),
    ('COMPANY_REG_NUM', 'GMC-9982-X', 'Company Profile', 'Company Registration Number'),
    ('SYSTEM_LANGUAGE', 'en-US', 'Company Profile', 'System Language'),

-- ============================================================
-- HR MANAGEMENT: Departments & Designations
-- ============================================================

-- T0028 - Departments
COMMENT ON TABLE T0028 IS 'HR — Organizational departments';
CREATE TABLE T0028 (
    id              SERIAL PRIMARY KEY,
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(100) NOT NULL,
    parent_id       INT REFERENCES T0028(id),
    manager_id      INT REFERENCES T0021(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0028.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0028.department_code IS 'Unique department code';
COMMENT ON COLUMN T0028.department_name IS 'Department display name';
COMMENT ON COLUMN T0028.parent_id IS 'Parent department for hierarchy (FK to self)';
COMMENT ON COLUMN T0028.manager_id IS 'Department manager (FK to T0021)';
COMMENT ON COLUMN T0028.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0028.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0028.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0028.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0028.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0028.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0029 - Designations
COMMENT ON TABLE T0029 IS 'HR — Job designations / titles';
CREATE TABLE T0029 (
    id                SERIAL PRIMARY KEY,
    designation_code  VARCHAR(20) NOT NULL UNIQUE,
    designation_name  VARCHAR(100) NOT NULL,
    department_id     INT REFERENCES T0028(id),
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT REFERENCES T0021(id),
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0029.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0029.designation_code IS 'Unique designation code';
COMMENT ON COLUMN T0029.designation_name IS 'Job title / designation display name';
COMMENT ON COLUMN T0029.department_id IS 'Department this designation belongs to (FK to T0028)';
COMMENT ON COLUMN T0029.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0029.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0029.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0029.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0029.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0029.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0030 - Employees
COMMENT ON TABLE T0030 IS 'HR — Employee master records';
CREATE TABLE T0030 (
    id                SERIAL PRIMARY KEY,
    employee_code     VARCHAR(30) NOT NULL UNIQUE,
    full_name         VARCHAR(200) NOT NULL,
    arabic_name       VARCHAR(200),
    email             VARCHAR(200),
    phone             VARCHAR(30),
    address           TEXT,
    national_id       VARCHAR(50),
    passport_no       VARCHAR(50),
    gender            VARCHAR(10),
    marital_status    VARCHAR(20),
    birth_date        DATE,
    hire_date         DATE,
    termination_date  DATE,
    employment_status VARCHAR(30) DEFAULT 'Active',
    department_id     INT REFERENCES T0028(id),
    designation_id    INT REFERENCES T0029(id),
    manager_id        INT REFERENCES T0030(id),
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT REFERENCES T0021(id),
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0030.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0030.employee_code IS 'Unique employee identifier code';
COMMENT ON COLUMN T0030.full_name IS 'Employee full name in English';
COMMENT ON COLUMN T0030.arabic_name IS 'Employee full name in Arabic';
COMMENT ON COLUMN T0030.email IS 'Employee work email address';
COMMENT ON COLUMN T0030.phone IS 'Employee contact phone number';
COMMENT ON COLUMN T0030.address IS 'Employee residential address';
COMMENT ON COLUMN T0030.national_id IS 'National ID or civil ID number';
COMMENT ON COLUMN T0030.passport_no IS 'Passport number';
COMMENT ON COLUMN T0030.gender IS 'Employee gender';
COMMENT ON COLUMN T0030.marital_status IS 'Employee marital status';
COMMENT ON COLUMN T0030.birth_date IS 'Employee date of birth';
COMMENT ON COLUMN T0030.hire_date IS 'Date of employment start';
COMMENT ON COLUMN T0030.termination_date IS 'Date of employment termination (if applicable)';
COMMENT ON COLUMN T0030.employment_status IS 'Current employment status (Active, Terminated, On Leave)';
COMMENT ON COLUMN T0030.department_id IS 'Assigned department (FK to T0028)';
COMMENT ON COLUMN T0030.designation_id IS 'Assigned job title / designation (FK to T0029)';
COMMENT ON COLUMN T0030.manager_id IS 'Direct reporting manager (FK to self/T0030)';
COMMENT ON COLUMN T0030.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0030.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0030.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0030.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0030.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0030.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0030_dept ON T0030(department_id);
CREATE INDEX idx_T0030_status ON T0030(employment_status);

-- T0031 - Employee Contracts
COMMENT ON TABLE T0031 IS 'HR — Employee contract details';
CREATE TABLE T0031 (
    id                  SERIAL PRIMARY KEY,
    employee_id         INT NOT NULL REFERENCES T0030(id),
    contract_type       VARCHAR(50) NOT NULL DEFAULT 'Permanent',
    start_date          DATE NOT NULL,
    end_date            DATE,
    basic_salary        NUMERIC(12,2) DEFAULT 0,
    housing_allowance   NUMERIC(12,2) DEFAULT 0,
    transport_allowance NUMERIC(12,2) DEFAULT 0,
    other_allowances    NUMERIC(12,2) DEFAULT 0,
    currency            VARCHAR(10) DEFAULT 'USD',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT REFERENCES T0021(id),
    update_number       INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0031.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0031.employee_id IS 'Employee this contract belongs to (FK to T0030)';
COMMENT ON COLUMN T0031.contract_type IS 'Contract type (Permanent, Fixed Term, Probation, Intern)';
COMMENT ON COLUMN T0031.start_date IS 'Contract effective start date';
COMMENT ON COLUMN T0031.end_date IS 'Contract expiry date (NULL = indefinite)';
COMMENT ON COLUMN T0031.basic_salary IS 'Base salary amount excluding allowances';
COMMENT ON COLUMN T0031.housing_allowance IS 'Housing allowance amount';
COMMENT ON COLUMN T0031.transport_allowance IS 'Transportation allowance amount';
COMMENT ON COLUMN T0031.other_allowances IS 'Other miscellaneous allowances';
COMMENT ON COLUMN T0031.currency IS 'Salary currency code (e.g. USD, EUR, SAR)';
COMMENT ON COLUMN T0031.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0031.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0031.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0031.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0031.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0031.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0031_employee ON T0031(employee_id);

-- T0032 - Employee Documents
COMMENT ON TABLE T0032 IS 'HR — Employee document attachments';
CREATE TABLE T0032 (
    id              SERIAL PRIMARY KEY,
    employee_id     INT NOT NULL REFERENCES T0030(id),
    document_type   VARCHAR(50) NOT NULL,
    document_name   VARCHAR(200) NOT NULL,
    file_path       VARCHAR(500),
    expiry_date     DATE,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0032.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0032.employee_id IS 'Employee who owns this document (FK to T0030)';
COMMENT ON COLUMN T0032.document_type IS 'Category of document (Passport, ID, Certificate, Contract)';
COMMENT ON COLUMN T0032.document_name IS 'Display name of the document';
COMMENT ON COLUMN T0032.file_path IS 'File system or blob storage path';
COMMENT ON COLUMN T0032.expiry_date IS 'Document expiry date (e.g. passport expiration)';
COMMENT ON COLUMN T0032.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0032.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0032.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0032.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0032.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0032.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0032_employee ON T0032(employee_id);

-- ============================================================
-- HR MANAGEMENT: Time & Attendance
-- ============================================================

-- T0033 - Shifts
COMMENT ON TABLE T0033 IS 'HR — Work shift definitions';
CREATE TABLE T0033 (
    id            SERIAL PRIMARY KEY,
    shift_code    VARCHAR(20) NOT NULL UNIQUE,
    shift_name    VARCHAR(100) NOT NULL,
    start_time    TIME NOT NULL,
    end_time      TIME NOT NULL,
    grace_minutes SMALLINT DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT REFERENCES T0021(id),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT REFERENCES T0021(id),
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0033.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0033.shift_code IS 'Unique shift code (e.g. MORNING, EVENING)';
COMMENT ON COLUMN T0033.shift_name IS 'Shift display name';
COMMENT ON COLUMN T0033.start_time IS 'Shift start time';
COMMENT ON COLUMN T0033.end_time IS 'Shift end time';
COMMENT ON COLUMN T0033.grace_minutes IS 'Grace period in minutes before marking late';
COMMENT ON COLUMN T0033.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0033.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0033.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0033.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0033.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0033.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0034 - Attendance Records
COMMENT ON TABLE T0034 IS 'HR — Daily employee attendance logs';
CREATE TABLE T0034 (
    id            SERIAL PRIMARY KEY,
    employee_id   INT NOT NULL REFERENCES T0030(id),
    date          DATE NOT NULL,
    shift_id      INT REFERENCES T0033(id),
    clock_in      TIMESTAMPTZ,
    clock_out     TIMESTAMPTZ,
    status        VARCHAR(30) DEFAULT 'Present',
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT REFERENCES T0021(id),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT REFERENCES T0021(id),
    update_number INT NOT NULL DEFAULT 1,
    UNIQUE (employee_id, date)
);
COMMENT ON COLUMN T0034.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0034.employee_id IS 'Employee attendance record (FK to T0030)';
COMMENT ON COLUMN T0034.date IS 'Attendance date';
COMMENT ON COLUMN T0034.shift_id IS 'Assigned shift for this day (FK to T0033)';
COMMENT ON COLUMN T0034.clock_in IS 'Actual clock-in timestamp';
COMMENT ON COLUMN T0034.clock_out IS 'Actual clock-out timestamp';
COMMENT ON COLUMN T0034.status IS 'Attendance status (Present, Absent, Late, Half Day, Holiday)';
COMMENT ON COLUMN T0034.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0034.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0034.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0034.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0034.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0034.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0034_date ON T0034(date);
CREATE INDEX idx_T0034_employee ON T0034(employee_id);

-- T0035 - Leave Types
COMMENT ON TABLE T0035 IS 'HR — Leave / absence type definitions';
CREATE TABLE T0035 (
    id              SERIAL PRIMARY KEY,
    leave_code      VARCHAR(20) NOT NULL UNIQUE,
    leave_name      VARCHAR(100) NOT NULL,
    days_per_year   NUMERIC(5,1) DEFAULT 0,
    is_paid         BOOLEAN NOT NULL DEFAULT true,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0035.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0035.leave_code IS 'Unique leave type code (e.g. ANNUAL, SICK)';
COMMENT ON COLUMN T0035.leave_name IS 'Leave type display name';
COMMENT ON COLUMN T0035.days_per_year IS 'Annual entitlement in days';
COMMENT ON COLUMN T0035.is_paid IS 'TRUE = paid leave, FALSE = unpaid leave';
COMMENT ON COLUMN T0035.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0035.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0035.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0035.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0035.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0035.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0036 - Leave Requests
COMMENT ON TABLE T0036 IS 'HR — Employee leave / absence requests';
CREATE TABLE T0036 (
    id              SERIAL PRIMARY KEY,
    employee_id     INT NOT NULL REFERENCES T0030(id),
    leave_type_id   INT NOT NULL REFERENCES T0035(id),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    days            NUMERIC(5,1) NOT NULL,
    reason          TEXT,
    status          VARCHAR(30) DEFAULT 'Pending',
    approved_by     INT REFERENCES T0021(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0036.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0036.employee_id IS 'Employee requesting leave (FK to T0030)';
COMMENT ON COLUMN T0036.leave_type_id IS 'Type of leave being requested (FK to T0035)';
COMMENT ON COLUMN T0036.start_date IS 'Leave start date';
COMMENT ON COLUMN T0036.end_date IS 'Leave end date';
COMMENT ON COLUMN T0036.days IS 'Number of leave days (including weekends if applicable)';
COMMENT ON COLUMN T0036.reason IS 'Reason for leave request';
COMMENT ON COLUMN T0036.status IS 'Request status (Pending, Approved, Rejected, Cancelled)';
COMMENT ON COLUMN T0036.approved_by IS 'User who approved or rejected this request (FK to T0021)';
COMMENT ON COLUMN T0036.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0036.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0036.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0036.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0036.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0036.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0036_employee ON T0036(employee_id);
CREATE INDEX idx_T0036_status ON T0036(status);

-- ============================================================
-- HR MANAGEMENT: Payroll
-- ============================================================

-- T0037 - Payroll Periods
COMMENT ON TABLE T0037 IS 'HR — Payroll processing periods';
CREATE TABLE T0037 (
    id            SERIAL PRIMARY KEY,
    period_code   VARCHAR(20) NOT NULL UNIQUE,
    period_name   VARCHAR(100) NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    status        VARCHAR(30) DEFAULT 'Open',
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    INT REFERENCES T0021(id),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    INT REFERENCES T0021(id),
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0037.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0037.period_code IS 'Unique payroll period code (e.g. P2026-01)';
COMMENT ON COLUMN T0037.period_name IS 'Payroll period display name (e.g. January 2026)';
COMMENT ON COLUMN T0037.start_date IS 'Payroll period start date';
COMMENT ON COLUMN T0037.end_date IS 'Payroll period end date';
COMMENT ON COLUMN T0037.status IS 'Period status (Open, Processing, Closed)';
COMMENT ON COLUMN T0037.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0037.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0037.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0037.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0037.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0037.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0038 - Payroll Entries
COMMENT ON TABLE T0038 IS 'HR — Employee payroll calculations per period';
CREATE TABLE T0038 (
    id                  SERIAL PRIMARY KEY,
    employee_id         INT NOT NULL REFERENCES T0030(id),
    payroll_period_id   INT NOT NULL REFERENCES T0037(id),
    basic_salary        NUMERIC(12,2) DEFAULT 0,
    housing_allowance   NUMERIC(12,2) DEFAULT 0,
    transport_allowance NUMERIC(12,2) DEFAULT 0,
    other_allowances    NUMERIC(12,2) DEFAULT 0,
    overtime            NUMERIC(12,2) DEFAULT 0,
    deductions          NUMERIC(12,2) DEFAULT 0,
    tax                 NUMERIC(12,2) DEFAULT 0,
    gross_pay           NUMERIC(12,2) DEFAULT 0,
    net_pay             NUMERIC(12,2) DEFAULT 0,
    status              VARCHAR(30) DEFAULT 'Draft',
    payment_date        DATE,
    notes               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT REFERENCES T0021(id),
    update_number       INT NOT NULL DEFAULT 1,
    UNIQUE (employee_id, payroll_period_id)
);
COMMENT ON COLUMN T0038.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0038.employee_id IS 'Employee being paid (FK to T0030)';
COMMENT ON COLUMN T0038.payroll_period_id IS 'Payroll period this entry belongs to (FK to T0037)';
COMMENT ON COLUMN T0038.basic_salary IS 'Base salary for this period';
COMMENT ON COLUMN T0038.housing_allowance IS 'Housing allowance for this period';
COMMENT ON COLUMN T0038.transport_allowance IS 'Transport allowance for this period';
COMMENT ON COLUMN T0038.other_allowances IS 'Other allowances for this period';
COMMENT ON COLUMN T0038.overtime IS 'Overtime pay for this period';
COMMENT ON COLUMN T0038.deductions IS 'Total deductions for this period';
COMMENT ON COLUMN T0038.tax IS 'Tax withheld for this period';
COMMENT ON COLUMN T0038.gross_pay IS 'Gross pay before deductions and tax';
COMMENT ON COLUMN T0038.net_pay IS 'Net pay after all deductions and tax';
COMMENT ON COLUMN T0038.status IS 'Entry status (Draft, Approved, Paid)';
COMMENT ON COLUMN T0038.payment_date IS 'Date payment was made';
COMMENT ON COLUMN T0038.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0038.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0038.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0038.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0038.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0038.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0038.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0038_period ON T0038(payroll_period_id);

-- ============================================================
-- HR MANAGEMENT: Recruitment
-- ============================================================

-- T0039 - Job Openings
COMMENT ON TABLE T0039 IS 'HR — Job vacancy / requisition postings';
CREATE TABLE T0039 (
    id              SERIAL PRIMARY KEY,
    job_code        VARCHAR(30) NOT NULL UNIQUE,
    job_title       VARCHAR(200) NOT NULL,
    department_id   INT REFERENCES T0028(id),
    designation_id  INT REFERENCES T0029(id),
    openings        SMALLINT DEFAULT 1,
    description     TEXT,
    requirements    TEXT,
    status          VARCHAR(30) DEFAULT 'Draft',
    posted_date     DATE,
    closing_date    DATE,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0039.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0039.job_code IS 'Unique job opening code (e.g. REQ-2026-001)';
COMMENT ON COLUMN T0039.job_title IS 'Title of the position being recruited';
COMMENT ON COLUMN T0039.department_id IS 'Department hiring for this position (FK to T0028)';
COMMENT ON COLUMN T0039.designation_id IS 'Designation for this position (FK to T0029)';
COMMENT ON COLUMN T0039.openings IS 'Number of vacant positions';
COMMENT ON COLUMN T0039.description IS 'Job description details';
COMMENT ON COLUMN T0039.requirements IS 'Job requirements and qualifications';
COMMENT ON COLUMN T0039.status IS 'Opening status (Draft, Published, Closed, Cancelled)';
COMMENT ON COLUMN T0039.posted_date IS 'Date the opening was published';
COMMENT ON COLUMN T0039.closing_date IS 'Application closing date';
COMMENT ON COLUMN T0039.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0039.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0039.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0039.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0039.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0039.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0039_status ON T0039(status);

-- T0040 - Candidates
COMMENT ON TABLE T0040 IS 'HR — Job applicants / candidates';
CREATE TABLE T0040 (
    id              SERIAL PRIMARY KEY,
    candidate_code  VARCHAR(30) NOT NULL UNIQUE,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    phone           VARCHAR(30),
    job_opening_id  INT REFERENCES T0039(id),
    status          VARCHAR(30) DEFAULT 'Applied',
    resume_path     VARCHAR(500),
    notes           TEXT,
    applied_date    DATE DEFAULT CURRENT_DATE,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0040.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0040.candidate_code IS 'Unique candidate code (e.g. CAND-001)';
COMMENT ON COLUMN T0040.full_name IS 'Candidate full name';
COMMENT ON COLUMN T0040.email IS 'Candidate email address';
COMMENT ON COLUMN T0040.phone IS 'Candidate phone number';
COMMENT ON COLUMN T0040.job_opening_id IS 'Job opening the candidate applied for (FK to T0039)';
COMMENT ON COLUMN T0040.status IS 'Application status (Applied, Screened, Interviewed, Offered, Hired, Rejected)';
COMMENT ON COLUMN T0040.resume_path IS 'File path to uploaded resume/CV';
COMMENT ON COLUMN T0040.notes IS 'Recruiter notes and comments';
COMMENT ON COLUMN T0040.applied_date IS 'Date the candidate applied';
COMMENT ON COLUMN T0040.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0040.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0040.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0040.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0040.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0040.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0040_job ON T0040(job_opening_id);
CREATE INDEX idx_T0040_status ON T0040(status);

-- ============================================================
-- MAINTENANCE MANAGEMENT
-- ============================================================

-- T0041 - Assets / Equipment
COMMENT ON TABLE T0041 IS 'MNT — Physical assets and equipment register';
CREATE TABLE T0041 (
    id              SERIAL PRIMARY KEY,
    asset_code      VARCHAR(30) NOT NULL UNIQUE,
    asset_name      VARCHAR(200) NOT NULL,
    asset_type      VARCHAR(100),
    asset_model     VARCHAR(100),
    serial_no       VARCHAR(100),
    location        VARCHAR(200),
    department_id   INT REFERENCES T0028(id),
    purchase_date   DATE,
    purchase_cost   NUMERIC(12,2) DEFAULT 0,
    useful_life     SMALLINT,
    warranty_expiry DATE,
    status          VARCHAR(30) DEFAULT 'Operational',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0041.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0041.asset_code IS 'Unique asset identification code';
COMMENT ON COLUMN T0041.asset_name IS 'Asset display name';
COMMENT ON COLUMN T0041.asset_type IS 'Asset category (e.g. Vehicle, Machinery, Furniture)';
COMMENT ON COLUMN T0041.asset_model IS 'Manufacturer model number';
COMMENT ON COLUMN T0041.serial_no IS 'Manufacturer serial number';
COMMENT ON COLUMN T0041.location IS 'Physical location of the asset';
COMMENT ON COLUMN T0041.department_id IS 'Department responsible for the asset (FK to T0028)';
COMMENT ON COLUMN T0041.purchase_date IS 'Date the asset was purchased';
COMMENT ON COLUMN T0041.purchase_cost IS 'Purchase cost of the asset';
COMMENT ON COLUMN T0041.useful_life IS 'Estimated useful life in years';
COMMENT ON COLUMN T0041.warranty_expiry IS 'Warranty expiration date';
COMMENT ON COLUMN T0041.status IS 'Asset status (Operational, Under Maintenance, Retired)';
COMMENT ON COLUMN T0041.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0041.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0041.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0041.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0041.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0041.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0041_type ON T0041(asset_type);
CREATE INDEX idx_T0041_status ON T0041(status);

-- T0042 - Maintenance Schedules
COMMENT ON TABLE T0042 IS 'MNT — Preventive maintenance schedules';
CREATE TABLE T0042 (
    id                  SERIAL PRIMARY KEY,
    asset_id            INT NOT NULL REFERENCES T0041(id),
    schedule_code       VARCHAR(30) NOT NULL UNIQUE,
    schedule_name       VARCHAR(200),
    frequency_type      VARCHAR(20) DEFAULT 'Monthly',
    frequency_value     SMALLINT DEFAULT 1,
    last_maintenance    DATE,
    next_maintenance    DATE,
    assigned_to         INT REFERENCES T0021(id),
    notes               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT REFERENCES T0021(id),
    update_number       INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0042.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0042.asset_id IS 'Asset under maintenance (FK to T0041)';
COMMENT ON COLUMN T0042.schedule_code IS 'Unique maintenance schedule code';
COMMENT ON COLUMN T0042.schedule_name IS 'Schedule description / name';
COMMENT ON COLUMN T0042.frequency_type IS 'Frequency unit (Daily, Weekly, Monthly, Yearly)';
COMMENT ON COLUMN T0042.frequency_value IS 'Number of frequency units between maintenance events';
COMMENT ON COLUMN T0042.last_maintenance IS 'Date of last performed maintenance';
COMMENT ON COLUMN T0042.next_maintenance IS 'Scheduled date for next maintenance';
COMMENT ON COLUMN T0042.assigned_to IS 'Technician responsible for this schedule (FK to T0021)';
COMMENT ON COLUMN T0042.notes IS 'Free-text notes or instructions';
COMMENT ON COLUMN T0042.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0042.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0042.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0042.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0042.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0042.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0042_asset ON T0042(asset_id);

-- T0043 - Maintenance Work Orders
COMMENT ON TABLE T0043 IS 'MNT — Maintenance work order execution';
CREATE TABLE T0043 (
    id              SERIAL PRIMARY KEY,
    asset_id        INT NOT NULL REFERENCES T0041(id),
    schedule_id     INT REFERENCES T0042(id),
    work_order_code VARCHAR(30) NOT NULL UNIQUE,
    description     TEXT,
    priority        VARCHAR(20) DEFAULT 'Medium',
    status          VARCHAR(30) DEFAULT 'Open',
    assigned_to     INT REFERENCES T0021(id),
    scheduled_date  DATE,
    completed_date  DATE,
    cost            NUMERIC(12,2) DEFAULT 0,
    notes           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0043.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0043.asset_id IS 'Asset being maintained (FK to T0041)';
COMMENT ON COLUMN T0043.schedule_id IS 'Preventive schedule this work order originates from (FK to T0042)';
COMMENT ON COLUMN T0043.work_order_code IS 'Unique work order reference code';
COMMENT ON COLUMN T0043.description IS 'Description of work to be performed';
COMMENT ON COLUMN T0043.priority IS 'Priority level (Low, Medium, High, Critical)';
COMMENT ON COLUMN T0043.status IS 'Work order status (Open, In Progress, Completed, Cancelled)';
COMMENT ON COLUMN T0043.assigned_to IS 'Technician assigned to this work order (FK to T0021)';
COMMENT ON COLUMN T0043.scheduled_date IS 'Scheduled date for the work';
COMMENT ON COLUMN T0043.completed_date IS 'Actual completion date';
COMMENT ON COLUMN T0043.cost IS 'Total cost of the maintenance work';
COMMENT ON COLUMN T0043.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0043.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0043.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0043.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0043.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0043.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0043.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0043_asset ON T0043(asset_id);
CREATE INDEX idx_T0043_status ON T0043(status);

-- ============================================================
-- PROJECTS & SERVICES
-- ============================================================

-- T0044 - Projects
COMMENT ON TABLE T0044 IS 'PJM — Project master records';
CREATE TABLE T0044 (
    id              SERIAL PRIMARY KEY,
    project_code    VARCHAR(30) NOT NULL UNIQUE,
    project_name    VARCHAR(200) NOT NULL,
    description     TEXT,
    department_id   INT REFERENCES T0028(id),
    manager_id      INT REFERENCES T0030(id),
    start_date      DATE,
    end_date        DATE,
    budget          NUMERIC(12,2) DEFAULT 0,
    status          VARCHAR(30) DEFAULT 'Draft',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0044.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0044.project_code IS 'Unique project code (e.g. PRJ-001)';
COMMENT ON COLUMN T0044.project_name IS 'Project display name';
COMMENT ON COLUMN T0044.description IS 'Project description and objectives';
COMMENT ON COLUMN T0044.department_id IS 'Owning department (FK to T0028)';
COMMENT ON COLUMN T0044.manager_id IS 'Project manager (FK to T0030)';
COMMENT ON COLUMN T0044.start_date IS 'Project start date';
COMMENT ON COLUMN T0044.end_date IS 'Project end date';
COMMENT ON COLUMN T0044.budget IS 'Project budget amount';
COMMENT ON COLUMN T0044.status IS 'Project status (Draft, Active, On Hold, Completed, Cancelled)';
COMMENT ON COLUMN T0044.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0044.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0044.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0044.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0044.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0044.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0044_status ON T0044(status);

-- T0045 - Project Tasks
COMMENT ON TABLE T0045 IS 'PJM — Tasks within a project';
CREATE TABLE T0045 (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES T0044(id),
    task_code       VARCHAR(30) NOT NULL,
    task_name       VARCHAR(200) NOT NULL,
    description     TEXT,
    assigned_to     INT REFERENCES T0030(id),
    start_date      DATE,
    end_date        DATE,
    priority        VARCHAR(20) DEFAULT 'Medium',
    status          VARCHAR(30) DEFAULT 'Pending',
    estimated_hours NUMERIC(8,2),
    actual_hours    NUMERIC(8,2) DEFAULT 0,
    parent_task_id  INT REFERENCES T0045(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1,
    UNIQUE (project_id, task_code)
);
COMMENT ON COLUMN T0045.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0045.project_id IS 'Parent project (FK to T0044)';
COMMENT ON COLUMN T0045.task_code IS 'Task code unique within the project';
COMMENT ON COLUMN T0045.task_name IS 'Task display name';
COMMENT ON COLUMN T0045.description IS 'Task description and details';
COMMENT ON COLUMN T0045.assigned_to IS 'Employee assigned to this task (FK to T0030)';
COMMENT ON COLUMN T0045.start_date IS 'Task start date';
COMMENT ON COLUMN T0045.end_date IS 'Task end date';
COMMENT ON COLUMN T0045.priority IS 'Priority level (Low, Medium, High, Critical)';
COMMENT ON COLUMN T0045.status IS 'Task status (Pending, In Progress, Completed, On Hold)';
COMMENT ON COLUMN T0045.estimated_hours IS 'Estimated effort in hours';
COMMENT ON COLUMN T0045.actual_hours IS 'Actual hours logged against this task';
COMMENT ON COLUMN T0045.parent_task_id IS 'Parent task for sub-task hierarchy (FK to self)';
COMMENT ON COLUMN T0045.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0045.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0045.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0045.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0045.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0045.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0045_project ON T0045(project_id);
CREATE INDEX idx_T0045_assigned ON T0045(assigned_to);

-- T0046 - Resource Allocations
COMMENT ON TABLE T0046 IS 'PJM — Employee resource allocation to projects';
CREATE TABLE T0046 (
    id                  SERIAL PRIMARY KEY,
    project_id          INT NOT NULL REFERENCES T0044(id),
    employee_id         INT NOT NULL REFERENCES T0030(id),
    allocation_pct      NUMERIC(5,2) DEFAULT 100,
    start_date          DATE,
    end_date            DATE,
    role                VARCHAR(100),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          INT REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          INT REFERENCES T0021(id),
    update_number       INT NOT NULL DEFAULT 1,
    UNIQUE (project_id, employee_id, start_date)
);
COMMENT ON COLUMN T0046.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0046.project_id IS 'Project being allocated to (FK to T0044)';
COMMENT ON COLUMN T0046.employee_id IS 'Employee being allocated (FK to T0030)';
COMMENT ON COLUMN T0046.allocation_pct IS 'Allocation percentage of employee time';
COMMENT ON COLUMN T0046.start_date IS 'Allocation start date';
COMMENT ON COLUMN T0046.end_date IS 'Allocation end date';
COMMENT ON COLUMN T0046.role IS 'Role on the project (Developer, Tester, Manager)';
COMMENT ON COLUMN T0046.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0046.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0046.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0046.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0046.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0046.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0046_project ON T0046(project_id);

-- T0047 - Timesheets
COMMENT ON TABLE T0047 IS 'PJM — Employee time tracking against tasks';
CREATE TABLE T0047 (
    id              SERIAL PRIMARY KEY,
    employee_id     INT NOT NULL REFERENCES T0030(id),
    project_id      INT REFERENCES T0044(id),
    task_id         INT REFERENCES T0045(id),
    date            DATE NOT NULL,
    hours           NUMERIC(6,2) NOT NULL,
    description     TEXT,
    status          VARCHAR(30) DEFAULT 'Submitted',
    approved_by     INT REFERENCES T0021(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0047.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0047.employee_id IS 'Employee logging time (FK to T0030)';
COMMENT ON COLUMN T0047.project_id IS 'Project the time is logged against (FK to T0044)';
COMMENT ON COLUMN T0047.task_id IS 'Task the time is logged against (FK to T0045)';
COMMENT ON COLUMN T0047.date IS 'Date the work was performed';
COMMENT ON COLUMN T0047.hours IS 'Hours worked';
COMMENT ON COLUMN T0047.description IS 'Description of work performed';
COMMENT ON COLUMN T0047.status IS 'Timesheet status (Submitted, Approved, Rejected)';
COMMENT ON COLUMN T0047.approved_by IS 'User who approved this timesheet entry (FK to T0021)';
COMMENT ON COLUMN T0047.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0047.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0047.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0047.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0047.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0047.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0047_employee ON T0047(employee_id);
CREATE INDEX idx_T0047_date ON T0047(date);

-- T0048 - Service Requests
COMMENT ON TABLE T0048 IS 'SRV — Customer / internal service requests';
CREATE TABLE T0048 (
    id              SERIAL PRIMARY KEY,
    request_code    VARCHAR(30) NOT NULL UNIQUE,
    customer_id     INT REFERENCES T0010(id),
    subject         VARCHAR(200) NOT NULL,
    description     TEXT,
    priority        VARCHAR(20) DEFAULT 'Medium',
    status          VARCHAR(30) DEFAULT 'Open',
    assigned_to     INT REFERENCES T0030(id),
    resolution      TEXT,
    resolved_date   DATE,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0048.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0048.request_code IS 'Unique service request code (e.g. SR-001)';
COMMENT ON COLUMN T0048.customer_id IS 'Customer making the request (FK to T0010)';
COMMENT ON COLUMN T0048.subject IS 'Request subject / title';
COMMENT ON COLUMN T0048.description IS 'Detailed description of the request';
COMMENT ON COLUMN T0048.priority IS 'Priority level (Low, Medium, High, Critical)';
COMMENT ON COLUMN T0048.status IS 'Request status (Open, In Progress, Resolved, Closed)';
COMMENT ON COLUMN T0048.assigned_to IS 'Employee assigned to handle this request (FK to T0030)';
COMMENT ON COLUMN T0048.resolution IS 'Resolution notes';
COMMENT ON COLUMN T0048.resolved_date IS 'Date the request was resolved';
COMMENT ON COLUMN T0048.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0048.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0048.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0048.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0048.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0048.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0048_status ON T0048(status);
CREATE INDEX idx_T0048_customer ON T0048(customer_id);

-- T0049 - Contracts / SLAs
COMMENT ON TABLE T0049 IS 'SRV — Customer contracts and Service Level Agreements';
CREATE TABLE T0049 (
    id              SERIAL PRIMARY KEY,
    contract_code   VARCHAR(30) NOT NULL UNIQUE,
    contract_name   VARCHAR(200) NOT NULL,
    customer_id     INT REFERENCES T0010(id),
    contract_type   VARCHAR(50),
    start_date      DATE NOT NULL,
    end_date        DATE,
    value           NUMERIC(12,2) DEFAULT 0,
    status          VARCHAR(30) DEFAULT 'Active',
    notes           TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0049.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0049.contract_code IS 'Unique contract code (e.g. CTR-001)';
COMMENT ON COLUMN T0049.contract_name IS 'Contract display name';
COMMENT ON COLUMN T0049.customer_id IS 'Customer under contract (FK to T0010)';
COMMENT ON COLUMN T0049.contract_type IS 'Contract type (Service, Maintenance, Lease)';
COMMENT ON COLUMN T0049.start_date IS 'Contract start date';
COMMENT ON COLUMN T0049.end_date IS 'Contract end date (NULL = ongoing)';
COMMENT ON COLUMN T0049.value IS 'Total contract value';
COMMENT ON COLUMN T0049.status IS 'Contract status (Active, Expired, Terminated, Draft)';
COMMENT ON COLUMN T0049.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0049.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0049.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0049.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0049.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0049.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0049.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0049_customer ON T0049(customer_id);
CREATE INDEX idx_T0049_status ON T0049(status);

-- T0050 - SLA Definitions
COMMENT ON TABLE T0050 IS 'SRV — SLA metrics and targets per contract';
CREATE TABLE T0050 (
    id              SERIAL PRIMARY KEY,
    contract_id     INT NOT NULL REFERENCES T0049(id),
    sla_code        VARCHAR(30) NOT NULL,
    sla_name        VARCHAR(200) NOT NULL,
    response_time   INTERVAL DEFAULT '4 hours',
    resolution_time INTERVAL DEFAULT '24 hours',
    penalty_rate    NUMERIC(10,2) DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1,
    UNIQUE (contract_id, sla_code)
);
COMMENT ON COLUMN T0050.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0050.contract_id IS 'Contract this SLA belongs to (FK to T0049)';
COMMENT ON COLUMN T0050.sla_code IS 'SLA code unique within the contract';
COMMENT ON COLUMN T0050.sla_name IS 'SLA metric display name';
COMMENT ON COLUMN T0050.response_time IS 'Target response time interval';
COMMENT ON COLUMN T0050.resolution_time IS 'Target resolution time interval';
COMMENT ON COLUMN T0050.penalty_rate IS 'Penalty rate for SLA breach';
COMMENT ON COLUMN T0050.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0050.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0050.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0050.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0050.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0050.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0050_contract ON T0050(contract_id);

-- ============================================================
-- SEARCH FRAMEWORK
-- ============================================================

-- T0051 - Search Index
COMMENT ON TABLE T0051 IS 'SYS — Full-text search index across entities';
CREATE TABLE T0051 (
    id              SERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       INT NOT NULL,
    keywords        TEXT,
    search_content  TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0051.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0051.entity_type IS 'Type of entity being indexed (e.g. product, customer, employee)';
COMMENT ON COLUMN T0051.entity_id IS 'Primary key of the indexed entity';
COMMENT ON COLUMN T0051.keywords IS 'Searchable keywords extracted from the entity';
COMMENT ON COLUMN T0051.search_content IS 'Full-text search content blob';
COMMENT ON COLUMN T0051.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0051.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0051.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0051.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0051_entity ON T0051(entity_type, entity_id);

-- ============================================================
-- BI & ANALYTICS
-- ============================================================

-- T0052 - KPI Definitions
COMMENT ON TABLE T0052 IS 'BI — Key Performance Indicator definitions';
CREATE TABLE T0052 (
    id              SERIAL PRIMARY KEY,
    kpi_code        VARCHAR(30) NOT NULL UNIQUE,
    kpi_name        VARCHAR(200) NOT NULL,
    category        VARCHAR(100),
    metric_unit     VARCHAR(50),
    target_value    NUMERIC(14,4),
    formula         TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0052.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0052.kpi_code IS 'Unique KPI code';
COMMENT ON COLUMN T0052.kpi_name IS 'KPI display name';
COMMENT ON COLUMN T0052.category IS 'KPI category for grouping';
COMMENT ON COLUMN T0052.metric_unit IS 'Unit of measurement (%, $, count, etc.)';
COMMENT ON COLUMN T0052.target_value IS 'Target value for this KPI';
COMMENT ON COLUMN T0052.formula IS 'KPI calculation formula or description';
COMMENT ON COLUMN T0052.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0052.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0052.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0052.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0052.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0052.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0053 - KPI Values
COMMENT ON TABLE T0053 IS 'BI — Recorded KPI measurements over time';
CREATE TABLE T0053 (
    id              SERIAL PRIMARY KEY,
    kpi_id          INT NOT NULL REFERENCES T0052(id),
    period          DATE NOT NULL,
    period_type     VARCHAR(20) DEFAULT 'Daily',
    actual_value    NUMERIC(14,4),
    target_value    NUMERIC(14,4),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1,
    UNIQUE (kpi_id, period, period_type)
);
COMMENT ON COLUMN T0053.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0053.kpi_id IS 'KPI definition (FK to T0052)';
COMMENT ON COLUMN T0053.period IS 'Date of the measurement period';
COMMENT ON COLUMN T0053.period_type IS 'Period granularity (Daily, Weekly, Monthly, Quarterly, Yearly)';
COMMENT ON COLUMN T0053.actual_value IS 'Actual measured value for the period';
COMMENT ON COLUMN T0053.target_value IS 'Target value for the period (overrides definition if set)';
COMMENT ON COLUMN T0053.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0053.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0053.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0053.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0053.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0053.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0053_kpi ON T0053(kpi_id);

-- T0054 - BI Dashboards
COMMENT ON TABLE T0054 IS 'BI — Dashboard configuration and layouts';
CREATE TABLE T0054 (
    id              SERIAL PRIMARY KEY,
    dashboard_code  VARCHAR(30) NOT NULL UNIQUE,
    dashboard_name  VARCHAR(200) NOT NULL,
    owner_id        INT REFERENCES T0021(id),
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0054.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0054.dashboard_code IS 'Unique dashboard code';
COMMENT ON COLUMN T0054.dashboard_name IS 'Dashboard display name';
COMMENT ON COLUMN T0054.owner_id IS 'Dashboard owner (FK to T0021)';
COMMENT ON COLUMN T0054.config IS 'Dashboard layout and configuration in JSONB';
COMMENT ON COLUMN T0054.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0054.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0054.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0054.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0054.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0054.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0055 - Dashboard Widgets
COMMENT ON TABLE T0055 IS 'BI — Individual widgets within a dashboard';
CREATE TABLE T0055 (
    id              SERIAL PRIMARY KEY,
    dashboard_id    INT NOT NULL REFERENCES T0054(id),
    widget_type     VARCHAR(50) NOT NULL,
    title           VARCHAR(200),
    config          JSONB,
    position        JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0055.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0055.dashboard_id IS 'Parent dashboard (FK to T0054)';
COMMENT ON COLUMN T0055.widget_type IS 'Widget type (Chart, Table, Metric, KPI)';
COMMENT ON COLUMN T0055.title IS 'Widget display title';
COMMENT ON COLUMN T0055.config IS 'Widget configuration (data source, options) in JSONB';
COMMENT ON COLUMN T0055.position IS 'Widget position and layout in JSONB';
COMMENT ON COLUMN T0055.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0055.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0055.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0055.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0055.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0055.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0055_dashboard ON T0055(dashboard_id);

-- ============================================================
-- MOBILE & INTEGRATIONS
-- ============================================================

-- T0056 - API Keys
COMMENT ON TABLE T0056 IS 'INT — API key management for integrations';
CREATE TABLE T0056 (
    id              SERIAL PRIMARY KEY,
    key_name        VARCHAR(100) NOT NULL,
    api_key         VARCHAR(255) NOT NULL UNIQUE,
    client_id       VARCHAR(100),
    permissions     TEXT[] DEFAULT '{}',
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0056.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0056.key_name IS 'Human-readable name for this API key';
COMMENT ON COLUMN T0056.api_key IS 'The API key value (hashed or raw)';
COMMENT ON COLUMN T0056.client_id IS 'Client identifier associated with this key';
COMMENT ON COLUMN T0056.permissions IS 'Array of permission scopes granted to this key';
COMMENT ON COLUMN T0056.expires_at IS 'Key expiration timestamp (NULL = never expires)';
COMMENT ON COLUMN T0056.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0056.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0056.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0056.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0056.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0056.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0057 - Integration Configurations
COMMENT ON TABLE T0057 IS 'INT — Third-party integration settings';
CREATE TABLE T0057 (
    id                SERIAL PRIMARY KEY,
    integration_code  VARCHAR(50) NOT NULL UNIQUE,
    integration_name  VARCHAR(200) NOT NULL,
    provider          VARCHAR(100),
    config            JSONB,
    credentials       JSONB,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        INT REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by        INT REFERENCES T0021(id),
    update_number     INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0057.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0057.integration_code IS 'Unique integration code';
COMMENT ON COLUMN T0057.integration_name IS 'Integration display name';
COMMENT ON COLUMN T0057.provider IS 'Third-party provider name (e.g. Stripe, Twilio)';
COMMENT ON COLUMN T0057.config IS 'Integration configuration options in JSONB';
COMMENT ON COLUMN T0057.credentials IS 'Encrypted credentials in JSONB';
COMMENT ON COLUMN T0057.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0057.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0057.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0057.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0057.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0057.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0058 - Sync Logs
COMMENT ON TABLE T0058 IS 'INT — Integration sync activity logs';
CREATE TABLE T0058 (
    id              SERIAL PRIMARY KEY,
    integration_id  INT REFERENCES T0057(id),
    entity_type     VARCHAR(50),
    action          VARCHAR(50),
    status          VARCHAR(30),
    message         TEXT,
    synced_at       TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0058.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0058.integration_id IS 'Integration that performed the sync (FK to T0057)';
COMMENT ON COLUMN T0058.entity_type IS 'Type of entity being synced';
COMMENT ON COLUMN T0058.action IS 'Sync action performed (Create, Update, Delete)';
COMMENT ON COLUMN T0058.status IS 'Sync status (Success, Failed, In Progress)';
COMMENT ON COLUMN T0058.message IS 'Detailed log message or error description';
COMMENT ON COLUMN T0058.synced_at IS 'Timestamp of the sync event';
COMMENT ON COLUMN T0058.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0058.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0058_integration ON T0058(integration_id);
CREATE INDEX idx_T0058_status ON T0058(status);

-- ============================================================
-- ENTERPRISE EXPANSION
-- ============================================================

-- T0059 - Tenants
COMMENT ON TABLE T0059 IS 'ENT — Multi-tenant configuration';
CREATE TABLE T0059 (
    id              SERIAL PRIMARY KEY,
    tenant_code     VARCHAR(30) NOT NULL UNIQUE,
    tenant_name     VARCHAR(200) NOT NULL,
    domain          VARCHAR(200),
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0059.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0059.tenant_code IS 'Unique tenant code';
COMMENT ON COLUMN T0059.tenant_name IS 'Tenant display name';
COMMENT ON COLUMN T0059.domain IS 'Tenant domain for routing';
COMMENT ON COLUMN T0059.config IS 'Tenant-specific configuration in JSONB';
COMMENT ON COLUMN T0059.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0059.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0059.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0059.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0059.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0059.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0060 - Workflow Definitions
COMMENT ON TABLE T0060 IS 'ENT — Configurable workflow / approval process definitions';
CREATE TABLE T0060 (
    id              SERIAL PRIMARY KEY,
    workflow_code   VARCHAR(30) NOT NULL UNIQUE,
    workflow_name   VARCHAR(200) NOT NULL,
    entity_type     VARCHAR(50),
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0060.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0060.workflow_code IS 'Unique workflow code';
COMMENT ON COLUMN T0060.workflow_name IS 'Workflow display name';
COMMENT ON COLUMN T0060.entity_type IS 'Entity type this workflow applies to';
COMMENT ON COLUMN T0060.config IS 'Workflow step definitions in JSONB';
COMMENT ON COLUMN T0060.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0060.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0060.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0060.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0060.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0060.update_number IS 'Version counter incremented on each update, starts at 1';

-- T0061 - Workflow Instances
COMMENT ON TABLE T0061 IS 'ENT — Active and completed workflow runs';
CREATE TABLE T0061 (
    id              SERIAL PRIMARY KEY,
    workflow_id     INT NOT NULL REFERENCES T0060(id),
    entity_type     VARCHAR(50),
    entity_id       INT,
    status          VARCHAR(30) DEFAULT 'Active',
    current_step    VARCHAR(100),
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0061.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0061.workflow_id IS 'Workflow definition being executed (FK to T0060)';
COMMENT ON COLUMN T0061.entity_type IS 'Entity type this instance is running for';
COMMENT ON COLUMN T0061.entity_id IS 'Primary key of the entity being processed';
COMMENT ON COLUMN T0061.status IS 'Instance status (Active, Completed, Rejected, Cancelled)';
COMMENT ON COLUMN T0061.current_step IS 'Identifier of the current workflow step';
COMMENT ON COLUMN T0061.config IS 'Runtime instance data in JSONB';
COMMENT ON COLUMN T0061.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0061.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0061.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0061.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0061.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0061.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0061_workflow ON T0061(workflow_id);
CREATE INDEX idx_T0061_status ON T0061(status);

-- T0062 - Document Management
COMMENT ON TABLE T0062 IS 'ENT — Document / file storage metadata';
CREATE TABLE T0062 (
    id              SERIAL PRIMARY KEY,
    document_code   VARCHAR(30) NOT NULL UNIQUE,
    document_name   VARCHAR(200) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       INT,
    file_path       VARCHAR(500),
    file_type       VARCHAR(50),
    file_size       INT,
    version         SMALLINT DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0062.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0062.document_code IS 'Unique document code';
COMMENT ON COLUMN T0062.document_name IS 'Document display name / filename';
COMMENT ON COLUMN T0062.entity_type IS 'Entity type this document is attached to';
COMMENT ON COLUMN T0062.entity_id IS 'Primary key of the attached entity';
COMMENT ON COLUMN T0062.file_path IS 'File system or blob storage path';
COMMENT ON COLUMN T0062.file_type IS 'MIME type or file extension';
COMMENT ON COLUMN T0062.file_size IS 'File size in bytes';
COMMENT ON COLUMN T0062.version IS 'Document version number, starts at 1';
COMMENT ON COLUMN T0062.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0062.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0062.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0062.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0062.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0062.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0062_entity ON T0062(entity_type, entity_id);

-- T0063 - Compliance Rules
COMMENT ON TABLE T0063 IS 'ENT — Compliance and governance rule definitions';
CREATE TABLE T0063 (
    id              SERIAL PRIMARY KEY,
    rule_code       VARCHAR(30) NOT NULL UNIQUE,
    rule_name       VARCHAR(200) NOT NULL,
    category        VARCHAR(100),
    description     TEXT,
    config          JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0063.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0063.rule_code IS 'Unique compliance rule code';
COMMENT ON COLUMN T0063.rule_name IS 'Rule display name';
COMMENT ON COLUMN T0063.category IS 'Rule category (Regulatory, Internal, Audit)';
COMMENT ON COLUMN T0063.description IS 'Rule description and purpose';
COMMENT ON COLUMN T0063.config IS 'Rule configuration and parameters in JSONB';
COMMENT ON COLUMN T0063.is_active IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0063.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0063.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0063.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0063.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0063.update_number IS 'Version counter incremented on each update, starts at 1';

-- ============================================================
-- INVENTORY: Stock Movement Ledger
-- ============================================================

COMMENT ON TABLE T0064 IS 'INV — Immutable stock movement audit trail';
CREATE TABLE T0064 (
    id              SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES T0003(id),
    warehouse_id    INT NOT NULL REFERENCES T0008(id),
    movement_type   VARCHAR(30) NOT NULL,
    reference_type  VARCHAR(30),
    reference_id    INT,
    qty_change      NUMERIC(12,2) NOT NULL,
    balance_after   NUMERIC(12,2) NOT NULL,
    description     TEXT,
    movement_date   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN T0064.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0064.product_id IS 'Product being moved (FK to T0003)';
COMMENT ON COLUMN T0064.warehouse_id IS 'Warehouse location (FK to T0008)';
COMMENT ON COLUMN T0064.movement_type IS 'Category of movement: Sale, Purchase, Transfer, Adjustment, Manufacturing, Return';
COMMENT ON COLUMN T0064.reference_type IS 'Source document type (SalesOrder, PurchaseOrder, MfgOrder)';
COMMENT ON COLUMN T0064.reference_id IS 'Primary key of the source document';
COMMENT ON COLUMN T0064.qty_change IS 'Quantity change: positive for stock in, negative for stock out';
COMMENT ON COLUMN T0064.balance_after IS 'Running balance in the warehouse after this movement';
COMMENT ON COLUMN T0064.description IS 'Free-text description or reason';
COMMENT ON COLUMN T0064.movement_date IS 'Timestamp when the movement occurred';
COMMENT ON COLUMN T0064.created_by IS 'User who triggered the movement (FK to T0021)';
COMMENT ON COLUMN T0064.created_at IS 'Record creation timestamp';
CREATE INDEX idx_T0064_product ON T0064(product_id);
CREATE INDEX idx_T0064_warehouse ON T0064(warehouse_id);
CREATE INDEX idx_T0064_date ON T0064(movement_date);
CREATE INDEX idx_T0064_reference ON T0064(reference_type, reference_id);

-- ============================================================
-- MANUFACTURING: Bill of Materials
-- ============================================================

COMMENT ON TABLE T0065 IS 'MFG — Bill of Materials header';
CREATE TABLE T0065 (
    id              SERIAL PRIMARY KEY,
    bom_code        VARCHAR(30) NOT NULL UNIQUE,
    bom_name        VARCHAR(200) NOT NULL,
    product_id      INT NOT NULL REFERENCES T0003(id),
    quantity        NUMERIC(12,2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
    version         SMALLINT DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0065.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0065.bom_code IS 'Unique BOM reference code';
COMMENT ON COLUMN T0065.bom_name IS 'BOM display name';
COMMENT ON COLUMN T0065.product_id IS 'Finished product this BOM produces (FK to T0003)';
COMMENT ON COLUMN T0065.quantity IS 'Quantity of finished product this BOM produces';
COMMENT ON COLUMN T0065.version IS 'BOM version for revision control';
COMMENT ON COLUMN T0065.is_active IS 'Soft delete flag';
COMMENT ON COLUMN T0065.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0065.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0065.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0065.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0065.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0065_product ON T0065(product_id);

COMMENT ON TABLE T0066 IS 'MFG — Bill of Materials component lines';
CREATE TABLE T0066 (
    id              SERIAL PRIMARY KEY,
    bom_id          INT NOT NULL REFERENCES T0065(id) ON DELETE CASCADE,
    component_id    INT NOT NULL REFERENCES T0003(id),
    component_name  VARCHAR(200) NOT NULL,
    quantity        NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    uom_id          INT REFERENCES T0001(id),
    scrap_pct       NUMERIC(5,2) DEFAULT 0 CHECK (scrap_pct >= 0),
    line_number     SMALLINT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0066.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0066.bom_id IS 'Parent BOM (FK to T0065)';
COMMENT ON COLUMN T0066.component_id IS 'Component/product used as raw material (FK to T0003)';
COMMENT ON COLUMN T0066.component_name IS 'Denormalized component name';
COMMENT ON COLUMN T0066.quantity IS 'Quantity of component required';
COMMENT ON COLUMN T0066.uom_id IS 'Unit of measure for the component (FK to T0001)';
COMMENT ON COLUMN T0066.scrap_pct IS 'Expected scrap/waste percentage';
COMMENT ON COLUMN T0066.line_number IS 'Line sequence number';
COMMENT ON COLUMN T0066.is_active IS 'Soft delete flag';
COMMENT ON COLUMN T0066.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0066.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0066.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0066.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0066.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0066_bom ON T0066(bom_id);
CREATE INDEX idx_T0066_component ON T0066(component_id);

-- ============================================================
-- TRANSACTIONS: Sales Quotations
-- ============================================================

-- T0067 - Sales Quotations (header)
COMMENT ON TABLE T0067 IS 'SAL — Sales quotation / proposal header';
CREATE TABLE T0067 (
    id              SERIAL PRIMARY KEY,
    quote_number    VARCHAR(30) NOT NULL UNIQUE,
    customer_id     INT NOT NULL REFERENCES T0010(id),
    quote_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until     DATE,
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax             NUMERIC(12,2) NOT NULL DEFAULT 0,
    grand_total     NUMERIC(12,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes           TEXT,
    converted_order_id INT REFERENCES T0012(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0067.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0067.quote_number IS 'Human-readable quote reference (e.g. QTE-001)';
COMMENT ON COLUMN T0067.customer_id IS 'Customer receiving the quote (FK to T0010)';
COMMENT ON COLUMN T0067.quote_date IS 'Date the quote was created';
COMMENT ON COLUMN T0067.valid_until IS 'Date until which the quote is valid';
COMMENT ON COLUMN T0067.subtotal IS 'Sum of line totals before tax';
COMMENT ON COLUMN T0067.tax IS 'Total tax amount';
COMMENT ON COLUMN T0067.grand_total IS 'Final amount including tax';
COMMENT ON COLUMN T0067.status IS 'Quote status: Draft, Sent, Accepted, Rejected, Converted';
COMMENT ON COLUMN T0067.notes IS 'Free-text notes';
COMMENT ON COLUMN T0067.converted_order_id IS 'Sales order created from this quote (FK to T0012)';
COMMENT ON COLUMN T0067.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0067.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0067.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0067.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0067.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0067_customer ON T0067(customer_id);
CREATE INDEX idx_T0067_status ON T0067(status);

-- T0068 - Sales Quotation Lines
COMMENT ON TABLE T0068 IS 'SAL — Individual line items on a sales quotation';
CREATE TABLE T0068 (
    id              SERIAL PRIMARY KEY,
    quotation_id    INT NOT NULL REFERENCES T0067(id) ON DELETE CASCADE,
    product_id      INT REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    uom_id          INT REFERENCES T0001(id),
    qty             NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    unit_price      NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    line_total      NUMERIC(12,2) NOT NULL CHECK (line_total >= 0),
    line_number     SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0068.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0068.quotation_id IS 'Parent quotation (FK to T0067)';
COMMENT ON COLUMN T0068.product_id IS 'Product being quoted (FK to T0003)';
COMMENT ON COLUMN T0068.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0068.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0068.qty IS 'Quantity quoted';
COMMENT ON COLUMN T0068.unit_price IS 'Price per unit';
COMMENT ON COLUMN T0068.line_total IS 'Computed total: qty × unit_price';
COMMENT ON COLUMN T0068.line_number IS 'Line sequence number';
COMMENT ON COLUMN T0068.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0068.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0068.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0068.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0068.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0068_quotation ON T0068(quotation_id);

-- ============================================================
-- TRANSACTIONS: Purchase Requisitions
-- ============================================================

-- T0069 - Purchase Requisitions (header)
COMMENT ON TABLE T0069 IS 'PUR — Request for goods/services initiated within the organization';
CREATE TABLE T0069 (
    id              SERIAL PRIMARY KEY,
    req_number      VARCHAR(30) NOT NULL UNIQUE,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    department_id   INT,
    requested_by    INT NOT NULL REFERENCES T0021(id),
    approved_by     INT REFERENCES T0021(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    priority        VARCHAR(10) NOT NULL DEFAULT 'Medium',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0069.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0069.req_number IS 'Unique requisition number (e.g. REQ-2024-001)';
COMMENT ON COLUMN T0069.title IS 'Short description of what is being requested';
COMMENT ON COLUMN T0069.description IS 'Full details and justification for the requisition';
COMMENT ON COLUMN T0069.department_id IS 'Department making the request (FK)';
COMMENT ON COLUMN T0069.requested_by IS 'Employee who created the requisition (FK to T0021)';
COMMENT ON COLUMN T0069.approved_by IS 'Manager who approved the requisition (FK to T0021)';
COMMENT ON COLUMN T0069.status IS 'Requisition status: Draft, Pending Approval, Approved, Rejected, Partially Ordered, Ordered';
COMMENT ON COLUMN T0069.priority IS 'Priority level: Low, Medium, High, Urgent';
COMMENT ON COLUMN T0069.notes IS 'Additional notes or special instructions';
COMMENT ON COLUMN T0069.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0069.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0069.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0069.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0069.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0069_status ON T0069(status);
CREATE INDEX idx_T0069_department ON T0069(department_id);
CREATE INDEX idx_T0069_requested_by ON T0069(requested_by);

-- T0070 - Purchase Requisition Lines
COMMENT ON TABLE T0070 IS 'PUR — Individual line items within a purchase requisition';
CREATE TABLE T0070 (
    id              SERIAL PRIMARY KEY,
    requisition_id  INT NOT NULL REFERENCES T0069(id) ON DELETE CASCADE,
    product_id      INT REFERENCES T0003(id),
    description     VARCHAR(500) NOT NULL,
    qty             NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price     NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    uom_id          INT REFERENCES T0001(id),
    expected_date   DATE,
    notes           TEXT,
    line_number     SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT REFERENCES T0021(id),
    update_number   INT NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0070.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0070.requisition_id IS 'Parent requisition (FK to T0069)';
COMMENT ON COLUMN T0070.product_id IS 'Requested product (FK to T0003)';
COMMENT ON COLUMN T0070.description IS 'Free-text description of what is needed';
COMMENT ON COLUMN T0070.qty IS 'Quantity requested';
COMMENT ON COLUMN T0070.unit_price IS 'Estimated unit price';
COMMENT ON COLUMN T0070.total_price IS 'Computed: qty × unit_price';
COMMENT ON COLUMN T0070.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0070.expected_date IS 'When the item is needed by';
COMMENT ON COLUMN T0070.notes IS 'Line-level notes';
COMMENT ON COLUMN T0070.line_number IS 'Line sequence number';
COMMENT ON COLUMN T0070.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0070.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0070.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0070.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0070.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0070_requisition ON T0070(requisition_id);
CREATE INDEX idx_T0070_product ON T0070(product_id);

-- ============================================================
-- TRANSACTIONS: Request for Quotation (RFQ)
-- ============================================================

-- T0071 - RFQs (header)
COMMENT ON TABLE T0071 IS 'PUR — Request for Quotation header';
CREATE TABLE T0071 (
    id              SERIAL PRIMARY KEY,
    rfq_number      VARCHAR(30) NOT NULL UNIQUE,
    title           VARCHAR(200),
    description     TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    due_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0071.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0071.rfq_number IS 'Unique RFQ reference number (e.g. RFQ-2024-001)';
COMMENT ON COLUMN T0071.title IS 'Short description of the RFQ';
COMMENT ON COLUMN T0071.description IS 'Full details and specifications for the RFQ';
COMMENT ON COLUMN T0071.status IS 'RFQ status: Draft, Sent, Open, Closed, Cancelled';
COMMENT ON COLUMN T0071.due_date IS 'Deadline for vendor responses';
COMMENT ON COLUMN T0071.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0071.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0071.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0071.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0071.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0071.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0071_status ON T0071(status);
CREATE INDEX idx_T0071_due_date ON T0071(due_date);

-- T0072 - RFQ Lines
COMMENT ON TABLE T0072 IS 'PUR — Individual line items on an RFQ';
CREATE TABLE T0072 (
    id              SERIAL PRIMARY KEY,
    rfq_id          INT          NOT NULL REFERENCES T0071(id) ON DELETE CASCADE,
    product_id      INT          REFERENCES T0003(id),
    description     VARCHAR(500),
    qty             NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    uom_id          INT          REFERENCES T0001(id),
    line_number     SMALLINT     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0072.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0072.rfq_id IS 'Parent RFQ (FK to T0071)';
COMMENT ON COLUMN T0072.product_id IS 'Requested product (FK to T0003)';
COMMENT ON COLUMN T0072.description IS 'Free-text description of the item';
COMMENT ON COLUMN T0072.qty IS 'Quantity requested';
COMMENT ON COLUMN T0072.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0072.line_number IS 'Line sequence number for display';
COMMENT ON COLUMN T0072.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0072.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0072.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0072.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0072.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0072_rfq ON T0072(rfq_id);
CREATE INDEX idx_T0072_product ON T0072(product_id);

-- T0073 - RFQ Vendors
COMMENT ON TABLE T0073 IS 'PUR — Vendors invited to quote on an RFQ';
CREATE TABLE T0073 (
    id              SERIAL PRIMARY KEY,
    rfq_id          INT          NOT NULL REFERENCES T0071(id) ON DELETE CASCADE,
    vendor_id       INT          NOT NULL REFERENCES T0011(id),
    status          VARCHAR(20)  NOT NULL DEFAULT 'Pending',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0073.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0073.rfq_id IS 'Parent RFQ (FK to T0071)';
COMMENT ON COLUMN T0073.vendor_id IS 'Invited supplier/vendor (FK to T0011)';
COMMENT ON COLUMN T0073.status IS 'Vendor response status: Pending, Quoted, Declined';
COMMENT ON COLUMN T0073.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0073.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0073.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0073.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0073.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0073_rfq ON T0073(rfq_id);
CREATE INDEX idx_T0073_vendor ON T0073(vendor_id);
CREATE INDEX idx_T0073_status ON T0073(status);

-- T0074 - RFQ Quotes (vendor responses)
COMMENT ON TABLE T0074 IS 'PUR — Quoted prices received from vendors per line item';
CREATE TABLE T0074 (
    id              SERIAL PRIMARY KEY,
    rfq_id          INT          NOT NULL REFERENCES T0071(id) ON DELETE CASCADE,
    vendor_id       INT,
    rfq_vendor_id   INT          REFERENCES T0073(id),
    line_id         INT          REFERENCES T0072(id),
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_price     NUMERIC(12,2) NOT NULL DEFAULT 0,
    delivery_days   INT,
    currency        VARCHAR(3)   NOT NULL DEFAULT 'USD',
    valid_until     DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0074.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0074.rfq_id IS 'Parent RFQ (FK to T0071)';
COMMENT ON COLUMN T0074.vendor_id IS 'Vendor submitting the quote';
COMMENT ON COLUMN T0074.rfq_vendor_id IS 'RFQ vendor link (FK to T0073)';
COMMENT ON COLUMN T0074.line_id IS 'RFQ line being quoted (FK to T0072)';
COMMENT ON COLUMN T0074.unit_price IS 'Price per unit quoted by vendor';
COMMENT ON COLUMN T0074.total_price IS 'Computed: qty × unit_price';
COMMENT ON COLUMN T0074.delivery_days IS 'Estimated delivery time in days';
COMMENT ON COLUMN T0074.currency IS 'Currency code (e.g. USD, EUR)';
COMMENT ON COLUMN T0074.valid_until IS 'Date until which the quote is valid';
COMMENT ON COLUMN T0074.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0074.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0074.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0074.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0074.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0074.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0074_rfq ON T0074(rfq_id);
CREATE INDEX idx_T0074_vendor ON T0074(vendor_id);
CREATE INDEX idx_T0074_line ON T0074(line_id);

-- ============================================================
-- INVENTORY: Goods Receipt
-- ============================================================

-- T0075 - Goods Receipts (header)
COMMENT ON TABLE T0075 IS 'INV — Goods Receipt Note header for incoming stock against Purchase Orders';
CREATE TABLE T0075 (
    id              SERIAL PRIMARY KEY,
    receipt_number  VARCHAR(30) NOT NULL UNIQUE,
    purchase_order_id INT REFERENCES T0014(id),
    receipt_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    warehouse_id    INT REFERENCES T0008(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0075.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0075.receipt_number IS 'Human-readable GRN reference (e.g. GRN-2024-001)';
COMMENT ON COLUMN T0075.purchase_order_id IS 'Purchase Order being received against (FK to T0014)';
COMMENT ON COLUMN T0075.receipt_date IS 'Date the goods were received';
COMMENT ON COLUMN T0075.warehouse_id IS 'Warehouse where goods are stored (FK to T0008)';
COMMENT ON COLUMN T0075.status IS 'Receipt status: Draft, Completed, Cancelled';
COMMENT ON COLUMN T0075.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0075.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0075.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0075.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0075.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0075.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0075_po ON T0075(purchase_order_id);
CREATE INDEX idx_T0075_status ON T0075(status);
CREATE INDEX idx_T0075_date ON T0075(receipt_date);

-- T0076 - Goods Receipt Lines
COMMENT ON TABLE T0076 IS 'INV — Individual line items on a Goods Receipt Note';
CREATE TABLE T0076 (
    id              SERIAL PRIMARY KEY,
    receipt_id      INT NOT NULL REFERENCES T0075(id) ON DELETE CASCADE,
    purchase_order_line_id INT REFERENCES T0015(id),
    product_id      INT REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    qty_received    NUMERIC(12,2) NOT NULL CHECK (qty_received > 0),
    qty_ordered     NUMERIC(12,2) NOT NULL DEFAULT 0,
    uom_id          INT REFERENCES T0001(id),
    line_number     SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT         REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT         REFERENCES T0021(id),
    update_number   INT         NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0076.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0076.receipt_id IS 'Parent Goods Receipt Note (FK to T0075)';
COMMENT ON COLUMN T0076.purchase_order_line_id IS 'Matching PO line (FK to T0015)';
COMMENT ON COLUMN T0076.product_id IS 'Product being received (FK to T0003)';
COMMENT ON COLUMN T0076.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0076.qty_received IS 'Quantity actually received in the line UOM';
COMMENT ON COLUMN T0076.qty_ordered IS 'Quantity originally ordered on the PO line';
COMMENT ON COLUMN T0076.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0076.line_number IS 'Line item sequence number for display';
COMMENT ON COLUMN T0076.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0076.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0076.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0076.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0076.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0076_receipt ON T0076(receipt_id);
CREATE INDEX idx_T0076_product ON T0076(product_id);

-- ============================================================
-- SALES: Delivery / Shipment
-- ============================================================

-- T0077 - Deliveries (header)
COMMENT ON TABLE T0077 IS 'SALES — Delivery Note header for outbound shipments against Sales Orders';
CREATE TABLE T0077 (
    id              SERIAL PRIMARY KEY,
    delivery_number VARCHAR(30) NOT NULL UNIQUE,
    sales_order_id  INT NOT NULL REFERENCES T0012(id),
    delivery_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    warehouse_id    INT REFERENCES T0008(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0077.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0077.delivery_number IS 'Human-readable delivery reference (e.g. DEL-2024-001)';
COMMENT ON COLUMN T0077.sales_order_id IS 'Sales Order being fulfilled (FK to T0012)';
COMMENT ON COLUMN T0077.delivery_date IS 'Date the goods are shipped';
COMMENT ON COLUMN T0077.warehouse_id IS 'Warehouse from which goods are shipped (FK to T0008)';
COMMENT ON COLUMN T0077.status IS 'Delivery status: Draft, Shipped, Delivered, Cancelled';
COMMENT ON COLUMN T0077.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0077.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0077.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0077.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0077.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0077.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0077_so ON T0077(sales_order_id);
CREATE INDEX idx_T0077_status ON T0077(status);
CREATE INDEX idx_T0077_date ON T0077(delivery_date);

-- T0078 - Delivery Lines
COMMENT ON TABLE T0078 IS 'SALES — Individual line items on a Delivery Note';
CREATE TABLE T0078 (
    id              SERIAL PRIMARY KEY,
    delivery_id     INT NOT NULL REFERENCES T0077(id) ON DELETE CASCADE,
    sales_order_line_id INT REFERENCES T0013(id),
    product_id      INT REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    qty_shipped     NUMERIC(12,2) NOT NULL CHECK (qty_shipped > 0),
    qty_ordered     NUMERIC(12,2) NOT NULL DEFAULT 0,
    uom_id          INT REFERENCES T0001(id),
    line_number     SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT         REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT         REFERENCES T0021(id),
    update_number   INT         NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0078.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0078.delivery_id IS 'Parent Delivery Note (FK to T0077)';
COMMENT ON COLUMN T0078.sales_order_line_id IS 'Matching Sales Order line (FK to T0013)';
COMMENT ON COLUMN T0078.product_id IS 'Product being shipped (FK to T0003)';
COMMENT ON COLUMN T0078.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0078.qty_shipped IS 'Quantity actually shipped in the line UOM';
COMMENT ON COLUMN T0078.qty_ordered IS 'Quantity originally ordered on the Sales Order line';
COMMENT ON COLUMN T0078.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0078.line_number IS 'Line item sequence number for display';
COMMENT ON COLUMN T0078.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0078.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0078.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0078.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0078.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0078_delivery ON T0078(delivery_id);
CREATE INDEX idx_T0078_product ON T0078(product_id);

-- ============================================================
-- SALES: Sales Returns / RMA
-- ============================================================

-- T0079 - Sales Returns (header)
COMMENT ON TABLE T0079 IS 'SALES — Sales Returns / RMA header for customer returns of goods';
CREATE TABLE T0079 (
    id              SERIAL PRIMARY KEY,
    return_number   VARCHAR(30) NOT NULL UNIQUE,
    sales_order_id  INT REFERENCES T0012(id),
    customer_id     INT NOT NULL REFERENCES T0010(id),
    return_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    reason          TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0079.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0079.return_number IS 'Human-readable return reference (e.g. SR-2024-001)';
COMMENT ON COLUMN T0079.sales_order_id IS 'Original Sales Order being returned against (FK to T0012)';
COMMENT ON COLUMN T0079.customer_id IS 'Customer returning the goods (FK to T0010)';
COMMENT ON COLUMN T0079.return_date IS 'Date the return is recorded';
COMMENT ON COLUMN T0079.status IS 'Return status: Draft, Approved, Received, Cancelled';
COMMENT ON COLUMN T0079.reason IS 'Reason for the return';
COMMENT ON COLUMN T0079.notes IS 'Free-text notes or comments';
COMMENT ON COLUMN T0079.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0079.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0079.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0079.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0079.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0079_so ON T0079(sales_order_id);
CREATE INDEX idx_T0079_customer ON T0079(customer_id);
CREATE INDEX idx_T0079_status ON T0079(status);
CREATE INDEX idx_T0079_date ON T0079(return_date);

-- T0080 - Sales Return Lines
COMMENT ON TABLE T0080 IS 'SALES — Individual line items on a Sales Return';
CREATE TABLE T0080 (
    id              SERIAL PRIMARY KEY,
    return_id       INT NOT NULL REFERENCES T0079(id) ON DELETE CASCADE,
    product_id      INT REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    qty             NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(12,2) NOT NULL DEFAULT 0,
    uom_id          INT REFERENCES T0001(id),
    line_number     SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT         REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT         REFERENCES T0021(id),
    update_number   INT         NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0080.id IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0080.return_id IS 'Parent Sales Return (FK to T0079)';
COMMENT ON COLUMN T0080.product_id IS 'Product being returned (FK to T0003)';
COMMENT ON COLUMN T0080.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0080.qty IS 'Quantity returned';
COMMENT ON COLUMN T0080.unit_price IS 'Unit price at time of return';
COMMENT ON COLUMN T0080.line_total IS 'Line total = qty * unit_price';
COMMENT ON COLUMN T0080.uom_id IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0080.line_number IS 'Line item sequence number for display';
COMMENT ON COLUMN T0080.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN T0080.created_by IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0080.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN T0080.updated_by IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0080.update_number IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0080_return ON T0080(return_id);
CREATE INDEX idx_T0080_product ON T0080(product_id);

-- ============================================================
-- TRANSACTIONS: Purchase Returns
-- ============================================================

-- T0081 - Purchase Returns (header)
COMMENT ON TABLE T0081 IS 'PURCHASING — Purchase Return header for returning defective/unwanted goods to supplier';
CREATE TABLE T0081 (
    id              SERIAL PRIMARY KEY,
    return_number   VARCHAR(30) NOT NULL UNIQUE,
    purchase_order_id INT REFERENCES T0014(id),
    supplier_id     INT         NOT NULL REFERENCES T0011(id),
    return_date     DATE        NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    reason          TEXT,
    notes           TEXT,
    -- audit
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      INT         REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      INT         REFERENCES T0021(id),
    update_number   INT         NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0081.id                IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0081.return_number     IS 'Human-readable return reference (e.g. PR-2024-001)';
COMMENT ON COLUMN T0081.purchase_order_id IS 'Original Purchase Order being returned against (FK to T0014)';
COMMENT ON COLUMN T0081.supplier_id       IS 'Supplier receiving the return (FK to T0011)';
COMMENT ON COLUMN T0081.return_date       IS 'Date the return is recorded';
COMMENT ON COLUMN T0081.status            IS 'Return status: Draft, Approved, Returned, Cancelled';
COMMENT ON COLUMN T0081.reason            IS 'Reason for the return';
COMMENT ON COLUMN T0081.notes             IS 'Free-text notes or comments';
COMMENT ON COLUMN T0081.created_at        IS 'Record creation timestamp';
COMMENT ON COLUMN T0081.created_by        IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0081.updated_at        IS 'Last modification timestamp';
COMMENT ON COLUMN T0081.updated_by        IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0081.update_number     IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0081_po       ON T0081(purchase_order_id);
CREATE INDEX idx_T0081_supplier ON T0081(supplier_id);
CREATE INDEX idx_T0081_status   ON T0081(status);
CREATE INDEX idx_T0081_date     ON T0081(return_date);

-- T0082 - Purchase Return Lines
COMMENT ON TABLE T0082 IS 'PURCHASING — Individual line items on a Purchase Return';
CREATE TABLE T0082 (
    id              SERIAL PRIMARY KEY,
    return_id       INT          NOT NULL REFERENCES T0081(id) ON DELETE CASCADE,
    product_id      INT          REFERENCES T0003(id),
    product_name    VARCHAR(200) NOT NULL,
    qty             NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    unit_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total      NUMERIC(12,2) NOT NULL DEFAULT 0,
    uom_id          INT          REFERENCES T0001(id),
    line_number     SMALLINT     NOT NULL DEFAULT 0,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0082.id          IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0082.return_id   IS 'Parent Purchase Return (FK to T0081)';
COMMENT ON COLUMN T0082.product_id  IS 'Product being returned (FK to T0003)';
COMMENT ON COLUMN T0082.product_name IS 'Denormalized product name';
COMMENT ON COLUMN T0082.qty         IS 'Quantity returned';
COMMENT ON COLUMN T0082.unit_price  IS 'Unit price at time of return';
COMMENT ON COLUMN T0082.line_total  IS 'Line total = qty * unit_price';
COMMENT ON COLUMN T0082.uom_id      IS 'Unit of measure (FK to T0001)';
COMMENT ON COLUMN T0082.line_number IS 'Line item sequence number for display';
COMMENT ON COLUMN T0082.created_at  IS 'Record creation timestamp';
COMMENT ON COLUMN T0082.created_by  IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0082.updated_at  IS 'Last modification timestamp';
COMMENT ON COLUMN T0082.updated_by  IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0082.update_number IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0082_return  ON T0082(return_id);
CREATE INDEX idx_T0082_product ON T0082(product_id);

-- ============================================================
-- TAXES: Tax Rates & Rules
-- ============================================================

-- T0085 - Tax Rates
COMMENT ON TABLE T0085 IS 'SALES — Tax rate definitions (e.g. Standard VAT, Reduced VAT, Exempt)';
CREATE TABLE T0085 (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(20)  NOT NULL UNIQUE,
    rate            NUMERIC(5,2) NOT NULL,
    type            VARCHAR(20)  NOT NULL DEFAULT 'Sales',
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    is_default      BOOLEAN      NOT NULL DEFAULT false,
    description     TEXT,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0085.id          IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0085.name        IS 'Tax rate display name (e.g. Standard VAT)';
COMMENT ON COLUMN T0085.code        IS 'Unique tax rate code (e.g. VAT-STD, VAT-RED, EXEMPT)';
COMMENT ON COLUMN T0085.rate        IS 'Tax rate percentage (e.g. 15.00 for 15% VAT)';
COMMENT ON COLUMN T0085.type        IS 'Tax type: Sales, Purchase, or Both';
COMMENT ON COLUMN T0085.is_active   IS 'Whether this tax rate is active';
COMMENT ON COLUMN T0085.is_default  IS 'Whether this tax rate is the system default';
COMMENT ON COLUMN T0085.description IS 'Free-text description of the tax rate';
COMMENT ON COLUMN T0085.created_at        IS 'Record creation timestamp';
COMMENT ON COLUMN T0085.created_by        IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0085.updated_at        IS 'Last modification timestamp';
COMMENT ON COLUMN T0085.updated_by        IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0085.update_number     IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0085_code ON T0085(code);
CREATE INDEX idx_T0085_type ON T0085(type);
CREATE INDEX idx_T0085_active ON T0085(is_active);

-- T0086 - Tax Rules
COMMENT ON TABLE T0086 IS 'SALES — Tax rule assignments linking tax rates to products, customers, or suppliers';
CREATE TABLE T0086 (
    id              SERIAL PRIMARY KEY,
    tax_rate_id     INT          NOT NULL REFERENCES T0085(id) ON DELETE CASCADE,
    applies_to      VARCHAR(20)  NOT NULL DEFAULT 'All',
    target_id       INT          DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0086.id          IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0086.tax_rate_id IS 'Tax rate to apply (FK to T0085)';
COMMENT ON COLUMN T0086.applies_to  IS 'Scope: All, Products, Services, Customers, Suppliers';
COMMENT ON COLUMN T0086.target_id   IS 'FK to product/customer/supplier (0 means all in scope)';
COMMENT ON COLUMN T0086.is_active   IS 'Whether this rule is active';
COMMENT ON COLUMN T0086.created_at        IS 'Record creation timestamp';
COMMENT ON COLUMN T0086.created_by        IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0086.updated_at        IS 'Last modification timestamp';
COMMENT ON COLUMN T0086.updated_by        IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0086.update_number     IS 'Version counter incremented on each update, starts at 1';
CREATE INDEX idx_T0086_rate ON T0086(tax_rate_id);
CREATE INDEX idx_T0086_applies ON T0086(applies_to);
CREATE INDEX idx_T0086_target ON T0086(target_id);

-- ============================================================
-- PRICE LISTS
-- ============================================================

-- T0083 - Price Lists
COMMENT ON TABLE T0083 IS 'SAL — Price list tiers (Standard, Wholesale, Promotional, etc.)';
CREATE TABLE T0083 (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(20)  NOT NULL UNIQUE,
    description     TEXT,
    currency        VARCHAR(3)   NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    is_default      BOOLEAN      NOT NULL DEFAULT false,
    -- audit
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0083.id          IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0083.name        IS 'Price list display name (e.g. Standard, Wholesale, Promotional)';
COMMENT ON COLUMN T0083.code        IS 'Unique short code (e.g. STD, WHL, PRO)';
COMMENT ON COLUMN T0083.description IS 'Description or notes about this price list';
COMMENT ON COLUMN T0083.currency    IS 'Currency code for prices in this list (e.g. USD, EUR)';
COMMENT ON COLUMN T0083.is_active   IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0083.is_default  IS 'TRUE = default price list used when no specific list is assigned';
COMMENT ON COLUMN T0083.created_at     IS 'Record creation timestamp';
COMMENT ON COLUMN T0083.created_by     IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0083.updated_at     IS 'Last modification timestamp';
COMMENT ON COLUMN T0083.updated_by     IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0083.update_number  IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0083_code   ON T0083(code);
CREATE INDEX idx_T0083_active ON T0083(is_active);

-- T0084 - Price List Items
COMMENT ON TABLE T0084 IS 'SAL — Per-product prices within a price list';
CREATE TABLE T0084 (
    id              SERIAL PRIMARY KEY,
    price_list_id   INT            NOT NULL REFERENCES T0083(id) ON DELETE CASCADE,
    product_id      INT            NOT NULL REFERENCES T0003(id),
    unit_price      NUMERIC(12,2)  NOT NULL CHECK (unit_price >= 0),
    min_qty         NUMERIC(12,2)  DEFAULT 1,
    uom_id          INT            REFERENCES T0001(id),
    effective_from  DATE,
    effective_to    DATE,
    line_number     SMALLINT       NOT NULL DEFAULT 0,
    -- audit
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    created_by      INT            REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_by      INT            REFERENCES T0021(id),
    update_number   INT            NOT NULL DEFAULT 1,
    UNIQUE (price_list_id, product_id)
);
COMMENT ON COLUMN T0084.id              IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0084.price_list_id   IS 'Parent price list (FK to T0083)';
COMMENT ON COLUMN T0084.product_id      IS 'Product this price applies to (FK to T0003)';
COMMENT ON COLUMN T0084.unit_price      IS 'Price per unit in the price list currency';
COMMENT ON COLUMN T0084.min_qty         IS 'Minimum quantity required for this price tier';
COMMENT ON COLUMN T0084.uom_id          IS 'Unit of measure for the price (FK to T0001)';
COMMENT ON COLUMN T0084.effective_from  IS 'Date from which this price is effective';
COMMENT ON COLUMN T0084.effective_to    IS 'Date until which this price is effective';
COMMENT ON COLUMN T0084.line_number     IS 'Line item sequence number for display';
COMMENT ON COLUMN T0084.created_at      IS 'Record creation timestamp';
COMMENT ON COLUMN T0084.created_by      IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0084.updated_at      IS 'Last modification timestamp';
COMMENT ON COLUMN T0084.updated_by      IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0084.update_number   IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0084_list     ON T0084(price_list_id);
CREATE INDEX idx_T0084_product  ON T0084(product_id);
CREATE INDEX idx_T0084_dates    ON T0084(effective_from, effective_to);

-- ============================================================
-- SERIAL & BATCH TRACKING
-- ============================================================

-- T0087 - Serial Numbers
COMMENT ON TABLE T0087 IS 'INV — Individual item serial number tracking';
CREATE TABLE T0087 (
    id                      SERIAL PRIMARY KEY,
    product_id              INT          NOT NULL REFERENCES T0003(id),
    serial_number           VARCHAR(100) NOT NULL UNIQUE,
    status                  VARCHAR(20)  NOT NULL DEFAULT 'In Stock',
    warehouse_id            INT          REFERENCES T0008(id),
    purchase_order_line_id  INT          REFERENCES T0015(id),
    sales_order_line_id     INT          REFERENCES T0013(id),
    notes                   TEXT,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by              INT          REFERENCES T0021(id),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by              INT          REFERENCES T0021(id),
    update_number           INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0087.id                     IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0087.product_id             IS 'Product this serial number belongs to (FK to T0003)';
COMMENT ON COLUMN T0087.serial_number           IS 'Unique serial number identifier';
COMMENT ON COLUMN T0087.status                 IS 'Current status: In Stock, Reserved, Sold, Returned, Scrapped, Lost';
COMMENT ON COLUMN T0087.warehouse_id           IS 'Storage location (FK to T0008)';
COMMENT ON COLUMN T0087.purchase_order_line_id IS 'PO line that received this serial (FK to T0015)';
COMMENT ON COLUMN T0087.sales_order_line_id    IS 'SO line that sold this serial (FK to T0013)';
COMMENT ON COLUMN T0087.notes                  IS 'Free-text notes or comments';
COMMENT ON COLUMN T0087.created_at             IS 'Record creation timestamp';
COMMENT ON COLUMN T0087.created_by             IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0087.updated_at             IS 'Last modification timestamp';
COMMENT ON COLUMN T0087.updated_by             IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0087.update_number          IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0087_product   ON T0087(product_id);
CREATE INDEX idx_T0087_serial    ON T0087(serial_number);
CREATE INDEX idx_T0087_status    ON T0087(status);
CREATE INDEX idx_T0087_warehouse ON T0087(warehouse_id);

-- T0088 - Batch Numbers
COMMENT ON TABLE T0088 IS 'INV — Batch/lot number tracking for grouped items';
CREATE TABLE T0088 (
    id                  SERIAL PRIMARY KEY,
    product_id          INT           NOT NULL REFERENCES T0003(id),
    batch_number        VARCHAR(100)  NOT NULL,
    expiry_date         DATE,
    manufacturing_date  DATE,
    quantity            NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    warehouse_id        INT           REFERENCES T0008(id),
    status              VARCHAR(20)   NOT NULL DEFAULT 'Available',
    notes               TEXT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    created_by          INT           REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by          INT           REFERENCES T0021(id),
    update_number       INT           NOT NULL DEFAULT 1,
    UNIQUE (product_id, batch_number)
);
COMMENT ON COLUMN T0088.id                 IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0088.product_id         IS 'Product this batch belongs to (FK to T0003)';
COMMENT ON COLUMN T0088.batch_number       IS 'Batch/lot number (unique per product)';
COMMENT ON COLUMN T0088.expiry_date        IS 'Expiration date for this batch';
COMMENT ON COLUMN T0088.manufacturing_date IS 'Date this batch was manufactured';
COMMENT ON COLUMN T0088.quantity           IS 'Current available quantity in base UOM (>= 0)';
COMMENT ON COLUMN T0088.warehouse_id       IS 'Storage location (FK to T0008)';
COMMENT ON COLUMN T0088.status             IS 'Batch status: Available, Partially Used, Expired, Depleted';
COMMENT ON COLUMN T0088.notes              IS 'Free-text notes or comments';
COMMENT ON COLUMN T0088.created_at         IS 'Record creation timestamp';
COMMENT ON COLUMN T0088.created_by         IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0088.updated_at         IS 'Last modification timestamp';
COMMENT ON COLUMN T0088.updated_by         IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0088.update_number      IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0088_product   ON T0088(product_id);
CREATE INDEX idx_T0088_batch     ON T0088(batch_number);
CREATE INDEX idx_T0088_status    ON T0088(status);
CREATE INDEX idx_T0088_expiry    ON T0088(expiry_date);

-- ============================================================
-- CRM: Leads & Opportunities
-- ============================================================

-- T0092 - Leads
COMMENT ON TABLE T0092 IS 'CRM — Lead generation and qualification pipeline';
CREATE TABLE T0092 (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255),
    phone           VARCHAR(50),
    company         VARCHAR(200),
    title           VARCHAR(100),
    source          VARCHAR(50) DEFAULT 'Website',
    status          VARCHAR(20) NOT NULL DEFAULT 'New',
    assigned_to     INT REFERENCES T0021(id),
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0092.id           IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0092.first_name   IS 'Lead first name';
COMMENT ON COLUMN T0092.last_name    IS 'Lead last name';
COMMENT ON COLUMN T0092.email        IS 'Lead email address';
COMMENT ON COLUMN T0092.phone        IS 'Lead contact phone number';
COMMENT ON COLUMN T0092.company      IS 'Lead company/organization name';
COMMENT ON COLUMN T0092.title        IS 'Lead job title';
COMMENT ON COLUMN T0092.source       IS 'Lead source: Website, Referral, Cold Call, Social Media, Trade Show, Other';
COMMENT ON COLUMN T0092.status       IS 'Lead status: New, Contacted, Qualified, Disqualified, Converted';
COMMENT ON COLUMN T0092.assigned_to  IS 'Sales rep assigned to this lead (FK to T0021)';
COMMENT ON COLUMN T0092.notes        IS 'Free-text notes about the lead';
COMMENT ON COLUMN T0092.created_at   IS 'Record creation timestamp';
COMMENT ON COLUMN T0092.created_by   IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0092.updated_at   IS 'Last modification timestamp';
COMMENT ON COLUMN T0092.updated_by   IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0092.update_number IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0092_status     ON T0092(status);
CREATE INDEX idx_T0092_assigned   ON T0092(assigned_to);
CREATE INDEX idx_T0092_source     ON T0092(source);

-- T0093 - Lead Activities
COMMENT ON TABLE T0093 IS 'CRM — Activities and interactions logged against a lead';
CREATE TABLE T0093 (
    id              SERIAL PRIMARY KEY,
    lead_id         INT NOT NULL REFERENCES T0092(id) ON DELETE CASCADE,
    activity_type   VARCHAR(30) NOT NULL,
    subject         VARCHAR(200) NOT NULL,
    description     TEXT,
    activity_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    completed       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0093.id            IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0093.lead_id       IS 'Lead this activity belongs to (FK to T0092)';
COMMENT ON COLUMN T0093.activity_type IS 'Activity type: Call, Email, Meeting, Note, Task';
COMMENT ON COLUMN T0093.subject       IS 'Activity subject or title';
COMMENT ON COLUMN T0093.description   IS 'Detailed description of the activity';
COMMENT ON COLUMN T0093.activity_date IS 'Date the activity occurred or is scheduled';
COMMENT ON COLUMN T0093.completed     IS 'Whether this activity has been completed';
COMMENT ON COLUMN T0093.created_at    IS 'Record creation timestamp';
COMMENT ON COLUMN T0093.created_by    IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0093.updated_at    IS 'Last modification timestamp';
COMMENT ON COLUMN T0093.updated_by    IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0093.update_number IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0093_lead       ON T0093(lead_id);
CREATE INDEX idx_T0093_type       ON T0093(activity_type);
CREATE INDEX idx_T0093_date       ON T0093(activity_date);

-- T0094 - Opportunities
COMMENT ON TABLE T0094 IS 'CRM — Sales opportunities and pipeline stages';
CREATE TABLE T0094 (
    id                  SERIAL PRIMARY KEY,
    opportunity_name    VARCHAR(200) NOT NULL,
    lead_id             INT REFERENCES T0092(id),
    customer_id         INT REFERENCES T0010(id),
    stage               VARCHAR(30) NOT NULL DEFAULT 'Prospecting',
    amount              NUMERIC(12,2) NOT NULL DEFAULT 0,
    probability         SMALLINT NOT NULL DEFAULT 10,
    expected_close_date DATE,
    assigned_to         INT REFERENCES T0021(id),
    notes               TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by          INT          REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by          INT          REFERENCES T0021(id),
    update_number       INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0094.id                 IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0094.opportunity_name   IS 'Name or title of the sales opportunity';
COMMENT ON COLUMN T0094.lead_id            IS 'Originating lead (FK to T0092)';
COMMENT ON COLUMN T0094.customer_id        IS 'Customer account (FK to T0010)';
COMMENT ON COLUMN T0094.stage              IS 'Pipeline stage: Prospecting, Qualification, Needs Analysis, Proposal, Negotiation, Closed Won, Closed Lost';
COMMENT ON COLUMN T0094.amount             IS 'Expected deal amount in base currency';
COMMENT ON COLUMN T0094.probability        IS 'Win probability percentage (0-100)';
COMMENT ON COLUMN T0094.expected_close_date IS 'Expected close date for the deal';
COMMENT ON COLUMN T0094.assigned_to        IS 'Sales rep responsible (FK to T0021)';
COMMENT ON COLUMN T0094.notes              IS 'Free-text notes about the opportunity';
COMMENT ON COLUMN T0094.created_at         IS 'Record creation timestamp';
COMMENT ON COLUMN T0094.created_by         IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0094.updated_at         IS 'Last modification timestamp';
COMMENT ON COLUMN T0094.updated_by         IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0094.update_number      IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0094_stage      ON T0094(stage);
CREATE INDEX idx_T0094_lead       ON T0094(lead_id);
CREATE INDEX idx_T0094_customer   ON T0094(customer_id);
CREATE INDEX idx_T0094_assigned   ON T0094(assigned_to);

-- T0095 - Opportunity Lines
COMMENT ON TABLE T0095 IS 'CRM — Product line items on an opportunity';
CREATE TABLE T0095 (
    id                SERIAL PRIMARY KEY,
    opportunity_id    INT NOT NULL REFERENCES T0094(id) ON DELETE CASCADE,
    product_id        INT REFERENCES T0003(id),
    product_name      VARCHAR(200) NOT NULL,
    qty               NUMERIC(12,2) NOT NULL CHECK (qty > 0),
    unit_price        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_total        NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_number       SMALLINT NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by        INT          REFERENCES T0021(id),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by        INT          REFERENCES T0021(id),
    update_number     INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0095.id              IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0095.opportunity_id  IS 'Parent opportunity (FK to T0094)';
COMMENT ON COLUMN T0095.product_id      IS 'Product being offered (FK to T0003)';
COMMENT ON COLUMN T0095.product_name    IS 'Denormalized product name';
COMMENT ON COLUMN T0095.qty             IS 'Quantity in the line UOM';
COMMENT ON COLUMN T0095.unit_price      IS 'Price per unit at time of quotation';
COMMENT ON COLUMN T0095.line_total      IS 'Computed total: qty × unit_price';
COMMENT ON COLUMN T0095.line_number     IS 'Line item sequence number for display';
COMMENT ON COLUMN T0095.created_at      IS 'Record creation timestamp';
COMMENT ON COLUMN T0095.created_by      IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0095.updated_at      IS 'Last modification timestamp';
COMMENT ON COLUMN T0095.updated_by      IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0095.update_number   IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0095_opportunity ON T0095(opportunity_id);
CREATE INDEX idx_T0095_product     ON T0095(product_id);

-- ============================================================
-- T0096 - Payment Terms
-- ============================================================

-- T0096 - Payment Terms master
COMMENT ON TABLE T0096 IS 'Payment terms master — defines payment due dates and early payment discounts';
CREATE TABLE T0096 (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    code                VARCHAR(20)  NOT NULL UNIQUE,
    description         TEXT,
    due_days            INT          NOT NULL DEFAULT 30,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
    discount_days       INT          NOT NULL DEFAULT 0,
    is_active           BOOLEAN      NOT NULL DEFAULT true,
    is_default          BOOLEAN      NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by          INT          REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by          INT          REFERENCES T0021(id),
    update_number       INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0096.id                 IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0096.name               IS 'Display name (e.g. Net 30, Net 60, Due on Receipt)';
COMMENT ON COLUMN T0096.code               IS 'Unique short code (e.g. NET30, NET60, DUE_RECEIPT)';
COMMENT ON COLUMN T0096.description        IS 'Optional description or notes';
COMMENT ON COLUMN T0096.due_days           IS 'Number of days after invoice date for payment';
COMMENT ON COLUMN T0096.discount_percentage IS 'Early payment discount percentage (e.g. 2.00 for 2%%)';
COMMENT ON COLUMN T0096.discount_days      IS 'Days within which early payment discount applies';
COMMENT ON COLUMN T0096.is_active          IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0096.is_default         IS 'Only one record can be the default payment term';
COMMENT ON COLUMN T0096.created_at         IS 'Record creation timestamp';
COMMENT ON COLUMN T0096.created_by         IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0096.updated_at         IS 'Last modification timestamp';
COMMENT ON COLUMN T0096.updated_by         IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0096.update_number      IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0096_is_default ON T0096(is_default);

-- ============================================================
-- T0097 - Payment Methods
-- ============================================================

-- T0097 - Payment Methods master
COMMENT ON TABLE T0097 IS 'Payment methods master — defines modes of payment (Bank Transfer, Cash, Credit Card, etc.)';
CREATE TABLE T0097 (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    code                VARCHAR(20)  NOT NULL UNIQUE,
    description         TEXT,
    is_active           BOOLEAN      NOT NULL DEFAULT true,
    is_default          BOOLEAN      NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by          INT          REFERENCES T0021(id),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by          INT          REFERENCES T0021(id),
    update_number       INT          NOT NULL DEFAULT 1
);
COMMENT ON COLUMN T0097.id                 IS 'Primary key (auto-increment)';
COMMENT ON COLUMN T0097.name               IS 'Display name (e.g. Bank Transfer, Cash, Credit Card)';
COMMENT ON COLUMN T0097.code               IS 'Unique short code (e.g. BANK_TRANSFER, CASH, CREDIT_CARD)';
COMMENT ON COLUMN T0097.description        IS 'Optional description or notes';
COMMENT ON COLUMN T0097.is_active          IS 'Soft delete flag: TRUE = active, FALSE = inactive/deleted';
COMMENT ON COLUMN T0097.is_default         IS 'Only one record can be the default payment method';
COMMENT ON COLUMN T0097.created_at         IS 'Record creation timestamp';
COMMENT ON COLUMN T0097.created_by         IS 'User who created this record (FK to T0021)';
COMMENT ON COLUMN T0097.updated_at         IS 'Last modification timestamp';
COMMENT ON COLUMN T0097.updated_by         IS 'User who last modified this record (FK to T0021)';
COMMENT ON COLUMN T0097.update_number      IS 'Version counter incremented on each update, starts at 1';

CREATE INDEX idx_T0097_is_default ON T0097(is_default);

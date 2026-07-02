-- Nova ERP — Missing Tables Migration (002)
-- Generated from controller business_columns and Pydantic models
-- Run against a PostgreSQL database with the Nova schema already created

BEGIN;

-- Employee Contracts
CREATE TABLE IF NOT EXISTS "Nova".t0031 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    contract_type VARCHAR(30),
    start_date DATE,
    end_date DATE,
    basic_salary NUMERIC(12,2),
    housing_allowance NUMERIC(12,2),
    transport_allowance NUMERIC(12,2),
    other_allowances NUMERIC(12,2),
    currency VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0031 IS 'Employee Contracts';
COMMENT ON COLUMN "Nova".t0031.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0031.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0031.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0031_employee_id ON "Nova".t0031(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0031_active ON "Nova".t0031(is_active);

-- Employee Documents
CREATE TABLE IF NOT EXISTS "Nova".t0032 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    document_type VARCHAR(30),
    document_name VARCHAR(200),
    file_path TEXT,
    expiry_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0032 IS 'Employee Documents';
COMMENT ON COLUMN "Nova".t0032.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0032.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0032.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0032_employee_id ON "Nova".t0032(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0032_active ON "Nova".t0032(is_active);

-- Work Shifts
CREATE TABLE IF NOT EXISTS "Nova".t0033 (
    id SERIAL PRIMARY KEY,
    shift_code VARCHAR(30),
    shift_name VARCHAR(200),
    start_time TIME,
    end_time TIME,
    grace_minutes NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0033 IS 'Work Shifts';
COMMENT ON COLUMN "Nova".t0033.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0033.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0033_active ON "Nova".t0033(is_active);

-- Employee Attendance Records
CREATE TABLE IF NOT EXISTS "Nova".t0034 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    date DATE,
    shift_id INT,
    clock_in TIME,
    clock_out TIME,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0034 IS 'Employee Attendance Records';
COMMENT ON COLUMN "Nova".t0034.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0034.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0034.shift_id IS 'Reference to Shift';
COMMENT ON COLUMN "Nova".t0034.status IS 'Status';
COMMENT ON COLUMN "Nova".t0034.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0034_employee_id ON "Nova".t0034(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0034_shift_id ON "Nova".t0034(shift_id);
CREATE INDEX IF NOT EXISTS idx_t0034_status ON "Nova".t0034(status);
CREATE INDEX IF NOT EXISTS idx_t0034_active ON "Nova".t0034(is_active);

-- Leave Types
CREATE TABLE IF NOT EXISTS "Nova".t0035 (
    id SERIAL PRIMARY KEY,
    leave_code VARCHAR(30),
    leave_name VARCHAR(200),
    days_per_year VARCHAR(200),
    is_paid VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0035 IS 'Leave Types';
COMMENT ON COLUMN "Nova".t0035.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0035.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0035_active ON "Nova".t0035(is_active);

-- Leave Requests
CREATE TABLE IF NOT EXISTS "Nova".t0036 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    leave_type_id INT,
    start_date DATE,
    end_date DATE,
    days NUMERIC(5,1),
    reason VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    approved_by VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0036 IS 'Leave Requests';
COMMENT ON COLUMN "Nova".t0036.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0036.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0036.leave_type_id IS 'Reference to Leave_Type';
COMMENT ON COLUMN "Nova".t0036.status IS 'Status';
COMMENT ON COLUMN "Nova".t0036.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0036_employee_id ON "Nova".t0036(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0036_leave_type_id ON "Nova".t0036(leave_type_id);
CREATE INDEX IF NOT EXISTS idx_t0036_status ON "Nova".t0036(status);
CREATE INDEX IF NOT EXISTS idx_t0036_active ON "Nova".t0036(is_active);

-- Payroll Periods
CREATE TABLE IF NOT EXISTS "Nova".t0037 (
    id SERIAL PRIMARY KEY,
    period_code VARCHAR(30),
    period_name VARCHAR(200),
    start_date DATE,
    end_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0037 IS 'Payroll Periods';
COMMENT ON COLUMN "Nova".t0037.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0037.status IS 'Status';
COMMENT ON COLUMN "Nova".t0037.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0037_status ON "Nova".t0037(status);
CREATE INDEX IF NOT EXISTS idx_t0037_active ON "Nova".t0037(is_active);

-- Payroll Entries
CREATE TABLE IF NOT EXISTS "Nova".t0038 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    payroll_period_id INT,
    basic_salary NUMERIC(12,2),
    housing_allowance NUMERIC(12,2),
    transport_allowance NUMERIC(12,2),
    other_allowances NUMERIC(12,2),
    overtime NUMERIC(12,2),
    deductions NUMERIC(12,2),
    tax NUMERIC(12,2),
    gross_pay NUMERIC(12,2),
    net_pay NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    payment_date DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0038 IS 'Payroll Entries';
COMMENT ON COLUMN "Nova".t0038.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0038.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0038.payroll_period_id IS 'Reference to Payroll_Period';
COMMENT ON COLUMN "Nova".t0038.status IS 'Status';
COMMENT ON COLUMN "Nova".t0038.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0038_employee_id ON "Nova".t0038(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0038_payroll_period_id ON "Nova".t0038(payroll_period_id);
CREATE INDEX IF NOT EXISTS idx_t0038_status ON "Nova".t0038(status);
CREATE INDEX IF NOT EXISTS idx_t0038_active ON "Nova".t0038(is_active);

-- Job Openings
CREATE TABLE IF NOT EXISTS "Nova".t0039 (
    id SERIAL PRIMARY KEY,
    job_code VARCHAR(30),
    job_title VARCHAR(200),
    department_id INT,
    designation_id INT,
    openings INT,
    description TEXT,
    requirements TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    posted_date DATE,
    closing_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0039 IS 'Job Openings';
COMMENT ON COLUMN "Nova".t0039.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0039.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0039.designation_id IS 'Reference to Designation';
COMMENT ON COLUMN "Nova".t0039.status IS 'Status';
COMMENT ON COLUMN "Nova".t0039.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0039_department_id ON "Nova".t0039(department_id);
CREATE INDEX IF NOT EXISTS idx_t0039_designation_id ON "Nova".t0039(designation_id);
CREATE INDEX IF NOT EXISTS idx_t0039_status ON "Nova".t0039(status);
CREATE INDEX IF NOT EXISTS idx_t0039_active ON "Nova".t0039(is_active);

-- Job Candidates
CREATE TABLE IF NOT EXISTS "Nova".t0040 (
    id SERIAL PRIMARY KEY,
    candidate_code VARCHAR(30),
    full_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(200),
    job_opening_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    resume_path TEXT,
    notes TEXT,
    applied_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0040 IS 'Job Candidates';
COMMENT ON COLUMN "Nova".t0040.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0040.job_opening_id IS 'Reference to Job_Opening';
COMMENT ON COLUMN "Nova".t0040.status IS 'Status';
COMMENT ON COLUMN "Nova".t0040.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0040_job_opening_id ON "Nova".t0040(job_opening_id);
CREATE INDEX IF NOT EXISTS idx_t0040_status ON "Nova".t0040(status);
CREATE INDEX IF NOT EXISTS idx_t0040_active ON "Nova".t0040(is_active);

-- Maintenance Assets
CREATE TABLE IF NOT EXISTS "Nova".t0041 (
    id SERIAL PRIMARY KEY,
    asset_code VARCHAR(30),
    asset_name VARCHAR(200),
    asset_type VARCHAR(30),
    asset_model VARCHAR(200),
    serial_no VARCHAR(200),
    location VARCHAR(200),
    department_id INT,
    purchase_date DATE,
    purchase_cost NUMERIC(12,2),
    useful_life INT,
    warranty_expiry VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0041 IS 'Maintenance Assets';
COMMENT ON COLUMN "Nova".t0041.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0041.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0041.status IS 'Status';
COMMENT ON COLUMN "Nova".t0041.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0041_department_id ON "Nova".t0041(department_id);
CREATE INDEX IF NOT EXISTS idx_t0041_status ON "Nova".t0041(status);
CREATE INDEX IF NOT EXISTS idx_t0041_active ON "Nova".t0041(is_active);

-- Maintenance Schedules
CREATE TABLE IF NOT EXISTS "Nova".t0042 (
    id SERIAL PRIMARY KEY,
    asset_id INT,
    schedule_code VARCHAR(30),
    schedule_name VARCHAR(200),
    frequency_type VARCHAR(30),
    frequency_value NUMERIC(12,2),
    last_maintenance DATE,
    next_maintenance DATE,
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0042 IS 'Maintenance Schedules';
COMMENT ON COLUMN "Nova".t0042.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0042.asset_id IS 'Reference to Asset';
COMMENT ON COLUMN "Nova".t0042.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0042_asset_id ON "Nova".t0042(asset_id);
CREATE INDEX IF NOT EXISTS idx_t0042_active ON "Nova".t0042(is_active);

-- Maintenance Work Orders
CREATE TABLE IF NOT EXISTS "Nova".t0043 (
    id SERIAL PRIMARY KEY,
    asset_id INT,
    schedule_id INT,
    work_order_code VARCHAR(30),
    description TEXT,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    scheduled_date DATE,
    completed_date DATE,
    cost NUMERIC(12,2),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0043 IS 'Maintenance Work Orders';
COMMENT ON COLUMN "Nova".t0043.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0043.asset_id IS 'Reference to Asset';
COMMENT ON COLUMN "Nova".t0043.schedule_id IS 'Reference to Schedule';
COMMENT ON COLUMN "Nova".t0043.status IS 'Status';
COMMENT ON COLUMN "Nova".t0043.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0043_asset_id ON "Nova".t0043(asset_id);
CREATE INDEX IF NOT EXISTS idx_t0043_schedule_id ON "Nova".t0043(schedule_id);
CREATE INDEX IF NOT EXISTS idx_t0043_status ON "Nova".t0043(status);
CREATE INDEX IF NOT EXISTS idx_t0043_active ON "Nova".t0043(is_active);

-- Projects
CREATE TABLE IF NOT EXISTS "Nova".t0044 (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(30),
    project_name VARCHAR(200),
    description TEXT,
    department_id INT,
    manager_id INT,
    start_date DATE,
    end_date DATE,
    budget NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0044 IS 'Projects';
COMMENT ON COLUMN "Nova".t0044.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0044.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0044.manager_id IS 'Reference to Manager';
COMMENT ON COLUMN "Nova".t0044.status IS 'Status';
COMMENT ON COLUMN "Nova".t0044.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0044_department_id ON "Nova".t0044(department_id);
CREATE INDEX IF NOT EXISTS idx_t0044_manager_id ON "Nova".t0044(manager_id);
CREATE INDEX IF NOT EXISTS idx_t0044_status ON "Nova".t0044(status);
CREATE INDEX IF NOT EXISTS idx_t0044_active ON "Nova".t0044(is_active);

-- Project Tasks
CREATE TABLE IF NOT EXISTS "Nova".t0045 (
    id SERIAL PRIMARY KEY,
    project_id INT,
    task_code VARCHAR(30),
    task_name VARCHAR(200),
    description TEXT,
    assigned_to VARCHAR(200),
    start_date DATE,
    end_date DATE,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    estimated_hours NUMERIC(8,2),
    actual_hours NUMERIC(8,2),
    parent_task_id INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0045 IS 'Project Tasks';
COMMENT ON COLUMN "Nova".t0045.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0045.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0045.status IS 'Status';
COMMENT ON COLUMN "Nova".t0045.parent_task_id IS 'Reference to Parent_Task';
COMMENT ON COLUMN "Nova".t0045.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0045_project_id ON "Nova".t0045(project_id);
CREATE INDEX IF NOT EXISTS idx_t0045_status ON "Nova".t0045(status);
CREATE INDEX IF NOT EXISTS idx_t0045_parent_task_id ON "Nova".t0045(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_t0045_active ON "Nova".t0045(is_active);

-- Project Resource Allocations
CREATE TABLE IF NOT EXISTS "Nova".t0046 (
    id SERIAL PRIMARY KEY,
    project_id INT,
    employee_id INT,
    allocation_pct NUMERIC(5,2),
    start_date DATE,
    end_date DATE,
    role VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0046 IS 'Project Resource Allocations';
COMMENT ON COLUMN "Nova".t0046.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0046.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0046.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0046.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0046_project_id ON "Nova".t0046(project_id);
CREATE INDEX IF NOT EXISTS idx_t0046_employee_id ON "Nova".t0046(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0046_active ON "Nova".t0046(is_active);

-- Project Timesheets
CREATE TABLE IF NOT EXISTS "Nova".t0047 (
    id SERIAL PRIMARY KEY,
    employee_id INT,
    project_id INT,
    task_id INT,
    date DATE,
    hours NUMERIC(8,2),
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    approved_by VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0047 IS 'Project Timesheets';
COMMENT ON COLUMN "Nova".t0047.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0047.employee_id IS 'Reference to Employee';
COMMENT ON COLUMN "Nova".t0047.project_id IS 'Reference to Project';
COMMENT ON COLUMN "Nova".t0047.task_id IS 'Reference to Task';
COMMENT ON COLUMN "Nova".t0047.status IS 'Status';
COMMENT ON COLUMN "Nova".t0047.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0047_employee_id ON "Nova".t0047(employee_id);
CREATE INDEX IF NOT EXISTS idx_t0047_project_id ON "Nova".t0047(project_id);
CREATE INDEX IF NOT EXISTS idx_t0047_task_id ON "Nova".t0047(task_id);
CREATE INDEX IF NOT EXISTS idx_t0047_status ON "Nova".t0047(status);
CREATE INDEX IF NOT EXISTS idx_t0047_active ON "Nova".t0047(is_active);

-- Service Requests
CREATE TABLE IF NOT EXISTS "Nova".t0048 (
    id SERIAL PRIMARY KEY,
    request_code VARCHAR(30),
    subject VARCHAR(200),
    description TEXT,
    customer_id INT,
    priority VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    resolution TEXT,
    resolved_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0048 IS 'Service Requests';
COMMENT ON COLUMN "Nova".t0048.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0048.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0048.status IS 'Status';
COMMENT ON COLUMN "Nova".t0048.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0048_customer_id ON "Nova".t0048(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0048_status ON "Nova".t0048(status);
CREATE INDEX IF NOT EXISTS idx_t0048_active ON "Nova".t0048(is_active);

-- Customer Contracts
CREATE TABLE IF NOT EXISTS "Nova".t0049 (
    id SERIAL PRIMARY KEY,
    contract_code VARCHAR(30),
    contract_name VARCHAR(200),
    customer_id INT,
    contract_type VARCHAR(30),
    start_date DATE,
    end_date DATE,
    value NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0049 IS 'Customer Contracts';
COMMENT ON COLUMN "Nova".t0049.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0049.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0049.status IS 'Status';
COMMENT ON COLUMN "Nova".t0049.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0049_customer_id ON "Nova".t0049(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0049_status ON "Nova".t0049(status);
CREATE INDEX IF NOT EXISTS idx_t0049_active ON "Nova".t0049(is_active);

-- SLA Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0050 (
    id SERIAL PRIMARY KEY,
    contract_id INT,
    sla_code VARCHAR(30),
    sla_name VARCHAR(200),
    response_time NUMERIC(12,2),
    resolution_time NUMERIC(12,2),
    penalty_rate NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0050 IS 'SLA Definitions';
COMMENT ON COLUMN "Nova".t0050.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0050.contract_id IS 'Reference to Contract';
COMMENT ON COLUMN "Nova".t0050.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0050_contract_id ON "Nova".t0050(contract_id);
CREATE INDEX IF NOT EXISTS idx_t0050_active ON "Nova".t0050(is_active);

-- Search Index
CREATE TABLE IF NOT EXISTS "Nova".t0051 (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(30),
    entity_id INT,
    keywords TEXT,
    search_content TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0051 IS 'Search Index';
COMMENT ON COLUMN "Nova".t0051.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0051.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0051.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0051_entity_id ON "Nova".t0051(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0051_active ON "Nova".t0051(is_active);

-- KPI Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0052 (
    id SERIAL PRIMARY KEY,
    kpi_code VARCHAR(30),
    kpi_name VARCHAR(200),
    category VARCHAR(200),
    metric_unit VARCHAR(200),
    target_value NUMERIC(12,2),
    formula VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0052 IS 'KPI Definitions';
COMMENT ON COLUMN "Nova".t0052.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0052.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0052_active ON "Nova".t0052(is_active);

-- KPI Values
CREATE TABLE IF NOT EXISTS "Nova".t0053 (
    id SERIAL PRIMARY KEY,
    kpi_id INT,
    period VARCHAR(200),
    period_type VARCHAR(30),
    actual_value NUMERIC(12,2),
    target_value NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0053 IS 'KPI Values';
COMMENT ON COLUMN "Nova".t0053.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0053.kpi_id IS 'Reference to Kpi';
COMMENT ON COLUMN "Nova".t0053.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0053_kpi_id ON "Nova".t0053(kpi_id);
CREATE INDEX IF NOT EXISTS idx_t0053_active ON "Nova".t0053(is_active);

-- BI Dashboards
CREATE TABLE IF NOT EXISTS "Nova".t0054 (
    id SERIAL PRIMARY KEY,
    dashboard_code VARCHAR(30),
    dashboard_name VARCHAR(200),
    owner_id INT,
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0054 IS 'BI Dashboards';
COMMENT ON COLUMN "Nova".t0054.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0054.owner_id IS 'Reference to Owner';
COMMENT ON COLUMN "Nova".t0054.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0054_owner_id ON "Nova".t0054(owner_id);
CREATE INDEX IF NOT EXISTS idx_t0054_active ON "Nova".t0054(is_active);

-- Dashboard Widgets
CREATE TABLE IF NOT EXISTS "Nova".t0055 (
    id SERIAL PRIMARY KEY,
    dashboard_id INT,
    widget_type VARCHAR(30),
    title VARCHAR(200),
    config JSONB,
    position INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0055 IS 'Dashboard Widgets';
COMMENT ON COLUMN "Nova".t0055.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0055.dashboard_id IS 'Reference to Dashboard';
COMMENT ON COLUMN "Nova".t0055.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0055_dashboard_id ON "Nova".t0055(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_t0055_active ON "Nova".t0055(is_active);

-- API Keys
CREATE TABLE IF NOT EXISTS "Nova".t0056 (
    id SERIAL PRIMARY KEY,
    key_name VARCHAR(200),
    api_key VARCHAR(255),
    client_id INT,
    permissions TEXT[],
    expires_at DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0056 IS 'API Keys';
COMMENT ON COLUMN "Nova".t0056.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0056.client_id IS 'Reference to Client';
COMMENT ON COLUMN "Nova".t0056.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0056_client_id ON "Nova".t0056(client_id);
CREATE INDEX IF NOT EXISTS idx_t0056_active ON "Nova".t0056(is_active);

-- Integration Configurations
CREATE TABLE IF NOT EXISTS "Nova".t0057 (
    id SERIAL PRIMARY KEY,
    integration_code VARCHAR(30),
    integration_name VARCHAR(200),
    provider VARCHAR(200),
    config JSONB,
    credentials JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0057 IS 'Integration Configurations';
COMMENT ON COLUMN "Nova".t0057.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0057.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0057_active ON "Nova".t0057(is_active);

-- Integration Sync Logs
CREATE TABLE IF NOT EXISTS "Nova".t0058 (
    id SERIAL PRIMARY KEY,
    integration_id INT,
    entity_type VARCHAR(30),
    action VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    message TEXT,
    synced_at DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0058 IS 'Integration Sync Logs';
COMMENT ON COLUMN "Nova".t0058.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0058.integration_id IS 'Reference to Integration';
COMMENT ON COLUMN "Nova".t0058.status IS 'Status';
COMMENT ON COLUMN "Nova".t0058.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0058_integration_id ON "Nova".t0058(integration_id);
CREATE INDEX IF NOT EXISTS idx_t0058_status ON "Nova".t0058(status);
CREATE INDEX IF NOT EXISTS idx_t0058_active ON "Nova".t0058(is_active);

-- Enterprise Tenants
CREATE TABLE IF NOT EXISTS "Nova".t0059 (
    id SERIAL PRIMARY KEY,
    tenant_code VARCHAR(30),
    tenant_name VARCHAR(200),
    domain VARCHAR(200),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0059 IS 'Enterprise Tenants';
COMMENT ON COLUMN "Nova".t0059.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0059.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0059_active ON "Nova".t0059(is_active);

-- Workflow Definitions
CREATE TABLE IF NOT EXISTS "Nova".t0060 (
    id SERIAL PRIMARY KEY,
    workflow_code VARCHAR(30),
    workflow_name VARCHAR(200),
    entity_type VARCHAR(30),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0060 IS 'Workflow Definitions';
COMMENT ON COLUMN "Nova".t0060.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0060.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0060_active ON "Nova".t0060(is_active);

-- Workflow Instances
CREATE TABLE IF NOT EXISTS "Nova".t0061 (
    id SERIAL PRIMARY KEY,
    workflow_id INT,
    entity_type VARCHAR(30),
    entity_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    current_step VARCHAR(200),
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0061 IS 'Workflow Instances';
COMMENT ON COLUMN "Nova".t0061.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0061.workflow_id IS 'Reference to Workflow';
COMMENT ON COLUMN "Nova".t0061.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0061.status IS 'Status';
COMMENT ON COLUMN "Nova".t0061.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0061_workflow_id ON "Nova".t0061(workflow_id);
CREATE INDEX IF NOT EXISTS idx_t0061_entity_id ON "Nova".t0061(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0061_status ON "Nova".t0061(status);
CREATE INDEX IF NOT EXISTS idx_t0061_active ON "Nova".t0061(is_active);

-- Enterprise Documents
CREATE TABLE IF NOT EXISTS "Nova".t0062 (
    id SERIAL PRIMARY KEY,
    document_code VARCHAR(30),
    document_name VARCHAR(200),
    entity_type VARCHAR(30),
    entity_id INT,
    file_path TEXT,
    file_type VARCHAR(30),
    file_size NUMERIC(12,2),
    version NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0062 IS 'Enterprise Documents';
COMMENT ON COLUMN "Nova".t0062.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0062.entity_id IS 'Reference to Entity';
COMMENT ON COLUMN "Nova".t0062.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0062_entity_id ON "Nova".t0062(entity_id);
CREATE INDEX IF NOT EXISTS idx_t0062_active ON "Nova".t0062(is_active);

-- Compliance Rules
CREATE TABLE IF NOT EXISTS "Nova".t0063 (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(30),
    rule_name VARCHAR(200),
    category VARCHAR(200),
    description TEXT,
    config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0063 IS 'Compliance Rules';
COMMENT ON COLUMN "Nova".t0063.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0063.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0063_active ON "Nova".t0063(is_active);

-- Stock Movements
CREATE TABLE IF NOT EXISTS "Nova".t0064 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    warehouse_id INT,
    movement_type VARCHAR(30),
    reference_type VARCHAR(30),
    reference_id INT,
    qty_change NUMERIC(12,2),
    balance_after NUMERIC(12,2),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0064 IS 'Stock Movements';
COMMENT ON COLUMN "Nova".t0064.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0064.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0064.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0064.reference_id IS 'Reference to Reference';
COMMENT ON COLUMN "Nova".t0064.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0064_product_id ON "Nova".t0064(product_id);
CREATE INDEX IF NOT EXISTS idx_t0064_warehouse_id ON "Nova".t0064(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0064_reference_id ON "Nova".t0064(reference_id);
CREATE INDEX IF NOT EXISTS idx_t0064_active ON "Nova".t0064(is_active);

-- Bill of Materials
CREATE TABLE IF NOT EXISTS "Nova".t0065 (
    id SERIAL PRIMARY KEY,
    bom_code VARCHAR(30),
    bom_name VARCHAR(200),
    product_id INT,
    quantity NUMERIC(12,2),
    version NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0065 IS 'Bill of Materials';
COMMENT ON COLUMN "Nova".t0065.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0065.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0065.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0065_product_id ON "Nova".t0065(product_id);
CREATE INDEX IF NOT EXISTS idx_t0065_active ON "Nova".t0065(is_active);

-- BOM Lines
CREATE TABLE IF NOT EXISTS "Nova".t0066 (
    id SERIAL PRIMARY KEY,
    bom_id INT,
    component_id INT,
    component_name VARCHAR(200),
    quantity NUMERIC(12,2),
    uom_id INT,
    scrap_pct NUMERIC(5,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0066 IS 'BOM Lines';
COMMENT ON COLUMN "Nova".t0066.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0066.bom_id IS 'Reference to Bom';
COMMENT ON COLUMN "Nova".t0066.component_id IS 'Reference to Component';
COMMENT ON COLUMN "Nova".t0066.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0066.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0066_bom_id ON "Nova".t0066(bom_id);
CREATE INDEX IF NOT EXISTS idx_t0066_component_id ON "Nova".t0066(component_id);
CREATE INDEX IF NOT EXISTS idx_t0066_uom_id ON "Nova".t0066(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0066_active ON "Nova".t0066(is_active);

-- Sales Quotations
CREATE TABLE IF NOT EXISTS "Nova".t0067 (
    id SERIAL PRIMARY KEY,
    quote_number VARCHAR(200),
    customer_id INT,
    quote_date DATE,
    valid_until DATE,
    subtotal NUMERIC(12,2),
    tax NUMERIC(12,2),
    grand_total NUMERIC(12,2),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0067 IS 'Sales Quotations';
COMMENT ON COLUMN "Nova".t0067.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0067.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0067.status IS 'Status';
COMMENT ON COLUMN "Nova".t0067.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0067_customer_id ON "Nova".t0067(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0067_status ON "Nova".t0067(status);
CREATE INDEX IF NOT EXISTS idx_t0067_active ON "Nova".t0067(is_active);

-- Sales Quotation Lines
CREATE TABLE IF NOT EXISTS "Nova".t0068 (
    id SERIAL PRIMARY KEY,
    quotation_id INT,
    product_id INT,
    product_name VARCHAR(200),
    uom_id INT,
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0068 IS 'Sales Quotation Lines';
COMMENT ON COLUMN "Nova".t0068.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0068.quotation_id IS 'Reference to Quotation';
COMMENT ON COLUMN "Nova".t0068.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0068.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0068.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0068_quotation_id ON "Nova".t0068(quotation_id);
CREATE INDEX IF NOT EXISTS idx_t0068_product_id ON "Nova".t0068(product_id);
CREATE INDEX IF NOT EXISTS idx_t0068_uom_id ON "Nova".t0068(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0068_active ON "Nova".t0068(is_active);

-- Purchase Requisitions
CREATE TABLE IF NOT EXISTS "Nova".t0069 (
    id SERIAL PRIMARY KEY,
    req_number VARCHAR(200),
    title VARCHAR(200),
    description TEXT,
    department_id INT,
    requested_by VARCHAR(200),
    approved_by VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    priority VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0069 IS 'Purchase Requisitions';
COMMENT ON COLUMN "Nova".t0069.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0069.department_id IS 'Reference to Department';
COMMENT ON COLUMN "Nova".t0069.status IS 'Status';
COMMENT ON COLUMN "Nova".t0069.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0069_department_id ON "Nova".t0069(department_id);
CREATE INDEX IF NOT EXISTS idx_t0069_status ON "Nova".t0069(status);
CREATE INDEX IF NOT EXISTS idx_t0069_active ON "Nova".t0069(is_active);

-- Purchase Requisition Lines
CREATE TABLE IF NOT EXISTS "Nova".t0070 (
    id SERIAL PRIMARY KEY,
    requisition_id INT,
    product_id INT,
    description TEXT,
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    uom_id INT,
    expected_date DATE,
    notes TEXT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0070 IS 'Purchase Requisition Lines';
COMMENT ON COLUMN "Nova".t0070.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0070.requisition_id IS 'Reference to Requisition';
COMMENT ON COLUMN "Nova".t0070.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0070.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0070.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0070_requisition_id ON "Nova".t0070(requisition_id);
CREATE INDEX IF NOT EXISTS idx_t0070_product_id ON "Nova".t0070(product_id);
CREATE INDEX IF NOT EXISTS idx_t0070_uom_id ON "Nova".t0070(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0070_active ON "Nova".t0070(is_active);

-- Request for Quotations (RFQ)
CREATE TABLE IF NOT EXISTS "Nova".t0071 (
    id SERIAL PRIMARY KEY,
    rfq_number VARCHAR(200),
    title VARCHAR(200),
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    due_date DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0071 IS 'Request for Quotations (RFQ)';
COMMENT ON COLUMN "Nova".t0071.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0071.status IS 'Status';
COMMENT ON COLUMN "Nova".t0071.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0071_status ON "Nova".t0071(status);
CREATE INDEX IF NOT EXISTS idx_t0071_active ON "Nova".t0071(is_active);

-- RFQ Lines
CREATE TABLE IF NOT EXISTS "Nova".t0072 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    product_id INT,
    description TEXT,
    qty NUMERIC(12,2),
    uom_id INT,
    line_number NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0072 IS 'RFQ Lines';
COMMENT ON COLUMN "Nova".t0072.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0072.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0072.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0072.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0072.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0072_rfq_id ON "Nova".t0072(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0072_product_id ON "Nova".t0072(product_id);
CREATE INDEX IF NOT EXISTS idx_t0072_uom_id ON "Nova".t0072(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0072_active ON "Nova".t0072(is_active);

-- RFQ Vendors
CREATE TABLE IF NOT EXISTS "Nova".t0073 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    vendor_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0073 IS 'RFQ Vendors';
COMMENT ON COLUMN "Nova".t0073.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0073.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0073.vendor_id IS 'Reference to Vendor';
COMMENT ON COLUMN "Nova".t0073.status IS 'Status';
COMMENT ON COLUMN "Nova".t0073.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0073_rfq_id ON "Nova".t0073(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0073_vendor_id ON "Nova".t0073(vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0073_status ON "Nova".t0073(status);
CREATE INDEX IF NOT EXISTS idx_t0073_active ON "Nova".t0073(is_active);

-- RFQ Vendor Quotes
CREATE TABLE IF NOT EXISTS "Nova".t0074 (
    id SERIAL PRIMARY KEY,
    rfq_id INT,
    vendor_id INT,
    rfq_vendor_id INT,
    line_id INT,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    delivery_days INT,
    currency VARCHAR(30),
    valid_until DATE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0074 IS 'RFQ Vendor Quotes';
COMMENT ON COLUMN "Nova".t0074.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0074.rfq_id IS 'Reference to Rfq';
COMMENT ON COLUMN "Nova".t0074.vendor_id IS 'Reference to Vendor';
COMMENT ON COLUMN "Nova".t0074.rfq_vendor_id IS 'Reference to Rfq_Vendor';
COMMENT ON COLUMN "Nova".t0074.line_id IS 'Reference to Line';
COMMENT ON COLUMN "Nova".t0074.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0074_rfq_id ON "Nova".t0074(rfq_id);
CREATE INDEX IF NOT EXISTS idx_t0074_vendor_id ON "Nova".t0074(vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0074_rfq_vendor_id ON "Nova".t0074(rfq_vendor_id);
CREATE INDEX IF NOT EXISTS idx_t0074_line_id ON "Nova".t0074(line_id);
CREATE INDEX IF NOT EXISTS idx_t0074_active ON "Nova".t0074(is_active);

-- Goods Receipts
CREATE TABLE IF NOT EXISTS "Nova".t0075 (
    id SERIAL PRIMARY KEY,
    receipt_number VARCHAR(200),
    purchase_order_id INT,
    receipt_date DATE,
    warehouse_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0075 IS 'Goods Receipts';
COMMENT ON COLUMN "Nova".t0075.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0075.purchase_order_id IS 'Reference to Purchase_Order';
COMMENT ON COLUMN "Nova".t0075.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0075.status IS 'Status';
COMMENT ON COLUMN "Nova".t0075.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0075_purchase_order_id ON "Nova".t0075(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0075_warehouse_id ON "Nova".t0075(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0075_status ON "Nova".t0075(status);
CREATE INDEX IF NOT EXISTS idx_t0075_active ON "Nova".t0075(is_active);

-- Goods Receipt Lines
CREATE TABLE IF NOT EXISTS "Nova".t0076 (
    id SERIAL PRIMARY KEY,
    receipt_id INT,
    purchase_order_line_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty_received NUMERIC(12,2),
    qty_ordered NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0076 IS 'Goods Receipt Lines';
COMMENT ON COLUMN "Nova".t0076.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0076.receipt_id IS 'Reference to Receipt';
COMMENT ON COLUMN "Nova".t0076.purchase_order_line_id IS 'Reference to Purchase_Order_Line';
COMMENT ON COLUMN "Nova".t0076.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0076.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0076.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0076_receipt_id ON "Nova".t0076(receipt_id);
CREATE INDEX IF NOT EXISTS idx_t0076_purchase_order_line_id ON "Nova".t0076(purchase_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0076_product_id ON "Nova".t0076(product_id);
CREATE INDEX IF NOT EXISTS idx_t0076_uom_id ON "Nova".t0076(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0076_active ON "Nova".t0076(is_active);

-- Sales Deliveries
CREATE TABLE IF NOT EXISTS "Nova".t0077 (
    id SERIAL PRIMARY KEY,
    delivery_number VARCHAR(200),
    sales_order_id INT,
    delivery_date DATE,
    warehouse_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0077 IS 'Sales Deliveries';
COMMENT ON COLUMN "Nova".t0077.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0077.sales_order_id IS 'Reference to Sales_Order';
COMMENT ON COLUMN "Nova".t0077.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0077.status IS 'Status';
COMMENT ON COLUMN "Nova".t0077.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0077_sales_order_id ON "Nova".t0077(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0077_warehouse_id ON "Nova".t0077(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0077_status ON "Nova".t0077(status);
CREATE INDEX IF NOT EXISTS idx_t0077_active ON "Nova".t0077(is_active);

-- Sales Delivery Lines
CREATE TABLE IF NOT EXISTS "Nova".t0078 (
    id SERIAL PRIMARY KEY,
    delivery_id INT,
    sales_order_line_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty_shipped NUMERIC(12,2),
    qty_ordered NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0078 IS 'Sales Delivery Lines';
COMMENT ON COLUMN "Nova".t0078.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0078.delivery_id IS 'Reference to Delivery';
COMMENT ON COLUMN "Nova".t0078.sales_order_line_id IS 'Reference to Sales_Order_Line';
COMMENT ON COLUMN "Nova".t0078.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0078.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0078.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0078_delivery_id ON "Nova".t0078(delivery_id);
CREATE INDEX IF NOT EXISTS idx_t0078_sales_order_line_id ON "Nova".t0078(sales_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0078_product_id ON "Nova".t0078(product_id);
CREATE INDEX IF NOT EXISTS idx_t0078_uom_id ON "Nova".t0078(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0078_active ON "Nova".t0078(is_active);

-- Sales Returns
CREATE TABLE IF NOT EXISTS "Nova".t0079 (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(200),
    sales_order_id INT,
    customer_id INT,
    return_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    reason VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0079 IS 'Sales Returns';
COMMENT ON COLUMN "Nova".t0079.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0079.sales_order_id IS 'Reference to Sales_Order';
COMMENT ON COLUMN "Nova".t0079.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0079.status IS 'Status';
COMMENT ON COLUMN "Nova".t0079.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0079_sales_order_id ON "Nova".t0079(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_t0079_customer_id ON "Nova".t0079(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0079_status ON "Nova".t0079(status);
CREATE INDEX IF NOT EXISTS idx_t0079_active ON "Nova".t0079(is_active);

-- Sales Return Lines
CREATE TABLE IF NOT EXISTS "Nova".t0080 (
    id SERIAL PRIMARY KEY,
    return_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0080 IS 'Sales Return Lines';
COMMENT ON COLUMN "Nova".t0080.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0080.return_id IS 'Reference to Return';
COMMENT ON COLUMN "Nova".t0080.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0080.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0080.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0080_return_id ON "Nova".t0080(return_id);
CREATE INDEX IF NOT EXISTS idx_t0080_product_id ON "Nova".t0080(product_id);
CREATE INDEX IF NOT EXISTS idx_t0080_uom_id ON "Nova".t0080(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0080_active ON "Nova".t0080(is_active);

-- Purchase Returns
CREATE TABLE IF NOT EXISTS "Nova".t0081 (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(200),
    purchase_order_id INT,
    supplier_id INT,
    return_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    reason VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0081 IS 'Purchase Returns';
COMMENT ON COLUMN "Nova".t0081.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0081.purchase_order_id IS 'Reference to Purchase_Order';
COMMENT ON COLUMN "Nova".t0081.supplier_id IS 'Reference to Supplier';
COMMENT ON COLUMN "Nova".t0081.status IS 'Status';
COMMENT ON COLUMN "Nova".t0081.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0081_purchase_order_id ON "Nova".t0081(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_t0081_supplier_id ON "Nova".t0081(supplier_id);
CREATE INDEX IF NOT EXISTS idx_t0081_status ON "Nova".t0081(status);
CREATE INDEX IF NOT EXISTS idx_t0081_active ON "Nova".t0081(is_active);

-- Purchase Return Lines
CREATE TABLE IF NOT EXISTS "Nova".t0082 (
    id SERIAL PRIMARY KEY,
    return_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    uom_id INT,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0082 IS 'Purchase Return Lines';
COMMENT ON COLUMN "Nova".t0082.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0082.return_id IS 'Reference to Return';
COMMENT ON COLUMN "Nova".t0082.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0082.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0082.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0082_return_id ON "Nova".t0082(return_id);
CREATE INDEX IF NOT EXISTS idx_t0082_product_id ON "Nova".t0082(product_id);
CREATE INDEX IF NOT EXISTS idx_t0082_uom_id ON "Nova".t0082(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0082_active ON "Nova".t0082(is_active);

-- Price List Items
CREATE TABLE IF NOT EXISTS "Nova".t0084 (
    id SERIAL PRIMARY KEY,
    price_list_id INT,
    product_id INT,
    unit_price NUMERIC(12,2),
    min_qty INT,
    uom_id INT,
    effective_from DATE,
    effective_to DATE,
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0084 IS 'Price List Items';
COMMENT ON COLUMN "Nova".t0084.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0084.price_list_id IS 'Reference to Price_List';
COMMENT ON COLUMN "Nova".t0084.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0084.uom_id IS 'Reference to Uom';
COMMENT ON COLUMN "Nova".t0084.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0084_price_list_id ON "Nova".t0084(price_list_id);
CREATE INDEX IF NOT EXISTS idx_t0084_product_id ON "Nova".t0084(product_id);
CREATE INDEX IF NOT EXISTS idx_t0084_uom_id ON "Nova".t0084(uom_id);
CREATE INDEX IF NOT EXISTS idx_t0084_active ON "Nova".t0084(is_active);

-- Tax Rules
CREATE TABLE IF NOT EXISTS "Nova".t0086 (
    id SERIAL PRIMARY KEY,
    tax_rate_id INT,
    applies_to VARCHAR(200),
    target_id INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0086 IS 'Tax Rules';
COMMENT ON COLUMN "Nova".t0086.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0086.tax_rate_id IS 'Reference to Tax_Rate';
COMMENT ON COLUMN "Nova".t0086.target_id IS 'Reference to Target';
COMMENT ON COLUMN "Nova".t0086.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0086_tax_rate_id ON "Nova".t0086(tax_rate_id);
CREATE INDEX IF NOT EXISTS idx_t0086_target_id ON "Nova".t0086(target_id);
CREATE INDEX IF NOT EXISTS idx_t0086_active ON "Nova".t0086(is_active);

-- Serial Numbers
CREATE TABLE IF NOT EXISTS "Nova".t0087 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    serial_number VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    warehouse_id INT,
    purchase_order_line_id INT,
    sales_order_line_id INT,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0087 IS 'Serial Numbers';
COMMENT ON COLUMN "Nova".t0087.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0087.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0087.status IS 'Status';
COMMENT ON COLUMN "Nova".t0087.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0087.purchase_order_line_id IS 'Reference to Purchase_Order_Line';
COMMENT ON COLUMN "Nova".t0087.sales_order_line_id IS 'Reference to Sales_Order_Line';
COMMENT ON COLUMN "Nova".t0087.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0087_product_id ON "Nova".t0087(product_id);
CREATE INDEX IF NOT EXISTS idx_t0087_status ON "Nova".t0087(status);
CREATE INDEX IF NOT EXISTS idx_t0087_warehouse_id ON "Nova".t0087(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0087_purchase_order_line_id ON "Nova".t0087(purchase_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0087_sales_order_line_id ON "Nova".t0087(sales_order_line_id);
CREATE INDEX IF NOT EXISTS idx_t0087_active ON "Nova".t0087(is_active);

-- Batch Numbers
CREATE TABLE IF NOT EXISTS "Nova".t0088 (
    id SERIAL PRIMARY KEY,
    product_id INT,
    batch_number VARCHAR(255),
    expiry_date DATE,
    manufacturing_date DATE,
    quantity NUMERIC(12,2),
    warehouse_id INT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0088 IS 'Batch Numbers';
COMMENT ON COLUMN "Nova".t0088.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0088.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0088.warehouse_id IS 'Reference to Warehouse';
COMMENT ON COLUMN "Nova".t0088.status IS 'Status';
COMMENT ON COLUMN "Nova".t0088.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0088_product_id ON "Nova".t0088(product_id);
CREATE INDEX IF NOT EXISTS idx_t0088_warehouse_id ON "Nova".t0088(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_t0088_status ON "Nova".t0088(status);
CREATE INDEX IF NOT EXISTS idx_t0088_active ON "Nova".t0088(is_active);

-- Journal Entry Lines
CREATE TABLE IF NOT EXISTS "Nova".t0089 (
    id SERIAL PRIMARY KEY,
    journal_entry_id INT,
    account_id INT,
    debit NUMERIC(12,2),
    credit NUMERIC(12,2),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0089 IS 'Journal Entry Lines';
COMMENT ON COLUMN "Nova".t0089.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0089.journal_entry_id IS 'Reference to Journal_Entry';
COMMENT ON COLUMN "Nova".t0089.account_id IS 'Reference to Account';
COMMENT ON COLUMN "Nova".t0089.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0089_journal_entry_id ON "Nova".t0089(journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_t0089_account_id ON "Nova".t0089(account_id);
CREATE INDEX IF NOT EXISTS idx_t0089_active ON "Nova".t0089(is_active);

-- CRM Leads
CREATE TABLE IF NOT EXISTS "Nova".t0092 (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(200),
    last_name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(200),
    company VARCHAR(200),
    title VARCHAR(200),
    source VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0092 IS 'CRM Leads';
COMMENT ON COLUMN "Nova".t0092.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0092.status IS 'Status';
COMMENT ON COLUMN "Nova".t0092.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0092_status ON "Nova".t0092(status);
CREATE INDEX IF NOT EXISTS idx_t0092_active ON "Nova".t0092(is_active);

-- CRM Lead Activities
CREATE TABLE IF NOT EXISTS "Nova".t0093 (
    id SERIAL PRIMARY KEY,
    lead_id INT,
    activity_type VARCHAR(30),
    subject VARCHAR(200),
    description TEXT,
    activity_date DATE,
    completed VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0093 IS 'CRM Lead Activities';
COMMENT ON COLUMN "Nova".t0093.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0093.lead_id IS 'Reference to Lead';
COMMENT ON COLUMN "Nova".t0093.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0093_lead_id ON "Nova".t0093(lead_id);
CREATE INDEX IF NOT EXISTS idx_t0093_active ON "Nova".t0093(is_active);

-- CRM Opportunities
CREATE TABLE IF NOT EXISTS "Nova".t0094 (
    id SERIAL PRIMARY KEY,
    opportunity_name VARCHAR(200),
    lead_id INT,
    customer_id INT,
    stage VARCHAR(200),
    amount NUMERIC(12,2),
    probability NUMERIC(5,2),
    expected_close_date DATE,
    assigned_to VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0094 IS 'CRM Opportunities';
COMMENT ON COLUMN "Nova".t0094.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0094.lead_id IS 'Reference to Lead';
COMMENT ON COLUMN "Nova".t0094.customer_id IS 'Reference to Customer';
COMMENT ON COLUMN "Nova".t0094.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0094_lead_id ON "Nova".t0094(lead_id);
CREATE INDEX IF NOT EXISTS idx_t0094_customer_id ON "Nova".t0094(customer_id);
CREATE INDEX IF NOT EXISTS idx_t0094_active ON "Nova".t0094(is_active);

-- CRM Opportunity Lines
CREATE TABLE IF NOT EXISTS "Nova".t0095 (
    id SERIAL PRIMARY KEY,
    opportunity_id INT,
    product_id INT,
    product_name VARCHAR(200),
    qty NUMERIC(12,2),
    unit_price NUMERIC(12,2),
    line_total NUMERIC(12,2),
    line_number INT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by INT,
    update_number INT NOT NULL DEFAULT 1
);
COMMENT ON TABLE "Nova".t0095 IS 'CRM Opportunity Lines';
COMMENT ON COLUMN "Nova".t0095.id IS 'Primary key';
COMMENT ON COLUMN "Nova".t0095.opportunity_id IS 'Reference to Opportunity';
COMMENT ON COLUMN "Nova".t0095.product_id IS 'Reference to Product';
COMMENT ON COLUMN "Nova".t0095.is_active IS 'Active status flag';
CREATE INDEX IF NOT EXISTS idx_t0095_opportunity_id ON "Nova".t0095(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_t0095_product_id ON "Nova".t0095(product_id);
CREATE INDEX IF NOT EXISTS idx_t0095_active ON "Nova".t0095(is_active);

COMMIT;

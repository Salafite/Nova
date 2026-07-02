-- Nova ERP — Add missing order status enum values
BEGIN;

ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Confirmed';
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Draft';
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Processing';
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Delivered';
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'Invoiced';

COMMIT;

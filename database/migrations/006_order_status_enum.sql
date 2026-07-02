-- Nova ERP — Add missing order status enum values
BEGIN;

ALTER TYPE "Nova".order_status ADD VALUE IF NOT EXISTS 'Confirmed';
ALTER TYPE "Nova".order_status ADD VALUE IF NOT EXISTS 'Processing';
ALTER TYPE "Nova".order_status ADD VALUE IF NOT EXISTS 'Delivered';
ALTER TYPE "Nova".order_status ADD VALUE IF NOT EXISTS 'Invoiced';

COMMIT;

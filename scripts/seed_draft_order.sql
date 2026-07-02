-- Seed a Draft order for smoke-testing the confirm endpoint
-- Idempotent: creates a unique order each time

DO $$
DECLARE
  next_num INT;
  order_id INT;
BEGIN
  SELECT COALESCE(MAX(CAST(SPLIT_PART(order_number, '-', 3) AS INTEGER)), 0) + 1
    INTO next_num
    FROM "Nova".t0012
   WHERE order_number LIKE 'SO-DRAFT-%';

  INSERT INTO "Nova".t0012 (order_number, customer_id, warehouse_id, subtotal, tax, grand_total, status, notes)
  VALUES (CONCAT('SO-DRAFT-', LPAD(next_num::TEXT, 3, '0')), 1, 1, 250.00, 37.50, 287.50, 'Draft', 'Seeded draft order for confirm endpoint test')
  RETURNING id INTO order_id;

  INSERT INTO "Nova".t0013 (sales_order_id, product_id, uom_id, qty, unit_price, line_total)
  VALUES (order_id, 1, 1, 10, 25.00, 250.00);
END
$$;

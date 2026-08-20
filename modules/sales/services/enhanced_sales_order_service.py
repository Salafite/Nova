from decimal import Decimal
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.connection import get_connection, release_connection


def _to_decimal(value) -> Decimal:
    """Coerce a numeric input to Decimal without raising on mixed operand types."""
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return Decimal(0)


class EnhancedSalesOrderService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.line_repo = CrudRepository('T0013', ['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        self.price_list_item_repo = CrudRepository('T0084', ['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty'])
        self.tax_rate_repo = CrudRepository('T0085', ['id', 'name', 'code', 'rate', 'type'])

    def create_with_lines(self, order_data, lines, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            order = super().create(order_data, conn=conn)
            subtotal = Decimal(0)
            tax_rate_pct = _to_decimal(self._lookup_tax_rate(order_data.get('tax_rate_id'), conn=conn))
            price_list_id = order_data.get('price_list_id')

            for line_data in lines:
                unit_price = _to_decimal(self._resolve_unit_price(line_data, price_list_id, conn=conn))
                qty = _to_decimal(line_data.get('qty', 1))
                line_total = qty * unit_price
                subtotal += line_total
                self.line_repo.create({
                    'sales_order_id': order['id'],
                    'product_id': line_data.get('product_id'),
                    'product_name': line_data.get('product_name', ''),
                    'qty': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                    'line_number': line_data.get('line_number', 1),
                }, conn=conn)

            tax_amount = subtotal * tax_rate_pct / Decimal(100)
            result = super().update(order['id'], {
                'subtotal': subtotal,
                'tax': tax_amount,
                'grand_total': subtotal + tax_amount,
            }, conn=conn)
            if should_release:
                conn.commit()
            return result
        except Exception:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if should_release:
                release_connection(conn)

    def _lookup_tax_rate(self, tax_rate_id, conn=None):
        if not tax_rate_id:
            return 0
        tax_rate = self.tax_rate_repo.get(tax_rate_id, conn=conn)
        return tax_rate.get('rate', 0) if tax_rate else 0

    def _resolve_unit_price(self, line_data, price_list_id, conn=None):
        unit_price = line_data.get('unit_price', 0)
        if unit_price and unit_price > 0:
            return unit_price
        product_id = line_data.get('product_id')
        if not price_list_id or not product_id:
            return 0
        prices = self.price_list_item_repo.list(filters={
            'price_list_id': price_list_id,
            'product_id': product_id,
        }, conn=conn)
        return prices[0].get('unit_price', 0) if prices else 0
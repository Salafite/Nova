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
        self.line_repo = CrudRepository(
            'T0013',
            business_columns=[
                'id',
                'sales_order_id',
                'product_id',
                'product_name',
                'uom_id',
                'qty',
                'unit_price',
                'cost_price',
                'discount',
                'line_total',
                'line_number',
                'is_catch_weight',
                'pricing_uom_id',
                'unit_price_pricing_uom',
                'nominal_weight',
                'catch_weight_actual',
                'recalculated_total',
            ],
        )
        self.price_list_item_repo = CrudRepository('T0084', business_columns=['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty'])
        self.tax_rate_repo = CrudRepository('T0085', business_columns=['id', 'name', 'code', 'rate', 'type'])
        self.customer_repo = CrudRepository(
            'T0010',
            business_columns=['id', 'name', 'credit_limit', 'balance', 'payment_term_id'],
        )
        self.payment_term_repo = CrudRepository(
            'T0096',
            business_columns=[
                'id',
                'name',
                'code',
                'description',
                'due_days',
                'discount_percentage',
                'discount_days',
                'is_active',
                'is_default',
            ],
        )

    def create_with_lines(self, order_data, lines, conn=None):
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            if not order_data.get('payment_term_id') and order_data.get('customer_id'):
                try:
                    customer = self.customer_repo.get(order_data['customer_id'], conn=conn)
                    if customer and customer.get('payment_term_id'):
                        order_data['payment_term_id'] = customer['payment_term_id']
                except Exception:
                    pass

            if not order_data.get('payment_term_id'):
                try:
                    default_terms = self.payment_term_repo.list(filters={'is_default': True, 'is_active': True}, limit=1, conn=conn)
                    if default_terms and default_terms[0].get('id'):
                        order_data['payment_term_id'] = default_terms[0]['id']
                except Exception:
                    pass

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
                    'qty': float(qty),
                    'unit_price': float(unit_price),
                    'line_total': float(line_total),
                    'line_number': line_data.get('line_number', 1),
                    'is_catch_weight': line_data.get('is_catch_weight', False),
                    'pricing_uom_id': line_data.get('pricing_uom_id'),
                    'unit_price_pricing_uom': line_data.get('unit_price_pricing_uom'),
                    'nominal_weight': line_data.get('nominal_weight'),
                    'catch_weight_actual': line_data.get('catch_weight_actual'),
                    'recalculated_total': line_data.get('recalculated_total'),
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
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository


class EnhancedSalesOrderService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.line_repo = CrudRepository('T0013', ['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        self.price_list_item_repo = CrudRepository('T0084', ['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty'])
        self.tax_rate_repo = CrudRepository('T0085', ['id', 'name', 'code', 'rate', 'type'])

    def create_with_lines(self, order_data, lines):
        order = super().create(order_data)
        subtotal = 0
        tax_rate_pct = self._lookup_tax_rate(order_data.get('tax_rate_id'))
        price_list_id = order_data.get('price_list_id')

        for line_data in lines:
            unit_price = self._resolve_unit_price(line_data, price_list_id)
            qty = line_data.get('qty', 1)
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
            })

        tax_amount = subtotal * tax_rate_pct / 100
        return super().update(order['id'], {
            'subtotal': subtotal,
            'tax': tax_amount,
            'grand_total': subtotal + tax_amount,
        })

    def _lookup_tax_rate(self, tax_rate_id):
        if not tax_rate_id:
            return 0
        tax_rate = self.tax_rate_repo.get(tax_rate_id)
        return tax_rate.get('rate', 0) if tax_rate else 0

    def _resolve_unit_price(self, line_data, price_list_id):
        unit_price = line_data.get('unit_price', 0)
        if unit_price and unit_price > 0:
            return unit_price
        product_id = line_data.get('product_id')
        if not price_list_id or not product_id:
            return 0
        prices = self.price_list_item_repo.list(filters={
            'price_list_id': price_list_id,
            'product_id': product_id,
        })
        return prices[0].get('unit_price', 0) if prices else 0
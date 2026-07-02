from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository


class EnhancedSalesOrderService(CrudService):
    def __init__(self, repo):
        super().__init__(repo)
        self.line_repo = CrudRepository('T0013', ['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        self.price_list_item_repo = CrudRepository('T0084', ['id', 'price_list_id', 'product_id', 'unit_price', 'min_qty'])
        self.tax_rate_repo = CrudRepository('T0085', ['id', 'name', 'code', 'rate', 'type'])

    def create_with_lines(self, order_data, lines):
        """Create a sales order with lines, applying price list and tax rate."""
        order = super().create(order_data)

        price_list_id = order_data.get('price_list_id')
        tax_rate_id = order_data.get('tax_rate_id')
        subtotal = 0

        tax_rate_pct = 0
        if tax_rate_id:
            tax_rate = self.tax_rate_repo.get(tax_rate_id)
            if tax_rate:
                tax_rate_pct = tax_rate.get('rate', 0)

        for line_data in lines:
            unit_price = line_data.get('unit_price', 0)
            product_id = line_data.get('product_id')

            if price_list_id and product_id and (not unit_price or unit_price == 0):
                prices = self.price_list_item_repo.list(filters={
                    'price_list_id': price_list_id,
                    'product_id': product_id
                })
                if prices:
                    unit_price = prices[0].get('unit_price', 0)

            qty = line_data.get('qty', 1)
            line_total = qty * unit_price
            subtotal += line_total

            self.line_repo.create({
                'sales_order_id': order['id'],
                'product_id': product_id,
                'product_name': line_data.get('product_name', ''),
                'qty': qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'line_number': line_data.get('line_number', 1),
            })

        tax_amount = subtotal * tax_rate_pct / 100
        grand_total = subtotal + tax_amount
        return super().update(order['id'], {
            'subtotal': subtotal,
            'tax': tax_amount,
            'grand_total': grand_total,
        })

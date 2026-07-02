from modules.core.repositories.base import CrudRepository

PL_REPO = CrudRepository('T0101', business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'])
PLI_REPO = CrudRepository('T0102', business_columns=['id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name', 'qty_ordered', 'qty_picked', 'line_number'])


def generate_pick_list_number():
    rows = PL_REPO.list(order_by='id', limit=1)
    last_num = 0
    if rows:
        last_val = rows[0].get('pick_list_number', 'PL-00000')
        try:
            last_num = int(last_val.split('-')[1])
        except (IndexError, ValueError):
            pass
    return f'PL-{last_num + 1:05d}'


class PickListService:
    def create_from_order(self, sales_order_id, warehouse_id=None):
        order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'warehouse_id', 'customer_id'])
        order = order_repo.get(sales_order_id)
        if not order:
            raise ValueError(f'Sales order {sales_order_id} not found')
        wh_id = warehouse_id or order.get('warehouse_id')
        if not wh_id:
            wh_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = wh_repo.list(filters={'is_active': True}, limit=1)
            if not warehouses:
                raise ValueError('No active warehouse found')
            wh_id = warehouses[0]['id']

        pick_list_number = generate_pick_list_number()
        pl = PL_REPO.create({
            'pick_list_number': pick_list_number,
            'sales_order_id': sales_order_id,
            'warehouse_id': wh_id,
            'status': 'Pending',
        })

        line_repo = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        order_lines = line_repo.list(filters={'sales_order_id': sales_order_id})
        for line in order_lines:
            PLI_REPO.create({
                'pick_list_id': pl['id'],
                'sales_order_line_id': line['id'],
                'product_id': line['product_id'],
                'product_name': line.get('product_name', ''),
                'qty_ordered': line.get('qty', 0),
                'qty_picked': 0,
                'line_number': line.get('line_number', 1),
            })

        return self.get_with_items(pl['id'])

    def get_with_items(self, pick_list_id):
        pl = PL_REPO.get(pick_list_id)
        if not pl:
            return None
        items = PLI_REPO.list(filters={'pick_list_id': pick_list_id}, order_by='line_number')
        pl['items'] = items
        pl['progress_pct'] = self._calc_progress(items)
        return pl

    def pick_item(self, item_id, qty_picked):
        item = PLI_REPO.get(item_id)
        if not item:
            raise ValueError(f'Pick list item {item_id} not found')
        PLI_REPO.update(item_id, {'qty_picked': qty_picked})
        return PLI_REPO.get(item_id)

    def start_picking(self, pick_list_id):
        pl = PL_REPO.get(pick_list_id)
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        if pl['status'] != 'Pending':
            raise ValueError(f'Pick list status is {pl["status"]}, expected Pending')
        PL_REPO.update(pick_list_id, {'status': 'In Progress'})
        return PL_REPO.get(pick_list_id)

    def complete_picking(self, pick_list_id):
        pl = PL_REPO.get(pick_list_id)
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        items = PLI_REPO.list(filters={'pick_list_id': pick_list_id})
        for item in items:
            if item.get('qty_picked', 0) < item.get('qty_ordered', 0):
                raise ValueError(f'Item {item.get("product_name", item["product_id"])} has {item["qty_picked"]} picked of {item["qty_ordered"]} ordered')
        PL_REPO.update(pick_list_id, {'status': 'Completed'})
        order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'status'])
        order_repo.update(pl['sales_order_id'], {'status': 'Shipped'})
        return self.get_with_items(pick_list_id)

    def _calc_progress(self, items):
        if not items:
            return 100
        total_ordered = sum(i.get('qty_ordered', 0) for i in items)
        total_picked = sum(i.get('qty_picked', 0) for i in items)
        if total_ordered == 0:
            return 100
        return round((total_picked / total_ordered) * 100, 1)

from modules.core.repositories.base import CrudRepository
from modules.warehouse.services.batch_number_service import BatchNumberService

PL_REPO = CrudRepository('T0101', business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'])
PLI_REPO = CrudRepository('T0102', business_columns=[
    'id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name',
    'qty_ordered', 'qty_picked', 'line_number',
    'batch_id', 'batch_number', 'expiry_date', 'picked_batch_id', 'picked_batch_number'
])
BATCH_REPO = CrudRepository('T0088', business_columns=[
    'id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date',
    'quantity', 'warehouse_id', 'status', 'notes'
])


def generate_pick_list_number(pl_repo=None):
    repo = pl_repo or PL_REPO
    rows = repo.list(order_by='id', limit=1)
    last_num = 0
    if rows:
        last_val = rows[0].get('pick_list_number', 'PL-00000')
        try:
            last_num = int(last_val.split('-')[1])
        except (IndexError, ValueError):
            pass
    return f'PL-{last_num + 1:05d}'


class PickListService:
    def __init__(self, pl_repo=None, pli_repo=None, batch_service=None, order_repo=None, line_repo=None, wh_repo=None):
        self.pl_repo = pl_repo or PL_REPO
        self.pli_repo = pli_repo or PLI_REPO
        self.batch_service = batch_service or BatchNumberService(BATCH_REPO)
        self.order_repo = order_repo or CrudRepository('T0012', business_columns=['id', 'order_number', 'warehouse_id', 'customer_id', 'status'])
        self.line_repo = line_repo or CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        self.wh_repo = wh_repo or CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])

    def create_from_order(self, sales_order_id, warehouse_id=None):
        order = self.order_repo.get(sales_order_id)
        if not order:
            raise ValueError(f'Sales order {sales_order_id} not found')
        wh_id = warehouse_id or order.get('warehouse_id')
        if not wh_id:
            warehouses = self.wh_repo.list(filters={'is_active': True}, limit=1)
            if not warehouses:
                raise ValueError('No active warehouse found')
            wh_id = warehouses[0]['id']

        pick_list_number = generate_pick_list_number(self.pl_repo)
        pl = self.pl_repo.create({
            'pick_list_number': pick_list_number,
            'sales_order_id': sales_order_id,
            'warehouse_id': wh_id,
            'status': 'Pending',
        })

        order_lines = self.line_repo.list(filters={'sales_order_id': sales_order_id})
        order_lines.sort(key=lambda l: (l.get('line_number') or 0, l.get('id') or 0))

        item_line_num = 1
        for line in order_lines:
            product_id = line.get('product_id')
            qty_ordered = float(line.get('qty', 0) or 0)
            product_name = line.get('product_name', '')
            order_line_id = line.get('id')

            allocations = []
            if product_id and qty_ordered > 0:
                try:
                    allocations = self.batch_service.allocate_fefo_lots(
                        product_id=product_id,
                        warehouse_id=wh_id,
                        qty_needed=qty_ordered
                    )
                except Exception:
                    allocations = []

            if allocations:
                total_allocated = 0.0
                for alloc in allocations:
                    alloc_qty = float(alloc.get('quantity') or alloc.get('allocated_qty') or 0)
                    if alloc_qty <= 0:
                        continue
                    self.pli_repo.create({
                        'pick_list_id': pl['id'],
                        'sales_order_line_id': order_line_id,
                        'product_id': product_id,
                        'product_name': product_name,
                        'qty_ordered': alloc_qty,
                        'qty_picked': 0,
                        'line_number': item_line_num,
                        'batch_id': alloc.get('batch_id'),
                        'batch_number': alloc.get('batch_number'),
                        'expiry_date': alloc.get('expiry_date'),
                    })
                    total_allocated += alloc_qty
                    item_line_num += 1

                remaining_qty = qty_ordered - total_allocated
                if remaining_qty > 0:
                    self.pli_repo.create({
                        'pick_list_id': pl['id'],
                        'sales_order_line_id': order_line_id,
                        'product_id': product_id,
                        'product_name': product_name,
                        'qty_ordered': remaining_qty,
                        'qty_picked': 0,
                        'line_number': item_line_num,
                        'batch_id': None,
                        'batch_number': None,
                        'expiry_date': None,
                    })
                    item_line_num += 1
            else:
                self.pli_repo.create({
                    'pick_list_id': pl['id'],
                    'sales_order_line_id': order_line_id,
                    'product_id': product_id,
                    'product_name': product_name,
                    'qty_ordered': qty_ordered,
                    'qty_picked': 0,
                    'line_number': item_line_num,
                    'batch_id': None,
                    'batch_number': None,
                    'expiry_date': None,
                })
                item_line_num += 1

        return self.get_with_items(pl['id'])

    def get_with_items(self, pick_list_id):
        pl = self.pl_repo.get(pick_list_id)
        if not pl:
            return None
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, order_by='line_number')
        pl['items'] = items
        pl['progress_pct'] = self._calc_progress(items)
        return pl

    def get_available_batches_for_item(self, pick_list_id: int, item_id: int):
        pl = self.pl_repo.get(pick_list_id)
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        item = self.pli_repo.get(item_id)
        if not item or item.get('pick_list_id') != pick_list_id:
            raise ValueError(f'Pick list item {item_id} not found in pick list {pick_list_id}')

        product_id = item.get('product_id')
        if not product_id:
            return []

        filters = {'product_id': product_id}
        wh_id = pl.get('warehouse_id')
        if wh_id:
            filters['warehouse_id'] = wh_id

        batches = self.batch_service.repo.list(filters=filters)
        available = [
            b for b in batches
            if b.get('status') in ('Available', 'Partially Used', 'Active')
            and float(b.get('quantity') or 0) > 0
        ]

        def sort_key(b):
            exp = b.get('expiry_date')
            has_exp = 0 if exp is not None else 1
            exp_str = str(exp) if exp is not None else ''
            bid = b.get('id') or 0
            return (has_exp, exp_str, bid)

        available.sort(key=sort_key)
        return available

    def pick_item(self, item_id, qty_picked, picked_batch_id=None, picked_batch_number=None):
        item = self.pli_repo.get(item_id)
        if not item:
            raise ValueError(f'Pick list item {item_id} not found')

        update_data = {'qty_picked': qty_picked}
        if picked_batch_id is not None:
            update_data['picked_batch_id'] = picked_batch_id
            if not picked_batch_number:
                batch = self.batch_service.get(picked_batch_id)
                if batch:
                    update_data['picked_batch_number'] = batch.get('batch_number')
            else:
                update_data['picked_batch_number'] = picked_batch_number
        elif picked_batch_number is not None and str(picked_batch_number).strip():
            picked_batch_number = str(picked_batch_number).strip()
            update_data['picked_batch_number'] = picked_batch_number
            batches = self.batch_service.repo.list(filters={
                'batch_number': picked_batch_number,
                'product_id': item.get('product_id')
            })
            if batches:
                update_data['picked_batch_id'] = batches[0]['id']

        self.pli_repo.update(item_id, update_data)
        return self.pli_repo.get(item_id)

    def start_picking(self, pick_list_id):
        pl = self.pl_repo.get(pick_list_id)
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        if pl['status'] != 'Pending':
            raise ValueError(f'Pick list status is {pl["status"]}, expected Pending')
        self.pl_repo.update(pick_list_id, {'status': 'In Progress'})
        return self.pl_repo.get(pick_list_id)

    def complete_picking(self, pick_list_id):
        pl = self.pl_repo.get(pick_list_id)
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id})
        for item in items:
            if item.get('qty_picked', 0) < item.get('qty_ordered', 0):
                raise ValueError(f'Item {item.get("product_name", item["product_id"])} has {item["qty_picked"]} picked of {item["qty_ordered"]} ordered')

        for item in items:
            picked_qty = float(item.get('qty_picked', 0) or 0)
            if picked_qty <= 0:
                continue

            batch_id = item.get('picked_batch_id') or item.get('batch_id')
            if not batch_id and (item.get('picked_batch_number') or item.get('batch_number')):
                batch_num = item.get('picked_batch_number') or item.get('batch_number')
                batches = self.batch_service.repo.list(filters={
                    'batch_number': batch_num,
                    'product_id': item.get('product_id')
                })
                if batches:
                    batch_id = batches[0]['id']

            if batch_id:
                self.batch_service.adjustQuantity(batch_id, -picked_qty)

        self.pl_repo.update(pick_list_id, {'status': 'Completed'})
        self.order_repo.update(pl['sales_order_id'], {'status': 'Shipped'})
        return self.get_with_items(pick_list_id)

    def _calc_progress(self, items):
        if not items:
            return 100
        total_ordered = sum(i.get('qty_ordered', 0) for i in items)
        total_picked = sum(i.get('qty_picked', 0) for i in items)
        if total_ordered == 0:
            return 100
        return round((total_picked / total_ordered) * 100, 1)

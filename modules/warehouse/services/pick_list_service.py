import logging
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_pick_list_number
from modules.warehouse.services.batch_number_service import BatchNumberService

logger = logging.getLogger(__name__)

PL_REPO = CrudRepository(
    'T0101',
    business_columns=[
        'id',
        'pick_list_number',
        'sales_order_id',
        'warehouse_id',
        'status',
        'notes',
    ],
)
PLI_REPO = CrudRepository(
    'T0102',
    business_columns=[
        'id',
        'pick_list_id',
        'sales_order_line_id',
        'product_id',
        'product_name',
        'qty_ordered',
        'qty_picked',
        'line_number',
        'batch_id',
        'batch_number',
        'expiry_date',
        'picked_batch_id',
        'picked_batch_number',
    ],
)
BATCH_REPO = CrudRepository(
    'T0088',
    business_columns=[
        'id',
        'product_id',
        'batch_number',
        'expiry_date',
        'manufacturing_date',
        'quantity',
        'warehouse_id',
        'status',
        'notes',
    ],
)


def _conn_kwargs(conn):
    """Only forward conn to repositories when an explicit connection is provided."""
    return {'conn': conn} if conn is not None else {}


class PickListService(CrudService):
    def __init__(self, repo: CrudRepository = None, pl_repo=None, pli_repo=None,
                 batch_service=None, order_repo=None, line_repo=None, wh_repo=None):
        super().__init__(repo or pl_repo or PL_REPO)
        self.pl_repo = self.repo
        self.pli_repo = pli_repo or PLI_REPO
        self.batch_service = batch_service or BatchNumberService(BATCH_REPO)
        self.order_repo = order_repo or CrudRepository(
            'T0012', business_columns=['id', 'order_number', 'warehouse_id', 'customer_id', 'status']
        )
        self.line_repo = line_repo or CrudRepository(
            'T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number']
        )
        self.wh_repo = wh_repo or CrudRepository(
            'T0008', business_columns=['id', 'name', 'is_active']
        )

    def create(self, payload, conn=None):
        if not payload.get('pick_list_number') or not str(payload.get('pick_list_number')).strip():
            try:
                payload['pick_list_number'] = generate_pick_list_number(**_conn_kwargs(conn))
                logger.info(f"Generated pick list sequence number: {payload['pick_list_number']}")
            except Exception as e:
                logger.error(f"Failed to generate pick list sequence number: {e}")
                raise RuntimeError(f"Failed to generate pick list number: {e}") from e
        try:
            result = super().create(payload, **_conn_kwargs(conn))
            logger.info(f"Created pick list {result.get('pick_list_number')} (id: {result.get('id')})")
            return result
        except Exception as e:
            logger.error(f"Failed to create pick list in repository: {e}")
            raise

    def create_from_order(self, sales_order_id, warehouse_id=None, conn=None):
        logger.info(f"Creating pick list for sales order {sales_order_id} (warehouse_id={warehouse_id})")
        order = self.order_repo.get(sales_order_id, **_conn_kwargs(conn))
        if not order:
            logger.error(f"Cannot create pick list: Sales order {sales_order_id} not found")
            raise ValueError(f"Sales order {sales_order_id} not found")

        wh_id = warehouse_id or order.get('warehouse_id')
        if not wh_id:
            warehouses = self.wh_repo.list(filters={'is_active': True}, limit=1, **_conn_kwargs(conn))
            if not warehouses:
                logger.error(f"Cannot create pick list for sales order {sales_order_id}: No active warehouse found")
                raise ValueError("No active warehouse found")
            wh_id = warehouses[0]['id']

        order_lines = self.line_repo.list(filters={'sales_order_id': sales_order_id}, **_conn_kwargs(conn))
        if not order_lines:
            logger.warning(f"Sales order {sales_order_id} has no order lines when generating pick list")
        order_lines.sort(key=lambda l: (l.get('line_number') or 0, l.get('id') or 0))

        try:
            pl = self.create({
                'sales_order_id': sales_order_id,
                'warehouse_id': wh_id,
                'status': 'Pending',
            }, conn=conn)
        except Exception as e:
            logger.error(f"Failed to create pick list header for sales order {sales_order_id}: {e}")
            raise RuntimeError(f"Failed to create pick list header for sales order {sales_order_id}: {e}") from e

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
                    try:
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
                        }, **_conn_kwargs(conn))
                    except Exception as e:
                        logger.error(f"Failed to create pick list item for sales order line {order_line_id} in pick list {pl['id']}: {e}")
                        raise RuntimeError(f"Failed to create pick list item for sales order line {order_line_id}: {e}") from e
                    total_allocated += alloc_qty
                    item_line_num += 1

                remaining_qty = qty_ordered - total_allocated
                if remaining_qty > 0:
                    try:
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
                        }, **_conn_kwargs(conn))
                    except Exception as e:
                        logger.error(f"Failed to create pick list item for sales order line {order_line_id} in pick list {pl['id']}: {e}")
                        raise RuntimeError(f"Failed to create pick list item for sales order line {order_line_id}: {e}") from e
                    item_line_num += 1
            else:
                try:
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
                    }, **_conn_kwargs(conn))
                except Exception as e:
                    logger.error(f"Failed to create pick list item for sales order line {order_line_id} in pick list {pl['id']}: {e}")
                    raise RuntimeError(f"Failed to create pick list item for sales order line {order_line_id}: {e}") from e
                item_line_num += 1

        logger.info(f"Successfully generated pick list {pl.get('pick_list_number')} (id {pl['id']}) with {len(order_lines)} items for sales order {sales_order_id}")
        return self.get_with_items(pl['id'], conn=conn)

    def get_with_items(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, **_conn_kwargs(conn))
        if not pl:
            logger.warning(f"Pick list {pick_list_id} not found")
            return None
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, order_by='line_number', **_conn_kwargs(conn))
        pl['items'] = items
        pl['progress_pct'] = self._calc_progress(items)
        return pl

    def get_available_batches_for_item(self, pick_list_id, item_id, conn=None):
        pl = self.repo.get(pick_list_id, **_conn_kwargs(conn))
        if not pl:
            raise ValueError(f'Pick list {pick_list_id} not found')
        item = self.pli_repo.get(item_id, **_conn_kwargs(conn))
        if not item or item.get('pick_list_id') != pick_list_id:
            raise ValueError(f'Pick list item {item_id} not found in pick list {pick_list_id}')

        product_id = item.get('product_id')
        if not product_id:
            return []

        filters = {'product_id': product_id}
        wh_id = pl.get('warehouse_id')
        if wh_id:
            filters['warehouse_id'] = wh_id

        batches = self.batch_service.repo.list(filters=filters, **_conn_kwargs(conn))
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

    def pick_item(self, item_id, qty_picked, picked_batch_id=None, picked_batch_number=None, conn=None):
        item = self.pli_repo.get(item_id, **_conn_kwargs(conn))
        if not item:
            logger.error(f"Cannot pick item: Pick list item {item_id} not found")
            raise ValueError(f"Pick list item {item_id} not found")
        if qty_picked < 0:
            logger.warning(f"Invalid picked quantity {qty_picked} for item {item_id}")
            raise ValueError(f"Quantity picked cannot be negative: {qty_picked}")

        update_data = {'qty_picked': qty_picked}
        if picked_batch_id is not None:
            update_data['picked_batch_id'] = picked_batch_id
            if not picked_batch_number:
                batch = self.batch_service.get(picked_batch_id, **_conn_kwargs(conn))
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
            }, **_conn_kwargs(conn))
            if batches:
                update_data['picked_batch_id'] = batches[0]['id']

        try:
            self.pli_repo.update(item_id, update_data, **_conn_kwargs(conn))
            logger.info(f"Updated pick list item {item_id} qty_picked to {qty_picked}")
        except Exception as e:
            logger.error(f"Failed to update pick list item {item_id}: {e}")
            raise RuntimeError(f"Failed to update pick list item {item_id}: {e}") from e
        return self.pli_repo.get(item_id, **_conn_kwargs(conn))

    def start_picking(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, **_conn_kwargs(conn))
        if not pl:
            logger.error(f"Cannot start picking: Pick list {pick_list_id} not found")
            raise ValueError(f"Pick list {pick_list_id} not found")
        if pl['status'] != 'Pending':
            logger.warning(f"Cannot start picking: Pick list {pick_list_id} status is {pl['status']}, expected Pending")
            raise ValueError(f"Pick list status is {pl['status']}, expected Pending")
        try:
            self.repo.update(pick_list_id, {'status': 'In Progress'}, **_conn_kwargs(conn))
            logger.info(f"Started picking for pick list {pick_list_id} (status: In Progress)")
        except Exception as e:
            logger.error(f"Failed to update status for pick list {pick_list_id}: {e}")
            raise RuntimeError(f"Failed to update status for pick list {pick_list_id}: {e}") from e
        return self.repo.get(pick_list_id, **_conn_kwargs(conn))

    def complete_picking(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, **_conn_kwargs(conn))
        if not pl:
            logger.error(f"Cannot complete picking: Pick list {pick_list_id} not found")
            raise ValueError(f"Pick list {pick_list_id} not found")
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, **_conn_kwargs(conn))
        unpicked = []
        for item in items:
            if item.get('qty_picked', 0) < item.get('qty_ordered', 0):
                unpicked.append(f"Item {item.get('product_name', item['product_id'])} has {item.get('qty_picked', 0)} picked of {item.get('qty_ordered', 0)} ordered")
        if unpicked:
            msg = f"Cannot complete pick list {pick_list_id}: {'; '.join(unpicked)}"
            logger.warning(msg)
            raise ValueError(msg)
        try:
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
                    }, **_conn_kwargs(conn))
                    if batches:
                        batch_id = batches[0]['id']

                if batch_id:
                    self.batch_service.adjustQuantity(batch_id, -picked_qty)

            self.repo.update(pick_list_id, {'status': 'Completed'}, **_conn_kwargs(conn))
            self.order_repo.update(pl['sales_order_id'], {'status': 'Shipped'}, **_conn_kwargs(conn))
            logger.info(f"Completed pick list {pick_list_id} and updated sales order {pl['sales_order_id']} to Shipped")
        except Exception as e:
            logger.error(f"Failed to complete picking for pick list {pick_list_id}: {e}")
            raise RuntimeError(f"Failed to complete picking for pick list {pick_list_id}: {e}") from e
        return self.get_with_items(pick_list_id, conn=conn)

    def _calc_progress(self, items):
        if not items:
            return 100
        total_ordered = sum(i.get('qty_ordered', 0) for i in items)
        total_picked = sum(i.get('qty_picked', 0) for i in items)
        if total_ordered == 0:
            return 100
        return round((total_picked / total_ordered) * 100, 1)
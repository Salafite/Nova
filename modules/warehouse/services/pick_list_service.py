import logging
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_pick_list_number

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
    ],
)


class PickListService(CrudService):
    def __init__(self, repo: CrudRepository = None):
        super().__init__(repo or PL_REPO)
        self.pli_repo = PLI_REPO

    def create(self, payload: dict, conn=None):
        if not payload.get('pick_list_number') or not str(payload.get('pick_list_number')).strip():
            try:
                payload['pick_list_number'] = generate_pick_list_number(conn=conn)
                logger.info(f"Generated pick list sequence number: {payload['pick_list_number']}")
            except Exception as e:
                logger.error(f"Failed to generate pick list sequence number: {e}")
                raise RuntimeError(f"Failed to generate pick list number: {e}") from e
        try:
            result = super().create(payload, conn=conn)
            logger.info(f"Created pick list {result.get('pick_list_number')} (id: {result.get('id')})")
            return result
        except Exception as e:
            logger.error(f"Failed to create pick list in repository: {e}")
            raise

    def create_from_order(self, sales_order_id, warehouse_id=None, conn=None):
        logger.info(f"Creating pick list for sales order {sales_order_id} (warehouse_id={warehouse_id})")
        order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'warehouse_id', 'customer_id'])
        order = order_repo.get(sales_order_id, conn=conn)
        if not order:
            logger.error(f"Cannot create pick list: Sales order {sales_order_id} not found")
            raise ValueError(f"Sales order {sales_order_id} not found")

        wh_id = warehouse_id or order.get('warehouse_id')
        if not wh_id:
            wh_repo = CrudRepository('T0008', business_columns=['id', 'name', 'is_active'])
            warehouses = wh_repo.list(filters={'is_active': True}, limit=1, conn=conn)
            if not warehouses:
                logger.error(f"Cannot create pick list for sales order {sales_order_id}: No active warehouse found")
                raise ValueError("No active warehouse found")
            wh_id = warehouses[0]['id']

        line_repo = CrudRepository('T0013', business_columns=['id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price', 'line_total', 'line_number'])
        order_lines = line_repo.list(filters={'sales_order_id': sales_order_id}, conn=conn)
        if not order_lines:
            logger.warning(f"Sales order {sales_order_id} has no order lines when generating pick list")

        try:
            pl = self.create({
                'sales_order_id': sales_order_id,
                'warehouse_id': wh_id,
                'status': 'Pending',
            }, conn=conn)
        except Exception as e:
            logger.error(f"Failed to create pick list header for sales order {sales_order_id}: {e}")
            raise RuntimeError(f"Failed to create pick list header for sales order {sales_order_id}: {e}") from e

        for line in order_lines:
            try:
                self.pli_repo.create({
                    'pick_list_id': pl['id'],
                    'sales_order_line_id': line['id'],
                    'product_id': line['product_id'],
                    'product_name': line.get('product_name', ''),
                    'qty_ordered': line.get('qty', 0),
                    'qty_picked': 0,
                    'line_number': line.get('line_number', 1),
                }, conn=conn)
            except Exception as e:
                logger.error(f"Failed to create pick list item for sales order line {line.get('id')} in pick list {pl['id']}: {e}")
                raise RuntimeError(f"Failed to create pick list item for sales order line {line.get('id')}: {e}") from e

        logger.info(f"Successfully generated pick list {pl.get('pick_list_number')} (id {pl['id']}) with {len(order_lines)} items for sales order {sales_order_id}")
        return self.get_with_items(pl['id'], conn=conn)

    def get_with_items(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, conn=conn)
        if not pl:
            logger.warning(f"Pick list {pick_list_id} not found")
            return None
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, order_by='line_number', conn=conn)
        pl['items'] = items
        pl['progress_pct'] = self._calc_progress(items)
        return pl

    def pick_item(self, item_id, qty_picked, conn=None):
        item = self.pli_repo.get(item_id, conn=conn)
        if not item:
            logger.error(f"Cannot pick item: Pick list item {item_id} not found")
            raise ValueError(f"Pick list item {item_id} not found")
        if qty_picked < 0:
            logger.warning(f"Invalid picked quantity {qty_picked} for item {item_id}")
            raise ValueError(f"Quantity picked cannot be negative: {qty_picked}")
        try:
            self.pli_repo.update(item_id, {'qty_picked': qty_picked}, conn=conn)
            logger.info(f"Updated pick list item {item_id} qty_picked to {qty_picked}")
        except Exception as e:
            logger.error(f"Failed to update pick list item {item_id}: {e}")
            raise RuntimeError(f"Failed to update pick list item {item_id}: {e}") from e
        return self.pli_repo.get(item_id, conn=conn)

    def start_picking(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, conn=conn)
        if not pl:
            logger.error(f"Cannot start picking: Pick list {pick_list_id} not found")
            raise ValueError(f"Pick list {pick_list_id} not found")
        if pl['status'] != 'Pending':
            logger.warning(f"Cannot start picking: Pick list {pick_list_id} status is {pl['status']}, expected Pending")
            raise ValueError(f"Pick list status is {pl['status']}, expected Pending")
        try:
            self.repo.update(pick_list_id, {'status': 'In Progress'}, conn=conn)
            logger.info(f"Started picking for pick list {pick_list_id} (status: In Progress)")
        except Exception as e:
            logger.error(f"Failed to update status for pick list {pick_list_id}: {e}")
            raise RuntimeError(f"Failed to update status for pick list {pick_list_id}: {e}") from e
        return self.repo.get(pick_list_id, conn=conn)

    def complete_picking(self, pick_list_id, conn=None):
        pl = self.repo.get(pick_list_id, conn=conn)
        if not pl:
            logger.error(f"Cannot complete picking: Pick list {pick_list_id} not found")
            raise ValueError(f"Pick list {pick_list_id} not found")
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, conn=conn)
        unpicked = []
        for item in items:
            if item.get('qty_picked', 0) < item.get('qty_ordered', 0):
                unpicked.append(f"Item {item.get('product_name', item['product_id'])} has {item.get('qty_picked', 0)} picked of {item.get('qty_ordered', 0)} ordered")
        if unpicked:
            msg = f"Cannot complete pick list {pick_list_id}: {'; '.join(unpicked)}"
            logger.warning(msg)
            raise ValueError(msg)
        try:
            self.repo.update(pick_list_id, {'status': 'Completed'}, conn=conn)
            order_repo = CrudRepository('T0012', business_columns=['id', 'order_number', 'status'])
            order_repo.update(pl['sales_order_id'], {'status': 'Shipped'}, conn=conn)
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

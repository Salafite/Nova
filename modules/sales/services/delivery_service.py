import logging
from fastapi import HTTPException
from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)

DELIVERY_LINE_REPO = CrudRepository(
    'T0078',
    business_columns=[
        'id', 'delivery_id', 'sales_order_line_id', 'product_id',
        'product_name', 'qty_shipped', 'qty_ordered', 'uom_id', 'line_number'
    ],
)

PL_REPO = CrudRepository(
    'T0101',
    business_columns=['id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'],
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
        'catch_weight_actual',
        'catch_weight_uom',
        'nominal_weight',
        'tolerance_pct',
        'tolerance_variance_pct',
        'tolerance_status',
        'supervisor_approved',
        'supervisor_approved_by',
        'supervisor_approved_at',
        'supervisor_notes',
    ],
)


class DeliveryService(CrudService):
    def __init__(self, repo, line_repo=None, pl_repo=None, pli_repo=None, stock_service=None):
        super().__init__(repo)
        self.stock_service = stock_service or StockMovementService()
        self.line_repo = line_repo or DELIVERY_LINE_REPO
        self.pl_repo = pl_repo or PL_REPO
        self.pli_repo = pli_repo or PLI_REPO

    def _validate_tolerance_approvals(self, sales_order_id, conn=None):
        """
        Validate that all pick list items for the sales order have no unapproved catch-weight tolerance discrepancies.
        """
        if not sales_order_id or not hasattr(self, 'pl_repo') or not self.pl_repo:
            return
        kwargs = {'conn': conn} if conn is not None else {}
        try:
            pick_lists = self.pl_repo.list(filters={'sales_order_id': sales_order_id}, **kwargs)
        except Exception as e:
            logger.warning(f"Could not check pick lists for order {sales_order_id}: {e}")
            return

        for pl in pick_lists:
            if hasattr(self, 'pli_repo') and self.pli_repo:
                try:
                    items = self.pli_repo.list(filters={'pick_list_id': pl['id']}, **kwargs)
                    unapproved = [
                        it for it in items
                        if it.get('tolerance_status') == 'Out of Tolerance' and not it.get('supervisor_approved')
                    ]
                    if unapproved:
                        names = [it.get('product_name') or f"Item #{it.get('id')}" for it in unapproved]
                        msg = f"Cannot deliver order {sales_order_id}: Unapproved catch-weight tolerance discrepancies exist on pick list #{pl.get('id')} items: {', '.join(names)}"
                        logger.warning(msg)
                        raise HTTPException(400, msg)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Could not check pick list items for pick list {pl['id']}: {e}")

    def create(self, payload: dict, conn=None):
        sales_order_id = payload.get('sales_order_id')
        if sales_order_id and payload.get('status') in ('Shipped', 'Delivered'):
            self._validate_tolerance_approvals(sales_order_id, conn=conn)
        result = super().create(payload, **({'conn': conn} if conn is not None else {}))
        if result and payload.get('status') == 'Shipped':
            self._record_stock_movements(result['id'])
        return result

    def update(self, id_val, payload: dict, conn=None):
        kwargs = {'conn': conn} if conn is not None else {}
        old = self.repo.get(id_val, **kwargs)
        sales_order_id = payload.get('sales_order_id') or (old.get('sales_order_id') if old else None)
        if sales_order_id and payload.get('status') in ('Shipped', 'Delivered'):
            self._validate_tolerance_approvals(sales_order_id, conn=conn)
        result = super().update(id_val, payload, **kwargs)
        if old and payload.get('status') == 'Shipped' and old.get('status') != 'Shipped':
            self._record_stock_movements(id_val)
        return result

    def _record_stock_movements(self, delivery_id):
        lines = self.line_repo.list(filters={'delivery_id': delivery_id})
        for line in lines:
            if line.get('product_id'):
                self.stock_service.record_movement(
                    product_id=line['product_id'],
                    warehouse_id=1,
                    movement_type='Delivery',
                    qty_change=-abs(line.get('qty_shipped', 0)),
                    reference_type='Delivery',
                    reference_id=delivery_id,
                    description=f'Delivery: {line.get("product_name", "")}',
                )

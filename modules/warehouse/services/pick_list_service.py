import logging
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.database.sequence import generate_pick_list_number
from packages.database.connection import get_connection, release_connection
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
                 batch_service=None, order_repo=None, line_repo=None, wh_repo=None,
                 product_repo=None, uom_repo=None):
        super().__init__(repo or pl_repo or PL_REPO)
        self.pl_repo = self.repo
        self.pli_repo = pli_repo or PLI_REPO
        self.batch_service = batch_service or BatchNumberService(BATCH_REPO)
        self.order_repo = order_repo or CrudRepository(
            'T0012', business_columns=['id', 'order_number', 'warehouse_id', 'customer_id', 'status']
        )
        self.line_repo = line_repo or CrudRepository(
            'T0013', business_columns=[
                'id', 'sales_order_id', 'product_id', 'product_name', 'qty', 'unit_price',
                'line_total', 'line_number', 'is_catch_weight', 'pricing_uom_id',
                'unit_price_pricing_uom', 'nominal_weight', 'catch_weight_actual', 'recalculated_total'
            ]
        )
        self.wh_repo = wh_repo or CrudRepository(
            'T0008', business_columns=['id', 'name', 'is_active']
        )
        self.product_repo = product_repo or CrudRepository(
            'T0003', business_columns=[
                'id', 'name', 'sku', 'barcode', 'description', 'type', 'price', 'cost_price',
                'category', 'brand', 'tax_rate', 'weight', 'volume', 'image_url',
                'is_purchasable', 'is_saleable', 'is_phantom', 'last_transaction_date', 'is_active',
                'is_catch_weight', 'pricing_uom_id', 'nominal_weight', 'tolerance_pct', 'pricing_basis'
            ]
        )
        self.uom_repo = uom_repo or CrudRepository(
            'T0001', business_columns=['id', 'uom_code', 'uom_name', 'category', 'is_base_unit', 'is_active']
        )

    def calculate_weight_variance(self, nominal_weight, actual_weight):
        """
        Calculate variance percentage between nominal expected weight and actual scale weight.
        Returns: round(((actual - nominal) / nominal) * 100, 2) or None if nominal <= 0 or actual is None.
        """
        if actual_weight is None:
            return None
        if nominal_weight is None or float(nominal_weight) <= 0:
            return None
        actual_val = float(actual_weight)
        nom_val = float(nominal_weight)
        return round(((actual_val - nom_val) / nom_val) * 100.0, 2)

    def evaluate_tolerance(self, nominal_weight, actual_weight, tolerance_pct, supervisor_approved=False):
        """
        Evaluate weight variance and determine tolerance status.
        Tolerance status values:
          - 'Not Applicable' (if actual_weight is None)
          - 'Within Tolerance' (if abs(variance_pct) <= tolerance_pct)
          - 'Out of Tolerance' (if abs(variance_pct) > tolerance_pct and not supervisor_approved)
          - 'Approved' (if abs(variance_pct) > tolerance_pct and supervisor_approved)
        Returns: tuple(tolerance_variance_pct, tolerance_status)
        """
        if actual_weight is None:
            return None, 'Not Applicable'

        variance_pct = self.calculate_weight_variance(nominal_weight, actual_weight)
        if variance_pct is None:
            status = 'Approved' if supervisor_approved else 'Within Tolerance'
            return None, status

        limit = float(tolerance_pct) if tolerance_pct is not None else 0.0
        if abs(variance_pct) <= (limit + 1e-6):
            return variance_pct, 'Within Tolerance'
        else:
            return variance_pct, 'Approved' if supervisor_approved else 'Out of Tolerance'

    def check_pick_list_discrepancies(self, pick_list_id, conn=None):
        """
        Retrieve all items in a pick list that have unapproved catch weight tolerance discrepancies.
        """
        items = self.pli_repo.list(filters={'pick_list_id': pick_list_id}, **_conn_kwargs(conn))
        discrepancies = []
        for item in items:
            status = item.get('tolerance_status')
            approved = item.get('supervisor_approved', False)
            if status == 'Out of Tolerance' or (status not in ('Within Tolerance', 'Not Applicable', 'Approved') and not approved):
                discrepancies.append(item)
        return discrepancies

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

            # Fetch product dual UOM info if available
            product = None
            if product_id and hasattr(self, 'product_repo') and self.product_repo:
                try:
                    product = self.product_repo.get(product_id, **_conn_kwargs(conn))
                except Exception:
                    product = None

            is_cw = bool((product and product.get('is_catch_weight')) or line.get('is_catch_weight'))
            cw_uom = None
            tol_pct = None
            nom_unit_wt = 0.0

            if is_cw:
                tol_pct = float(product.get('tolerance_pct')) if (product and product.get('tolerance_pct') is not None) else (float(line.get('tolerance_pct')) if line.get('tolerance_pct') is not None else None)
                if product and product.get('nominal_weight') is not None:
                    nom_unit_wt = float(product.get('nominal_weight'))
                elif line.get('nominal_weight') is not None and qty_ordered > 0:
                    nom_unit_wt = float(line.get('nominal_weight')) / qty_ordered

                pricing_uom_id = (product.get('pricing_uom_id') if product else None) or line.get('pricing_uom_id')
                if pricing_uom_id and hasattr(self, 'uom_repo') and self.uom_repo:
                    try:
                        uom_obj = self.uom_repo.get(pricing_uom_id, **_conn_kwargs(conn))
                        cw_uom = uom_obj.get('uom_code') if uom_obj else 'kg'
                    except Exception:
                        cw_uom = 'kg'
                else:
                    cw_uom = 'kg'

            allocations = []
            alloc_kwargs = {'conn': conn} if conn is not None else {}
            if product_id and qty_ordered > 0:
                try:
                    allocations = self.batch_service.allocate_fefo_lots(
                        product_id=product_id,
                        warehouse_id=wh_id,
                        qty_needed=qty_ordered,
                        **alloc_kwargs
                    )
                except Exception:
                    allocations = []

            if allocations:
                total_allocated = 0.0
                for alloc in allocations:
                    alloc_qty = float(alloc.get('quantity') or alloc.get('allocated_qty') or 0)
                    if alloc_qty <= 0:
                        continue
                    item_nominal = round(nom_unit_wt * alloc_qty, 4) if nom_unit_wt > 0 else None
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
                            'catch_weight_actual': None,
                            'catch_weight_uom': cw_uom if is_cw else None,
                            'nominal_weight': item_nominal,
                            'tolerance_pct': tol_pct,
                            'tolerance_variance_pct': None,
                            'tolerance_status': 'Not Applicable',
                            'supervisor_approved': False,
                            'supervisor_approved_by': None,
                            'supervisor_approved_at': None,
                            'supervisor_notes': None,
                        }, **_conn_kwargs(conn))
                    except Exception as e:
                        logger.error(f"Failed to create pick list item for sales order line {order_line_id} in pick list {pl['id']}: {e}")
                        raise RuntimeError(f"Failed to create pick list item for sales order line {order_line_id}: {e}") from e
                    total_allocated += alloc_qty
                    item_line_num += 1

                remaining_qty = qty_ordered - total_allocated
                if remaining_qty > 0:
                    rem_nominal = round(nom_unit_wt * remaining_qty, 4) if nom_unit_wt > 0 else None
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
                            'catch_weight_actual': None,
                            'catch_weight_uom': cw_uom if is_cw else None,
                            'nominal_weight': rem_nominal,
                            'tolerance_pct': tol_pct,
                            'tolerance_variance_pct': None,
                            'tolerance_status': 'Not Applicable',
                            'supervisor_approved': False,
                            'supervisor_approved_by': None,
                            'supervisor_approved_at': None,
                            'supervisor_notes': None,
                        }, **_conn_kwargs(conn))
                    except Exception as e:
                        logger.error(f"Failed to create pick list item for sales order line {order_line_id} in pick list {pl['id']}: {e}")
                        raise RuntimeError(f"Failed to create pick list item for sales order line {order_line_id}: {e}") from e
                    item_line_num += 1
            else:
                line_nominal = round(nom_unit_wt * qty_ordered, 4) if nom_unit_wt > 0 else None
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
                        'catch_weight_actual': None,
                        'catch_weight_uom': cw_uom if is_cw else None,
                        'nominal_weight': line_nominal,
                        'tolerance_pct': tol_pct,
                        'tolerance_variance_pct': None,
                        'tolerance_status': 'Not Applicable',
                        'supervisor_approved': False,
                        'supervisor_approved_by': None,
                        'supervisor_approved_at': None,
                        'supervisor_notes': None,
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

    def _validate_batch_for_item(self, batch, item, qty_picked, warehouse_id=None):
        batch_label = batch.get('batch_number') or batch.get('id')
        product_id = batch.get('product_id')
        if product_id is not None and product_id != item.get('product_id'):
            raise ValueError(f"Batch {batch_label} does not match product {item.get('product_id')}")
        if warehouse_id is not None:
            batch_wh = batch.get('warehouse_id')
            if batch_wh is not None and batch_wh != warehouse_id:
                raise ValueError(f"Batch {batch_label} belongs to a different warehouse")
        status = batch.get('status')
        if status is not None and status not in ('Available', 'Partially Used', 'Active'):
            raise ValueError(f"Batch {batch_label} is not available (status: {status})")
        qty = batch.get('quantity')
        if qty is not None and qty_picked > float(qty or 0):
            raise ValueError(f"Batch {batch_label} has insufficient quantity ({qty}) for {qty_picked} picked")

    def pick_item(self, item_id, qty_picked, pick_list_id=None, picked_batch_id=None,
                  picked_batch_number=None, catch_weight_actual=None, catch_weight_uom=None,
                  nominal_weight=None, tolerance_pct=None, conn=None):
        item = self.pli_repo.get(item_id, **_conn_kwargs(conn))
        if not item:
            logger.error(f"Cannot pick item: Pick list item {item_id} not found")
            raise ValueError(f"Pick list item {item_id} not found")
        if pick_list_id is not None and item.get('pick_list_id') != pick_list_id:
            logger.warning(f"Cannot pick item {item_id}: it does not belong to pick list {pick_list_id}")
            raise ValueError(f"Pick list item {item_id} not found in pick list {pick_list_id}")
        if qty_picked < 0:
            logger.warning(f"Invalid picked quantity {qty_picked} for item {item_id}")
            raise ValueError(f"Quantity picked cannot be negative: {qty_picked}")
        ordered = float(item.get('qty_ordered', 0) or 0)
        if qty_picked > ordered:
            logger.warning(f"Picked quantity {qty_picked} exceeds ordered quantity {ordered} for item {item_id}")
            raise ValueError(f"Quantity picked {qty_picked} exceeds ordered quantity {ordered}")

        warehouse_id = None
        if pick_list_id is not None:
            pl = self.repo.get(pick_list_id, **_conn_kwargs(conn))
            warehouse_id = pl.get('warehouse_id') if pl else None

        update_data = {'qty_picked': qty_picked}
        if picked_batch_id is not None:
            update_data['picked_batch_id'] = picked_batch_id
            batch = self.batch_service.get(picked_batch_id, **_conn_kwargs(conn))
            if not batch:
                raise ValueError(f"Batch {picked_batch_id} not found")
            self._validate_batch_for_item(batch, item, qty_picked, warehouse_id=warehouse_id)
            if batch.get('batch_number'):
                update_data['picked_batch_number'] = batch.get('batch_number')
            elif picked_batch_number:
                update_data['picked_batch_number'] = picked_batch_number
        elif picked_batch_number is not None and str(picked_batch_number).strip():
            picked_batch_number = str(picked_batch_number).strip()
            update_data['picked_batch_number'] = picked_batch_number
            batches = self.batch_service.repo.list(filters={
                'batch_number': picked_batch_number,
                'product_id': item.get('product_id')
            }, **_conn_kwargs(conn))
            if not batches:
                raise ValueError(f"Batch {picked_batch_number} not found for product {item.get('product_id')}")
            self._validate_batch_for_item(batches[0], item, qty_picked, warehouse_id=warehouse_id)
            update_data['picked_batch_id'] = batches[0]['id']

        # Dual UOM & Catch-weight scale weight handling
        if catch_weight_actual is not None:
            try:
                cw_act = float(catch_weight_actual)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid catch_weight_actual: {catch_weight_actual}")
            if cw_act < 0:
                raise ValueError(f"Catch weight cannot be negative: {catch_weight_actual}")
            update_data['catch_weight_actual'] = cw_act

            # Catch weight UOM
            if catch_weight_uom is not None and str(catch_weight_uom).strip():
                update_data['catch_weight_uom'] = str(catch_weight_uom).strip()
            elif not item.get('catch_weight_uom') and item.get('product_id') and hasattr(self, 'product_repo') and self.product_repo:
                try:
                    prod = self.product_repo.get(item.get('product_id'), **_conn_kwargs(conn))
                    if prod and prod.get('pricing_uom_id') and hasattr(self, 'uom_repo') and self.uom_repo:
                        uom_obj = self.uom_repo.get(prod.get('pricing_uom_id'), **_conn_kwargs(conn))
                        if uom_obj and uom_obj.get('uom_code'):
                            update_data['catch_weight_uom'] = uom_obj.get('uom_code')
                except Exception:
                    pass

            # Nominal weight
            if nominal_weight is not None:
                try:
                    nom_w = float(nominal_weight)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid nominal_weight: {nominal_weight}")
                if nom_w < 0:
                    raise ValueError(f"Nominal weight cannot be negative: {nominal_weight}")
                update_data['nominal_weight'] = nom_w
            elif item.get('nominal_weight') is not None:
                nom_w = float(item.get('nominal_weight'))
            else:
                nom_w = None
                if item.get('product_id') and hasattr(self, 'product_repo') and self.product_repo:
                    try:
                        prod = self.product_repo.get(item.get('product_id'), **_conn_kwargs(conn))
                        if prod and prod.get('nominal_weight') is not None:
                            unit_nominal = float(prod.get('nominal_weight'))
                            nom_w = round(unit_nominal * (qty_picked if qty_picked > 0 else ordered), 4)
                            update_data['nominal_weight'] = nom_w
                    except Exception:
                        pass

            # Tolerance percentage
            if tolerance_pct is not None:
                try:
                    tol_p = float(tolerance_pct)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid tolerance_pct: {tolerance_pct}")
                if tol_p < 0 or tol_p > 100:
                    raise ValueError(f"Tolerance percentage must be between 0 and 100: {tolerance_pct}")
                update_data['tolerance_pct'] = tol_p
            elif item.get('tolerance_pct') is not None:
                tol_p = float(item.get('tolerance_pct'))
            else:
                tol_p = None
                if item.get('product_id') and hasattr(self, 'product_repo') and self.product_repo:
                    try:
                        prod = self.product_repo.get(item.get('product_id'), **_conn_kwargs(conn))
                        if prod and prod.get('tolerance_pct') is not None:
                            tol_p = float(prod.get('tolerance_pct'))
                            update_data['tolerance_pct'] = tol_p
                    except Exception:
                        pass

            supervisor_approved = item.get('supervisor_approved', False)
            variance_pct, tol_status = self.evaluate_tolerance(
                nominal_weight=nom_w,
                actual_weight=cw_act,
                tolerance_pct=tol_p,
                supervisor_approved=supervisor_approved
            )
            update_data['tolerance_variance_pct'] = variance_pct
            update_data['tolerance_status'] = tol_status
        else:
            if catch_weight_uom is not None:
                update_data['catch_weight_uom'] = str(catch_weight_uom).strip()
            if nominal_weight is not None:
                update_data['nominal_weight'] = float(nominal_weight)
            if tolerance_pct is not None:
                update_data['tolerance_pct'] = float(tolerance_pct)

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
                label = item.get('product_name') or item.get('product_id') or f"id {item.get('id')}"
                unpicked.append(f"Item {label} has {item.get('qty_picked', 0)} picked of {item.get('qty_ordered', 0)} ordered")
        if unpicked:
            msg = f"Cannot complete pick list {pick_list_id}: {'; '.join(unpicked)}"
            logger.warning(msg)
            raise ValueError(msg)

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
                self.batch_service.adjustQuantity(batch_id, -picked_qty, **_conn_kwargs(conn))

        self.repo.update(pick_list_id, {'status': 'Completed'}, **_conn_kwargs(conn))
        self.order_repo.update(pl['sales_order_id'], {'status': 'Shipped'}, **_conn_kwargs(conn))
        logger.info(f"Completed pick list {pick_list_id} and updated sales order {pl['sales_order_id']} to Shipped")

        return self.get_with_items(pick_list_id, **_conn_kwargs(conn))

    def _calc_progress(self, items):
        if not items:
            return 100
        total_ordered = sum(i.get('qty_ordered', 0) for i in items)
        total_picked = sum(i.get('qty_picked', 0) for i in items)
        if total_ordered == 0:
            return 100
        return round((total_picked / total_ordered) * 100, 1)
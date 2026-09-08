import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from modules.core.services.base import CrudService
from modules.inventory.services.stock_movement import StockMovementService
from modules.core.repositories.base import CrudRepository

logger = logging.getLogger(__name__)

DELIVERY_REPO = CrudRepository(
    'T0077',
    business_columns=[
        'id', 'delivery_number', 'sales_order_id', 'delivery_date', 'warehouse_id',
        'freight_cost', 'delivery_route', 'actual_delivery_date', 'status', 'notes',
        'recipient_signature', 'delivery_photo_url', 'pod_timestamp', 'delivery_location',
        'payment_status', 'cod_cash_amount', 'cod_check_amount', 'cod_check_number',
        'cod_check_bank', 'driver_id'
    ],
)

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
    def __init__(self, repo=None, line_repo=None, pl_repo=None, pli_repo=None, stock_service=None):
        repo = repo or DELIVERY_REPO
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

    def capture_pod(
        self,
        delivery_id: int,
        signature: Optional[str] = None,
        photo_url: Optional[str] = None,
        location: Optional[str] = None,
        timestamp: Optional[Any] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Record recipient signature, delivery photo URL, location, and POD timestamp.
        Updates status to Delivered.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        delivery = self.repo.get(delivery_id, **kwargs)
        if not delivery:
            raise HTTPException(404, f"Delivery #{delivery_id} not found")

        pod_time = timestamp or datetime.now()
        if isinstance(pod_time, str):
            try:
                pod_time = datetime.fromisoformat(pod_time)
            except ValueError:
                pass

        if isinstance(pod_time, datetime):
            actual_date = pod_time.date()
        elif isinstance(pod_time, date):
            actual_date = pod_time
        else:
            actual_date = date.today()

        payload = {
            'status': 'Delivered',
            'actual_delivery_date': actual_date,
            'pod_timestamp': pod_time,
        }
        if signature is not None:
            payload['recipient_signature'] = signature
        if photo_url is not None:
            payload['delivery_photo_url'] = photo_url
        if location is not None:
            payload['delivery_location'] = location

        return self.update(delivery_id, payload, conn=conn)

    def log_cod_collection(
        self,
        delivery_id: int,
        cash_amount: float = 0.0,
        check_amount: float = 0.0,
        check_number: Optional[str] = None,
        check_bank: Optional[str] = None,
        payment_status: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Log cash or check collection at delivery time.
        Updates payment_status to 'Collected' / 'In Transit' (or custom status).
        """
        kwargs = {'conn': conn} if conn is not None else {}
        delivery = self.repo.get(delivery_id, **kwargs)
        if not delivery:
            raise HTTPException(404, f"Delivery #{delivery_id} not found")

        cash = float(cash_amount or 0.0)
        check = float(check_amount or 0.0)
        if cash < 0 or check < 0:
            raise HTTPException(400, "COD collection amounts cannot be negative")

        total_collected = cash + check
        target_status = payment_status or ("Collected" if total_collected > 0 else (delivery.get('payment_status') or 'Pending'))

        payload = {
            'cod_cash_amount': cash,
            'cod_check_amount': check,
            'payment_status': target_status,
        }
        if check_number is not None:
            payload['cod_check_number'] = check_number
        if check_bank is not None:
            payload['cod_check_bank'] = check_bank

        return self.update(delivery_id, payload, conn=conn)

    def _matches_date(self, record_date: Any, target_date: Any) -> bool:
        if record_date is None:
            return True
        if isinstance(record_date, str):
            r_str = record_date[:10]
        elif isinstance(record_date, (date, datetime)):
            r_str = record_date.strftime('%Y-%m-%d')
        else:
            r_str = str(record_date)[:10]

        if isinstance(target_date, str):
            t_str = target_date[:10]
        elif isinstance(target_date, (date, datetime)):
            t_str = target_date.strftime('%Y-%m-%d')
        else:
            t_str = str(target_date)[:10]

        return r_str == t_str

    def get_driver_handover_report(
        self,
        driver_id: int,
        delivery_date: Optional[Any] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Generate end-of-day driver handover report summarizing cash/check collections
        and status of assigned deliveries.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        target_date = delivery_date or date.today()

        deliveries = self.repo.list(filters={'driver_id': driver_id}, **kwargs)

        driver_deliveries = [
            d for d in deliveries
            if self._matches_date(d.get('delivery_date') or d.get('actual_delivery_date'), target_date)
        ]

        total_deliveries = len(driver_deliveries)
        completed_deliveries = len([d for d in driver_deliveries if d.get('status') == 'Delivered'])
        pending_deliveries = len([d for d in driver_deliveries if d.get('status') not in ('Delivered', 'Cancelled')])
        total_cash = sum(float(d.get('cod_cash_amount') or 0.0) for d in driver_deliveries)
        total_check = sum(float(d.get('cod_check_amount') or 0.0) for d in driver_deliveries)
        total_collected = total_cash + total_check
        reconciled_deliveries = len([d for d in driver_deliveries if d.get('payment_status') == 'Reconciled'])
        unreconciled_deliveries = len([
            d for d in driver_deliveries if d.get('payment_status') in ('Collected', 'In Transit', 'Pending')
        ])
        is_reconciled = (total_deliveries > 0 and reconciled_deliveries == total_deliveries)

        date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, (date, datetime)) else str(target_date)[:10]

        return {
            "driver_id": driver_id,
            "delivery_date": date_str,
            "total_deliveries": total_deliveries,
            "completed_deliveries": completed_deliveries,
            "pending_deliveries": pending_deliveries,
            "total_cash_collected": total_cash,
            "total_check_collected": total_check,
            "total_collected": total_collected,
            "reconciled_deliveries": reconciled_deliveries,
            "unreconciled_deliveries": unreconciled_deliveries,
            "is_reconciled": is_reconciled,
            "deliveries": driver_deliveries,
        }

    def reconcile_driver_cash(
        self,
        driver_id: int,
        delivery_date: Optional[Any] = None,
        cash_submitted: float = 0.0,
        check_submitted: float = 0.0,
        delivery_ids: Optional[List[int]] = None,
        notes: Optional[str] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Reconcile driver collected cash & checks against submitted physical cash & checks.
        Updates payment_status of collected deliveries to 'Reconciled'.
        """
        kwargs = {'conn': conn} if conn is not None else {}
        report = self.get_driver_handover_report(driver_id, delivery_date=delivery_date, **kwargs)

        expected_cash = report['total_cash_collected']
        expected_check = report['total_check_collected']
        expected_total = report['total_collected']

        cash_sub = float(cash_submitted or 0.0)
        check_sub = float(check_submitted or 0.0)
        total_sub = cash_sub + check_sub

        cash_discrepancy = cash_sub - expected_cash
        check_discrepancy = check_sub - expected_check
        total_discrepancy = total_sub - expected_total

        is_balanced = abs(cash_discrepancy) < 0.01 and abs(check_discrepancy) < 0.01

        target_deliveries = report['deliveries']
        if delivery_ids:
            target_deliveries = [d for d in target_deliveries if d.get('id') in delivery_ids]

        reconciled_deliveries = []
        for d in target_deliveries:
            if d.get('payment_status') in ('Collected', 'In Transit', 'Pending'):
                updated = self.update(d['id'], {'payment_status': 'Reconciled'}, **kwargs)
                if updated:
                    reconciled_deliveries.append(updated)

        return {
            "driver_id": driver_id,
            "delivery_date": report['delivery_date'],
            "expected_cash": expected_cash,
            "expected_check": expected_check,
            "expected_total": expected_total,
            "cash_submitted": cash_sub,
            "check_submitted": check_sub,
            "total_submitted": total_sub,
            "cash_discrepancy": cash_discrepancy,
            "check_discrepancy": check_discrepancy,
            "total_discrepancy": total_discrepancy,
            "is_balanced": is_balanced,
            "reconciled_count": len(reconciled_deliveries),
            "reconciled_delivery_ids": [d['id'] for d in reconciled_deliveries if 'id' in d],
            "status": "Reconciled" if is_balanced else "Discrepancy",
            "notes": notes,
        }


delivery_service = DeliveryService(DELIVERY_REPO)



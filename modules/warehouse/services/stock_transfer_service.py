"""
Nova ERP — Stock Transfer Domain Service
Multi-warehouse stock transfer workflows, in-transit inventory tracking,
discrepancy & loss recording, and status state machine.
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union
from fastapi import HTTPException
from pydantic import BaseModel

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.inventory.services.stock_movement import StockMovementService
from packages.database.sequence import generate_stock_transfer_number
from packages.database.connection import get_connection, release_connection

logger = logging.getLogger(__name__)

# Primary repositories for Stock Transfers
TRANSFER_REPO = CrudRepository(
    'T0108',
    business_columns=[
        'id', 'transfer_number', 'source_warehouse_id', 'destination_warehouse_id',
        'status', 'transfer_date', 'expected_delivery_date', 'carrier',
        'tracking_number', 'dispatched_at', 'dispatched_by', 'received_at',
        'received_by', 'notes', 'is_active', 'business_id'
    ]
)

TRANSFER_LINE_REPO = CrudRepository(
    'T0111',
    business_columns=[
        'id', 'transfer_id', 'product_id', 'qty_requested', 'qty_dispatched',
        'qty_received', 'qty_lost', 'loss_reason', 'loss_notes', 'batch_id',
        'batch_number', 'line_number', 'notes', 'is_active', 'business_id'
    ]
)

WH_REPO = CrudRepository(
    'T0008',
    business_columns=['id', 'name', 'location', 'warehouse_type', 'is_virtual', 'is_active', 'business_id']
)

PRODUCT_REPO = CrudRepository(
    'T0003',
    business_columns=[
        'id', 'name', 'sku', 'barcode', 'description', 'type', 'price',
        'cost_price', 'category', 'brand', 'is_active', 'business_id'
    ]
)

BATCH_REPO = CrudRepository(
    'T0088',
    business_columns=[
        'id', 'product_id', 'batch_number', 'expiry_date', 'manufacturing_date',
        'quantity', 'warehouse_id', 'status', 'notes', 'business_id'
    ]
)

USER_REPO = CrudRepository(
    'T0021',
    business_columns=['id', 'username', 'email', 'full_name', 'role', 'is_active']
)


def _conn_kwargs(conn):
    """Only forward conn to repositories when an explicit connection is provided."""
    return {'conn': conn} if conn is not None else {}


class StockTransferService(CrudService):
    """
    Domain service orchestrating multi-warehouse stock transfer lifecycles:
    Draft -> In Transit -> Received / Partially Received (or Cancelled).
    """

    def __init__(
        self,
        repo: CrudRepository = None,
        line_repo: CrudRepository = None,
        stock_service: StockMovementService = None,
        wh_repo: CrudRepository = None,
        product_repo: CrudRepository = None,
        batch_repo: CrudRepository = None,
        user_repo: CrudRepository = None,
    ):
        super().__init__(repo or TRANSFER_REPO)
        self.transfer_repo = self.repo
        self.line_repo = line_repo or TRANSFER_LINE_REPO
        self.stock_service = stock_service or StockMovementService()
        self.wh_repo = wh_repo or WH_REPO
        self.product_repo = product_repo or PRODUCT_REPO
        self.batch_repo = batch_repo or BATCH_REPO
        self.user_repo = user_repo or USER_REPO

    # -------------------------------------------------------------------------
    # Creation & Retrieval
    # -------------------------------------------------------------------------

    def create(self, payload: Union[dict, BaseModel], conn=None) -> dict:
        """Alias for create_transfer to support standard CrudService router integration."""
        return self.create_transfer(payload, conn=conn)

    def create_transfer(self, payload: Union[dict, BaseModel], conn=None) -> dict:
        """
        Create a new Stock Transfer Order (Draft) with itemized transfer lines.
        Auto-generates unique transfer_number if not provided.
        """
        data = payload.model_dump() if isinstance(payload, BaseModel) else dict(payload)

        source_wh_id = data.get('source_warehouse_id')
        dest_wh_id = data.get('destination_warehouse_id')

        if not source_wh_id or not dest_wh_id:
            raise HTTPException(400, "Source and destination warehouses are required")

        if int(source_wh_id) == int(dest_wh_id):
            raise HTTPException(400, "Source and destination warehouses must be different")

        # Validate warehouse existence
        src_wh = self.wh_repo.get(source_wh_id, **_conn_kwargs(conn))
        if not src_wh:
            raise HTTPException(404, f"Source warehouse #{source_wh_id} not found")
        dest_wh = self.wh_repo.get(dest_wh_id, **_conn_kwargs(conn))
        if not dest_wh:
            raise HTTPException(404, f"Destination warehouse #{dest_wh_id} not found")

        # Auto-generate transfer_number if omitted
        if not data.get('transfer_number') or not str(data.get('transfer_number')).strip():
            data['transfer_number'] = generate_stock_transfer_number(conn=conn)

        # Default header values
        data.setdefault('status', 'Draft')
        if not data.get('transfer_date'):
            data['transfer_date'] = date.today()

        lines_data = data.pop('lines', None) or []

        # Create transfer header
        transfer = self.repo.create(data, **_conn_kwargs(conn))
        transfer_id = transfer['id']

        # Create nested line items
        for idx, line in enumerate(lines_data, start=1):
            line_dict = line.model_dump() if isinstance(line, BaseModel) else dict(line)
            line_dict['transfer_id'] = transfer_id
            line_dict.setdefault('line_number', idx)
            line_dict.setdefault('qty_dispatched', 0.0)
            line_dict.setdefault('qty_received', 0.0)
            line_dict.setdefault('qty_lost', 0.0)

            qty_req = float(line_dict.get('qty_requested', 0) or 0)
            if qty_req <= 0:
                raise HTTPException(400, f"Line {idx}: Requested quantity must be greater than 0")

            if not line_dict.get('product_id'):
                raise HTTPException(400, f"Line {idx}: Product ID is required")

            self.line_repo.create(line_dict, **_conn_kwargs(conn))

        logger.info(f"Created stock transfer {transfer.get('transfer_number')} (ID: {transfer_id}) with {len(lines_data)} line(s)")
        return self.get_transfer_with_lines(transfer_id, conn=conn)

    def get_transfer_with_lines(self, transfer_id: int, conn=None) -> Optional[dict]:
        """
        Retrieve transfer header enriched with warehouse names, user names,
        line items, product descriptions, and aggregated quantities.
        """
        transfer = self.repo.get(transfer_id, **_conn_kwargs(conn))
        if not transfer:
            return None

        # Fetch lines ordered by line_number
        lines = self.line_repo.list(
            filters={'transfer_id': transfer_id},
            order_by='line_number',
            **_conn_kwargs(conn)
        )

        # Enrich header with warehouse names
        if transfer.get('source_warehouse_id'):
            src_wh = self.wh_repo.get(transfer['source_warehouse_id'], **_conn_kwargs(conn))
            transfer['source_warehouse_name'] = src_wh.get('name') if src_wh else None
        if transfer.get('destination_warehouse_id'):
            dest_wh = self.wh_repo.get(transfer['destination_warehouse_id'], **_conn_kwargs(conn))
            transfer['destination_warehouse_name'] = dest_wh.get('name') if dest_wh else None

        # Enrich header with user names
        if transfer.get('dispatched_by'):
            d_user = self.user_repo.get(transfer['dispatched_by'], **_conn_kwargs(conn))
            transfer['dispatched_by_name'] = (d_user.get('full_name') or d_user.get('username')) if d_user else None
        if transfer.get('received_by'):
            r_user = self.user_repo.get(transfer['received_by'], **_conn_kwargs(conn))
            transfer['received_by_name'] = (r_user.get('full_name') or r_user.get('username')) if r_user else None

        # Enrich lines with product details
        for line in lines:
            prod_id = line.get('product_id')
            if prod_id:
                prod = self.product_repo.get(prod_id, **_conn_kwargs(conn))
                if prod:
                    line['product_name'] = prod.get('name')
                    line['product_code'] = prod.get('sku')

        # Calculate totals
        transfer['total_requested_qty'] = sum(float(l.get('qty_requested', 0) or 0) for l in lines)
        transfer['total_dispatched_qty'] = sum(float(l.get('qty_dispatched', 0) or 0) for l in lines)
        transfer['total_received_qty'] = sum(float(l.get('qty_received', 0) or 0) for l in lines)
        transfer['total_lost_qty'] = sum(float(l.get('qty_lost', 0) or 0) for l in lines)
        transfer['lines_count'] = len(lines)
        transfer['lines'] = lines

        return transfer

    def list_with_lines(self, filters: dict = None, order_by: str = None, limit: int = 50, offset: int = 0, conn=None) -> List[dict]:
        """List stock transfers with enriched warehouse names and summary counts."""
        transfers = self.repo.list(filters=filters, order_by=order_by, limit=limit, offset=offset, **_conn_kwargs(conn))
        results = []
        for trf in transfers:
            detailed = self.get_transfer_with_lines(trf['id'], conn=conn)
            if detailed:
                results.append(detailed)
        return results

    def list_in_transit(self, conn=None) -> List[dict]:
        """Convenience method returning all stock transfers currently in-transit."""
        return self.list_with_lines(filters={'status': 'In Transit'}, order_by='transfer_date', conn=conn)

    # -------------------------------------------------------------------------
    # Line Item Management (Draft / Pending)
    # -------------------------------------------------------------------------

    def add_line(self, transfer_id: int, line_data: Union[dict, BaseModel], conn=None) -> dict:
        """Add a line item to an existing Draft transfer."""
        transfer = self.repo.get(transfer_id, **_conn_kwargs(conn))
        if not transfer:
            raise HTTPException(404, f"Stock transfer #{transfer_id} not found")
        if transfer.get('status') not in ('Draft', 'Pending'):
            raise HTTPException(400, f"Cannot add line to transfer with status '{transfer.get('status')}'")

        data = line_data.model_dump() if isinstance(line_data, BaseModel) else dict(line_data)
        data['transfer_id'] = transfer_id
        if not data.get('line_number'):
            existing_lines = self.line_repo.list(filters={'transfer_id': transfer_id}, **_conn_kwargs(conn))
            data['line_number'] = len(existing_lines) + 1

        data.setdefault('qty_dispatched', 0.0)
        data.setdefault('qty_received', 0.0)
        data.setdefault('qty_lost', 0.0)

        created_line = self.line_repo.create(data, **_conn_kwargs(conn))
        return created_line

    def update_line(self, line_id: int, line_data: Union[dict, BaseModel], conn=None) -> dict:
        """Update a line item on an existing Draft transfer."""
        line = self.line_repo.get(line_id, **_conn_kwargs(conn))
        if not line:
            raise HTTPException(404, f"Transfer line #{line_id} not found")

        transfer = self.repo.get(line['transfer_id'], **_conn_kwargs(conn))
        if not transfer or transfer.get('status') not in ('Draft', 'Pending'):
            raise HTTPException(400, "Cannot modify lines on a non-draft transfer")

        data = line_data.model_dump(exclude_unset=True) if isinstance(line_data, BaseModel) else dict(line_data)
        return self.line_repo.update(line_id, data, **_conn_kwargs(conn))

    def delete_line(self, line_id: int, conn=None) -> dict:
        """Remove a line item from a Draft transfer."""
        line = self.line_repo.get(line_id, **_conn_kwargs(conn))
        if not line:
            raise HTTPException(404, f"Transfer line #{line_id} not found")

        transfer = self.repo.get(line['transfer_id'], **_conn_kwargs(conn))
        if not transfer or transfer.get('status') not in ('Draft', 'Pending'):
            raise HTTPException(400, "Cannot delete lines from a non-draft transfer")

        self.line_repo.delete(line_id, **_conn_kwargs(conn))
        return {'success': True, 'id': line_id}

    # -------------------------------------------------------------------------
    # Transfer Lifecycle Execution: Dispatch, Receive, Cancel
    # -------------------------------------------------------------------------

    def dispatch_transfer(
        self,
        transfer_id: int,
        dispatch_data: Optional[Union[dict, BaseModel]] = None,
        conn=None,
    ) -> dict:
        """
        Dispatches inventory from source warehouse to in-transit:
        - Validates transfer status is Draft / Pending.
        - Deducts stock from source warehouse.
        - Increments in_transit_qty at destination warehouse.
        - Records 'Transfer Out' stock movements.
        - Transitions transfer status to 'In Transit'.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            transfer = self.repo.get(transfer_id, **_conn_kwargs(conn))
            if not transfer:
                raise HTTPException(404, f"Stock transfer #{transfer_id} not found")

            current_status = transfer.get('status', '').strip()
            if current_status not in ('Draft', 'Pending'):
                raise HTTPException(
                    400,
                    f"Cannot dispatch transfer with status '{current_status}'. Status must be 'Draft' or 'Pending'."
                )

            lines = self.line_repo.list(filters={'transfer_id': transfer_id}, order_by='line_number', **_conn_kwargs(conn))
            if not lines:
                raise HTTPException(400, "Cannot dispatch transfer with no line items")

            disp_dict = {}
            if dispatch_data:
                disp_dict = dispatch_data.model_dump() if isinstance(dispatch_data, BaseModel) else dict(dispatch_data)

            # Update itemized line quantities if provided
            disp_lines_input = disp_dict.get('lines')
            if disp_lines_input:
                line_map = {l['id']: l for l in lines}
                for d_line in disp_lines_input:
                    d_item = d_line.model_dump() if isinstance(d_line, BaseModel) else dict(d_line)
                    target_line_id = d_item.get('line_id') or d_item.get('id')
                    if target_line_id and target_line_id in line_map:
                        q_disp = float(d_item.get('qty_dispatched', 0) or 0)
                        update_fields = {'qty_dispatched': q_disp}
                        if d_item.get('batch_id'):
                            update_fields['batch_id'] = d_item['batch_id']
                        if d_item.get('batch_number'):
                            update_fields['batch_number'] = d_item['batch_number']
                        self.line_repo.update(target_line_id, update_fields, **_conn_kwargs(conn))
                        line_map[target_line_id].update(update_fields)
            else:
                # Default qty_dispatched to qty_requested for all lines
                for l in lines:
                    q_req = float(l.get('qty_requested', 0) or 0)
                    self.line_repo.update(l['id'], {'qty_dispatched': q_req}, **_conn_kwargs(conn))
                    l['qty_dispatched'] = q_req

            source_wh_id = transfer['source_warehouse_id']
            dest_wh_id = transfer['destination_warehouse_id']
            dispatched_by = disp_dict.get('dispatched_by') or transfer.get('dispatched_by')
            transfer_num = transfer.get('transfer_number')

            total_dispatched = 0.0
            for line in lines:
                qty_disp = float(line.get('qty_dispatched', 0) or 0)
                if qty_disp <= 0:
                    raise HTTPException(
                        400,
                        f"Dispatched quantity for product {line.get('product_id')} must be greater than 0"
                    )

                # Deduct source stock and increment destination in-transit
                self.stock_service.transfer_dispatch(
                    product_id=line['product_id'],
                    source_warehouse_id=source_wh_id,
                    destination_warehouse_id=dest_wh_id,
                    qty=qty_disp,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    description=f"Transfer Dispatch: {transfer_num}",
                    user_id=dispatched_by,
                    conn=conn,
                )

                # Batch deduction at source warehouse if batch tracked
                batch_id = line.get('batch_id')
                if batch_id and hasattr(self, 'batch_repo') and self.batch_repo:
                    try:
                        batch = self.batch_repo.get(batch_id, **_conn_kwargs(conn))
                        if batch:
                            cur_b_qty = float(batch.get('quantity') or 0)
                            new_b_qty = max(0.0, cur_b_qty - qty_disp)
                            self.batch_repo.update(
                                batch_id,
                                {'quantity': new_b_qty, 'status': 'Depleted' if new_b_qty == 0 else 'Partially Used'},
                                **_conn_kwargs(conn)
                            )
                    except Exception as b_err:
                        logger.warning(f"Batch adjustment skipped during dispatch for batch {batch_id}: {b_err}")

                total_dispatched += qty_disp

            if total_dispatched <= 0:
                raise HTTPException(400, "Total dispatched quantity must be greater than 0")

            # Update transfer header
            header_update = {
                'status': 'In Transit',
                'dispatched_at': disp_dict.get('dispatched_at') or datetime.now(),
            }
            if dispatched_by:
                header_update['dispatched_by'] = dispatched_by
            if disp_dict.get('carrier'):
                header_update['carrier'] = disp_dict['carrier']
            if disp_dict.get('tracking_number'):
                header_update['tracking_number'] = disp_dict['tracking_number']
            if disp_dict.get('notes'):
                existing_notes = transfer.get('notes') or ''
                header_update['notes'] = f"{existing_notes}\n{disp_dict['notes']}".strip()

            self.repo.update(transfer_id, header_update, **_conn_kwargs(conn))

            if should_release:
                conn.commit()

            logger.info(f"Dispatched stock transfer {transfer_num} (ID: {transfer_id}) with {total_dispatched} unit(s)")
            return self.get_transfer_with_lines(transfer_id, conn=conn)

        except Exception as e:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Failed to dispatch transfer {transfer_id}: {e}")
            raise
        finally:
            if should_release:
                release_connection(conn)

    def receive_transfer(
        self,
        transfer_id: int,
        receive_data: Optional[Union[dict, BaseModel]] = None,
        conn=None,
    ) -> dict:
        """
        Receives inventory at destination warehouse:
        - Validates transfer status is 'In Transit'.
        - Decrements in_transit_qty at destination warehouse.
        - Adds received quantity to destination available inventory.
        - Records 'Transfer In' stock movements.
        - Logs any loss/damage discrepancies as 'Transfer Loss' with reason codes.
        - Transitions transfer status to 'Received' or 'Partially Received'.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            transfer = self.repo.get(transfer_id, **_conn_kwargs(conn))
            if not transfer:
                raise HTTPException(404, f"Stock transfer #{transfer_id} not found")

            current_status = transfer.get('status', '').strip()
            if current_status != 'In Transit':
                raise HTTPException(
                    400,
                    f"Cannot receive transfer with status '{current_status}'. Status must be 'In Transit'."
                )

            lines = self.line_repo.list(filters={'transfer_id': transfer_id}, order_by='line_number', **_conn_kwargs(conn))
            if not lines:
                raise HTTPException(400, "Cannot receive transfer with no line items")

            rec_dict = {}
            if receive_data:
                rec_dict = receive_data.model_dump() if isinstance(receive_data, BaseModel) else dict(receive_data)

            # Process itemized receipt quantities and losses
            rec_lines_input = rec_dict.get('lines')
            losses_input = rec_dict.get('losses') or []

            loss_map_by_product = {loss.get('product_id'): loss for loss in losses_input if isinstance(loss, dict) and loss.get('product_id')}
            loss_map_by_line = {loss.get('line_id'): loss for loss in losses_input if isinstance(loss, dict) and loss.get('line_id')}

            if rec_lines_input:
                line_map = {l['id']: l for l in lines}
                for r_line in rec_lines_input:
                    r_item = r_line.model_dump() if isinstance(r_line, BaseModel) else dict(r_line)
                    target_line_id = r_item.get('line_id') or r_item.get('id')
                    if target_line_id and target_line_id in line_map:
                        q_rec = float(r_item.get('qty_received', 0) or 0)
                        q_lost = float(r_item.get('qty_lost', 0) or 0)
                        loss_reason = r_item.get('loss_reason')
                        loss_notes = r_item.get('loss_notes')

                        # Check if losses were passed in separate losses array
                        if q_lost == 0:
                            matched_loss = loss_map_by_line.get(target_line_id) or loss_map_by_product.get(line_map[target_line_id].get('product_id'))
                            if matched_loss:
                                q_lost = float(matched_loss.get('qty_lost', 0) or 0)
                                loss_reason = matched_loss.get('loss_reason') or loss_reason
                                loss_notes = matched_loss.get('loss_notes') or loss_notes

                        update_fields = {
                            'qty_received': q_rec,
                            'qty_lost': q_lost,
                            'loss_reason': loss_reason,
                            'loss_notes': loss_notes,
                        }
                        if r_item.get('batch_id'):
                            update_fields['batch_id'] = r_item['batch_id']
                        if r_item.get('batch_number'):
                            update_fields['batch_number'] = r_item['batch_number']

                        self.line_repo.update(target_line_id, update_fields, **_conn_kwargs(conn))
                        line_map[target_line_id].update(update_fields)
            else:
                # Default full receipt: qty_received = qty_dispatched, qty_lost = 0
                for l in lines:
                    q_disp = float(l.get('qty_dispatched', 0) or l.get('qty_requested', 0) or 0)
                    self.line_repo.update(l['id'], {'qty_received': q_disp, 'qty_lost': 0.0}, **_conn_kwargs(conn))
                    l['qty_received'] = q_disp
                    l['qty_lost'] = 0.0

            dest_wh_id = transfer['destination_warehouse_id']
            src_wh_id = transfer['source_warehouse_id']
            received_by = rec_dict.get('received_by') or transfer.get('received_by')
            transfer_num = transfer.get('transfer_number')

            total_received = 0.0
            total_dispatched = 0.0
            total_lost = 0.0

            for line in lines:
                qty_disp = float(line.get('qty_dispatched', 0) or line.get('qty_requested', 0) or 0)
                qty_rec = float(line.get('qty_received', 0) or 0)
                qty_lost = float(line.get('qty_lost', 0) or 0)
                loss_reason = line.get('loss_reason')
                loss_notes = line.get('loss_notes')

                total_dispatched += qty_disp
                total_received += qty_rec
                total_lost += qty_lost

                # 1. Transfer In movement (decrements in_transit by qty_disp, adds qty_rec to destination stock)
                self.stock_service.transfer_receive(
                    product_id=line['product_id'],
                    destination_warehouse_id=dest_wh_id,
                    qty_received=qty_rec,
                    qty_dispatched=qty_disp,
                    source_warehouse_id=src_wh_id,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    description=f"Transfer Receipt: {transfer_num}",
                    user_id=received_by,
                    conn=conn,
                )

                # 2. Record loss / transit damage movement if discrepancy exists
                if qty_lost > 0:
                    self.stock_service.record_transfer_loss(
                        product_id=line['product_id'],
                        warehouse_id=dest_wh_id,
                        qty_lost=qty_lost,
                        loss_reason=loss_reason,
                        loss_notes=loss_notes,
                        reference_type='StockTransfer',
                        reference_id=transfer_id,
                        description=f"Transfer Discrepancy: {transfer_num}",
                        decrement_in_transit=False,
                        user_id=received_by,
                        conn=conn,
                    )

                # 3. Batch registration/quantity increment at destination warehouse
                batch_num = line.get('batch_number')
                if batch_num and qty_rec > 0 and hasattr(self, 'batch_repo') and self.batch_repo:
                    self._register_destination_batch(line, dest_wh_id, qty_rec, conn=conn)

            # Determine final status
            if total_received == total_dispatched and total_lost == 0:
                final_status = 'Received'
            elif (total_received + total_lost) >= total_dispatched:
                # All items accounted for, with some damaged / lost in transit
                final_status = 'Received'
            elif total_received > 0:
                final_status = 'Partially Received'
            else:
                final_status = 'Received'

            # Update transfer header
            header_update = {
                'status': final_status,
                'received_at': rec_dict.get('received_at') or datetime.now(),
            }
            if received_by:
                header_update['received_by'] = received_by
            if rec_dict.get('notes'):
                existing_notes = transfer.get('notes') or ''
                header_update['notes'] = f"{existing_notes}\n{rec_dict['notes']}".strip()

            self.repo.update(transfer_id, header_update, **_conn_kwargs(conn))

            if should_release:
                conn.commit()

            logger.info(
                f"Received stock transfer {transfer_num} (ID: {transfer_id}): "
                f"Received={total_received}, Lost={total_lost}, Status={final_status}"
            )
            return self.get_transfer_with_lines(transfer_id, conn=conn)

        except Exception as e:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Failed to receive transfer {transfer_id}: {e}")
            raise
        finally:
            if should_release:
                release_connection(conn)

    def cancel_transfer(
        self,
        transfer_id: int,
        reason: Optional[str] = None,
        conn=None,
    ) -> dict:
        """
        Cancels a stock transfer order:
        - If 'In Transit': Reverses inventory deductions (restores source stock & clears in-transit).
        - If 'Draft' or 'Pending': Simply transitions status to 'Cancelled'.
        - If already 'Received' or 'Partially Received': Rejects cancellation.
        """
        should_release = False
        if conn is None:
            conn = get_connection()
            should_release = True

        try:
            transfer = self.repo.get(transfer_id, **_conn_kwargs(conn))
            if not transfer:
                raise HTTPException(404, f"Stock transfer #{transfer_id} not found")

            current_status = transfer.get('status', '').strip()
            if current_status in ('Received', 'Partially Received'):
                raise HTTPException(
                    400,
                    f"Cannot cancel transfer with status '{current_status}'. Inventory has already been received."
                )

            if current_status == 'Cancelled':
                return self.get_transfer_with_lines(transfer_id, conn=conn)

            # If In Transit, reverse physical inventory dispatch
            if current_status == 'In Transit':
                lines = self.line_repo.list(filters={'transfer_id': transfer_id}, **_conn_kwargs(conn))
                src_wh_id = transfer['source_warehouse_id']
                dest_wh_id = transfer['destination_warehouse_id']
                transfer_num = transfer.get('transfer_number')

                for line in lines:
                    qty_disp = float(line.get('qty_dispatched', 0) or 0)
                    if qty_disp > 0:
                        self.stock_service.cancel_transfer_dispatch(
                            product_id=line['product_id'],
                            source_warehouse_id=src_wh_id,
                            destination_warehouse_id=dest_wh_id,
                            qty=qty_disp,
                            reference_type='StockTransfer',
                            reference_id=transfer_id,
                            description=f"Transfer Cancelled: {transfer_num} ({reason or 'No reason provided'})",
                            conn=conn,
                        )

                        # Restore batch quantity at source if batch tracked
                        batch_id = line.get('batch_id')
                        if batch_id and hasattr(self, 'batch_repo') and self.batch_repo:
                            try:
                                batch = self.batch_repo.get(batch_id, **_conn_kwargs(conn))
                                if batch:
                                    cur_b_qty = float(batch.get('quantity') or 0)
                                    self.batch_repo.update(
                                        batch_id,
                                        {'quantity': cur_b_qty + qty_disp, 'status': 'Available'},
                                        **_conn_kwargs(conn)
                                    )
                            except Exception as b_err:
                                logger.warning(f"Batch restoration skipped during cancellation for batch {batch_id}: {b_err}")

            # Update transfer header
            existing_notes = transfer.get('notes') or ''
            cancel_note = f"[Cancelled: {reason}]" if reason else "[Cancelled]"
            new_notes = f"{existing_notes} {cancel_note}".strip()

            self.repo.update(transfer_id, {'status': 'Cancelled', 'notes': new_notes}, **_conn_kwargs(conn))

            if should_release:
                conn.commit()

            logger.info(f"Cancelled stock transfer {transfer.get('transfer_number')} (ID: {transfer_id})")
            return self.get_transfer_with_lines(transfer_id, conn=conn)

        except Exception as e:
            if should_release:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"Failed to cancel transfer {transfer_id}: {e}")
            raise
        finally:
            if should_release:
                release_connection(conn)

    # -------------------------------------------------------------------------
    # Batch Synchronization Helper
    # -------------------------------------------------------------------------

    def _register_destination_batch(self, line: dict, dest_wh_id: int, qty_received: float, conn=None):
        """Creates or increments batch lot record at destination warehouse upon receipt."""
        batch_num = line.get('batch_number')
        prod_id = line.get('product_id')
        if not batch_num or not prod_id or qty_received <= 0:
            return

        batch_num_clean = str(batch_num).strip()
        existing = self.batch_repo.list(
            filters={'product_id': prod_id, 'batch_number': batch_num_clean, 'warehouse_id': dest_wh_id},
            **_conn_kwargs(conn)
        )

        if existing:
            batch = existing[0]
            new_qty = float(batch.get('quantity') or 0) + float(qty_received)
            self.batch_repo.update(
                batch['id'],
                {'quantity': new_qty, 'status': 'Available'},
                **_conn_kwargs(conn)
            )
        else:
            # Look up dates from source batch if batch_id provided
            mfg_date = None
            exp_date = None
            if line.get('batch_id'):
                try:
                    src_batch = self.batch_repo.get(line['batch_id'], **_conn_kwargs(conn))
                    if src_batch:
                        mfg_date = src_batch.get('manufacturing_date')
                        exp_date = src_batch.get('expiry_date')
                except Exception:
                    pass

            self.batch_repo.create({
                'product_id': prod_id,
                'batch_number': batch_num_clean,
                'manufacturing_date': mfg_date,
                'expiry_date': exp_date,
                'quantity': qty_received,
                'warehouse_id': dest_wh_id,
                'status': 'Available'
            }, **_conn_kwargs(conn))

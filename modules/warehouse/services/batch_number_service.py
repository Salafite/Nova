from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository


class BatchNumberService(CrudService):
    def __init__(self, repo, grn_line_repo=None, grn_repo=None, po_repo=None, supplier_repo=None,
                 pli_repo=None, pl_repo=None, order_repo=None, customer_repo=None,
                 invoice_repo=None, product_repo=None, wh_repo=None):
        super().__init__(repo)
        self.grn_line_repo = grn_line_repo or CrudRepository('T0076', business_columns=[
            'id', 'receipt_id', 'purchase_order_line_id', 'product_id', 'product_name',
            'qty_received', 'qty_ordered', 'uom_id', 'line_number',
            'batch_number', 'manufacturing_date', 'expiry_date'
        ])
        self.grn_repo = grn_repo or CrudRepository('T0075', business_columns=[
            'id', 'receipt_number', 'purchase_order_id', 'receipt_date', 'warehouse_id', 'status', 'notes'
        ])
        self.po_repo = po_repo or CrudRepository('T0014', business_columns=[
            'id', 'order_number', 'supplier_id', 'total', 'status', 'order_date', 'expected_date'
        ])
        self.supplier_repo = supplier_repo or CrudRepository('T0011', business_columns=[
            'id', 'name', 'category', 'phone', 'email', 'payment_terms', 'rating'
        ])
        self.pli_repo = pli_repo or CrudRepository('T0102', business_columns=[
            'id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name',
            'qty_ordered', 'qty_picked', 'line_number',
            'batch_id', 'batch_number', 'expiry_date', 'picked_batch_id', 'picked_batch_number'
        ])
        self.pl_repo = pl_repo or CrudRepository('T0101', business_columns=[
            'id', 'pick_list_number', 'sales_order_id', 'warehouse_id', 'status', 'notes'
        ])
        self.order_repo = order_repo or CrudRepository('T0012', business_columns=[
            'id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal', 'tax', 'grand_total', 'status', 'order_date', 'notes'
        ])
        self.customer_repo = customer_repo or CrudRepository('T0010', business_columns=[
            'id', 'name', 'group_name', 'phone', 'email', 'credit_limit', 'balance'
        ])
        self.invoice_repo = invoice_repo or CrudRepository('T0090', business_columns=[
            'id', 'invoice_number', 'invoice_type', 'partner_id', 'sales_order_id', 'issue_date', 'due_date', 'total_amount', 'status', 'notes'
        ])
        self.product_repo = product_repo or CrudRepository('T0003', business_columns=[
            'id', 'name', 'sku', 'price', 'cost_price', 'category', 'brand'
        ])
        self.wh_repo = wh_repo or CrudRepository('T0008', business_columns=[
            'id', 'name', 'location', 'is_active'
        ])

    def create(self, payload: dict):
        existing = self.repo.list(filters={
            'product_id': payload.get('product_id'),
            'batch_number': payload.get('batch_number')
        })
        if existing:
            raise ValueError(f"Batch number '{payload.get('batch_number')}' already exists for this product")
        payload.setdefault('status', 'Available')
        return super().create(payload)

    def adjustQuantity(self, id_val, qty: float):
        batch = self.get(id_val)
        if not batch:
            raise ValueError('Batch not found')
        new_qty = batch['quantity'] + qty
        if new_qty < 0:
            raise ValueError('Resulting quantity cannot be below 0')
        payload = {'quantity': new_qty}
        if new_qty == 0:
            payload['status'] = 'Depleted'
        elif batch['quantity'] > 0 and new_qty > 0 and batch['status'] not in ('Expired',):
            payload['status'] = 'Available' if batch.get('quantity', 0) == 0 else 'Partially Used'
        return self.update(id_val, payload)

    def allocate_fefo_lots(self, product_id: int, warehouse_id: int = None, qty_needed: float = 0.0) -> list[dict]:
        """
        Allocate lots using FEFO (First-Expired-First-Out).
        Queries available batches sorted by expiry_date ASC NULLS LAST, id ASC,
        filtering for status='Available' (and non-depleted) with quantity > 0.
        Returns a list of lot allocations across single or multiple batches to fulfill qty_needed.
        """
        if not product_id or qty_needed is None or float(qty_needed) <= 0:
            return []

        filters = {'product_id': product_id}
        if warehouse_id is not None:
            filters['warehouse_id'] = warehouse_id

        batches = self.repo.list(filters=filters)

        # Filter for status='Available' (or active available) and quantity > 0
        available_batches = [
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

        available_batches.sort(key=sort_key)

        allocations = []
        remaining = float(qty_needed)

        for batch in available_batches:
            if remaining <= 0:
                break
            batch_qty = float(batch.get('quantity') or 0)
            allocated = min(remaining, batch_qty)
            allocations.append({
                'batch_id': batch['id'],
                'batch_number': batch.get('batch_number'),
                'expiry_date': batch.get('expiry_date'),
                'manufacturing_date': batch.get('manufacturing_date'),
                'quantity': allocated,
                'allocated_qty': allocated,
                'available_quantity': batch_qty,
                'warehouse_id': batch.get('warehouse_id'),
            })
            remaining -= allocated

        return allocations

    def get_recall_report(self, batch_number: str = None, batch_id: int = None, product_id: int = None) -> dict:
        """
        Generate an end-to-end food recall and lot traceability report.
        Identifies inbound suppliers/goods receipts, current warehouse stock,
        and outbound pick lists, sales orders, invoices, and affected customer contact info.
        """
        if not batch_number and not batch_id:
            raise ValueError("Either batch_number or batch_id must be provided")

        batch = None
        if batch_id is not None:
            batch = self.get(batch_id)
            if not batch:
                raise ValueError(f"Batch with ID {batch_id} not found")
            batch_number = batch.get('batch_number')
            if not product_id:
                product_id = batch.get('product_id')
        elif batch_number is not None:
            batch_number = str(batch_number).strip()
            filters = {'batch_number': batch_number}
            if product_id is not None:
                filters['product_id'] = product_id
            batches = self.repo.list(filters=filters)
            if batches:
                batch = batches[0]
                batch_id = batch.get('id')
                if not product_id:
                    product_id = batch.get('product_id')

        # If batch not found in T0088, check if any goods receipt or pick list has this batch_number
        grn_lines_raw = []
        if batch_number:
            try:
                grn_lines_raw = self.grn_line_repo.list(filters={'batch_number': batch_number})
            except Exception:
                grn_lines_raw = []

        pli_raw = []
        pli_picked_raw = []
        if batch_id is not None:
            try:
                pli_raw.extend(self.pli_repo.list(filters={'batch_id': batch_id}))
            except Exception:
                pass
            try:
                pli_picked_raw.extend(self.pli_repo.list(filters={'picked_batch_id': batch_id}))
            except Exception:
                pass
        if batch_number:
            try:
                pli_raw.extend(self.pli_repo.list(filters={'batch_number': batch_number}))
            except Exception:
                pass
            try:
                pli_picked_raw.extend(self.pli_repo.list(filters={'picked_batch_number': batch_number}))
            except Exception:
                pass

        if not batch and not grn_lines_raw and not pli_raw and not pli_picked_raw:
            raise ValueError(f"Batch '{batch_number}' not found")

        # Deduplicate pick list items
        seen_pli_ids = set()
        outbound_items = []
        for item in pli_raw + pli_picked_raw:
            item_id = item.get('id')
            if item_id and item_id not in seen_pli_ids:
                seen_pli_ids.add(item_id)
                outbound_items.append(item)
            elif not item_id and item not in outbound_items:
                outbound_items.append(item)

        if product_id:
            grn_lines_raw = [l for l in grn_lines_raw if not l.get('product_id') or l.get('product_id') == product_id]
            outbound_items = [i for i in outbound_items if not i.get('product_id') or i.get('product_id') == product_id]

        # Product details
        product = None
        if product_id:
            try:
                product = self.product_repo.get(product_id)
            except Exception:
                product = None

        product_name = (batch.get('product_name') if batch and batch.get('product_name') else None) or \
                       (product.get('name') if product else None) or \
                       (grn_lines_raw[0].get('product_name') if grn_lines_raw and grn_lines_raw[0].get('product_name') else None) or \
                       (outbound_items[0].get('product_name') if outbound_items and outbound_items[0].get('product_name') else None) or ''

        product_sku = product.get('sku') if product else ''
        product_category = product.get('category') if product else ''

        # Warehouse info
        wh_id = batch.get('warehouse_id') if batch else None
        warehouse = None
        if wh_id:
            try:
                warehouse = self.wh_repo.get(wh_id)
            except Exception:
                warehouse = None
        warehouse_name = warehouse.get('name') if warehouse else ''

        # Inbound trace
        inbound_trace = []
        for line in grn_lines_raw:
            receipt = None
            if line.get('receipt_id'):
                try:
                    receipt = self.grn_repo.get(line['receipt_id'])
                except Exception:
                    receipt = None

            po = None
            if receipt and receipt.get('purchase_order_id'):
                try:
                    po = self.po_repo.get(receipt['purchase_order_id'])
                except Exception:
                    po = None

            supplier = None
            if po and po.get('supplier_id'):
                try:
                    supplier = self.supplier_repo.get(po['supplier_id'])
                except Exception:
                    supplier = None

            wh = None
            rec_wh_id = receipt.get('warehouse_id') if receipt else None
            if rec_wh_id:
                try:
                    wh = self.wh_repo.get(rec_wh_id)
                except Exception:
                    wh = None

            inbound_trace.append({
                'receipt_id': receipt.get('id') if receipt else line.get('receipt_id'),
                'receipt_number': receipt.get('receipt_number') if receipt else None,
                'receipt_date': str(receipt.get('receipt_date')) if receipt and receipt.get('receipt_date') else None,
                'receipt_status': receipt.get('status') if receipt else None,
                'purchase_order_id': po.get('id') if po else (receipt.get('purchase_order_id') if receipt else None),
                'po_number': po.get('order_number') if po else None,
                'po_status': po.get('status') if po else None,
                'supplier_id': supplier.get('id') if supplier else (po.get('supplier_id') if po else None),
                'supplier_name': supplier.get('name') if supplier else (f"Supplier #{po.get('supplier_id')}" if po and po.get('supplier_id') else 'Unknown Supplier'),
                'supplier_email': supplier.get('email') if supplier else None,
                'supplier_phone': supplier.get('phone') if supplier else None,
                'supplier_category': supplier.get('category') if supplier else None,
                'warehouse_id': rec_wh_id,
                'warehouse_name': wh.get('name') if wh else None,
                'qty_received': float(line.get('qty_received') or 0),
                'manufacturing_date': str(line.get('manufacturing_date')) if line.get('manufacturing_date') else None,
                'expiry_date': str(line.get('expiry_date')) if line.get('expiry_date') else None,
            })

        # Outbound trace
        outbound_trace = []
        for item in outbound_items:
            pl = None
            if item.get('pick_list_id'):
                try:
                    pl = self.pl_repo.get(item['pick_list_id'])
                except Exception:
                    pl = None

            so = None
            if pl and pl.get('sales_order_id'):
                try:
                    so = self.order_repo.get(pl['sales_order_id'])
                except Exception:
                    so = None

            customer = None
            if so and so.get('customer_id'):
                try:
                    customer = self.customer_repo.get(so['customer_id'])
                except Exception:
                    customer = None

            wh = None
            pl_wh_id = pl.get('warehouse_id') if pl else None
            if pl_wh_id:
                try:
                    wh = self.wh_repo.get(pl_wh_id)
                except Exception:
                    wh = None

            invoices = []
            if so and so.get('id'):
                try:
                    invoices = self.invoice_repo.list(filters={'sales_order_id': so['id']})
                except Exception:
                    invoices = []
            primary_inv = invoices[0] if invoices else None

            qty_picked = float(item.get('qty_picked') or 0)
            qty_ordered = float(item.get('qty_ordered') or 0)

            outbound_trace.append({
                'pick_list_item_id': item.get('id'),
                'pick_list_id': pl.get('id') if pl else item.get('pick_list_id'),
                'pick_list_number': pl.get('pick_list_number') if pl else None,
                'pick_list_status': pl.get('status') if pl else None,
                'pick_list_date': str(pl.get('created_at')) if pl and pl.get('created_at') else None,
                'sales_order_id': so.get('id') if so else (pl.get('sales_order_id') if pl else None),
                'sales_order_number': so.get('order_number') if so else None,
                'order_date': str(so.get('order_date')) if so and so.get('order_date') else None,
                'order_status': so.get('status') if so else None,
                'customer_id': customer.get('id') if customer else (so.get('customer_id') if so else None),
                'customer_name': customer.get('name') if customer else (f"Customer #{so.get('customer_id')}" if so and so.get('customer_id') else 'Unknown Customer'),
                'customer_email': customer.get('email') if customer else None,
                'customer_phone': customer.get('phone') if customer else None,
                'customer_group': customer.get('group_name') if customer else None,
                'warehouse_id': pl_wh_id,
                'warehouse_name': wh.get('name') if wh else None,
                'qty_ordered': qty_ordered,
                'qty_picked': qty_picked,
                'suggested_batch_number': item.get('batch_number'),
                'picked_batch_number': item.get('picked_batch_number') or item.get('batch_number'),
                'invoice_id': primary_inv.get('id') if primary_inv else None,
                'invoice_number': primary_inv.get('invoice_number') if primary_inv else None,
                'invoice_status': primary_inv.get('status') if primary_inv else None,
            })

        # Build affected customers summary
        customer_map = {}
        for entry in outbound_trace:
            cid = entry.get('customer_id') or entry.get('customer_name')
            if cid not in customer_map:
                customer_map[cid] = {
                    'customer_id': entry.get('customer_id'),
                    'customer_name': entry.get('customer_name'),
                    'email': entry.get('customer_email'),
                    'phone': entry.get('customer_phone'),
                    'group_name': entry.get('customer_group'),
                    'total_qty_picked': 0.0,
                    'total_qty_ordered': 0.0,
                    'orders': {},
                    'pick_lists': {},
                    'invoices': {}
                }
            cust = customer_map[cid]
            cust['total_qty_picked'] += entry.get('qty_picked', 0.0)
            cust['total_qty_ordered'] += entry.get('qty_ordered', 0.0)

            if entry.get('sales_order_id') or entry.get('sales_order_number'):
                so_key = entry.get('sales_order_id') or entry.get('sales_order_number')
                if so_key not in cust['orders']:
                    cust['orders'][so_key] = {
                        'sales_order_id': entry.get('sales_order_id'),
                        'order_number': entry.get('sales_order_number'),
                        'order_date': entry.get('order_date'),
                        'status': entry.get('order_status'),
                        'qty_picked': entry.get('qty_picked', 0.0)
                    }
                else:
                    cust['orders'][so_key]['qty_picked'] += entry.get('qty_picked', 0.0)

            if entry.get('pick_list_id') or entry.get('pick_list_number'):
                pl_key = entry.get('pick_list_id') or entry.get('pick_list_number')
                if pl_key not in cust['pick_lists']:
                    cust['pick_lists'][pl_key] = {
                        'pick_list_id': entry.get('pick_list_id'),
                        'pick_list_number': entry.get('pick_list_number'),
                        'status': entry.get('pick_list_status')
                    }

            if entry.get('invoice_id') or entry.get('invoice_number'):
                inv_key = entry.get('invoice_id') or entry.get('invoice_number')
                if inv_key not in cust['invoices']:
                    cust['invoices'][inv_key] = {
                        'invoice_id': entry.get('invoice_id'),
                        'invoice_number': entry.get('invoice_number'),
                        'status': entry.get('invoice_status')
                    }

        affected_customers = []
        for cust in customer_map.values():
            affected_customers.append({
                'customer_id': cust['customer_id'],
                'customer_name': cust['customer_name'],
                'email': cust['email'],
                'phone': cust['phone'],
                'group_name': cust['group_name'],
                'total_qty_picked': round(cust['total_qty_picked'], 2),
                'total_qty_ordered': round(cust['total_qty_ordered'], 2),
                'orders': list(cust['orders'].values()),
                'pick_lists': list(cust['pick_lists'].values()),
                'invoices': list(cust['invoices'].values())
            })

        total_qty_received = round(sum(entry.get('qty_received', 0.0) for entry in inbound_trace), 2)
        total_qty_picked = round(sum(entry.get('qty_picked', 0.0) for entry in outbound_trace), 2)
        current_quantity = float(batch.get('quantity') or 0.0) if batch else 0.0

        unique_orders = set(e.get('sales_order_id') for e in outbound_trace if e.get('sales_order_id') is not None)
        unique_receipts = set(e.get('receipt_id') for e in inbound_trace if e.get('receipt_id') is not None)
        unique_pick_lists = set(e.get('pick_list_id') for e in outbound_trace if e.get('pick_list_id') is not None)

        return {
            'batch': {
                'id': batch.get('id') if batch else batch_id,
                'batch_number': batch_number,
                'product_id': product_id,
                'product_name': product_name,
                'product_sku': product_sku,
                'product_category': product_category,
                'expiry_date': str(batch.get('expiry_date')) if batch and batch.get('expiry_date') else (inbound_trace[0].get('expiry_date') if inbound_trace else None),
                'manufacturing_date': str(batch.get('manufacturing_date')) if batch and batch.get('manufacturing_date') else (inbound_trace[0].get('manufacturing_date') if inbound_trace else None),
                'quantity': current_quantity,
                'warehouse_id': wh_id,
                'warehouse_name': warehouse_name,
                'status': batch.get('status') if batch else 'Available',
                'notes': batch.get('notes') if batch else None
            },
            'summary': {
                'total_qty_received': total_qty_received,
                'total_qty_picked': total_qty_picked,
                'current_quantity': current_quantity,
                'total_affected_customers': len(affected_customers),
                'total_affected_orders': len(unique_orders),
                'total_inbound_receipts': len(unique_receipts),
                'total_outbound_pick_lists': len(unique_pick_lists),
            },
            'inbound_trace': inbound_trace,
            'outbound_trace': outbound_trace,
            'affected_customers': affected_customers,
        }



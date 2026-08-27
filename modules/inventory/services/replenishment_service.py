"""
Nova ERP — Inter-Branch Replenishment Service
Evaluates branch warehouse inventory levels vs reorder points and safety thresholds,
matches deficit items with surplus central distribution hubs, and generates
transfer recommendations with one-click transfer order creation.
"""
import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any, Union
from fastapi import HTTPException
from pydantic import BaseModel

from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.warehouse.services.stock_transfer_service import StockTransferService
from modules.inventory.services.stock_movement import StockMovementService
from modules.warehouse.models.stock_transfer import (
    ReplenishmentSuggestionItem,
    ReplenishmentSuggestionResponse,
    ReplenishmentGenerateItem,
    ReplenishmentGenerateRequest,
    ReplenishmentGenerateResponse,
)

logger = logging.getLogger(__name__)

# Repositories for replenishment domain
STOCK_REPO = CrudRepository(
    'T0009',
    business_columns=['id', 'product_id', 'warehouse_id', 'qty', 'reserved_qty', 'in_transit_qty', 'reorder_level', 'business_id']
)

WH_REPO = CrudRepository(
    'T0008',
    business_columns=['id', 'name', 'location', 'warehouse_type', 'is_virtual', 'is_active', 'business_id']
)

PRODUCT_REPO = CrudRepository(
    'T0003',
    business_columns=['id', 'name', 'sku', 'barcode', 'description', 'type', 'price', 'cost_price', 'category', 'brand', 'is_active', 'business_id']
)


def _conn_kwargs(conn):
    """Only forward conn to repositories when an explicit connection is provided."""
    return {'conn': conn} if conn is not None else {}


class ReplenishmentService:
    """
    Domain service evaluating inventory health across branch & regional locations,
    calculating deficits against reorder points and safety stock thresholds,
    finding optimal surplus source hubs, and generating draft Stock Transfers.
    """

    def __init__(
        self,
        stock_repo: CrudRepository = None,
        wh_repo: CrudRepository = None,
        product_repo: CrudRepository = None,
        transfer_service: StockTransferService = None,
        stock_movement_service: StockMovementService = None,
    ):
        self.stock_repo = stock_repo or STOCK_REPO
        self.wh_repo = wh_repo or WH_REPO
        self.product_repo = product_repo or PRODUCT_REPO
        self.transfer_service = transfer_service or StockTransferService()
        self.stock_movement_service = stock_movement_service or StockMovementService()

    # -------------------------------------------------------------------------
    # Replenishment Suggestions & Deficit Evaluation
    # -------------------------------------------------------------------------

    def get_replenishment_suggestions(
        self,
        warehouse_id: Optional[int] = None,
        source_warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        min_deficit: float = 0.0,
        safety_stock_ratio: float = 0.5,
        target_coverage_multiplier: float = 1.5,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Scans warehouse inventory levels against reorder thresholds and safety stock,
        computes suggested transfer quantities, and matches each deficit SKU with
        the highest-surplus source warehouse.

        Parameters:
        - warehouse_id: Filter evaluation to a specific destination branch warehouse.
        - source_warehouse_id: Preferred source hub warehouse ID.
        - product_id: Filter to a specific product SKU.
        - category: Filter products by category.
        - priority: Filter by priority level ('Critical', 'High', 'Normal', 'Low').
        - min_deficit: Minimum quantity deficit required to include in suggestions.
        - safety_stock_ratio: Ratio of reorder level used as safety threshold (default 0.5).
        - target_coverage_multiplier: Multiplier on reorder level for target order size (default 1.5).
        """
        # 1. Fetch active warehouses (exclude virtual locations like In-Transit)
        all_warehouses = self.wh_repo.list(**_conn_kwargs(conn))
        active_warehouses = [
            w for w in all_warehouses
            if w.get('is_active', True) is not False and not w.get('is_virtual', False)
        ]
        warehouses_by_id = {w['id']: w for w in active_warehouses}

        if warehouse_id:
            if warehouse_id not in warehouses_by_id:
                wh_check = self.wh_repo.get(warehouse_id, **_conn_kwargs(conn))
                if not wh_check:
                    raise HTTPException(404, f"Warehouse #{warehouse_id} not found")
                if wh_check.get('is_virtual'):
                    raise HTTPException(400, f"Cannot evaluate replenishment for virtual warehouse #{warehouse_id}")
                warehouses_by_id[warehouse_id] = wh_check
            eval_dest_warehouses = [warehouses_by_id[warehouse_id]]
        else:
            eval_dest_warehouses = active_warehouses

        # 2. Fetch products
        product_filters = {}
        if product_id:
            product_filters['id'] = product_id
        if category:
            product_filters['category'] = category

        all_products = self.product_repo.list(filters=product_filters or None, **_conn_kwargs(conn))
        active_products = [p for p in all_products if p.get('is_active', True) is not False]
        products_by_id = {p['id']: p for p in active_products}

        if not active_products or not eval_dest_warehouses:
            return {
                'total_suggestions': 0,
                'critical_count': 0,
                'high_count': 0,
                'items': [],
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }

        # 3. Fetch stock levels
        all_stock_rows = self.stock_repo.list(**_conn_kwargs(conn))
        stock_by_key: Dict[tuple, dict] = {
            (s['product_id'], s['warehouse_id']): s for s in all_stock_rows
        }

        suggestions: List[Dict[str, Any]] = []

        # 4. Evaluate each product at each destination warehouse
        for dest_wh in eval_dest_warehouses:
            dest_wh_id = dest_wh['id']
            dest_wh_name = dest_wh.get('name')

            for prod in active_products:
                prod_id = prod['id']
                stock_rec = stock_by_key.get((prod_id, dest_wh_id)) or {}

                current_qty = float(stock_rec.get('qty', 0) or 0)
                reserved_qty = float(stock_rec.get('reserved_qty', 0) or 0)
                in_transit_qty = float(stock_rec.get('in_transit_qty', 0) or 0)
                reorder_level = float(stock_rec.get('reorder_level', 0) or 0)

                available_qty = max(0.0, current_qty - reserved_qty)
                effective_qty = available_qty + in_transit_qty
                safety_stock = round(reorder_level * safety_stock_ratio, 2)

                # Deficit evaluation: item needs replenishment when reorder_level > 0 and effective stock < reorder_level
                if reorder_level <= 0:
                    continue

                deficit = round(reorder_level - effective_qty, 2)
                if deficit <= 0:
                    # Stock + in-transit is sufficient to satisfy reorder level
                    continue

                if deficit < min_deficit:
                    continue

                # Determine Priority & Rationale
                if available_qty <= 0:
                    item_priority = "Critical"
                    reason = f"Out of stock: available ({available_qty}) below safety threshold ({safety_stock})"
                elif available_qty < safety_stock:
                    item_priority = "Critical"
                    reason = f"Stock level ({available_qty}) below safety threshold ({safety_stock})"
                elif effective_qty < (reorder_level * 0.5):
                    item_priority = "High"
                    reason = f"Effective stock ({effective_qty}) significantly below reorder point ({reorder_level})"
                elif effective_qty < reorder_level:
                    item_priority = "Normal"
                    reason = f"Effective stock ({effective_qty}) below reorder point ({reorder_level})"
                else:
                    item_priority = "Low"
                    reason = f"Stock ({effective_qty}) near reorder point ({reorder_level})"

                if priority and item_priority.lower() != str(priority).strip().lower():
                    continue

                # Calculate Suggested Transfer Quantity
                target_stock = max(reorder_level + safety_stock, reorder_level * target_coverage_multiplier)
                suggested_transfer_qty = max(1.0, round(target_stock - effective_qty, 2))

                # Match optimal source warehouse
                matched_source = self._match_source_warehouse(
                    product_id=prod_id,
                    dest_warehouse_id=dest_wh_id,
                    suggested_qty=suggested_transfer_qty,
                    preferred_source_id=source_warehouse_id,
                    warehouses_by_id=warehouses_by_id,
                    stock_by_key=stock_by_key,
                )

                source_wh_id = matched_source.get('source_warehouse_id')
                source_wh_name = matched_source.get('source_warehouse_name')
                source_avail = matched_source.get('source_available_stock', 0.0)

                suggestion_item = {
                    'product_id': prod_id,
                    'product_code': prod.get('sku'),
                    'product_name': prod.get('name'),
                    'destination_warehouse_id': dest_wh_id,
                    'destination_warehouse_name': dest_wh_name,
                    'current_stock': current_qty,
                    'reserved_stock': reserved_qty,
                    'in_transit_stock': in_transit_qty,
                    'available_stock': available_qty,
                    'reorder_point': reorder_level,
                    'safety_stock': safety_stock,
                    'suggested_transfer_qty': suggested_transfer_qty,
                    'source_warehouse_id': source_wh_id,
                    'source_warehouse_name': source_wh_name,
                    'source_available_stock': source_avail,
                    'priority': item_priority,
                    'reason': reason,
                }
                suggestions.append(suggestion_item)

        # 5. Sort suggestions: Critical -> High -> Normal -> Low, then by deficit descending
        priority_weights = {"Critical": 4, "High": 3, "Normal": 2, "Low": 1}
        suggestions.sort(
            key=lambda x: (
                priority_weights.get(x['priority'], 0),
                x['reorder_point'] - (x['available_stock'] + x['in_transit_stock']),
            ),
            reverse=True,
        )

        critical_count = sum(1 for s in suggestions if s['priority'] == 'Critical')
        high_count = sum(1 for s in suggestions if s['priority'] == 'High')

        return {
            'total_suggestions': len(suggestions),
            'critical_count': critical_count,
            'high_count': high_count,
            'items': suggestions,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    # -------------------------------------------------------------------------
    # Surplus Source Warehouse Matching
    # -------------------------------------------------------------------------

    def _match_source_warehouse(
        self,
        product_id: int,
        dest_warehouse_id: int,
        suggested_qty: float,
        preferred_source_id: Optional[int],
        warehouses_by_id: Dict[int, dict],
        stock_by_key: Dict[tuple, dict],
    ) -> Dict[str, Any]:
        """
        Finds the best source warehouse across the network to fulfill a replenishment deficit.
        Preference order:
        1. Preferred source warehouse if requested and has available stock.
        2. Central Hub / Regional DC with sufficient surplus (stock > reorder point + suggested_qty).
        3. Any warehouse with surplus above its own reorder point.
        4. Central Hub with any positive available stock.
        5. Any warehouse with the highest available stock.
        """
        candidate_sources = [
            w for w_id, w in warehouses_by_id.items()
            if w_id != dest_warehouse_id and not w.get('is_virtual', False)
        ]

        if not candidate_sources:
            return {
                'source_warehouse_id': None,
                'source_warehouse_name': None,
                'source_available_stock': 0.0,
                'note': "No eligible source warehouses in network",
            }

        # If a preferred source warehouse was requested and exists
        if preferred_source_id and preferred_source_id in warehouses_by_id and preferred_source_id != dest_warehouse_id:
            pref_wh = warehouses_by_id[preferred_source_id]
            pref_stock = stock_by_key.get((product_id, preferred_source_id)) or {}
            pref_avail = max(0.0, float(pref_stock.get('qty', 0) or 0) - float(pref_stock.get('reserved_qty', 0) or 0))
            if pref_avail > 0:
                return {
                    'source_warehouse_id': pref_wh['id'],
                    'source_warehouse_name': pref_wh.get('name'),
                    'source_available_stock': pref_avail,
                    'note': "Preferred source warehouse",
                }

        best_hub_with_surplus = None
        best_wh_with_surplus = None
        best_hub_with_stock = None
        best_wh_with_stock = None
        max_surplus = -1.0
        max_stock = -1.0

        central_hub_types = ('Central Hub', 'Central', 'Hub', 'Main', 'Regional DC')

        for wh in candidate_sources:
            wh_id = wh['id']
            wh_type = wh.get('warehouse_type', '')
            is_central = wh_type in central_hub_types

            stock_rec = stock_by_key.get((product_id, wh_id)) or {}
            avail = max(0.0, float(stock_rec.get('qty', 0) or 0) - float(stock_rec.get('reserved_qty', 0) or 0))
            reorder = float(stock_rec.get('reorder_level', 0) or 0)
            surplus = max(0.0, avail - reorder)

            # Check surplus (above warehouse's own reorder level)
            if surplus > 0:
                if is_central and (best_hub_with_surplus is None or surplus > max_surplus):
                    best_hub_with_surplus = (wh, avail, surplus)
                if best_wh_with_surplus is None or surplus > max_surplus:
                    best_wh_with_surplus = (wh, avail, surplus)
                    max_surplus = surplus

            # Check general positive stock
            if avail > 0:
                if is_central and (best_hub_with_stock is None or avail > max_stock):
                    best_hub_with_stock = (wh, avail)
                if best_wh_with_stock is None or avail > max_stock:
                    best_wh_with_stock = (wh, avail)
                    max_stock = avail

        # Choose best match based on ranking
        if best_hub_with_surplus:
            wh, avail, _ = best_hub_with_surplus
            return {
                'source_warehouse_id': wh['id'],
                'source_warehouse_name': wh.get('name'),
                'source_available_stock': avail,
                'note': "Central hub with surplus inventory",
            }
        elif best_wh_with_surplus:
            wh, avail, _ = best_wh_with_surplus
            return {
                'source_warehouse_id': wh['id'],
                'source_warehouse_name': wh.get('name'),
                'source_available_stock': avail,
                'note': "Branch warehouse with surplus inventory",
            }
        elif best_hub_with_stock:
            wh, avail = best_hub_with_stock
            return {
                'source_warehouse_id': wh['id'],
                'source_warehouse_name': wh.get('name'),
                'source_available_stock': avail,
                'note': "Central hub available stock",
            }
        elif best_wh_with_stock:
            wh, avail = best_wh_with_stock
            return {
                'source_warehouse_id': wh['id'],
                'source_warehouse_name': wh.get('name'),
                'source_available_stock': avail,
                'note': "Warehouse with available stock",
            }
        else:
            # Look for any central hub even if 0 stock
            first_central = next((w for w in candidate_sources if w.get('warehouse_type') in central_hub_types), None)
            fallback_wh = first_central or (candidate_sources[0] if candidate_sources else None)
            return {
                'source_warehouse_id': fallback_wh['id'] if fallback_wh else None,
                'source_warehouse_name': fallback_wh.get('name') if fallback_wh else None,
                'source_available_stock': 0.0,
                'note': "No surplus stock available in network",
            }

    # -------------------------------------------------------------------------
    # One-Click Stock Transfer Order Generation
    # -------------------------------------------------------------------------

    def generate_transfers(
        self,
        payload: Union[dict, ReplenishmentGenerateRequest, BaseModel],
        user_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Creates draft Stock Transfer orders from replenishment recommendations.
        Groups requested replenishment items by (source_warehouse_id, destination_warehouse_id)
        and calls StockTransferService to generate unified transfer documents.
        """
        data = payload.model_dump() if isinstance(payload, BaseModel) else dict(payload)

        items_input = data.get('items')

        # If items not explicitly provided, auto-calculate suggestions from current inventory state
        if not items_input:
            suggestions_res = self.get_replenishment_suggestions(
                warehouse_id=data.get('destination_warehouse_id'),
                source_warehouse_id=data.get('source_warehouse_id'),
                conn=conn,
            )
            items_input = []
            for s in suggestions_res.get('items', []):
                if s.get('source_warehouse_id') and float(s.get('suggested_transfer_qty', 0) or 0) > 0:
                    items_input.append({
                        'product_id': s['product_id'],
                        'destination_warehouse_id': s['destination_warehouse_id'],
                        'source_warehouse_id': s['source_warehouse_id'],
                        'suggested_transfer_qty': s['suggested_transfer_qty'],
                    })

        if not items_input:
            return {
                'transfers_created': 0,
                'transfer_ids': [],
                'transfer_numbers': [],
                'transfers': [],
            }

        # Group items by (source_warehouse_id, destination_warehouse_id)
        groups: Dict[tuple, List[dict]] = {}
        for raw_item in items_input:
            item = raw_item.model_dump() if isinstance(raw_item, BaseModel) else dict(raw_item)
            src_id = item.get('source_warehouse_id') or data.get('source_warehouse_id')
            dest_id = item.get('destination_warehouse_id') or data.get('destination_warehouse_id')
            qty = float(item.get('suggested_transfer_qty', 0) or 0)

            if not src_id or not dest_id:
                logger.warning(f"Skipping replenishment item {item}: missing source or destination warehouse")
                continue

            if int(src_id) == int(dest_id):
                logger.warning(f"Skipping replenishment item {item}: source and destination warehouse are identical (#{src_id})")
                continue

            if qty <= 0:
                logger.warning(f"Skipping replenishment item {item}: quantity must be greater than 0")
                continue

            group_key = (int(src_id), int(dest_id))
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)

        created_transfers = []
        transfer_ids = []
        transfer_numbers = []

        transfer_date = data.get('transfer_date') or date.today()
        expected_date = data.get('expected_delivery_date')
        carrier = data.get('carrier')
        notes = data.get('notes') or "Automated inter-branch replenishment order"

        for (src_id, dest_id), group_items in groups.items():
            lines_data = []
            for idx, item in enumerate(group_items, start=1):
                lines_data.append({
                    'product_id': item['product_id'],
                    'qty_requested': float(item['suggested_transfer_qty']),
                    'batch_id': item.get('batch_id'),
                    'batch_number': item.get('batch_number'),
                    'line_number': idx,
                    'notes': "Auto-replenishment suggestion",
                })

            transfer_payload = {
                'source_warehouse_id': src_id,
                'destination_warehouse_id': dest_id,
                'status': 'Draft',
                'transfer_date': transfer_date,
                'expected_delivery_date': expected_date,
                'carrier': carrier,
                'notes': notes,
                'lines': lines_data,
            }

            created = self.transfer_service.create_transfer(transfer_payload, conn=conn)
            created_transfers.append(created)
            transfer_ids.append(created['id'])
            transfer_numbers.append(created['transfer_number'])

        logger.info(f"Generated {len(created_transfers)} replenishment stock transfer(s): {transfer_numbers}")

        return {
            'transfers_created': len(created_transfers),
            'transfer_ids': transfer_ids,
            'transfer_numbers': transfer_numbers,
            'transfers': created_transfers,
        }

    # -------------------------------------------------------------------------
    # Inventory Health Summary
    # -------------------------------------------------------------------------

    def get_stock_health_summary(self, conn=None) -> Dict[str, Any]:
        """
        Returns high-level inventory health KPIs across the warehouse network:
        - Total SKUs monitored
        - Total warehouses
        - Deficit SKUs count (below reorder point)
        - Critical stockout SKUs count
        - Active in-transit transfers count
        """
        suggestions = self.get_replenishment_suggestions(conn=conn)
        in_transit_transfers = self.transfer_service.list_in_transit(conn=conn)

        all_products = self.product_repo.list(**_conn_kwargs(conn))
        all_whs = self.wh_repo.list(**_conn_kwargs(conn))

        return {
            'total_products': len(all_products),
            'total_warehouses': len([w for w in all_whs if not w.get('is_virtual', False)]),
            'total_deficits': suggestions.get('total_suggestions', 0),
            'critical_deficits': suggestions.get('critical_count', 0),
            'high_deficits': suggestions.get('high_count', 0),
            'active_in_transit_transfers': len(in_transit_transfers),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

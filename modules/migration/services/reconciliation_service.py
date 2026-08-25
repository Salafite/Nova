"""Comprehensive Opening Balance and Inventory Reconciliation Engine.

Provides deep reconciliation reporting between legacy source systems and Nova target entities:
1. Customer Opening Balances & Receivables: compares legacy customer balances vs Nova opening balance
   journals/invoices, detects deltas, sign inversions, and missing accounts.
2. Inventory Quantities & Valuation: compares stock quantities and valuation across warehouses,
   identifies negative stock items, clamped values, and valuation variances.
3. Entity Count Reconciliation: audits source count vs staged count vs phantom/cleansed vs errors.
4. Comprehensive Reconciliation Report generation with intelligent actionable recommendations.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.migration.models.migration import (
    CleansingSummary,
    CustomerBalanceItem,
    CustomerBalanceReconciliation,
    EntityCountReconciliation,
    InventoryReconciliation,
    ReconciliationReport,
    RowValidationError,
    WarehouseReconciliationSummary,
    WarehouseStockItem,
)

logger = logging.getLogger(__name__)

BATCH_REPO = CrudRepository("T0104", business_columns=["id", "batch_key", "entity_type", "reconciliation_summary", "business_id"])


class CustomerBalanceReconciler:
    """Reconciles legacy customer balances / receivables against Nova opening balance records."""

    @staticmethod
    def _extract_customer_key(rec: Dict[str, Any]) -> str:
        """Extract a unique customer identifier from legacy or Nova record."""
        return str(
            rec.get("customer_key")
            or rec.get("code")
            or rec.get("customer_code")
            or rec.get("partner_id")
            or rec.get("id")
            or rec.get("phone")
            or rec.get("name")
            or ""
        ).strip()

    @staticmethod
    def _extract_customer_name(rec: Dict[str, Any]) -> str:
        """Extract customer name."""
        return str(
            rec.get("customer_name")
            or rec.get("name")
            or rec.get("cust_name")
            or rec.get("partner_name")
            or "Unknown Customer"
        ).strip()

    @classmethod
    def _extract_balance(cls, rec: Dict[str, Any]) -> float:
        """Extract numeric balance, supporting balance, open_balance, debit/credit fields."""
        if "balance" in rec and rec["balance"] is not None:
            try:
                return float(rec["balance"])
            except (ValueError, TypeError):
                pass

        if "open_balance" in rec and rec["open_balance"] is not None:
            try:
                return float(rec["open_balance"])
            except (ValueError, TypeError):
                pass

        if "total_amount" in rec and rec["total_amount"] is not None:
            try:
                return float(rec["total_amount"])
            except (ValueError, TypeError):
                pass

        if "amount" in rec and rec["amount"] is not None:
            try:
                return float(rec["amount"])
            except (ValueError, TypeError):
                pass

        # Check for debit and credit columns
        debit = 0.0
        credit = 0.0
        has_debit_credit = False
        if "debit" in rec and rec["debit"] is not None:
            try:
                debit = float(rec["debit"])
                has_debit_credit = True
            except (ValueError, TypeError):
                pass
        if "credit" in rec and rec["credit"] is not None:
            try:
                credit = float(rec["credit"])
                has_debit_credit = True
            except (ValueError, TypeError):
                pass

        if has_debit_credit:
            return round(debit - credit, 2)

        return 0.0

    def reconcile(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.01,
    ) -> CustomerBalanceReconciliation:
        """Perform line-by-line and aggregate customer balance reconciliation."""
        # Index legacy records by key and normalized name
        legacy_by_key: Dict[str, Dict[str, Any]] = {}
        legacy_by_name: Dict[str, Dict[str, Any]] = {}
        legacy_totals_by_key: Dict[str, float] = {}
        legacy_names_by_key: Dict[str, str] = {}

        for rec in legacy_records:
            key = self._extract_customer_key(rec)
            name = self._extract_customer_name(rec)
            bal = self._extract_balance(rec)

            if not key and name:
                key = name.lower()

            if key:
                legacy_totals_by_key[key] = round(legacy_totals_by_key.get(key, 0.0) + bal, 2)
                legacy_names_by_key[key] = name
                legacy_by_key[key] = rec
            if name:
                legacy_by_name[name.lower()] = rec

        # Index Nova records
        nova_totals_by_key: Dict[str, float] = {}
        nova_names_by_key: Dict[str, str] = {}
        nova_by_key: Dict[str, Dict[str, Any]] = {}

        for rec in nova_records:
            key = self._extract_customer_key(rec)
            name = self._extract_customer_name(rec)
            bal = self._extract_balance(rec)

            if not key and name:
                key = name.lower()

            if key:
                nova_totals_by_key[key] = round(nova_totals_by_key.get(key, 0.0) + bal, 2)
                nova_names_by_key[key] = name
                nova_by_key[key] = rec

        all_keys: Set[str] = set(legacy_totals_by_key.keys()) | set(nova_totals_by_key.keys())

        discrepancies: List[CustomerBalanceItem] = []
        all_items: List[CustomerBalanceItem] = []
        matched_count = 0
        mismatched_count = 0

        for key in sorted(all_keys):
            legacy_bal = legacy_totals_by_key.get(key, 0.0)
            nova_bal = nova_totals_by_key.get(key, 0.0)
            name = legacy_names_by_key.get(key) or nova_names_by_key.get(key) or key

            delta = round(abs(legacy_bal - nova_bal), 2)
            is_matched = delta <= tolerance
            notes: Optional[str] = None

            if key not in legacy_totals_by_key:
                is_matched = False
                notes = "Customer present in Nova opening balances but missing in legacy source"
            elif key not in nova_totals_by_key:
                is_matched = False
                notes = "Customer present in legacy source but missing in Nova opening balances"
            elif not is_matched:
                # Check for sign inversion (e.g. legacy had negative credit balance vs positive debit)
                if legacy_bal != 0.0 and abs(legacy_bal + nova_bal) <= tolerance:
                    notes = f"Sign inversion detected: legacy={legacy_bal}, nova={nova_bal} (credit/debit inverted)"
                else:
                    notes = f"Balance variance of {delta:+.2f} (legacy={legacy_bal}, nova={nova_bal})"

            item = CustomerBalanceItem(
                customer_key=key,
                customer_name=name,
                legacy_balance=legacy_bal,
                nova_balance=nova_bal,
                delta=delta,
                is_matched=is_matched,
                notes=notes,
            )
            all_items.append(item)

            if is_matched:
                matched_count += 1
            else:
                mismatched_count += 1
                discrepancies.append(item)

        total_legacy = round(sum(legacy_totals_by_key.values()), 2)
        total_nova = round(sum(nova_totals_by_key.values()), 2)
        total_delta = round(abs(total_legacy - total_nova), 2)

        # Sort top variances by delta descending
        top_variances = sorted(discrepancies, key=lambda x: x.delta, reverse=True)[:10]

        is_reconciled = (mismatched_count == 0 and total_delta <= tolerance)

        return CustomerBalanceReconciliation(
            total_legacy_receivables=total_legacy,
            total_nova_receivables=total_nova,
            total_receivables_delta=total_delta,
            customers_count=len(all_keys),
            matched_count=matched_count,
            mismatched_count=mismatched_count,
            discrepancies=discrepancies,
            top_variances=top_variances,
            is_reconciled=is_reconciled,
        )


class InventoryReconciler:
    """Reconciles legacy inventory stock levels and valuation against Nova opening stock."""

    @staticmethod
    def _extract_sku(rec: Dict[str, Any]) -> str:
        return str(
            rec.get("sku")
            or rec.get("item_code")
            or rec.get("code")
            or rec.get("product_id")
            or rec.get("id")
            or ""
        ).strip()

    @staticmethod
    def _extract_product_name(rec: Dict[str, Any]) -> str:
        return str(
            rec.get("product_name")
            or rec.get("name")
            or rec.get("item_name")
            or "Unknown Product"
        ).strip()

    @staticmethod
    def _extract_warehouse(rec: Dict[str, Any]) -> str:
        return str(
            rec.get("warehouse_name")
            or rec.get("warehouse")
            or rec.get("warehouse_code")
            or rec.get("location")
            or "Main Warehouse"
        ).strip()

    @staticmethod
    def _extract_quantity(rec: Dict[str, Any]) -> float:
        for f in ("qty", "quantity", "stock_quantity", "stock", "on_hand", "open_qty"):
            if f in rec and rec[f] is not None:
                try:
                    return float(rec[f])
                except (ValueError, TypeError):
                    pass
        return 0.0

    @staticmethod
    def _extract_unit_cost(rec: Dict[str, Any]) -> float:
        for f in ("cost_price", "cost", "unit_cost", "avg_cost", "purchase_price", "price"):
            if f in rec and rec[f] is not None:
                try:
                    val = float(rec[f])
                    if val >= 0:
                        return val
                except (ValueError, TypeError):
                    pass
        return 0.0

    def reconcile(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.001,
    ) -> InventoryReconciliation:
        """Perform SKU-level and warehouse-level inventory quantity and valuation reconciliation."""
        # Index legacy stock by (sku, warehouse)
        legacy_stock: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for rec in legacy_records:
            sku = self._extract_sku(rec)
            if not sku:
                continue
            wh = self._extract_warehouse(rec)
            name = self._extract_product_name(rec)
            qty = self._extract_quantity(rec)
            cost = self._extract_unit_cost(rec)
            key = (sku, wh)

            if key in legacy_stock:
                legacy_stock[key]["qty"] = round(legacy_stock[key]["qty"] + qty, 4)
                if cost > 0:
                    legacy_stock[key]["cost"] = cost
            else:
                legacy_stock[key] = {
                    "sku": sku,
                    "name": name,
                    "warehouse": wh,
                    "qty": round(qty, 4),
                    "cost": cost,
                    "raw": rec,
                }

        # Index Nova stock by (sku, warehouse)
        nova_stock: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for rec in nova_records:
            sku = self._extract_sku(rec)
            if not sku:
                continue
            wh = self._extract_warehouse(rec)
            name = self._extract_product_name(rec)
            qty = self._extract_quantity(rec)
            cost = self._extract_unit_cost(rec)
            key = (sku, wh)

            if key in nova_stock:
                nova_stock[key]["qty"] = round(nova_stock[key]["qty"] + qty, 4)
                if cost > 0:
                    nova_stock[key]["cost"] = cost
            else:
                nova_stock[key] = {
                    "sku": sku,
                    "name": name,
                    "warehouse": wh,
                    "qty": round(qty, 4),
                    "cost": cost,
                    "raw": rec,
                }

        all_keys: Set[Tuple[str, str]] = set(legacy_stock.keys()) | set(nova_stock.keys())

        discrepancies: List[WarehouseStockItem] = []
        warehouse_stats: Dict[str, Dict[str, Any]] = {}
        negative_stock_count = 0
        mismatched_count = 0

        for key in sorted(all_keys):
            sku, wh = key
            leg_info = legacy_stock.get(key)
            nov_info = nova_stock.get(key)

            name = (leg_info.get("name") if leg_info else None) or (nov_info.get("name") if nov_info else None) or sku
            legacy_qty = leg_info["qty"] if leg_info else 0.0
            nova_qty = nov_info["qty"] if nov_info else 0.0
            unit_cost = (leg_info.get("cost") if leg_info and leg_info.get("cost", 0) > 0 else (nov_info.get("cost") if nov_info else 0.0)) or 0.0

            legacy_val = round(legacy_qty * unit_cost, 2)
            nova_val = round(nova_qty * unit_cost, 2)

            qty_delta = round(abs(legacy_qty - nova_qty), 4)
            val_delta = round(abs(legacy_val - nova_val), 2)

            is_neg = legacy_qty < 0 or nova_qty < 0
            if is_neg:
                negative_stock_count += 1

            status = "OK"
            is_matched = qty_delta <= tolerance and val_delta <= 0.01

            if is_neg:
                status = "NegativeStock"
                is_matched = False
            elif leg_info is None:
                status = "MissingInSource"
                is_matched = False
            elif nov_info is None:
                status = "MissingInTarget"
                is_matched = False
            elif not is_matched:
                status = "Mismatch"

            item = WarehouseStockItem(
                product_key=sku,
                sku=sku,
                product_name=name,
                warehouse_name=wh,
                legacy_quantity=legacy_qty,
                nova_quantity=nova_qty,
                quantity_delta=qty_delta,
                unit_cost=unit_cost,
                legacy_valuation=legacy_val,
                nova_valuation=nova_val,
                valuation_delta=val_delta,
                is_negative_stock=is_neg,
                is_matched=is_matched,
                status=status,
            )

            # Warehouse summary accumulation
            if wh not in warehouse_stats:
                warehouse_stats[wh] = {
                    "legacy_qty": 0.0,
                    "nova_qty": 0.0,
                    "legacy_val": 0.0,
                    "nova_val": 0.0,
                    "items": 0,
                    "mismatches": 0,
                }
            warehouse_stats[wh]["legacy_qty"] = round(warehouse_stats[wh]["legacy_qty"] + legacy_qty, 4)
            warehouse_stats[wh]["nova_qty"] = round(warehouse_stats[wh]["nova_qty"] + nova_qty, 4)
            warehouse_stats[wh]["legacy_val"] = round(warehouse_stats[wh]["legacy_val"] + legacy_val, 2)
            warehouse_stats[wh]["nova_val"] = round(warehouse_stats[wh]["nova_val"] + nova_val, 2)
            warehouse_stats[wh]["items"] += 1

            if not is_matched:
                mismatched_count += 1
                warehouse_stats[wh]["mismatches"] += 1
                discrepancies.append(item)

        # Build warehouse summaries
        warehouse_summaries: Dict[str, WarehouseReconciliationSummary] = {}
        for wh_name, stats in warehouse_stats.items():
            q_delta = round(abs(stats["legacy_qty"] - stats["nova_qty"]), 4)
            v_delta = round(abs(stats["legacy_val"] - stats["nova_val"]), 2)
            warehouse_summaries[wh_name] = WarehouseReconciliationSummary(
                warehouse_name=wh_name,
                legacy_total_quantity=stats["legacy_qty"],
                nova_total_quantity=stats["nova_qty"],
                quantity_delta=q_delta,
                legacy_total_valuation=stats["legacy_val"],
                nova_total_valuation=stats["nova_val"],
                valuation_delta=v_delta,
                item_count=stats["items"],
                mismatched_count=stats["mismatches"],
            )

        total_leg_qty = round(sum(s["legacy_qty"] for s in warehouse_stats.values()), 4)
        total_nov_qty = round(sum(s["nova_qty"] for s in warehouse_stats.values()), 4)
        total_q_delta = round(abs(total_leg_qty - total_nov_qty), 4)

        total_leg_val = round(sum(s["legacy_val"] for s in warehouse_stats.values()), 2)
        total_nov_val = round(sum(s["nova_val"] for s in warehouse_stats.values()), 2)
        total_v_delta = round(abs(total_leg_val - total_nov_val), 2)

        is_reconciled = (
            mismatched_count == 0
            and negative_stock_count == 0
            and total_q_delta <= tolerance
            and total_v_delta <= 0.01
        )

        return InventoryReconciliation(
            total_legacy_quantity=total_leg_qty,
            total_nova_quantity=total_nov_qty,
            total_quantity_delta=total_q_delta,
            total_legacy_valuation=total_leg_val,
            total_nova_valuation=total_nov_val,
            total_valuation_delta=total_v_delta,
            negative_stock_count=negative_stock_count,
            warehouse_summaries=warehouse_summaries,
            discrepancies=discrepancies,
            is_reconciled=is_reconciled,
        )


class EntityCountReconciler:
    """Reconciles entity-level row counts through the migration pipeline stages."""

    def reconcile(
        self,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        staged_by_entity: Dict[str, List[Dict[str, Any]]],
        cleansing_summary: Optional[CleansingSummary] = None,
        validation_errors: Optional[List[RowValidationError]] = None,
    ) -> Dict[str, EntityCountReconciliation]:
        """Compute source vs staged vs phantom vs cleansed vs error count per entity."""
        all_entities = set(extracted_by_entity.keys()) | set(staged_by_entity.keys())

        # Count errors per entity
        error_counts: Dict[str, int] = {}
        if validation_errors:
            for err in validation_errors:
                if getattr(err, "severity", "error") == "error":
                    ent = getattr(err, "entity_type", "unknown")
                    error_counts[ent] = error_counts.get(ent, 0) + 1

        result: Dict[str, EntityCountReconciliation] = {}

        for entity in sorted(all_entities):
            src_count = len(extracted_by_entity.get(entity, []))
            staged_count = len(staged_by_entity.get(entity, []))
            err_count = error_counts.get(entity, 0)

            # Phantom & Cleansing metrics
            phantom_count = 0
            cleansed_count = 0
            if entity == "products" and cleansing_summary:
                phantom_count = cleansing_summary.phantom_products_detected
                cleansed_count = (
                    cleansing_summary.duplicates_resolved
                    + cleansing_summary.clamped_numeric_values
                )
            elif entity in ("customers", "suppliers") and cleansing_summary:
                cleansed_count = cleansing_summary.contacts_sanitized

            # Determine match status
            if err_count > 0:
                match_status = "ErrorsPresent"
            elif staged_count == src_count:
                match_status = "Matched"
            else:
                match_status = "CleanedWithDeltas"

            result[entity] = EntityCountReconciliation(
                entity_type=entity,
                source_count=src_count,
                staged_count=staged_count,
                phantom_count=phantom_count,
                cleansed_count=cleansed_count,
                error_count=err_count,
                committed_count=0,
                match_status=match_status,
            )

        return result


class ReconciliationService:
    """Comprehensive Opening Balance and Inventory Reconciliation Service."""

    def __init__(self) -> None:
        self.customer_reconciler = CustomerBalanceReconciler()
        self.inventory_reconciler = InventoryReconciler()
        self.entity_count_reconciler = EntityCountReconciler()

    def reconcile_customer_balances(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.01,
    ) -> CustomerBalanceReconciliation:
        """Reconcile legacy customer receivables against Nova opening balance journals/invoices."""
        return self.customer_reconciler.reconcile(
            legacy_records=legacy_records,
            nova_records=nova_records,
            tolerance=tolerance,
        )

    def reconcile_inventory(
        self,
        legacy_records: List[Dict[str, Any]],
        nova_records: List[Dict[str, Any]],
        tolerance: float = 0.001,
    ) -> InventoryReconciliation:
        """Reconcile legacy inventory stock quantities and valuation against Nova opening stock."""
        return self.inventory_reconciler.reconcile(
            legacy_records=legacy_records,
            nova_records=nova_records,
            tolerance=tolerance,
        )

    def reconcile_entity_counts(
        self,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        staged_by_entity: Dict[str, List[Dict[str, Any]]],
        cleansing_summary: Optional[CleansingSummary] = None,
        validation_errors: Optional[List[RowValidationError]] = None,
    ) -> Dict[str, EntityCountReconciliation]:
        """Audit entity row counts from extraction through cleansing and staging."""
        return self.entity_count_reconciler.reconcile(
            extracted_by_entity=extracted_by_entity,
            staged_by_entity=staged_by_entity,
            cleansing_summary=cleansing_summary,
            validation_errors=validation_errors,
        )

    def generate_reconciliation_report(
        self,
        batch_key: str,
        extracted_by_entity: Dict[str, List[Dict[str, Any]]],
        staged_by_entity: Dict[str, List[Dict[str, Any]]],
        cleansing_summary: Optional[CleansingSummary] = None,
        validation_errors: Optional[List[RowValidationError]] = None,
        tolerance: float = 0.01,
    ) -> ReconciliationReport:
        """Generate a complete end-to-end reconciliation report."""
        errors_list = validation_errors or []
        unresolved_errors = len([e for e in errors_list if getattr(e, "severity", "error") == "error"])

        # 1. Customer Opening Balances Reconciliation
        legacy_ar: List[Dict[str, Any]] = []
        nova_ar: List[Dict[str, Any]] = []
        for key in ("customer_opening_balances", "customers"):
            if key in extracted_by_entity:
                legacy_ar = extracted_by_entity[key]
                break
        for key in ("customer_opening_balances", "customers"):
            if key in staged_by_entity:
                nova_ar = staged_by_entity[key]
                break

        cust_recon: Optional[CustomerBalanceReconciliation] = None
        if legacy_ar or nova_ar:
            cust_recon = self.reconcile_customer_balances(
                legacy_records=legacy_ar,
                nova_records=nova_ar,
                tolerance=tolerance,
            )

        # 2. Inventory Quantities & Valuation Reconciliation
        legacy_inv: List[Dict[str, Any]] = []
        nova_inv: List[Dict[str, Any]] = []
        for key in ("inventory_opening", "products"):
            if key in extracted_by_entity:
                legacy_inv = extracted_by_entity[key]
                break
        for key in ("inventory_opening", "products"):
            if key in staged_by_entity:
                nova_inv = staged_by_entity[key]
                break

        inv_recon: Optional[InventoryReconciliation] = None
        if legacy_inv or nova_inv:
            inv_recon = self.reconcile_inventory(
                legacy_records=legacy_inv,
                nova_records=nova_inv,
                tolerance=tolerance,
            )

        # 3. Entity Count Reconciliation
        entity_counts = self.reconcile_entity_counts(
            extracted_by_entity=extracted_by_entity,
            staged_by_entity=staged_by_entity,
            cleansing_summary=cleansing_summary,
            validation_errors=errors_list,
        )

        # 4. Phantom Products Summary
        phantom_summary: Optional[Dict[str, Any]] = None
        if cleansing_summary:
            phantom_summary = {
                "detected": cleansing_summary.phantom_products_detected,
                "skipped": cleansing_summary.phantom_products_skipped,
                "duplicates_resolved": cleansing_summary.duplicates_resolved,
                "contacts_sanitized": cleansing_summary.contacts_sanitized,
                "lookups_created": cleansing_summary.lookups_auto_created,
                "clamped_values": cleansing_summary.clamped_numeric_values,
            }

        # 5. Overall Status Determination
        has_ar_mismatch = cust_recon is not None and not cust_recon.is_reconciled
        has_inv_mismatch = inv_recon is not None and not inv_recon.is_reconciled
        has_unresolved_errors = unresolved_errors > 0

        if has_unresolved_errors or (has_ar_mismatch and cust_recon and cust_recon.total_receivables_delta > 1.0) or (has_inv_mismatch and inv_recon and inv_recon.total_quantity_delta > 1.0):
            overall_status = "Failed"
        elif has_ar_mismatch or has_inv_mismatch or (cleansing_summary and cleansing_summary.phantom_products_detected > 0):
            overall_status = "PassedWithWarnings"
        else:
            overall_status = "Passed"

        # 6. Actionable Recommendations Generation
        recommendations = self.generate_recommendations(
            cust_recon=cust_recon,
            inv_recon=inv_recon,
            cleansing_summary=cleansing_summary,
            unresolved_errors_count=unresolved_errors,
        )

        return ReconciliationReport(
            batch_key=batch_key,
            report_date=datetime.now(),
            overall_status=overall_status,
            customer_balance=cust_recon,
            inventory=inv_recon,
            entity_counts=entity_counts,
            phantom_summary=phantom_summary,
            unresolved_errors_count=unresolved_errors,
            recommendations=recommendations,
        )

    def generate_recommendations(
        self,
        cust_recon: Optional[CustomerBalanceReconciliation],
        inv_recon: Optional[InventoryReconciliation],
        cleansing_summary: Optional[CleansingSummary],
        unresolved_errors_count: int,
    ) -> List[str]:
        """Generate human-readable, prioritized operational recommendations."""
        recommendations: List[str] = []

        if unresolved_errors_count > 0:
            recommendations.append(
                f"Action Required: Resolve {unresolved_errors_count} fatal row validation errors before proceeding with commit."
            )

        if cust_recon:
            if not cust_recon.is_reconciled:
                if cust_recon.mismatched_count > 0:
                    recommendations.append(
                        f"Opening Balance Discrepancy: {cust_recon.mismatched_count} customer balance(s) have variances totaling {cust_recon.total_receivables_delta:,.2f}. Review top variance items."
                    )
                # Check for sign inversion notes
                sign_inversions = [d for d in cust_recon.discrepancies if d.notes and "Sign inversion" in d.notes]
                if sign_inversions:
                    recommendations.append(
                        f"Credit/Debit Inversion: Detected {len(sign_inversions)} customer balance(s) with reversed signs. Verify accounting credit/debit column mapping."
                    )
            else:
                recommendations.append("Customer Receivables: Fully balanced and verified against legacy opening accounts.")

        if inv_recon:
            if inv_recon.negative_stock_count > 0:
                recommendations.append(
                    f"Negative Inventory: {inv_recon.negative_stock_count} item(s) have negative stock in source system. Automated cleansing clamped them to 0.0; perform physical inventory count after go-live."
                )
            if not inv_recon.is_reconciled:
                recommendations.append(
                    f"Inventory Variance: Quantity delta of {inv_recon.total_quantity_delta:,.2f} across warehouses ({len(inv_recon.discrepancies)} discrepancy items)."
                )
            else:
                recommendations.append("Inventory Stock & Valuation: Perfectly matched across all target warehouses.")

        if cleansing_summary:
            if cleansing_summary.phantom_products_detected > 0:
                recommendations.append(
                    f"Phantom Products: Detected {cleansing_summary.phantom_products_detected} inactive/ghost product(s) (no transaction in 12+ months or zero stock). Review flagged items before commit."
                )
            if cleansing_summary.duplicates_resolved > 0:
                recommendations.append(
                    f"Deduplication: Resolved {cleansing_summary.duplicates_resolved} duplicate SKU/barcode entries."
                )
            if cleansing_summary.lookups_auto_created > 0:
                recommendations.append(
                    f"Master Lookups: {cleansing_summary.lookups_auto_created} missing categories, UOMs, or warehouses were automatically provisioned."
                )

        if not recommendations:
            recommendations.append("All reconciliation checks passed successfully. Migration batch is ready for one-click commit.")

        return recommendations


# Global default instance
reconciliation_service = ReconciliationService()

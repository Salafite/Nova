"""Unit and integration tests for the Reconciliation Engine (ReconciliationService)."""

from datetime import datetime
import pytest

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
from modules.migration.services.reconciliation_service import (
    CustomerBalanceReconciler,
    EntityCountReconciler,
    InventoryReconciler,
    ReconciliationService,
    reconciliation_service,
)


# ==============================================================================
# 1. Customer Opening Balances & Receivables Reconciliation Tests
# ==============================================================================

class TestCustomerBalanceReconciliation:
    def setup_method(self):
        self.reconciler = CustomerBalanceReconciler()

    def test_perfectly_matched_customer_balances(self):
        legacy = [
            {"customer_key": "CUST-001", "name": "Al-Nour Cafe", "balance": 1500.50},
            {"customer_key": "CUST-002", "name": "Sunset Bakery", "balance": 3200.00},
            {"customer_key": "CUST-003", "name": "Quick Bites", "balance": 0.00},
        ]
        nova = [
            {"partner_id": "CUST-001", "name": "Al-Nour Cafe", "total_amount": 1500.50},
            {"partner_id": "CUST-002", "name": "Sunset Bakery", "total_amount": 3200.00},
            {"partner_id": "CUST-003", "name": "Quick Bites", "total_amount": 0.00},
        ]

        result = self.reconciler.reconcile(legacy, nova, tolerance=0.01)

        assert isinstance(result, CustomerBalanceReconciliation)
        assert result.total_legacy_receivables == 4700.50
        assert result.total_nova_receivables == 4700.50
        assert result.total_receivables_delta == 0.0
        assert result.customers_count == 3
        assert result.matched_count == 3
        assert result.mismatched_count == 0
        assert len(result.discrepancies) == 0
        assert result.is_reconciled is True

    def test_customer_balance_variances_and_top_discrepancies(self):
        legacy = [
            {"customer_key": "C1", "name": "Alpha Corp", "balance": 5000.00},
            {"customer_key": "C2", "name": "Beta LLC", "balance": 1000.00},
            {"customer_key": "C3", "name": "Gamma Co", "balance": 250.00},
        ]
        nova = [
            {"partner_id": "C1", "name": "Alpha Corp", "total_amount": 4500.00},  # Delta 500.00
            {"partner_id": "C2", "name": "Beta LLC", "total_amount": 950.00},    # Delta 50.00
            {"partner_id": "C3", "name": "Gamma Co", "total_amount": 250.00},    # Matched
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.total_legacy_receivables == 6250.00
        assert result.total_nova_receivables == 5700.00
        assert result.total_receivables_delta == 550.00
        assert result.matched_count == 1
        assert result.mismatched_count == 2
        assert result.is_reconciled is False
        assert len(result.discrepancies) == 2
        # Top variances sorted by delta descending
        assert result.top_variances[0].customer_key == "C1"
        assert result.top_variances[0].delta == 500.00
        assert result.top_variances[1].customer_key == "C2"
        assert result.top_variances[1].delta == 50.00

    def test_sign_inversion_detection(self):
        legacy = [
            {"customer_key": "C10", "name": "Delta Bistro", "balance": 1250.00},
        ]
        nova = [
            {"partner_id": "C10", "name": "Delta Bistro", "total_amount": -1250.00},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.is_reconciled is False
        assert len(result.discrepancies) == 1
        disc = result.discrepancies[0]
        assert disc.customer_key == "C10"
        assert disc.delta == 2500.00
        assert "Sign inversion detected" in disc.notes
        assert "credit/debit inverted" in disc.notes

    def test_missing_customer_accounts(self):
        legacy = [
            {"customer_key": "C1", "name": "Exists in Both", "balance": 100.00},
            {"customer_key": "C2", "name": "Only in Legacy", "balance": 500.00},
        ]
        nova = [
            {"partner_id": "C1", "name": "Exists in Both", "total_amount": 100.00},
            {"partner_id": "C3", "name": "Only in Nova", "total_amount": 300.00},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.customers_count == 3
        assert result.matched_count == 1
        assert result.mismatched_count == 2
        assert result.is_reconciled is False

        notes_map = {d.customer_key: d.notes for d in result.discrepancies}
        assert "missing in Nova opening balances" in notes_map["C2"]
        assert "missing in legacy source" in notes_map["C3"]

    def test_debit_credit_column_calculation(self):
        legacy = [
            {"customer_key": "ACC-1", "name": "Debtor One", "debit": 2000.00, "credit": 500.00},  # Net 1500.00
            {"customer_key": "ACC-2", "name": "Debtor Two", "debit": 1000.00, "credit": 1000.00}, # Net 0.00
        ]
        nova = [
            {"partner_id": "ACC-1", "name": "Debtor One", "balance": 1500.00},
            {"partner_id": "ACC-2", "name": "Debtor Two", "balance": 0.00},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.is_reconciled is True
        assert result.total_legacy_receivables == 1500.00
        assert result.total_nova_receivables == 1500.00


# ==============================================================================
# 2. Inventory Quantities & Valuation Reconciliation Tests
# ==============================================================================

class TestInventoryReconciliation:
    def setup_method(self):
        self.reconciler = InventoryReconciler()

    def test_perfectly_matched_inventory_across_warehouses(self):
        legacy = [
            {"sku": "COF-01", "name": "Espresso Beans", "warehouse": "Main Warehouse", "qty": 100.0, "cost_price": 10.0},
            {"sku": "COF-02", "name": "Arabica Beans", "warehouse": "Main Warehouse", "qty": 50.0, "cost_price": 12.0},
            {"sku": "COF-01", "name": "Espresso Beans", "warehouse": "Branch A", "qty": 20.0, "cost_price": 10.0},
        ]
        nova = [
            {"sku": "COF-01", "name": "Espresso Beans", "warehouse": "Main Warehouse", "qty": 100.0, "cost_price": 10.0},
            {"sku": "COF-02", "name": "Arabica Beans", "warehouse": "Main Warehouse", "qty": 50.0, "cost_price": 12.0},
            {"sku": "COF-01", "name": "Espresso Beans", "warehouse": "Branch A", "qty": 20.0, "cost_price": 10.0},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert isinstance(result, InventoryReconciliation)
        assert result.total_legacy_quantity == 170.0
        assert result.total_nova_quantity == 170.0
        assert result.total_quantity_delta == 0.0
        # Valuation: (100*10) + (50*12) + (20*10) = 1000 + 600 + 200 = 1800.0
        assert result.total_legacy_valuation == 1800.0
        assert result.total_nova_valuation == 1800.0
        assert result.total_valuation_delta == 0.0
        assert result.negative_stock_count == 0
        assert result.is_reconciled is True
        assert len(result.warehouse_summaries) == 2
        assert "Main Warehouse" in result.warehouse_summaries
        assert "Branch A" in result.warehouse_summaries
        assert result.warehouse_summaries["Main Warehouse"].item_count == 2
        assert result.warehouse_summaries["Main Warehouse"].mismatched_count == 0
        assert result.warehouse_summaries["Branch A"].item_count == 1

    def test_inventory_quantity_and_valuation_variances(self):
        legacy = [
            {"sku": "SKU-A", "name": "Item A", "warehouse": "Main", "qty": 100.0, "cost_price": 20.0},
            {"sku": "SKU-B", "name": "Item B", "warehouse": "Main", "qty": 50.0, "cost_price": 10.0},
        ]
        nova = [
            {"sku": "SKU-A", "name": "Item A", "warehouse": "Main", "qty": 90.0, "cost_price": 20.0},  # -10 qty, -200 val
            {"sku": "SKU-B", "name": "Item B", "warehouse": "Main", "qty": 50.0, "cost_price": 10.0},  # Matched
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.total_legacy_quantity == 150.0
        assert result.total_nova_quantity == 140.0
        assert result.total_quantity_delta == 10.0
        assert result.total_legacy_valuation == 2500.0
        assert result.total_nova_valuation == 2300.0
        assert result.total_valuation_delta == 200.0
        assert result.is_reconciled is False
        assert len(result.discrepancies) == 1
        disc = result.discrepancies[0]
        assert disc.sku == "SKU-A"
        assert disc.quantity_delta == 10.0
        assert disc.valuation_delta == 200.0
        assert disc.status == "Mismatch"

    def test_negative_stock_detection_and_flagging(self):
        legacy = [
            {"sku": "NEG-01", "name": "Negative Syrup", "warehouse": "Main", "qty": -15.0, "cost_price": 5.0},
            {"sku": "POS-01", "name": "Positive Syrup", "warehouse": "Main", "qty": 100.0, "cost_price": 5.0},
        ]
        # In Nova, negative stock was clamped to 0.0 by cleansing engine
        nova = [
            {"sku": "NEG-01", "name": "Negative Syrup", "warehouse": "Main", "qty": 0.0, "cost_price": 5.0},
            {"sku": "POS-01", "name": "Positive Syrup", "warehouse": "Main", "qty": 100.0, "cost_price": 5.0},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.negative_stock_count == 1
        assert result.is_reconciled is False
        assert len(result.discrepancies) == 1
        disc = result.discrepancies[0]
        assert disc.sku == "NEG-01"
        assert disc.is_negative_stock is True
        assert disc.status == "NegativeStock"
        assert disc.legacy_quantity == -15.0
        assert disc.nova_quantity == 0.0

    def test_missing_stock_in_target_or_source(self):
        legacy = [
            {"sku": "ONLY-LEG", "name": "Legacy Only", "warehouse": "Main", "qty": 40.0, "cost_price": 8.0},
        ]
        nova = [
            {"sku": "ONLY-NOV", "name": "Nova Only", "warehouse": "Main", "qty": 25.0, "cost_price": 10.0},
        ]

        result = self.reconciler.reconcile(legacy, nova)

        assert result.is_reconciled is False
        assert len(result.discrepancies) == 2
        statuses = {d.sku: d.status for d in result.discrepancies}
        assert statuses["ONLY-LEG"] == "MissingInTarget"
        assert statuses["ONLY-NOV"] == "MissingInSource"


# ==============================================================================
# 3. Entity Count Reconciliation Tests
# ==============================================================================

class TestEntityCountReconciliation:
    def setup_method(self):
        self.reconciler = EntityCountReconciler()

    def test_entity_count_audit_flow(self):
        extracted = {
            "products": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
            "customers": [{"id": 101}, {"id": 102}],
            "suppliers": [{"id": 201}],
        }
        staged = {
            "products": [{"id": 1}, {"id": 2}, {"id": 3}],  # 1 skipped phantom
            "customers": [{"id": 101}, {"id": 102}],
            "suppliers": [],  # Failed due to error
        }
        cleansing = CleansingSummary(
            total_records_processed=7,
            phantom_products_detected=1,
            phantom_products_skipped=1,
            contacts_sanitized=2,
        )
        errors = [
            RowValidationError(
                row_index=1,
                entity_type="suppliers",
                error_type="missing_required",
                message="Supplier name is required",
                severity="error",
            )
        ]

        result = self.reconciler.reconcile(
            extracted_by_entity=extracted,
            staged_by_entity=staged,
            cleansing_summary=cleansing,
            validation_errors=errors,
        )

        assert "products" in result
        assert "customers" in result
        assert "suppliers" in result

        prod_stat = result["products"]
        assert prod_stat.source_count == 4
        assert prod_stat.staged_count == 3
        assert prod_stat.phantom_count == 1
        assert prod_stat.error_count == 0
        assert prod_stat.match_status == "CleanedWithDeltas"

        cust_stat = result["customers"]
        assert cust_stat.source_count == 2
        assert cust_stat.staged_count == 2
        assert cust_stat.cleansed_count == 2
        assert cust_stat.match_status == "Matched"

        supp_stat = result["suppliers"]
        assert supp_stat.source_count == 1
        assert supp_stat.staged_count == 0
        assert supp_stat.error_count == 1
        assert supp_stat.match_status == "ErrorsPresent"


# ==============================================================================
# 4. End-to-End Comprehensive Reconciliation Service Report Tests
# ==============================================================================

class TestReconciliationServiceFacade:
    def setup_method(self):
        self.service = ReconciliationService()

    def test_generate_passed_reconciliation_report(self):
        extracted = {
            "products": [
                {"sku": "P-01", "name": "Latte", "qty": 100, "cost_price": 5.0, "warehouse": "Main"},
                {"sku": "P-02", "name": "Mocha", "qty": 50, "cost_price": 6.0, "warehouse": "Main"},
            ],
            "customer_opening_balances": [
                {"customer_key": "C-01", "name": "Cafe Royal", "balance": 1200.0},
            ],
        }
        staged = {
            "products": [
                {"sku": "P-01", "name": "Latte", "qty": 100, "cost_price": 5.0, "warehouse": "Main"},
                {"sku": "P-02", "name": "Mocha", "qty": 50, "cost_price": 6.0, "warehouse": "Main"},
            ],
            "customer_opening_balances": [
                {"customer_key": "C-01", "name": "Cafe Royal", "total_amount": 1200.0},
            ],
        }

        report = self.service.generate_reconciliation_report(
            batch_key="TEST_BATCH_01",
            extracted_by_entity=extracted,
            staged_by_entity=staged,
        )

        assert isinstance(report, ReconciliationReport)
        assert report.batch_key == "TEST_BATCH_01"
        assert report.overall_status == "Passed"
        assert report.customer_balance is not None
        assert report.customer_balance.is_reconciled is True
        assert report.inventory is not None
        assert report.inventory.is_reconciled is True
        assert report.unresolved_errors_count == 0
        assert len(report.recommendations) >= 1
        assert "Customer Receivables: Fully balanced" in report.recommendations[0]

    def test_generate_failed_report_with_errors_and_variances(self):
        extracted = {
            "products": [
                {"sku": "P-10", "name": "Croissant", "qty": 50, "cost_price": 3.0, "warehouse": "Main"},
                {"sku": "P-11", "name": "Baguette", "qty": -5, "cost_price": 2.0, "warehouse": "Main"},
            ],
            "customers": [
                {"customer_key": "C-10", "name": "Client A", "balance": 5000.0},
            ],
        }
        staged = {
            "products": [
                {"sku": "P-10", "name": "Croissant", "qty": 50, "cost_price": 3.0, "warehouse": "Main"},
                {"sku": "P-11", "name": "Baguette", "qty": 0, "cost_price": 2.0, "warehouse": "Main"},  # Clamped negative
            ],
            "customers": [
                {"partner_id": "C-10", "name": "Client A", "balance": 1000.0},  # 4000.0 delta
            ],
        }
        cleansing = CleansingSummary(
            phantom_products_detected=2,
            clamped_numeric_values=1,
        )
        errors = [
            RowValidationError(
                row_index=1,
                entity_type="customers",
                error_type="constraint_violation",
                message="Credit limit exceeded",
                severity="error",
            )
        ]

        report = self.service.generate_reconciliation_report(
            batch_key="TEST_FAIL_01",
            extracted_by_entity=extracted,
            staged_by_entity=staged,
            cleansing_summary=cleansing,
            validation_errors=errors,
        )

        assert report.overall_status == "Failed"
        assert report.unresolved_errors_count == 1
        assert report.customer_balance.is_reconciled is False
        assert report.customer_balance.total_receivables_delta == 4000.0
        assert report.inventory.negative_stock_count == 1
        assert any("Resolve 1 fatal row validation errors" in r for r in report.recommendations)
        assert any("Opening Balance Discrepancy" in r for r in report.recommendations)
        assert any("Negative Inventory" in r for r in report.recommendations)
        assert any("Phantom Products" in r for r in report.recommendations)

    def test_passed_with_warnings_when_only_phantoms_present(self):
        extracted = {
            "products": [
                {"sku": "P-01", "name": "Active Product", "qty": 10, "cost_price": 5.0, "warehouse": "Main"},
                {"sku": "P-GHOST", "name": "Ghost Product", "qty": 0, "cost_price": 0.0, "warehouse": "Main"},
            ],
        }
        staged = {
            "products": [
                {"sku": "P-01", "name": "Active Product", "qty": 10, "cost_price": 5.0, "warehouse": "Main"},
                {"sku": "P-GHOST", "name": "Ghost Product", "qty": 0, "cost_price": 0.0, "warehouse": "Main"},
            ],
        }
        cleansing = CleansingSummary(
            phantom_products_detected=1,
        )

        report = self.service.generate_reconciliation_report(
            batch_key="TEST_WARN_01",
            extracted_by_entity=extracted,
            staged_by_entity=staged,
            cleansing_summary=cleansing,
        )

        assert report.overall_status == "PassedWithWarnings"
        assert report.unresolved_errors_count == 0
        assert any("Phantom Products: Detected 1 inactive/ghost" in r for r in report.recommendations)

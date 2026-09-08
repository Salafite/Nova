import pytest
from datetime import date
from pydantic import ValidationError

from modules.accounting.models import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceCatchWeightLineBreakdown,
    InvoiceCatchWeightBreakdownResponse,
    InvoiceCatchWeightSummary,
    InvoiceRecalculateAndCreateRequest,
)


class TestInvoiceCatchWeightModels:
    def test_invoice_create_catch_weight_defaults(self):
        """Test default values for catch-weight attributes on InvoiceCreate."""
        invoice = InvoiceCreate(
            partner_id=10,
            issue_date=date(2026, 8, 23),
            due_date=date(2026, 9, 23),
            total_amount=500.0,
        )
        assert invoice.is_catch_weight is False
        assert invoice.nominal_total_weight is None
        assert invoice.actual_total_weight is None
        assert invoice.weight_adjustment_amount == 0.0

    def test_invoice_create_with_catch_weight_values(self):
        """Test explicit catch-weight values on InvoiceCreate."""
        invoice = InvoiceCreate(
            invoice_number='INV-2026-001',
            partner_id=12,
            sales_order_id=45,
            issue_date=date(2026, 8, 23),
            due_date=date(2026, 9, 23),
            total_amount=1260.0,
            is_catch_weight=True,
            nominal_total_weight=80.0,
            actual_total_weight=84.0,
            weight_adjustment_amount=60.0,
        )
        assert invoice.is_catch_weight is True
        assert invoice.nominal_total_weight == 80.0
        assert invoice.actual_total_weight == 84.0
        assert invoice.weight_adjustment_amount == 60.0

    def test_invoice_create_validation_negative_nominal_weight_rejected(self):
        """Test that negative nominal_total_weight raises ValidationError."""
        with pytest.raises(ValidationError):
            InvoiceCreate(
                partner_id=10,
                issue_date=date(2026, 8, 23),
                due_date=date(2026, 9, 23),
                total_amount=500.0,
                nominal_total_weight=-5.0,
            )

    def test_invoice_create_validation_negative_actual_weight_rejected(self):
        """Test that negative actual_total_weight raises ValidationError."""
        with pytest.raises(ValidationError):
            InvoiceCreate(
                partner_id=10,
                issue_date=date(2026, 8, 23),
                due_date=date(2026, 9, 23),
                total_amount=500.0,
                actual_total_weight=-2.5,
            )

    def test_invoice_update_catch_weight_partial(self):
        """Test partial update with catch-weight fields on InvoiceUpdate."""
        update_data = InvoiceUpdate(
            is_catch_weight=True,
            nominal_total_weight=100.0,
            actual_total_weight=102.5,
            weight_adjustment_amount=37.5,
        )
        assert update_data.is_catch_weight is True
        assert update_data.nominal_total_weight == 100.0
        assert update_data.actual_total_weight == 102.5
        assert update_data.weight_adjustment_amount == 37.5

    def test_invoice_response_serialization(self):
        """Test serialization and deserialization of InvoiceResponse with catch weight."""
        resp = InvoiceResponse(
            id=1,
            invoice_number='INV-CW-100',
            invoice_type='Sales',
            partner_id=5,
            sales_order_id=20,
            issue_date=date(2026, 8, 23),
            due_date=date(2026, 9, 23),
            total_amount=1575.0,
            status='Unpaid',
            is_catch_weight=True,
            nominal_total_weight=150.0,
            actual_total_weight=157.5,
            weight_adjustment_amount=75.0,
        )
        assert resp.id == 1
        assert resp.is_catch_weight is True
        assert resp.nominal_total_weight == 150.0
        assert resp.actual_total_weight == 157.5
        assert resp.weight_adjustment_amount == 75.0

    def test_invoice_catch_weight_line_breakdown_schema(self):
        """Test InvoiceCatchWeightLineBreakdown model."""
        line = InvoiceCatchWeightLineBreakdown(
            id=10,
            sales_order_id=20,
            product_id=3,
            product_name='Aged Gouda Wheel',
            uom_id=1,
            qty=4.0,
            unit_price=200.0,
            line_total=800.0,
            is_catch_weight=True,
            pricing_uom_id=2,
            unit_price_pricing_uom=20.0,
            nominal_weight=40.0,
            catch_weight_actual=42.5,
            recalculated_total=850.0,
        )
        assert line.id == 10
        assert line.product_name == 'Aged Gouda Wheel'
        assert line.is_catch_weight is True
        assert line.nominal_weight == 40.0
        assert line.catch_weight_actual == 42.5
        assert line.recalculated_total == 850.0

    def test_invoice_catch_weight_breakdown_response_schema(self):
        """Test InvoiceCatchWeightBreakdownResponse model."""
        breakdown = InvoiceCatchWeightBreakdownResponse(
            invoice_id=5,
            invoice_number='INV-00005',
            is_catch_weight=True,
            nominal_total_weight=40.0,
            actual_total_weight=42.5,
            weight_adjustment_amount=25.0,
            total_amount=425.0,
            sales_order_id=30,
            lines=[
                {
                    'id': 1,
                    'product_name': 'Cheddar Block',
                    'line_total': 400.0,
                    'recalculated_total': 425.0,
                    'is_catch_weight': True,
                    'nominal_weight': 40.0,
                    'catch_weight_actual': 42.5,
                }
            ],
        )
        assert breakdown.invoice_id == 5
        assert breakdown.is_catch_weight is True
        assert breakdown.nominal_total_weight == 40.0
        assert breakdown.actual_total_weight == 42.5
        assert breakdown.weight_adjustment_amount == 25.0
        assert len(breakdown.lines) == 1

    def test_invoice_catch_weight_summary_schema(self):
        """Test InvoiceCatchWeightSummary model."""
        summary = InvoiceCatchWeightSummary(
            is_catch_weight=True,
            nominal_total_weight=80.0,
            actual_total_weight=84.0,
            weight_adjustment_amount=60.0,
            original_subtotal=1200.0,
            recalculated_subtotal=1260.0,
            lines=[],
        )
        assert summary.is_catch_weight is True
        assert summary.nominal_total_weight == 80.0
        assert summary.actual_total_weight == 84.0
        assert summary.weight_adjustment_amount == 60.0
        assert summary.recalculated_subtotal == 1260.0

    def test_invoice_recalculate_and_create_request_schema(self):
        """Test InvoiceRecalculateAndCreateRequest model."""
        req = InvoiceRecalculateAndCreateRequest(order_id=42, update_customer_balance=True)
        assert req.order_id == 42
        assert req.update_customer_balance is True

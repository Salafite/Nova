import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from modules.sales.models.sales import SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse
from modules.sales.controllers.T0012I import repo as sales_order_repo
from modules.sales.services.sales_service import SalesOrderService, ORDER_REPO


class TestSalesOrderModelsPaymentTermId:
    """Test suite for Sales Order Pydantic models supporting payment_term_id."""

    def test_sales_order_create_with_payment_term_id(self):
        order = SalesOrderCreate(
            order_number='SO-2026-001',
            customer_id=10,
            warehouse_id=1,
            subtotal=1000.0,
            tax=100.0,
            grand_total=1100.0,
            order_date=date(2026, 8, 25),
            payment_term_id=2,
            business_id=1,
        )
        assert order.order_number == 'SO-2026-001'
        assert order.customer_id == 10
        assert order.payment_term_id == 2
        assert order.grand_total == 1100.0

    def test_sales_order_create_without_payment_term_id_defaults_to_none(self):
        order = SalesOrderCreate(
            order_number='SO-2026-002',
            customer_id=10,
        )
        assert order.payment_term_id is None

    def test_sales_order_update_with_payment_term_id(self):
        update_payload = SalesOrderUpdate(payment_term_id=3)
        assert update_payload.payment_term_id == 3

    def test_sales_order_update_clear_payment_term_id(self):
        update_payload = SalesOrderUpdate(payment_term_id=None)
        assert update_payload.payment_term_id is None

    def test_sales_order_response_serialization_with_payment_term_id(self):
        resp = SalesOrderResponse(
            id=50,
            order_number='SO-2026-003',
            customer_id=10,
            warehouse_id=1,
            subtotal=2000.0,
            tax=200.0,
            grand_total=2200.0,
            status='Pending',
            order_date=date(2026, 8, 25),
            payment_term_id=4,
            business_id=1,
            update_number=1,
        )
        assert resp.id == 50
        assert resp.order_number == 'SO-2026-003'
        assert resp.payment_term_id == 4
        data = resp.model_dump()
        assert data['payment_term_id'] == 4


class TestSalesOrderCrudRepositoryPaymentTermId:
    """Test suite verifying CrudRepository for T0012 includes payment_term_id in business columns."""

    def test_sales_order_repo_business_columns_contains_payment_term_id(self):
        assert 'payment_term_id' in sales_order_repo.business_columns
        assert 'payment_term_id' in ORDER_REPO.business_columns

    @patch('modules.core.repositories.base.get_connection')
    @patch('modules.core.repositories.base.release_connection')
    def test_sales_order_repo_create_includes_payment_term_id(self, mock_release, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'order_number': 'SO-2026-004',
            'customer_id': 10,
            'payment_term_id': 3,
            'status': 'Pending',
            'business_id': 1,
        }
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value = mock_context
        mock_get_conn.return_value = mock_conn

        created = sales_order_repo.create({
            'order_number': 'SO-2026-004',
            'customer_id': 10,
            'payment_term_id': 3,
            'business_id': 1,
        })
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"payment_term_id"' in sql
        assert 3 in params
        assert created['payment_term_id'] == 3

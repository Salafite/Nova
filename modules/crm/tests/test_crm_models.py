import pytest
from unittest.mock import patch, MagicMock
from modules.crm.models.crm import CustomerCreate, CustomerUpdate, CustomerResponse
from modules.crm.controllers.T0010I import repo as customer_repo
from modules.crm.services.customer_service import CustomerService


class TestCustomerModelsPaymentTermId:
    """Test suite for Customer Pydantic models supporting payment_term_id."""

    def test_customer_create_with_payment_term_id(self):
        cust = CustomerCreate(
            name='Test Customer Ltd',
            group_name='Wholesale',
            phone='+1-555-0199',
            email='billing@testcustomer.com',
            credit_limit=50000.0,
            payment_term_id=3,
            business_id=1,
        )
        assert cust.name == 'Test Customer Ltd'
        assert cust.payment_term_id == 3
        assert cust.group_name == 'Wholesale'
        assert cust.credit_limit == 50000.0

    def test_customer_create_without_payment_term_id_defaults_to_none(self):
        cust = CustomerCreate(name='Cash Only Customer')
        assert cust.name == 'Cash Only Customer'
        assert cust.payment_term_id is None

    def test_customer_update_with_payment_term_id(self):
        update_payload = CustomerUpdate(payment_term_id=2)
        assert update_payload.payment_term_id == 2

    def test_customer_update_clear_payment_term_id(self):
        update_payload = CustomerUpdate(payment_term_id=None)
        assert update_payload.payment_term_id is None

    def test_customer_response_serialization_with_payment_term_id(self):
        resp = CustomerResponse(
            id=101,
            name='Acme Corp',
            group_name='Retail',
            credit_limit=10000.0,
            balance=2500.0,
            is_active=True,
            payment_term_id=4,
            business_id=1,
            update_number=1,
        )
        assert resp.id == 101
        assert resp.name == 'Acme Corp'
        assert resp.payment_term_id == 4
        assert resp.balance == 2500.0
        data = resp.model_dump()
        assert data['payment_term_id'] == 4


class TestCustomerCrudRepositoryPaymentTermId:
    """Test suite verifying CrudRepository for T0010 includes payment_term_id in business columns."""

    def test_customer_repo_business_columns_contains_payment_term_id(self):
        assert 'payment_term_id' in customer_repo.business_columns

    @patch('modules.core.repositories.base.get_connection')
    @patch('modules.core.repositories.base.release_connection')
    def test_customer_repo_create_includes_payment_term_id(self, mock_release, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'name': 'Term Customer',
            'payment_term_id': 5,
            'business_id': 1,
        }
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value = mock_context
        mock_get_conn.return_value = mock_conn

        created = customer_repo.create({
            'name': 'Term Customer',
            'payment_term_id': 5,
            'business_id': 1,
        })
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert '"payment_term_id"' in sql
        assert 5 in params
        assert created['payment_term_id'] == 5

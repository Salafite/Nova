from unittest.mock import patch, MagicMock
from packages.mcp.servers import accounting_mcp
from packages.mcp.servers.accounting_mcp import register_tools


class TestAccountingMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()
        registry._resources.clear()

    def test_list_coa(self):
        with patch.multiple(accounting_mcp, _coa_svc=MagicMock()):
            accounting_mcp._coa_svc.list.return_value = [{"id": 1, "account_code": "1000"}]
            result = accounting_mcp._list_coa()
            assert result == [{"id": 1, "account_code": "1000"}]

    def test_list_invoices(self):
        with patch.multiple(accounting_mcp, _inv_svc=MagicMock()):
            accounting_mcp._inv_svc.list.return_value = [
                {
                    "id": 1,
                    "invoice_number": "INV-001",
                    "payment_term_id": 5,
                    "due_date": "2026-09-24",
                    "discount_due_date": "2026-09-04",
                    "discount_percentage": 2.0,
                    "discount_days": 10,
                    "early_discount_amount": 20.0,
                }
            ]
            result = accounting_mcp._list_invoices(payment_term_id=5, status="Unpaid")
            assert result[0]["invoice_number"] == "INV-001"
            assert result[0]["payment_term_id"] == 5
            assert result[0]["early_discount_amount"] == 20.0
            accounting_mcp._inv_svc.list.assert_called_once_with(
                filters={"status": "Unpaid", "payment_term_id": 5},
                limit=50,
            )

    def test_get_invoice(self):
        with patch.multiple(accounting_mcp, _inv_svc=MagicMock(), _terms_svc=MagicMock()):
            accounting_mcp._inv_svc.get.return_value = {
                "id": 1,
                "total_amount": 1000.0,
                "payment_term_id": 2,
                "due_date": "2026-09-24",
                "discount_due_date": "2026-09-04",
                "discount_percentage": 2.0,
                "discount_days": 10,
                "early_discount_amount": 20.0,
            }
            accounting_mcp._terms_svc.get.return_value = {
                "id": 2,
                "name": "2/10 Net 30",
                "code": "2_10_NET_30",
                "due_days": 30,
                "discount_percentage": 2.0,
                "discount_days": 10,
            }
            res = accounting_mcp._get_invoice(1)
            assert res["total_amount"] == 1000.0
            assert res["payment_term"]["name"] == "2/10 Net 30"
            assert res["early_discount_amount"] == 20.0

    def test_list_payments(self):
        with patch.multiple(accounting_mcp, _pay_svc=MagicMock()):
            accounting_mcp._pay_svc.list.return_value = [{"id": 1, "amount": 50, "invoice_id": 10}]
            result = accounting_mcp._list_payments(invoice_id=10)
            assert len(result) == 1
            assert result[0]["invoice_id"] == 10
            accounting_mcp._pay_svc.list.assert_called_once_with(
                filters={"invoice_id": 10},
                limit=50,
            )

    def test_list_terms(self):
        with patch.multiple(accounting_mcp, _terms_svc=MagicMock()):
            accounting_mcp._terms_svc.list.return_value = [
                {"id": 1, "name": "Net 30", "code": "NET_30", "due_days": 30, "is_active": True, "is_default": True},
                {"id": 2, "name": "2/10 Net 30", "code": "2_10_NET_30", "due_days": 30, "discount_percentage": 2.0, "discount_days": 10, "is_active": True},
            ]
            res = accounting_mcp._list_terms(is_active=True)
            assert len(res) == 2
            assert res[1]["discount_percentage"] == 2.0
            accounting_mcp._terms_svc.list.assert_called_once_with(
                filters={"is_active": True},
                limit=50,
            )

    def test_get_payment_term_by_id(self):
        with patch.multiple(accounting_mcp, _terms_svc=MagicMock()):
            accounting_mcp._terms_svc.get.return_value = {"id": 3, "code": "NET_15", "due_days": 15}
            res = accounting_mcp._get_payment_term(id=3)
            assert res["code"] == "NET_15"
            assert res["due_days"] == 15

    def test_get_payment_term_by_code(self):
        with patch.multiple(accounting_mcp, _terms_svc=MagicMock()):
            accounting_mcp._terms_svc.list.return_value = [{"id": 4, "code": "COD", "due_days": 0}]
            res = accounting_mcp._get_payment_term(code="COD")
            assert res["code"] == "COD"
            assert res["due_days"] == 0

    def test_get_payment_term_standard_fallback(self):
        with patch.multiple(accounting_mcp, _terms_svc=MagicMock()):
            accounting_mcp._terms_svc.list.return_value = []
            res = accounting_mcp._get_payment_term(code="NET_60")
            assert res is not None
            assert res["code"] == "NET_60"
            assert res["due_days"] == 60

    def test_preview_invoice_early_discount(self):
        with patch.multiple(accounting_mcp, _pay_svc=MagicMock()):
            accounting_mcp._pay_svc.preview_payment_discount.return_value = {
                "invoice_id": 10,
                "is_eligible": True,
                "discount_percentage": 2.0,
                "discount_amount": 20.0,
                "net_amount_due": 980.0,
            }
            res = accounting_mcp._preview_invoice_early_discount(invoice_id=10, payment_date="2026-08-30")
            assert res["is_eligible"] is True
            assert res["discount_amount"] == 20.0
            assert res["net_amount_due"] == 980.0

    def test_parse_bank_statement_mcp(self):
        csv_data = "Date,Check Number,Payee,Amount\n2026-09-01,1001,Customer ABC,500.00\n2026-09-02,1002,Customer XYZ,250.00"
        res = accounting_mcp._parse_bank_statement(file_content=csv_data, file_name="statement.csv", file_type="CSV")
        assert res["file_type"] == "CSV"
        assert res["total_transactions"] == 2
        assert len(res["transactions"]) == 2
        assert res["transactions"][0]["check_number"] == "1001"
        assert res["transactions"][0]["amount"] == 500.00

    def test_auto_match_bank_statement_checks_mcp(self):
        with patch.object(accounting_mcp._matching_svc, "match_statement_transactions") as mock_match:
            mock_match.return_value = {
                "statement_id": 1,
                "total_transactions": 2,
                "matched_count": 2,
                "unmatched_count": 0,
                "matches": [
                    {"transaction_id": 10, "matched_payment_id": 100, "check_number": "1001", "score": 1.0},
                ],
            }
            res = accounting_mcp._auto_match_bank_statement_checks(statement_id=1, date_tolerance_days=15, min_score_threshold=0.8)
            assert res["matched_count"] == 2
            assert res["matches"][0]["check_number"] == "1001"
            mock_match.assert_called_once_with(
                statement_id=1,
                date_tolerance_days=15,
                min_score_threshold=0.8,
            )

    def test_confirm_batch_check_clearing_mcp(self):
        with patch.object(accounting_mcp._clearing_svc, "clear_matched_checks_batch") as mock_clear:
            mock_clear.return_value = {
                "statement_id": 1,
                "cleared_count": 2,
                "total_amount": 750.0,
                "cleared_payment_ids": [100, 101],
                "journal_entry_ids": [501, 502],
                "statement_status": "Reconciled",
            }
            res = accounting_mcp._confirm_batch_check_clearing(statement_id=1, transaction_ids=[10, 11])
            assert res["cleared_count"] == 2
            assert res["total_amount"] == 750.0
            assert res["statement_status"] == "Reconciled"
            mock_clear.assert_called_once_with(
                statement_id=1,
                transaction_ids=[10, 11],
            )

    def test_process_bounced_check_mcp(self):
        with patch.object(accounting_mcp._bounced_svc, "process_bounced_check") as mock_bounce:
            mock_bounce.return_value = {
                "bounced_check_number": "1001",
                "bounced_reason": "NSF - Non-Sufficient Funds",
                "penalty_fee": 35.0,
                "payment_amount": 500.0,
                "reopened_invoice_id": 42,
                "customer_id": 5,
                "status": "Bounced",
            }
            res = accounting_mcp._process_bounced_check(
                payment_id=100,
                bounced_reason="NSF - Non-Sufficient Funds",
                penalty_fee=35.0,
            )
            assert res["status"] == "Bounced"
            assert res["penalty_fee"] == 35.0
            assert res["reopened_invoice_id"] == 42
            mock_bounce.assert_called_once_with(
                clearing_record_id=None,
                payment_id=100,
                statement_transaction_id=None,
                check_number=None,
                bounced_date=None,
                bounced_reason="NSF - Non-Sufficient Funds",
                penalty_fee=35.0,
                notes=None,
            )

    def test_list_bounced_checks_mcp(self):
        with patch.object(accounting_mcp._bounced_svc, "list_bounced_checks") as mock_list:
            mock_list.return_value = [
                {"id": 1, "check_number": "1001", "status": "Bounced", "penalty_fee": 35.0},
            ]
            res = accounting_mcp._list_bounced_checks(customer_id=5)
            assert len(res) == 1
            assert res[0]["check_number"] == "1001"
            mock_list.assert_called_once_with(customer_id=5)

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools, list_resources
        names = [t.name for t in get_tools()]
        assert "list_chart_of_accounts" in names
        assert "list_invoices" in names
        assert "get_invoice" in names
        assert "list_payments" in names
        assert "list_payment_terms" in names
        assert "get_payment_term" in names
        assert "preview_invoice_early_discount" in names
        assert "parse_bank_statement" in names
        assert "auto_match_bank_statement_checks" in names
        assert "confirm_batch_check_clearing" in names
        assert "process_bounced_check" in names
        assert "list_bounced_checks" in names

        uris = [r.uri for r in list_resources()]
        assert "nova://accounting/payment-terms" in uris
        assert "nova://accounting/invoices" in uris



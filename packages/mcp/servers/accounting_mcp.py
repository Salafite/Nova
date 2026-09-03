from typing import Optional, Union, Dict, Any
from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from modules.accounting.services.payment_term_service import (
    PAYMENT_TERM_REPO,
    PaymentTermService,
    get_standard_payment_term,
    calculate_early_discount,
)
from modules.accounting.services.invoice_service import INVOICE_REPO, InvoiceService
from modules.accounting.services.payment_service import PAYMENT_REPO, PaymentService
from modules.accounting.services.bank_statement_parser import BankStatementParser
from modules.accounting.services.check_matching_service import CheckMatchingService
from modules.accounting.services.check_clearing_service import CheckClearingService
from modules.accounting.services.bounced_check_service import BouncedCheckService
from packages.mcp.registry import register_tool, register_resource
from packages.mcp.types import Tool, Resource


_coa_repo = CrudRepository('T0026', business_columns=['id', 'account_code', 'account_name', 'account_type', 'parent_id', 'currency', 'is_active'])
_coa_svc = CrudService(_coa_repo)

_inv_repo = INVOICE_REPO
_inv_svc = InvoiceService(_inv_repo)

_terms_repo = PAYMENT_TERM_REPO
_terms_svc = PaymentTermService(_terms_repo)

_pay_repo = PAYMENT_REPO
_pay_svc = PaymentService(_pay_repo, _inv_repo, payment_term_repo=_terms_repo)

_matching_svc = CheckMatchingService()
_clearing_svc = CheckClearingService()
_bounced_svc = BouncedCheckService()


def _list_coa(account_type: str = None, limit: int = 100):
    filters = {}
    if account_type:
        filters["account_type"] = account_type
    return _coa_svc.list(filters=filters or None, limit=limit)


def _list_invoices(
    status: str = None,
    partner_id: int = None,
    invoice_type: str = None,
    payment_term_id: int = None,
    limit: int = 50,
):
    filters = {}
    if status:
        filters["status"] = status
    if partner_id:
        filters["partner_id"] = partner_id
    if invoice_type:
        filters["invoice_type"] = invoice_type
    if payment_term_id:
        filters["payment_term_id"] = payment_term_id
    return _inv_svc.list(filters=filters or None, limit=limit)


def _get_invoice(id: int):
    inv = _inv_svc.get(id)
    if inv and isinstance(inv, dict) and inv.get("payment_term_id"):
        try:
            term = _terms_svc.get(inv["payment_term_id"])
            if term:
                inv["payment_term"] = term
        except Exception:
            pass
    return inv


def _list_payments(
    partner_id: int = None,
    invoice_id: int = None,
    status: str = None,
    limit: int = 50,
):
    filters = {}
    if partner_id:
        filters["partner_id"] = partner_id
    if invoice_id:
        filters["invoice_id"] = invoice_id
    if status:
        filters["status"] = status
    return _pay_svc.list(filters=filters or None, limit=limit)


def _list_terms(is_active: bool = None, limit: int = 50):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    return _terms_svc.list(filters=filters or None, limit=limit)


def _get_payment_term(id: int = None, code: str = None):
    if id is not None:
        return _terms_svc.get(id)
    if code:
        terms = _terms_svc.list(filters={"code": code})
        if terms:
            return terms[0]
        return get_standard_payment_term(code)
    return None


def _preview_invoice_early_discount(
    invoice_id: int,
    payment_date: str = None,
    payment_amount: float = None,
    grace_days: int = 0,
):
    if hasattr(_pay_svc, "preview_payment_discount"):
        try:
            return _pay_svc.preview_payment_discount(
                invoice_id=invoice_id,
                payment_date=payment_date,
                payment_amount=payment_amount,
                grace_days=grace_days,
            )
        except Exception:
            pass

    inv = _inv_svc.get(invoice_id)
    if not inv:
        raise ValueError(f"Invoice {invoice_id} not found")
    total = float(inv.get("total_amount", 0.0) or 0.0)
    disc_due = inv.get("discount_due_date")
    disc_pct = float(inv.get("discount_percentage", 0.0) or 0.0)
    return calculate_early_discount(
        total_amount=payment_amount if payment_amount is not None else total,
        payment_date=payment_date,
        discount_due_date=disc_due,
        discount_percentage=disc_pct,
        grace_days=grace_days,
    )


def _parse_bank_statement(
    file_content: str,
    file_name: Optional[str] = "",
    file_type: Optional[str] = None,
):
    parsed = BankStatementParser.parse_file(
        file_content=file_content,
        file_name=file_name or "",
        file_type=file_type,
    )
    return parsed.to_dict()


def _auto_match_bank_statement_checks(
    statement_id: int,
    date_tolerance_days: int = 30,
    min_score_threshold: float = 0.70,
):
    return _matching_svc.match_statement_transactions(
        statement_id=statement_id,
        date_tolerance_days=date_tolerance_days,
        min_score_threshold=min_score_threshold,
    )


def _confirm_batch_check_clearing(
    statement_id: int,
    transaction_ids: Optional[list] = None,
):
    return _clearing_svc.clear_matched_checks_batch(
        statement_id=statement_id,
        transaction_ids=transaction_ids,
    )


def _process_bounced_check(
    clearing_record_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    statement_transaction_id: Optional[int] = None,
    check_number: Optional[str] = None,
    bounced_date: Optional[str] = None,
    bounced_reason: str = "NSF - Non-Sufficient Funds",
    penalty_fee: float = 0.0,
    notes: Optional[str] = None,
):
    return _bounced_svc.process_bounced_check(
        clearing_record_id=clearing_record_id,
        payment_id=payment_id,
        statement_transaction_id=statement_transaction_id,
        check_number=check_number,
        bounced_date=bounced_date,
        bounced_reason=bounced_reason,
        penalty_fee=penalty_fee,
        notes=notes,
    )


def _list_bounced_checks(
    customer_id: Optional[int] = None,
    limit: int = 50,
):
    results = _bounced_svc.list_bounced_checks(customer_id=customer_id)
    if limit and len(results) > limit:
        return results[:limit]
    return results


def register_tools():
    register_tool(
        Tool(
            name="list_chart_of_accounts",
            description="List chart of accounts",
            input_schema={
                "type": "object",
                "properties": {
                    "account_type": {"type": "string", "description": "Filter by account type (Asset, Liability, Equity, Income, Expense)"},
                    "limit": {"type": "integer", "description": "Max results (default 100)"},
                },
            },
        ),
        _list_coa,
    )
    register_tool(
        Tool(
            name="list_invoices",
            description="List invoices with payment terms and discount metadata",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (Unpaid, Paid, Overdue, Cancelled)"},
                    "partner_id": {"type": "integer", "description": "Filter by customer/partner ID"},
                    "invoice_type": {"type": "string", "description": "Filter by invoice type (Sales, Purchase)"},
                    "payment_term_id": {"type": "integer", "description": "Filter by payment term ID"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_invoices,
    )
    register_tool(
        Tool(
            name="get_invoice",
            description="Get invoice by ID with linked payment terms and discount cutoff metadata",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Invoice ID"},
                },
                "required": ["id"],
            },
        ),
        _get_invoice,
    )
    register_tool(
        Tool(
            name="list_payments",
            description="List payments received with optional invoice and partner filters",
            input_schema={
                "type": "object",
                "properties": {
                    "partner_id": {"type": "integer", "description": "Filter by customer/partner ID"},
                    "invoice_id": {"type": "integer", "description": "Filter by invoice ID"},
                    "status": {"type": "string", "description": "Filter by payment status (Completed, Pending, Failed)"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_payments,
    )
    register_tool(
        Tool(
            name="list_payment_terms",
            description="List payment terms including discount percentage, discount days, and due days",
            input_schema={
                "type": "object",
                "properties": {
                    "is_active": {"type": "boolean", "description": "Filter by active status"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_terms,
    )
    register_tool(
        Tool(
            name="get_payment_term",
            description="Get payment term details by ID or code",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Payment term ID"},
                    "code": {"type": "string", "description": "Payment term code (e.g. NET_30, COD, 2_10_NET_30)"},
                },
            },
        ),
        _get_payment_term,
    )
    register_tool(
        Tool(
            name="preview_invoice_early_discount",
            description="Evaluate early payment discount eligibility, discount cutoff date, and net amount due for an invoice",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Invoice ID to evaluate discount for"},
                    "payment_date": {"type": "string", "description": "Proposed payment date (YYYY-MM-DD, defaults to today)"},
                    "payment_amount": {"type": "number", "description": "Proposed payment amount (defaults to invoice balance due)"},
                    "grace_days": {"type": "integer", "description": "Optional grace period days allowed past discount cutoff (default 0)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _preview_invoice_early_discount,
    )
    register_tool(
        Tool(
            name="parse_bank_statement",
            description="Parse an OFX or CSV bank statement file content into standardized statement header and transaction objects",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "file_content": {"type": "string", "description": "Raw string content of the OFX or CSV bank statement file"},
                    "file_name": {"type": "string", "description": "Optional file name (e.g. statement.ofx or bank_reconcile.csv)"},
                    "file_type": {"type": "string", "description": "Optional file format type override ('OFX' or 'CSV')"},
                },
                "required": ["file_content"],
            },
        ),
        _parse_bank_statement,
    )
    register_tool(
        Tool(
            name="auto_match_bank_statement_checks",
            description="Auto-match imported bank statement transaction lines against pending customer checks in ERP with match confidence scores",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "statement_id": {"type": "integer", "description": "Bank statement header ID (t0108)"},
                    "date_tolerance_days": {"type": "integer", "description": "Maximum date difference in days to match (default 30)"},
                    "min_score_threshold": {"type": "number", "description": "Minimum match confidence score (0.0 to 1.0, default 0.70)"},
                },
                "required": ["statement_id"],
            },
        ),
        _auto_match_bank_statement_checks,
    )
    register_tool(
        Tool(
            name="confirm_batch_check_clearing",
            description="Execute 1-click batch clearing for matched bank statement checks, updating check statuses to Cleared and posting General Ledger journal entries",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "statement_id": {"type": "integer", "description": "Bank statement header ID (t0108)"},
                    "transaction_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional explicit list of statement transaction line IDs to clear. If omitted, clears all matched transactions.",
                    },
                },
                "required": ["statement_id"],
            },
        ),
        _confirm_batch_check_clearing,
    )
    register_tool(
        Tool(
            name="process_bounced_check",
            description="Process a bounced or returned customer check: mark check as Bounced, reopen original customer invoice balances, charge NSF penalty fees, update customer credit hold status, and notify sales rep",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "clearing_record_id": {"type": "integer", "description": "Optional ID of check clearing record (t0110)"},
                    "payment_id": {"type": "integer", "description": "Optional ID of ERP customer payment (t0091)"},
                    "statement_transaction_id": {"type": "integer", "description": "Optional ID of bank statement transaction line (t0109)"},
                    "check_number": {"type": "string", "description": "Optional check number string"},
                    "bounced_date": {"type": "string", "description": "Optional date check bounced (YYYY-MM-DD, defaults to today)"},
                    "bounced_reason": {"type": "string", "description": "Reason for bounced check (e.g. NSF - Non-Sufficient Funds, Stop Payment)"},
                    "penalty_fee": {"type": "number", "description": "NSF penalty fee amount charged to customer (default 0.0)"},
                    "notes": {"type": "string", "description": "Optional custom notes for bounced check record"},
                },
            },
        ),
        _process_bounced_check,
    )
    register_tool(
        Tool(
            name="list_bounced_checks",
            description="List bounced customer checks with details on penalty fees, customer account balances, and reopened invoices",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Filter by customer/partner ID"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_bounced_checks,
    )
    register_resource(
        Resource(uri="nova://accounting/payment-terms", name="Payment Terms", description="List of all payment terms"),
        _list_terms,
    )
    register_resource(
        Resource(uri="nova://accounting/invoices", name="All Invoices", description="List of all invoices"),
        _list_invoices,
    )


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="accounting-mcp", version="1.0"))


if __name__ == "__main__":
    main()


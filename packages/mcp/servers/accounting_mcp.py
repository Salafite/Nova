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
from modules.accounting.services.einvoice_service import EInvoiceService
from modules.accounting.models.einvoice import (
    EINVOICE_RECORD_REPO,
    FISCAL_PROFILE_REPO,
)
from modules.accounting.services.ar_reminder_service import (
    ARReminderService,
    ar_reminder_service,
)
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

_einvoice_repo = EINVOICE_RECORD_REPO
_fiscal_profile_repo = FISCAL_PROFILE_REPO
_einvoice_svc = EInvoiceService(
    repo=_einvoice_repo,
    fiscal_profile_repo=_fiscal_profile_repo,
    invoice_repo=_inv_repo,
)

_reminder_svc = ar_reminder_service


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
    purchase_return_id: int = None,
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
    if purchase_return_id is not None:
        filters["purchase_return_id"] = purchase_return_id
    return _inv_svc.list(filters=filters or None, limit=limit)


def _list_debit_memos(
    purchase_return_id: Optional[int] = None,
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    if hasattr(_inv_svc, "get_debit_memos"):
        return _inv_svc.get_debit_memos(
            purchase_return_id=purchase_return_id,
            partner_id=partner_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    filters = {"invoice_type": "Debit Memo"}
    if purchase_return_id is not None:
        filters["purchase_return_id"] = purchase_return_id
    if partner_id is not None:
        filters["partner_id"] = partner_id
    if status is not None:
        filters["status"] = status
    return _inv_svc.list(filters=filters, limit=limit, offset=offset)


def _get_debit_memo_for_rma(purchase_return_id: int):
    if not purchase_return_id:
        return {"found": False, "error": "purchase_return_id is required"}

    dm = None
    if hasattr(_inv_svc, "get_debit_memo_by_purchase_return"):
        dm = _inv_svc.get_debit_memo_by_purchase_return(purchase_return_id)
    else:
        results = _inv_svc.list(
            filters={"purchase_return_id": purchase_return_id, "invoice_type": "Debit Memo"},
            limit=1,
        )
        dm = results[0] if results else None

    if not dm or (isinstance(dm, dict) and "error" in dm):
        return {
            "found": False,
            "purchase_return_id": purchase_return_id,
            "message": f"No debit memo found for Purchase Return (RMA) #{purchase_return_id}",
        }

    return {
        "found": True,
        "purchase_return_id": purchase_return_id,
        "debit_memo": dm,
        "debit_memo_id": dm.get("id"),
        "invoice_number": dm.get("invoice_number"),
        "supplier_id": dm.get("partner_id"),
        "total_amount": float(dm.get("total_amount", 0.0) or 0.0),
        "status": dm.get("status"),
        "issue_date": str(dm.get("issue_date")) if dm.get("issue_date") else None,
        "notes": dm.get("notes"),
        "message": (
            f"Debit Memo {dm.get('invoice_number') or '#' + str(dm.get('id'))} "
            f"found for RMA #{purchase_return_id} "
            f"(Total: ${float(dm.get('total_amount', 0.0) or 0.0):.2f}, "
            f"Status: {dm.get('status')})"
        ),
    }


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


def _generate_einvoice_xml(
    invoice_id: int,
    profile_id: Optional[int] = None,
    subtype: Optional[str] = None,
):
    xml_content = _einvoice_svc.generate_ubl_xml(
        invoice_id=invoice_id,
        profile_id=profile_id,
        subtype=subtype,
    )
    rec = _einvoice_svc.get_by_invoice_id(invoice_id)
    return {
        "invoice_id": invoice_id,
        "ubl_xml": xml_content,
        "invoice_uuid": rec.get("invoice_uuid") if rec else None,
        "invoice_hash": rec.get("invoice_hash") if rec else None,
        "qr_code_tlv": rec.get("qr_code_tlv") if rec else None,
        "clearance_status": rec.get("clearance_status") if rec else "Draft",
        "subtype": rec.get("subtype") if rec else subtype,
        "icv": rec.get("icv") if rec else None,
    }


def _sign_einvoice(
    invoice_id: int,
    profile_id: Optional[int] = None,
):
    return _einvoice_svc.sign_einvoice(
        invoice_id=invoice_id,
        profile_id=profile_id,
    )


def _submit_einvoice_clearance(
    invoice_id: int,
    profile_id: Optional[int] = None,
    environment: Optional[str] = None,
    auto_sign: bool = True,
):
    result = _einvoice_svc.submit_clearance(
        invoice_id=invoice_id,
        profile_id=profile_id,
        environment=environment,
        auto_sign=auto_sign,
    )
    if hasattr(result, "model_dump"):
        return result.model_dump()
    elif hasattr(result, "dict"):
        return result.dict()
    return result


def _get_einvoice_status(invoice_id: int):
    rec = _einvoice_svc.get_by_invoice_id(invoice_id=invoice_id)
    if rec:
        return rec
    return {
        "invoice_id": invoice_id,
        "clearance_status": "Not_Generated",
        "message": f"No e-invoice record found for invoice {invoice_id}",
    }


def _get_einvoice_qr_code(invoice_id: int):
    qr_res = _einvoice_svc.generate_qr_code(invoice_id=invoice_id)
    if hasattr(qr_res, "model_dump"):
        return qr_res.model_dump()
    elif hasattr(qr_res, "dict"):
        return qr_res.dict()
    return qr_res


def _get_fiscal_profile(profile_id: Optional[int] = None):
    return _einvoice_svc.get_active_fiscal_profile(profile_id=profile_id)


def _configure_fiscal_profile(
    profile_id: Optional[int] = None,
    profile_name: Optional[str] = "Main Fiscal Profile",
    authority_code: Optional[str] = "ZATCA",
    seller_name: Optional[str] = None,
    seller_name_ar: Optional[str] = None,
    tax_id: Optional[str] = None,
    commercial_registration_number: Optional[str] = None,
    building_number: Optional[str] = None,
    street_name: Optional[str] = None,
    street_name_ar: Optional[str] = None,
    district: Optional[str] = None,
    district_ar: Optional[str] = None,
    city: Optional[str] = None,
    city_ar: Optional[str] = None,
    postal_code: Optional[str] = None,
    country_code: Optional[str] = "SA",
    environment: Optional[str] = "Sandbox",
    api_base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    certificate: Optional[str] = None,
    private_key: Optional[str] = None,
    public_key: Optional[str] = None,
    is_default: Optional[bool] = True,
    is_active: Optional[bool] = True,
):
    payload = {}
    if profile_name is not None:
        payload["profile_name"] = profile_name
    if authority_code is not None:
        payload["authority_code"] = authority_code
    if seller_name is not None:
        payload["seller_name"] = seller_name
    if seller_name_ar is not None:
        payload["seller_name_ar"] = seller_name_ar
    if tax_id is not None:
        payload["tax_id"] = tax_id
    if commercial_registration_number is not None:
        payload["commercial_registration_number"] = commercial_registration_number
    if building_number is not None:
        payload["building_number"] = building_number
    if street_name is not None:
        payload["street_name"] = street_name
    if street_name_ar is not None:
        payload["street_name_ar"] = street_name_ar
    if district is not None:
        payload["district"] = district
    if district_ar is not None:
        payload["district_ar"] = district_ar
    if city is not None:
        payload["city"] = city
    if city_ar is not None:
        payload["city_ar"] = city_ar
    if postal_code is not None:
        payload["postal_code"] = postal_code
    if country_code is not None:
        payload["country_code"] = country_code
    if environment is not None:
        payload["environment"] = environment
    if api_base_url is not None:
        payload["api_base_url"] = api_base_url
    if api_key is not None:
        payload["api_key"] = api_key
    if api_secret is not None:
        payload["api_secret"] = api_secret
    if certificate is not None:
        payload["certificate"] = certificate
    if private_key is not None:
        payload["private_key"] = private_key
    if public_key is not None:
        payload["public_key"] = public_key
    if is_default is not None:
        payload["is_default"] = is_default
    if is_active is not None:
        payload["is_active"] = is_active

    if profile_id:
        _fiscal_profile_repo.update(profile_id, payload)
        return _fiscal_profile_repo.get(profile_id)
    else:
        if "seller_name" not in payload or not payload["seller_name"]:
            payload["seller_name"] = "Nova Global Trading LLC"
        if "tax_id" not in payload or not payload["tax_id"]:
            payload["tax_id"] = "300012345600003"
        return _fiscal_profile_repo.create(payload)


def _send_customer_reminder(
    customer_id: int,
    rule_id: Optional[int] = None,
    template_id: Optional[int] = None,
    channel: Optional[str] = None,
    custom_message: Optional[str] = None,
    attach_statement_pdf: bool = True,
    include_payment_link: bool = True,
):
    return _reminder_svc.send_customer_reminder(
        customer_id=customer_id,
        rule_id=rule_id,
        template_id=template_id,
        channel=channel,
        custom_message=custom_message,
        attach_statement_pdf=attach_statement_pdf,
        include_payment_link=include_payment_link,
    )


def _dispatch_customer_statement(
    customer_id: int,
    channel: Optional[str] = "EMAIL",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    as_of_date: Optional[str] = None,
    custom_message: Optional[str] = None,
):
    return _reminder_svc.dispatch_customer_statement(
        customer_id=customer_id,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        as_of_date=as_of_date,
        custom_message=custom_message,
    )


def _list_reminder_rules(
    is_active: Optional[bool] = None,
    trigger_type: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
):
    return _reminder_svc.list_rules(
        is_active=is_active,
        trigger_type=trigger_type,
        channel=channel,
        limit=limit,
    )


def _update_reminder_rule(
    id: int,
    rule_name: Optional[str] = None,
    trigger_type: Optional[str] = None,
    threshold_days: Optional[int] = None,
    channel: Optional[str] = None,
    min_overdue_balance: Optional[float] = None,
    template_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    exclude_vip: Optional[bool] = None,
    schedule_day: Optional[str] = None,
):
    update_data = {
        k: v for k, v in {
            "rule_name": rule_name,
            "trigger_type": trigger_type,
            "threshold_days": threshold_days,
            "channel": channel,
            "min_overdue_balance": min_overdue_balance,
            "template_id": template_id,
            "is_active": is_active,
            "exclude_vip": exclude_vip,
            "schedule_day": schedule_day,
        }.items() if v is not None
    }
    return _reminder_svc.update_rule(rule_id=id, data=update_data)


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
                    "invoice_type": {"type": "string", "description": "Filter by invoice type (Sales, Purchase, Debit Memo)"},
                    "payment_term_id": {"type": "integer", "description": "Filter by payment term ID"},
                    "purchase_return_id": {"type": "integer", "description": "Filter by linked Purchase Return (RMA) ID"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_invoices,
    )
    register_tool(
        Tool(
            name="list_debit_memos",
            description="List supplier debit memos (T0090 with invoice_type='Debit Memo') linked to vendor returns (RMA) or supplier credit adjustments",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "purchase_return_id": {"type": "integer", "description": "Filter by linked Purchase Return (RMA) ID"},
                    "partner_id": {"type": "integer", "description": "Filter by supplier/partner ID"},
                    "status": {"type": "string", "description": "Filter by debit memo status (Draft, Approved, Applied, Paid, Cancelled)"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                    "offset": {"type": "integer", "description": "Offset for pagination (default 0)"},
                },
            },
        ),
        _list_debit_memos,
    )
    register_tool(
        Tool(
            name="get_debit_memo_for_rma",
            description="Get the supplier debit memo record and credit amount linked to a specific Purchase Return (RMA) ID",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "purchase_return_id": {"type": "integer", "description": "Purchase Return (RMA) ID"},
                },
                "required": ["purchase_return_id"],
            },
        ),
        _get_debit_memo_for_rma,
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
    register_tool(
        Tool(
            name="generate_einvoice_xml",
            description="Generate OASIS UBL 2.1 XML e-invoice document (Standard B2B or Simplified B2C) for a sales invoice",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Sales invoice ID (T0090)"},
                    "profile_id": {"type": "integer", "description": "Optional fiscal profile ID (T0130)"},
                    "subtype": {"type": "string", "description": "Invoice subtype code ('0100000' for Standard B2B, '0200000' for Simplified B2C)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _generate_einvoice_xml,
    )
    register_tool(
        Tool(
            name="sign_einvoice",
            description="Cryptographically sign an e-invoice with ECDSA/RSA private key, compute SHA-256 canonical hash, and embed signature into UBL XML",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Sales invoice ID (T0090)"},
                    "profile_id": {"type": "integer", "description": "Optional fiscal profile ID (T0130)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _sign_einvoice,
    )
    register_tool(
        Tool(
            name="submit_einvoice_clearance",
            description="Submit an e-invoice to government fiscal authority (e.g. ZATCA) for B2B clearance or B2C reporting",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Sales invoice ID (T0090)"},
                    "profile_id": {"type": "integer", "description": "Optional fiscal profile ID (T0130)"},
                    "environment": {"type": "string", "description": "Gateway environment ('Sandbox', 'Simulation', 'Production')"},
                    "auto_sign": {"type": "boolean", "description": "Automatically sign the document before submission if not yet signed (default true)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _submit_einvoice_clearance,
    )
    register_tool(
        Tool(
            name="get_einvoice_status",
            description="Retrieve e-invoice fiscal clearance status, clearance UUID, cryptographic hash, and validation outcomes",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Sales invoice ID (T0090)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _get_einvoice_status,
    )
    register_tool(
        Tool(
            name="get_einvoice_qr_code",
            description="Generate or fetch Base64 Tag-Length-Value (TLV) QR code payload compliant with national tax authority standards (e.g. ZATCA)",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "integer", "description": "Sales invoice ID (T0090)"},
                },
                "required": ["invoice_id"],
            },
        ),
        _get_einvoice_qr_code,
    )
    register_tool(
        Tool(
            name="get_fiscal_profile",
            description="Get the active fiscal authority configuration profile (seller legal details, tax ID, CSID/certificate, environment)",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Optional profile ID. If omitted, returns active/default profile."},
                },
            },
        ),
        _get_fiscal_profile,
    )
    register_tool(
        Tool(
            name="configure_fiscal_profile",
            description="Create or update fiscal authority integration profile and tax credentials (ZATCA / PEPPOL / European e-Invoicing)",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Optional profile ID to update an existing profile"},
                    "profile_name": {"type": "string", "description": "Descriptive name for the fiscal profile"},
                    "authority_code": {"type": "string", "description": "Authority code ('ZATCA', 'PEPPOL', etc.)"},
                    "seller_name": {"type": "string", "description": "Official legal seller name in English/Latin"},
                    "seller_name_ar": {"type": "string", "description": "Official legal seller name in Arabic"},
                    "tax_id": {"type": "string", "description": "VAT / Tax registration ID"},
                    "commercial_registration_number": {"type": "string", "description": "CR number"},
                    "building_number": {"type": "string", "description": "Building / unit number"},
                    "street_name": {"type": "string", "description": "Street name"},
                    "district": {"type": "string", "description": "District / neighborhood"},
                    "city": {"type": "string", "description": "City"},
                    "postal_code": {"type": "string", "description": "Postal code"},
                    "country_code": {"type": "string", "description": "ISO 2-letter country code (default 'SA')"},
                    "environment": {"type": "string", "description": "Environment ('Sandbox', 'Simulation', 'Production')"},
                    "api_base_url": {"type": "string", "description": "Authority API base URL"},
                    "api_key": {"type": "string", "description": "API key / client ID"},
                    "api_secret": {"type": "string", "description": "API secret"},
                    "certificate": {"type": "string", "description": "X.509 security certificate PEM"},
                    "private_key": {"type": "string", "description": "Private key PEM"},
                    "public_key": {"type": "string", "description": "Public key PEM"},
                    "is_default": {"type": "boolean", "description": "Set as default profile"},
                    "is_active": {"type": "boolean", "description": "Whether profile is active"},
                },
            },
        ),
        _configure_fiscal_profile,
    )
    register_tool(
        Tool(
            name="send_customer_reminder",
            description="Send an on-demand or automated AR collection reminder to a customer via email or WhatsApp",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID (T0010)"},
                    "rule_id": {"type": "integer", "description": "Optional reminder rule ID (T0120)"},
                    "template_id": {"type": "integer", "description": "Optional message template ID (T0121)"},
                    "channel": {"type": "string", "description": "Communication channel override ('EMAIL', 'WHATSAPP')"},
                    "custom_message": {"type": "string", "description": "Optional custom note/message prepended to reminder"},
                    "attach_statement_pdf": {"type": "boolean", "description": "Whether to attach generated PDF account statement (default True)"},
                    "include_payment_link": {"type": "boolean", "description": "Whether to generate and include payment link in message (default True)"},
                },
                "required": ["customer_id"],
            },
        ),
        _send_customer_reminder,
    )
    register_tool(
        Tool(
            name="dispatch_customer_statement",
            description="Generate and dispatch a branded PDF customer account statement with aging summary and open invoices via Email or WhatsApp",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID (T0010)"},
                    "channel": {"type": "string", "description": "Target dispatch channel ('EMAIL' or 'WHATSAPP', default 'EMAIL')"},
                    "start_date": {"type": "string", "description": "Statement start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "Statement end date (YYYY-MM-DD)"},
                    "as_of_date": {"type": "string", "description": "As-of calculation date (YYYY-MM-DD, defaults to today)"},
                    "custom_message": {"type": "string", "description": "Optional custom message note included in statement"},
                },
                "required": ["customer_id"],
            },
        ),
        _dispatch_customer_statement,
    )
    register_tool(
        Tool(
            name="list_reminder_rules",
            description="List AR collection reminder rules, schedules, and aging threshold triggers",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "is_active": {"type": "boolean", "description": "Filter by active status"},
                    "trigger_type": {"type": "string", "description": "Filter by trigger type (AGING_THRESHOLD, STATEMENT_SCHEDULE, DUE_DATE_OFFSET)"},
                    "channel": {"type": "string", "description": "Filter by channel (EMAIL, WHATSAPP, ALL)"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
            },
        ),
        _list_reminder_rules,
    )
    register_tool(
        Tool(
            name="update_reminder_rule",
            description="Update an AR collection reminder rule configuration, threshold days, channel, active state, or VIP exclusion policy",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Reminder rule ID (T0120)"},
                    "rule_name": {"type": "string", "description": "Name of the reminder rule"},
                    "trigger_type": {"type": "string", "description": "Trigger type (AGING_THRESHOLD, STATEMENT_SCHEDULE, DUE_DATE_OFFSET)"},
                    "threshold_days": {"type": "integer", "description": "Overdue aging threshold in days (e.g. 30, 60, 90)"},
                    "channel": {"type": "string", "description": "Target delivery channel (EMAIL, WHATSAPP, ALL)"},
                    "min_overdue_balance": {"type": "number", "description": "Minimum overdue amount to trigger reminder"},
                    "template_id": {"type": "integer", "description": "Associated message template ID"},
                    "is_active": {"type": "boolean", "description": "Whether rule is active"},
                    "exclude_vip": {"type": "boolean", "description": "Whether to exclude VIP customer accounts"},
                    "schedule_day": {"type": "string", "description": "Weekly schedule day (e.g. Friday)"},
                },
                "required": ["id"],
            },
        ),
        _update_reminder_rule,
    )
    register_resource(
        Resource(uri="nova://accounting/payment-terms", name="Payment Terms", description="List of all payment terms"),
        _list_terms,
    )
    register_resource(
        Resource(uri="nova://accounting/invoices", name="All Invoices", description="List of all invoices"),
        _list_invoices,
    )
    register_resource(
        Resource(uri="nova://accounting/debit-memos", name="Supplier Debit Memos", description="List of all supplier debit memos"),
        _list_debit_memos,
    )
    register_resource(
        Resource(uri="nova://accounting/fiscal-profiles", name="Fiscal Profiles", description="List of all fiscal authority profiles"),
        _fiscal_profile_repo.list,
    )
    register_resource(
        Resource(uri="nova://accounting/einvoices", name="All E-Invoices", description="List of all e-invoice records"),
        _einvoice_repo.list,
    )


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="accounting-mcp", version="1.0"))


if __name__ == "__main__":
    main()


"""Nova ERP — MCP Integrations Server for B2B EDI Gateway & Supplier Catalog Sync.

Exposes AI tools for natural language EDI operations:
- list_edi_partners (Tier 1): List trading partners with optional filters.
- get_edi_partner (Tier 1): Get trading partner details by ID or code.
- ingest_edi_document (Tier 1): Ingest and process inbound EDI document (850/832/ORDERS/PRICAT).
- list_edi_transactions (Tier 1): List EDI transaction logs with filtering.
- get_edi_transaction (Tier 1): Inspect transaction log with raw payload, parsed JSON, and ACK.
- reprocess_edi_transaction (Tier 1): Reprocess transaction held for price/SKU discrepancy.
- generate_edi_asn (Tier 1): Generate Outbound EDI 856 ASN / DESADV for delivery.
- transmit_edi_invoice (Tier 2 - Propose/Confirm): Transmit Outbound EDI 810 / INVOIC.
- sync_supplier_catalog (Tier 1): Sync supermarket catalog items (832/PRICAT) and update matrix.
"""

from typing import Any, Dict, List, Optional, Union
import logging

from modules.core.context import get_current_tenant
from modules.core.services.base import CrudService
from modules.integrations.models.edi import (
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_TRANSACTION_REPO,
    EDI_SSCC_PALLET_REPO,
    EDI_CATALOG_ITEM_REPO,
    EdiInvoiceTransmitRequest,
)
from modules.integrations.services.edi import (
    edi_850_service as default_edi_850_svc,
    edi_856_service as default_edi_856_svc,
    edi_810_service as default_edi_810_svc,
    edi_catalog_service as default_edi_catalog_svc,
    cross_reference_service as default_cross_reference_svc,
    sscc_service as default_sscc_svc,
)
from packages.mcp.registry import register_tool, register_resource, get_current_user
from packages.mcp.types import Tool, Resource

logger = logging.getLogger(__name__)

# Service instances (can be patched in tests)
_partner_svc = CrudService(EDI_PARTNER_REPO)
_transaction_svc = CrudService(EDI_TRANSACTION_REPO)
_sku_mapping_svc = CrudService(EDI_SKU_MAPPING_REPO)
_sscc_pallet_svc = CrudService(EDI_SSCC_PALLET_REPO)
_catalog_item_svc = CrudService(EDI_CATALOG_ITEM_REPO)

_edi_850_svc = default_edi_850_svc
_edi_856_svc = default_edi_856_svc
_edi_810_svc = default_edi_810_svc
_edi_catalog_svc = default_edi_catalog_svc
_cross_reference_svc = default_cross_reference_svc
_sscc_svc = default_sscc_svc


def _get_active_tenant_id() -> Optional[int]:
    """Resolve active tenant ID from MCP user context or contextvars."""
    current_user = get_current_user()
    tenant_id = None
    if isinstance(current_user, dict):
        tenant_id = current_user.get("business_id")
        if tenant_id is None:
            tenant_id = current_user.get("tenant_id")
    if tenant_id is None:
        tenant_id = get_current_tenant()
    return tenant_id


def register_tools() -> None:
    """Register all MCP tools and resources for B2B EDI Gateway & Integrations."""
    register_tool(
        Tool(
            name="list_edi_partners",
            description="List B2B EDI trading partners with optional filtering by active status, EDI standard, and communication method",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "is_active": {
                        "type": "boolean",
                        "description": "Filter by active status (true/false)",
                    },
                    "standard": {
                        "type": "string",
                        "description": "Filter by EDI standard (ANSI_X12 or EDIFACT)",
                        "enum": ["ANSI_X12", "EDIFACT"],
                    },
                    "communication_method": {
                        "type": "string",
                        "description": "Filter by communication method (MANUAL, API, AS2, SFTP)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of partners to return (default: 50)",
                    },
                },
            },
        ),
        _list_edi_partners,
    )

    register_tool(
        Tool(
            name="get_edi_partner",
            description="Get detailed profile and configuration for an EDI trading partner by ID or unique partner code",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Trading partner database ID (T0134)",
                    },
                    "partner_code": {
                        "type": "string",
                        "description": "Unique trading partner code (e.g. CRF-UAE, LULU-HQ)",
                    },
                },
            },
        ),
        _get_edi_partner,
    )

    register_tool(
        Tool(
            name="ingest_edi_document",
            description="Ingest and process an inbound raw EDI document (ANSI X12 850 PO / 832 Catalog or UN/EDIFACT ORDERS / PRICAT), cross-referencing SKUs and prices, validating credit limits, creating sales orders or catalog items, and generating functional acknowledgment (997 FA or CONTRL)",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "raw_payload": {
                        "type": "string",
                        "description": "Raw unparsed EDI interchange message text (ISA...IEA or UNB...UNZ)",
                    },
                    "partner_id": {
                        "type": "integer",
                        "description": "Optional trading partner ID override (if omitted, auto-detected from envelope headers)",
                    },
                    "standard": {
                        "type": "string",
                        "description": "Optional standard override: ANSI_X12 or EDIFACT",
                        "enum": ["ANSI_X12", "EDIFACT"],
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Optional document type (850, ORDERS, 832, PRICAT)",
                    },
                    "auto_confirm": {
                        "type": "boolean",
                        "description": "Optional override for partner auto_confirm setting",
                    },
                },
                "required": ["raw_payload"],
            },
        ),
        _ingest_edi_document,
    )

    register_tool(
        Tool(
            name="list_edi_transactions",
            description="List EDI transaction / interchange audit logs with optional filtering by partner, status, document type, and direction",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "partner_id": {
                        "type": "integer",
                        "description": "Filter by trading partner ID",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (PENDING, PROCESSED, FAILED, PRICE_DISCREPANCY_HOLD, ACKNOWLEDGED)",
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Filter by document type (850, 856, 810, 832, 997, ORDERS, DESADV, INVOIC, PRICAT, CONTRL)",
                    },
                    "direction": {
                        "type": "string",
                        "description": "Filter by direction: INBOUND or OUTBOUND",
                        "enum": ["INBOUND", "OUTBOUND"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return (default: 50)",
                    },
                },
            },
        ),
        _list_edi_transactions,
    )

    register_tool(
        Tool(
            name="get_edi_transaction",
            description="Get detailed EDI transaction log by ID including raw interchange payload, parsed structured JSON, acknowledgment message, and error details",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "EDI transaction log ID (T0136)",
                    },
                },
                "required": ["id"],
            },
        ),
        _get_edi_transaction,
    )

    register_tool(
        Tool(
            name="reprocess_edi_transaction",
            description="Reprocess an EDI transaction held for price discrepancies or missing SKU mappings, with optional force confirmation or price tolerance override",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "EDI transaction ID to reprocess",
                    },
                    "transaction_id": {
                        "type": "integer",
                        "description": "Alternative parameter for transaction ID",
                    },
                    "force_confirm": {
                        "type": "boolean",
                        "description": "Force confirm the sales order even if price discrepancies exist (default: false)",
                    },
                    "override_price_tolerance": {
                        "type": "number",
                        "description": "Custom price tolerance percent for this reprocessing run",
                    },
                },
            },
        ),
        _reprocess_edi_transaction,
    )

    register_tool(
        Tool(
            name="generate_edi_asn",
            description="Generate and transmit Outbound EDI 856 (Advance Shipping Notice / ASN) or UN/EDIFACT DESADV for a delivery dispatch with SSCC-18 pallet hierarchy and lot tracking",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "delivery_id": {
                        "type": "integer",
                        "description": "Nova delivery shipment ID (T0077/T0016)",
                    },
                    "partner_id": {
                        "type": "integer",
                        "description": "Optional trading partner ID override (defaults to partner linked to delivery customer)",
                    },
                    "carrier_name": {
                        "type": "string",
                        "description": "Carrier name or SCAC code (e.g. DHL, FEDEX, Nova Fleet)",
                    },
                    "tracking_number": {
                        "type": "string",
                        "description": "Bill of lading or consignment tracking number",
                    },
                    "vehicle_number": {
                        "type": "string",
                        "description": "Truck license plate or vehicle number",
                    },
                    "seal_number": {
                        "type": "string",
                        "description": "Container seal number",
                    },
                },
                "required": ["delivery_id"],
            },
        ),
        _generate_edi_asn,
    )

    register_tool(
        Tool(
            name="transmit_edi_invoice",
            description="Generate and transmit Outbound EDI 810 (Sales Invoice) or UN/EDIFACT INVOIC electronic tax invoice matching delivered goods, tax breakdowns, and buyer PO number. [REQUIRES CONFIRMATION]",
            tier="tier2",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {
                        "type": "integer",
                        "description": "Nova sales invoice ID (T0090/T0026)",
                    },
                    "delivery_id": {
                        "type": "integer",
                        "description": "Optional linked delivery ID",
                    },
                    "partner_id": {
                        "type": "integer",
                        "description": "Optional trading partner ID override",
                    },
                },
                "required": ["invoice_id"],
            },
        ),
        _transmit_edi_invoice,
    )

    register_tool(
        Tool(
            name="sync_supplier_catalog",
            description="Synchronize supermarket / retail partner catalog items in T0138, detect price changes, and upsert SKU cross-reference matrix (T0135)",
            tier="tier1",
            input_schema={
                "type": "object",
                "properties": {
                    "partner_id": {
                        "type": "integer",
                        "description": "Trading partner ID (T0134)",
                    },
                    "catalog_code": {
                        "type": "string",
                        "description": "Catalog batch or version code (e.g. CAT-2026-Q3)",
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of catalog item dictionaries (buyer_sku, product_name, list_price, gtin, uom, pack_size, etc.)",
                    },
                    "auto_match_skus": {
                        "type": "boolean",
                        "description": "Whether to auto-match items to Nova products by GTIN/SKU (default: true)",
                    },
                },
                "required": ["partner_id", "catalog_code", "items"],
            },
        ),
        _sync_supplier_catalog,
    )

    register_resource(
        Resource(
            uri="nova://integrations/edi/partners",
            name="EDI Trading Partners",
            description="List of active B2B EDI trading partners configured in Nova ERP",
        ),
        _resource_list_partners,
    )

    register_resource(
        Resource(
            uri="nova://integrations/edi/transactions",
            name="EDI Transaction Logs",
            description="List of recent EDI document interchange transactions and statuses",
        ),
        _resource_list_transactions,
    )


# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------

def _list_edi_partners(
    is_active: Optional[bool] = None,
    standard: Optional[str] = None,
    communication_method: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Handler for list_edi_partners tool."""
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if standard:
        filters["edi_standard"] = standard
    if communication_method:
        filters["communication_method"] = communication_method

    return _partner_svc.list(filters=filters or None, limit=limit)


def _get_edi_partner(
    id: Optional[int] = None,
    partner_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Handler for get_edi_partner tool."""
    partner = None
    if id is not None:
        partner = _partner_svc.get(id)
    elif partner_code:
        partners = _partner_svc.list(filters={"partner_code": partner_code}, limit=1)
        if partners:
            partner = partners[0]

    if not partner:
        ident = id if id is not None else partner_code
        raise ValueError(f"EDI Trading Partner '{ident}' not found")

    # Enrich with SKU mapping count and recent transaction count
    partner_id = partner.get("id")
    if partner_id:
        try:
            mappings = _sku_mapping_svc.list(filters={"partner_id": partner_id}, limit=1000)
            partner["sku_mappings_count"] = len(mappings)
        except Exception:
            partner["sku_mappings_count"] = 0

    return partner


def _ingest_edi_document(
    raw_payload: str,
    partner_id: Optional[int] = None,
    standard: Optional[str] = None,
    document_type: Optional[str] = None,
    auto_confirm: Optional[bool] = None,
) -> Dict[str, Any]:
    """Handler for ingest_edi_document tool."""
    cleaned_payload = raw_payload.strip() if raw_payload else ""
    if not cleaned_payload:
        raise ValueError("EDI raw_payload cannot be empty")

    doc_type = document_type.upper() if document_type else ""

    # Route catalog documents (832 / PRICAT) to catalog service
    if doc_type in ("832", "PRICAT") or "PRICAT" in cleaned_payload or "BCT*" in cleaned_payload:
        res = _edi_catalog_svc.ingest_inbound_catalog(
            raw_payload=cleaned_payload,
            partner_id=partner_id,
            standard=standard,
        )
        return {
            "transaction_id": res.transaction_id,
            "transaction_number": f"TXN-832-{res.catalog_code}",
            "status": res.sync_status,
            "standard": standard or ("EDIFACT" if "UNB" in cleaned_payload else "ANSI_X12"),
            "document_type": "PRICAT" if "UNB" in cleaned_payload else "832",
            "partner_id": res.partner_id,
            "ack_generated": True,
            "errors": res.errors,
            "total_items": res.total_items,
            "matched_items": res.matched_items,
        }

    # Standard Inbound Purchase Order (850 / ORDERS)
    res = _edi_850_svc.ingest_inbound_order(
        raw_payload=cleaned_payload,
        partner_id=partner_id,
        standard=standard,
        document_type=document_type or "850",
        auto_confirm=auto_confirm,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _list_edi_transactions(
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Handler for list_edi_transactions tool."""
    filters = {}
    if partner_id is not None:
        filters["partner_id"] = partner_id
    if status:
        filters["status"] = status
    if document_type:
        filters["document_type"] = document_type
    if direction:
        filters["direction"] = direction

    return _transaction_svc.list(filters=filters or None, limit=limit)


def _get_edi_transaction(id: int) -> Dict[str, Any]:
    """Handler for get_edi_transaction tool."""
    tx = _transaction_svc.get(id)
    if not tx:
        raise ValueError(f"EDI Transaction #{id} not found")
    return tx


def _reprocess_edi_transaction(
    id: Optional[int] = None,
    transaction_id: Optional[int] = None,
    force_confirm: bool = False,
    override_price_tolerance: Optional[float] = None,
) -> Dict[str, Any]:
    """Handler for reprocess_edi_transaction tool."""
    target_id = id if id is not None else transaction_id
    if target_id is None:
        raise ValueError("Transaction id must be provided")

    res = _edi_850_svc.reprocess_transaction(
        transaction_id=target_id,
        force_confirm=force_confirm,
        override_price_tolerance=override_price_tolerance,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _generate_edi_asn(
    delivery_id: int,
    partner_id: Optional[int] = None,
    carrier_name: Optional[str] = None,
    tracking_number: Optional[str] = None,
    vehicle_number: Optional[str] = None,
    seal_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Handler for generate_edi_asn tool."""
    res = _edi_856_svc.generate_asn_for_delivery(
        delivery_id=delivery_id,
        partner_id=partner_id,
        carrier_name=carrier_name,
        tracking_number=tracking_number,
        vehicle_number=vehicle_number,
        seal_number=seal_number,
        auto_generate_sscc=True,
    )
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _transmit_edi_invoice(
    invoice_id: int,
    delivery_id: Optional[int] = None,
    partner_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Handler for transmit_edi_invoice tool (Tier 2 - Propose/Confirm)."""
    req = EdiInvoiceTransmitRequest(
        invoice_id=invoice_id,
        delivery_id=delivery_id,
        partner_id=partner_id,
    )
    res = _edi_810_svc.transmit_invoice(req)
    if hasattr(res, "model_dump"):
        return res.model_dump()
    return res if isinstance(res, dict) else dict(res)


def _sync_supplier_catalog(
    partner_id: int,
    catalog_code: str,
    items: List[Dict[str, Any]],
    auto_match_skus: bool = True,
) -> Dict[str, Any]:
    """Handler for sync_supplier_catalog tool."""
    sync_res = _edi_catalog_svc.sync_catalog(
        partner_id=partner_id,
        catalog_code=catalog_code,
        items=items,
        auto_match_skus=auto_match_skus,
    )
    if hasattr(sync_res, "model_dump"):
        return sync_res.model_dump()
    return {
        "partner_id": sync_res.partner_id,
        "catalog_code": sync_res.catalog_code,
        "total_items": sync_res.total_items,
        "matched_items": sync_res.matched_items,
        "unmatched_items": sync_res.unmatched_items,
        "price_updated_items": sync_res.price_updated_items,
        "sync_status": sync_res.sync_status,
    }


# ---------------------------------------------------------------------------
# Resources Handlers
# ---------------------------------------------------------------------------

def _resource_list_partners() -> List[Dict[str, Any]]:
    """Resource handler for nova://integrations/edi/partners."""
    return _partner_svc.list(filters={"is_active": True}, limit=100)


def _resource_list_transactions() -> List[Dict[str, Any]]:
    """Resource handler for nova://integrations/edi/transactions."""
    return _transaction_svc.list(limit=50)


# ---------------------------------------------------------------------------
# Stdio Server Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run integrations MCP server in stdio mode."""
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio

    server = McpServer(name="integrations-mcp", version="1.0")
    run_stdio(server)


if __name__ == "__main__":
    main()

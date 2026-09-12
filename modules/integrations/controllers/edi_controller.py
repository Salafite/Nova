"""
Nova ERP — B2B EDI Gateway & Supplier Catalog Sync REST API Controller
Exposes endpoints for:
- Inbound EDI document ingestion (850 PO / ORDERS, 832 / PRICAT)
- File upload & Webhook ingestion
- Transaction reprocessing & error remediation
- Raw payload & ACK inspection
- Outbound EDI 856 (ASN / DESADV) generation
- Outbound EDI 810 (Invoice / INVOIC) transmission
- Supplier Catalog sync & export
- SKU cross-referencing & bulk mapping import
- GS1-128 / SSCC-18 pallet logistics label generation
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, status
from fastapi.responses import PlainTextResponse

from packages.auth.deps import get_current_user
from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.integrations.models.edi import (
    EdiIngestRequest,
    EdiIngestResult,
    EdiReprocessRequest,
    EdiAsnGenerateRequest,
    EdiAsnGenerateResponse,
    EdiInvoiceTransmitRequest,
    EdiInvoiceTransmitResponse,
    EdiCatalogSyncRequest,
    EdiCatalogSyncResponse,
    EDI_PARTNER_REPO,
    EDI_TRANSACTION_REPO,
    EDI_SSCC_PALLET_REPO,
)
from modules.integrations.services.edi import (
    detect_edi_standard,
    edi_850_service,
    edi_856_service,
    edi_810_service,
    edi_catalog_service,
    cross_reference_service,
    sscc_service,
    generate_sscc18,
    format_gs1_logistics_label,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/edi",
    tags=["B2B EDI Gateway & Integrations"],
)


# ---------------------------------------------------------------------------
# 1. Inbound Ingestion & Upload Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=EdiIngestResult)
def ingest_edi_document(
    request: EdiIngestRequest,
    user: dict = Depends(get_current_user),
):
    """
    Ingest and process an inbound EDI document (ANSI X12 850/832 or UN/EDIFACT ORDERS/PRICAT).
    Automatically matches trading partner, resolves SKU mappings, validates pricing against contracts,
    creates Nova sales orders (T0012/T0013) or catalog items (T0138), and generates functional ACK (997/CONTRL).
    """
    raw_payload = request.raw_payload.strip() if request.raw_payload else ""
    if not raw_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EDI payload cannot be empty",
        )

    doc_type = request.document_type.upper() if request.document_type else ""

    # Route catalog documents (832 / PRICAT) to catalog service
    if doc_type in ("832", "PRICAT") or "PRICAT" in raw_payload or "BCT*" in raw_payload:
        try:
            cat_res = edi_catalog_service.ingest_inbound_catalog(
                raw_payload=raw_payload,
                partner_id=request.partner_id,
                standard=request.standard,
            )
            return EdiIngestResult(
                transaction_id=cat_res.transaction_id,
                transaction_number=f"TXN-832-{cat_res.catalog_code}",
                status=cat_res.sync_status,
                standard=request.standard or "EDIFACT" if "UNB" in raw_payload else "ANSI_X12",
                document_type="PRICAT" if "UNB" in raw_payload else "832",
                partner_id=cat_res.partner_id,
                ack_generated=True,
                errors=cat_res.errors,
            )
        except Exception as e:
            logger.error(f"Catalog ingestion failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Catalog ingestion error: {str(e)}",
            )

    # Standard Inbound Purchase Order (850 / ORDERS)
    try:
        result = edi_850_service.ingest_inbound_order(
            raw_payload=raw_payload,
            partner_id=request.partner_id,
            standard=request.standard,
            document_type=request.document_type or "850",
            auto_confirm=request.auto_confirm,
        )
        return result
    except Exception as e:
        logger.error(f"Inbound EDI ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Inbound EDI processing error: {str(e)}",
        )


@router.post("/upload", response_model=EdiIngestResult)
async def upload_edi_file(
    file: UploadFile = File(...),
    partner_id: Optional[int] = Form(None),
    auto_confirm: Optional[bool] = Form(None),
    standard: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """
    Upload and process an EDI document file (.edi, .x12, .txt).
    """
    try:
        content_bytes = await file.read()
        raw_text = content_bytes.decode("utf-8", errors="replace").strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    req = EdiIngestRequest(
        partner_id=partner_id,
        raw_payload=raw_text,
        standard=standard,
        document_type=document_type,
        auto_confirm=auto_confirm,
    )
    return ingest_edi_document(req, user=user)


@router.post("/webhook")
@router.post("/webhook/{partner_code}")
async def edi_webhook_ingest(
    request: Request,
    partner_code: Optional[str] = None,
):
    """
    Webhook endpoint for automated AS2 / SFTP / HTTP push document ingestion from trading partners.
    """
    # 1. Read raw body or JSON
    raw_payload = ""
    std_override = None
    doc_type_override = None
    partner_id_override = None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body_json = await request.json()
            raw_payload = body_json.get("raw_payload", "")
            std_override = body_json.get("standard")
            doc_type_override = body_json.get("document_type")
            partner_id_override = body_json.get("partner_id")
        except Exception:
            pass
    else:
        body_bytes = await request.body()
        raw_payload = body_bytes.decode("utf-8", errors="replace").strip()

    if not raw_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook EDI payload received",
        )

    # 2. Resolve partner by code if provided
    if partner_code and not partner_id_override:
        partners = EDI_PARTNER_REPO.list(filters={"partner_code": partner_code, "is_active": True}, limit=1)
        if partners:
            partner_id_override = partners[0]["id"]

    try:
        result = edi_850_service.ingest_inbound_order(
            raw_payload=raw_payload,
            partner_id=partner_id_override,
            standard=std_override,
            document_type=doc_type_override or "850",
        )
        return {
            "ok": True,
            "status": result.status,
            "transaction_id": result.transaction_id,
            "transaction_number": result.transaction_number,
            "sales_order_number": result.sales_order_number,
            "ack_payload": result.ack_payload,
            "errors": result.errors,
        }
    except Exception as e:
        logger.error(f"Webhook EDI processing error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# 2. Transaction Management & Reprocessing
# ---------------------------------------------------------------------------

@router.post("/reprocess", response_model=EdiIngestResult)
@router.post("/transactions/{id}/reprocess", response_model=EdiIngestResult)
def reprocess_edi_transaction(
    id: Optional[int] = None,
    payload: Optional[EdiReprocessRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Reprocess an EDI transaction held for price discrepancies or missing SKU mappings.
    Allows passing force_confirm=True or override_price_tolerance.
    """
    target_id = id or (payload.transaction_id if payload else None)
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction ID is required",
        )

    force_confirm = payload.force_confirm if payload else False
    price_tol = payload.override_price_tolerance if payload else None

    try:
        result = edi_850_service.reprocess_transaction(
            transaction_id=target_id,
            force_confirm=force_confirm,
            override_price_tolerance=price_tol,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Reprocess transaction #{target_id} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Reprocess failure: {str(e)}",
        )


@router.get("/transactions/{id}/raw")
def get_transaction_raw_payload(
    id: int,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve raw EDI interchange payload for an EDI transaction (T0136).
    """
    tx = EDI_TRANSACTION_REPO.get(id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction #{id} not found")

    return {
        "id": tx.get("id"),
        "transaction_number": tx.get("transaction_number"),
        "standard": tx.get("standard"),
        "document_type": tx.get("document_type"),
        "direction": tx.get("direction"),
        "status": tx.get("status"),
        "raw_payload": tx.get("raw_payload"),
        "parsed_data": tx.get("parsed_data"),
    }


@router.get("/transactions/{id}/ack")
def get_transaction_ack_payload(
    id: int,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve generated or received 997 Functional Acknowledgment / CONTRL message.
    """
    tx = EDI_TRANSACTION_REPO.get(id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction #{id} not found")

    return {
        "id": tx.get("id"),
        "transaction_number": tx.get("transaction_number"),
        "ack_status": tx.get("ack_status"),
        "ack_payload": tx.get("ack_payload"),
        "error_details": tx.get("error_details"),
    }


# ---------------------------------------------------------------------------
# 3. Outbound EDI 856 (ASN) & EDI 810 (Invoice) Automation
# ---------------------------------------------------------------------------

@router.post("/asn/generate", response_model=EdiAsnGenerateResponse)
def generate_edi_asn(
    payload: EdiAsnGenerateRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate and transmit an Outbound EDI 856 (Advance Shipping Notice) or UN/EDIFACT DESADV
    with SSCC-18 pallet hierarchy, pick batches, and carrier dispatch details.
    """
    try:
        response = edi_856_service.generate_asn_for_delivery(
            delivery_id=payload.delivery_id,
            partner_id=payload.partner_id,
            carrier_name=payload.carrier_name,
            tracking_number=payload.tracking_number,
            vehicle_number=payload.vehicle_number,
            seal_number=payload.seal_number,
            auto_generate_sscc=True,
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"ASN generation failed for delivery #{payload.delivery_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ASN generation failed: {str(e)}",
        )


@router.post("/asn/{delivery_id}", response_model=EdiAsnGenerateResponse)
def generate_edi_asn_by_delivery(
    delivery_id: int,
    payload: Optional[EdiAsnGenerateRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Generate ASN for a specific delivery shipment ID.
    """
    req = payload or EdiAsnGenerateRequest(delivery_id=delivery_id)
    req.delivery_id = delivery_id
    return generate_edi_asn(payload=req, user=user)


@router.post("/invoice/transmit", response_model=EdiInvoiceTransmitResponse)
def transmit_edi_invoice(
    payload: EdiInvoiceTransmitRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate and transmit an Outbound EDI 810 (Sales Invoice) or UN/EDIFACT INVOIC
    matching delivered line items, tax breakdowns, discounts, and buyer purchase orders.
    """
    try:
        response = edi_810_service.transmit_invoice(payload)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"EDI Invoice transmission failed for invoice #{payload.invoice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invoice transmission failed: {str(e)}",
        )


@router.post("/invoice/{invoice_id}", response_model=EdiInvoiceTransmitResponse)
def transmit_edi_invoice_by_id(
    invoice_id: int,
    payload: Optional[EdiInvoiceTransmitRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Transmit EDI invoice for a specific invoice ID.
    """
    req = payload or EdiInvoiceTransmitRequest(invoice_id=invoice_id)
    req.invoice_id = invoice_id
    return transmit_edi_invoice(payload=req, user=user)


# ---------------------------------------------------------------------------
# 4. Supplier Catalog Sync (832 / PRICAT) & Export
# ---------------------------------------------------------------------------

@router.post("/catalog/sync", response_model=EdiCatalogSyncResponse)
def sync_supplier_catalog_endpoint(
    request: EdiCatalogSyncRequest,
    user: dict = Depends(get_current_user),
):
    """
    Synchronize supermarket catalog items (T0138), detect price changes, and upsert SKU cross-reference matrix (T0135).
    """
    try:
        sync_res = edi_catalog_service.sync_catalog(
            partner_id=request.partner_id,
            catalog_code=request.catalog_code,
            items=request.items,
            auto_match_skus=request.auto_match_skus,
        )
        return EdiCatalogSyncResponse(
            partner_id=sync_res.partner_id,
            catalog_code=sync_res.catalog_code,
            total_items=sync_res.total_items,
            matched_items=sync_res.matched_items,
            unmatched_items=sync_res.unmatched_items,
            price_updated_items=sync_res.price_updated_items,
            sync_status=sync_res.sync_status,
        )
    except Exception as e:
        logger.error(f"Catalog sync error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Catalog sync error: {str(e)}",
        )


@router.post("/catalog/export")
def export_supplier_catalog_endpoint(
    partner_id: int = Query(...),
    standard: str = Query("ANSI_X12", description="ANSI_X12 or EDIFACT"),
    catalog_code: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    currency: str = Query("USD"),
    user: dict = Depends(get_current_user),
):
    """
    Export Nova product catalog into EDI 832 (Price/Sales Catalog) or UN/EDIFACT PRICAT interchange format.
    """
    try:
        result = edi_catalog_service.export_catalog(
            partner_id=partner_id,
            standard=standard,
            catalog_code=catalog_code,
            category=category,
            currency=currency,
        )
        return {
            "partner_id": result.partner_id,
            "standard": result.standard,
            "catalog_code": result.catalog_code,
            "total_items": result.total_items,
            "control_number": result.control_number,
            "edi_payload": result.edi_payload,
        }
    except Exception as e:
        logger.error(f"Catalog export error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Catalog export failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# 5. SKU Cross-Reference Matrix & Bulk Import
# ---------------------------------------------------------------------------

@router.post("/cross-reference/resolve")
def resolve_line_cross_reference(
    partner_id: Optional[int] = None,
    partner_sku: Optional[str] = None,
    partner_sku_type: Optional[str] = None,
    gtin: Optional[str] = None,
    partner_uom: str = "EA",
    ordered_price: Optional[float] = None,
    customer_id: Optional[int] = None,
    price_tolerance_percent: float = 0.0,
    user: dict = Depends(get_current_user),
):
    """
    Resolve buyer part number, GTIN, or barcode against internal Nova products and calculate contract pricing.
    """
    raw_item = {
        "partner_sku": partner_sku,
        "partner_sku_type": partner_sku_type,
        "gtin": gtin,
        "ordered_uom": partner_uom,
        "ordered_price": ordered_price or 0.0,
        "ordered_qty": 1.0,
    }

    res = cross_reference_service.cross_reference_line(
        partner_id=partner_id,
        raw_item=raw_item,
        line_no=1,
        customer_id=customer_id,
        price_tolerance_percent=price_tolerance_percent,
    )
    is_matched = False
    errors_list = []
    if res.sku_resolution:
        is_matched = getattr(res.sku_resolution, "matched", getattr(res.sku_resolution, "is_matched", False))
        if hasattr(res.sku_resolution, "errors") and res.sku_resolution.errors:
            errors_list = res.sku_resolution.errors
        elif getattr(res.sku_resolution, "error_message", None):
            errors_list = [res.sku_resolution.error_message]

    return {
        "is_matched": is_matched,
        "product_id": res.product_id,
        "product_name": res.product_name,
        "resolved_sku": res.internal_sku,
        "uom_conversion_factor": res.uom_factor,
        "internal_qty": res.converted_qty,
        "contract_price": res.expected_price,
        "price_discrepancy": res.discrepancy_info.model_dump() if res.discrepancy_info else None,
        "has_discrepancy": res.has_discrepancy,
        "errors": errors_list,
    }



@router.post("/sku-mappings/bulk-import")
def bulk_import_sku_mappings(
    partner_id: int = Query(...),
    mappings: List[Dict[str, Any]] = [],
    overwrite_existing: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    """
    Bulk import SKU / GTIN cross-reference mappings for a trading partner (T0135).
    """
    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mappings list cannot be empty",
        )

    result = cross_reference_service.bulk_import_mappings(
        partner_id=partner_id,
        mappings=mappings,
        overwrite_existing=overwrite_existing,
    )
    return result


# ---------------------------------------------------------------------------
# 6. GS1 SSCC Pallet Logistics & Label Formatting
# ---------------------------------------------------------------------------

@router.post("/sscc/generate")
def generate_sscc_barcode_endpoint(
    company_prefix: Optional[str] = Query(None),
    pallet_number: Optional[str] = Query(None),
    delivery_id: Optional[int] = Query(None),
    sales_order_id: Optional[int] = Query(None),
    package_type: str = Query("PALLET"),
    gross_weight_kg: Optional[float] = Query(None),
    user: dict = Depends(get_current_user),
):
    """
    Generate a unique GS1 SSCC-18 (Serial Shipping Container Code) with Modulo-10 check digit and register pallet in T0137.
    """
    sscc_18 = generate_sscc18(company_prefix=company_prefix)
    record = {
        "sscc_barcode": sscc_18,
        "delivery_id": delivery_id,
        "sales_order_id": sales_order_id,
        "pallet_number": pallet_number or f"PLT-{sscc_18[-6:]}",
        "package_type": package_type,
        "gross_weight_kg": gross_weight_kg,
        "status": "CREATED",
    }
    created = EDI_SSCC_PALLET_REPO.create(record)
    return {
        "id": created.get("id"),
        "sscc_barcode": sscc_18,
        "gs1_128_formatted": f"(00){sscc_18}",
        "pallet_record": created,
    }


@router.get("/sscc/{identifier}/label")
def get_sscc_logistics_label(
    identifier: str,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve formatted GS1-128 Logistics Pallet Label with AI(00) and packaging metadata.
    """
    # Check if identifier is ID or SSCC barcode
    pallet = None
    if identifier.isdigit():
        pallet = EDI_SSCC_PALLET_REPO.get(int(identifier))
    if not pallet:
        pallets = EDI_SSCC_PALLET_REPO.list(filters={"sscc_barcode": identifier}, limit=1)
        if pallets:
            pallet = pallets[0]

    if not pallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pallet SSCC '{identifier}' not found in T0137",
        )

    label_data = format_gs1_logistics_label(pallet_data=pallet)

    return {
        "sscc_barcode": pallet.get("sscc_barcode"),
        "pallet_number": pallet.get("pallet_number"),
        "package_type": pallet.get("package_type"),
        "status": pallet.get("status"),
        "gross_weight_kg": pallet.get("gross_weight_kg"),
        "label": label_data,
        "label_text": label_data.get("ascii_label", ""),
    }

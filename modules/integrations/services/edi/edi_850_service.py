"""
Nova ERP — Inbound EDI 850 (Purchase Order) & UN/EDIFACT ORDERS Ingestion Service
Parses inbound ANSI X12 850 and UN/EDIFACT ORDERS interchanges, extracts header and line items,
cross-references buyer SKUs and prices with tolerance thresholds, checks customer credit limits,
creates Nova sales orders (T0012/T0013), generates Functional Acknowledgments (997 FA / CONTRL),
and manages transaction logs in T0136.
"""

import re
import uuid
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from modules.core.services.base import CrudService
from packages.database.connection import get_connection, release_connection, db_transaction

from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiAckStatus,
    EdiDirection,
    EdiIngestResult,
    EdiLineDiscrepancy,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_TRANSACTION_REPO,
)
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiSegment,
    EdiTransactionSet,
    EdiFunctionalGroup,
    EdiInterchange,
    parse_edi,
    parse_x12,
    parse_edifact,
    detect_edi_standard,
    EdiSyntaxError,
)
from modules.integrations.services.edi.cross_reference_service import (
    CrossReferenceService,
    cross_reference_service,
    OrderCrossReferenceSummary,
    LineCrossReferenceResult,
    normalize_sku_type,
)
from modules.integrations.services.edi.edi_ack_service import (
    EdiAckService,
    edi_ack_service,
    generate_edi_ack,
    EdiSyntaxErrorInfo,
)
from modules.sales.services.credit_service import CreditService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default Repositories for Sales Orders, Order Lines, and Customers
# ---------------------------------------------------------------------------

SALES_ORDER_T0012_REPO = CrudRepository(
    'T0012',
    business_columns=[
        'id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal',
        'tax', 'grand_total', 'freight_amount', 'discount_amount',
        'sales_rep_id', 'status', 'order_date', 'notes', 'price_list_id',
        'tax_rate_id', 'payment_term_id', 'client_order_uuid',
        'is_offline_sync', 'sync_status', 'offline_created_at',
        'hold_reason', 'hold_released_by', 'hold_released_at', 'hold_release_reason',
    ],
)

SALES_LINE_T0013_REPO = CrudRepository(
    'T0013',
    business_columns=[
        'id', 'sales_order_id', 'product_id', 'product_name', 'uom_id',
        'qty', 'unit_price', 'cost_price', 'discount', 'line_total',
        'line_number', 'is_catch_weight', 'pricing_uom_id',
        'unit_price_pricing_uom', 'nominal_weight', 'catch_weight_actual',
        'recalculated_total',
    ],
)

CUSTOMER_T0010_REPO = CrudRepository(
    'T0010',
    business_columns=[
        'id', 'name', 'group_name', 'phone', 'email', 'credit_limit',
        'balance', 'is_active', 'default_price_list_id', 'default_tax_rate_id',
        'payment_term_id',
    ],
)


# ---------------------------------------------------------------------------
# Helper: Sequence Nextval for Control & Transaction Numbers
# ---------------------------------------------------------------------------

def _fetch_nextval(conn, sequence_name: str = "seq_edi_control_num") -> Optional[int]:
    """Fetch next integer value from PostgreSQL sequence."""
    try:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT nextval('\"Nova\".{sequence_name}')")
            row = cur.fetchone()
            if row:
                return int(row[0])
        except Exception:
            try:
                cur.execute(f"SELECT nextval('{sequence_name}')")
                row = cur.fetchone()
                if row:
                    return int(row[0])
            except Exception:
                pass
        finally:
            cur.close()
    except Exception as e:
        logger.debug(f"Could not read sequence {sequence_name}: {e}")
    return None


def _generate_control_number(conn=None) -> str:
    """Generate next EDI control number."""
    val = None
    if conn is not None:
        val = _fetch_nextval(conn, "seq_edi_control_num")
    else:
        try:
            c = get_connection()
            try:
                val = _fetch_nextval(c, "seq_edi_control_num")
            finally:
                release_connection(c)
        except Exception:
            pass

    if val is None:
        import time
        val = int(time.time() * 1000) % 1000000000
    return str(val)


# ---------------------------------------------------------------------------
# Date Parsing Helpers
# ---------------------------------------------------------------------------

def _parse_edi_date(raw_date_str: Optional[str], format_qualifier: Optional[str] = None) -> Optional[date]:
    """
    Safely parse various EDI date strings into standard Python date objects.
    Supports CCYYMMDD, YYMMDD, ISO YYYY-MM-DD, and EDIFACT format qualifiers (102, 203, 602).
    """
    if not raw_date_str:
        return None

    clean = str(raw_date_str).strip()
    if not clean:
        return None

    # Handle ISO string (e.g. 2026-09-08 or 2026-09-08T00:00:00)
    if '-' in clean:
        try:
            return date.fromisoformat(clean[:10])
        except Exception:
            pass

    # EDIFACT format qualifier 102 = CCYYMMDD, 203 = CCYYMMDDHHMM
    if format_qualifier == '102' or (len(clean) == 8 and clean.isdigit()):
        try:
            year = int(clean[0:4])
            month = int(clean[4:6])
            day = int(clean[6:8])
            return date(year, month, day)
        except Exception:
            pass

    if format_qualifier == '203' and len(clean) >= 8 and clean[:8].isdigit():
        try:
            year = int(clean[0:4])
            month = int(clean[4:6])
            day = int(clean[6:8])
            return date(year, month, day)
        except Exception:
            pass

    # ANSI X12 YYMMDD (6 digits)
    if len(clean) == 6 and clean.isdigit():
        try:
            yy = int(clean[0:2])
            year = 2000 + yy if yy < 70 else 1900 + yy
            month = int(clean[2:4])
            day = int(clean[4:6])
            return date(year, month, day)
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Data Models for Parsed Inbound EDI 850 / ORDERS
# ---------------------------------------------------------------------------

class Edi850Header(BaseModel):
    """Header data extracted from an EDI 850 or EDIFACT ORDERS message."""
    po_number: str = Field(..., description="Buyer purchase order number")
    order_type: str = Field("NE", description="Order type code (e.g. NE, SA, 220)")
    order_date: Optional[date] = Field(None, description="PO order date")
    requested_delivery_date: Optional[date] = Field(None, description="Requested delivery date")
    requested_ship_date: Optional[date] = Field(None, description="Requested ship date")
    currency: str = Field("USD", description="Order currency (USD, AED, EUR, etc.)")
    department: Optional[str] = Field(None, description="Buyer department / store division code")
    vendor_id: Optional[str] = Field(None, description="Vendor account identifier assigned by buyer")
    customer_account: Optional[str] = Field(None, description="Buyer account number")
    buyer_name: Optional[str] = Field(None, description="Buyer organization name")
    buyer_id: Optional[str] = Field(None, description="Buyer GLN / identifier")
    ship_to_name: Optional[str] = Field(None, description="Ship-to destination name")
    ship_to_id: Optional[str] = Field(None, description="Ship-to GLN or location code")
    ship_to_address: Optional[str] = Field(None, description="Ship-to street address")
    bill_to_name: Optional[str] = Field(None, description="Bill-to organization name")
    bill_to_id: Optional[str] = Field(None, description="Bill-to identifier")
    notes: Optional[str] = Field(None, description="Free-text instructions or terms")


class Edi850LineItem(BaseModel):
    """Line item data extracted from an EDI 850 PO1 or EDIFACT ORDERS LIN loop."""
    line_number: int = Field(..., description="Line sequence number")
    buyer_sku: str = Field(..., description="Buyer part number / SKU / GTIN")
    vendor_sku: Optional[str] = Field(None, description="Vendor part number if present")
    gtin: Optional[str] = Field(None, description="GTIN / EAN barcode")
    partner_sku_type: str = Field("BUYER_PART_NO", description="Normalized SKU type")
    ordered_qty: float = Field(..., description="Quantity ordered")
    ordered_uom: str = Field("EA", description="Unit of measure (e.g. EA, CA, BX, KG)")
    ordered_price: float = Field(0.0, description="Unit price per partner UOM")
    description: Optional[str] = Field(None, description="Product description / item details")


class ParsedEdi850Order(BaseModel):
    """Complete parsed structure of an EDI 850 or EDIFACT ORDERS purchase order."""
    standard: str = "ANSI_X12"
    document_type: str = "850"
    control_number: str = ""
    sender_id: str = ""
    sender_qualifier: str = "ZZ"
    receiver_id: str = ""
    receiver_qualifier: str = "ZZ"
    header: Edi850Header
    lines: List[Edi850LineItem] = Field(default_factory=list)
    raw_segments_count: int = 0


# ---------------------------------------------------------------------------
# 1. ANSI X12 850 Parser Engine
# ---------------------------------------------------------------------------

def parse_x12_850(interchange_or_raw: Union[str, EdiInterchange], delimiters: Optional[EdiDelimiters] = None) -> List[ParsedEdi850Order]:
    """
    Parse ANSI X12 850 Purchase Order interchange(s) into structured ParsedEdi850Order objects.
    Extracts BEG, CUR, DTM, REF, N1 party loops, and PO1 item loops with qualifiers.
    """
    if isinstance(interchange_or_raw, str):
        interchange = parse_x12(interchange_or_raw, delimiters)
    else:
        interchange = interchange_or_raw

    results: List[ParsedEdi850Order] = []
    tx_sets = interchange.all_transactions()

    for tx in tx_sets:
        doc_type = tx.doc_type or "850"
        ctrl_num = tx.control_number or interchange.control_number or ""

        # 1. Extract BEG (Beginning Segment for Purchase Order)
        beg = tx.find_first("BEG")
        po_number = beg.get(3) if beg else f"PO-{ctrl_num}"
        order_type = beg.get(2, "NE") if beg else "NE"
        order_date_raw = beg.get(5) if beg else None
        order_date = _parse_edi_date(order_date_raw)

        # 2. Extract Currency (CUR)
        cur = tx.find_first("CUR")
        currency = cur.get(2, "USD") if cur else "USD"

        # 3. Extract DTM (Date/Time References)
        requested_delivery_date = None
        requested_ship_date = None
        for dtm in tx.find_segments("DTM"):
            qual = dtm.get(1)
            d_val = _parse_edi_date(dtm.get(2))
            if qual in ("002", "037", "038") and not requested_delivery_date:
                requested_delivery_date = d_val
            elif qual in ("010", "004") and not requested_ship_date:
                requested_ship_date = d_val

        # 4. Extract REF (Reference Information)
        department = None
        vendor_id = None
        customer_account = None
        for ref in tx.find_segments("REF"):
            r_qual = ref.get(1)
            r_val = ref.get(2)
            if r_qual == "DP":
                department = r_val
            elif r_qual in ("IA", "VR"):
                vendor_id = r_val
            elif r_qual in ("IT", "CA"):
                customer_account = r_val

        # 5. Extract N1 loops (Name and Address)
        n1_loops = tx.get_loops("N1", ["PO1", "CTT", "AMT", "SE"])
        buyer_name = None
        buyer_id = None
        ship_to_name = None
        ship_to_id = None
        ship_to_address = None
        bill_to_name = None
        bill_to_id = None

        for n1_loop in n1_loops:
            if not n1_loop:
                continue
            n1_seg = n1_loop[0]
            entity_code = n1_seg.get(1, "").upper()
            p_name = n1_seg.get(2)
            p_id = n1_seg.get(4)

            # Check for N3 address inside loop
            addr_str = None
            for sub_seg in n1_loop[1:]:
                if sub_seg.tag == "N3":
                    addr_str = sub_seg.get(1)

            if entity_code in ("BY", "OB", "BT"):
                if not buyer_name:
                    buyer_name = p_name
                if not buyer_id:
                    buyer_id = p_id
                if entity_code == "BT":
                    bill_to_name = p_name
                    bill_to_id = p_id
            elif entity_code == "ST":
                ship_to_name = p_name
                ship_to_id = p_id
                ship_to_address = addr_str
            elif entity_code == "VN":
                if not vendor_id and p_id:
                    vendor_id = p_id

        # 6. Extract Notes (NTE / MSG)
        notes_list = []
        for nte in tx.find_segments("NTE"):
            if nte.get(2):
                notes_list.append(nte.get(2))
        for msg in tx.find_segments("MSG"):
            if msg.get(1):
                notes_list.append(msg.get(1))
        notes = " | ".join(notes_list) if notes_list else None

        header = Edi850Header(
            po_number=po_number,
            order_type=order_type,
            order_date=order_date or date.today(),
            requested_delivery_date=requested_delivery_date,
            requested_ship_date=requested_ship_date,
            currency=currency,
            department=department,
            vendor_id=vendor_id,
            customer_account=customer_account,
            buyer_name=buyer_name or interchange.sender_id,
            buyer_id=buyer_id or interchange.sender_id,
            ship_to_name=ship_to_name,
            ship_to_id=ship_to_id,
            ship_to_address=ship_to_address,
            bill_to_name=bill_to_name,
            bill_to_id=bill_to_id,
            notes=notes,
        )

        # 7. Extract PO1 Item Loops
        po1_loops = tx.get_loops("PO1", ["CTT", "AMT", "SE"])
        line_items: List[Edi850LineItem] = []

        for idx, p_loop in enumerate(po1_loops, start=1):
            if not p_loop:
                continue
            po1 = p_loop[0]

            line_no_str = po1.get(1)
            try:
                line_no = int(line_no_str) if line_no_str and line_no_str.isdigit() else idx
            except Exception:
                line_no = idx

            try:
                ordered_qty = float(po1.get(2, 0.0) or 0.0)
            except Exception:
                ordered_qty = 0.0

            ordered_uom = po1.get(3, "EA").strip().upper() or "EA"

            try:
                ordered_price = float(po1.get(4, 0.0) or 0.0)
            except Exception:
                ordered_price = 0.0

            # Scan paired qualifiers (PO106/PO107, PO108/PO109, etc.)
            buyer_sku = None
            vendor_sku = None
            gtin = None
            canon_type = "BUYER_PART_NO"

            elem_idx = 6
            while elem_idx <= len(po1.elements):
                q_code = po1.get(elem_idx, "").strip().upper()
                q_val = po1.get(elem_idx + 1, "").strip()
                if q_code and q_val:
                    c_type = normalize_sku_type(q_code)
                    if c_type == "GTIN":
                        gtin = q_val
                        if not buyer_sku:
                            buyer_sku = q_val
                            canon_type = "GTIN"
                    elif c_type == "VENDOR_PART_NO":
                        vendor_sku = q_val
                    elif c_type == "BUYER_PART_NO":
                        buyer_sku = q_val
                        canon_type = "BUYER_PART_NO"
                    elif not buyer_sku:
                        buyer_sku = q_val
                        canon_type = c_type
                elem_idx += 2

            # Fallback if no qualifier found
            if not buyer_sku:
                # Check PO107 directly or line sequence
                fallback = po1.get(7) or po1.get(6) or f"ITEM-{line_no}"
                buyer_sku = fallback

            # Extract PID (Product Description) within PO1 loop
            item_desc = None
            for sub_seg in p_loop[1:]:
                if sub_seg.tag == "PID":
                    item_desc = sub_seg.get(5) or sub_seg.get(4)
                    break
                elif sub_seg.tag == "CTP" and ordered_price == 0.0:
                    try:
                        ordered_price = float(sub_seg.get(3, 0.0) or 0.0)
                    except Exception:
                        pass

            line_items.append(
                Edi850LineItem(
                    line_number=line_no,
                    buyer_sku=buyer_sku,
                    vendor_sku=vendor_sku,
                    gtin=gtin,
                    partner_sku_type=canon_type,
                    ordered_qty=ordered_qty,
                    ordered_uom=ordered_uom,
                    ordered_price=ordered_price,
                    description=item_desc,
                )
            )

        results.append(
            ParsedEdi850Order(
                standard="ANSI_X12",
                document_type=doc_type,
                control_number=ctrl_num,
                sender_id=interchange.sender_id,
                sender_qualifier=interchange.sender_qualifier or "ZZ",
                receiver_id=interchange.receiver_id,
                receiver_qualifier=interchange.receiver_qualifier or "ZZ",
                header=header,
                lines=line_items,
                raw_segments_count=len(tx.segments),
            )
        )

    return results


# ---------------------------------------------------------------------------
# 2. UN/EDIFACT ORDERS Parser Engine
# ---------------------------------------------------------------------------

def parse_edifact_orders(interchange_or_raw: Union[str, EdiInterchange], delimiters: Optional[EdiDelimiters] = None) -> List[ParsedEdi850Order]:
    """
    Parse UN/EDIFACT ORDERS message interchange(s) into structured ParsedEdi850Order objects.
    Extracts BGM, DTM, NAD, FTX, and LIN item loops with QTY, PRI, PIA, and IMD segments.
    """
    if isinstance(interchange_or_raw, str):
        interchange = parse_edifact(interchange_or_raw, delimiters)
    else:
        interchange = interchange_or_raw

    results: List[ParsedEdi850Order] = []
    tx_sets = interchange.all_transactions()

    for tx in tx_sets:
        doc_type = tx.doc_type or "ORDERS"
        ctrl_num = tx.control_number or interchange.control_number or ""

        # 1. Extract BGM (Beginning of Message)
        bgm = tx.find_first("BGM")
        po_number = f"PO-{ctrl_num}"
        order_type = "220"
        if bgm:
            po_val = bgm.get_component(2, 1) or bgm.get(2)
            if po_val:
                po_number = po_val
            order_type = bgm.get_component(1, 1) or bgm.get(1, "220")

        # 2. Extract DTM (Date/Time/Period)
        order_date = None
        requested_delivery_date = None
        for dtm in tx.find_segments("DTM"):
            # DTM+137:20260908:102'
            dtm_comp = dtm.get_composite(1)
            if len(dtm_comp) >= 2:
                qual = dtm_comp[0]
                d_str = dtm_comp[1]
                fmt = dtm_comp[2] if len(dtm_comp) > 2 else "102"
                d_val = _parse_edi_date(d_str, fmt)
                if qual in ("137", "4") and not order_date:
                    order_date = d_val
                elif qual in ("2", "117", "64") and not requested_delivery_date:
                    requested_delivery_date = d_val

        # 3. Extract CUX (Currency)
        currency = "USD"
        cux = tx.find_first("CUX")
        if cux:
            cux_comp = cux.get_composite(1)
            if len(cux_comp) >= 2 and cux_comp[1]:
                currency = cux_comp[1]
            elif cux.get(2):
                currency = cux.get(2)

        # 4. Extract FTX (Free Text Notes)
        notes_list = []
        for ftx in tx.find_segments("FTX"):
            ftx_comp = ftx.get_composite(4)
            if ftx_comp:
                notes_list.append(" ".join(ftx_comp))
            elif ftx.get(4):
                notes_list.append(ftx.get(4))
        notes = " | ".join(notes_list) if notes_list else None

        # 5. Extract NAD Loops (Name and Address)
        nad_loops = tx.get_loops("NAD", ["LIN", "UNS", "CNT", "MOA", "UNT"])
        buyer_name = None
        buyer_id = None
        ship_to_name = None
        ship_to_id = None
        ship_to_address = None
        bill_to_name = None
        bill_to_id = None

        for n_loop in nad_loops:
            if not n_loop:
                continue
            nad = n_loop[0]
            party_qual = nad.get(1, "").upper()
            party_id = nad.get_component(2, 1) or nad.get(2)
            party_name = nad.get_component(4, 1) or nad.get(4)
            street = nad.get_component(5, 1) or nad.get(5)

            if party_qual in ("BY", "IV"):
                if not buyer_name:
                    buyer_name = party_name
                if not buyer_id:
                    buyer_id = party_id
                if party_qual == "IV":
                    bill_to_name = party_name
                    bill_to_id = party_id
            elif party_qual in ("DP", "CN", "UD"):
                ship_to_name = party_name
                ship_to_id = party_id
                ship_to_address = street

        header = Edi850Header(
            po_number=po_number,
            order_type=order_type,
            order_date=order_date or date.today(),
            requested_delivery_date=requested_delivery_date,
            currency=currency,
            buyer_name=buyer_name or interchange.sender_id,
            buyer_id=buyer_id or interchange.sender_id,
            ship_to_name=ship_to_name,
            ship_to_id=ship_to_id,
            ship_to_address=ship_to_address,
            bill_to_name=bill_to_name,
            bill_to_id=bill_to_id,
            notes=notes,
        )

        # 6. Extract LIN Item Loops
        lin_loops = tx.get_loops("LIN", ["UNS", "CNT", "MOA", "UNT"])
        line_items: List[Edi850LineItem] = []

        for idx, l_loop in enumerate(lin_loops, start=1):
            if not l_loop:
                continue
            lin = l_loop[0]

            line_no_str = lin.get(1)
            try:
                line_no = int(line_no_str) if line_no_str and line_no_str.isdigit() else idx
            except Exception:
                line_no = idx

            # LIN03: Item number identification (e.g. 6291041000101:SRV or CRF-SKU:IN)
            lin_item_id = lin.get_component(3, 1) or lin.get(3)
            lin_item_qual = lin.get_component(3, 2) or "IN"

            buyer_sku = None
            vendor_sku = None
            gtin = None
            canon_type = normalize_sku_type(lin_item_qual)

            if canon_type == "GTIN":
                gtin = lin_item_id
                buyer_sku = lin_item_id
            elif canon_type == "VENDOR_PART_NO":
                vendor_sku = lin_item_id
            else:
                buyer_sku = lin_item_id

            ordered_qty = 0.0
            ordered_uom = "EA"
            ordered_price = 0.0
            item_desc = None

            # Scan sub-segments inside LIN loop
            for sub_seg in l_loop[1:]:
                if sub_seg.tag == "PIA":
                    # PIA+1+CRF-SKU:IN+VEND-SKU:SA'
                    for p_pos in range(2, len(sub_seg.elements) + 1):
                        p_val = sub_seg.get_component(p_pos, 1)
                        p_q = sub_seg.get_component(p_pos, 2)
                        if p_val:
                            c_t = normalize_sku_type(p_q)
                            if c_t == "GTIN":
                                gtin = p_val
                                if not buyer_sku:
                                    buyer_sku = p_val
                                    canon_type = "GTIN"
                            elif c_t == "VENDOR_PART_NO":
                                vendor_sku = p_val
                            elif c_t == "BUYER_PART_NO":
                                buyer_sku = p_val
                                canon_type = "BUYER_PART_NO"

                elif sub_seg.tag == "IMD":
                    # IMD+F++:::Basmati Rice 5kg'
                    desc_comp = sub_seg.get_component(3, 4) or sub_seg.get_component(3, 1) or sub_seg.get(3)
                    if desc_comp:
                        item_desc = desc_comp

                elif sub_seg.tag == "QTY":
                    # QTY+21:100:EA'
                    qty_comp = sub_seg.get_composite(1)
                    if len(qty_comp) >= 2:
                        try:
                            ordered_qty = float(qty_comp[1] or 0.0)
                        except Exception:
                            ordered_qty = 0.0
                        if len(qty_comp) >= 3 and qty_comp[2]:
                            ordered_uom = qty_comp[2].strip().upper()

                elif sub_seg.tag == "PRI":
                    # PRI+AAA:12.50:::NTP'
                    pri_comp = sub_seg.get_composite(1)
                    if len(pri_comp) >= 2:
                        try:
                            ordered_price = float(pri_comp[1] or 0.0)
                        except Exception:
                            ordered_price = 0.0

            if not buyer_sku:
                buyer_sku = lin_item_id or f"ITEM-{line_no}"

            line_items.append(
                Edi850LineItem(
                    line_number=line_no,
                    buyer_sku=buyer_sku,
                    vendor_sku=vendor_sku,
                    gtin=gtin,
                    partner_sku_type=canon_type,
                    ordered_qty=ordered_qty,
                    ordered_uom=ordered_uom,
                    ordered_price=ordered_price,
                    description=item_desc,
                )
            )

        results.append(
            ParsedEdi850Order(
                standard="EDIFACT",
                document_type=doc_type,
                control_number=ctrl_num,
                sender_id=interchange.sender_id,
                sender_qualifier=interchange.sender_qualifier or "ZZ",
                receiver_id=interchange.receiver_id,
                receiver_qualifier=interchange.receiver_qualifier or "ZZ",
                header=header,
                lines=line_items,
                raw_segments_count=len(tx.segments),
            )
        )

    return results


# ---------------------------------------------------------------------------
# Universal Inbound Order Parser
# ---------------------------------------------------------------------------

def parse_inbound_order_edi(raw_content: str, standard: Optional[str] = None) -> List[ParsedEdi850Order]:
    """
    Universal parser for inbound purchase order EDI messages (ANSI X12 850 or UN/EDIFACT ORDERS).
    Automatically detects standard if omitted.
    """
    if not raw_content or not raw_content.strip():
        raise EdiSyntaxError("EDI payload is empty")

    std_enum = EdiStandard.EDIFACT if standard and standard.upper() == "EDIFACT" else (
        EdiStandard.ANSI_X12 if standard and standard.upper() == "ANSI_X12" else detect_edi_standard(raw_content)
    )

    if std_enum == EdiStandard.EDIFACT:
        return parse_edifact_orders(raw_content)
    else:
        return parse_x12_850(raw_content)


# ---------------------------------------------------------------------------
# Inbound EDI 850 Service Engine
# ---------------------------------------------------------------------------

class Edi850Service(CrudService):
    """
    Core Inbound EDI 850 / ORDERS Service.
    Coordinates interchange ingestion, trading partner matching, SKU & price cross-referencing,
    customer credit limit verification, sales order creation in T0012/T0013, 997/CONTRL ACK generation,
    and audit log updates in T0136.
    """

    def __init__(
        self,
        transaction_repo: Optional[CrudRepository] = None,
        partner_repo: Optional[CrudRepository] = None,
        order_repo: Optional[CrudRepository] = None,
        line_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        xref_service: Optional[CrossReferenceService] = None,
        credit_svc: Optional[CreditService] = None,
        ack_svc: Optional[EdiAckService] = None,
    ):
        self.tx_repo = transaction_repo or EDI_TRANSACTION_REPO
        self.partner_repo = partner_repo or EDI_PARTNER_REPO
        self.order_repo = order_repo or SALES_ORDER_T0012_REPO
        self.line_repo = line_repo or SALES_LINE_T0013_REPO
        self.customer_repo = customer_repo or CUSTOMER_T0010_REPO
        self.xref_service = xref_service or cross_reference_service
        self.credit_service = credit_svc or CreditService(customer_repo=self.customer_repo, order_repo=self.order_repo)
        self.ack_service = ack_svc or edi_ack_service
        super().__init__(self.tx_repo)

    # -----------------------------------------------------------------------
    # Trading Partner Matching
    # -----------------------------------------------------------------------

    def resolve_partner(
        self,
        inbound_order: ParsedEdi850Order,
        partner_id: Optional[int] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Locate matching EdiPartner (T0134) configuration by partner_id, interchange_sender_id,
        or buyer identifier.
        """
        if partner_id:
            try:
                p = self.partner_repo.get(partner_id, conn=conn)
                if p and p.get('is_active', True):
                    return p
            except Exception as e:
                logger.warning(f"Failed to lookup partner by ID {partner_id}: {e}")

        sender_id = inbound_order.sender_id.strip() if inbound_order.sender_id else ""
        if sender_id:
            try:
                partners = self.partner_repo.list(
                    filters={'interchange_sender_id': sender_id, 'is_active': True},
                    limit=1,
                    conn=conn,
                )
                if partners:
                    return partners[0]
            except Exception as e:
                logger.debug(f"Partner lookup by sender_id '{sender_id}' failed: {e}")

        # Check buyer_id / GLN from header
        buyer_id = inbound_order.header.buyer_id
        if buyer_id and buyer_id != sender_id:
            try:
                partners = self.partner_repo.list(
                    filters={'interchange_sender_id': buyer_id, 'is_active': True},
                    limit=1,
                    conn=conn,
                )
                if partners:
                    return partners[0]
            except Exception:
                pass

        return None

    # -----------------------------------------------------------------------
    # Sales Order Creation in Nova ERP (T0012 & T0013)
    # -----------------------------------------------------------------------

    def create_sales_order(
        self,
        parsed_order: ParsedEdi850Order,
        partner: Optional[Dict[str, Any]],
        summary: OrderCrossReferenceSummary,
        credit_eval: Optional[Dict[str, Any]],
        auto_confirm: bool = False,
        conn=None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a new sales order header (T0012) and order lines (T0013) corresponding to the EDI 850 PO.
        Determines order status: 'Confirmed', 'Pending', or 'Credit Hold'.
        """
        customer_id = partner.get('customer_id') if partner else None
        if not customer_id and self.customer_repo:
            # Fallback: search customer by partner code or buyer name
            try:
                c_name = parsed_order.header.buyer_name or parsed_order.sender_id
                custs = self.customer_repo.list(filters={'name': c_name}, limit=1, conn=conn)
                if custs:
                    customer_id = custs[0]['id']
            except Exception:
                pass

        if not customer_id:
            customer_id = 1  # Default fallback customer

        po_num = parsed_order.header.po_number or "UNKNOWN"
        order_date_val = parsed_order.header.order_date or date.today()

        # Determine Order Status and Hold Reason
        hold_reasons = []
        is_clean = summary.is_clean
        is_credit_hold = credit_eval.get('is_hold_required', False) if credit_eval else False

        if summary.unmatched_lines > 0:
            hold_reasons.append(f"Unmatched SKUs on {summary.unmatched_lines} line(s)")
        if summary.discrepancy_lines > 0:
            hold_reasons.append(f"Price discrepancies on {summary.discrepancy_lines} line(s)")
        if is_credit_hold:
            hold_reasons.append(credit_eval.get('hold_reason', 'Customer credit threshold exceeded'))

        if hold_reasons:
            status = "Pending"  # In T0012 order_status enum
            hold_reason_text = "; ".join(hold_reasons)
        elif auto_confirm:
            status = "Confirmed"
            hold_reason_text = None
        else:
            status = "Pending"
            hold_reason_text = None

        # Format Order Number
        clean_po = re.sub(r'[^A-Za-z0-9\-]', '', po_num)[:30]
        order_num_candidate = f"SO-EDI-{clean_po}"
        # Ensure unique order number
        existing = self.order_repo.list(filters={'order_number': order_num_candidate}, limit=1, conn=conn)
        if existing:
            unique_suffix = uuid.uuid4().hex[:6].upper()
            order_number = f"SO-EDI-{clean_po}-{unique_suffix}"
        else:
            order_number = order_num_candidate

        notes_parts = [f"EDI Inbound {parsed_order.document_type} PO: {po_num}"]
        if partner:
            notes_parts.append(f"Partner: {partner.get('partner_code', partner.get('partner_name'))}")
        if parsed_order.header.department:
            notes_parts.append(f"Dept: {parsed_order.header.department}")
        if parsed_order.header.notes:
            notes_parts.append(f"Instructions: {parsed_order.header.notes}")
        if hold_reason_text:
            notes_parts.append(f"HOLD: {hold_reason_text}")

        full_notes = " | ".join(notes_parts)

        subtotal = summary.total_ordered_amount
        tax = 0.0
        grand_total = subtotal

        order_data = {
            'order_number': order_number,
            'customer_id': customer_id,
            'warehouse_id': None,
            'subtotal': round(subtotal, 2),
            'tax': round(tax, 2),
            'grand_total': round(grand_total, 2),
            'freight_amount': 0.0,
            'discount_amount': 0.0,
            'status': status,
            'order_date': order_date_val,
            'notes': full_notes,
            'price_list_id': None,
            'hold_reason': hold_reason_text,
            'sync_status': 'Synced',
        }

        created_order = self.order_repo.create(order_data, conn=conn)
        order_id = created_order['id']

        # Insert Order Lines (T0013)
        created_lines: List[Dict[str, Any]] = []
        for line_res in summary.line_results:
            p_id = line_res.product_id or 1
            p_name = line_res.product_name or line_res.buyer_sku
            qty_val = line_res.converted_qty if line_res.converted_qty > 0 else line_res.ordered_qty
            unit_p = line_res.ordered_price
            l_total = round(line_res.ordered_qty * line_res.ordered_price, 2)

            line_data = {
                'sales_order_id': order_id,
                'product_id': p_id,
                'product_name': p_name[:200],
                'uom_id': None,
                'qty': round(qty_val, 2),
                'unit_price': round(unit_p, 2),
                'cost_price': 0.0,
                'discount': 0.0,
                'line_total': round(l_total, 2),
                'line_number': line_res.line_number,
            }
            c_line = self.line_repo.create(line_data, conn=conn)
            created_lines.append(c_line)

        return created_order, created_lines

    # -----------------------------------------------------------------------
    # Main Inbound 850 Ingestion Workflow
    # -----------------------------------------------------------------------

    def process_inbound_850(
        self,
        raw_payload: str,
        partner_id: Optional[int] = None,
        auto_confirm: Optional[bool] = None,
        standard: Optional[str] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> EdiIngestResult:
        """
        Main entry point for processing an inbound EDI 850 PO or EDIFACT ORDERS message.
        
        Workflow:
        1. Initialize transaction record in T0136.
        2. Parse EDI payload into structured order(s).
        3. Match trading partner configuration (T0134).
        4. Cross-reference SKUs, UOMs, and prices against contracts / price lists (T0135/T0138/T0122/T0084).
        5. Check customer credit standing and delinquent invoice thresholds.
        6. Create sales order in T0012 and sales line items in T0013.
        7. Generate 997 Functional Acknowledgment / EDIFACT CONTRL response.
        8. Update and persist final transaction status and parsed data in T0136.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        clean_payload = raw_payload.strip() if raw_payload else ""
        if not clean_payload:
            raise ValueError("EDI document payload cannot be empty")

        # Generate unique transaction number & control number
        ctrl_num = _generate_control_number(conn=conn)
        txn_number = f"TXN-850-{ctrl_num[-6:]}"

        detected_std = EdiStandard.EDIFACT if standard and standard.upper() == "EDIFACT" else (
            EdiStandard.ANSI_X12 if standard and standard.upper() == "ANSI_X12" else detect_edi_standard(clean_payload)
        )
        std_str = detected_std.value
        doc_type_str = "ORDERS" if detected_std == EdiStandard.EDIFACT else "850"

        # 1. Create Initial Transaction Log (T0136)
        tx_record = {
            'transaction_number': txn_number,
            'partner_id': partner_id,
            'standard': std_str,
            'document_type': doc_type_str,
            'direction': EdiDirection.INBOUND.value,
            'control_number': ctrl_num,
            'status': EdiTransactionStatus.PENDING.value,
            'raw_payload': clean_payload,
            'ack_status': EdiAckStatus.PENDING.value,
        }
        created_tx = self.tx_repo.create(tx_record, conn=conn)
        tx_id = created_tx['id']

        # 2. Parse EDI Payload
        try:
            parsed_orders = parse_inbound_order_edi(clean_payload, standard=std_str)
        except EdiSyntaxError as syn_err:
            logger.error(f"EDI Syntax Error in transaction {tx_id}: {syn_err}")
            # Generate rejection ACK
            ack_payload, ack_status_enum, ack_summary = generate_edi_ack(
                inbound=clean_payload,
                standard=std_str,
                is_accepted=False,
                errors=[EdiSyntaxErrorInfo(error_message=str(syn_err))],
                ack_control_number=ctrl_num,
            )
            err_msg = f"Syntax Error: {syn_err.message}"
            self.tx_repo.update(
                tx_id,
                {
                    'status': EdiTransactionStatus.FAILED.value,
                    'ack_status': EdiAckStatus.REJECTED.value,
                    'ack_payload': ack_payload,
                    'error_details': err_msg,
                    'processed_at': datetime.now(timezone.utc),
                },
                conn=conn,
            )
            return EdiIngestResult(
                transaction_id=tx_id,
                transaction_number=txn_number,
                status=EdiTransactionStatus.FAILED.value,
                standard=std_str,
                document_type=doc_type_str,
                control_number=ctrl_num,
                partner_id=partner_id,
                ack_generated=True,
                ack_payload=ack_payload,
                errors=[err_msg],
            )
        except Exception as e:
            logger.error(f"Unexpected parser failure for EDI transaction {tx_id}: {e}")
            err_msg = f"Document parsing failed: {str(e)}"
            self.tx_repo.update(
                tx_id,
                {
                    'status': EdiTransactionStatus.FAILED.value,
                    'error_details': err_msg,
                    'processed_at': datetime.now(timezone.utc),
                },
                conn=conn,
            )
            return EdiIngestResult(
                transaction_id=tx_id,
                transaction_number=txn_number,
                status=EdiTransactionStatus.FAILED.value,
                standard=std_str,
                document_type=doc_type_str,
                control_number=ctrl_num,
                partner_id=partner_id,
                errors=[err_msg],
            )

        if not parsed_orders:
            err_msg = "No transaction sets or purchase order messages found in interchange"
            ack_payload, ack_status_enum, _ = generate_edi_ack(
                inbound=clean_payload,
                standard=std_str,
                is_accepted=False,
                errors=[EdiSyntaxErrorInfo(error_message=err_msg)],
                ack_control_number=ctrl_num,
            )
            self.tx_repo.update(
                tx_id,
                {
                    'status': EdiTransactionStatus.FAILED.value,
                    'ack_status': EdiAckStatus.REJECTED.value,
                    'ack_payload': ack_payload,
                    'error_details': err_msg,
                    'processed_at': datetime.now(timezone.utc),
                },
                conn=conn,
            )
            return EdiIngestResult(
                transaction_id=tx_id,
                transaction_number=txn_number,
                status=EdiTransactionStatus.FAILED.value,
                standard=std_str,
                document_type=doc_type_str,
                control_number=ctrl_num,
                partner_id=partner_id,
                ack_generated=True,
                ack_payload=ack_payload,
                errors=[err_msg],
            )

        # Process the primary purchase order from interchange
        order = parsed_orders[0]

        # 3. Match Trading Partner (T0134)
        partner = self.resolve_partner(order, partner_id=partner_id, conn=conn)
        effective_partner_id = partner.get('id') if partner else partner_id
        partner_code = partner.get('partner_code') if partner else None
        partner_auto_confirm = partner.get('auto_confirm_orders', False) if partner else False
        price_tolerance = float(partner.get('price_tolerance_percent', 0.0)) if partner else 0.0
        customer_id = partner.get('customer_id') if partner else None

        effective_auto_confirm = auto_confirm if auto_confirm is not None else partner_auto_confirm

        # 4. Cross-Reference Lines (T0135, T0138, T0122, T0084, T0001)
        raw_lines = [l.model_dump() for l in order.lines]
        xref_summary = self.xref_service.cross_reference_order(
            partner_id=effective_partner_id,
            customer_id=customer_id,
            line_items=raw_lines,
            price_tolerance_percent=price_tolerance,
            auto_confirm_orders=effective_auto_confirm,
            eval_date=order.header.order_date,
            conn=conn,
        )

        # 5. Customer Credit Limit & Delinquency Check
        credit_eval = None
        if customer_id and self.credit_service:
            try:
                credit_eval = self.credit_service.evaluate_order_credit(
                    customer_id=customer_id,
                    order_amount=xref_summary.total_ordered_amount,
                    as_of_date=order.header.order_date,
                    conn=conn,
                )
            except Exception as e:
                logger.warning(f"Credit evaluation failed for customer {customer_id}: {e}")

        # 6. Create Sales Order (T0012 / T0013)
        created_order, created_lines = self.create_sales_order(
            parsed_order=order,
            partner=partner,
            summary=xref_summary,
            credit_eval=credit_eval,
            auto_confirm=effective_auto_confirm,
            conn=conn,
        )

        sales_order_id = created_order.get('id')
        sales_order_number = created_order.get('order_number')

        # Determine Final Transaction Status
        all_clean = xref_summary.is_clean and not (credit_eval and credit_eval.get('is_hold_required'))
        if not xref_summary.is_clean or (credit_eval and credit_eval.get('is_hold_required')):
            tx_status = EdiTransactionStatus.PRICE_DISCREPANCY_HOLD.value
            ack_accept_flag = False if xref_summary.unmatched_lines > 0 else True
        else:
            tx_status = EdiTransactionStatus.PROCESSED.value
            ack_accept_flag = True

        # 7. Generate Functional Acknowledgment (997 FA / CONTRL)
        ack_errors = []
        for disc in xref_summary.price_discrepancies:
            ack_errors.append(
                EdiSyntaxErrorInfo(
                    segment_tag="PO1" if std_str == "ANSI_X12" else "LIN",
                    segment_position=disc.line_number,
                    error_message=f"Line {disc.line_number}: {disc.details or disc.discrepancy_type}",
                )
            )

        ack_payload, ack_status_enum, ack_summary = generate_edi_ack(
            inbound=clean_payload,
            partner=partner,
            standard=std_str,
            is_accepted=ack_accept_flag,
            errors=ack_errors if ack_errors else None,
            ack_control_number=ctrl_num,
        )

        # 8. Update Transaction Log in T0136
        err_details_list = list(xref_summary.errors)
        if credit_eval and credit_eval.get('is_hold_required'):
            err_details_list.append(f"Credit Hold: {credit_eval.get('hold_reason')}")
        err_details_str = " | ".join(err_details_list) if err_details_list else None

        parsed_data_summary = {
            'header': order.header.model_dump(mode='json'),
            'total_lines': len(order.lines),
            'matched_lines': xref_summary.matched_lines,
            'unmatched_lines': xref_summary.unmatched_lines,
            'discrepancy_lines': xref_summary.discrepancy_lines,
            'total_amount': xref_summary.total_ordered_amount,
            'recommended_status': xref_summary.recommended_status,
            'order_status': created_order.get('status'),
            'credit_check': credit_eval,
        }

        self.tx_repo.update(
            tx_id,
            {
                'partner_id': effective_partner_id,
                'status': tx_status,
                'sales_order_id': sales_order_id,
                'parsed_data': parsed_data_summary,
                'ack_status': ack_status_enum.value,
                'ack_payload': ack_payload,
                'error_details': err_details_str,
                'processed_at': datetime.now(timezone.utc),
            },
            conn=conn,
        )

        return EdiIngestResult(
            transaction_id=tx_id,
            transaction_number=txn_number,
            status=tx_status,
            standard=std_str,
            document_type=doc_type_str,
            control_number=ctrl_num,
            partner_id=effective_partner_id,
            partner_code=partner_code,
            sales_order_id=sales_order_id,
            sales_order_number=sales_order_number,
            ack_generated=True,
            ack_payload=ack_payload,
            price_discrepancies=xref_summary.price_discrepancies,
            errors=err_details_list,
        )

    # -----------------------------------------------------------------------
    # Transaction Reprocessing Engine
    # -----------------------------------------------------------------------

    def reprocess_transaction(
        self,
        transaction_id: int,
        force_confirm: bool = False,
        override_price_tolerance: Optional[float] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> EdiIngestResult:
        """
        Reprocess a previously held or failed EDI transaction (T0136).
        Allows overriding price tolerance thresholds or force-confirming sales orders.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        tx = self.tx_repo.get(transaction_id, conn=conn)
        if not tx:
            raise ValueError(f"EDI Transaction record {transaction_id} not found")

        raw_payload = tx.get('raw_payload', '')
        if not raw_payload:
            raise ValueError(f"EDI Transaction {transaction_id} contains no raw payload to reprocess")

        partner_id = tx.get('partner_id')
        std_str = tx.get('standard')
        ctrl_num = tx.get('control_number') or _generate_control_number(conn=conn)
        txn_number = tx.get('transaction_number') or f"TXN-850-{ctrl_num[-6:]}"
        doc_type_str = tx.get('document_type') or "850"

        # Parse EDI Payload
        parsed_orders = parse_inbound_order_edi(raw_payload, standard=std_str)
        if not parsed_orders:
            raise ValueError("Failed to parse purchase order message from raw payload")

        order = parsed_orders[0]
        partner = self.resolve_partner(order, partner_id=partner_id, conn=conn)
        effective_partner_id = partner.get('id') if partner else partner_id
        partner_code = partner.get('partner_code') if partner else None
        customer_id = partner.get('customer_id') if partner else None

        tol_pct = override_price_tolerance if override_price_tolerance is not None else (
            float(partner.get('price_tolerance_percent', 0.0)) if partner else 0.0
        )

        # Cross-reference lines with updated tolerance
        raw_lines = [l.model_dump() for l in order.lines]
        xref_summary = self.xref_service.cross_reference_order(
            partner_id=effective_partner_id,
            customer_id=customer_id,
            line_items=raw_lines,
            price_tolerance_percent=tol_pct,
            auto_confirm_orders=force_confirm,
            eval_date=order.header.order_date,
            conn=conn,
        )

        # Check existing sales order
        sales_order_id = tx.get('sales_order_id')
        sales_order_number = None

        if sales_order_id:
            try:
                existing_so = self.order_repo.get(sales_order_id, conn=conn)
                if existing_so:
                    sales_order_number = existing_so.get('order_number')
                    # Update status
                    new_status = "Confirmed" if (force_confirm or (xref_summary.is_clean)) else "Pending"
                    new_hold_reason = None if (force_confirm or xref_summary.is_clean) else "Price Discrepancy Hold"
                    self.order_repo.update(
                        sales_order_id,
                        {
                            'status': new_status,
                            'hold_reason': new_hold_reason,
                        },
                        conn=conn,
                    )
            except Exception as e:
                logger.warning(f"Failed to update existing sales order {sales_order_id}: {e}")
        else:
            # Create sales order if one didn't exist
            created_order, _ = self.create_sales_order(
                parsed_order=order,
                partner=partner,
                summary=xref_summary,
                credit_eval=None,
                auto_confirm=force_confirm or xref_summary.is_clean,
                conn=conn,
            )
            sales_order_id = created_order.get('id')
            sales_order_number = created_order.get('order_number')

        new_tx_status = EdiTransactionStatus.PROCESSED.value if (force_confirm or xref_summary.is_clean) else EdiTransactionStatus.PRICE_DISCREPANCY_HOLD.value

        # Update transaction in T0136
        self.tx_repo.update(
            transaction_id,
            {
                'status': new_tx_status,
                'sales_order_id': sales_order_id,
                'error_details': None if (force_confirm or xref_summary.is_clean) else " | ".join(xref_summary.errors),
                'processed_at': datetime.now(timezone.utc),
            },
            conn=conn,
        )

        return EdiIngestResult(
            transaction_id=transaction_id,
            transaction_number=txn_number,
            status=new_tx_status,
            standard=std_str,
            document_type=doc_type_str,
            control_number=ctrl_num,
            partner_id=effective_partner_id,
            partner_code=partner_code,
            sales_order_id=sales_order_id,
            sales_order_number=sales_order_number,
            ack_generated=bool(tx.get('ack_payload')),
            ack_payload=tx.get('ack_payload'),
            price_discrepancies=[] if force_confirm else xref_summary.price_discrepancies,
            errors=[] if (force_confirm or xref_summary.is_clean) else xref_summary.errors,
        )

    # Alias for API controllers & MCP tools
    ingest_inbound_order = process_inbound_850


# Global singleton instance
edi_850_service = Edi850Service()


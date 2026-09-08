"""
Nova ERP — Supplier Catalog Sync & EDI 832 / PRICAT Engine
Provides parsing, synchronization, and outbound generation of electronic product catalogs
and wholesale price lists (ANSI X12 832 Price/Sales Catalog & UN/EDIFACT PRICAT).
Automates SKU/GTIN cross-referencing, price change detection, packaging dimension capture,
and synchronization into the EDI SKU Cross-Reference Matrix (T0125) and Catalog Items (T0128).
"""

import re
import uuid
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field

from modules.core.context import get_current_tenant
from modules.core.repositories.base import CrudRepository
from packages.database.connection import get_connection, release_connection, db_transaction

from modules.integrations.models.edi import (
    EdiStandard,
    EdiDocumentType,
    EdiTransactionStatus,
    EdiCatalogSyncStatus,
    EdiDirection,
    EdiCatalogSyncRequest,
    EdiCatalogSyncResponse,
    EdiPartner,
    EdiCatalogItem,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_CATALOG_ITEM_REPO,
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
    serialize_x12,
    serialize_edifact,
    serialize_edi,
    detect_edi_standard,
    X12Builder,
    EdifactBuilder,
    EdiSyntaxError,
)
from modules.integrations.services.edi.cross_reference_service import (
    normalize_sku_type,
    EDI_SKU_QUALIFIERS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default Repositories for Products, Barcodes, and Price Lists
# ---------------------------------------------------------------------------

PRODUCT_T0001_REPO = CrudRepository(
    'T0001',
    business_columns=[
        'id', 'name', 'sku', 'barcode', 'description', 'type',
        'price', 'cost_price', 'category', 'brand', 'tax_rate',
        'weight', 'volume', 'is_active', 'is_catch_weight'
    ]
)

BARCODE_T0004_REPO = CrudRepository(
    'T0004',
    business_columns=['id', 'product_id', 'barcode', 'barcode_type', 'is_primary']
)

PRICE_LIST_T0083_REPO = CrudRepository(
    'T0083',
    business_columns=['id', 'name', 'code', 'description', 'is_default', 'is_active']
)

PRICE_LIST_ITEM_T0084_REPO = CrudRepository(
    'T0084',
    business_columns=[
        'id', 'price_list_id', 'product_id', 'price', 'min_qty', 'max_qty',
        'discount_percent', 'discount_amount', 'pricing_type', 'is_active'
    ]
)


# ---------------------------------------------------------------------------
# Data Models for Catalog Interchange & Synchronization
# ---------------------------------------------------------------------------

class EdiCatalogHeader(BaseModel):
    """Parsed header of an EDI 832 / PRICAT catalog interchange."""
    catalog_code: str
    catalog_name: Optional[str] = None
    partner_id: Optional[int] = None
    partner_code: Optional[str] = None
    supplier_code: Optional[str] = None
    buyer_code: Optional[str] = None
    currency: str = "USD"
    action_code: str = "00"  # 00: Original, 05: Replace, RC: Replace Catalog, 9: Original
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    control_number: Optional[str] = None
    standard: str = "ANSI_X12"


class EdiCatalogLine(BaseModel):
    """Parsed line item from an EDI 832 / PRICAT catalog."""
    line_number: int
    buyer_sku: str
    supplier_sku: Optional[str] = None
    gtin: Optional[str] = None
    product_name: str
    product_description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    uom: str = "EA"
    pack_size: int = 1
    list_price: float = 0.0
    currency: str = "USD"
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    dimension_uom: Optional[str] = None
    matched_product_id: Optional[int] = None
    sync_status: str = "PENDING"


class ParsedEdiCatalog(BaseModel):
    """Structured catalog extracted from an EDI document."""
    header: EdiCatalogHeader
    items: List[EdiCatalogLine] = Field(default_factory=list)
    standard: str
    control_number: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class CatalogItemSyncDetail(BaseModel):
    """Per-item outcome of the catalog sync process."""
    buyer_sku: str
    supplier_sku: Optional[str] = None
    gtin: Optional[str] = None
    product_name: str
    matched_product_id: Optional[int] = None
    old_price: Optional[float] = None
    new_price: float
    price_changed: bool = False
    sync_status: str  # SYNCED, PRICE_CHANGED, UNMATCHED
    message: Optional[str] = None
    sku_mapping_id: Optional[int] = None
    catalog_item_id: Optional[int] = None


class CatalogSyncResult(BaseModel):
    """Comprehensive catalog synchronization summary."""
    partner_id: int
    catalog_code: str
    total_items: int = 0
    matched_items: int = 0
    unmatched_items: int = 0
    price_updated_items: int = 0
    sync_status: str = "SYNCED"  # SYNCED, PRICE_CHANGED, UNMATCHED, PARTIALLY_SYNCED
    details: List[CatalogItemSyncDetail] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CatalogExportResult(BaseModel):
    """Generated outbound EDI 832 / PRICAT export result."""
    partner_id: int
    catalog_code: str
    control_number: str
    standard: str
    document_type: str
    total_items: int
    edi_payload: str


# ---------------------------------------------------------------------------
# Helper: Date and Number Parsers
# ---------------------------------------------------------------------------

def _parse_edi_date(val: Optional[str]) -> Optional[date]:
    """Parse date from common EDI string formats (YYYYMMDD, YYMMDD, CCYYMMDD)."""
    if not val:
        return None
    cleaned = re.sub(r'[^0-9]', '', str(val).strip())
    if len(cleaned) == 8:
        try:
            return datetime.strptime(cleaned, "%Y%m%d").date()
        except ValueError:
            pass
    elif len(cleaned) == 6:
        try:
            return datetime.strptime(cleaned, "%y%m%d").date()
        except ValueError:
            pass
    return None


def _parse_float(val: Any, default: float = 0.0) -> float:
    """Safe float conversion from string or number."""
    if val is None or val == "":
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def _parse_int(val: Any, default: int = 1) -> int:
    """Safe int conversion from string or number."""
    if val is None or val == "":
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


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
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# ANSI X12 832 Parser (Price/Sales Catalog)
# ---------------------------------------------------------------------------

def parse_x12_832(payload: str, delimiters: Optional[EdiDelimiters] = None) -> ParsedEdiCatalog:
    """
    Parse an ANSI X12 832 Price/Sales Catalog document into a structured ParsedEdiCatalog.
    Extracts BCT header, CUR currency, DTM dates, N1 trading parties, and LIN product loops
    with PID descriptions, CTP pricing, PO4 packaging/dimensions, and MEA measurements.
    """
    interchange = parse_x12(payload, delimiters)
    errors: List[str] = []

    # Find 832 transaction set
    tx_832: Optional[EdiTransactionSet] = None
    for tx in interchange.all_transactions():
        if tx.doc_type == "832" or tx.doc_type.startswith("832"):
            tx_832 = tx
            break

    if not tx_832:
        all_txs = interchange.all_transactions()
        if all_txs:
            tx_832 = all_txs[0]
        else:
            raise EdiSyntaxError("No transaction sets found in ANSI X12 832 document")

    # 1. Header Information
    catalog_code = f"CAT-{uuid.uuid4().hex[:8].upper()}"
    catalog_name = None
    action_code = "00"
    currency = "USD"
    eff_start_date: Optional[date] = None
    eff_end_date: Optional[date] = None
    partner_code = None
    supplier_code = None
    buyer_code = None

    # BCT segment (1-based position indexing: BCT01 = get(1), BCT02 = get(2)...)
    bct_seg = tx_832.find_first("BCT")
    if bct_seg:
        action_code = bct_seg.get(1, "00") or "00"
        cat_num = bct_seg.get(2)
        if cat_num:
            catalog_code = cat_num
        bct_date = bct_seg.get(6) or bct_seg.get(10)
        if bct_date:
            eff_start_date = _parse_edi_date(bct_date)

    # CUR segment (CUR01 = entity qual, CUR02 = currency)
    cur_seg = tx_832.find_first("CUR")
    if cur_seg:
        currency = cur_seg.get(2, "USD") or cur_seg.get(1, "USD") or "USD"

    # DTM segments (DTM01 = qual, DTM02 = date)
    for dtm_seg in tx_832.find_segments("DTM"):
        qual = dtm_seg.get(1, "").upper()
        dt_val = _parse_edi_date(dtm_seg.get(2))
        if dt_val:
            if qual in ("007", "193", "092", "002"):
                eff_start_date = dt_val
            elif qual in ("194", "093", "036"):
                eff_end_date = dt_val
            elif not eff_start_date:
                eff_start_date = dt_val

    # N1 segments (N101 = qual, N102 = name, N103 = id qual, N104 = id)
    for n1_seg in tx_832.find_segments("N1"):
        party_type = n1_seg.get(1, "").upper()
        party_name = n1_seg.get(2)
        party_id = n1_seg.get(4)
        if party_type in ("VN", "SE", "SU"):
            supplier_code = party_id or party_name
            if not catalog_name and party_name:
                catalog_name = f"{party_name} Catalog"
        elif party_type in ("BY", "ST", "BT"):
            buyer_code = party_id or party_name
            partner_code = buyer_code

    header = EdiCatalogHeader(
        catalog_code=catalog_code,
        catalog_name=catalog_name or f"Catalog {catalog_code}",
        partner_code=partner_code or buyer_code or interchange.sender_id.strip(),
        supplier_code=supplier_code or interchange.receiver_id.strip(),
        buyer_code=buyer_code or partner_code or interchange.sender_id.strip(),
        currency=currency,
        action_code=action_code,
        effective_start_date=eff_start_date,
        effective_end_date=eff_end_date,
        control_number=tx_832.control_number or interchange.control_number,
        standard="ANSI_X12",
    )

    # 2. Line Items (LIN loops)
    items: List[EdiCatalogLine] = []
    line_number = 1
    total_segs = len(tx_832.segments)
    idx = 0

    while idx < total_segs:
        seg = tx_832.segments[idx]
        if seg.tag == "LIN":
            loop_segs = [seg]
            idx += 1
            while idx < total_segs and tx_832.segments[idx].tag not in ("LIN", "CTT", "SE"):
                loop_segs.append(tx_832.segments[idx])
                idx += 1

            buyer_sku = None
            supplier_sku = None
            gtin = None
            prod_name = None
            prod_desc = None
            category = None
            brand = None
            uom = "EA"
            pack_size = 1
            list_price = 0.0
            line_eff_start = eff_start_date
            line_eff_end = eff_end_date
            gross_wt = None
            net_wt = None
            vol = None
            length = None
            width = None
            height = None
            dim_uom = None

            assigned_id = seg.get(1)
            if assigned_id and str(assigned_id).isdigit():
                current_line_no = int(assigned_id)
            else:
                current_line_no = line_number

            elem_idx = 1
            while elem_idx < len(seg.elements):
                qual = str(seg.elements[elem_idx]).strip().upper()
                val = str(seg.elements[elem_idx + 1]).strip() if elem_idx + 1 < len(seg.elements) else ""
                if qual and val:
                    canon_type = normalize_sku_type(qual)
                    if canon_type == "BUYER_PART_NO":
                        buyer_sku = val
                    elif canon_type == "VENDOR_PART_NO":
                        supplier_sku = val
                    elif canon_type == "GTIN":
                        gtin = val
                    elif qual in ("BP", "CB", "IN"):
                        buyer_sku = val
                    elif qual in ("VN", "VP", "SK", "SA"):
                        supplier_sku = val
                    elif qual in ("UP", "EN", "UK", "SRV"):
                        gtin = val
                elem_idx += 2

            if not buyer_sku:
                if supplier_sku:
                    buyer_sku = supplier_sku
                elif gtin:
                    buyer_sku = gtin
                elif assigned_id:
                    buyer_sku = str(assigned_id)
                else:
                    buyer_sku = f"SKU-{current_line_no}"

            for child in loop_segs[1:]:
                if child.tag == "PID":
                    # PID01=type(F), PID02=char code, PID05=description
                    item_type = child.get(1, "").upper()
                    char_code = child.get(2, "").upper()
                    desc_val = child.get(5) or child.get(4) or child.get(3)
                    if desc_val:
                        if char_code == "08" or item_type == "08":
                            category = desc_val
                        elif not prod_name:
                            prod_name = desc_val
                        else:
                            prod_desc = desc_val

                elif child.tag == "CTP":
                    # CTP01=class, CTP02=price_id, CTP03=unit_price, CTP04=qty, CTP05=uom
                    price_val = child.get(3) or child.get(2)
                    if price_val:
                        list_price = _parse_float(price_val, list_price)
                    qty_val = child.get(4)
                    if qty_val:
                        pack_size = _parse_int(qty_val, pack_size)
                    uom_val = child.get(5)
                    if uom_val:
                        uom = uom_val

                elif child.tag == "PO4":
                    # PO401=pack, PO405=wt qual, PO406=gross wt, PO407=vol qual, PO408=vol, PO409=len, PO410=width, PO411=height, PO412=uom
                    pack_val = child.get(1)
                    if pack_val:
                        pack_size = _parse_int(pack_val, pack_size)
                    gross_val = child.get(6) or child.get(7)
                    if gross_val:
                        gross_wt = _parse_float(gross_val)
                    vol_val = child.get(8) or child.get(9)
                    if vol_val:
                        vol = _parse_float(vol_val)
                    if child.get(9) and child.get(8):
                        length = _parse_float(child.get(9))
                        width = _parse_float(child.get(10))
                        height = _parse_float(child.get(11))
                        dim_uom = child.get(12)
                    elif child.get(10):
                        length = _parse_float(child.get(10))
                        width = _parse_float(child.get(11))
                        height = _parse_float(child.get(12))
                        dim_uom = child.get(13)

                elif child.tag == "MEA":
                    # MEA01=spec, MEA02=type, MEA03=val, MEA04=uom
                    meas_spec = child.get(1, "").upper()
                    meas_val = _parse_float(child.get(3))
                    meas_uom = child.get(4, "").upper()
                    if meas_spec in ("WT", "PD", "G") or meas_uom in ("KG", "LBS", "G"):
                        if gross_wt is None:
                            gross_wt = meas_val
                        else:
                            net_wt = meas_val
                    elif meas_spec in ("VOL", "VL") or meas_uom in ("CBM", "M3", "CFT"):
                        vol = meas_val
                    elif meas_spec in ("LN", "LEN"):
                        length = meas_val
                    elif meas_spec in ("WD", "WID"):
                        width = meas_val
                    elif meas_spec in ("HT", "HEI"):
                        height = meas_val

                elif child.tag == "DTM":
                    qual = child.get(1, "").upper()
                    dt_val = _parse_edi_date(child.get(2))
                    if dt_val:
                        if qual in ("193", "007", "092"):
                            line_eff_start = dt_val
                        elif qual in ("194", "093", "036"):
                            line_eff_end = dt_val

            if not prod_name:
                prod_name = buyer_sku or supplier_sku or "Catalog Product"

            line_item = EdiCatalogLine(
                line_number=current_line_no,
                buyer_sku=buyer_sku,
                supplier_sku=supplier_sku,
                gtin=gtin,
                product_name=prod_name,
                product_description=prod_desc,
                category=category,
                brand=brand,
                uom=uom,
                pack_size=pack_size,
                list_price=list_price,
                currency=currency,
                effective_start_date=line_eff_start,
                effective_end_date=line_eff_end,
                gross_weight_kg=gross_wt,
                net_weight_kg=net_wt,
                volume_cbm=vol,
                length=length,
                width=width,
                height=height,
                dimension_uom=dim_uom,
            )
            items.append(line_item)
            line_number += 1
        else:
            idx += 1

    return ParsedEdiCatalog(
        header=header,
        items=items,
        standard="ANSI_X12",
        control_number=header.control_number,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# UN/EDIFACT PRICAT Parser (Price/Sales Catalogue)
# ---------------------------------------------------------------------------

def parse_edifact_pricat(payload: str, delimiters: Optional[EdiDelimiters] = None) -> ParsedEdiCatalog:
    """
    Parse a UN/EDIFACT PRICAT Price/Sales Catalogue document into a structured ParsedEdiCatalog.
    Extracts BGM document number, DTM dates, CUX currency, NAD trading parties, and LIN loops
    with PIA additional IDs, IMD descriptions, PRI prices, PAC packaging, and MEA measurements.
    """
    interchange = parse_edifact(payload, delimiters)
    errors: List[str] = []

    msg_pricat: Optional[EdiTransactionSet] = None
    for msg in interchange.all_transactions():
        if msg.doc_type == "PRICAT" or msg.doc_type.startswith("PRICAT"):
            msg_pricat = msg
            break

    if not msg_pricat:
        all_msgs = interchange.all_transactions()
        if all_msgs:
            msg_pricat = all_msgs[0]
        else:
            raise EdiSyntaxError("No messages found in UN/EDIFACT PRICAT document")

    # 1. Header Information
    catalog_code = f"CAT-{uuid.uuid4().hex[:8].upper()}"
    catalog_name = None
    action_code = "9"
    currency = "USD"
    eff_start_date: Optional[date] = None
    eff_end_date: Optional[date] = None
    partner_code = None
    supplier_code = None
    buyer_code = None

    # BGM segment: BGM+9+CAT-2026-EDIF+9' -> BGM01=9, BGM02=CAT-2026-EDIF, BGM03=9
    bgm_seg = msg_pricat.find_first("BGM")
    if bgm_seg:
        doc_num = bgm_seg.get(2)
        if doc_num:
            catalog_code = str(doc_num)
        action_val = bgm_seg.get(3)
        if action_val:
            action_code = str(action_val)

    # DTM segments: DTM+137:20260908:102' -> DTM01 is composite [137, 20260908, 102]
    for dtm_seg in msg_pricat.find_segments("DTM"):
        dtm_comp = dtm_seg.get_composite(1)
        if dtm_comp and len(dtm_comp) >= 2:
            qual = str(dtm_comp[0]).upper()
            dt_str = str(dtm_comp[1])
            dt_val = _parse_edi_date(dt_str)
            if dt_val:
                if qual in ("137", "193", "200"):
                    eff_start_date = dt_val
                elif qual in ("194", "206", "36"):
                    eff_end_date = dt_val
                elif not eff_start_date:
                    eff_start_date = dt_val

    # CUX segment: CUX+2:EUR:4' -> CUX01 is composite [2, EUR, 4]
    cux_seg = msg_pricat.find_first("CUX")
    if cux_seg:
        cux_comp = cux_seg.get_composite(1)
        if cux_comp and len(cux_comp) >= 2:
            currency = str(cux_comp[1])
        elif cux_seg.get(2):
            currency = str(cux_seg.get(2))

    # NAD segments: NAD+SU+NOVA-HQ::92++Nova Distribution HQ'
    # NAD01=SU, NAD02=[NOVA-HQ, '', 92], NAD04=Nova Distribution HQ
    for nad_seg in msg_pricat.find_segments("NAD"):
        party_type = str(nad_seg.get(1, "")).upper()
        id_comp = nad_seg.get_composite(2)
        party_id = id_comp[0] if id_comp else nad_seg.get(2)
        name_comp = nad_seg.get_composite(4) or nad_seg.get_composite(3)
        party_name = name_comp[0] if name_comp else (nad_seg.get(4) or nad_seg.get(3))

        if party_type in ("SU", "SE", "VN"):
            supplier_code = str(party_id or party_name or "")
            if not catalog_name and party_name:
                catalog_name = f"{party_name} Catalogue"
        elif party_type in ("BY", "UD", "IV"):
            buyer_code = str(party_id or party_name or "")
            partner_code = buyer_code

    header = EdiCatalogHeader(
        catalog_code=catalog_code,
        catalog_name=catalog_name or f"Catalogue {catalog_code}",
        partner_code=partner_code or buyer_code or interchange.sender_id.strip(),
        supplier_code=supplier_code or interchange.receiver_id.strip(),
        buyer_code=buyer_code or partner_code or interchange.sender_id.strip(),
        currency=currency,
        action_code=action_code,
        effective_start_date=eff_start_date,
        effective_end_date=eff_end_date,
        control_number=msg_pricat.control_number or interchange.control_number,
        standard="EDIFACT",
    )

    # 2. Line Items (LIN loops)
    items: List[EdiCatalogLine] = []
    line_number = 1
    total_segs = len(msg_pricat.segments)
    idx = 0

    while idx < total_segs:
        seg = msg_pricat.segments[idx]
        if seg.tag == "LIN":
            loop_segs = [seg]
            idx += 1
            while idx < total_segs and msg_pricat.segments[idx].tag not in ("LIN", "UNT"):
                loop_segs.append(msg_pricat.segments[idx])
                idx += 1

            buyer_sku = None
            supplier_sku = None
            gtin = None
            prod_name = None
            prod_desc = None
            category = None
            brand = None
            uom = "EA"
            pack_size = 1
            list_price = 0.0
            line_eff_start = eff_start_date
            line_eff_end = eff_end_date
            gross_wt = None
            net_wt = None
            vol = None
            length = None
            width = None
            height = None
            dim_uom = None

            # LIN+1++6291041000303:SRV' -> LIN01=1, LIN03=[6291041000303, SRV]
            line_idx_val = seg.get(1)
            current_line_no = int(line_idx_val) if str(line_idx_val).isdigit() else line_number

            item_comp = seg.get_composite(3) or seg.get_composite(2)
            if item_comp:
                val = str(item_comp[0]).strip()
                qual = str(item_comp[1]).strip().upper() if len(item_comp) > 1 else "SRV"
                canon = normalize_sku_type(qual)
                if canon == "GTIN":
                    gtin = val
                elif canon == "BUYER_PART_NO":
                    buyer_sku = val
                elif canon == "VENDOR_PART_NO":
                    supplier_sku = val

            for child in loop_segs[1:]:
                if child.tag == "PIA":
                    # PIA+1+NV-CHEESE-200G:SA+CRF-CHEESE-200:BP'
                    for p_idx in range(2, len(child.elements) + 1):
                        p_comp = child.get_composite(p_idx)
                        if p_comp and len(p_comp) >= 2:
                            p_val = str(p_comp[0]).strip()
                            p_qual = str(p_comp[1]).strip().upper()
                            canon = normalize_sku_type(p_qual)
                            if canon == "BUYER_PART_NO":
                                buyer_sku = p_val
                            elif canon == "VENDOR_PART_NO":
                                supplier_sku = p_val
                            elif canon == "GTIN":
                                gtin = p_val

                elif child.tag == "IMD":
                    # IMD+F++:::Cheddar Cheese Block 200g'
                    desc_type = child.get(1, "").upper()
                    desc_comp = child.get_composite(3)
                    desc_text = desc_comp[3] if len(desc_comp) > 3 else (desc_comp[0] if desc_comp else child.get(3))

                    if desc_text:
                        if desc_type == "C":
                            category = str(desc_text)
                        elif not prod_name:
                            prod_name = str(desc_text)
                        else:
                            prod_desc = str(desc_text)

                elif child.tag == "PRI":
                    # PRI+AAA:8.75:CAL:EA'
                    pri_comp = child.get_composite(1)
                    if pri_comp and len(pri_comp) >= 2:
                        list_price = _parse_float(pri_comp[1], list_price)
                        if len(pri_comp) >= 4:
                            uom = str(pri_comp[3])

                elif child.tag == "PAC":
                    # PAC+24++CT'
                    pac_qty = child.get(1)
                    if pac_qty:
                        pack_size = _parse_int(pac_qty, pack_size)
                    pkg_comp = child.get_composite(3)
                    if pkg_comp:
                        uom = str(pkg_comp[0])

                elif child.tag == "MEA":
                    # MEA+WT+G+KGM:5.400'
                    spec_type = str(child.get(1, "")).upper()
                    val_comp = child.get_composite(3)
                    if val_comp and len(val_comp) >= 2:
                        uom_code = str(val_comp[0]).upper()
                        num_val = _parse_float(val_comp[1])
                    else:
                        uom_code = ""
                        num_val = _parse_float(child.get(3))

                    if spec_type in ("WT", "AAB") or uom_code in ("KGM", "KG", "LBR"):
                        if gross_wt is None:
                            gross_wt = num_val
                        else:
                            net_wt = num_val
                    elif spec_type in ("VOL", "ABJ") or uom_code in ("MTQ", "CBM"):
                        vol = num_val
                    elif spec_type in ("LN", "LEN"):
                        length = num_val
                    elif spec_type in ("WD", "WID"):
                        width = num_val
                    elif spec_type in ("HT", "HEI"):
                        height = num_val

                elif child.tag == "DTM":
                    # DTM+193:20260101:102'
                    dtm_comp = child.get_composite(1)
                    if dtm_comp and len(dtm_comp) >= 2:
                        qual = str(dtm_comp[0]).upper()
                        dt_val = _parse_edi_date(str(dtm_comp[1]))
                        if dt_val:
                            if qual in ("193", "137"):
                                line_eff_start = dt_val
                            elif qual in ("194", "206"):
                                line_eff_end = dt_val

            if not buyer_sku:
                if supplier_sku:
                    buyer_sku = supplier_sku
                elif gtin:
                    buyer_sku = gtin
                else:
                    buyer_sku = f"SKU-{current_line_no}"

            if not prod_name:
                prod_name = buyer_sku or supplier_sku or "Catalogue Product"

            line_item = EdiCatalogLine(
                line_number=current_line_no,
                buyer_sku=buyer_sku,
                supplier_sku=supplier_sku,
                gtin=gtin,
                product_name=prod_name,
                product_description=prod_desc,
                category=category,
                brand=brand,
                uom=uom,
                pack_size=pack_size,
                list_price=list_price,
                currency=currency,
                effective_start_date=line_eff_start,
                effective_end_date=line_eff_end,
                gross_weight_kg=gross_wt,
                net_weight_kg=net_wt,
                volume_cbm=vol,
                length=length,
                width=width,
                height=height,
                dimension_uom=dim_uom,
            )
            items.append(line_item)
            line_number += 1
        else:
            idx += 1

    return ParsedEdiCatalog(
        header=header,
        items=items,
        standard="EDIFACT",
        control_number=header.control_number,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Universal Catalog EDI Parser
# ---------------------------------------------------------------------------

def parse_inbound_catalog_edi(
    payload: str,
    standard: Optional[Union[str, EdiStandard]] = None,
    delimiters: Optional[EdiDelimiters] = None,
) -> ParsedEdiCatalog:
    """
    Parse any inbound catalog document (ANSI X12 832 or UN/EDIFACT PRICAT)
    into a unified ParsedEdiCatalog representation.
    """
    if not standard:
        detected = detect_edi_standard(payload)
    else:
        detected = EdiStandard(str(standard))

    if detected == EdiStandard.EDIFACT or str(standard).upper() == "EDIFACT":
        return parse_edifact_pricat(payload, delimiters)
    else:
        return parse_x12_832(payload, delimiters)


# ---------------------------------------------------------------------------
# ANSI X12 832 Document Builder / Generator
# ---------------------------------------------------------------------------

def generate_x12_832(
    partner: Union[EdiPartner, Dict[str, Any]],
    catalog_code: str,
    items: List[Dict[str, Any]],
    control_number: Optional[str] = None,
    currency: str = "USD",
    delimiters: Optional[EdiDelimiters] = None,
) -> str:
    """
    Construct an ANSI X12 832 (Price/Sales Catalog) formatted interchange.
    Generates ISA, GS, ST, BCT, CUR, DTM, N1 (Vendor & Buyer), LIN loops with
    PID, CTP, PO4, MEA, SE, GE, and IEA envelopes.
    """
    delims = delimiters or EdiDelimiters.from_partner(partner)
    p_dict = partner if isinstance(partner, dict) else partner.dict()

    sender_id = p_dict.get("interchange_receiver_id", "NOVADIST")
    sender_qual = p_dict.get("receiver_qualifier", "ZZ")
    receiver_id = p_dict.get("interchange_sender_id", "SUPERMARKET")
    receiver_qual = p_dict.get("sender_qualifier", "ZZ")
    ctrl_num = control_number or str(uuid.uuid4().int)[:9]

    builder = X12Builder(
        sender_id=sender_id,
        receiver_id=receiver_id,
        sender_qualifier=sender_qual,
        receiver_qualifier=receiver_qual,
        control_number=ctrl_num,
        delimiters=delims,
    )

    now = datetime.now(timezone.utc)
    today_ymd = now.strftime("%Y%m%d")

    builder.start_group(functional_code="SC", group_control_number=ctrl_num)
    builder.start_transaction(doc_type="832", control_number="0001")

    # BCT: Beginning Segment for Price/Sales Catalog
    builder.add_segment("BCT", "00", catalog_code, "", "", "", today_ymd)

    # CUR: Currency
    builder.add_segment("CUR", "SE", currency)

    # DTM: Effective Date
    builder.add_segment("DTM", "007", today_ymd)

    # N1: Parties (VN: Vendor/Supplier, BY: Buyer)
    vendor_name = p_dict.get("partner_name", "Nova Distribution")
    builder.add_segment("N1", "VN", vendor_name, "91", sender_id.strip())
    builder.add_segment("N1", "BY", p_dict.get("partner_name", "Buyer Partner"), "92", receiver_id.strip())

    # LIN Loops (Items)
    for idx, itm in enumerate(items, start=1):
        b_sku = itm.get("buyer_sku") or itm.get("partner_sku") or f"SKU-{idx}"
        s_sku = itm.get("supplier_sku") or itm.get("sku") or ""
        gtin = itm.get("gtin") or itm.get("barcode") or ""
        name = itm.get("product_name") or itm.get("name") or b_sku
        price = _parse_float(itm.get("list_price") or itm.get("price"), 0.0)
        uom = itm.get("uom") or itm.get("partner_uom") or "EA"
        pack_size = _parse_int(itm.get("pack_size"), 1)

        lin_elements: List[str] = [str(idx)]
        if b_sku:
            lin_elements.extend(["BP", str(b_sku)])
        if s_sku:
            lin_elements.extend(["VN", str(s_sku)])
        if gtin:
            lin_elements.extend(["UP", str(gtin)])

        builder.add_segment("LIN", *lin_elements)

        # PID: Product Description (PID01=F, PID05=description)
        builder.add_segment("PID", "F", "", "", "", str(name))

        # CTP: Pricing (CTP01=WS, CTP02=RES, CTP03=unit price, CTP04=qty, CTP05=uom)
        builder.add_segment("CTP", "WS", "RES", f"{price:.2f}", str(pack_size), str(uom))

        # PO4: Packaging Details
        gross_wt = itm.get("gross_weight_kg") or itm.get("weight")
        vol = itm.get("volume_cbm") or itm.get("volume")
        po4_elements = [str(pack_size), "", "", "", ""]
        if gross_wt is not None:
            po4_elements.extend([f"{float(gross_wt):.3f}", "KG"])
        else:
            po4_elements.extend(["", ""])
        if vol is not None:
            po4_elements.extend([f"{float(vol):.4f}", "M3"])
        builder.add_segment("PO4", *po4_elements)

    builder.add_segment("CTT", str(len(items)))

    builder.end_transaction()
    builder.end_group()

    return builder.build(line_breaks=True)


# ---------------------------------------------------------------------------
# UN/EDIFACT PRICAT Document Builder / Generator
# ---------------------------------------------------------------------------

def generate_edifact_pricat(
    partner: Union[EdiPartner, Dict[str, Any]],
    catalog_code: str,
    items: List[Dict[str, Any]],
    control_number: Optional[str] = None,
    currency: str = "USD",
    delimiters: Optional[EdiDelimiters] = None,
) -> str:
    """
    Construct a UN/EDIFACT PRICAT (Price/Sales Catalogue) formatted interchange.
    Generates UNA, UNB, UNH (PRICAT:D:96A:UN), BGM, DTM, CUX, NAD, LIN loops with
    PIA, IMD, PRI, PAC, MEA, UNT, and UNZ envelopes.
    """
    delims = delimiters or EdiDelimiters.from_partner(partner)
    p_dict = partner if isinstance(partner, dict) else partner.dict()

    sender_id = p_dict.get("interchange_receiver_id", "NOVADIST")
    sender_qual = p_dict.get("receiver_qualifier", "ZZ")
    receiver_id = p_dict.get("interchange_sender_id", "SUPERMARKET")
    receiver_qual = p_dict.get("sender_qualifier", "ZZ")
    ctrl_num = control_number or str(uuid.uuid4().int)[:9]

    builder = EdifactBuilder(
        sender_id=sender_id,
        receiver_id=receiver_id,
        sender_qualifier=sender_qual,
        receiver_qualifier=receiver_qual,
        control_number=ctrl_num,
        delimiters=delims,
        include_una=True,
    )

    now = datetime.now(timezone.utc)
    today_ymd = now.strftime("%Y%m%d")

    builder.start_message(doc_type="PRICAT", control_number="1")

    # BGM: Beginning of Message
    builder.add_segment("BGM", "9", catalog_code, "9")

    # DTM: Document / Effective Date (137 = Document Date)
    builder.add_segment("DTM", ["137", today_ymd, "102"])

    # CUX: Currencies
    builder.add_segment("CUX", ["2", currency, "4"])

    # NAD: Name and Address (SU = Supplier, BY = Buyer)
    vendor_name = p_dict.get("partner_name", "Nova Distribution")
    builder.add_segment("NAD", "SU", [sender_id.strip(), "", "92"], "", vendor_name)
    builder.add_segment("NAD", "BY", [receiver_id.strip(), "", "9"], "", p_dict.get("partner_name", "Buyer Partner"))

    # LIN Loops
    for idx, itm in enumerate(items, start=1):
        b_sku = itm.get("buyer_sku") or itm.get("partner_sku") or f"SKU-{idx}"
        s_sku = itm.get("supplier_sku") or itm.get("sku") or ""
        gtin = itm.get("gtin") or itm.get("barcode") or ""
        name = itm.get("product_name") or itm.get("name") or b_sku
        price = _parse_float(itm.get("list_price") or itm.get("price"), 0.0)
        uom = itm.get("uom") or itm.get("partner_uom") or "EA"
        pack_size = _parse_int(itm.get("pack_size"), 1)

        if gtin:
            builder.add_segment("LIN", str(idx), "", [gtin, "SRV"])
        elif b_sku:
            builder.add_segment("LIN", str(idx), "", [b_sku, "IN"])
        else:
            builder.add_segment("LIN", str(idx), "", [s_sku or f"SKU-{idx}", "SA"])

        pia_elems = ["1"]
        if s_sku:
            pia_elems.append([s_sku, "SA"])
        if b_sku and gtin:
            pia_elems.append([b_sku, "BP"])
        if len(pia_elems) > 1:
            builder.add_segment("PIA", *pia_elems)

        # IMD: Item Description
        builder.add_segment("IMD", "F", "", ["", "", "", str(name)])

        # PRI: Price Details
        builder.add_segment("PRI", ["AAA", f"{price:.2f}", "CAL", str(uom)])

        # PAC: Package Details
        builder.add_segment("PAC", str(pack_size), "", str(uom))

        # MEA: Weight
        gross_wt = itm.get("gross_weight_kg") or itm.get("weight")
        if gross_wt is not None:
            builder.add_segment("MEA", "WT", "G", ["KGM", f"{float(gross_wt):.3f}"])

    builder.end_message()
    return builder.build(line_breaks=True)


# ---------------------------------------------------------------------------
# Supplier Catalog Sync Service Engine
# ---------------------------------------------------------------------------

class EdiCatalogService:
    """
    B2B EDI Catalog Service Engine.
    Handles electronic catalog parsing, product/GTIN matching, price change detection,
    database synchronization in T0128, automated SKU cross-reference matrix updates in T0125,
    and outbound EDI 832 / PRICAT catalog export.
    """

    def __init__(
        self,
        partner_repo: Optional[CrudRepository] = None,
        sku_mapping_repo: Optional[CrudRepository] = None,
        catalog_repo: Optional[CrudRepository] = None,
        transaction_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        barcode_repo: Optional[CrudRepository] = None,
        price_list_repo: Optional[CrudRepository] = None,
        price_list_item_repo: Optional[CrudRepository] = None,
    ):
        self.partner_repo = partner_repo or EDI_PARTNER_REPO
        self.sku_mapping_repo = sku_mapping_repo or EDI_SKU_MAPPING_REPO
        self.catalog_repo = catalog_repo or EDI_CATALOG_ITEM_REPO
        self.transaction_repo = transaction_repo or EDI_TRANSACTION_REPO
        self.product_repo = product_repo or PRODUCT_T0001_REPO
        self.barcode_repo = barcode_repo or BARCODE_T0004_REPO
        self.price_list_repo = price_list_repo or PRICE_LIST_T0083_REPO
        self.price_list_item_repo = price_list_item_repo or PRICE_LIST_ITEM_T0084_REPO

    # -----------------------------------------------------------------------
    # 1. Product & SKU Matching
    # -----------------------------------------------------------------------

    def match_catalog_item(
        self,
        item: Union[EdiCatalogLine, Dict[str, Any]],
        partner_id: int,
        business_id: Optional[int] = None,
    ) -> Tuple[Optional[int], str]:
        """
        Attempt to resolve an incoming catalog item to an existing Nova product (T0001).
        Matching strategy hierarchy:
          1. Check active mapping in EDI SKU Matrix (T0125) for this partner by buyer_sku or GTIN.
          2. Check GTIN barcode in Barcodes (T0004) or Product Master (T0001).
          3. Check supplier_sku / vendor SKU against Product Master sku (T0001).
          4. Check buyer_sku against Product Master sku (T0001).
          5. Check exact match by Product Name in Product Master (T0001).
        Returns: (matched_product_id, match_source)
        """
        raw_buyer_sku = item.get("buyer_sku") if isinstance(item, dict) else getattr(item, "buyer_sku", None)
        raw_supplier_sku = item.get("supplier_sku") if isinstance(item, dict) else getattr(item, "supplier_sku", None)
        raw_gtin = item.get("gtin") if isinstance(item, dict) else getattr(item, "gtin", None)
        raw_product_name = item.get("product_name") if isinstance(item, dict) else getattr(item, "product_name", None)

        buyer_sku = str(raw_buyer_sku).strip() if raw_buyer_sku else ""
        supplier_sku = str(raw_supplier_sku).strip() if raw_supplier_sku else ""
        gtin = str(raw_gtin).strip() if raw_gtin else ""
        product_name = str(raw_product_name).strip() if raw_product_name else ""

        # Step 1: Check T0125 SKU Cross-Reference Matrix for partner
        try:
            mappings = self.sku_mapping_repo.list(
                filters={"partner_id": partner_id, "is_active": True},
                limit=1000,
            )
            for m in mappings:
                m_sku = str(m.get("partner_sku", "")).strip().upper()
                m_gtin = str(m.get("gtin", "")).strip().upper() if m.get("gtin") else ""
                if buyer_sku and m_sku == buyer_sku.upper():
                    return (m.get("product_id"), "CROSS_REFERENCE_MATRIX_T0125")
                if gtin and m_gtin and m_gtin == gtin.upper():
                    return (m.get("product_id"), "CROSS_REFERENCE_MATRIX_T0125")
        except Exception as e:
            logger.warning(f"Error querying SKU mapping repo: {e}")

        # Step 2: Check GTIN barcode in T0004 or T0001
        if gtin:
            try:
                b_records = self.barcode_repo.list(filters={"barcode": gtin}, limit=1)
                if b_records and b_records[0].get("product_id"):
                    return (b_records[0].get("product_id"), "PRODUCT_BARCODE_T0004")
            except Exception:
                pass

            try:
                p_records = self.product_repo.list(filters={"barcode": gtin}, limit=1)
                if p_records and p_records[0].get("id"):
                    return (p_records[0].get("id"), "PRODUCT_BARCODE_T0001")
            except Exception:
                pass

        # Step 3: Check supplier_sku in T0001
        if supplier_sku:
            try:
                p_records = self.product_repo.list(filters={"sku": supplier_sku}, limit=1)
                if p_records and p_records[0].get("id"):
                    return (p_records[0].get("id"), "PRODUCT_SKU_T0001")
            except Exception:
                pass

        # Step 4: Check buyer_sku in T0001
        if buyer_sku:
            try:
                p_records = self.product_repo.list(filters={"sku": buyer_sku}, limit=1)
                if p_records and p_records[0].get("id"):
                    return (p_records[0].get("id"), "PRODUCT_SKU_T0001")
            except Exception:
                pass

        # Step 5: Check exact product name match in T0001
        if product_name:
            try:
                p_records = self.product_repo.list(filters={"name": product_name}, limit=1)
                if p_records and p_records[0].get("id"):
                    return (p_records[0].get("id"), "PRODUCT_NAME_T0001")
            except Exception:
                pass

        return (None, "UNMATCHED")

    # -----------------------------------------------------------------------
    # 2. Catalog Synchronization Engine
    # -----------------------------------------------------------------------

    def sync_catalog(
        self,
        partner_id: int,
        catalog_code: str,
        items: List[Union[EdiCatalogLine, Dict[str, Any]]],
        auto_match_skus: bool = True,
        update_cross_reference_matrix: bool = True,
        business_id: Optional[int] = None,
    ) -> CatalogSyncResult:
        """
        Synchronize catalog items into table T0128.
        Detects price changes vs existing catalog versions, automatically resolves
        matched product IDs (T0001), and updates the EDI SKU Cross-Reference Matrix (T0125).
        """
        tenant_id = business_id or get_current_tenant()
        details: List[CatalogItemSyncDetail] = []
        errors: List[str] = []

        total_count = len(items)
        matched_count = 0
        unmatched_count = 0
        price_updated_count = 0

        existing_catalog_items_map: Dict[str, Dict[str, Any]] = {}
        try:
            existing_records = self.catalog_repo.list(
                filters={"partner_id": partner_id, "catalog_code": catalog_code},
                limit=5000,
            )
            for rec in existing_records:
                b_sku_key = str(rec.get("buyer_sku", "")).strip().upper()
                if b_sku_key:
                    existing_catalog_items_map[b_sku_key] = rec
        except Exception as e:
            logger.warning(f"Failed to fetch existing catalog items: {e}")

        for itm in items:
            itm_dict = itm if isinstance(itm, dict) else (itm.model_dump() if hasattr(itm, "model_dump") else itm.dict())
            buyer_sku = str(itm_dict.get("buyer_sku", "")).strip()
            supplier_sku = itm_dict.get("supplier_sku")
            gtin = itm_dict.get("gtin")
            prod_name = itm_dict.get("product_name") or buyer_sku
            prod_desc = itm_dict.get("product_description")
            category = itm_dict.get("category")
            brand = itm_dict.get("brand")
            uom = itm_dict.get("uom", "EA")
            pack_size = _parse_int(itm_dict.get("pack_size"), 1)
            list_price = _parse_float(itm_dict.get("list_price"), 0.0)
            currency = itm_dict.get("currency", "USD")
            eff_start = itm_dict.get("effective_start_date")
            eff_end = itm_dict.get("effective_end_date")

            matched_product_id = itm_dict.get("matched_product_id")
            match_source = "EXPLICIT"

            if auto_match_skus and not matched_product_id:
                matched_product_id, match_source = self.match_catalog_item(itm_dict, partner_id, tenant_id)

            sku_key = buyer_sku.upper()
            existing_record = existing_catalog_items_map.get(sku_key)
            old_price: Optional[float] = None
            price_changed = False

            if existing_record:
                old_price = _parse_float(existing_record.get("list_price"))
                if abs(old_price - list_price) > 0.0001:
                    price_changed = True

            if not matched_product_id:
                sync_status = EdiCatalogSyncStatus.UNMATCHED.value
                unmatched_count += 1
            elif price_changed:
                sync_status = EdiCatalogSyncStatus.PRICE_CHANGED.value
                price_updated_count += 1
                matched_count += 1
            else:
                sync_status = EdiCatalogSyncStatus.SYNCED.value
                matched_count += 1

            catalog_item_payload = {
                "partner_id": partner_id,
                "catalog_code": catalog_code,
                "buyer_sku": buyer_sku,
                "supplier_sku": supplier_sku,
                "gtin": gtin,
                "product_name": prod_name,
                "product_description": prod_desc,
                "category": category,
                "brand": brand,
                "uom": uom,
                "pack_size": pack_size,
                "list_price": list_price,
                "currency": currency,
                "effective_start_date": eff_start,
                "effective_end_date": eff_end,
                "matched_product_id": matched_product_id,
                "sync_status": sync_status,
                "is_active": True,
            }
            if tenant_id:
                catalog_item_payload["business_id"] = tenant_id

            cat_item_id = None
            try:
                if existing_record and existing_record.get("id"):
                    cat_item_id = existing_record.get("id")
                    self.catalog_repo.update(cat_item_id, catalog_item_payload)
                else:
                    new_rec = self.catalog_repo.create(catalog_item_payload)
                    cat_item_id = new_rec.get("id") if isinstance(new_rec, dict) else getattr(new_rec, "id", None)
            except Exception as e:
                err_msg = f"Failed to persist catalog item {buyer_sku}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

            sku_mapping_id = None
            if update_cross_reference_matrix and matched_product_id:
                try:
                    sku_mapping_id = self._sync_sku_matrix_mapping(
                        partner_id=partner_id,
                        product_id=matched_product_id,
                        buyer_sku=buyer_sku,
                        gtin=gtin,
                        uom=uom,
                        list_price=list_price,
                        tenant_id=tenant_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to update SKU matrix for {buyer_sku}: {e}")

            if matched_product_id and gtin:
                try:
                    self._ensure_gtin_barcode(
                        product_id=matched_product_id,
                        gtin=gtin,
                        tenant_id=tenant_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to link GTIN {gtin} in barcode repo: {e}")

            details.append(
                CatalogItemSyncDetail(
                    buyer_sku=buyer_sku,
                    supplier_sku=supplier_sku,
                    gtin=gtin,
                    product_name=prod_name,
                    matched_product_id=matched_product_id,
                    old_price=old_price,
                    new_price=list_price,
                    price_changed=price_changed,
                    sync_status=sync_status,
                    message=f"Match source: {match_source}" if matched_product_id else "No matching product found",
                    sku_mapping_id=sku_mapping_id,
                    catalog_item_id=cat_item_id,
                )
            )

        if unmatched_count == 0 and price_updated_count == 0:
            overall_status = "SYNCED"
        elif unmatched_count > 0 and matched_count > 0:
            overall_status = "PARTIALLY_SYNCED"
        elif price_updated_count > 0:
            overall_status = "PRICE_CHANGED"
        elif matched_count == 0 and unmatched_count > 0:
            overall_status = "UNMATCHED"
        else:
            overall_status = "SYNCED"

        return CatalogSyncResult(
            partner_id=partner_id,
            catalog_code=catalog_code,
            total_items=total_count,
            matched_items=matched_count,
            unmatched_items=unmatched_count,
            price_updated_items=price_updated_count,
            sync_status=overall_status,
            details=details,
            errors=errors,
        )

    def _sync_sku_matrix_mapping(
        self,
        partner_id: int,
        product_id: int,
        buyer_sku: str,
        gtin: Optional[str],
        uom: str,
        list_price: float,
        tenant_id: Optional[int] = None,
    ) -> Optional[int]:
        """Upsert a row in table T0125 for partner and buyer SKU."""
        try:
            existing = self.sku_mapping_repo.list(
                filters={"partner_id": partner_id, "partner_sku": buyer_sku},
                limit=1,
            )
            mapping_data = {
                "partner_id": partner_id,
                "product_id": product_id,
                "partner_sku": buyer_sku,
                "partner_sku_type": "BUYER_PART_NO",
                "gtin": gtin,
                "partner_uom": uom,
                "internal_uom": uom,
                "uom_conversion_factor": 1.0,
                "catalog_price": list_price,
                "is_active": True,
            }
            if tenant_id:
                mapping_data["business_id"] = tenant_id

            if existing and existing[0].get("id"):
                mapping_id = existing[0].get("id")
                self.sku_mapping_repo.update(mapping_id, mapping_data)
                return mapping_id
            else:
                created = self.sku_mapping_repo.create(mapping_data)
                return created.get("id") if isinstance(created, dict) else getattr(created, "id", None)
        except Exception as e:
            logger.error(f"Error upserting SKU matrix: {e}")
            return None

    def _ensure_gtin_barcode(
        self,
        product_id: int,
        gtin: str,
        tenant_id: Optional[int] = None,
    ) -> None:
        """Ensure the GTIN barcode is linked to the product in T0004."""
        try:
            existing = self.barcode_repo.list(
                filters={"product_id": product_id, "barcode": gtin},
                limit=1,
            )
            if not existing:
                b_payload = {
                    "product_id": product_id,
                    "barcode": gtin,
                    "barcode_type": "GTIN",
                    "is_primary": False,
                }
                if tenant_id:
                    b_payload["business_id"] = tenant_id
                self.barcode_repo.create(b_payload)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # 3. Outbound Catalog Export Engine
    # -----------------------------------------------------------------------

    def export_catalog_edi(
        self,
        partner_id: int,
        catalog_code: str,
        format_override: Optional[str] = None,
        items_override: Optional[List[Dict[str, Any]]] = None,
        price_list_id: Optional[int] = None,
        control_number: Optional[str] = None,
        log_transaction: bool = True,
        business_id: Optional[int] = None,
    ) -> CatalogExportResult:
        """
        Generate and export an outbound EDI catalog document (ANSI X12 832 or UN/EDIFACT PRICAT).
        Extracts items from T0128 or price list T0084 / product catalog T0001,
        builds standard-compliant EDI text, and records transaction in T0126.
        """
        tenant_id = business_id or get_current_tenant()

        partner_rec = self.partner_repo.get(partner_id)
        if not partner_rec:
            raise ValueError(f"Trading partner #{partner_id} not found in T0124")

        standard = format_override or partner_rec.get("edi_standard", "ANSI_X12")
        delims = EdiDelimiters.from_partner(partner_rec)

        items: List[Dict[str, Any]] = []
        if items_override:
            items = items_override
        else:
            catalog_items = self.catalog_repo.list(
                filters={"partner_id": partner_id, "catalog_code": catalog_code, "is_active": True},
                limit=5000,
            )
            if catalog_items:
                items = catalog_items
            elif price_list_id:
                pli_records = self.price_list_item_repo.list(
                    filters={"price_list_id": price_list_id, "is_active": True},
                    limit=5000,
                )
                for pli in pli_records:
                    prod_id = pli.get("product_id")
                    prod = self.product_repo.get(prod_id) if prod_id else {}
                    items.append({
                        "buyer_sku": prod.get("sku") or f"PROD-{prod_id}",
                        "supplier_sku": prod.get("sku"),
                        "gtin": prod.get("barcode"),
                        "product_name": prod.get("name") or "Product Item",
                        "uom": "EA",
                        "pack_size": 1,
                        "list_price": _parse_float(pli.get("price")),
                        "category": prod.get("category"),
                        "brand": prod.get("brand"),
                    })
            else:
                products = self.product_repo.list(filters={"is_active": True}, limit=500)
                for prod in products:
                    items.append({
                        "buyer_sku": prod.get("sku") or f"PROD-{prod.get('id')}",
                        "supplier_sku": prod.get("sku"),
                        "gtin": prod.get("barcode"),
                        "product_name": prod.get("name") or "Product Item",
                        "uom": "EA",
                        "pack_size": 1,
                        "list_price": _parse_float(prod.get("price")),
                        "category": prod.get("category"),
                        "brand": prod.get("brand"),
                    })

        ctrl_num = control_number
        if not ctrl_num:
            conn = get_connection()
            try:
                seq_val = _fetch_nextval(conn, "seq_edi_control_num")
                ctrl_num = str(seq_val).zfill(9) if seq_val else str(uuid.uuid4().int)[:9]
            finally:
                release_connection(conn)

        doc_type = "832" if str(standard).upper() == "ANSI_X12" else "PRICAT"

        if str(standard).upper() == "EDIFACT":
            edi_payload = generate_edifact_pricat(
                partner=partner_rec,
                catalog_code=catalog_code,
                items=items,
                control_number=ctrl_num,
                currency="USD",
                delimiters=delims,
            )
        else:
            edi_payload = generate_x12_832(
                partner=partner_rec,
                catalog_code=catalog_code,
                items=items,
                control_number=ctrl_num,
                currency="USD",
                delimiters=delims,
            )

        if log_transaction:
            try:
                tx_num = f"TX-CAT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
                tx_data = {
                    "transaction_number": tx_num,
                    "partner_id": partner_id,
                    "standard": str(standard).upper(),
                    "document_type": doc_type,
                    "direction": EdiDirection.OUTBOUND.value,
                    "control_number": ctrl_num,
                    "status": EdiTransactionStatus.PROCESSED.value,
                    "raw_payload": edi_payload,
                    "parsed_data": {
                        "catalog_code": catalog_code,
                        "total_items": len(items),
                    },
                    "processed_at": datetime.now(timezone.utc),
                }
                if tenant_id:
                    tx_data["business_id"] = tenant_id
                self.transaction_repo.create(tx_data)
            except Exception as e:
                logger.warning(f"Failed to record outbound catalog transaction log: {e}")

        return CatalogExportResult(
            partner_id=partner_id,
            catalog_code=catalog_code,
            control_number=ctrl_num,
            standard=str(standard).upper(),
            document_type=doc_type,
            total_items=len(items),
            edi_payload=edi_payload,
        )

    # -----------------------------------------------------------------------
    # 4. Inbound EDI Document Ingestion Pipeline
    # -----------------------------------------------------------------------

    def ingest_catalog_document(
        self,
        payload: str,
        partner_id: Optional[int] = None,
        standard: Optional[str] = None,
        auto_match_skus: bool = True,
        update_cross_reference_matrix: bool = True,
        business_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ingest an inbound EDI 832 / PRICAT document.
        Parses interchange, resolves trading partner, synchronizes catalog items into T0128,
        updates SKU matrix T0125, and records an audit log transaction in T0126.
        """
        tenant_id = business_id or get_current_tenant()
        now = datetime.now(timezone.utc)

        parsed = parse_inbound_catalog_edi(payload, standard=standard)

        resolved_partner_id = partner_id
        if not resolved_partner_id:
            sender_id = parsed.header.partner_code or parsed.header.buyer_code
            if sender_id:
                try:
                    candidates = self.partner_repo.list(limit=500)
                    for p in candidates:
                        p_sender = str(p.get("interchange_sender_id", "")).strip().upper()
                        p_code = str(p.get("partner_code", "")).strip().upper()
                        if sender_id.upper() in (p_sender, p_code):
                            resolved_partner_id = p.get("id")
                            break
                except Exception as e:
                    logger.warning(f"Error querying partner for catalog ingestion: {e}")

        if not resolved_partner_id:
            try:
                partners = self.partner_repo.list(limit=1)
                if partners:
                    resolved_partner_id = partners[0].get("id")
            except Exception:
                pass

        if not resolved_partner_id:
            resolved_partner_id = 1

        sync_result = self.sync_catalog(
            partner_id=resolved_partner_id,
            catalog_code=parsed.header.catalog_code,
            items=parsed.items,
            auto_match_skus=auto_match_skus,
            update_cross_reference_matrix=update_cross_reference_matrix,
            business_id=tenant_id,
        )

        tx_number = f"TX-CAT-IN-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        doc_type = "832" if parsed.standard == "ANSI_X12" else "PRICAT"
        tx_id = None

        try:
            tx_data = {
                "transaction_number": tx_number,
                "partner_id": resolved_partner_id,
                "standard": parsed.standard,
                "document_type": doc_type,
                "direction": EdiDirection.INBOUND.value,
                "control_number": parsed.control_number,
                "status": EdiTransactionStatus.PROCESSED.value if not sync_result.errors else EdiTransactionStatus.FAILED.value,
                "raw_payload": payload,
                "parsed_data": {
                    "catalog_code": parsed.header.catalog_code,
                    "catalog_name": parsed.header.catalog_name,
                    "currency": parsed.header.currency,
                    "total_items": sync_result.total_items,
                    "matched_items": sync_result.matched_items,
                    "unmatched_items": sync_result.unmatched_items,
                    "price_updated_items": sync_result.price_updated_items,
                    "sync_status": sync_result.sync_status,
                },
                "processed_at": now,
            }
            if tenant_id:
                tx_data["business_id"] = tenant_id
            created_tx = self.transaction_repo.create(tx_data)
            tx_id = created_tx.get("id") if isinstance(created_tx, dict) else getattr(created_tx, "id", None)
        except Exception as e:
            logger.error(f"Failed to record inbound catalog transaction log: {e}")

        result_dict = sync_result.model_dump() if hasattr(sync_result, "model_dump") else sync_result.dict()

        return {
            "transaction_id": tx_id,
            "transaction_number": tx_number,
            "partner_id": resolved_partner_id,
            "catalog_code": parsed.header.catalog_code,
            "standard": parsed.standard,
            "document_type": doc_type,
            "control_number": parsed.control_number,
            "sync_result": result_dict,
            "errors": sync_result.errors,
        }

    def export_catalog(
        self,
        partner_id: int,
        standard: Optional[str] = None,
        catalog_code: Optional[str] = None,
        category: Optional[str] = None,
        currency: str = "USD",
        price_list_id: Optional[int] = None,
        items_override: Optional[List[Dict[str, Any]]] = None,
        control_number: Optional[str] = None,
        log_transaction: bool = True,
        business_id: Optional[int] = None,
    ) -> CatalogExportResult:
        """Alias and flexible wrapper for export_catalog_edi."""
        cat_code = catalog_code or f"CAT-{partner_id}"
        return self.export_catalog_edi(
            partner_id=partner_id,
            catalog_code=cat_code,
            format_override=standard,
            items_override=items_override,
            price_list_id=price_list_id,
            control_number=control_number,
            log_transaction=log_transaction,
            business_id=business_id,
        )


# Singleton instance
edi_catalog_service = EdiCatalogService()

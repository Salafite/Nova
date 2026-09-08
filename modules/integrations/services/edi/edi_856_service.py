"""
Nova ERP — Outbound EDI 856 (Advance Shipping Notice / ASN) & UN/EDIFACT DESADV Generator
Constructs Hierarchical Level (HL) structures (Shipment -> Order -> Tare/Pallet SSCC -> Pack -> Item)
with SSCC-18 barcodes, batch numbers (T0102), expiry dates, carrier details, and truck dispatch info.
Supports both ANSI X12 856 and UN/EDIFACT DESADV document formats.
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
    EdiDirection,
    EdiAsnGenerateRequest,
    EdiAsnGenerateResponse,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_TRANSACTION_REPO,
    EDI_SSCC_PALLET_REPO,
)
from modules.integrations.services.edi.edi_core import (
    EdiDelimiters,
    EdiSegment,
    EdiTransactionSet,
    EdiFunctionalGroup,
    EdiInterchange,
    detect_edi_standard,
    parse_x12,
    parse_edifact,
    parse_edi,
    serialize_x12,
    serialize_edifact,
    serialize_edi,
    X12Builder,
    EdifactBuilder,
    EdiSyntaxError,
)
from modules.integrations.services.edi.sscc_service import (
    PackagingHierarchy,
    PackagingPallet,
    PackagingBox,
    PackagingItem,
    SsccService,
    sscc_service,
    generate_sscc18,
    parse_sscc_gs1_128,
    validate_sscc,
    format_sscc_gs1_128,
    DEFAULT_GS1_COMPANY_PREFIX,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Repositories for Deliveries, Sales Orders, Pick Lists, and Customers
# ---------------------------------------------------------------------------

DELIVERY_T0077_REPO = CrudRepository(
    'T0077',
    business_columns=[
        'id', 'delivery_number', 'sales_order_id', 'delivery_date', 'warehouse_id',
        'freight_cost', 'delivery_route', 'actual_delivery_date', 'status', 'notes',
        'recipient_signature', 'delivery_photo_url', 'pod_timestamp', 'delivery_location',
        'payment_status', 'cod_cash_amount', 'cod_check_amount', 'cod_check_number',
        'cod_check_bank', 'driver_id',
    ],
)

DELIVERY_LINE_T0078_REPO = CrudRepository(
    'T0078',
    business_columns=[
        'id', 'delivery_id', 'sales_order_line_id', 'product_id',
        'product_name', 'qty_shipped', 'qty_ordered', 'uom_id', 'line_number',
    ],
)

SALES_ORDER_T0012_REPO = CrudRepository(
    'T0012',
    business_columns=[
        'id', 'order_number', 'customer_id', 'warehouse_id', 'subtotal',
        'tax', 'grand_total', 'freight_amount', 'discount_amount',
        'sales_rep_id', 'status', 'order_date', 'notes', 'price_list_id',
        'tax_rate_id', 'payment_term_id', 'client_order_uuid',
    ],
)

SALES_LINE_T0013_REPO = CrudRepository(
    'T0013',
    business_columns=[
        'id', 'sales_order_id', 'product_id', 'product_name', 'uom_id',
        'qty', 'unit_price', 'cost_price', 'discount', 'line_total',
        'line_number',
    ],
)

PICK_LIST_ITEM_T0102_REPO = CrudRepository(
    'T0102',
    business_columns=[
        'id', 'pick_list_id', 'sales_order_line_id', 'product_id', 'product_name',
        'qty_ordered', 'qty_picked', 'line_number', 'batch_id', 'batch_number',
        'expiry_date', 'picked_batch_id', 'picked_batch_number',
    ],
)

CUSTOMER_T0010_REPO = CrudRepository(
    'T0010',
    business_columns=[
        'id', 'name', 'group_name', 'phone', 'email', 'credit_limit',
        'balance', 'is_active', 'default_price_list_id', 'default_tax_rate_id',
    ],
)

PRODUCT_T0001_REPO = CrudRepository(
    'T0001',
    business_columns=[
        'id', 'sku', 'name', 'description', 'category_id', 'brand_id',
        'uom_id', 'price', 'cost', 'barcode', 'is_active',
    ],
)


# ---------------------------------------------------------------------------
# Sequence Helper
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
# Domain Models for ASN & DESADV Generation and Parsing
# ---------------------------------------------------------------------------

class EdiAsnShipmentHeader(BaseModel):
    """Header data for an EDI 856 ASN or UN/EDIFACT DESADV message."""
    delivery_id: Optional[int] = None
    delivery_number: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = None
    buyer_po_number: Optional[str] = None
    ship_date: Optional[date] = None
    ship_time: Optional[str] = None
    estimated_delivery_date: Optional[date] = None
    carrier_name: Optional[str] = None
    carrier_code: Optional[str] = None  # Standard SCAC or carrier code
    tracking_number: Optional[str] = None  # Bill of Lading (BOL) or tracking reference
    vehicle_number: Optional[str] = None  # Truck / Trailer license plate
    seal_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_id: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = None
    total_pallets: int = 0
    total_boxes: int = 0
    total_units: int = 0
    ship_from_name: Optional[str] = None
    ship_from_id: Optional[str] = None
    ship_from_address: Optional[str] = None
    ship_from_city: Optional[str] = None
    ship_from_country: Optional[str] = None
    ship_to_name: Optional[str] = None
    ship_to_id: Optional[str] = None
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_country: Optional[str] = None
    ship_to_store_number: Optional[str] = None


class EdiAsnItemDetail(BaseModel):
    """Line item detail within a packaging unit or shipment."""
    line_number: int = 1
    product_id: Optional[int] = None
    sku: str
    buyer_sku: Optional[str] = None
    vendor_sku: Optional[str] = None
    gtin: Optional[str] = None
    product_name: Optional[str] = None
    qty_shipped: float = 1.0
    qty_ordered: Optional[float] = None
    uom: str = "EA"
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    manufacturing_date: Optional[date] = None
    serial_numbers: List[str] = Field(default_factory=list)
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None


class EdiAsnBoxDetail(BaseModel):
    """Box / Carton sub-packaging container on a pallet."""
    box_number: Optional[str] = None
    sscc_barcode: Optional[str] = None
    package_type: str = "BOX"
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = 0.5
    volume_cbm: Optional[float] = None
    items: List[EdiAsnItemDetail] = Field(default_factory=list)


class EdiAsnPalletDetail(BaseModel):
    """Pallet-level packaging container with SSCC-18 identifier."""
    pallet_id: Optional[int] = None
    pallet_number: Optional[str] = None
    sscc_barcode: str
    sscc_gs1_128: Optional[str] = None
    package_type: str = "PALLET"
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = 25.0
    volume_cbm: Optional[float] = None
    boxes: List[EdiAsnBoxDetail] = Field(default_factory=list)
    direct_items: List[EdiAsnItemDetail] = Field(default_factory=list)

    def total_units(self) -> int:
        box_u = sum(int(it.qty_shipped) for b in self.boxes for it in b.items)
        direct_u = sum(int(it.qty_shipped) for it in self.direct_items)
        return box_u + direct_u


class EdiAsnDocument(BaseModel):
    """Complete structured ASN / DESADV document object."""
    standard: str = "ANSI_X12"
    document_type: str = "856"
    control_number: str = "1"
    sender_id: str = ""
    sender_qualifier: str = "ZZ"
    receiver_id: str = ""
    receiver_qualifier: str = "ZZ"
    is_test: bool = False
    header: EdiAsnShipmentHeader
    pallets: List[EdiAsnPalletDetail] = Field(default_factory=list)
    direct_items: List[EdiAsnItemDetail] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ANSI X12 856 ASN Builder
# ---------------------------------------------------------------------------

def generate_x12_856(
    asn_doc: EdiAsnDocument,
    delimiters: Optional[EdiDelimiters] = None,
    partner: Optional[Any] = None,
) -> str:
    """
    Constructs an ANSI X12 856 (Shipment Notice / Manifest) interchange document
    following standard 5-level or 4-level Hierarchical Level (HL) structure:
      HL 1: Shipment (S)
      HL 2: Order (O)
      HL 3: Tare / Pallet (T) with SSCC-18 (MAN*GM)
      HL 4: Pack / Box (P)
      HL 5: Item (I) with LIN, SN1, PID, DTM (036), REF (LT)
    """
    delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else EdiDelimiters.x12_default())
    header = asn_doc.header

    builder = X12Builder(
        sender_id=asn_doc.sender_id or "NOVAERP",
        receiver_id=asn_doc.receiver_id or "RETAILHUB",
        sender_qualifier=asn_doc.sender_qualifier or "ZZ",
        receiver_qualifier=asn_doc.receiver_qualifier or "ZZ",
        control_number=asn_doc.control_number or "1",
        is_test=asn_doc.is_test,
        delimiters=delims,
    )

    builder.start_group(
        functional_code="SH",
        group_control_number=asn_doc.control_number or "1",
        version="004010",
    )

    builder.start_transaction(
        doc_type="856",
        control_number=str(asn_doc.control_number or "0001").zfill(4)[-4:],
    )

    now = datetime.now(timezone.utc)
    ship_date_str = header.ship_date.strftime("%Y%m%d") if header.ship_date else now.strftime("%Y%m%d")
    ship_time_str = header.ship_time or now.strftime("%H%M")
    shipment_id = header.delivery_number or (f"SHP-{header.delivery_id}" if header.delivery_id else "SHP-001")

    builder.add_segment("BSN", "00", shipment_id, ship_date_str, ship_time_str, "0001")

    builder.add_segment("DTM", "011", ship_date_str)
    if header.estimated_delivery_date:
        est_del_str = header.estimated_delivery_date.strftime("%Y%m%d")
        builder.add_segment("DTM", "017", est_del_str)

    hl_counter = 1
    total_units = 0

    # HL Level 1: Shipment (S)
    shipment_hl_id = hl_counter
    builder.add_segment("HL", str(shipment_hl_id), "", "S")
    hl_counter += 1

    pallet_count = header.total_pallets or len(asn_doc.pallets)
    if pallet_count > 0:
        builder.add_segment("TD1", "PLT90", str(pallet_count))
    elif header.total_boxes > 0:
        builder.add_segment("TD1", "CTN25", str(header.total_boxes))

    carrier_scac = (header.carrier_code or "FDEG")[:4]
    carrier_name = header.carrier_name or "Nova Logistics Fleet"
    builder.add_segment("TD5", "B", "2", carrier_scac, "M", carrier_name)

    if header.vehicle_number:
        builder.add_segment("TD3", "TL", "", header.vehicle_number)

    if header.tracking_number:
        builder.add_segment("REF", "BM", header.tracking_number)
    if header.seal_number:
        builder.add_segment("REF", "CN", header.seal_number)
    if header.delivery_number:
        builder.add_segment("REF", "SI", header.delivery_number)

    sf_id = header.ship_from_id or asn_doc.sender_id or "NOVA-HQ"
    sf_name = header.ship_from_name or "Nova Distribution Warehouse"
    builder.add_segment("N1", "SF", sf_name, "92", sf_id)

    st_id = header.ship_to_id or header.ship_to_store_number or asn_doc.receiver_id or "RETAIL-DC"
    st_name = header.ship_to_name or "Retail Distribution Center"
    builder.add_segment("N1", "ST", st_name, "92", st_id)

    # HL Level 2: Order (O)
    order_hl_id = hl_counter
    builder.add_segment("HL", str(order_hl_id), str(shipment_hl_id), "O")
    hl_counter += 1

    po_num = header.buyer_po_number or "PO-UNSPECIFIED"
    builder.add_segment("PRF", po_num)

    if header.sales_order_number:
        builder.add_segment("REF", "SO", header.sales_order_number)
    elif header.sales_order_id:
        builder.add_segment("REF", "SO", f"SO-{header.sales_order_id}")

    # HL Level 3+: Pallets (T), Boxes (P), and Items (I)
    if asn_doc.pallets:
        for pallet in asn_doc.pallets:
            pallet_hl_id = hl_counter
            builder.add_segment("HL", str(pallet_hl_id), str(order_hl_id), "T")
            hl_counter += 1

            clean_sscc = parse_sscc_gs1_128(pallet.sscc_barcode)
            formatted_sscc = f"00{clean_sscc}" if len(clean_sscc) == 18 else clean_sscc
            builder.add_segment("MAN", "GM", formatted_sscc)

            if pallet.gross_weight_kg is not None:
                builder.add_segment("MEA", "PD", "G", str(round(pallet.gross_weight_kg, 2)), "KG")
            if pallet.net_weight_kg is not None:
                builder.add_segment("MEA", "PD", "N", str(round(pallet.net_weight_kg, 2)), "KG")

            if pallet.boxes:
                for box in pallet.boxes:
                    box_hl_id = hl_counter
                    builder.add_segment("HL", str(box_hl_id), str(pallet_hl_id), "P")
                    hl_counter += 1

                    box_id_or_sscc = box.sscc_barcode or box.box_number or "BOX-1"
                    builder.add_segment("MAN", "GM", box_id_or_sscc)
                    if box.gross_weight_kg is not None:
                        builder.add_segment("MEA", "PD", "G", str(round(box.gross_weight_kg, 2)), "KG")

                    for item in box.items:
                        item_hl_id = hl_counter
                        builder.add_segment("HL", str(item_hl_id), str(box_hl_id), "I")
                        hl_counter += 1
                        total_units += int(item.qty_shipped)

                        lin_elements = [str(item.line_number)]
                        if item.buyer_sku:
                            lin_elements.extend(["BP", item.buyer_sku])
                        if item.vendor_sku:
                            lin_elements.extend(["VP", item.vendor_sku])
                        elif item.sku and not item.buyer_sku:
                            lin_elements.extend(["IN", item.sku])
                        if item.gtin:
                            lin_elements.extend(["UP", item.gtin])
                        builder.add_segment("LIN", *lin_elements)

                        builder.add_segment("SN1", str(item.line_number), str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "EA")

                        if item.product_name:
                            builder.add_segment("PID", "F", "", "", "", item.product_name)

                        if item.expiry_date:
                            builder.add_segment("DTM", "036", item.expiry_date.strftime("%Y%m%d"))

                        if item.batch_number:
                            builder.add_segment("REF", "LT", item.batch_number)

            if pallet.direct_items:
                for item in pallet.direct_items:
                    item_hl_id = hl_counter
                    builder.add_segment("HL", str(item_hl_id), str(pallet_hl_id), "I")
                    hl_counter += 1
                    total_units += int(item.qty_shipped)

                    lin_elements = [str(item.line_number)]
                    if item.buyer_sku:
                        lin_elements.extend(["BP", item.buyer_sku])
                    if item.vendor_sku:
                        lin_elements.extend(["VP", item.vendor_sku])
                    elif item.sku and not item.buyer_sku:
                        lin_elements.extend(["IN", item.sku])
                    if item.gtin:
                        lin_elements.extend(["UP", item.gtin])
                    builder.add_segment("LIN", *lin_elements)

                    builder.add_segment("SN1", str(item.line_number), str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "EA")

                    if item.product_name:
                        builder.add_segment("PID", "F", "", "", "", item.product_name)

                    if item.expiry_date:
                        builder.add_segment("DTM", "036", item.expiry_date.strftime("%Y%m%d"))

                    if item.batch_number:
                        builder.add_segment("REF", "LT", item.batch_number)

    elif asn_doc.direct_items:
        for item in asn_doc.direct_items:
            item_hl_id = hl_counter
            builder.add_segment("HL", str(item_hl_id), str(order_hl_id), "I")
            hl_counter += 1
            total_units += int(item.qty_shipped)

            lin_elements = [str(item.line_number)]
            if item.buyer_sku:
                lin_elements.extend(["BP", item.buyer_sku])
            if item.vendor_sku:
                lin_elements.extend(["VP", item.vendor_sku])
            elif item.sku and not item.buyer_sku:
                lin_elements.extend(["IN", item.sku])
            if item.gtin:
                lin_elements.extend(["UP", item.gtin])
            builder.add_segment("LIN", *lin_elements)

            builder.add_segment("SN1", str(item.line_number), str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "EA")
            if item.product_name:
                builder.add_segment("PID", "F", "", "", "", item.product_name)
            if item.expiry_date:
                builder.add_segment("DTM", "036", item.expiry_date.strftime("%Y%m%d"))
            if item.batch_number:
                builder.add_segment("REF", "LT", item.batch_number)

    # 4. CTT Segment (Transaction Totals)
    total_hl_count = hl_counter - 1
    builder.add_segment("CTT", str(total_hl_count), str(total_units))

    builder.end_transaction()
    builder.end_group()

    return builder.build(line_breaks=True)


# ---------------------------------------------------------------------------
# UN/EDIFACT DESADV Builder
# ---------------------------------------------------------------------------

def generate_edifact_desadv(
    asn_doc: EdiAsnDocument,
    delimiters: Optional[EdiDelimiters] = None,
    partner: Optional[Any] = None,
) -> str:
    """
    Constructs a UN/EDIFACT DESADV (Despatch Advice) interchange document
    following standard CPS (Consignment Packing Sequence) packaging hierarchy:
      CPS 1: Outer / Shipment level
      CPS 2: Pallet / SSCC-18 packaging level (PAC + PCI + GIN)
      CPS 3: Box / Item detail levels (LIN + PIA + IMD + QTY + DTM + GIR)
    """
    delims = delimiters or (EdiDelimiters.from_partner(partner) if partner else EdiDelimiters.edifact_default())
    header = asn_doc.header

    builder = EdifactBuilder(
        sender_id=asn_doc.sender_id or "NOVAERP",
        receiver_id=asn_doc.receiver_id or "RETAILHUB",
        sender_qualifier=asn_doc.sender_qualifier or "ZZ",
        receiver_qualifier=asn_doc.receiver_qualifier or "ZZ",
        control_number=asn_doc.control_number or "1",
        is_test=asn_doc.is_test,
        delimiters=delims,
        include_una=False,
    )

    builder.start_message(
        doc_type="DESADV",
        control_number=str(asn_doc.control_number or "1"),
    )

    despatch_num = header.delivery_number or (f"DES-{header.delivery_id}" if header.delivery_id else "DES-001")
    builder.add_segment("BGM", "351", despatch_num, "9")

    now = datetime.now(timezone.utc)
    doc_dt_str = now.strftime("%Y%m%d%H%M")
    builder.add_segment("DTM", ["137", doc_dt_str, "203"])

    ship_date_str = header.ship_date.strftime("%Y%m%d") if header.ship_date else now.strftime("%Y%m%d")
    builder.add_segment("DTM", ["11", ship_date_str, "102"])

    if header.buyer_po_number:
        builder.add_segment("RFF", ["ON", header.buyer_po_number])
    if header.delivery_number:
        builder.add_segment("RFF", ["DQ", header.delivery_number])
    if header.tracking_number:
        builder.add_segment("RFF", ["AAS", header.tracking_number])

    sf_id = header.ship_from_id or asn_doc.sender_id or "NOVA-HQ"
    sf_name = header.ship_from_name or "Nova Distribution Warehouse"
    builder.add_segment("NAD", "CZ", [sf_id, "", "92"], "", sf_name)

    st_id = header.ship_to_id or header.ship_to_store_number or asn_doc.receiver_id or "RETAIL-DC"
    st_name = header.ship_to_name or "Retail Distribution Center"
    builder.add_segment("NAD", "CN", [st_id, "", "92"], "", st_name)

    if header.carrier_name or header.carrier_code:
        c_code = header.carrier_code or "CA01"
        c_name = header.carrier_name or "Carrier Express"
        builder.add_segment("NAD", "CA", [c_code, "", "92"], "", c_name)

    if header.vehicle_number or header.carrier_name:
        builder.add_segment("TDT", "20", "", "30", "31", header.carrier_name or "", "", "", header.vehicle_number or "")

    cps_counter = 1
    total_lines = 0

    shipment_cps = cps_counter
    builder.add_segment("CPS", str(shipment_cps))
    cps_counter += 1

    if asn_doc.pallets:
        for pallet in asn_doc.pallets:
            pallet_cps = cps_counter
            builder.add_segment("CPS", str(pallet_cps), str(shipment_cps))
            cps_counter += 1

            builder.add_segment("PAC", "1", "", "201")

            if pallet.gross_weight_kg is not None:
                builder.add_segment("MEA", "WT", "G", ["KGM", str(round(pallet.gross_weight_kg, 2))])
            if pallet.net_weight_kg is not None:
                builder.add_segment("MEA", "WT", "N", ["KGM", str(round(pallet.net_weight_kg, 2))])

            clean_sscc = parse_sscc_gs1_128(pallet.sscc_barcode)
            builder.add_segment("PCI", "33E")
            builder.add_segment("GIN", "ML", clean_sscc)

            if pallet.boxes:
                for box in pallet.boxes:
                    box_cps = cps_counter
                    builder.add_segment("CPS", str(box_cps), str(pallet_cps))
                    cps_counter += 1

                    builder.add_segment("PAC", "1", "", "CT")
                    if box.gross_weight_kg is not None:
                        builder.add_segment("MEA", "WT", "G", ["KGM", str(round(box.gross_weight_kg, 2))])

                    for item in box.items:
                        item_cps = cps_counter
                        builder.add_segment("CPS", str(item_cps), str(box_cps))
                        cps_counter += 1
                        total_lines += 1

                        item_code = item.gtin or item.sku
                        builder.add_segment("LIN", str(item.line_number), "", [item_code, "SRV"])

                        if item.buyer_sku:
                            builder.add_segment("PIA", "1", [item.buyer_sku, "IN"])

                        if item.product_name:
                            builder.add_segment("IMD", "F", "", ["", "", "", item.product_name])

                        builder.add_segment("QTY", ["12", str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "PCE"])

                        if item.expiry_date:
                            builder.add_segment("DTM", ["361", item.expiry_date.strftime("%Y%m%d"), "102"])

                        if item.batch_number:
                            builder.add_segment("GIR", "3", [item.batch_number, "BX"])

            if pallet.direct_items:
                for item in pallet.direct_items:
                    item_cps = cps_counter
                    builder.add_segment("CPS", str(item_cps), str(pallet_cps))
                    cps_counter += 1
                    total_lines += 1

                    item_code = item.gtin or item.sku
                    builder.add_segment("LIN", str(item.line_number), "", [item_code, "SRV"])
                    if item.buyer_sku:
                        builder.add_segment("PIA", "1", [item.buyer_sku, "IN"])
                    if item.product_name:
                        builder.add_segment("IMD", "F", "", ["", "", "", item.product_name])

                    builder.add_segment("QTY", ["12", str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "PCE"])
                    if item.expiry_date:
                        builder.add_segment("DTM", ["361", item.expiry_date.strftime("%Y%m%d"), "102"])
                    if item.batch_number:
                        builder.add_segment("GIR", "3", [item.batch_number, "BX"])

    elif asn_doc.direct_items:
        for item in asn_doc.direct_items:
            item_cps = cps_counter
            builder.add_segment("CPS", str(item_cps), str(shipment_cps))
            cps_counter += 1
            total_lines += 1

            item_code = item.gtin or item.sku
            builder.add_segment("LIN", str(item.line_number), "", [item_code, "SRV"])
            if item.buyer_sku:
                builder.add_segment("PIA", "1", [item.buyer_sku, "IN"])
            if item.product_name:
                builder.add_segment("IMD", "F", "", ["", "", "", item.product_name])
            builder.add_segment("QTY", ["12", str(int(item.qty_shipped) if item.qty_shipped.is_integer() else item.qty_shipped), item.uom or "PCE"])
            if item.expiry_date:
                builder.add_segment("DTM", ["361", item.expiry_date.strftime("%Y%m%d"), "102"])
            if item.batch_number:
                builder.add_segment("GIR", "3", [item.batch_number, "BX"])

    builder.add_segment("CNT", ["2", str(total_lines)])

    builder.end_message()

    return builder.build(line_breaks=True)


# ---------------------------------------------------------------------------
# Inbound Parsers for ANSI X12 856 & UN/EDIFACT DESADV
# ---------------------------------------------------------------------------

def parse_x12_856(
    raw_content: str,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiAsnDocument:
    """
    Parses an inbound or outbound ANSI X12 856 Shipment Notice / Manifest into an EdiAsnDocument model.
    """
    interchange = parse_x12(raw_content, delimiters)
    tx_sets = interchange.all_transactions()
    if not tx_sets:
        raise EdiSyntaxError("No transaction sets found in ANSI X12 856 message")

    tx = tx_sets[0]
    segments = tx.segments

    header = EdiAsnShipmentHeader()
    pallets: List[EdiAsnPalletDetail] = []
    direct_items: List[EdiAsnItemDetail] = []

    current_hl_type = ""
    current_pallet: Optional[EdiAsnPalletDetail] = None
    current_box: Optional[EdiAsnBoxDetail] = None
    current_item: Optional[EdiAsnItemDetail] = None
    line_seq = 1

    for seg in segments:
        tag = seg.tag

        if tag == "BSN":
            header.delivery_number = seg.get(2)
            raw_date = seg.get(3)
            if raw_date and len(raw_date) == 8 and raw_date.isdigit():
                try:
                    header.ship_date = date(int(raw_date[0:4]), int(raw_date[4:6]), int(raw_date[6:8]))
                except Exception:
                    pass
            header.ship_time = seg.get(4)

        elif tag == "DTM":
            qual = seg.get(1)
            raw_dt = seg.get(2)
            if raw_dt and len(raw_dt) >= 8 and raw_dt[:8].isdigit():
                try:
                    parsed_dt = date(int(raw_dt[0:4]), int(raw_dt[4:6]), int(raw_dt[6:8]))
                    if qual == "011":
                        header.ship_date = parsed_dt
                    elif qual == "017":
                        header.estimated_delivery_date = parsed_dt
                    elif qual == "036" and current_item:
                        current_item.expiry_date = parsed_dt
                except Exception:
                    pass

        elif tag == "TD1":
            try:
                cnt = int(seg.get(2, "0"))
                if "PLT" in seg.get(1):
                    header.total_pallets = cnt
                elif "CTN" in seg.get(1):
                    header.total_boxes = cnt
            except Exception:
                pass

        elif tag == "TD5":
            header.carrier_code = seg.get(3)
            header.carrier_name = seg.get(5) or seg.get(4)

        elif tag == "TD3":
            header.vehicle_number = seg.get(3) or seg.get(2)

        elif tag == "REF":
            ref_qual = seg.get(1)
            ref_val = seg.get(2)
            if ref_qual == "BM":
                header.tracking_number = ref_val
            elif ref_qual == "CN":
                header.seal_number = ref_val
            elif ref_qual == "SO":
                header.sales_order_number = ref_val
            elif ref_qual == "LT" and current_item:
                current_item.batch_number = ref_val

        elif tag == "N1":
            n1_qual = seg.get(1)
            n1_name = seg.get(2)
            n1_id = seg.get(4)
            if n1_qual == "SF":
                header.ship_from_name = n1_name
                header.ship_from_id = n1_id
            elif n1_qual == "ST":
                header.ship_to_name = n1_name
                header.ship_to_id = n1_id

        elif tag == "PRF":
            header.buyer_po_number = seg.get(1)

        elif tag == "HL":
            current_hl_type = seg.get(3).upper()
            if current_hl_type == "T":
                current_pallet = EdiAsnPalletDetail(
                    pallet_number=f"PLT-{seg.get(1)}",
                    sscc_barcode="",
                )
                pallets.append(current_pallet)
                current_box = None
            elif current_hl_type == "P" and current_pallet:
                current_box = EdiAsnBoxDetail(box_number=f"BX-{seg.get(1)}")
                current_pallet.boxes.append(current_box)
            elif current_hl_type == "I":
                current_item = EdiAsnItemDetail(
                    line_number=line_seq,
                    sku="",
                )
                line_seq += 1
                if current_box:
                    current_box.items.append(current_item)
                elif current_pallet:
                    current_pallet.direct_items.append(current_item)
                else:
                    direct_items.append(current_item)

        elif tag == "MAN":
            man_val = seg.get(2)
            clean = parse_sscc_gs1_128(man_val)
            if current_hl_type == "T" and current_pallet:
                current_pallet.sscc_barcode = clean or man_val
                current_pallet.sscc_gs1_128 = format_sscc_gs1_128(current_pallet.sscc_barcode)
            elif current_hl_type == "P" and current_box:
                current_box.sscc_barcode = clean or man_val

        elif tag == "MEA":
            try:
                meas_type = seg.get(2)
                meas_val = float(seg.get(3, "0"))
                if current_hl_type == "T" and current_pallet:
                    if meas_type == "G":
                        current_pallet.gross_weight_kg = meas_val
                    elif meas_type == "N":
                        current_pallet.net_weight_kg = meas_val
                elif current_hl_type == "P" and current_box and meas_type == "G":
                    current_box.gross_weight_kg = meas_val
            except Exception:
                pass

        elif tag == "LIN" and current_item:
            elems = seg.elements
            i = 1
            while i < len(elems) - 1:
                q = seg.get(i + 1).upper()
                v = seg.get(i + 2)
                if q in ("BP", "IN"):
                    current_item.buyer_sku = v
                    if not current_item.sku:
                        current_item.sku = v
                elif q in ("VP", "VN", "VA"):
                    current_item.vendor_sku = v
                    if not current_item.sku:
                        current_item.sku = v
                elif q in ("UP", "EN", "GT"):
                    current_item.gtin = v
                i += 2
            if not current_item.sku and current_item.buyer_sku:
                current_item.sku = current_item.buyer_sku

        elif tag == "SN1" and current_item:
            try:
                current_item.qty_shipped = float(seg.get(2, "1"))
                current_item.uom = seg.get(3, "EA")
            except Exception:
                pass

        elif tag == "PID" and current_item:
            current_item.product_name = seg.get(5)

    return EdiAsnDocument(
        standard="ANSI_X12",
        document_type="856",
        control_number=interchange.control_number or "1",
        sender_id=interchange.sender_id or "",
        sender_qualifier=interchange.sender_qualifier or "ZZ",
        receiver_id=interchange.receiver_id or "",
        receiver_qualifier=interchange.receiver_qualifier or "ZZ",
        is_test=interchange.is_test,
        header=header,
        pallets=pallets,
        direct_items=direct_items,
    )


def parse_edifact_desadv(
    raw_content: str,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiAsnDocument:
    """
    Parses an inbound or outbound UN/EDIFACT DESADV (Despatch Advice) message into an EdiAsnDocument model.
    """
    interchange = parse_edifact(raw_content, delimiters)
    tx_sets = interchange.all_transactions()
    if not tx_sets:
        raise EdiSyntaxError("No messages found in UN/EDIFACT DESADV document")

    msg = tx_sets[0]
    segments = msg.segments

    header = EdiAsnShipmentHeader()
    pallets: List[EdiAsnPalletDetail] = []
    direct_items: List[EdiAsnItemDetail] = []

    current_pallet: Optional[EdiAsnPalletDetail] = None
    current_box: Optional[EdiAsnBoxDetail] = None
    current_item: Optional[EdiAsnItemDetail] = None
    line_seq = 1

    for seg in segments:
        tag = seg.tag

        if tag == "BGM":
            bgm_comp = seg.get_composite(1)
            header.delivery_number = bgm_comp[1] if len(bgm_comp) > 1 else (seg.get(2) or seg.get(1))

        elif tag == "DTM":
            dtm_comp = seg.get_composite(1)
            qual = dtm_comp[0] if dtm_comp else seg.get(1)
            raw_dt = dtm_comp[1] if len(dtm_comp) > 1 else seg.get(2)
            if raw_dt and len(raw_dt) >= 8 and raw_dt[:8].isdigit():
                try:
                    parsed_dt = date(int(raw_dt[0:4]), int(raw_dt[4:6]), int(raw_dt[6:8]))
                    if qual in ("11", "137"):
                        header.ship_date = parsed_dt
                    elif qual == "361" and current_item:
                        current_item.expiry_date = parsed_dt
                except Exception:
                    pass

        elif tag == "RFF":
            rff_comp = seg.get_composite(1)
            qual = rff_comp[0] if rff_comp else seg.get(1)
            val = rff_comp[1] if len(rff_comp) > 1 else seg.get(2)
            if qual == "ON":
                header.buyer_po_number = val
            elif qual == "DQ":
                header.delivery_number = val
            elif qual == "AAS":
                header.tracking_number = val

        elif tag == "NAD":
            nad_qual = seg.get(1)
            id_comp = seg.get_composite(2)
            nad_id = id_comp[0] if id_comp else seg.get(2)
            nad_name = seg.get(4)
            if nad_qual == "CZ":
                header.ship_from_name = nad_name
                header.ship_from_id = nad_id
            elif nad_qual == "CN":
                header.ship_to_name = nad_name
                header.ship_to_id = nad_id
            elif nad_qual == "CA":
                header.carrier_name = nad_name
                header.carrier_code = nad_id

        elif tag == "TDT":
            header.vehicle_number = seg.get(8) or seg.get(5)
            if not header.carrier_name:
                header.carrier_name = seg.get(5)

        elif tag == "CPS":
            pass

        elif tag == "PAC":
            pac_code = seg.get(3)
            if pac_code in ("201", "PLT", "PX"):
                current_pallet = EdiAsnPalletDetail(
                    pallet_number=f"PLT-{len(pallets) + 1}",
                    sscc_barcode="",
                )
                pallets.append(current_pallet)
                current_box = None
            elif pac_code in ("CT", "BX", "BOX", "CS") and current_pallet:
                current_box = EdiAsnBoxDetail(box_number=f"BX-{len(current_pallet.boxes) + 1}")
                current_pallet.boxes.append(current_box)

        elif tag == "GIN":
            sscc_val = seg.get(2)
            clean = parse_sscc_gs1_128(sscc_val)
            if current_pallet:
                current_pallet.sscc_barcode = clean or sscc_val
                current_pallet.sscc_gs1_128 = format_sscc_gs1_128(current_pallet.sscc_barcode)

        elif tag == "MEA":
            try:
                meas_qual = seg.get(2)
                val_comp = seg.get_composite(3)
                w_val = float(val_comp[1]) if len(val_comp) > 1 else float(seg.get(3, "0"))
                if current_pallet:
                    if meas_qual == "G":
                        current_pallet.gross_weight_kg = w_val
                    elif meas_qual == "N":
                        current_pallet.net_weight_kg = w_val
            except Exception:
                pass

        elif tag == "LIN":
            current_item = EdiAsnItemDetail(
                line_number=line_seq,
                sku="",
            )
            line_seq += 1
            code_comp = seg.get_composite(3)
            if code_comp:
                current_item.gtin = code_comp[0]
                current_item.sku = code_comp[0]
            if current_box:
                current_box.items.append(current_item)
            elif current_pallet:
                current_pallet.direct_items.append(current_item)
            else:
                direct_items.append(current_item)

        elif tag == "PIA" and current_item:
            comp = seg.get_composite(2)
            if comp:
                current_item.buyer_sku = comp[0]
                if not current_item.sku:
                    current_item.sku = comp[0]

        elif tag == "IMD" and current_item:
            comp = seg.get_composite(3)
            if comp and len(comp) >= 4:
                current_item.product_name = comp[3]
            elif comp:
                current_item.product_name = comp[0]

        elif tag == "QTY" and current_item:
            comp = seg.get_composite(1)
            if comp and len(comp) >= 2:
                try:
                    current_item.qty_shipped = float(comp[1])
                    if len(comp) >= 3:
                        current_item.uom = comp[2]
                except Exception:
                    pass

        elif tag == "GIR" and current_item:
            comp = seg.get_composite(2)
            if comp:
                current_item.batch_number = comp[0]

    return EdiAsnDocument(
        standard="EDIFACT",
        document_type="DESADV",
        control_number=interchange.control_number or "1",
        sender_id=interchange.sender_id or "",
        sender_qualifier=interchange.sender_qualifier or "ZZ",
        receiver_id=interchange.receiver_id or "",
        receiver_qualifier=interchange.receiver_qualifier or "ZZ",
        is_test=interchange.is_test,
        header=header,
        pallets=pallets,
        direct_items=direct_items,
    )


def parse_inbound_asn(
    raw_content: str,
    standard: Optional[Union[str, EdiStandard]] = None,
    delimiters: Optional[EdiDelimiters] = None,
) -> EdiAsnDocument:
    """
    Universal parser for Advance Shipping Notices (ANSI X12 856 or UN/EDIFACT DESADV).
    """
    if not standard:
        detected = detect_edi_standard(raw_content)
    elif isinstance(standard, EdiStandard):
        detected = standard
    else:
        detected = EdiStandard.EDIFACT if str(standard).upper() == "EDIFACT" else EdiStandard.ANSI_X12

    if detected == EdiStandard.EDIFACT:
        return parse_edifact_desadv(raw_content, delimiters)
    return parse_x12_856(raw_content, delimiters)


# ---------------------------------------------------------------------------
# Outbound EDI 856 / DESADV Service Class
# ---------------------------------------------------------------------------

class Edi856Service(CrudService):
    """
    Business service for automated generation of Outbound EDI 856 (ASN) & UN/EDIFACT DESADV documents
    upon truck dispatch / shipment completion with full multi-tenant isolation.
    """

    def __init__(
        self,
        repo: Optional[CrudRepository] = None,
        partner_repo: Optional[CrudRepository] = None,
        sku_mapping_repo: Optional[CrudRepository] = None,
        delivery_repo: Optional[CrudRepository] = None,
        delivery_line_repo: Optional[CrudRepository] = None,
        sales_order_repo: Optional[CrudRepository] = None,
        sales_line_repo: Optional[CrudRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        pick_list_item_repo: Optional[CrudRepository] = None,
        sscc_service_instance: Optional[SsccService] = None,
    ):
        super().__init__(repo or EDI_TRANSACTION_REPO)
        self.partner_repo = partner_repo or EDI_PARTNER_REPO
        self.sku_mapping_repo = sku_mapping_repo or EDI_SKU_MAPPING_REPO
        self.delivery_repo = delivery_repo or DELIVERY_T0077_REPO
        self.delivery_line_repo = delivery_line_repo or DELIVERY_LINE_T0078_REPO
        self.sales_order_repo = sales_order_repo or SALES_ORDER_T0012_REPO
        self.sales_line_repo = sales_line_repo or SALES_LINE_T0013_REPO
        self.customer_repo = customer_repo or CUSTOMER_T0010_REPO
        self.product_repo = product_repo or PRODUCT_T0001_REPO
        self.pick_list_item_repo = pick_list_item_repo or PICK_LIST_ITEM_T0102_REPO
        self.sscc_svc = sscc_service_instance or sscc_service

    def resolve_partner_for_delivery(
        self,
        delivery: Dict[str, Any],
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves the trading partner configuration (T0124) associated with a delivery's customer.
        """
        kwargs = {"conn": conn} if conn is not None else {}
        if partner_id:
            return self.partner_repo.get(partner_id, **kwargs)

        sales_order_id = delivery.get("sales_order_id")
        if not sales_order_id:
            return None

        so = self.sales_order_repo.get(sales_order_id, **kwargs)
        if not so or not so.get("customer_id"):
            return None

        customer_id = so["customer_id"]
        partners = self.partner_repo.list(
            filters={"customer_id": customer_id, "is_active": True},
            limit=1,
            **kwargs,
        )
        return partners[0] if partners else None

    def generate_asn_for_delivery(
        self,
        delivery_id: int,
        partner_id: Optional[int] = None,
        carrier_name: Optional[str] = None,
        tracking_number: Optional[str] = None,
        vehicle_number: Optional[str] = None,
        seal_number: Optional[str] = None,
        auto_generate_sscc: bool = True,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> EdiAsnGenerateResponse:
        """
        Constructs and transmits an outbound Advance Shipping Notice (EDI 856 ASN or DESADV)
        for a completed/dispatched delivery (T0077) with full SSCC-18 pallet hierarchy and batch tracking.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        with db_transaction(conn) as tx_conn:
            delivery = self.delivery_repo.get(delivery_id, conn=tx_conn)
            if not delivery:
                raise ValueError(f"Delivery record {delivery_id} not found")

            sales_order_id = delivery.get("sales_order_id")
            so = self.sales_order_repo.get(sales_order_id, conn=tx_conn) if sales_order_id else None

            customer = None
            if so and so.get("customer_id"):
                customer = self.customer_repo.get(so["customer_id"], conn=tx_conn)

            partner = self.resolve_partner_for_delivery(delivery, partner_id, conn=tx_conn, tenant_id=tenant_id)
            if not partner:
                raise ValueError(
                    f"No active EDI Trading Partner (T0124) found for Delivery #{delivery_id} "
                    f"(Customer #{customer.get('id') if customer else 'None'})"
                )

            # 1. Gather Delivery Lines
            delivery_lines = self.delivery_line_repo.list(
                filters={"delivery_id": delivery_id},
                order_by="line_number ASC",
                conn=tx_conn,
            )

            # Fallback to Sales Order lines if delivery lines not populated
            if not delivery_lines and sales_order_id:
                so_lines = self.sales_line_repo.list(
                    filters={"sales_order_id": sales_order_id},
                    order_by="line_number ASC",
                    conn=tx_conn,
                )
                delivery_lines = [
                    {
                        "delivery_id": delivery_id,
                        "sales_order_line_id": sol.get("id"),
                        "product_id": sol.get("product_id"),
                        "product_name": sol.get("product_name"),
                        "qty_shipped": sol.get("qty", 1.0),
                        "qty_ordered": sol.get("qty", 1.0),
                        "uom_id": sol.get("uom_id"),
                        "line_number": sol.get("line_number", idx + 1),
                    }
                    for idx, sol in enumerate(so_lines)
                ]

            # 2. Gather Batch and Expiry information from Pick List Items (T0102)
            pick_items = []
            if sales_order_id:
                try:
                    pick_items = self.pick_list_item_repo.list(
                        filters={"sales_order_line_id": [dl.get("sales_order_line_id") for dl in delivery_lines if dl.get("sales_order_line_id")]},
                        conn=tx_conn,
                    )
                except Exception as e:
                    logger.debug(f"Could not fetch pick items for SO {sales_order_id}: {e}")

            pick_by_sol = {p["sales_order_line_id"]: p for p in pick_items if p.get("sales_order_line_id")}

            # 3. Gather or Generate SSCC Pallets (T0127)
            existing_pallets = self.sscc_svc.get_pallets_for_delivery(delivery_id, conn=tx_conn, tenant_id=tenant_id)
            if not existing_pallets and auto_generate_sscc:
                company_prefix = partner.get("gs1_company_prefix") or DEFAULT_GS1_COMPANY_PREFIX
                p_items = []
                for dl in delivery_lines:
                    pid = dl.get("product_id")
                    prod = self.product_repo.get(pid, conn=tx_conn) if pid else None
                    sku = prod.get("sku") if prod else f"PRD-{pid}"
                    sol_id = dl.get("sales_order_line_id")
                    pi = pick_by_sol.get(sol_id, {})
                    b_num = pi.get("picked_batch_number") or pi.get("batch_number")
                    exp_d = str(pi.get("expiry_date")) if pi.get("expiry_date") else None

                    p_items.append(
                        PackagingItem(
                            product_id=pid,
                            sku=str(sku),
                            product_name=str(dl.get("product_name") or (prod.get("name") if prod else "Standard Product")),
                            quantity=float(dl.get("qty_shipped") or 1.0),
                            batch_number=str(b_num) if b_num else None,
                            expiry_date=exp_d,
                            gross_weight_kg=round(float(dl.get("qty_shipped") or 1.0) * 1.5, 2),
                            net_weight_kg=round(float(dl.get("qty_shipped") or 1.0) * 1.4, 2),
                        )
                    )

                hierarchy = PackagingHierarchy(
                    delivery_id=delivery_id,
                    sales_order_id=sales_order_id,
                    carrier_code=str(partner.get("partner_code") or "NOVA"),
                )
                pallet = PackagingPallet(
                    pallet_number=f"PLT-{delivery_id}-01",
                    sscc_barcode="",
                    direct_items=p_items,
                )
                hierarchy.add_pallet(pallet)
                existing_pallets = self.sscc_svc.create_pallet_hierarchy(
                    delivery_id=delivery_id,
                    hierarchy=hierarchy,
                    sales_order_id=sales_order_id,
                    company_prefix=str(company_prefix),
                    conn=tx_conn,
                    tenant_id=tenant_id,
                )

            # 4. Resolve SKU cross-references for Trading Partner (T0125)
            sku_mappings = self.sku_mapping_repo.list(
                filters={"partner_id": partner["id"], "is_active": True},
                conn=tx_conn,
            )
            map_by_product = {m["product_id"]: m for m in sku_mappings if m.get("product_id")}

            # 5. Build AsnDocument
            del_date = delivery.get("actual_delivery_date") or delivery.get("delivery_date") or date.today()
            if isinstance(del_date, str):
                try:
                    del_date = date.fromisoformat(del_date[:10])
                except Exception:
                    del_date = date.today()

            c_name = str(carrier_name or partner.get("partner_name") or "Nova Express Delivery")
            c_code = str(partner.get("partner_code") or "NOVA")
            sf_id_val = str(partner.get("interchange_sender_id") or "NOVAERP")
            st_id_val = str(partner.get("interchange_receiver_id") or "RETAILHUB")
            st_name_val = str(customer.get("name") if customer else (partner.get("partner_name") or "Retail DC"))

            header = EdiAsnShipmentHeader(
                delivery_id=delivery_id,
                delivery_number=str(delivery.get("delivery_number") or f"DEL-{delivery_id}"),
                sales_order_id=sales_order_id,
                sales_order_number=str(so.get("order_number")) if so and so.get("order_number") else None,
                buyer_po_number=str(so.get("notes")) if so and so.get("notes") and "PO" in str(so.get("notes")) else (f"PO-{sales_order_id}" if sales_order_id else "PO-001"),
                ship_date=del_date,
                ship_time=datetime.now(timezone.utc).strftime("%H%M"),
                estimated_delivery_date=del_date,
                carrier_name=c_name,
                carrier_code=c_code,
                tracking_number=str(tracking_number or delivery.get("delivery_route") or f"BOL-{delivery_id}"),
                vehicle_number=str(vehicle_number or (f"TRK-{delivery.get('driver_id')}" if delivery.get("driver_id") else "TRK-01")),
                seal_number=str(seal_number or f"SEAL-{delivery_id}"),
                driver_id=delivery.get("driver_id"),
                total_pallets=len(existing_pallets),
                ship_from_name="Nova Distribution Hub",
                ship_from_id=sf_id_val,
                ship_to_name=st_name_val,
                ship_to_id=st_id_val,
            )

            # Build Pallet & Item Details
            pallet_details: List[EdiAsnPalletDetail] = []
            sscc_barcodes: List[str] = []

            for pal_record in existing_pallets:
                if pal_record.get("package_type") not in ("PALLET", "CONTAINER") and pal_record.get("parent_sscc_id"):
                    continue

                sscc_bc = str(pal_record.get("sscc_barcode") or "")
                sscc_barcodes.append(sscc_bc)

                items_in_pallet: List[EdiAsnItemDetail] = []
                for idx, dl in enumerate(delivery_lines, 1):
                    pid = dl.get("product_id")
                    prod = self.product_repo.get(pid, conn=tx_conn) if pid else None
                    sku_code = str(prod.get("sku") if prod else f"SKU-{pid}")
                    mapping = map_by_product.get(pid, {})
                    sol_id = dl.get("sales_order_line_id")
                    pi = pick_by_sol.get(sol_id, {})

                    exp_val = pi.get("expiry_date")
                    if isinstance(exp_val, str):
                        try:
                            exp_val = date.fromisoformat(exp_val[:10])
                        except Exception:
                            exp_val = None

                    b_num = pi.get("picked_batch_number") or pi.get("batch_number") or f"LOT-{delivery_id}"

                    items_in_pallet.append(
                        EdiAsnItemDetail(
                            line_number=idx,
                            product_id=pid,
                            sku=sku_code,
                            buyer_sku=str(mapping.get("partner_sku") or sku_code),
                            vendor_sku=sku_code,
                            gtin=str(mapping.get("gtin") or (prod.get("barcode") if prod else "")) or None,
                            product_name=str(dl.get("product_name") or (prod.get("name") if prod else "Food Item")),
                            qty_shipped=float(dl.get("qty_shipped") or 1.0),
                            qty_ordered=float(dl.get("qty_ordered") or dl.get("qty_shipped") or 1.0),
                            uom=str(mapping.get("partner_uom") or "EA"),
                            batch_number=str(b_num),
                            expiry_date=exp_val,
                            gross_weight_kg=round(float(dl.get("qty_shipped") or 1.0) * 1.5, 2),
                            net_weight_kg=round(float(dl.get("qty_shipped") or 1.0) * 1.4, 2),
                        )
                    )

                pallet_details.append(
                    EdiAsnPalletDetail(
                        pallet_id=pal_record.get("id"),
                        pallet_number=str(pal_record.get("pallet_number") or f"PLT-{pal_record.get('id', 1)}"),
                        sscc_barcode=sscc_bc,
                        sscc_gs1_128=format_sscc_gs1_128(sscc_bc),
                        package_type=str(pal_record.get("package_type") or "PALLET"),
                        gross_weight_kg=float(pal_record.get("gross_weight_kg") or (sum(it.gross_weight_kg or 0.0 for it in items_in_pallet) + 25.0)),
                        net_weight_kg=float(pal_record.get("net_weight_kg") or sum(it.net_weight_kg or 0.0 for it in items_in_pallet)),
                        tare_weight_kg=float(pal_record.get("tare_weight_kg") or 25.0),
                        volume_cbm=float(pal_record.get("volume_cbm") or 1.2),
                        direct_items=items_in_pallet,
                    )
                )

            ctrl_num = _generate_control_number(tx_conn)
            partner_std = str(partner.get("edi_standard") or "ANSI_X12")
            is_edifact = (partner_std == "EDIFACT" or partner_std == EdiStandard.EDIFACT)
            doc_type = "DESADV" if is_edifact else "856"

            asn_doc = EdiAsnDocument(
                standard=partner_std,
                document_type=doc_type,
                control_number=ctrl_num,
                sender_id=str(partner.get("interchange_sender_id") or "NOVAERP"),
                sender_qualifier=str(partner.get("sender_qualifier") or "ZZ"),
                receiver_id=str(partner.get("interchange_receiver_id") or "RETAILHUB"),
                receiver_qualifier=str(partner.get("receiver_qualifier") or "ZZ"),
                header=header,
                pallets=pallet_details,
            )

            if is_edifact:
                edi_payload = generate_edifact_desadv(asn_doc, partner=partner)
            else:
                edi_payload = generate_x12_856(asn_doc, partner=partner)

            tx_num = f"TX-ASN-{ctrl_num}"
            tx_record = {
                "transaction_number": tx_num,
                "partner_id": partner["id"],
                "standard": partner_std,
                "document_type": doc_type,
                "direction": EdiDirection.OUTBOUND.value,
                "control_number": ctrl_num,
                "status": EdiTransactionStatus.PROCESSED.value,
                "sales_order_id": sales_order_id,
                "delivery_id": delivery_id,
                "invoice_id": None,
                "raw_payload": edi_payload,
                "parsed_data": asn_doc.model_dump(mode="json"),
                "ack_status": "PENDING",
                "processed_at": datetime.now(timezone.utc),
            }
            saved_tx = self.repo.create(tx_record, conn=tx_conn)

            for p_rec in existing_pallets:
                if p_rec.get("id"):
                    self.sscc_svc.update_pallet_status(p_rec["id"], "DISPATCHED", conn=tx_conn, tenant_id=tenant_id)

            return EdiAsnGenerateResponse(
                transaction_id=saved_tx["id"],
                transaction_number=tx_num,
                delivery_id=delivery_id,
                control_number=ctrl_num,
                standard=partner_std,
                document_type=doc_type,
                sscc_pallets_count=len(pallet_details),
                sscc_barcodes=sscc_barcodes,
                edi_payload=edi_payload,
            )


# Default singleton instance
edi_856_service = Edi856Service()

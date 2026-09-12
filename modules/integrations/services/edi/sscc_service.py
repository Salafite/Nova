"""
Nova ERP — GS1-128 / SSCC-18 Pallet Barcode Generator & Packaging Hierarchy Service
Provides GS1 SSCC-18 (Serial Shipping Container Code) generation with Modulo-10 check digit calculation,
GS1-128 Application Identifier (00) formatting, packaging hierarchy tracking (Pallet -> Box -> Item),
and database persistence with multi-tenant scoping.
"""

import re
import logging
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
import psycopg2.extras

from packages.database.connection import get_connection, release_connection, db_transaction
from modules.core.context import get_current_tenant
from modules.core.services.base import CrudService
from modules.integrations.models.edi import (
    EDI_SSCC_PALLET_REPO,
    EDI_PARTNER_REPO,
    EdiPackageType,
    EdiPalletStatus,
)

logger = logging.getLogger(__name__)

DEFAULT_GS1_COMPANY_PREFIX = "0614141"  # Default 7-digit GS1 Company Prefix fallback


# ===========================================================================
# 1. GS1 Modulo-10 Check Digit Calculation & SSCC-18 Utilities
# ===========================================================================

def calculate_modulo10_check_digit(data: str) -> int:
    """
    Calculates the GS1 Modulo-10 check digit for a numeric string.
    
    Standard GS1 Algorithm:
    - Number positions from right to left starting from position 1 (rightmost data digit).
    - Odd positions from right (1, 3, 5, ...) are multiplied by 3.
    - Even positions from right (2, 4, 6, ...) are multiplied by 1.
    - Sum all products.
    - Check digit = (10 - (Sum % 10)) % 10.
    
    Args:
        data: Numeric string (e.g. 17 digits for SSCC-18, 13 digits for GTIN-14, etc.)
        
    Returns:
        Check digit as an integer (0-9).
        
    Raises:
        ValueError: If data is empty or contains non-digit characters.
    """
    data_str = str(data).strip()
    if not data_str or not data_str.isdigit():
        raise ValueError(f"Invalid numeric input for GS1 check digit calculation: '{data}'")

    # From right to left: rightmost has index len-1, distance from right = 1 (odd) -> weight 3
    weighted_sum = sum(
        int(digit) * (3 if (len(data_str) - idx) % 2 == 1 else 1)
        for idx, digit in enumerate(data_str)
    )
    remainder = weighted_sum % 10
    return 0 if remainder == 0 else (10 - remainder)


def validate_modulo10(data_with_check_digit: str) -> bool:
    """
    Validates whether the last digit of the numeric string matches the GS1 Modulo-10 check digit
    calculated over the preceding digits.
    """
    s = str(data_with_check_digit).strip()
    if not s or len(s) < 2 or not s.isdigit():
        return False
    data_part = s[:-1]
    expected_check = int(s[-1])
    try:
        calculated_check = calculate_modulo10_check_digit(data_part)
        return expected_check == calculated_check
    except Exception:
        return False


def parse_sscc_gs1_128(raw: str) -> str:
    """
    Extracts and normalizes the 18-digit SSCC number from a raw barcode scan or formatted string.
    Supports formats like:
      - Raw 18 digits: '006141411234567895'
      - AI formatted: '(00)006141411234567895'
      - Raw stream with AI 00: '00006141411234567895' (20 digits starting with 00)
      - Symbology prefixed: ']C100006141411234567895'
    """
    if not raw:
        return ""
    clean = str(raw).strip()
    clean = re.sub(r'^\][Ce][01]', '', clean)
    clean = re.sub(r'[\s\-]', '', clean)

    # Match parenthesized AI (00)
    match_ai = re.search(r'\(00\)(\d{18})', clean)
    if match_ai:
        return match_ai.group(1)

    # If starts with '00' and length is 20 digits, strip the leading AI '00'
    if len(clean) == 20 and clean.startswith('00') and clean.isdigit():
        return clean[2:]

    # Match raw 18 digits
    match_18 = re.search(r'\b(\d{18})\b', clean)
    if match_18:
        return match_18.group(1)

    return clean


def validate_sscc(sscc: str) -> bool:
    """
    Validates if an SSCC is a valid 18-digit code with correct GS1 Modulo-10 check digit.
    """
    extracted = parse_sscc_gs1_128(sscc)
    if len(extracted) != 18 or not extracted.isdigit():
        return False
    return validate_modulo10(extracted)


def format_sscc_gs1_128(sscc: str, with_ai_parentheses: bool = True) -> str:
    """
    Formats an 18-digit SSCC into standard GS1-128 representation with Application Identifier (00).
    
    Args:
        sscc: 18-digit SSCC string
        with_ai_parentheses: If True, returns '(00)006141411234567895'.
                             If False, returns '00006141411234567895'.
    """
    clean_sscc = parse_sscc_gs1_128(sscc)
    if len(clean_sscc) != 18:
        clean_sscc = str(sscc).strip()
    return f"(00){clean_sscc}" if with_ai_parentheses else f"00{clean_sscc}"


def generate_sscc18(
    company_prefix: Optional[str] = None,
    serial_number: Union[int, str] = 1,
    extension_digit: Union[int, str] = 0,
) -> str:
    """
    Generates a full 18-digit GS1 Serial Shipping Container Code (SSCC-18).
    
    Structure:
    - Digit 1: Extension digit (0-9, default 0)
    - Digits 2..(K+1): GS1 Company Prefix (typically 7 to 10 digits)
    - Digits (K+2)..17: Serial Reference Number (zero-padded)
    - Digit 18: Modulo-10 Check Digit calculated over digits 1..17
    
    Args:
        company_prefix: GS1 Company Prefix (6 to 12 digits). Defaults to DEFAULT_GS1_COMPANY_PREFIX if None.
        serial_number: Unique sequential identifier for this shipping container.
        extension_digit: Extension digit 0-9 (default 0 for cartons/pallets).
        
    Returns:
        18-digit SSCC string.
        
    Raises:
        ValueError: If company prefix, extension digit, or serial reference exceed 17 data digits.
    """
    ext_str = str(extension_digit).strip()
    if len(ext_str) != 1 or not ext_str.isdigit():
        raise ValueError(f"Extension digit must be a single digit (0-9), got: '{extension_digit}'")

    prefix = str(company_prefix or DEFAULT_GS1_COMPANY_PREFIX).strip()
    if not prefix.isdigit() or len(prefix) < 4 or len(prefix) > 12:
        raise ValueError(f"GS1 Company Prefix must be between 4 and 12 digits, got: '{company_prefix}'")

    # The data string before check digit must be exactly 17 digits:
    # 1 digit (extension) + len(prefix) + len(serial_reference) = 17
    serial_len = 17 - 1 - len(prefix)
    if serial_len <= 0:
        raise ValueError(f"GS1 Company Prefix '{prefix}' is too long to accommodate serial reference")

    serial_str = str(serial_number).strip()
    if not serial_str.isdigit():
        raise ValueError(f"Serial number must be numeric, got: '{serial_number}'")

    if len(serial_str) > serial_len:
        raise ValueError(
            f"Serial number '{serial_str}' exceeds maximum allowed capacity ({serial_len} digits) "
            f"for company prefix length {len(prefix)}"
        )

    padded_serial = serial_str.zfill(serial_len)
    data_17 = f"{ext_str}{prefix}{padded_serial}"
    check_digit = calculate_modulo10_check_digit(data_17)
    return f"{data_17}{check_digit}"


def decompose_sscc18(sscc: str, company_prefix_len: Optional[int] = None) -> Dict[str, Any]:
    """
    Decomposes an 18-digit SSCC into its constituent parts:
    extension digit, GS1 company prefix, serial reference, and check digit.
    """
    clean = parse_sscc_gs1_128(sscc)
    is_valid = validate_sscc(clean)
    if len(clean) != 18 or not clean.isdigit():
        return {
            "sscc_18": clean,
            "is_valid": False,
            "extension_digit": None,
            "company_prefix": None,
            "serial_reference": None,
            "check_digit": None,
            "gs1_128_formatted": format_sscc_gs1_128(clean),
        }

    ext_digit = clean[0]
    check_digit = int(clean[-1])
    data_16 = clean[1:17]

    p_len = company_prefix_len or 7
    if p_len < 4 or p_len > 12:
        p_len = 7

    company_prefix = data_16[:p_len]
    serial_ref = data_16[p_len:]

    return {
        "sscc_18": clean,
        "is_valid": is_valid,
        "extension_digit": ext_digit,
        "company_prefix": company_prefix,
        "serial_reference": serial_ref,
        "check_digit": check_digit,
        "gs1_128_formatted": format_sscc_gs1_128(clean),
    }


# ===========================================================================
# 2. Packaging Hierarchy Tracking Models (Pallet -> Box -> Item)
# ===========================================================================

class PackagingLevel(str, Enum):
    PALLET = "PALLET"
    CONTAINER = "CONTAINER"
    BOX = "BOX"
    CASE = "CASE"
    CARTON = "CARTON"
    ITEM = "ITEM"


class PackagingItem(BaseModel):
    """
    Item-level packaging entity inside a box or pallet.
    """
    product_id: Optional[int] = None
    sku: str
    product_name: Optional[str] = None
    buyer_sku: Optional[str] = None
    gtin: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: float = 1.0
    uom: str = "EA"
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    serial_numbers: List[str] = Field(default_factory=list)


class PackagingBox(BaseModel):
    """
    Box / Case / Carton level container on a pallet.
    """
    box_id: Optional[str] = None
    box_number: Optional[str] = None
    sscc_barcode: Optional[str] = None
    package_type: str = "BOX"  # BOX | CASE | CARTON
    items: List[PackagingItem] = Field(default_factory=list)
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = 0.5  # Standard corrugated box tare
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    volume_cbm: Optional[float] = None

    def add_item(self, item: Union[PackagingItem, Dict[str, Any]]) -> "PackagingBox":
        if isinstance(item, dict):
            item = PackagingItem(**item)
        self.items.append(item)
        return self

    def calculate_weights(self, default_box_tare: float = 0.5) -> None:
        """
        Calculates and rolls up net and gross weights from contained items.
        """
        tare = self.tare_weight_kg if self.tare_weight_kg is not None else default_box_tare
        net = sum(
            (it.net_weight_kg if it.net_weight_kg is not None else (it.gross_weight_kg or 0.0))
            for it in self.items
        )
        self.net_weight_kg = round(net, 3)
        self.gross_weight_kg = round(net + tare, 3)
        if self.length_cm and self.width_cm and self.height_cm:
            self.volume_cbm = round((self.length_cm * self.width_cm * self.height_cm) / 1_000_000, 4)


class PackagingPallet(BaseModel):
    """
    Top-level shipping container / pallet entity (SSCC-18 identified).
    """
    pallet_id: Optional[int] = None
    pallet_number: Optional[str] = None
    sscc_barcode: str
    package_type: str = "PALLET"  # PALLET | CONTAINER
    parent_sscc_id: Optional[int] = None
    boxes: List[PackagingBox] = Field(default_factory=list)
    direct_items: List[PackagingItem] = Field(default_factory=list)
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = 25.0  # Standard wooden pallet tare ~25kg
    volume_cbm: Optional[float] = None
    status: str = "PACKED"  # CREATED | PACKED | STAGED | DISPATCHED | DELIVERED

    def add_box(self, box: Union[PackagingBox, Dict[str, Any]]) -> "PackagingPallet":
        if isinstance(box, dict):
            box = PackagingBox(**box)
        self.boxes.append(box)
        return self

    def add_direct_item(self, item: Union[PackagingItem, Dict[str, Any]]) -> "PackagingPallet":
        if isinstance(item, dict):
            item = PackagingItem(**item)
        self.direct_items.append(item)
        return self

    def total_units(self) -> int:
        """Counts total item units packed across all boxes and direct items."""
        box_units = sum(int(it.quantity) for b in self.boxes for it in b.items)
        direct_units = sum(int(it.quantity) for it in self.direct_items)
        return box_units + direct_units

    def total_boxes(self) -> int:
        return len(self.boxes)

    def calculate_weights(self, default_pallet_tare: float = 25.0, default_box_tare: float = 0.5) -> None:
        """
        Calculates and rolls up net and gross weights from all nested boxes and direct items.
        """
        for box in self.boxes:
            box.calculate_weights(default_box_tare=default_box_tare)

        pallet_tare = self.tare_weight_kg if self.tare_weight_kg is not None else default_pallet_tare
        boxes_net = sum(b.net_weight_kg or 0.0 for b in self.boxes)
        boxes_gross = sum(b.gross_weight_kg or 0.0 for b in self.boxes)

        direct_net = sum(
            (it.net_weight_kg if it.net_weight_kg is not None else (it.gross_weight_kg or 0.0))
            for it in self.direct_items
        )

        total_net = boxes_net + direct_net
        total_gross = boxes_gross + direct_net + pallet_tare

        self.net_weight_kg = round(total_net, 3)
        self.gross_weight_kg = round(total_gross, 3)

        # Roll up volumes if available
        box_vols = [b.volume_cbm for b in self.boxes if b.volume_cbm is not None]
        if box_vols and self.volume_cbm is None:
            self.volume_cbm = round(sum(box_vols), 4)


class PackagingHierarchy(BaseModel):
    """
    Shipment / Delivery level packaging hierarchy aggregator for ASN generation.
    Tracks Pallet -> Box -> Item structures.
    """
    delivery_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    carrier_code: Optional[str] = None
    tracking_number: Optional[str] = None
    pallets: List[PackagingPallet] = Field(default_factory=list)

    def add_pallet(self, pallet: Union[PackagingPallet, Dict[str, Any]]) -> "PackagingHierarchy":
        if isinstance(pallet, dict):
            pallet = PackagingPallet(**pallet)
        self.pallets.append(pallet)
        return self

    def calculate_all_weights(self) -> None:
        for p in self.pallets:
            p.calculate_weights()

    def total_pallets(self) -> int:
        return len(self.pallets)

    def total_boxes(self) -> int:
        return sum(p.total_boxes() for p in self.pallets)

    def total_items(self) -> int:
        return sum(p.total_units() for p in self.pallets)

    def total_gross_weight(self) -> float:
        return round(sum(p.gross_weight_kg or 0.0 for p in self.pallets), 3)

    def total_net_weight(self) -> float:
        return round(sum(p.net_weight_kg or 0.0 for p in self.pallets), 3)

    def to_hl_records(self) -> List[Dict[str, Any]]:
        """
        Converts the packaging hierarchy into a structured list of Hierarchical Level (HL) records
        for EDI 856 ASN and EDIFACT DESADV message builders.
        
        Returns:
            List of dicts with:
              - hl_id (int: 1, 2, 3...)
              - parent_hl_id (int or None)
              - level_code: 'S' (Shipment), 'O' (Order), 'T' (Tare/Pallet), 'P' (Pack/Box), 'I' (Item)
              - data: Level-specific attributes (SSCC, SKU, quantity, batch, weights)
        """
        self.calculate_all_weights()
        records: List[Dict[str, Any]] = []
        hl_counter = 1

        # 1. Shipment Level (S)
        shipment_hl_id = hl_counter
        records.append({
            "hl_id": shipment_hl_id,
            "parent_hl_id": None,
            "level_code": "S",
            "level_name": "Shipment",
            "delivery_id": self.delivery_id,
            "carrier_code": self.carrier_code,
            "tracking_number": self.tracking_number,
            "total_pallets": self.total_pallets(),
            "total_boxes": self.total_boxes(),
            "total_items": self.total_items(),
            "gross_weight_kg": self.total_gross_weight(),
            "net_weight_kg": self.total_net_weight(),
        })
        hl_counter += 1

        # 2. Order Level (O)
        order_hl_id = hl_counter
        records.append({
            "hl_id": order_hl_id,
            "parent_hl_id": shipment_hl_id,
            "level_code": "O",
            "level_name": "Order",
            "sales_order_id": self.sales_order_id,
        })
        hl_counter += 1

        # 3. Pallets (T - Tare / Pallet), Boxes (P - Pack), Items (I - Item)
        for pallet in self.pallets:
            pallet_hl_id = hl_counter
            records.append({
                "hl_id": pallet_hl_id,
                "parent_hl_id": order_hl_id,
                "level_code": "T",
                "level_name": "Tare/Pallet",
                "pallet_number": pallet.pallet_number,
                "sscc_barcode": pallet.sscc_barcode,
                "sscc_gs1_128": format_sscc_gs1_128(pallet.sscc_barcode),
                "package_type": pallet.package_type,
                "gross_weight_kg": pallet.gross_weight_kg,
                "net_weight_kg": pallet.net_weight_kg,
                "tare_weight_kg": pallet.tare_weight_kg,
                "volume_cbm": pallet.volume_cbm,
                "boxes_count": len(pallet.boxes),
                "units_count": pallet.total_units(),
            })
            hl_counter += 1

            # Boxes within pallet
            for box in pallet.boxes:
                box_hl_id = hl_counter
                records.append({
                    "hl_id": box_hl_id,
                    "parent_hl_id": pallet_hl_id,
                    "level_code": "P",
                    "level_name": "Pack/Box",
                    "box_number": box.box_number,
                    "sscc_barcode": box.sscc_barcode,
                    "package_type": box.package_type,
                    "gross_weight_kg": box.gross_weight_kg,
                    "net_weight_kg": box.net_weight_kg,
                    "tare_weight_kg": box.tare_weight_kg,
                    "volume_cbm": box.volume_cbm,
                    "items_count": len(box.items),
                })
                hl_counter += 1

                # Items within box
                for item in box.items:
                    item_hl_id = hl_counter
                    records.append({
                        "hl_id": item_hl_id,
                        "parent_hl_id": box_hl_id,
                        "level_code": "I",
                        "level_name": "Item",
                        "product_id": item.product_id,
                        "sku": item.sku,
                        "buyer_sku": item.buyer_sku,
                        "product_name": item.product_name,
                        "gtin": item.gtin,
                        "quantity": item.quantity,
                        "uom": item.uom,
                        "batch_number": item.batch_number,
                        "expiry_date": item.expiry_date,
                        "gross_weight_kg": item.gross_weight_kg,
                        "net_weight_kg": item.net_weight_kg,
                        "serial_numbers": item.serial_numbers,
                    })
                    hl_counter += 1

            # Direct items on pallet (no box intermediate level)
            for item in pallet.direct_items:
                item_hl_id = hl_counter
                records.append({
                    "hl_id": item_hl_id,
                    "parent_hl_id": pallet_hl_id,
                    "level_code": "I",
                    "level_name": "Item",
                    "product_id": item.product_id,
                    "sku": item.sku,
                    "buyer_sku": item.buyer_sku,
                    "product_name": item.product_name,
                    "gtin": item.gtin,
                    "quantity": item.quantity,
                    "uom": item.uom,
                    "batch_number": item.batch_number,
                    "expiry_date": item.expiry_date,
                    "gross_weight_kg": item.gross_weight_kg,
                    "net_weight_kg": item.net_weight_kg,
                    "serial_numbers": item.serial_numbers,
                })
                hl_counter += 1

        return records


# ===========================================================================
# 3. GS1 Logistics Label Data Generator & Formatter
# ===========================================================================

def format_gs1_logistics_label(
    pallet_data: Union[Dict[str, Any], PackagingPallet],
    company_info: Optional[Dict[str, Any]] = None,
    ship_to: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Formats complete GS1 Logistics Label data following the GS1 International Standard Layout:
    
    1. Top Section (Free Format / Carrier & Destination):
       - Shipper / Sender Company Name & Address
       - Receiver / Consignee / Ship-To Name, Address, Postal Code
       - Carrier info, Bill of Lading, Purchase Order number
    
    2. Middle Section (Human Readable Text):
       - Product Description / Content Summary
       - SSCC in Human Readable Format: (00) 0 0614141 123456789 5
       - Batch / Lot Number (10)
       - Expiry Date (17) YYMMDD
       - Gross Weight / Net Weight / Pallet Number / Total Cartons
    
    3. Bottom Section (Barcodes):
       - Primary Barcode: GS1-128 SSCC AI (00)
       - Secondary Barcode: Batch AI (10) + Expiry AI (17)
    """
    if isinstance(pallet_data, PackagingPallet):
        p_dict = pallet_data.model_dump()
    else:
        p_dict = dict(pallet_data)

    sscc = parse_sscc_gs1_128(p_dict.get("sscc_barcode", ""))
    company = company_info or {
        "company_name": "Nova Distribution Ltd.",
        "address": "Warehouse 4B, Logistics City",
        "city": "Dubai",
        "country": "UAE",
    }
    destination = ship_to or {
        "partner_name": "Carrefour Supermarket DC",
        "store_number": "CRF-042",
        "city": "Dubai Investment Park",
        "country": "UAE",
    }

    contents = p_dict.get("contents_summary") or {}
    items_count = p_dict.get("items_count") or p_dict.get("units_count") or 0

    return {
        "header": {
            "title": "GS1 LOGISTICS LABEL",
            "shipper": company,
            "ship_to": destination,
            "order_number": p_dict.get("sales_order_id"),
            "delivery_number": p_dict.get("delivery_id"),
        },
        "item_details": {
            "pallet_number": p_dict.get("pallet_number") or f"PLT-{p_dict.get('id', 1)}",
            "package_type": p_dict.get("package_type", "PALLET"),
            "gross_weight_kg": p_dict.get("gross_weight_kg"),
            "net_weight_kg": p_dict.get("net_weight_kg"),
            "total_units": items_count,
            "contents": contents,
        },
        "sscc": {
            "raw_18": sscc,
            "formatted_gs1_128": format_sscc_gs1_128(sscc, with_ai_parentheses=True),
            "barcode_value": f"00{sscc}",
            "human_readable_spaced": f"(00) {sscc[0]} {sscc[1:8]} {sscc[8:17]} {sscc[17]}" if len(sscc) == 18 else sscc,
            "is_valid": validate_sscc(sscc),
        },
        "barcodes": [
            {
                "ai": "00",
                "name": "SSCC",
                "human_readable": format_sscc_gs1_128(sscc, with_ai_parentheses=True),
                "barcode_data": f"00{sscc}",
            }
        ],
    }


# ===========================================================================
# 4. SsccService Database Operations & Lifecycle Manager
# ===========================================================================

class SsccService(CrudService):
    """
    Business service managing SSCC-18 pallet generation, hierarchical logistics persistence (T0137),
    and multi-tenant isolation.
    """

    def __init__(self, repo=None, partner_repo=None):
        repo = repo or EDI_SSCC_PALLET_REPO
        super().__init__(repo)
        self.partner_repo = partner_repo or EDI_PARTNER_REPO

    def get_company_prefix_for_partner(
        self,
        partner_id: Optional[int] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> str:
        """
        Retrieves the GS1 Company Prefix configured for a trading partner (T0134)
        or falls back to the system default prefix.
        """
        if not partner_id:
            return DEFAULT_GS1_COMPANY_PREFIX

        if tenant_id is None:
            tenant_id = get_current_tenant()

        kwargs = {"conn": conn} if conn is not None else {}
        try:
            partner = self.partner_repo.get(partner_id, **kwargs)
            if partner and partner.get("gs1_company_prefix"):
                prefix = str(partner["gs1_company_prefix"]).strip()
                if prefix.isdigit() and 4 <= len(prefix) <= 12:
                    return prefix
        except Exception as e:
            logger.warning(f"Failed to fetch GS1 company prefix for partner {partner_id}: {e}")

        return DEFAULT_GS1_COMPANY_PREFIX

    def generate_next_sscc(
        self,
        company_prefix: Optional[str] = None,
        extension_digit: Union[int, str] = 0,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> str:
        """
        Generates the next unique SSCC-18 using atomic sequence `seq_sscc_pallet_id` from the database
        or in-memory sequence fallback.
        """
        prefix = company_prefix or DEFAULT_GS1_COMPANY_PREFIX
        serial_val = None

        def _fetch_nextval(c):
            with c.cursor() as cur:
                cur.execute('SELECT nextval(\'"Nova".seq_sscc_pallet_id\')')
                row = cur.fetchone()
                if row and isinstance(row[0], (int, float)):
                    return int(row[0])
                if row and isinstance(row[0], str) and row[0].isdigit():
                    return int(row[0])
                return None

        if conn is not None:
            try:
                serial_val = _fetch_nextval(conn)
            except Exception as e:
                logger.warning(f"Error fetching nextval from seq_sscc_pallet_id with conn: {e}")
        else:
            try:
                c = get_connection()
                try:
                    serial_val = _fetch_nextval(c)
                finally:
                    release_connection(c)
            except Exception as e:
                logger.warning(f"Error acquiring connection for seq_sscc_pallet_id: {e}")

        # Fallback to timestamp counter if database sequence unavailable
        if serial_val is None:
            import time
            serial_val = int(time.time() * 1000) % 1000000

        return generate_sscc18(
            company_prefix=prefix,
            serial_number=serial_val,
            extension_digit=extension_digit,
        )

    def create_pallet(
        self,
        delivery_id: Optional[int] = None,
        sales_order_id: Optional[int] = None,
        pallet_number: Optional[str] = None,
        company_prefix: Optional[str] = None,
        package_type: str = "PALLET",
        parent_sscc_id: Optional[int] = None,
        gross_weight_kg: Optional[float] = None,
        net_weight_kg: Optional[float] = None,
        tare_weight_kg: Optional[float] = None,
        volume_cbm: Optional[float] = None,
        items_count: int = 0,
        contents_summary: Optional[Any] = None,
        status: str = "PACKED",
        extension_digit: Union[int, str] = 0,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generates an SSCC-18 barcode and creates a new packaging record in table T0137.
        """
        if tenant_id is None:
            tenant_id = get_current_tenant()

        sscc_barcode = self.generate_next_sscc(
            company_prefix=company_prefix,
            extension_digit=extension_digit,
            conn=conn,
            tenant_id=tenant_id,
        )

        pallet_data = {
            "sscc_barcode": sscc_barcode,
            "delivery_id": delivery_id,
            "sales_order_id": sales_order_id,
            "pallet_number": pallet_number or f"PLT-{sscc_barcode[-6:]}",
            "package_type": package_type or "PALLET",
            "parent_sscc_id": parent_sscc_id,
            "gross_weight_kg": gross_weight_kg,
            "net_weight_kg": net_weight_kg,
            "tare_weight_kg": tare_weight_kg,
            "volume_cbm": volume_cbm,
            "items_count": items_count,
            "contents_summary": contents_summary,
            "status": status or "PACKED",
        }

        kwargs = {"conn": conn} if conn is not None else {}
        created = self.repo.create(pallet_data, **kwargs)
        return created

    def create_pallet_hierarchy(
        self,
        delivery_id: int,
        hierarchy: Union[PackagingHierarchy, Dict[str, Any]],
        sales_order_id: Optional[int] = None,
        company_prefix: Optional[str] = None,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Persists a full packaging hierarchy (Pallet -> Box -> Item) into table T0137 within a single transaction.
        Generates SSCC-18 barcodes for any containers lacking one.
        """
        if isinstance(hierarchy, dict):
            hierarchy_obj = PackagingHierarchy(**hierarchy)
        else:
            hierarchy_obj = hierarchy

        hierarchy_obj.calculate_all_weights()
        created_records: List[Dict[str, Any]] = []

        with db_transaction(conn) as tx_conn:
            for pallet_idx, pallet in enumerate(hierarchy_obj.pallets, 1):
                sscc = pallet.sscc_barcode
                if not sscc or not validate_sscc(sscc):
                    sscc = self.generate_next_sscc(
                        company_prefix=company_prefix,
                        extension_digit=0,
                        conn=tx_conn,
                        tenant_id=tenant_id,
                    )
                    pallet.sscc_barcode = sscc

                pallet_num = pallet.pallet_number or f"PLT-{pallet_idx:02d}"
                pallet_record = self.create_pallet(
                    delivery_id=delivery_id,
                    sales_order_id=sales_order_id or hierarchy_obj.sales_order_id,
                    pallet_number=pallet_num,
                    company_prefix=company_prefix,
                    package_type=pallet.package_type or "PALLET",
                    gross_weight_kg=pallet.gross_weight_kg,
                    net_weight_kg=pallet.net_weight_kg,
                    tare_weight_kg=pallet.tare_weight_kg,
                    volume_cbm=pallet.volume_cbm,
                    items_count=pallet.total_units(),
                    contents_summary={
                        "boxes_count": len(pallet.boxes),
                        "items_count": pallet.total_units(),
                        "boxes": [b.model_dump() for b in pallet.boxes],
                        "direct_items": [it.model_dump() for it in pallet.direct_items],
                    },
                    status=pallet.status or "PACKED",
                    conn=tx_conn,
                    tenant_id=tenant_id,
                )
                pallet_id = pallet_record["id"]
                created_records.append(pallet_record)

                # Persist boxes if they have SSCCs or if sub-container tracking is needed
                for box_idx, box in enumerate(pallet.boxes, 1):
                    box_sscc = box.sscc_barcode
                    if not box_sscc:
                        box_sscc = self.generate_next_sscc(
                            company_prefix=company_prefix,
                            extension_digit=1,  # Extension digit 1 for cartons
                            conn=tx_conn,
                            tenant_id=tenant_id,
                        )
                        box.sscc_barcode = box_sscc

                    box_record = self.create_pallet(
                        delivery_id=delivery_id,
                        sales_order_id=sales_order_id or hierarchy_obj.sales_order_id,
                        pallet_number=box.box_number or f"{pallet_num}-BX{box_idx:02d}",
                        company_prefix=company_prefix,
                        package_type=box.package_type or "BOX",
                        parent_sscc_id=pallet_id,
                        gross_weight_kg=box.gross_weight_kg,
                        net_weight_kg=box.net_weight_kg,
                        tare_weight_kg=box.tare_weight_kg,
                        volume_cbm=box.volume_cbm,
                        items_count=sum(int(it.quantity) for it in box.items),
                        contents_summary={"items": [it.model_dump() for it in box.items]},
                        status=pallet.status or "PACKED",
                        conn=tx_conn,
                        tenant_id=tenant_id,
                    )
                    created_records.append(box_record)

        return created_records

    def get_pallets_for_delivery(
        self,
        delivery_id: int,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all SSCC packaging records linked to a specific delivery dispatch (T0016).
        """
        kwargs = {"conn": conn} if conn is not None else {}
        return self.repo.list(
            filters={"delivery_id": delivery_id},
            order_by="id ASC",
            **kwargs,
        )

    def get_pallet_by_sscc(
        self,
        sscc_barcode: str,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Queries table T0137 by 18-digit SSCC barcode.
        """
        clean_sscc = parse_sscc_gs1_128(sscc_barcode)
        kwargs = {"conn": conn} if conn is not None else {}
        pallets = self.repo.list(
            filters={"sscc_barcode": clean_sscc},
            limit=1,
            **kwargs,
        )
        return pallets[0] if pallets else None

    def update_pallet_status(
        self,
        pallet_id_or_sscc: Union[int, str],
        status: str,
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Updates the lifecycle status of a pallet (e.g. PACKED -> STAGED -> DISPATCHED -> DELIVERED).
        """
        kwargs = {"conn": conn} if conn is not None else {}
        if isinstance(pallet_id_or_sscc, int) or (isinstance(pallet_id_or_sscc, str) and pallet_id_or_sscc.isdigit() and len(pallet_id_or_sscc) < 10):
            pallet_id = int(pallet_id_or_sscc)
            return self.repo.update(pallet_id, {"status": status}, **kwargs)
        else:
            pallet = self.get_pallet_by_sscc(str(pallet_id_or_sscc), conn=conn, tenant_id=tenant_id)
            if not pallet:
                return None
            return self.repo.update(pallet["id"], {"status": status}, **kwargs)

    def generate_sscc_label_data(
        self,
        pallet_id_or_sscc: Union[int, str],
        conn=None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Produces formatted GS1 Logistics Label metadata for a saved pallet record.
        """
        if isinstance(pallet_id_or_sscc, int) or (isinstance(pallet_id_or_sscc, str) and pallet_id_or_sscc.isdigit() and len(pallet_id_or_sscc) < 10):
            kwargs = {"conn": conn} if conn is not None else {}
            pallet = self.repo.get(int(pallet_id_or_sscc), **kwargs)
        else:
            pallet = self.get_pallet_by_sscc(str(pallet_id_or_sscc), conn=conn, tenant_id=tenant_id)

        if not pallet:
            raise ValueError(f"SSCC pallet record not found for: {pallet_id_or_sscc}")

        return format_gs1_logistics_label(pallet)


# Default singleton instance
sscc_service = SsccService()

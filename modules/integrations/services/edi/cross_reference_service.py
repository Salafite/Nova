"""
Nova ERP — B2B EDI Gateway: SKU & Price Cross-Referencing Engine
Resolves buyer part numbers, GTINs, and vendor SKUs to Nova product IDs (T0001),
converts partner units of measure (UOM), and verifies buyer order prices against
customer contracts (T0122), price lists (T0083/T0084/T0120), and reference catalogs (T0125/T0128)
with configurable discrepancy tolerance thresholds.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import date, datetime
from pydantic import BaseModel, Field

from modules.core.repositories.base import CrudRepository
from modules.integrations.models.edi import (
    EdiLineDiscrepancy,
    EDI_PARTNER_REPO,
    EDI_SKU_MAPPING_REPO,
    EDI_CATALOG_ITEM_REPO,
)
from modules.sales.repositories.volume_pricing_repo import (
    CustomerContractRepository,
    VolumeTierBreakRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EDI Qualifier Mapping Constants
# ---------------------------------------------------------------------------

EDI_SKU_QUALIFIERS = {
    # ANSI X12 850 PO1 qualifiers
    'CB': 'BUYER_PART_NO',       # Buyer's Catalog Number
    'BP': 'BUYER_PART_NO',       # Buyer's Part Number
    'IN': 'BUYER_PART_NO',       # Buyer's Item Number
    'VN': 'VENDOR_PART_NO',      # Vendor's Item Number
    'VP': 'VENDOR_PART_NO',      # Vendor's Part Number
    'SK': 'VENDOR_PART_NO',      # Stock Keeping Unit
    'UP': 'GTIN',                # UPC (Universal Product Code)
    'EN': 'GTIN',                # EAN (European Article Number)
    'UK': 'GTIN',                # GTIN-14 / UCC-14
    'MG': 'MANUFACTURER_NO',     # Manufacturer's Part Number
    # UN/EDIFACT ORDERS LIN qualifiers
    'SRV': 'GTIN',               # GS1 Global Trade Item Number
    'SA': 'VENDOR_PART_NO',      # Supplier's Article Number
}


def normalize_sku_type(raw_type: Optional[str]) -> str:
    """
    Normalize EDI product qualifier codes (CB, BP, IN, VN, UP, EN, SRV)
    or descriptive names into canonical types: BUYER_PART_NO, GTIN, VENDOR_PART_NO, etc.
    """
    if not raw_type:
        return 'BUYER_PART_NO'

    upper_type = raw_type.strip().upper()
    if upper_type in EDI_SKU_QUALIFIERS:
        return EDI_SKU_QUALIFIERS[upper_type]

    if upper_type in ('EAN', 'UPC', 'GTIN', 'EAN13', 'EAN14', 'GTIN14', 'GTIN-14', 'GTIN-13'):
        return 'GTIN'
    if upper_type in ('BUYER', 'BUYER_SKU', 'BUYER_PART_NO', 'BUYER_ITEM_NO', 'PART_NO'):
        return 'BUYER_PART_NO'
    if upper_type in ('VENDOR', 'VENDOR_SKU', 'VENDOR_PART_NO', 'SUPPLIER_SKU', 'INTERNAL_SKU'):
        return 'VENDOR_PART_NO'

    return upper_type


# ---------------------------------------------------------------------------
# Data Models for Cross-Referencing Results
# ---------------------------------------------------------------------------

class SkuResolutionResult(BaseModel):
    """Result of resolving a partner/buyer SKU to an internal Nova product."""
    matched: bool = False
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    internal_sku: Optional[str] = None
    gtin: Optional[str] = None
    partner_sku: str
    partner_sku_type: str = 'BUYER_PART_NO'
    partner_uom: str = 'EA'
    internal_uom: str = 'EA'
    uom_conversion_factor: float = 1.0
    catalog_price: Optional[float] = None
    match_source: str = 'UNMATCHED'  # CROSS_REFERENCE_MATRIX_T0125, CATALOG_SYNC_T0128, PRODUCT_SKU_T0001, PRODUCT_BARCODE_T0004, UNMATCHED
    mapping_id: Optional[int] = None
    error_message: Optional[str] = None


class UomConversionResult(BaseModel):
    """Result of converting quantities and prices across unit of measures."""
    original_quantity: float
    original_uom: str
    converted_quantity: float
    converted_uom: str
    conversion_factor: float = 1.0
    is_converted: bool = False


class PriceVerificationResult(BaseModel):
    """Detailed price verification report comparing ordered vs expected pricing."""
    is_valid: bool = True
    is_discrepancy: bool = False
    discrepancy_type: str = 'NONE'  # NONE, PRICE_MISMATCH, UNDERPAYMENT, OVERPAYMENT, UOM_MISMATCH, PRODUCT_NOT_FOUND
    ordered_unit_price: float
    expected_unit_price: float
    effective_ordered_unit_price: float
    discrepancy_amount: float = 0.0
    discrepancy_percent: float = 0.0
    tolerance_percent: float = 0.0
    tolerance_exceeded: bool = False
    price_source: str = 'PRODUCT_BASE_T0001'  # CUSTOMER_CONTRACT_T0122, PRICE_LIST_T0084, VOLUME_TIER_T0120, CATALOG_PRICE_T0125, CATALOG_SYNC_T0128, PRODUCT_BASE_T0001, DEFAULT_ZERO
    contract_number: Optional[str] = None
    contract_id: Optional[int] = None
    price_list_id: Optional[int] = None
    action_required: str = 'NONE'  # NONE, PRICE_DISCREPANCY_HOLD, MANUAL_REVIEW
    details: Optional[str] = None


class LineCrossReferenceResult(BaseModel):
    """Complete cross-reference and pricing verification outcome for an order line."""
    line_number: int
    buyer_sku: str
    partner_sku_type: str = 'BUYER_PART_NO'
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    internal_sku: Optional[str] = None
    ordered_qty: float
    ordered_uom: str = 'EA'
    converted_qty: float
    internal_uom: str = 'EA'
    uom_factor: float = 1.0
    ordered_price: float
    expected_price: float
    line_total: float
    sku_resolution: SkuResolutionResult
    uom_conversion: UomConversionResult
    price_verification: PriceVerificationResult
    has_discrepancy: bool = False
    discrepancy_info: Optional[EdiLineDiscrepancy] = None


class OrderCrossReferenceSummary(BaseModel):
    """Aggregated cross-reference report for an entire purchase order interchange."""
    total_lines: int = 0
    matched_lines: int = 0
    unmatched_lines: int = 0
    discrepancy_lines: int = 0
    is_clean: bool = True
    recommended_status: str = 'Confirmed'  # Confirmed, Pending, PRICE_DISCREPANCY_HOLD, FAILED
    total_ordered_amount: float = 0.0
    total_expected_amount: float = 0.0
    price_discrepancies: List[EdiLineDiscrepancy] = Field(default_factory=list)
    line_results: List[LineCrossReferenceResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Core Repositories
# ---------------------------------------------------------------------------

PRODUCT_T0001_REPO = CrudRepository(
    'T0001',
    business_columns=[
        'id', 'name', 'sku', 'barcode', 'description', 'type',
        'price', 'cost_price', 'category', 'brand', 'tax_rate',
        'weight', 'volume', 'is_active', 'is_catch_weight'
    ]
)

PRODUCT_T0003_REPO = CrudRepository(
    'T0003',
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

CUSTOMER_T0010_REPO = CrudRepository(
    'T0010',
    business_columns=['id', 'name', 'customer_group', 'credit_limit', 'balance', 'price_list_id', 'payment_term_id']
)


# ---------------------------------------------------------------------------
# Cross Reference Service Engine
# ---------------------------------------------------------------------------

class CrossReferenceService:
    """
    B2B EDI Cross-Reference Service Engine.
    Handles automated SKU mapping resolution, UOM conversion, customer contract pricing,
    volume tier pricing, and price tolerance verification.
    """

    def __init__(
        self,
        partner_repo: Optional[CrudRepository] = None,
        sku_mapping_repo: Optional[CrudRepository] = None,
        catalog_repo: Optional[CrudRepository] = None,
        product_repo: Optional[CrudRepository] = None,
        barcode_repo: Optional[CrudRepository] = None,
        contract_repo: Optional[CustomerContractRepository] = None,
        price_list_repo: Optional[CrudRepository] = None,
        price_list_item_repo: Optional[CrudRepository] = None,
        volume_tier_repo: Optional[VolumeTierBreakRepository] = None,
        customer_repo: Optional[CrudRepository] = None,
    ):
        self.partner_repo = partner_repo or EDI_PARTNER_REPO
        self.sku_mapping_repo = sku_mapping_repo or EDI_SKU_MAPPING_REPO
        self.catalog_repo = catalog_repo or EDI_CATALOG_ITEM_REPO
        self.product_repo = product_repo or PRODUCT_T0001_REPO
        self.barcode_repo = barcode_repo or BARCODE_T0004_REPO
        self.contract_repo = contract_repo or CustomerContractRepository()
        self.price_list_repo = price_list_repo or PRICE_LIST_T0083_REPO
        self.price_list_item_repo = price_list_item_repo or PRICE_LIST_ITEM_T0084_REPO
        self.volume_tier_repo = volume_tier_repo or VolumeTierBreakRepository()
        self.customer_repo = customer_repo or CUSTOMER_T0010_REPO

    # -----------------------------------------------------------------------
    # 1. Product & SKU Resolution
    # -----------------------------------------------------------------------

    def resolve_sku(
        self,
        partner_id: Optional[int],
        buyer_sku: str,
        partner_sku_type: Optional[str] = None,
        gtin: Optional[str] = None,
        conn=None,
    ) -> SkuResolutionResult:
        """
        Resolve a buyer part number, GTIN barcode, or vendor SKU to an internal Nova product ID (T0001).

        Resolution Hierarchy:
        1. EDI SKU Cross-Reference Matrix table (T0125) for (partner_id, partner_sku) or GTIN.
        2. EDI Supplier Catalog table (T0128) with matched_product_id for (partner_id, buyer_sku/gtin).
        3. Internal Products catalog (T0001/T0003) by matching SKU or Barcode.
        4. Barcodes table (T0004) by matching Barcode to GTIN/EAN.
        """
        if not buyer_sku:
            return SkuResolutionResult(
                matched=False,
                partner_sku='',
                error_message="Buyer SKU cannot be empty",
            )

        clean_sku = str(buyer_sku).strip()
        clean_gtin = str(gtin).strip() if gtin else None
        canon_sku_type = normalize_sku_type(partner_sku_type)

        # -------------------------------------------------------------------
        # Step 1: Check EDI SKU Cross-Reference Matrix (T0125)
        # -------------------------------------------------------------------
        if partner_id and self.sku_mapping_repo:
            # Try by partner_sku
            filters = {'partner_id': partner_id, 'partner_sku': clean_sku, 'is_active': True}
            mappings = self.sku_mapping_repo.list(filters=filters, limit=1, conn=conn)

            # If not found and GTIN provided or clean_sku looks like a GTIN/EAN (digits only 8-14 chars)
            if not mappings and (clean_gtin or (clean_sku.isdigit() and len(clean_sku) in (8, 12, 13, 14))):
                lookup_gtin = clean_gtin or clean_sku
                mappings = self.sku_mapping_repo.list(
                    filters={'partner_id': partner_id, 'gtin': lookup_gtin, 'is_active': True},
                    limit=1,
                    conn=conn,
                )

            if mappings:
                m = mappings[0]
                prod_id = m.get('product_id')
                product = self._get_product_by_id(prod_id, conn=conn)

                return SkuResolutionResult(
                    matched=True,
                    product_id=prod_id,
                    product_name=product.get('name') if product else None,
                    internal_sku=product.get('sku') if product else None,
                    gtin=m.get('gtin') or (product.get('barcode') if product else None),
                    partner_sku=clean_sku,
                    partner_sku_type=m.get('partner_sku_type') or canon_sku_type,
                    partner_uom=m.get('partner_uom') or 'EA',
                    internal_uom=m.get('internal_uom') or 'EA',
                    uom_conversion_factor=float(m.get('uom_conversion_factor') or 1.0),
                    catalog_price=float(m.get('catalog_price')) if m.get('catalog_price') is not None else None,
                    match_source='CROSS_REFERENCE_MATRIX_T0125',
                    mapping_id=m.get('id'),
                )

        # -------------------------------------------------------------------
        # Step 2: Check EDI Supplier Catalog Sync (T0128)
        # -------------------------------------------------------------------
        if partner_id and self.catalog_repo:
            cat_filters = {'partner_id': partner_id, 'buyer_sku': clean_sku, 'is_active': True}
            cat_items = self.catalog_repo.list(filters=cat_filters, limit=1, conn=conn)

            if not cat_items and (clean_gtin or (clean_sku.isdigit() and len(clean_sku) in (8, 12, 13, 14))):
                lookup_gtin = clean_gtin or clean_sku
                cat_items = self.catalog_repo.list(
                    filters={'partner_id': partner_id, 'gtin': lookup_gtin, 'is_active': True},
                    limit=1,
                    conn=conn,
                )

            if cat_items and cat_items[0].get('matched_product_id'):
                c = cat_items[0]
                prod_id = c.get('matched_product_id')
                product = self._get_product_by_id(prod_id, conn=conn)

                return SkuResolutionResult(
                    matched=True,
                    product_id=prod_id,
                    product_name=product.get('name') if product else c.get('product_name'),
                    internal_sku=product.get('sku') if product else c.get('supplier_sku'),
                    gtin=c.get('gtin') or (product.get('barcode') if product else None),
                    partner_sku=clean_sku,
                    partner_sku_type=canon_sku_type,
                    partner_uom=c.get('uom') or 'EA',
                    internal_uom='EA',
                    uom_conversion_factor=float(c.get('pack_size') or 1.0),
                    catalog_price=float(c.get('list_price')) if c.get('list_price') is not None else None,
                    match_source='CATALOG_SYNC_T0128',
                    mapping_id=c.get('id'),
                )

        # -------------------------------------------------------------------
        # Step 3: Match against internal Products catalog (T0001 / T0003)
        # -------------------------------------------------------------------
        # Direct SKU match
        product = self._find_product_by_sku(clean_sku, conn=conn)

        # Barcode / GTIN match
        if not product:
            lookup_barcode = clean_gtin or clean_sku
            product = self._find_product_by_barcode(lookup_barcode, conn=conn)

        if product:
            return SkuResolutionResult(
                matched=True,
                product_id=product.get('id'),
                product_name=product.get('name'),
                internal_sku=product.get('sku'),
                gtin=product.get('barcode') or clean_gtin,
                partner_sku=clean_sku,
                partner_sku_type=canon_sku_type,
                partner_uom='EA',
                internal_uom='EA',
                uom_conversion_factor=1.0,
                catalog_price=float(product.get('price')) if product.get('price') is not None else None,
                match_source='PRODUCT_SKU_T0001',
            )

        # -------------------------------------------------------------------
        # Step 4: Check Secondary Barcodes table (T0004)
        # -------------------------------------------------------------------
        if self.barcode_repo:
            lookup_barcode = clean_gtin or clean_sku
            try:
                b_rows = self.barcode_repo.list(filters={'barcode': lookup_barcode}, limit=1, conn=conn)
                if b_rows and b_rows[0].get('product_id'):
                    prod_id = b_rows[0]['product_id']
                    product = self._get_product_by_id(prod_id, conn=conn)
                    if product:
                        return SkuResolutionResult(
                            matched=True,
                            product_id=prod_id,
                            product_name=product.get('name'),
                            internal_sku=product.get('sku'),
                            gtin=lookup_barcode,
                            partner_sku=clean_sku,
                            partner_sku_type='GTIN',
                            partner_uom='EA',
                            internal_uom='EA',
                            uom_conversion_factor=1.0,
                            catalog_price=float(product.get('price')) if product.get('price') is not None else None,
                            match_source='PRODUCT_BARCODE_T0004',
                        )
            except Exception as e:
                logger.debug(f"Barcode secondary lookup bypassed: {e}")

        # Unmatched
        return SkuResolutionResult(
            matched=False,
            partner_sku=clean_sku,
            partner_sku_type=canon_sku_type,
            gtin=clean_gtin,
            match_source='UNMATCHED',
            error_message=f"Buyer SKU '{clean_sku}' could not be resolved to any active product",
        )

    # -----------------------------------------------------------------------
    # 2. UOM Conversion
    # -----------------------------------------------------------------------

    def convert_uom_quantity(
        self,
        quantity: float,
        partner_uom: str,
        internal_uom: Optional[str] = None,
        uom_conversion_factor: Optional[float] = None,
        product_id: Optional[int] = None,
        conn=None,
    ) -> UomConversionResult:
        """
        Convert partner ordered quantity and UOM to internal base inventory quantity.
        E.g., Partner orders 10 CA (Cases) with conversion factor 12.0 -> 120 EA base units.
        """
        orig_qty = float(quantity or 0.0)
        p_uom = (partner_uom or 'EA').strip().upper()
        i_uom = (internal_uom or 'EA').strip().upper()
        factor = float(uom_conversion_factor or 1.0)

        if factor <= 0:
            factor = 1.0

        # If UOMs match and factor is 1.0, direct 1:1
        if p_uom == i_uom and factor == 1.0:
            return UomConversionResult(
                original_quantity=orig_qty,
                original_uom=p_uom,
                converted_quantity=orig_qty,
                converted_uom=i_uom,
                conversion_factor=1.0,
                is_converted=False,
            )

        converted_qty = round(orig_qty * factor, 4)
        return UomConversionResult(
            original_quantity=orig_qty,
            original_uom=p_uom,
            converted_quantity=converted_qty,
            converted_uom=i_uom,
            conversion_factor=factor,
            is_converted=(factor != 1.0 or p_uom != i_uom),
        )

    # -----------------------------------------------------------------------
    # 3. Contract & Price Resolution
    # -----------------------------------------------------------------------

    def resolve_contract_price(
        self,
        customer_id: int,
        product_id: int,
        quantity: float = 1.0,
        eval_date: Optional[date] = None,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Check for an active customer contract price override in T0122.
        Validates effective date range and minimum order quantity threshold.
        """
        if not customer_id or not product_id or not self.contract_repo:
            return None

        try:
            contracts = self.contract_repo.list(
                filters={'customer_id': customer_id, 'product_id': product_id, 'is_active': True, 'status': 'Active'},
                conn=conn,
            )
        except Exception as e:
            logger.warning(f"Error querying customer contracts: {e}")
            return None

        if not contracts:
            return None

        check_date = eval_date or date.today()
        for c in contracts:
            st = c.get('start_date')
            et = c.get('end_date')

            if isinstance(st, str):
                try:
                    st = date.fromisoformat(st)
                except Exception:
                    pass
            if isinstance(et, str):
                try:
                    et = date.fromisoformat(et)
                except Exception:
                    pass

            if st and check_date < st:
                continue
            if et and check_date > et:
                continue

            min_qty = float(c.get('min_order_quantity') or 1.0)
            if quantity < min_qty:
                continue

            return c

        return None

    def resolve_price_list_price(
        self,
        price_list_id: int,
        product_id: int,
        quantity: float = 1.0,
        conn=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate price list items (T0084) and volume tier breaks (T0120) for price list and product.
        """
        if not price_list_id or not product_id:
            return None

        # 1. Check volume tier breaks in T0120 first
        if self.volume_tier_repo:
            try:
                tiers = self.volume_tier_repo.list(
                    filters={'price_list_id': price_list_id, 'product_id': product_id, 'is_active': True},
                    order_by='min_quantity DESC',
                    conn=conn,
                )
                for tb in tiers:
                    min_q = float(tb.get('min_quantity') or 0.0)
                    max_q_val = tb.get('max_quantity')
                    max_q = float(max_q_val) if max_q_val is not None else None

                    if quantity >= min_q:
                        if max_q is None or quantity <= max_q:
                            return {
                                'price': float(tb.get('unit_price') or 0.0),
                                'discount_percentage': float(tb.get('discount_percentage') or 0.0),
                                'discount_type': tb.get('discount_type') or 'FixedPrice',
                                'source': 'VOLUME_TIER_T0120',
                                'tier_break_id': tb.get('id'),
                            }
            except Exception as e:
                logger.debug(f"Volume tier lookup error: {e}")

        # 2. Check standard price list item in T0084
        if self.price_list_item_repo:
            try:
                items = self.price_list_item_repo.list(
                    filters={'price_list_id': price_list_id, 'product_id': product_id, 'is_active': True},
                    conn=conn,
                )
                if items:
                    it = items[0]
                    return {
                        'price': float(it.get('price') or 0.0),
                        'discount_percentage': float(it.get('discount_percent') or 0.0),
                        'discount_amount': float(it.get('discount_amount') or 0.0),
                        'source': 'PRICE_LIST_T0084',
                        'item_id': it.get('id'),
                    }
            except Exception as e:
                logger.debug(f"Price list item lookup error: {e}")

        return None

    def resolve_expected_price(
        self,
        customer_id: Optional[int],
        product_id: int,
        quantity: float = 1.0,
        price_list_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        eval_date: Optional[date] = None,
        conn=None,
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Determine the expected contract/sales price following ERP pricing hierarchy:
        1. Customer Contract (T0122)
        2. Customer / Partner Price List (T0084) & Volume Tier Breaks (T0120)
        3. EDI SKU Mapping Catalog Price (T0125)
        4. Supplier Catalog Price (T0128)
        5. Base Product Price (T0001)

        Returns: (expected_unit_price, price_source_tag, metadata_dict)
        """
        meta: Dict[str, Any] = {}

        # 1. Customer Contract (T0122)
        if customer_id:
            contract = self.resolve_contract_price(customer_id, product_id, quantity, eval_date, conn=conn)
            if contract:
                raw_price = float(contract.get('contracted_price') or 0.0)
                disc_pct = float(contract.get('discount_percentage') or 0.0)
                final_price = raw_price * (1.0 - (disc_pct / 100.0)) if disc_pct > 0 else raw_price
                meta['contract_number'] = contract.get('contract_number')
                meta['contract_id'] = contract.get('id')
                meta['discount_percentage'] = disc_pct
                return (round(final_price, 4), 'CUSTOMER_CONTRACT_T0122', meta)

        # Determine effective price list ID
        effective_pl_id = price_list_id
        if not effective_pl_id and customer_id and self.customer_repo:
            try:
                cust = self.customer_repo.get(customer_id, conn=conn)
                if cust and cust.get('price_list_id'):
                    effective_pl_id = cust.get('price_list_id')
            except Exception:
                pass

        # 2. Price List & Volume Tier Breaks (T0084 / T0120)
        if effective_pl_id:
            pl_result = self.resolve_price_list_price(effective_pl_id, product_id, quantity, conn=conn)
            if pl_result and pl_result.get('price', 0) > 0:
                meta['price_list_id'] = effective_pl_id
                meta['tier_source'] = pl_result.get('source')
                return (round(pl_result['price'], 4), pl_result.get('source', 'PRICE_LIST_T0084'), meta)

        # 3. EDI SKU Mapping Catalog Price (T0125)
        if partner_id and self.sku_mapping_repo:
            try:
                mappings = self.sku_mapping_repo.list(
                    filters={'partner_id': partner_id, 'product_id': product_id, 'is_active': True},
                    limit=1,
                    conn=conn,
                )
                if mappings and mappings[0].get('catalog_price') is not None:
                    cat_p = float(mappings[0]['catalog_price'])
                    if cat_p > 0:
                        meta['mapping_id'] = mappings[0].get('id')
                        return (round(cat_p, 4), 'CATALOG_PRICE_T0125', meta)
            except Exception:
                pass

        # 4. Supplier Catalog Item Price (T0128)
        if partner_id and self.catalog_repo:
            try:
                cat_items = self.catalog_repo.list(
                    filters={'partner_id': partner_id, 'matched_product_id': product_id, 'is_active': True},
                    limit=1,
                    conn=conn,
                )
                if cat_items and cat_items[0].get('list_price') is not None:
                    lp = float(cat_items[0]['list_price'])
                    if lp > 0:
                        meta['catalog_item_id'] = cat_items[0].get('id')
                        return (round(lp, 4), 'CATALOG_SYNC_T0128', meta)
            except Exception:
                pass

        # 5. Product Base Unit Price (T0001)
        product = self._get_product_by_id(product_id, conn=conn)
        if product and product.get('price') is not None:
            base_p = float(product.get('price') or 0.0)
            meta['product_name'] = product.get('name')
            return (round(base_p, 4), 'PRODUCT_BASE_T0001', meta)

        return (0.0, 'DEFAULT_ZERO', meta)

    # -----------------------------------------------------------------------
    # 4. Price Verification & Discrepancy Tolerance Engine
    # -----------------------------------------------------------------------

    def verify_line_price(
        self,
        ordered_price: float,
        expected_price: float,
        tolerance_percent: float = 0.0,
        uom_factor: float = 1.0,
        price_source: str = 'PRODUCT_BASE_T0001',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PriceVerificationResult:
        """
        Verify buyer ordered unit price against contract / price list pricing with tolerance.

        UOM normalization:
        If buyer orders in Case (factor 12) at $120/case, and expected price is $10/ea,
        effective ordered price per single unit is $120 / 12 = $10/ea.
        """
        ordered_p = float(ordered_price or 0.0)
        expected_p = float(expected_price or 0.0)
        tol_pct = max(0.0, float(tolerance_percent or 0.0))
        factor = float(uom_factor or 1.0)
        if factor <= 0:
            factor = 1.0

        # Normalized ordered price per internal unit
        effective_ordered_p = round(ordered_p / factor, 4) if factor != 1.0 else round(ordered_p, 4)

        meta = metadata or {}
        contract_num = meta.get('contract_number')
        contract_id = meta.get('contract_id')
        price_list_id = meta.get('price_list_id')

        # If expected price is zero / not set
        if expected_p <= 0:
            return PriceVerificationResult(
                is_valid=True,
                is_discrepancy=False,
                discrepancy_type='NONE',
                ordered_unit_price=ordered_p,
                expected_unit_price=expected_p,
                effective_ordered_unit_price=effective_ordered_p,
                discrepancy_amount=0.0,
                discrepancy_percent=0.0,
                tolerance_percent=tol_pct,
                tolerance_exceeded=False,
                price_source=price_source,
                contract_number=contract_num,
                contract_id=contract_id,
                price_list_id=price_list_id,
                action_required='NONE',
                details="No expected contract/base price established",
            )

        diff = round(effective_ordered_p - expected_p, 4)
        abs_diff = abs(diff)
        pct_diff = round((abs_diff / expected_p) * 100.0, 2)

        # Check tolerance
        is_exceeded = pct_diff > tol_pct

        if not is_exceeded:
            # Within allowable tolerance
            return PriceVerificationResult(
                is_valid=True,
                is_discrepancy=False,
                discrepancy_type='NONE',
                ordered_unit_price=ordered_p,
                expected_unit_price=expected_p,
                effective_ordered_unit_price=effective_ordered_p,
                discrepancy_amount=diff,
                discrepancy_percent=pct_diff,
                tolerance_percent=tol_pct,
                tolerance_exceeded=False,
                price_source=price_source,
                contract_number=contract_num,
                contract_id=contract_id,
                price_list_id=price_list_id,
                action_required='NONE',
                details=f"Price matches or within tolerance ({pct_diff:.2f}% <= {tol_pct:.2f}%)",
            )

        # Exceeds tolerance -> Discrepancy
        disc_type = 'UNDERPAYMENT' if diff < 0 else 'OVERPAYMENT'
        action = 'PRICE_DISCREPANCY_HOLD'

        return PriceVerificationResult(
            is_valid=False,
            is_discrepancy=True,
            discrepancy_type=disc_type,
            ordered_unit_price=ordered_p,
            expected_unit_price=expected_p,
            effective_ordered_unit_price=effective_ordered_p,
            discrepancy_amount=diff,
            discrepancy_percent=pct_diff,
            tolerance_percent=tol_pct,
            tolerance_exceeded=True,
            price_source=price_source,
            contract_number=contract_num,
            contract_id=contract_id,
            price_list_id=price_list_id,
            action_required=action,
            details=f"Price discrepancy of {pct_diff:.2f}% exceeds tolerance threshold of {tol_pct:.2f}% (Ordered: ${effective_ordered_p:.2f}, Contract: ${expected_p:.2f})",
        )

    # -----------------------------------------------------------------------
    # 5. Full Line Item Cross-Referencing
    # -----------------------------------------------------------------------

    def cross_reference_line(
        self,
        partner_id: Optional[int],
        customer_id: Optional[int],
        line_number: int,
        buyer_sku: str,
        ordered_qty: float,
        ordered_price: float,
        partner_uom: str = 'EA',
        partner_sku_type: Optional[str] = None,
        gtin: Optional[str] = None,
        price_tolerance_percent: Optional[float] = None,
        price_list_id: Optional[int] = None,
        eval_date: Optional[date] = None,
        conn=None,
    ) -> LineCrossReferenceResult:
        """
        Cross-reference an individual line item from an inbound EDI 850 / ORDERS message.
        """
        # 1. Resolve SKU
        sku_res = self.resolve_sku(
            partner_id=partner_id,
            buyer_sku=buyer_sku,
            partner_sku_type=partner_sku_type,
            gtin=gtin,
            conn=conn,
        )

        effective_uom = partner_uom or sku_res.partner_uom or 'EA'
        uom_factor = sku_res.uom_conversion_factor or 1.0

        # 2. Convert UOM
        uom_res = self.convert_uom_quantity(
            quantity=ordered_qty,
            partner_uom=effective_uom,
            internal_uom=sku_res.internal_uom,
            uom_conversion_factor=uom_factor,
            product_id=sku_res.product_id,
            conn=conn,
        )

        # 3. Resolve Tolerance
        tol_pct = price_tolerance_percent
        if tol_pct is None and partner_id and self.partner_repo:
            try:
                partner = self.partner_repo.get(partner_id, conn=conn)
                if partner and partner.get('price_tolerance_percent') is not None:
                    tol_pct = float(partner.get('price_tolerance_percent'))
            except Exception:
                pass
        if tol_pct is None:
            tol_pct = 0.0

        # If product not matched
        if not sku_res.matched or not sku_res.product_id:
            price_ver = PriceVerificationResult(
                is_valid=False,
                is_discrepancy=True,
                discrepancy_type='PRODUCT_NOT_FOUND',
                ordered_unit_price=ordered_price,
                expected_unit_price=0.0,
                effective_ordered_unit_price=ordered_price,
                discrepancy_amount=0.0,
                discrepancy_percent=100.0,
                tolerance_percent=tol_pct,
                tolerance_exceeded=True,
                price_source='UNMATCHED',
                action_required='PRICE_DISCREPANCY_HOLD',
                details=sku_res.error_message or f"Product for buyer SKU '{buyer_sku}' not found",
            )
            discrepancy_obj = EdiLineDiscrepancy(
                line_number=line_number,
                buyer_sku=buyer_sku,
                partner_sku_type=sku_res.partner_sku_type,
                product_id=None,
                product_name=None,
                ordered_price=ordered_price,
                contract_price=0.0,
                discrepancy_percent=100.0,
                discrepancy_type='PRODUCT_NOT_FOUND',
                details=price_ver.details,
            )
            return LineCrossReferenceResult(
                line_number=line_number,
                buyer_sku=buyer_sku,
                partner_sku_type=sku_res.partner_sku_type,
                product_id=None,
                product_name=None,
                internal_sku=None,
                ordered_qty=ordered_qty,
                ordered_uom=effective_uom,
                converted_qty=uom_res.converted_quantity,
                internal_uom=sku_res.internal_uom,
                uom_factor=uom_factor,
                ordered_price=ordered_price,
                expected_price=0.0,
                line_total=round(ordered_qty * ordered_price, 2),
                sku_resolution=sku_res,
                uom_conversion=uom_res,
                price_verification=price_ver,
                has_discrepancy=True,
                discrepancy_info=discrepancy_obj,
            )

        # 4. Resolve Expected Price
        expected_p, price_source, meta = self.resolve_expected_price(
            customer_id=customer_id,
            product_id=sku_res.product_id,
            quantity=uom_res.converted_quantity,
            price_list_id=price_list_id,
            partner_id=partner_id,
            eval_date=eval_date,
            conn=conn,
        )

        # 5. Verify Price with Tolerance
        price_ver = self.verify_line_price(
            ordered_price=ordered_price,
            expected_price=expected_p,
            tolerance_percent=tol_pct,
            uom_factor=uom_factor,
            price_source=price_source,
            metadata=meta,
        )

        discrepancy_obj = None
        if price_ver.is_discrepancy:
            discrepancy_obj = EdiLineDiscrepancy(
                line_number=line_number,
                buyer_sku=buyer_sku,
                partner_sku_type=sku_res.partner_sku_type,
                product_id=sku_res.product_id,
                product_name=sku_res.product_name,
                ordered_price=ordered_price,
                contract_price=expected_p,
                discrepancy_percent=price_ver.discrepancy_percent,
                discrepancy_type=price_ver.discrepancy_type,
                details=price_ver.details,
            )

        line_total = round(ordered_qty * ordered_price, 2)

        return LineCrossReferenceResult(
            line_number=line_number,
            buyer_sku=buyer_sku,
            partner_sku_type=sku_res.partner_sku_type,
            product_id=sku_res.product_id,
            product_name=sku_res.product_name,
            internal_sku=sku_res.internal_sku,
            ordered_qty=ordered_qty,
            ordered_uom=effective_uom,
            converted_qty=uom_res.converted_quantity,
            internal_uom=sku_res.internal_uom,
            uom_factor=uom_factor,
            ordered_price=ordered_price,
            expected_price=expected_p,
            line_total=line_total,
            sku_resolution=sku_res,
            uom_conversion=uom_res,
            price_verification=price_ver,
            has_discrepancy=price_ver.is_discrepancy,
            discrepancy_info=discrepancy_obj,
        )

    # -----------------------------------------------------------------------
    # 6. Entire Order Cross-Referencing
    # -----------------------------------------------------------------------

    def cross_reference_order(
        self,
        partner_id: Optional[int],
        customer_id: Optional[int],
        line_items: List[Dict[str, Any]],
        price_tolerance_percent: Optional[float] = None,
        price_list_id: Optional[int] = None,
        auto_confirm_orders: bool = False,
        eval_date: Optional[date] = None,
        conn=None,
    ) -> OrderCrossReferenceSummary:
        """
        Process and cross-reference all line items from an inbound EDI 850 / ORDERS document.
        Calculates totals, aggregates discrepancies, and assigns recommended order status.
        """
        summary = OrderCrossReferenceSummary(total_lines=len(line_items))
        if not line_items:
            summary.recommended_status = 'Pending'
            return summary

        total_ordered_amount = 0.0
        total_expected_amount = 0.0

        for idx, item in enumerate(line_items, start=1):
            line_num = int(item.get('line_number') or idx)
            b_sku = str(item.get('buyer_sku') or item.get('partner_sku') or item.get('sku') or '').strip()
            qty = float(item.get('ordered_qty') or item.get('quantity') or item.get('qty') or 0.0)
            price = float(item.get('ordered_price') or item.get('unit_price') or item.get('price') or 0.0)
            uom = str(item.get('partner_uom') or item.get('uom') or 'EA')
            sku_type = item.get('partner_sku_type') or item.get('sku_type')
            gtin = item.get('gtin')

            line_res = self.cross_reference_line(
                partner_id=partner_id,
                customer_id=customer_id,
                line_number=line_num,
                buyer_sku=b_sku,
                ordered_qty=qty,
                ordered_price=price,
                partner_uom=uom,
                partner_sku_type=sku_type,
                gtin=gtin,
                price_tolerance_percent=price_tolerance_percent,
                price_list_id=price_list_id,
                eval_date=eval_date,
                conn=conn,
            )

            summary.line_results.append(line_res)
            total_ordered_amount += line_res.line_total
            total_expected_amount += round(line_res.converted_qty * line_res.expected_price, 2)

            if line_res.sku_resolution.matched:
                summary.matched_lines += 1
            else:
                summary.unmatched_lines += 1
                summary.errors.append(f"Line {line_num}: Unmatched SKU '{b_sku}'")

            if line_res.has_discrepancy:
                summary.discrepancy_lines += 1
                if line_res.discrepancy_info:
                    summary.price_discrepancies.append(line_res.discrepancy_info)

        summary.total_ordered_amount = round(total_ordered_amount, 2)
        summary.total_expected_amount = round(total_expected_amount, 2)

        # Status determination
        if summary.unmatched_lines > 0:
            summary.is_clean = False
            summary.recommended_status = 'PRICE_DISCREPANCY_HOLD'
        elif summary.discrepancy_lines > 0:
            summary.is_clean = False
            summary.recommended_status = 'PRICE_DISCREPANCY_HOLD'
        else:
            summary.is_clean = True
            summary.recommended_status = 'Confirmed' if auto_confirm_orders else 'Pending'

        return summary

    # -----------------------------------------------------------------------
    # 7. SKU Mapping CRUD & Utility Helpers
    # -----------------------------------------------------------------------

    def create_or_update_mapping(
        self,
        partner_id: int,
        product_id: int,
        partner_sku: str,
        partner_sku_type: str = 'BUYER_PART_NO',
        gtin: Optional[str] = None,
        partner_uom: str = 'EA',
        internal_uom: str = 'EA',
        uom_conversion_factor: float = 1.0,
        catalog_price: Optional[float] = None,
        is_active: bool = True,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Create or update an entry in the EDI SKU Cross-Reference Matrix (T0125).
        """
        clean_sku = partner_sku.strip()
        canon_type = normalize_sku_type(partner_sku_type)

        existing = self.sku_mapping_repo.list(
            filters={'partner_id': partner_id, 'partner_sku': clean_sku},
            limit=1,
            conn=conn,
        )

        payload = {
            'partner_id': partner_id,
            'product_id': product_id,
            'partner_sku': clean_sku,
            'partner_sku_type': canon_type,
            'gtin': gtin.strip() if gtin else None,
            'partner_uom': partner_uom.strip().upper(),
            'internal_uom': internal_uom.strip().upper(),
            'uom_conversion_factor': float(uom_conversion_factor or 1.0),
            'catalog_price': float(catalog_price) if catalog_price is not None else None,
            'is_active': is_active,
        }

        if existing:
            mapping_id = existing[0]['id']
            return self.sku_mapping_repo.update(mapping_id, payload, conn=conn)
        else:
            return self.sku_mapping_repo.create(payload, conn=conn)

    def bulk_import_mappings(
        self,
        partner_id: int,
        mappings: List[Dict[str, Any]],
        conn=None,
    ) -> Dict[str, Any]:
        """
        Bulk import SKU mappings for a trading partner.
        """
        created = 0
        updated = 0
        errors = []

        for idx, m in enumerate(mappings, start=1):
            p_sku = m.get('partner_sku') or m.get('buyer_sku')
            prod_id = m.get('product_id')

            if not p_sku or not prod_id:
                errors.append(f"Row {idx}: Missing partner_sku or product_id")
                continue

            try:
                clean_sku = str(p_sku).strip()
                existing = self.sku_mapping_repo.list(
                    filters={'partner_id': partner_id, 'partner_sku': clean_sku},
                    limit=1,
                    conn=conn,
                )

                payload = {
                    'partner_id': partner_id,
                    'product_id': int(prod_id),
                    'partner_sku': clean_sku,
                    'partner_sku_type': normalize_sku_type(m.get('partner_sku_type') or m.get('sku_type')),
                    'gtin': m.get('gtin'),
                    'partner_uom': (m.get('partner_uom') or 'EA').strip().upper(),
                    'internal_uom': (m.get('internal_uom') or 'EA').strip().upper(),
                    'uom_conversion_factor': float(m.get('uom_conversion_factor') or 1.0),
                    'catalog_price': float(m['catalog_price']) if m.get('catalog_price') is not None else None,
                    'is_active': m.get('is_active', True),
                }

                if existing:
                    self.sku_mapping_repo.update(existing[0]['id'], payload, conn=conn)
                    updated += 1
                else:
                    self.sku_mapping_repo.create(payload, conn=conn)
                    created += 1
            except Exception as e:
                errors.append(f"Row {idx} ({p_sku}): {str(e)}")

        return {
            'total': len(mappings),
            'created': created,
            'updated': updated,
            'errors': errors,
        }

    # -----------------------------------------------------------------------
    # Internal Product Lookup Helpers
    # -----------------------------------------------------------------------

    def _get_product_by_id(self, product_id: Optional[int], conn=None) -> Optional[Dict[str, Any]]:
        if not product_id:
            return None
        try:
            p = self.product_repo.get(product_id, conn=conn)
            if p:
                return p
        except Exception:
            pass

        # Fallback to T0003
        try:
            return PRODUCT_T0003_REPO.get(product_id, conn=conn)
        except Exception:
            return None

    def _find_product_by_sku(self, sku: str, conn=None) -> Optional[Dict[str, Any]]:
        try:
            prods = self.product_repo.list(filters={'sku': sku, 'is_active': True}, limit=1, conn=conn)
            if prods:
                return prods[0]
        except Exception:
            pass

        try:
            prods = PRODUCT_T0003_REPO.list(filters={'sku': sku, 'is_active': True}, limit=1, conn=conn)
            if prods:
                return prods[0]
        except Exception:
            pass

        return None

    def _find_product_by_barcode(self, barcode: str, conn=None) -> Optional[Dict[str, Any]]:
        try:
            prods = self.product_repo.list(filters={'barcode': barcode, 'is_active': True}, limit=1, conn=conn)
            if prods:
                return prods[0]
        except Exception:
            pass

        try:
            prods = PRODUCT_T0003_REPO.list(filters={'barcode': barcode, 'is_active': True}, limit=1, conn=conn)
            if prods:
                return prods[0]
        except Exception:
            pass

        return None


# Global singleton instance
cross_reference_service = CrossReferenceService()

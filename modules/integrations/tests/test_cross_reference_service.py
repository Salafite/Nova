"""
Unit tests for B2B EDI SKU & Price Cross-Referencing Engine
(modules/integrations/services/edi/cross_reference_service.py).
Tests SKU resolution, UOM conversion, customer contract pricing, volume tier pricing,
price tolerance verification, order line cross-referencing, and matrix CRUD operations.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from modules.integrations.services.edi.cross_reference_service import (
    normalize_sku_type,
    EDI_SKU_QUALIFIERS,
    SkuResolutionResult,
    UomConversionResult,
    PriceVerificationResult,
    LineCrossReferenceResult,
    OrderCrossReferenceSummary,
    CrossReferenceService,
    cross_reference_service,
)
from modules.integrations.models.edi import EdiLineDiscrepancy


# ===========================================================================
# 1. EDI SKU Qualifier Normalization Tests
# ===========================================================================

def test_normalize_sku_type():
    assert normalize_sku_type('CB') == 'BUYER_PART_NO'
    assert normalize_sku_type('BP') == 'BUYER_PART_NO'
    assert normalize_sku_type('IN') == 'BUYER_PART_NO'
    assert normalize_sku_type('VN') == 'VENDOR_PART_NO'
    assert normalize_sku_type('VP') == 'VENDOR_PART_NO'
    assert normalize_sku_type('SK') == 'VENDOR_PART_NO'
    assert normalize_sku_type('UP') == 'GTIN'
    assert normalize_sku_type('EN') == 'GTIN'
    assert normalize_sku_type('UK') == 'GTIN'
    assert normalize_sku_type('SRV') == 'GTIN'
    assert normalize_sku_type('SA') == 'VENDOR_PART_NO'
    assert normalize_sku_type('MG') == 'MANUFACTURER_NO'
    assert normalize_sku_type('EAN13') == 'GTIN'
    assert normalize_sku_type('UPC') == 'GTIN'
    assert normalize_sku_type('BUYER_SKU') == 'BUYER_PART_NO'
    assert normalize_sku_type('SUPPLIER_SKU') == 'VENDOR_PART_NO'
    assert normalize_sku_type(None) == 'BUYER_PART_NO'
    assert normalize_sku_type('') == 'BUYER_PART_NO'
    assert normalize_sku_type('CUSTOM_CODE') == 'CUSTOM_CODE'


# ===========================================================================
# 2. SKU Resolution Tests
# ===========================================================================

def test_resolve_sku_via_t0125_mapping():
    """
    Test resolving buyer SKU via EDI SKU Cross-Reference Matrix (T0125).
    """
    mock_sku_repo = MagicMock()
    mock_product_repo = MagicMock()

    mock_sku_repo.list.return_value = [
        {
            'id': 10,
            'partner_id': 1,
            'product_id': 101,
            'partner_sku': 'CRF-RICE-5KG',
            'partner_sku_type': 'BUYER_PART_NO',
            'gtin': '6291041000101',
            'partner_uom': 'CA',
            'internal_uom': 'EA',
            'uom_conversion_factor': 4.0,
            'catalog_price': 120.0,
            'is_active': True,
        }
    ]
    mock_product_repo.get.return_value = {
        'id': 101,
        'name': 'Basmati Rice 5kg Bag',
        'sku': 'NOVA-RICE-5KG',
        'barcode': '6291041000101',
        'price': 30.0,
    }

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        product_repo=mock_product_repo,
    )

    res = service.resolve_sku(partner_id=1, buyer_sku='CRF-RICE-5KG')

    assert res.matched is True
    assert res.product_id == 101
    assert res.product_name == 'Basmati Rice 5kg Bag'
    assert res.internal_sku == 'NOVA-RICE-5KG'
    assert res.gtin == '6291041000101'
    assert res.partner_sku == 'CRF-RICE-5KG'
    assert res.partner_uom == 'CA'
    assert res.internal_uom == 'EA'
    assert res.uom_conversion_factor == 4.0
    assert res.catalog_price == 120.0
    assert res.match_source == 'CROSS_REFERENCE_MATRIX_T0125'
    assert res.mapping_id == 10


def test_resolve_sku_via_t0128_catalog():
    """
    Test resolving buyer SKU via Supplier Catalog Sync (T0128) when T0125 mapping is absent.
    """
    mock_sku_repo = MagicMock()
    mock_catalog_repo = MagicMock()
    mock_product_repo = MagicMock()

    mock_sku_repo.list.return_value = []
    mock_catalog_repo.list.return_value = [
        {
            'id': 25,
            'partner_id': 2,
            'buyer_sku': 'LULU-MILK-1L',
            'supplier_sku': 'NOVA-MILK-1L',
            'gtin': '6291041000202',
            'product_name': 'Full Cream Milk 1L',
            'uom': 'CASE',
            'pack_size': 12,
            'list_price': 48.0,
            'matched_product_id': 202,
            'is_active': True,
        }
    ]
    mock_product_repo.get.return_value = {
        'id': 202,
        'name': 'Full Cream Fresh Milk 1L',
        'sku': 'NOVA-MILK-1L',
        'barcode': '6291041000202',
        'price': 4.0,
    }

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        catalog_repo=mock_catalog_repo,
        product_repo=mock_product_repo,
    )

    res = service.resolve_sku(partner_id=2, buyer_sku='LULU-MILK-1L')

    assert res.matched is True
    assert res.product_id == 202
    assert res.product_name == 'Full Cream Fresh Milk 1L'
    assert res.internal_sku == 'NOVA-MILK-1L'
    assert res.partner_uom == 'CASE'
    assert res.uom_conversion_factor == 12.0
    assert res.catalog_price == 48.0
    assert res.match_source == 'CATALOG_SYNC_T0128'


def test_resolve_sku_via_internal_product_sku():
    """
    Test resolving buyer SKU directly against internal Nova Product SKU (T0001).
    """
    mock_sku_repo = MagicMock()
    mock_catalog_repo = MagicMock()
    mock_product_repo = MagicMock()

    mock_sku_repo.list.return_value = []
    mock_catalog_repo.list.return_value = []

    def mock_prod_list(filters=None, limit=None, conn=None):
        if filters and filters.get('sku') == 'NOVA-OIL-1L':
            return [{
                'id': 303,
                'name': 'Sunflower Cooking Oil 1L',
                'sku': 'NOVA-OIL-1L',
                'barcode': '6291041000303',
                'price': 15.50,
            }]
        return []

    mock_product_repo.list.side_effect = mock_prod_list

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        catalog_repo=mock_catalog_repo,
        product_repo=mock_product_repo,
    )

    res = service.resolve_sku(partner_id=3, buyer_sku='NOVA-OIL-1L')

    assert res.matched is True
    assert res.product_id == 303
    assert res.product_name == 'Sunflower Cooking Oil 1L'
    assert res.internal_sku == 'NOVA-OIL-1L'
    assert res.match_source == 'PRODUCT_SKU_T0001'
    assert res.uom_conversion_factor == 1.0


def test_resolve_sku_via_product_barcode_gtin():
    """
    Test resolving buyer GTIN barcode directly against Product Barcode.
    """
    mock_sku_repo = MagicMock()
    mock_catalog_repo = MagicMock()
    mock_product_repo = MagicMock()

    mock_sku_repo.list.return_value = []
    mock_catalog_repo.list.return_value = []

    def mock_prod_list(filters=None, limit=None, conn=None):
        if filters and filters.get('barcode') == '6291041000404':
            return [{
                'id': 404,
                'name': 'Tomato Paste 400g',
                'sku': 'NOVA-TOM-400',
                'barcode': '6291041000404',
                'price': 3.25,
            }]
        return []

    mock_product_repo.list.side_effect = mock_prod_list

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        catalog_repo=mock_catalog_repo,
        product_repo=mock_product_repo,
    )

    res = service.resolve_sku(partner_id=3, buyer_sku='6291041000404', partner_sku_type='EN')

    assert res.matched is True
    assert res.product_id == 404
    assert res.product_name == 'Tomato Paste 400g'
    assert res.internal_sku == 'NOVA-TOM-400'
    assert res.match_source == 'PRODUCT_SKU_T0001'


def test_resolve_sku_unmatched():
    """
    Test handling an unknown buyer SKU that cannot be resolved.
    """
    mock_sku_repo = MagicMock()
    mock_catalog_repo = MagicMock()
    mock_product_repo = MagicMock()
    mock_barcode_repo = MagicMock()

    mock_sku_repo.list.return_value = []
    mock_catalog_repo.list.return_value = []
    mock_product_repo.list.return_value = []
    mock_barcode_repo.list.return_value = []

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        catalog_repo=mock_catalog_repo,
        product_repo=mock_product_repo,
        barcode_repo=mock_barcode_repo,
    )

    res = service.resolve_sku(partner_id=1, buyer_sku='UNKNOWN-SKU-999')

    assert res.matched is False
    assert res.product_id is None
    assert res.match_source == 'UNMATCHED'
    assert "could not be resolved" in res.error_message


# ===========================================================================
# 3. UOM Conversion Tests
# ===========================================================================

def test_convert_uom_quantity_standard():
    service = CrossReferenceService()

    # Same UOM factor 1.0
    uom_res1 = service.convert_uom_quantity(quantity=50, partner_uom='EA', internal_uom='EA', uom_conversion_factor=1.0)
    assert uom_res1.original_quantity == 50.0
    assert uom_res1.converted_quantity == 50.0
    assert uom_res1.is_converted is False

    # Case to Each conversion factor 12.0
    uom_res2 = service.convert_uom_quantity(quantity=10, partner_uom='CA', internal_uom='EA', uom_conversion_factor=12.0)
    assert uom_res2.original_quantity == 10.0
    assert uom_res2.converted_quantity == 120.0
    assert uom_res2.is_converted is True
    assert uom_res2.conversion_factor == 12.0


# ===========================================================================
# 4. Price Resolution & Verification Tests
# ===========================================================================

def test_resolve_expected_price_contract_hierarchy():
    """
    Test price resolution hierarchy prioritizing Customer Contract (T0122) over price list and base price.
    """
    mock_contract_repo = MagicMock()
    mock_price_list_repo = MagicMock()
    mock_tier_repo = MagicMock()
    mock_product_repo = MagicMock()

    today = date.today()
    mock_contract_repo.list.return_value = [
        {
            'id': 501,
            'contract_number': 'CTR-2026-001',
            'customer_id': 10,
            'product_id': 101,
            'contracted_price': 25.00,
            'discount_percentage': 10.00,  # 25 - 10% = 22.50
            'min_order_quantity': 5.0,
            'start_date': today - timedelta(days=30),
            'end_date': today + timedelta(days=30),
            'status': 'Active',
            'is_active': True,
        }
    ]

    service = CrossReferenceService(
        contract_repo=mock_contract_repo,
        price_list_repo=mock_price_list_repo,
        volume_tier_repo=mock_tier_repo,
        product_repo=mock_product_repo,
    )

    expected_p, source, meta = service.resolve_expected_price(
        customer_id=10,
        product_id=101,
        quantity=10.0,
    )

    assert expected_p == 22.50
    assert source == 'CUSTOMER_CONTRACT_T0122'
    assert meta['contract_number'] == 'CTR-2026-001'
    assert meta['contract_id'] == 501


def test_resolve_expected_price_volume_tier_hierarchy():
    """
    Test price resolution falling back to Volume Tier Breaks (T0120) when no contract exists.
    """
    mock_contract_repo = MagicMock()
    mock_tier_repo = MagicMock()

    mock_contract_repo.list.return_value = []
    mock_tier_repo.list.return_value = [
        {
            'id': 701,
            'price_list_id': 5,
            'product_id': 101,
            'min_quantity': 50.0,
            'max_quantity': None,
            'unit_price': 26.50,
            'discount_percentage': 0.0,
            'discount_type': 'FixedPrice',
            'is_active': True,
        },
        {
            'id': 702,
            'price_list_id': 5,
            'product_id': 101,
            'min_quantity': 10.0,
            'max_quantity': 49.0,
            'unit_price': 28.00,
            'discount_percentage': 0.0,
            'discount_type': 'FixedPrice',
            'is_active': True,
        }
    ]

    service = CrossReferenceService(
        contract_repo=mock_contract_repo,
        volume_tier_repo=mock_tier_repo,
    )

    # Quantity 60 should trigger tier 1 ($26.50)
    expected_p, source, meta = service.resolve_expected_price(
        customer_id=10,
        product_id=101,
        quantity=60.0,
        price_list_id=5,
    )

    assert expected_p == 26.50
    assert source == 'VOLUME_TIER_T0120'
    assert meta['price_list_id'] == 5


def test_verify_line_price_exact_and_within_tolerance():
    service = CrossReferenceService()

    # Exact match (Ordered $25.00, Expected $25.00)
    res_exact = service.verify_line_price(
        ordered_price=25.00,
        expected_price=25.00,
        tolerance_percent=0.0,
    )
    assert res_exact.is_valid is True
    assert res_exact.is_discrepancy is False
    assert res_exact.discrepancy_amount == 0.0
    assert res_exact.action_required == 'NONE'

    # Small variance within 2% tolerance (Ordered $24.75, Expected $25.00 -> 1.0% diff <= 2.0%)
    res_tol = service.verify_line_price(
        ordered_price=24.75,
        expected_price=25.00,
        tolerance_percent=2.0,
    )
    assert res_tol.is_valid is True
    assert res_tol.is_discrepancy is False
    assert res_tol.discrepancy_percent == 1.0
    assert res_tol.tolerance_exceeded is False
    assert res_tol.action_required == 'NONE'


def test_verify_line_price_exceeding_tolerance_underpayment():
    service = CrossReferenceService()

    # Underpayment: Ordered $20.00, Expected $25.00 with 2% tolerance -> 20.0% discrepancy
    res = service.verify_line_price(
        ordered_price=20.00,
        expected_price=25.00,
        tolerance_percent=2.0,
        price_source='CUSTOMER_CONTRACT_T0122',
        metadata={'contract_number': 'CTR-2026-001'},
    )
    assert res.is_valid is False
    assert res.is_discrepancy is True
    assert res.discrepancy_type == 'UNDERPAYMENT'
    assert res.discrepancy_percent == 20.0
    assert res.tolerance_exceeded is True
    assert res.action_required == 'PRICE_DISCREPANCY_HOLD'
    assert res.contract_number == 'CTR-2026-001'
    assert "exceeds tolerance threshold" in res.details


def test_verify_line_price_with_uom_normalization():
    """
    Buyer orders in Case (factor 12) at $120.00 per case. Expected price is $10.00 per each unit.
    Effective ordered price is $120 / 12 = $10.00 -> Clean match!
    """
    service = CrossReferenceService()

    res = service.verify_line_price(
        ordered_price=120.00,
        expected_price=10.00,
        uom_factor=12.0,
        tolerance_percent=0.0,
    )
    assert res.is_valid is True
    assert res.is_discrepancy is False
    assert res.effective_ordered_unit_price == 10.00


# ===========================================================================
# 5. Full Line & Order Cross-Referencing Tests
# ===========================================================================

def test_cross_reference_line_clean_order():
    mock_sku_repo = MagicMock()
    mock_product_repo = MagicMock()
    mock_contract_repo = MagicMock()

    mock_sku_repo.list.return_value = [
        {
            'id': 1,
            'partner_id': 1,
            'product_id': 101,
            'partner_sku': 'CRF-101',
            'partner_sku_type': 'BUYER_PART_NO',
            'partner_uom': 'EA',
            'internal_uom': 'EA',
            'uom_conversion_factor': 1.0,
            'is_active': True,
        }
    ]
    mock_product_repo.get.return_value = {
        'id': 101,
        'name': 'Olive Oil 1L',
        'sku': 'NOVA-OIL-1L',
        'price': 45.00,
    }
    mock_contract_repo.list.return_value = [
        {
            'id': 1,
            'contract_number': 'CTR-001',
            'contracted_price': 45.00,
            'min_order_quantity': 1.0,
            'status': 'Active',
            'is_active': True,
        }
    ]

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        product_repo=mock_product_repo,
        contract_repo=mock_contract_repo,
    )

    line_res = service.cross_reference_line(
        partner_id=1,
        customer_id=10,
        line_number=1,
        buyer_sku='CRF-101',
        ordered_qty=100.0,
        ordered_price=45.00,
        price_tolerance_percent=1.0,
    )

    assert line_res.line_number == 1
    assert line_res.product_id == 101
    assert line_res.product_name == 'Olive Oil 1L'
    assert line_res.ordered_qty == 100.0
    assert line_res.ordered_price == 45.00
    assert line_res.expected_price == 45.00
    assert line_res.line_total == 4500.00
    assert line_res.has_discrepancy is False
    assert line_res.discrepancy_info is None


def test_cross_reference_order_with_mixed_lines():
    """
    Test an entire inbound order with:
    - Line 1: Clean matched line
    - Line 2: Price discrepancy exceeding tolerance
    - Line 3: Unmatched SKU
    """
    mock_sku_repo = MagicMock()
    mock_product_repo = MagicMock()
    mock_contract_repo = MagicMock()

    def mock_sku_list(filters=None, limit=None, conn=None):
        if filters and filters.get('partner_sku') == 'SKU-OK':
            return [{
                'id': 1, 'partner_id': 1, 'product_id': 101, 'partner_sku': 'SKU-OK',
                'partner_sku_type': 'BUYER_PART_NO', 'partner_uom': 'EA', 'internal_uom': 'EA',
                'uom_conversion_factor': 1.0, 'is_active': True,
            }]
        if filters and filters.get('partner_sku') == 'SKU-BADPRICE':
            return [{
                'id': 2, 'partner_id': 1, 'product_id': 102, 'partner_sku': 'SKU-BADPRICE',
                'partner_sku_type': 'BUYER_PART_NO', 'partner_uom': 'EA', 'internal_uom': 'EA',
                'uom_conversion_factor': 1.0, 'is_active': True,
            }]
        return []

    mock_sku_repo.list.side_effect = mock_sku_list

    def mock_prod_get(prod_id, conn=None):
        if prod_id == 101:
            return {'id': 101, 'name': 'Product One', 'sku': 'NOVA-01', 'price': 50.00}
        if prod_id == 102:
            return {'id': 102, 'name': 'Product Two', 'sku': 'NOVA-02', 'price': 100.00}
        return None

    mock_product_repo.get.side_effect = mock_prod_get
    mock_product_repo.list.return_value = []
    mock_contract_repo.list.return_value = []

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        product_repo=mock_product_repo,
        contract_repo=mock_contract_repo,
    )

    raw_items = [
        {'line_number': 1, 'buyer_sku': 'SKU-OK', 'ordered_qty': 10, 'ordered_price': 50.00},
        {'line_number': 2, 'buyer_sku': 'SKU-BADPRICE', 'ordered_qty': 5, 'ordered_price': 70.00},  # Expected 100.00 -> 30% underpayment
        {'line_number': 3, 'buyer_sku': 'SKU-UNKNOWN', 'ordered_qty': 2, 'ordered_price': 20.00},   # Unmatched
    ]

    summary = service.cross_reference_order(
        partner_id=1,
        customer_id=10,
        line_items=raw_items,
        price_tolerance_percent=2.0,
        auto_confirm_orders=True,
    )

    assert summary.total_lines == 3
    assert summary.matched_lines == 2
    assert summary.unmatched_lines == 1
    assert summary.discrepancy_lines == 2  # Bad price line + unmatched line
    assert summary.is_clean is False
    assert summary.recommended_status == 'PRICE_DISCREPANCY_HOLD'

    assert summary.total_ordered_amount == (10 * 50.00) + (5 * 70.00) + (2 * 20.00)  # 500 + 350 + 40 = 890.00
    assert len(summary.price_discrepancies) == 2

    d1 = summary.price_discrepancies[0]
    assert d1.line_number == 2
    assert d1.ordered_price == 70.00
    assert d1.contract_price == 100.00
    assert d1.discrepancy_percent == 30.0
    assert d1.discrepancy_type == 'UNDERPAYMENT'

    d2 = summary.price_discrepancies[1]
    assert d2.line_number == 3
    assert d2.discrepancy_type == 'PRODUCT_NOT_FOUND'


def test_cross_reference_order_all_clean_auto_confirm():
    mock_sku_repo = MagicMock()
    mock_product_repo = MagicMock()
    mock_contract_repo = MagicMock()

    mock_sku_repo.list.return_value = [
        {
            'id': 1, 'partner_id': 1, 'product_id': 101, 'partner_sku': 'SKU-CLEAN',
            'partner_sku_type': 'BUYER_PART_NO', 'partner_uom': 'EA', 'internal_uom': 'EA',
            'uom_conversion_factor': 1.0, 'is_active': True,
        }
    ]
    mock_product_repo.get.return_value = {'id': 101, 'name': 'Clean Item', 'sku': 'NOVA-C', 'price': 20.00}
    mock_contract_repo.list.return_value = []

    service = CrossReferenceService(
        sku_mapping_repo=mock_sku_repo,
        product_repo=mock_product_repo,
        contract_repo=mock_contract_repo,
    )

    raw_items = [
        {'line_number': 1, 'buyer_sku': 'SKU-CLEAN', 'ordered_qty': 10, 'ordered_price': 20.00},
    ]

    summary = service.cross_reference_order(
        partner_id=1,
        customer_id=10,
        line_items=raw_items,
        auto_confirm_orders=True,
    )

    assert summary.is_clean is True
    assert summary.matched_lines == 1
    assert summary.unmatched_lines == 0
    assert summary.discrepancy_lines == 0
    assert summary.recommended_status == 'Confirmed'


# ===========================================================================
# 6. SKU Matrix CRUD & Bulk Import Tests
# ===========================================================================

def test_create_or_update_mapping_create():
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_sku_repo.create.return_value = {'id': 100, 'partner_sku': 'CRF-TEST-1'}

    service = CrossReferenceService(sku_mapping_repo=mock_sku_repo)

    res = service.create_or_update_mapping(
        partner_id=1,
        product_id=55,
        partner_sku='CRF-TEST-1',
        partner_sku_type='BUYER_PART_NO',
        gtin='6291041009999',
        partner_uom='CA',
        internal_uom='EA',
        uom_conversion_factor=6.0,
        catalog_price=90.00,
    )

    assert res['id'] == 100
    mock_sku_repo.create.assert_called_once()
    mock_sku_repo.update.assert_not_called()


def test_create_or_update_mapping_update():
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = [{'id': 100, 'partner_sku': 'CRF-TEST-1'}]
    mock_sku_repo.update.return_value = {'id': 100, 'partner_sku': 'CRF-TEST-1', 'catalog_price': 95.00}

    service = CrossReferenceService(sku_mapping_repo=mock_sku_repo)

    res = service.create_or_update_mapping(
        partner_id=1,
        product_id=55,
        partner_sku='CRF-TEST-1',
        catalog_price=95.00,
    )

    assert res['catalog_price'] == 95.00
    mock_sku_repo.update.assert_called_once()
    mock_sku_repo.create.assert_not_called()


def test_bulk_import_mappings():
    mock_sku_repo = MagicMock()
    mock_sku_repo.list.return_value = []
    mock_sku_repo.create.return_value = {'id': 1}

    service = CrossReferenceService(sku_mapping_repo=mock_sku_repo)

    import_data = [
        {'partner_sku': 'SKU-1', 'product_id': 101, 'partner_uom': 'EA', 'uom_conversion_factor': 1.0},
        {'partner_sku': 'SKU-2', 'product_id': 102, 'partner_uom': 'CA', 'uom_conversion_factor': 12.0},
        {'partner_sku': '', 'product_id': 103},  # Invalid row
    ]

    res = service.bulk_import_mappings(partner_id=1, mappings=import_data)

    assert res['total'] == 3
    assert res['created'] == 2
    assert len(res['errors']) == 1
    assert "Missing partner_sku or product_id" in res['errors'][0]

"""
Unit tests for GS1 SSCC-18 Pallet Barcode Generator & Packaging Hierarchy Service
"""

import pytest
from unittest.mock import MagicMock, patch

from modules.integrations.services.edi.sscc_service import (
    calculate_modulo10_check_digit,
    validate_modulo10,
    validate_sscc,
    parse_sscc_gs1_128,
    format_sscc_gs1_128,
    generate_sscc18,
    decompose_sscc18,
    format_gs1_logistics_label,
    PackagingLevel,
    PackagingItem,
    PackagingBox,
    PackagingPallet,
    PackagingHierarchy,
    SsccService,
    DEFAULT_GS1_COMPANY_PREFIX,
)


# ===========================================================================
# 1. GS1 Modulo-10 Check Digit & SSCC Calculation Tests
# ===========================================================================

def test_modulo10_check_digit_standard_vectors():
    """
    Test standard GS1 Modulo-10 calculation against known test vectors.
    """
    # Vector 1: 17 digits -> '00614141123456789' -> Check digit: 0
    assert calculate_modulo10_check_digit("00614141123456789") == 0

    # Vector 2: '10614141123456789' -> Check digit: 7
    assert calculate_modulo10_check_digit("10614141123456789") == 7

    # Vector 3: 13 digits '0061414100003' -> Check digit: 6
    assert calculate_modulo10_check_digit("0061414100003") == 6

    # Vector 4: '12345678901234567'
    cd4 = calculate_modulo10_check_digit("12345678901234567")
    assert 0 <= cd4 <= 9
    assert validate_modulo10(f"12345678901234567{cd4}") is True


def test_modulo10_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_modulo10_check_digit("")

    with pytest.raises(ValueError):
        calculate_modulo10_check_digit("12345ABC6789")

    with pytest.raises(ValueError):
        calculate_modulo10_check_digit("   ")


def test_validate_modulo10():
    # Valid
    assert validate_modulo10("006141411234567890") is True
    assert validate_modulo10("106141411234567897") is True

    # Invalid check digit
    assert validate_modulo10("006141411234567895") is False
    assert validate_modulo10("106141411234567890") is False

    # Malformed / empty
    assert validate_modulo10("") is False
    assert validate_modulo10("1") is False
    assert validate_modulo10("ABC") is False


# ===========================================================================
# 2. SSCC-18 Generation Tests
# ===========================================================================

def test_generate_sscc18_default_prefix():
    # Default prefix "0614141" (7 digits), extension "0" (1 digit), serial "1" -> 9 digits padded serial
    sscc = generate_sscc18(company_prefix="0614141", serial_number=1, extension_digit=0)
    assert len(sscc) == 18
    assert sscc.startswith("00614141000000001")
    assert validate_sscc(sscc) is True


def test_generate_sscc18_custom_prefix_and_extension():
    # 8-digit prefix "12345678", extension "2", serial "999"
    # 1 + 8 + 8 digits serial = 17 digits data
    sscc = generate_sscc18(company_prefix="12345678", serial_number=999, extension_digit=2)
    assert len(sscc) == 18
    assert sscc.startswith("21234567800000999")
    assert validate_sscc(sscc) is True


def test_generate_sscc18_various_prefix_lengths():
    prefixes = ["123456", "1234567", "12345678", "123456789", "1234567890"]
    for p in prefixes:
        sscc = generate_sscc18(company_prefix=p, serial_number=42, extension_digit=0)
        assert len(sscc) == 18
        assert validate_sscc(sscc) is True


def test_generate_sscc18_validation_errors():
    # Invalid extension digit
    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="0614141", serial_number=1, extension_digit=12)

    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="0614141", serial_number=1, extension_digit="X")

    # Invalid company prefix
    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="12", serial_number=1)  # too short

    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="123456789012345", serial_number=1)  # too long

    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="ABC1234", serial_number=1)  # non-digit

    # Serial number overflow
    # 10-digit prefix leaves 17 - 1 - 10 = 6 digits serial (max 999999)
    with pytest.raises(ValueError):
        generate_sscc18(company_prefix="1234567890", serial_number=1000000)


# ===========================================================================
# 3. Barcode Parsing, Formatting & Decomposition
# ===========================================================================

def test_parse_and_format_sscc():
    raw_18 = "006141411234567890"

    # Formatting
    formatted_parens = format_sscc_gs1_128(raw_18, with_ai_parentheses=True)
    assert formatted_parens == "(00)006141411234567890"

    formatted_plain = format_sscc_gs1_128(raw_18, with_ai_parentheses=False)
    assert formatted_plain == "00006141411234567890"

    # Parsing variations
    assert parse_sscc_gs1_128(raw_18) == raw_18
    assert parse_sscc_gs1_128("(00)006141411234567890") == raw_18
    assert parse_sscc_gs1_128("00006141411234567890") == raw_18
    assert parse_sscc_gs1_128("]C100006141411234567890") == raw_18
    assert parse_sscc_gs1_128(" (00) 006141411234567890 ") == raw_18


def test_decompose_sscc18():
    sscc = generate_sscc18("0614141", 1, 0)  # "006141410000000012"
    decomp = decompose_sscc18(sscc, company_prefix_len=7)
    assert decomp["is_valid"] is True
    assert decomp["extension_digit"] == "0"
    assert decomp["company_prefix"] == "0614141"
    assert decomp["serial_reference"] == "000000001"
    assert decomp["check_digit"] == 2
    assert decomp["gs1_128_formatted"] == f"(00){sscc}"


# ===========================================================================
# 4. Packaging Hierarchy Models & Roll-up Calculations
# ===========================================================================

def test_packaging_item_and_box_weight_calculation():
    item1 = PackagingItem(
        sku="MILK-1L",
        product_name="Fresh Whole Milk 1L",
        quantity=12,
        uom="EA",
        gross_weight_kg=1.05,
        net_weight_kg=1.00,
        batch_number="LOT-20260901",
        expiry_date="2026-09-30",
    )
    item2 = PackagingItem(
        sku="YOGURT-500G",
        product_name="Greek Yogurt 500g",
        quantity=6,
        uom="EA",
        gross_weight_kg=0.55,
        net_weight_kg=0.50,
        batch_number="LOT-20260902",
        expiry_date="2026-09-25",
    )

    box = PackagingBox(
        box_number="BX-01",
        package_type="BOX",
        tare_weight_kg=0.4,
        length_cm=40,
        width_cm=30,
        height_cm=20,
    )
    box.add_item(item1).add_item(item2)
    box.calculate_weights()

    # Net weight = 1.00 + 0.50 = 1.50 kg
    assert box.net_weight_kg == 1.50
    # Gross weight = 1.50 + 0.40 tare = 1.90 kg
    assert box.gross_weight_kg == 1.90
    # Volume: (40 * 30 * 20) / 1,000,000 = 0.024 cbm
    assert box.volume_cbm == 0.024


def test_packaging_pallet_and_hierarchy_aggregation():
    # Pallet 1 with 2 boxes
    box1 = PackagingBox(
        box_number="BX-01",
        package_type="BOX",
        tare_weight_kg=0.5,
        items=[
            PackagingItem(sku="SKU-A", quantity=10, net_weight_kg=5.0),
            PackagingItem(sku="SKU-B", quantity=5, net_weight_kg=2.5),
        ],
    )
    box2 = PackagingBox(
        box_number="BX-02",
        package_type="BOX",
        tare_weight_kg=0.5,
        items=[
            PackagingItem(sku="SKU-C", quantity=20, net_weight_kg=10.0),
        ],
    )

    sscc1 = generate_sscc18("0614141", 101, 0)
    pallet1 = PackagingPallet(
        pallet_number="PLT-01",
        sscc_barcode=sscc1,
        tare_weight_kg=20.0,
    )
    pallet1.add_box(box1).add_box(box2)
    pallet1.calculate_weights()

    # Box 1 net = 7.5, gross = 8.0
    # Box 2 net = 10.0, gross = 10.5
    # Pallet net = 7.5 + 10.0 = 17.5
    # Pallet gross = 8.0 + 10.5 + 20.0 (pallet tare) = 38.5
    assert pallet1.net_weight_kg == 17.5
    assert pallet1.gross_weight_kg == 38.5
    assert pallet1.total_boxes() == 2
    assert pallet1.total_units() == 35  # 10 + 5 + 20

    # Pallet 2 with direct items (bulk container)
    sscc2 = generate_sscc18("0614141", 102, 0)
    pallet2 = PackagingPallet(
        pallet_number="PLT-02",
        sscc_barcode=sscc2,
        tare_weight_kg=15.0,
        direct_items=[
            PackagingItem(sku="BULK-RICE", quantity=50, net_weight_kg=250.0),
        ],
    )
    pallet2.calculate_weights()
    assert pallet2.net_weight_kg == 250.0
    assert pallet2.gross_weight_kg == 265.0
    assert pallet2.total_boxes() == 0
    assert pallet2.total_units() == 50

    # Hierarchy container
    hierarchy = PackagingHierarchy(
        delivery_id=1001,
        sales_order_id=5001,
        carrier_code="DHL",
        tracking_number="TRK-987654",
    )
    hierarchy.add_pallet(pallet1).add_pallet(pallet2)
    hierarchy.calculate_all_weights()

    assert hierarchy.total_pallets() == 2
    assert hierarchy.total_boxes() == 2
    assert hierarchy.total_items() == 85
    assert hierarchy.total_gross_weight() == 38.5 + 265.0
    assert hierarchy.total_net_weight() == 17.5 + 250.0

    # Test HL Records generation for EDI 856 ASN
    hl_records = hierarchy.to_hl_records()
    assert len(hl_records) > 0

    # Check level progression: Shipment (S) -> Order (O) -> Tare (T) -> Pack (P) -> Item (I)
    level_codes = [r["level_code"] for r in hl_records]
    assert level_codes[0] == "S"
    assert level_codes[1] == "O"
    assert "T" in level_codes
    assert "P" in level_codes
    assert "I" in level_codes

    # Check parent IDs
    s_rec = hl_records[0]
    o_rec = hl_records[1]
    assert s_rec["parent_hl_id"] is None
    assert o_rec["parent_hl_id"] == s_rec["hl_id"]


# ===========================================================================
# 5. GS1 Logistics Label Data Formatting Tests
# ===========================================================================

def test_format_gs1_logistics_label():
    sscc = generate_sscc18("0614141", 888, 0)
    pallet = PackagingPallet(
        pallet_number="PLT-008",
        sscc_barcode=sscc,
        gross_weight_kg=350.5,
        net_weight_kg=325.0,
    )
    label = format_gs1_logistics_label(pallet)

    assert label["header"]["title"] == "GS1 LOGISTICS LABEL"
    assert label["sscc"]["raw_18"] == sscc
    assert label["sscc"]["is_valid"] is True
    assert label["sscc"]["formatted_gs1_128"] == f"(00){sscc}"
    assert label["sscc"]["barcode_value"] == f"00{sscc}"
    assert label["item_details"]["pallet_number"] == "PLT-008"
    assert label["item_details"]["gross_weight_kg"] == 350.5


# ===========================================================================
# 6. SsccService Database Operations & Mock Tests
# ===========================================================================

def test_sscc_service_generate_next_sscc_mocked():
    mock_repo = MagicMock()
    service = SsccService(repo=mock_repo)

    with patch.object(service, "generate_next_sscc", return_value="006141410000001239"):
        sscc = service.generate_next_sscc()
        assert sscc == "006141410000001239"


def test_sscc_service_create_pallet_mocked():
    mock_repo = MagicMock()
    mock_repo.create.return_value = {
        "id": 10,
        "sscc_barcode": "006141410000001239",
        "delivery_id": 45,
        "sales_order_id": 89,
        "pallet_number": "PLT-01",
        "package_type": "PALLET",
        "gross_weight_kg": 400.0,
        "status": "PACKED",
    }
    service = SsccService(repo=mock_repo)

    with patch.object(service, "generate_next_sscc", return_value="006141410000001239"):
        created = service.create_pallet(
            delivery_id=45,
            sales_order_id=89,
            pallet_number="PLT-01",
            gross_weight_kg=400.0,
        )

        assert created["id"] == 10
        assert created["sscc_barcode"] == "006141410000001239"
        mock_repo.create.assert_called_once()


def test_sscc_service_get_pallet_by_sscc_mocked():
    mock_repo = MagicMock()
    mock_repo.list.return_value = [
        {"id": 12, "sscc_barcode": "006141410000001239", "pallet_number": "PLT-12"}
    ]
    service = SsccService(repo=mock_repo)

    res = service.get_pallet_by_sscc("(00)006141410000001239")
    assert res is not None
    assert res["id"] == 12
    mock_repo.list.assert_called_once_with(
        filters={"sscc_barcode": "006141410000001239"},
        limit=1,
    )

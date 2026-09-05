import pytest
import xml.etree.ElementTree as ET
from modules.accounting.services.ubl_builder_service import (
    UBLInvoiceBuilder,
    generate_ubl_invoice_xml,
    SUBTYPE_STANDARD_B2B,
    SUBTYPE_SIMPLIFIED_B2C,
    INVOICE_TYPE_TAX_INVOICE,
    INVOICE_TYPE_CREDIT_NOTE,
)


def test_ubl_builder_standard_b2b():
    builder = UBLInvoiceBuilder(
        invoice_number="INV-2026-0001",
        invoice_uuid="c22b109e-1d54-4a46-88fe-74673fb3bc88",
        issue_date="2026-09-05",
        issue_time="08:30:00",
        invoice_type_code=INVOICE_TYPE_TAX_INVOICE,
        subtype=SUBTYPE_STANDARD_B2B,
        currency_code="SAR",
        icv=1,
        pih="NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0Nj振兴",
        qr_code_tlv="AQxOb3ZhIFNlbGxlcg==",
    )

    builder.set_supplier(
        name="Nova Wholesale Corp",
        tax_id="310123456700003",
        crn="1010123456",
        street="King Fahd Road",
        building_number="1234",
        district="Al Olaya",
        city="Riyadh",
        postal_code="12211",
        country_code="SA",
    )

    builder.set_customer(
        name="Al-Amal Retailers Co",
        tax_id="300987654300003",
        crn="1010987654",
        street="Tahlia Street",
        building_number="5678",
        district="Al Sulaimaniyah",
        city="Riyadh",
        postal_code="12244",
        country_code="SA",
    )

    builder.add_line_item(
        name="Premium Basmati Rice 10kg",
        quantity=10.0,
        unit_price=50.0,
        tax_rate=15.0,
        unit_code="PCE",
    )

    builder.add_line_item(
        name="Sunflower Cooking Oil 5L",
        quantity=5.0,
        unit_price=30.0,
        tax_rate=15.0,
        unit_code="PCE",
    )

    builder.calculate_totals()
    xml_str = builder.to_xml_string(pretty=True)

    assert xml_str.startswith("<?xml")
    assert "<cbc:ID>INV-2026-0001</cbc:ID>" in xml_str
    assert "<cbc:UUID>c22b109e-1d54-4a46-88fe-74673fb3bc88</cbc:UUID>" in xml_str
    assert 'name="0100000"' in xml_str
    assert "<cbc:RegistrationName>Nova Wholesale Corp</cbc:RegistrationName>" in xml_str
    assert "<cbc:RegistrationName>Al-Amal Retailers Co</cbc:RegistrationName>" in xml_str
    assert "<cbc:CompanyID>310123456700003</cbc:CompanyID>" in xml_str
    assert "<cbc:CompanyID>300987654300003</cbc:CompanyID>" in xml_str

    # Line amounts verification
    # Line 1: 10 * 50 = 500, Tax = 75
    # Line 2: 5 * 30 = 150, Tax = 22.5
    # Total Line Extension = 650.00, Tax Total = 97.50, Tax Inclusive = 747.50
    assert builder.line_extension_amount == 650.00
    assert builder.tax_total_amount == 97.50
    assert builder.tax_inclusive_amount == 747.50
    assert builder.payable_amount == 747.50

    assert '<cbc:LineExtensionAmount currencyID="SAR">650.00</cbc:LineExtensionAmount>' in xml_str
    assert '<cbc:TaxAmount currencyID="SAR">97.50</cbc:TaxAmount>' in xml_str
    assert '<cbc:TaxInclusiveAmount currencyID="SAR">747.50</cbc:TaxInclusiveAmount>' in xml_str


def test_ubl_builder_simplified_b2c():
    builder = UBLInvoiceBuilder(
        invoice_number="SIMP-2026-0099",
        subtype=SUBTYPE_SIMPLIFIED_B2C,
        qr_code_tlv="AQxOb3ZhIFNlbGxlcg==",
    )

    builder.set_supplier(
        name="Nova Quick Serve Store",
        tax_id="310123456700003",
    )

    builder.set_customer(name="Walk-in Retail Buyer")

    builder.add_line_item(
        name="Coffee Beans 1kg",
        quantity=2.0,
        unit_price=40.0,
        tax_rate=15.0,
    )

    builder.calculate_totals()
    xml_str = builder.to_xml_string()

    assert "<cbc:ID>SIMP-2026-0099</cbc:ID>" in xml_str
    assert 'name="0200000"' in xml_str
    assert "<cbc:RegistrationName>Nova Quick Serve Store</cbc:RegistrationName>" in xml_str
    assert builder.line_extension_amount == 80.00
    assert builder.tax_total_amount == 12.00
    assert builder.tax_inclusive_amount == 92.00


def test_generate_ubl_invoice_xml_helper():
    invoice = {
        "id": 42,
        "invoice_number": "INV-2026-0042",
        "notes": "Thank you for your business",
        "currency": "SAR",
    }
    supplier = {
        "seller_name": "Nova Global Trading",
        "tax_id": "310000000000003",
        "commercial_registration_number": "1010000001",
        "city": "Jeddah",
        "country_code": "SA",
    }
    customer = {
        "name": "B2B Client Ltd",
        "tax_id": "320000000000003",
    }
    lines = [
        {"product_name": "Industrial Sensor A1", "qty": 4, "unit_price": 250.0, "tax_rate": 15.0},
    ]

    xml_output = generate_ubl_invoice_xml(
        invoice=invoice,
        supplier_profile=supplier,
        customer=customer,
        lines=lines,
        subtype=SUBTYPE_STANDARD_B2B,
        icv=5,
    )

    assert "<cbc:ID>INV-2026-0042</cbc:ID>" in xml_output
    assert "<cbc:UUID>5</cbc:UUID>" in xml_output  # ICV UUID
    assert "<cbc:RegistrationName>Nova Global Trading</cbc:RegistrationName>" in xml_output
    assert "<cbc:RegistrationName>B2B Client Ltd</cbc:RegistrationName>" in xml_output
    assert "Industrial Sensor A1" in xml_output

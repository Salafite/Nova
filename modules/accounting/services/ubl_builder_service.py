"""UBL 2.1 XML Document Generator for e-Invoicing & Fiscal Compliance.

Compliant with UN/CEFACT, OASIS UBL 2.1, and regional tax authority mandates (ZATCA / EN16931).
Supports Standard B2B (0100000) and Simplified B2C (0200000) Tax Invoices, Credit Notes, and Debit Notes.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union
import uuid

# Namespaces
NAMESPACES = {
    "xmlns": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}

# Subtypes
SUBTYPE_STANDARD_B2B = "0100000"
SUBTYPE_SIMPLIFIED_B2C = "0200000"

# Invoice Type Codes (UN/ECE 1001)
INVOICE_TYPE_TAX_INVOICE = "388"
INVOICE_TYPE_CREDIT_NOTE = "381"
INVOICE_TYPE_DEBIT_NOTE = "383"
INVOICE_TYPE_PREPAYMENT = "386"


def _format_decimal(val: Union[float, int, str, None], decimals: int = 2) -> str:
    if val is None:
        return f"{0.0:.{decimals}f}"
    try:
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return f"{0.0:.{decimals}f}"


class UBLInvoiceBuilder:
    """Builder for generating OASIS UBL 2.1 XML invoices."""

    def __init__(
        self,
        invoice_number: str,
        invoice_uuid: Optional[str] = None,
        issue_date: Optional[Union[date, datetime, str]] = None,
        issue_time: Optional[Union[datetime, str]] = None,
        invoice_type_code: str = INVOICE_TYPE_TAX_INVOICE,
        subtype: str = SUBTYPE_STANDARD_B2B,
        currency_code: str = "SAR",
        tax_currency_code: str = "SAR",
        note: Optional[str] = None,
        icv: int = 1,
        pih: Optional[str] = None,
        qr_code_tlv: Optional[str] = None,
    ):
        self.invoice_number = invoice_number
        self.invoice_uuid = invoice_uuid or str(uuid.uuid4())
        
        # Handle issue_date and issue_time
        if isinstance(issue_date, (datetime, date)):
            self.issue_date = issue_date.strftime("%Y-%m-%d")
        elif issue_date:
            self.issue_date = str(issue_date)
        else:
            self.issue_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if isinstance(issue_time, datetime):
            self.issue_time = issue_time.strftime("%H:%M:%S")
        elif issue_time:
            self.issue_time = str(issue_time)
        else:
            self.issue_time = datetime.now(timezone.utc).strftime("%H:%M:%S")

        self.invoice_type_code = invoice_type_code
        self.subtype = subtype
        self.currency_code = currency_code
        self.tax_currency_code = tax_currency_code
        self.note = note
        self.icv = icv
        self.pih = pih or "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjAzZTQ4MmUwNzMzYTJhNw=="
        self.qr_code_tlv = qr_code_tlv

        # Supplier data
        self.supplier: Dict[str, Any] = {}
        # Customer data
        self.customer: Dict[str, Any] = {}
        # Line items
        self.lines: List[Dict[str, Any]] = []
        # Payment details
        self.payment_means_code: str = "10"
        self.payment_terms_note: Optional[str] = None
        # Allowances / Charges (Discounts)
        self.allowances: List[Dict[str, Any]] = []
        # Tax categories / totals breakdown
        self.tax_subtotals: List[Dict[str, Any]] = []
        # Overall totals
        self.line_extension_amount: float = 0.0
        self.tax_exclusive_amount: float = 0.0
        self.tax_inclusive_amount: float = 0.0
        self.allowance_total_amount: float = 0.0
        self.charge_total_amount: float = 0.0
        self.prepaid_amount: float = 0.0
        self.payable_amount: float = 0.0
        self.tax_total_amount: float = 0.0

    def set_supplier(
        self,
        name: str,
        tax_id: str,
        crn: Optional[str] = None,
        street: Optional[str] = None,
        building_number: Optional[str] = None,
        district: Optional[str] = None,
        city: Optional[str] = None,
        postal_code: Optional[str] = None,
        country_code: str = "SA",
    ) -> "UBLInvoiceBuilder":
        self.supplier = {
            "name": name,
            "tax_id": tax_id,
            "crn": crn,
            "street": street or "",
            "building_number": building_number or "",
            "district": district or "",
            "city": city or "",
            "postal_code": postal_code or "",
            "country_code": country_code,
        }
        return self

    def set_customer(
        self,
        name: str,
        tax_id: Optional[str] = None,
        crn: Optional[str] = None,
        street: Optional[str] = None,
        building_number: Optional[str] = None,
        district: Optional[str] = None,
        city: Optional[str] = None,
        postal_code: Optional[str] = None,
        country_code: str = "SA",
    ) -> "UBLInvoiceBuilder":
        self.customer = {
            "name": name,
            "tax_id": tax_id,
            "crn": crn,
            "street": street or "",
            "building_number": building_number or "",
            "district": district or "",
            "city": city or "",
            "postal_code": postal_code or "",
            "country_code": country_code,
        }
        return self

    def set_payment(self, means_code: str = "10", terms_note: Optional[str] = None) -> "UBLInvoiceBuilder":
        self.payment_means_code = means_code
        self.payment_terms_note = terms_note
        return self

    def add_line_item(
        self,
        name: str,
        quantity: float,
        unit_price: float,
        unit_code: str = "PCE",
        tax_rate: float = 15.0,
        tax_category_code: str = "S",
        tax_scheme: str = "VAT",
        discount: float = 0.0,
        line_id: Optional[int] = None,
    ) -> "UBLInvoiceBuilder":
        idx = line_id or (len(self.lines) + 1)
        gross_amount = quantity * unit_price
        line_net = gross_amount - discount
        line_tax = line_net * (tax_rate / 100.0)
        line_total_with_tax = line_net + line_tax

        self.lines.append({
            "line_id": str(idx),
            "name": name,
            "quantity": quantity,
            "unit_price": unit_price,
            "unit_code": unit_code,
            "discount": discount,
            "line_net": line_net,
            "tax_rate": tax_rate,
            "tax_category_code": tax_category_code,
            "tax_scheme": tax_scheme,
            "line_tax": line_tax,
            "line_total_with_tax": line_total_with_tax,
        })
        return self

    def calculate_totals(self) -> "UBLInvoiceBuilder":
        """Calculates tax subtotals, line extension, and legal monetary amounts."""
        line_extension = 0.0
        tax_groups: Dict[str, Dict[str, float]] = {}

        for line in self.lines:
            line_extension += line["line_net"]
            key = f"{line['tax_category_code']}_{line['tax_rate']}"
            if key not in tax_groups:
                tax_groups[key] = {
                    "taxable_amount": 0.0,
                    "tax_amount": 0.0,
                    "rate": line["tax_rate"],
                    "category": line["tax_category_code"],
                    "scheme": line["tax_scheme"],
                }
            tax_groups[key]["taxable_amount"] += line["line_net"]
            tax_groups[key]["tax_amount"] += line["line_tax"]

        self.line_extension_amount = round(line_extension, 2)
        total_tax = round(sum(g["tax_amount"] for g in tax_groups.values()), 2)
        self.tax_total_amount = total_tax
        self.tax_exclusive_amount = round(self.line_extension_amount - self.allowance_total_amount, 2)
        self.tax_inclusive_amount = round(self.tax_exclusive_amount + self.tax_total_amount, 2)
        self.payable_amount = round(self.tax_inclusive_amount - self.prepaid_amount, 2)

        self.tax_subtotals = [
            {
                "taxable_amount": round(g["taxable_amount"], 2),
                "tax_amount": round(g["tax_amount"], 2),
                "percent": g["rate"],
                "category_id": g["category"],
                "scheme_id": g["scheme"],
            }
            for g in tax_groups.values()
        ]
        return self

    def build_xml_tree(self) -> ET.Element:
        """Builds and returns the ElementTree root Element."""
        if not self.tax_subtotals and self.lines:
            self.calculate_totals()

        # Root element
        root = ET.Element("Invoice", {
            "xmlns": NAMESPACES["xmlns"],
            "xmlns:cac": NAMESPACES["cac"],
            "xmlns:cbc": NAMESPACES["cbc"],
            "xmlns:ext": NAMESPACES["ext"],
        })

        # UBLExtensions container
        ubl_extensions = ET.SubElement(root, "ext:UBLExtensions")
        ubl_ext = ET.SubElement(ubl_extensions, "ext:UBLExtension")
        ET.SubElement(ubl_ext, "ext:ExtensionURI").text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
        ext_content = ET.SubElement(ubl_ext, "ext:ExtensionContent")
        ET.SubElement(ext_content, "sig:UBLDocumentSignatures", {
            "xmlns:sig": "urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2",
            "xmlns:sac": "urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2",
            "xmlns:sbc": "urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2"
        })

        # Basic Header Elements
        ET.SubElement(root, "cbc:ProfileID").text = "reporting:1.0"
        ET.SubElement(root, "cbc:ID").text = self.invoice_number
        ET.SubElement(root, "cbc:UUID").text = self.invoice_uuid
        ET.SubElement(root, "cbc:IssueDate").text = self.issue_date
        ET.SubElement(root, "cbc:IssueTime").text = self.issue_time

        # InvoiceTypeCode with subtype
        inv_type_elem = ET.SubElement(root, "cbc:InvoiceTypeCode", {"name": self.subtype})
        inv_type_elem.text = self.invoice_type_code

        if self.note:
            ET.SubElement(root, "cbc:Note").text = self.note

        ET.SubElement(root, "cbc:DocumentCurrencyCode").text = self.currency_code
        ET.SubElement(root, "cbc:TaxCurrencyCode").text = self.tax_currency_code

        # Additional Document References (ICV, PIH, QR)
        # 1. ICV
        icv_ref = ET.SubElement(root, "cac:AdditionalDocumentReference")
        ET.SubElement(icv_ref, "cbc:ID").text = "ICV"
        ET.SubElement(icv_ref, "cbc:UUID").text = str(self.icv)

        # 2. PIH
        pih_ref = ET.SubElement(root, "cac:AdditionalDocumentReference")
        ET.SubElement(pih_ref, "cbc:ID").text = "PIH"
        pih_att = ET.SubElement(pih_ref, "cac:Attachment")
        pih_bin = ET.SubElement(pih_att, "cbc:EmbeddedDocumentBinaryObject", {"mimeCode": "text/plain"})
        pih_bin.text = self.pih

        # 3. QR Code (if provided)
        if self.qr_code_tlv:
            qr_ref = ET.SubElement(root, "cac:AdditionalDocumentReference")
            qr_ref_id = ET.SubElement(qr_ref, "cbc:ID")
            qr_ref_id.text = "QR"
            qr_att = ET.SubElement(qr_ref, "cac:Attachment")
            qr_bin = ET.SubElement(qr_att, "cbc:EmbeddedDocumentBinaryObject", {"mimeCode": "text/plain"})
            qr_bin.text = self.qr_code_tlv

        # Supplier Party
        supp_party = ET.SubElement(root, "cac:AccountingSupplierParty")
        party = ET.SubElement(supp_party, "cac:Party")
        
        if self.supplier.get("crn"):
            part_id = ET.SubElement(party, "cac:PartyIdentification")
            crn_elem = ET.SubElement(part_id, "cbc:ID", {"schemeID": "CRN"})
            crn_elem.text = self.supplier["crn"]

        supp_addr = ET.SubElement(party, "cac:PostalAddress")
        ET.SubElement(supp_addr, "cbc:StreetName").text = self.supplier.get("street", "")
        ET.SubElement(supp_addr, "cbc:BuildingNumber").text = self.supplier.get("building_number", "")
        ET.SubElement(supp_addr, "cbc:CitySubdivisionName").text = self.supplier.get("district", "")
        ET.SubElement(supp_addr, "cbc:CityName").text = self.supplier.get("city", "")
        ET.SubElement(supp_addr, "cbc:PostalZone").text = self.supplier.get("postal_code", "")
        country = ET.SubElement(supp_addr, "cac:Country")
        ET.SubElement(country, "cbc:IdentificationCode").text = self.supplier.get("country_code", "SA")

        supp_tax = ET.SubElement(party, "cac:PartyTaxScheme")
        ET.SubElement(supp_tax, "cbc:CompanyID").text = self.supplier.get("tax_id", "")
        tax_scheme = ET.SubElement(supp_tax, "cac:TaxScheme")
        ET.SubElement(tax_scheme, "cbc:ID").text = "VAT"

        supp_legal = ET.SubElement(party, "cac:PartyLegalEntity")
        ET.SubElement(supp_legal, "cbc:RegistrationName").text = self.supplier.get("name", "")

        # Customer Party
        cust_party = ET.SubElement(root, "cac:AccountingCustomerParty")
        c_party = ET.SubElement(cust_party, "cac:Party")

        if self.customer.get("crn"):
            c_part_id = ET.SubElement(c_party, "cac:PartyIdentification")
            c_crn = ET.SubElement(c_part_id, "cbc:ID", {"schemeID": "CRN"})
            c_crn.text = self.customer["crn"]

        c_addr = ET.SubElement(c_party, "cac:PostalAddress")
        ET.SubElement(c_addr, "cbc:StreetName").text = self.customer.get("street", "")
        ET.SubElement(c_addr, "cbc:BuildingNumber").text = self.customer.get("building_number", "")
        ET.SubElement(c_addr, "cbc:CitySubdivisionName").text = self.customer.get("district", "")
        ET.SubElement(c_addr, "cbc:CityName").text = self.customer.get("city", "")
        ET.SubElement(c_addr, "cbc:PostalZone").text = self.customer.get("postal_code", "")
        c_country = ET.SubElement(c_addr, "cac:Country")
        ET.SubElement(c_country, "cbc:IdentificationCode").text = self.customer.get("country_code", "SA")

        if self.customer.get("tax_id"):
            c_tax = ET.SubElement(c_party, "cac:PartyTaxScheme")
            ET.SubElement(c_tax, "cbc:CompanyID").text = self.customer["tax_id"]
            c_tax_scheme = ET.SubElement(c_tax, "cac:TaxScheme")
            ET.SubElement(c_tax_scheme, "cbc:ID").text = "VAT"

        c_legal = ET.SubElement(c_party, "cac:PartyLegalEntity")
        ET.SubElement(c_legal, "cbc:RegistrationName").text = self.customer.get("name", "Walk-in Customer")

        # Delivery Information
        delivery = ET.SubElement(root, "cac:Delivery")
        ET.SubElement(delivery, "cbc:ActualDeliveryDate").text = self.issue_date

        # Payment Means
        pay_means = ET.SubElement(root, "cac:PaymentMeans")
        ET.SubElement(pay_means, "cbc:PaymentMeansCode").text = self.payment_means_code
        if self.payment_terms_note:
            pay_terms = ET.SubElement(root, "cac:PaymentTerms")
            ET.SubElement(pay_terms, "cbc:Note").text = self.payment_terms_note

        # Tax Totals
        tax_total = ET.SubElement(root, "cac:TaxTotal")
        ET.SubElement(tax_total, "cbc:TaxAmount", {"currencyID": self.tax_currency_code}).text = _format_decimal(self.tax_total_amount)

        for sub in self.tax_subtotals:
            sub_elem = ET.SubElement(tax_total, "cac:TaxSubtotal")
            ET.SubElement(sub_elem, "cbc:TaxableAmount", {"currencyID": self.currency_code}).text = _format_decimal(sub["taxable_amount"])
            ET.SubElement(sub_elem, "cbc:TaxAmount", {"currencyID": self.tax_currency_code}).text = _format_decimal(sub["tax_amount"])
            
            cat_elem = ET.SubElement(sub_elem, "cac:TaxCategory")
            ET.SubElement(cat_elem, "cbc:ID").text = sub["category_id"]
            ET.SubElement(cat_elem, "cbc:Percent").text = _format_decimal(sub["percent"])
            t_sch = ET.SubElement(cat_elem, "cac:TaxScheme")
            ET.SubElement(t_sch, "cbc:ID").text = sub["scheme_id"]

        # Legal Monetary Total
        legal_total = ET.SubElement(root, "cac:LegalMonetaryTotal")
        ET.SubElement(legal_total, "cbc:LineExtensionAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.line_extension_amount)
        ET.SubElement(legal_total, "cbc:TaxExclusiveAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.tax_exclusive_amount)
        ET.SubElement(legal_total, "cbc:TaxInclusiveAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.tax_inclusive_amount)
        ET.SubElement(legal_total, "cbc:AllowanceTotalAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.allowance_total_amount)
        ET.SubElement(legal_total, "cbc:PrepaidAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.prepaid_amount)
        ET.SubElement(legal_total, "cbc:PayableAmount", {"currencyID": self.currency_code}).text = _format_decimal(self.payable_amount)

        # Invoice Lines
        for item in self.lines:
            line_elem = ET.SubElement(root, "cac:InvoiceLine")
            ET.SubElement(line_elem, "cbc:ID").text = str(item["line_id"])
            ET.SubElement(line_elem, "cbc:InvoicedQuantity", {"unitCode": item["unit_code"]}).text = _format_decimal(item["quantity"], 4)
            ET.SubElement(line_elem, "cbc:LineExtensionAmount", {"currencyID": self.currency_code}).text = _format_decimal(item["line_net"])

            # Line Tax Total
            l_tax = ET.SubElement(line_elem, "cac:TaxTotal")
            ET.SubElement(l_tax, "cbc:TaxAmount", {"currencyID": self.tax_currency_code}).text = _format_decimal(item["line_tax"])
            ET.SubElement(l_tax, "cbc:RoundingAmount", {"currencyID": self.tax_currency_code}).text = _format_decimal(item["line_total_with_tax"])

            # Item details
            item_elem = ET.SubElement(line_elem, "cac:Item")
            ET.SubElement(item_elem, "cbc:Name").text = item["name"]

            item_tax_cat = ET.SubElement(item_elem, "cac:ClassifiedTaxCategory")
            ET.SubElement(item_tax_cat, "cbc:ID").text = item["tax_category_code"]
            ET.SubElement(item_tax_cat, "cbc:Percent").text = _format_decimal(item["tax_rate"])
            i_scheme = ET.SubElement(item_tax_cat, "cac:TaxScheme")
            ET.SubElement(i_scheme, "cbc:ID").text = item["tax_scheme"]

            # Price
            price_elem = ET.SubElement(line_elem, "cac:Price")
            ET.SubElement(price_elem, "cbc:PriceAmount", {"currencyID": self.currency_code}).text = _format_decimal(item["unit_price"], 4)

        return root

    def to_xml_bytes(self, encoding: str = "utf-8", pretty: bool = True) -> bytes:
        """Serializes the UBL document to XML bytes."""
        root = self.build_xml_tree()
        raw_xml = ET.tostring(root, encoding="utf-8")
        if pretty:
            reparsed = minidom.parseString(raw_xml)
            return reparsed.toprettyxml(indent="  ", encoding=encoding)
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + raw_xml

    def to_xml_string(self, pretty: bool = True) -> str:
        """Serializes the UBL document to an XML string."""
        return self.to_xml_bytes(encoding="utf-8", pretty=pretty).decode("utf-8")


class UBLBuilderService:
    """Service wrapper offering static builder convenience methods."""

    @staticmethod
    def build_invoice_xml(
        invoice_id: str,
        invoice_uuid: Optional[str] = None,
        issue_date: Optional[Union[str, datetime, date]] = None,
        issue_time: Optional[Union[str, datetime]] = None,
        invoice_type_code: str = INVOICE_TYPE_TAX_INVOICE,
        subtype: str = SUBTYPE_STANDARD_B2B,
        currency_code: str = "SAR",
        tax_currency_code: str = "SAR",
        icv: int = 1,
        pih: Optional[str] = None,
        qr_code_tlv: Optional[str] = None,
        seller: Optional[Dict[str, Any]] = None,
        buyer: Optional[Dict[str, Any]] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        tax_total: Optional[Union[float, Decimal, str]] = None,
        subtotal: Optional[Union[float, Decimal, str]] = None,
        grand_total: Optional[Union[float, Decimal, str]] = None,
        discount_total: Optional[Union[float, Decimal, str]] = 0.0,
        prepaid_amount: Optional[Union[float, Decimal, str]] = 0.0,
        payable_amount: Optional[Union[float, Decimal, str]] = None,
        note: Optional[str] = None,
    ) -> str:
        builder = UBLInvoiceBuilder(
            invoice_number=str(invoice_id),
            invoice_uuid=invoice_uuid,
            issue_date=issue_date,
            issue_time=issue_time,
            invoice_type_code=invoice_type_code,
            subtype=subtype,
            currency_code=currency_code,
            tax_currency_code=tax_currency_code,
            note=note,
            icv=icv,
            pih=pih,
            qr_code_tlv=qr_code_tlv,
        )

        if seller:
            builder.set_supplier(
                name=seller.get("name") or seller.get("seller_name", "Nova Enterprises"),
                tax_id=seller.get("tax_id") or seller.get("vat_number", "300000000000003"),
                crn=seller.get("crn") or seller.get("commercial_registration_number"),
                street=seller.get("street") or seller.get("street_name"),
                building_number=seller.get("building_number"),
                district=seller.get("district"),
                city=seller.get("city"),
                postal_code=seller.get("postal_code"),
                country_code=seller.get("country_code", "SA"),
            )

        if buyer:
            builder.set_customer(
                name=buyer.get("name") or buyer.get("customer_name", "Customer"),
                tax_id=buyer.get("tax_id") or buyer.get("vat_number"),
                crn=buyer.get("crn") or buyer.get("commercial_registration_number"),
                street=buyer.get("street") or buyer.get("street_name"),
                building_number=buyer.get("building_number"),
                district=buyer.get("district"),
                city=buyer.get("city"),
                postal_code=buyer.get("postal_code"),
                country_code=buyer.get("country_code", "SA"),
            )

        if line_items:
            for idx, item in enumerate(line_items, start=1):
                qty = float(item.get("quantity") or item.get("qty", 1.0))
                price = float(item.get("unit_price") or item.get("price", 0.0))
                disc = float(item.get("discount", 0.0))
                rate = float(item.get("tax_rate") or item.get("vat_rate", 15.0))
                builder.add_line_item(
                    name=item.get("name") or item.get("product_name") or f"Item {idx}",
                    quantity=qty,
                    unit_price=price,
                    unit_code=item.get("unit_code") or "PCE",
                    tax_rate=rate,
                    tax_category_code=item.get("tax_category") or item.get("tax_category_code") or "S",
                    tax_scheme="VAT",
                    discount=disc,
                    line_id=idx,
                )

        builder.calculate_totals()
        return builder.to_xml_string(pretty=True)


def generate_ubl_invoice_xml(
    invoice: Dict[str, Any],
    supplier_profile: Dict[str, Any],
    customer: Optional[Dict[str, Any]] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
    subtype: str = SUBTYPE_STANDARD_B2B,
    icv: int = 1,
    pih: Optional[str] = None,
    qr_code_tlv: Optional[str] = None,
) -> str:
    """Convenience helper to generate UBL 2.1 XML from invoice entity dictionaries."""
    inv_num = invoice.get("invoice_number", f"INV-{invoice.get('id', '1')}")
    inv_uuid = invoice.get("invoice_uuid") or str(uuid.uuid4())
    issue_date = invoice.get("issue_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    issue_time = invoice.get("created_at") or datetime.now(timezone.utc).strftime("%H:%M:%S")

    builder = UBLInvoiceBuilder(
        invoice_number=inv_num,
        invoice_uuid=inv_uuid,
        issue_date=issue_date,
        issue_time=issue_time,
        invoice_type_code=invoice.get("invoice_type_code", INVOICE_TYPE_TAX_INVOICE),
        subtype=subtype,
        currency_code=invoice.get("currency", "SAR"),
        tax_currency_code="SAR",
        note=invoice.get("notes"),
        icv=icv,
        pih=pih,
        qr_code_tlv=qr_code_tlv,
    )

    # Supplier
    builder.set_supplier(
        name=supplier_profile.get("seller_name", "Nova Enterprises"),
        tax_id=supplier_profile.get("tax_id", "300000000000003"),
        crn=supplier_profile.get("commercial_registration_number"),
        street=supplier_profile.get("street_name"),
        building_number=supplier_profile.get("building_number"),
        district=supplier_profile.get("district"),
        city=supplier_profile.get("city"),
        postal_code=supplier_profile.get("postal_code"),
        country_code=supplier_profile.get("country_code", "SA"),
    )

    # Customer
    if customer:
        builder.set_customer(
            name=customer.get("name") or customer.get("customer_name") or "Standard Customer",
            tax_id=customer.get("tax_id") or customer.get("vat_number"),
            crn=customer.get("crn") or customer.get("commercial_registration_number"),
            street=customer.get("street") or customer.get("address"),
            building_number=customer.get("building_number"),
            district=customer.get("district"),
            city=customer.get("city"),
            postal_code=customer.get("postal_code") or customer.get("zip"),
            country_code=customer.get("country_code", "SA"),
        )
    else:
        builder.set_customer(name="Walk-in Customer")

    # Lines
    item_lines = lines or invoice.get("lines") or []
    if item_lines:
        for idx, item in enumerate(item_lines, start=1):
            qty = float(item.get("qty") or item.get("quantity") or 1.0)
            price = float(item.get("unit_price") or item.get("price") or 0.0)
            disc = float(item.get("discount") or 0.0)
            tax_rate = float(item.get("tax_rate") or 15.0)
            builder.add_line_item(
                name=item.get("product_name") or item.get("name") or f"Item {idx}",
                quantity=qty,
                unit_price=price,
                unit_code=item.get("unit_code") or "PCE",
                tax_rate=tax_rate,
                tax_category_code=item.get("tax_category_code") or "S",
                tax_scheme="VAT",
                discount=disc,
                line_id=idx,
            )
    else:
        total = float(invoice.get("total_amount") or 0.0)
        net = round(total / 1.15, 2)
        builder.add_line_item(
            name="General Invoice Item",
            quantity=1.0,
            unit_price=net,
            tax_rate=15.0,
            line_id=1,
        )

    builder.calculate_totals()
    return builder.to_xml_string(pretty=True)

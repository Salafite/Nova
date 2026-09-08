"""
Nova ERP — B2B EDI Gateway & Supplier Catalog Sync Models
Pydantic domain models for EDI Trading Partners (T0124), SKU Cross-Reference Matrix (T0125),
EDI Transaction / Interchange Logs (T0126), SSCC Pallet Logistics (T0127), and Supplier Catalog Sync (T0128).
"""

from typing import Optional, Any, List, Dict
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field
from modules.core.models.base import AuditMixin, TenantMixin
from modules.core.repositories.base import CrudRepository


# ---------------------------------------------------------------------------
# Enums for EDI Standards, Document Types, and Statuses
# ---------------------------------------------------------------------------

class EdiStandard(str, Enum):
    ANSI_X12 = "ANSI_X12"
    EDIFACT = "EDIFACT"


class EdiCommunicationMethod(str, Enum):
    MANUAL = "MANUAL"
    API = "API"
    AS2 = "AS2"
    SFTP = "SFTP"


class EdiDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class EdiDocumentType(str, Enum):
    # ANSI X12
    X12_850 = "850"       # Purchase Order
    X12_856 = "856"       # Advance Shipping Notice (ASN)
    X12_810 = "810"       # Invoice
    X12_832 = "832"       # Price / Sales Catalog
    X12_997 = "997"       # Functional Acknowledgment
    # UN/EDIFACT
    ORDERS = "ORDERS"     # Purchase Order
    DESADV = "DESADV"     # Despatch Advice
    INVOIC = "INVOIC"     # Commercial Invoice
    PRICAT = "PRICAT"     # Price / Sales Catalogue
    CONTRL = "CONTRL"     # Syntactical / Functional Acknowledgment


class EdiTransactionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    PRICE_DISCREPANCY_HOLD = "PRICE_DISCREPANCY_HOLD"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class EdiAckStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    ACCEPTED_WITH_ERRORS = "ACCEPTED_WITH_ERRORS"


class EdiPackageType(str, Enum):
    PALLET = "PALLET"
    BOX = "BOX"
    CONTAINER = "CONTAINER"
    CASE = "CASE"


class EdiPalletStatus(str, Enum):
    CREATED = "CREATED"
    PACKED = "PACKED"
    STAGED = "STAGED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"


class EdiCatalogSyncStatus(str, Enum):
    SYNCED = "SYNCED"
    PENDING = "PENDING"
    UNMATCHED = "UNMATCHED"
    PRICE_CHANGED = "PRICE_CHANGED"


# ---------------------------------------------------------------------------
# 1. EDI Trading Partners (T0124)
# ---------------------------------------------------------------------------

class EdiPartnerCreate(BaseModel):
    partner_name: str = Field(..., max_length=255, description="Trading partner company name")
    partner_code: str = Field(..., max_length=50, description="Unique trading partner code (e.g. CRF-UAE)")
    edi_standard: str = Field('ANSI_X12', max_length=20, description="EDI standard format: ANSI_X12 | EDIFACT")
    interchange_sender_id: str = Field(..., max_length=50, description="Interchange Sender ID (ISA06 / UNB 0004)")
    interchange_receiver_id: str = Field(..., max_length=50, description="Interchange Receiver ID (ISA08 / UNB 0010)")
    sender_qualifier: str = Field('ZZ', max_length=10, description="Sender Qualifier (e.g. ZZ, 01, 14)")
    receiver_qualifier: str = Field('ZZ', max_length=10, description="Receiver Qualifier (e.g. ZZ, 01, 14)")
    communication_method: str = Field('MANUAL', max_length=30, description="Data transfer protocol: MANUAL | API | AS2 | SFTP")
    endpoint_url: Optional[str] = Field(None, description="AS2 / SFTP / Webhook endpoint URL")
    customer_id: Optional[int] = Field(None, description="Linked Customer account for Sales EDI (t0010)")
    supplier_id: Optional[int] = Field(None, description="Linked Supplier account for Purchasing EDI (t0014)")
    segment_terminator: str = Field('~', max_length=5, description="Segment delimiter character")
    element_separator: str = Field('*', max_length=5, description="Data element delimiter character")
    subelement_separator: str = Field('>', max_length=5, description="Subelement delimiter character")
    release_character: Optional[str] = Field('?', max_length=5, description="Escape/Release character for EDIFACT")
    auto_confirm_orders: bool = Field(False, description="Whether clean 850 PO orders are auto-confirmed")
    price_tolerance_percent: float = Field(0.00, description="Allowed price discrepancy threshold percentage")
    gs1_company_prefix: Optional[str] = Field(None, max_length=20, description="GS1 Company Prefix for SSCC-18 generation")
    is_active: bool = Field(True, description="Whether partner configuration is active")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiPartnerUpdate(BaseModel):
    partner_name: Optional[str] = Field(None, max_length=255)
    partner_code: Optional[str] = Field(None, max_length=50)
    edi_standard: Optional[str] = Field(None, max_length=20)
    interchange_sender_id: Optional[str] = Field(None, max_length=50)
    interchange_receiver_id: Optional[str] = Field(None, max_length=50)
    sender_qualifier: Optional[str] = Field(None, max_length=10)
    receiver_qualifier: Optional[str] = Field(None, max_length=10)
    communication_method: Optional[str] = Field(None, max_length=30)
    endpoint_url: Optional[str] = None
    customer_id: Optional[int] = None
    supplier_id: Optional[int] = None
    segment_terminator: Optional[str] = Field(None, max_length=5)
    element_separator: Optional[str] = Field(None, max_length=5)
    subelement_separator: Optional[str] = Field(None, max_length=5)
    release_character: Optional[str] = Field(None, max_length=5)
    auto_confirm_orders: Optional[bool] = None
    price_tolerance_percent: Optional[float] = None
    gs1_company_prefix: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class EdiPartnerResponse(AuditMixin):
    id: int
    partner_name: str
    partner_code: str
    edi_standard: str
    interchange_sender_id: str
    interchange_receiver_id: str
    sender_qualifier: str
    receiver_qualifier: str
    communication_method: str
    endpoint_url: Optional[str] = None
    customer_id: Optional[int] = None
    supplier_id: Optional[int] = None
    segment_terminator: str
    element_separator: str
    subelement_separator: str
    release_character: Optional[str] = None
    auto_confirm_orders: bool
    price_tolerance_percent: float
    gs1_company_prefix: Optional[str] = None
    is_active: bool


class EdiPartner(EdiPartnerResponse):
    pass


# ---------------------------------------------------------------------------
# 2. EDI SKU Cross-Reference Matrix (T0125)
# ---------------------------------------------------------------------------

class EdiSkuMappingCreate(BaseModel):
    partner_id: int = Field(..., description="Trading partner reference (t0124)")
    product_id: int = Field(..., description="Internal product reference (t0001)")
    partner_sku: str = Field(..., max_length=100, description="Partner SKU / Buyer Part Number")
    partner_sku_type: str = Field('BUYER_PART_NO', max_length=30, description="Identifier type: BUYER_PART_NO | GTIN | EAN | UPC | VENDOR_PART_NO")
    gtin: Optional[str] = Field(None, max_length=20, description="Global Trade Item Number / EAN barcode")
    partner_uom: str = Field('EA', max_length=20, description="Partner unit of measure (e.g. CA, EA, BX, PL)")
    internal_uom: str = Field('EA', max_length=20, description="Internal unit of measure (e.g. CASE, PCS, KG)")
    uom_conversion_factor: float = Field(1.0000, description="Multiplier to convert partner quantity to internal base quantity")
    catalog_price: Optional[float] = Field(None, description="Contractual or agreed reference price")
    is_active: bool = Field(True, description="Whether mapping is active")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiSkuMappingUpdate(BaseModel):
    partner_id: Optional[int] = None
    product_id: Optional[int] = None
    partner_sku: Optional[str] = Field(None, max_length=100)
    partner_sku_type: Optional[str] = Field(None, max_length=30)
    gtin: Optional[str] = Field(None, max_length=20)
    partner_uom: Optional[str] = Field(None, max_length=20)
    internal_uom: Optional[str] = Field(None, max_length=20)
    uom_conversion_factor: Optional[float] = None
    catalog_price: Optional[float] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class EdiSkuMappingResponse(AuditMixin):
    id: int
    partner_id: int
    product_id: int
    partner_sku: str
    partner_sku_type: str
    gtin: Optional[str] = None
    partner_uom: str
    internal_uom: str
    uom_conversion_factor: float
    catalog_price: Optional[float] = None
    is_active: bool


class EdiSkuMapping(EdiSkuMappingResponse):
    pass


# ---------------------------------------------------------------------------
# 3. EDI Transaction / Interchange Logs (T0126)
# ---------------------------------------------------------------------------

class EdiTransactionCreate(BaseModel):
    transaction_number: Optional[str] = Field(None, max_length=50, description="Unique transaction number (auto-generated if omitted)")
    partner_id: Optional[int] = Field(None, description="Trading partner reference (t0124)")
    standard: str = Field(..., max_length=20, description="EDI standard: ANSI_X12 | EDIFACT")
    document_type: str = Field(..., max_length=20, description="Document type: 850, 856, 810, 832, 997, ORDERS, DESADV, INVOIC, PRICAT, CONTRL")
    direction: str = Field(..., max_length=10, description="Transmission direction: INBOUND | OUTBOUND")
    control_number: Optional[str] = Field(None, max_length=50, description="Interchange control number")
    status: str = Field('PENDING', max_length=30, description="Status: PENDING | PROCESSED | FAILED | PRICE_DISCREPANCY_HOLD | ACKNOWLEDGED")
    sales_order_id: Optional[int] = Field(None, description="Linked sales order (t0012)")
    delivery_id: Optional[int] = Field(None, description="Linked delivery dispatch (t0016)")
    invoice_id: Optional[int] = Field(None, description="Linked sales invoice (t0026)")
    raw_payload: str = Field(..., description="Raw unparsed EDI message text")
    parsed_data: Optional[Any] = Field(None, description="Structured parsed JSON representation")
    ack_status: Optional[str] = Field('PENDING', max_length=30, description="Acknowledgment status: PENDING | ACCEPTED | REJECTED | ACCEPTED_WITH_ERRORS")
    ack_payload: Optional[str] = Field(None, description="Generated or received 997 FA / CONTRL message")
    error_details: Optional[str] = Field(None, description="Validation or processing error details")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiTransactionUpdate(BaseModel):
    transaction_number: Optional[str] = Field(None, max_length=50)
    partner_id: Optional[int] = None
    standard: Optional[str] = Field(None, max_length=20)
    document_type: Optional[str] = Field(None, max_length=20)
    direction: Optional[str] = Field(None, max_length=10)
    control_number: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=30)
    sales_order_id: Optional[int] = None
    delivery_id: Optional[int] = None
    invoice_id: Optional[int] = None
    raw_payload: Optional[str] = None
    parsed_data: Optional[Any] = None
    ack_status: Optional[str] = Field(None, max_length=30)
    ack_payload: Optional[str] = None
    error_details: Optional[str] = None
    processed_at: Optional[datetime] = None
    business_id: Optional[int] = None


class EdiTransactionResponse(AuditMixin):
    id: int
    transaction_number: str
    partner_id: Optional[int] = None
    standard: str
    document_type: str
    direction: str
    control_number: Optional[str] = None
    status: str
    sales_order_id: Optional[int] = None
    delivery_id: Optional[int] = None
    invoice_id: Optional[int] = None
    raw_payload: str
    parsed_data: Optional[Any] = None
    ack_status: Optional[str] = None
    ack_payload: Optional[str] = None
    error_details: Optional[str] = None
    processed_at: Optional[datetime] = None


class EdiTransaction(EdiTransactionResponse):
    pass


# ---------------------------------------------------------------------------
# 4. EDI SSCC Pallet Logistics (T0127)
# ---------------------------------------------------------------------------

class EdiSsccPalletCreate(BaseModel):
    sscc_barcode: str = Field(..., max_length=20, description="18-digit Serial Shipping Container Code (GS1 SSCC-18)")
    delivery_id: Optional[int] = Field(None, description="Delivery shipment reference (t0016)")
    sales_order_id: Optional[int] = Field(None, description="Sales order reference (t0012)")
    pallet_number: Optional[str] = Field(None, max_length=50, description="Pallet identifier (e.g. PLT-001)")
    package_type: str = Field('PALLET', max_length=30, description="Container level: PALLET | BOX | CONTAINER | CASE")
    parent_sscc_id: Optional[int] = Field(None, description="Parent packaging SSCC for nested hierarchies")
    gross_weight_kg: Optional[float] = Field(None, description="Gross weight in KG")
    net_weight_kg: Optional[float] = Field(None, description="Net weight in KG")
    tare_weight_kg: Optional[float] = Field(None, description="Tare weight in KG")
    volume_cbm: Optional[float] = Field(None, description="Volume in cubic meters")
    items_count: int = Field(0, description="Total units count")
    contents_summary: Optional[Any] = Field(None, description="JSON summary of items and batch numbers")
    status: str = Field('PACKED', max_length=30, description="Status: CREATED | PACKED | STAGED | DISPATCHED | DELIVERED")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiSsccPalletUpdate(BaseModel):
    sscc_barcode: Optional[str] = Field(None, max_length=20)
    delivery_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    pallet_number: Optional[str] = Field(None, max_length=50)
    package_type: Optional[str] = Field(None, max_length=30)
    parent_sscc_id: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    items_count: Optional[int] = None
    contents_summary: Optional[Any] = None
    status: Optional[str] = Field(None, max_length=30)
    business_id: Optional[int] = None


class EdiSsccPalletResponse(AuditMixin):
    id: int
    sscc_barcode: str
    delivery_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    pallet_number: Optional[str] = None
    package_type: str
    parent_sscc_id: Optional[int] = None
    gross_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = None
    volume_cbm: Optional[float] = None
    items_count: int
    contents_summary: Optional[Any] = None
    status: str


class EdiSsccPallet(EdiSsccPalletResponse):
    pass


# ---------------------------------------------------------------------------
# 5. Supplier Catalog Sync / 832 PRICAT (T0128)
# ---------------------------------------------------------------------------

class EdiCatalogItemCreate(BaseModel):
    partner_id: int = Field(..., description="Trading partner reference (t0124)")
    catalog_code: str = Field(..., max_length=50, description="Catalog batch/version code")
    buyer_sku: str = Field(..., max_length=100, description="Buyer / Supermarket SKU")
    supplier_sku: Optional[str] = Field(None, max_length=100, description="Supplier / Vendor SKU")
    gtin: Optional[str] = Field(None, max_length=20, description="Global Trade Item Number / EAN")
    product_name: str = Field(..., max_length=255, description="Product description / name")
    product_description: Optional[str] = Field(None, description="Detailed specifications")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    uom: str = Field('EA', max_length=20, description="Unit of measure")
    pack_size: int = Field(1, description="Units per retail pack")
    list_price: float = Field(0.00, description="Catalog wholesale list price")
    currency: str = Field('USD', max_length=10, description="Currency code (e.g. USD, EUR, AED)")
    effective_start_date: Optional[date] = Field(None, description="Price validity start date")
    effective_end_date: Optional[date] = Field(None, description="Price validity expiration date")
    matched_product_id: Optional[int] = Field(None, description="Matched internal Nova product (t0001)")
    sync_status: str = Field('SYNCED', max_length=30, description="Status: SYNCED | PENDING | UNMATCHED | PRICE_CHANGED")
    is_active: bool = Field(True, description="Whether item is active")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiCatalogItemUpdate(BaseModel):
    partner_id: Optional[int] = None
    catalog_code: Optional[str] = Field(None, max_length=50)
    buyer_sku: Optional[str] = Field(None, max_length=100)
    supplier_sku: Optional[str] = Field(None, max_length=100)
    gtin: Optional[str] = Field(None, max_length=20)
    product_name: Optional[str] = Field(None, max_length=255)
    product_description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    uom: Optional[str] = Field(None, max_length=20)
    pack_size: Optional[int] = None
    list_price: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=10)
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    matched_product_id: Optional[int] = None
    sync_status: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None
    business_id: Optional[int] = None


class EdiCatalogItemResponse(AuditMixin):
    id: int
    partner_id: int
    catalog_code: str
    buyer_sku: str
    supplier_sku: Optional[str] = None
    gtin: Optional[str] = None
    product_name: str
    product_description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    uom: str
    pack_size: int
    list_price: float
    currency: str
    effective_start_date: Optional[date] = None
    effective_end_date: Optional[date] = None
    matched_product_id: Optional[int] = None
    sync_status: str
    is_active: bool


class EdiCatalogItem(EdiCatalogItemResponse):
    pass


# ---------------------------------------------------------------------------
# Workflow Request / Response Schemas
# ---------------------------------------------------------------------------

class EdiIngestRequest(BaseModel):
    partner_id: Optional[int] = Field(None, description="Optional trading partner ID override")
    raw_payload: str = Field(..., description="Raw EDI interchange document text")
    standard: Optional[str] = Field(None, description="Standard override (ANSI_X12 or EDIFACT)")
    document_type: Optional[str] = Field(None, description="Document type (850, ORDERS, 832, etc.)")
    direction: str = Field("INBOUND", description="Transmission direction")
    auto_confirm: Optional[bool] = Field(None, description="Override partner auto_confirm setting")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiLineDiscrepancy(BaseModel):
    line_number: int
    buyer_sku: str
    partner_sku_type: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    ordered_price: float
    contract_price: float
    discrepancy_percent: float
    discrepancy_type: str = "PRICE_MISMATCH"
    details: Optional[str] = None


class EdiIngestResult(BaseModel):
    transaction_id: int
    transaction_number: str
    status: str
    standard: str
    document_type: str
    control_number: Optional[str] = None
    partner_id: Optional[int] = None
    partner_code: Optional[str] = None
    sales_order_id: Optional[int] = None
    sales_order_number: Optional[str] = None
    ack_generated: bool = False
    ack_payload: Optional[str] = None
    price_discrepancies: List[EdiLineDiscrepancy] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class EdiReprocessRequest(BaseModel):
    transaction_id: int
    force_confirm: bool = Field(False, description="Force confirm order even with price discrepancies")
    override_price_tolerance: Optional[float] = Field(None, description="Custom tolerance percent for this run")


class EdiAsnGenerateRequest(BaseModel):
    delivery_id: int = Field(..., description="Nova delivery shipment ID (t0016)")
    partner_id: Optional[int] = Field(None, description="Partner ID override (defaults to partner linked to delivery/customer)")
    carrier_name: Optional[str] = Field(None, description="Carrier name / SCAC code")
    tracking_number: Optional[str] = Field(None, description="Bill of lading / tracking number")
    vehicle_number: Optional[str] = Field(None, description="Truck license plate or vehicle number")
    seal_number: Optional[str] = Field(None, description="Container seal number")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiAsnGenerateResponse(BaseModel):
    transaction_id: int
    transaction_number: str
    delivery_id: int
    control_number: str
    standard: str
    document_type: str
    sscc_pallets_count: int
    sscc_barcodes: List[str] = Field(default_factory=list)
    edi_payload: str


class EdiInvoiceTransmitRequest(BaseModel):
    invoice_id: int = Field(..., description="Nova invoice ID (t0026)")
    delivery_id: Optional[int] = Field(None, description="Optional delivery reference (t0016)")
    partner_id: Optional[int] = Field(None, description="Partner ID override")
    business_id: Optional[int] = Field(None, description="Tenant business ID")


class EdiInvoiceTransmitResponse(BaseModel):
    transaction_id: int
    transaction_number: str
    invoice_id: int
    invoice_number: str
    control_number: str
    standard: str
    document_type: str
    edi_payload: str


class EdiCatalogSyncRequest(BaseModel):
    partner_id: int
    catalog_code: str
    items: List[Dict[str, Any]] = Field(default_factory=list)
    auto_match_skus: bool = True
    business_id: Optional[int] = None


class EdiCatalogSyncResponse(BaseModel):
    partner_id: int
    catalog_code: str
    total_items: int
    matched_items: int
    unmatched_items: int
    price_updated_items: int
    sync_status: str


# ---------------------------------------------------------------------------
# CrudRepositories for EDI Tables
# ---------------------------------------------------------------------------

EDI_PARTNER_REPO = CrudRepository(
    'T0124',
    business_columns=[
        'id', 'partner_name', 'partner_code', 'edi_standard',
        'interchange_sender_id', 'interchange_receiver_id',
        'sender_qualifier', 'receiver_qualifier', 'communication_method',
        'endpoint_url', 'customer_id', 'supplier_id',
        'segment_terminator', 'element_separator', 'subelement_separator',
        'release_character', 'auto_confirm_orders', 'price_tolerance_percent',
        'gs1_company_prefix', 'is_active'
    ]
)

EDI_SKU_MAPPING_REPO = CrudRepository(
    'T0125',
    business_columns=[
        'id', 'partner_id', 'product_id', 'partner_sku', 'partner_sku_type',
        'gtin', 'partner_uom', 'internal_uom', 'uom_conversion_factor',
        'catalog_price', 'is_active'
    ]
)

EDI_TRANSACTION_REPO = CrudRepository(
    'T0126',
    business_columns=[
        'id', 'transaction_number', 'partner_id', 'standard', 'document_type',
        'direction', 'control_number', 'status', 'sales_order_id',
        'delivery_id', 'invoice_id', 'raw_payload', 'parsed_data',
        'ack_status', 'ack_payload', 'error_details', 'processed_at'
    ]
)

EDI_SSCC_PALLET_REPO = CrudRepository(
    'T0127',
    business_columns=[
        'id', 'sscc_barcode', 'delivery_id', 'sales_order_id', 'pallet_number',
        'package_type', 'parent_sscc_id', 'gross_weight_kg', 'net_weight_kg',
        'tare_weight_kg', 'volume_cbm', 'items_count', 'contents_summary', 'status'
    ]
)

EDI_CATALOG_ITEM_REPO = CrudRepository(
    'T0128',
    business_columns=[
        'id', 'partner_id', 'catalog_code', 'buyer_sku', 'supplier_sku',
        'gtin', 'product_name', 'product_description', 'category', 'brand',
        'uom', 'pack_size', 'list_price', 'currency', 'effective_start_date',
        'effective_end_date', 'matched_product_id', 'sync_status', 'is_active'
    ]
)

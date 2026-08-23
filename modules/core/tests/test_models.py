import pytest
from datetime import datetime, timezone
from modules.core.models.base import TenantMixin, AuditMixin
from modules.core.models.factory import crud_model
from modules.crm.models.crm import CustomerCreate, CustomerResponse
from modules.inventory.models.product import ProductCreate, ProductResponse
from modules.sales.models.sales import SalesOrderCreate, SalesOrderResponse
from modules.sales.models.price_list import PriceListCreate, PriceListResponse
from modules.administration.models.system import UserCreate, UserResponse, AuditLogResponse, SettingResponse
from modules.administration.models.notification import NotificationCreate, NotificationResponse
from modules.accounting.models.finance import InvoiceCreate, InvoiceResponse


def test_tenant_mixin():
    obj = TenantMixin()
    assert obj.business_id is None

    obj_with_tenant = TenantMixin(business_id=42)
    assert obj_with_tenant.business_id == 42


def test_audit_mixin_includes_tenant_and_audit_fields():
    obj = AuditMixin()
    assert obj.business_id is None
    assert obj.created_at is None
    assert obj.created_by is None
    assert obj.updated_at is None
    assert obj.updated_by is None
    assert obj.update_number == 1

    now = datetime.now(timezone.utc)
    obj_populated = AuditMixin(
        business_id=10,
        created_at=now,
        created_by=1,
        updated_at=now,
        updated_by=1,
        update_number=2
    )
    assert obj_populated.business_id == 10
    assert obj_populated.created_by == 1
    assert obj_populated.update_number == 2


def test_crud_model_factory_defaults():
    ItemCreate, ItemUpdate, ItemResponse = crud_model('TestItem', [
        ('title', str, ...),
        ('price', float, 0.0),
    ])

    # Test Create model supports optional business_id
    create_inst = ItemCreate(title='Test Item', price=19.99, business_id=5)
    assert create_inst.title == 'Test Item'
    assert create_inst.price == 19.99
    assert create_inst.business_id == 5

    create_no_tenant = ItemCreate(title='Test Item 2')
    assert create_no_tenant.business_id is None

    # Test Update model supports optional business_id
    update_inst = ItemUpdate(title='Updated Title', business_id=5)
    assert update_inst.title == 'Updated Title'
    assert update_inst.business_id == 5

    # Test Response model inherits AuditMixin and business_id
    resp_inst = ItemResponse(
        id=1,
        title='Item 1',
        price=10.0,
        business_id=5,
        update_number=1
    )
    assert resp_inst.id == 1
    assert resp_inst.title == 'Item 1'
    assert resp_inst.business_id == 5
    assert resp_inst.update_number == 1


def test_crud_model_factory_no_audit_with_tenant():
    ItemCreate, ItemUpdate, ItemResponse = crud_model(
        'TestNoAudit',
        [('name', str, ...)],
        audit=False,
        tenant=True
    )

    resp = ItemResponse(id=1, name='NoAuditItem', business_id=99)
    assert resp.id == 1
    assert resp.name == 'NoAuditItem'
    assert resp.business_id == 99
    assert not hasattr(resp, 'created_at') or 'created_at' not in resp.model_fields


def test_crud_model_factory_no_tenant():
    ItemCreate, ItemUpdate, ItemResponse = crud_model(
        'TestNoTenant',
        [('name', str, ...)],
        audit=False,
        tenant=False
    )

    create_inst = ItemCreate(name='NoTenantItem')
    assert 'business_id' not in ItemCreate.model_fields
    assert 'business_id' not in ItemResponse.model_fields


def test_crm_customer_models_support_business_id():
    cust_create = CustomerCreate(name='ACME Corp', business_id=3)
    assert cust_create.name == 'ACME Corp'
    assert cust_create.business_id == 3

    cust_resp = CustomerResponse(id=10, name='ACME Corp', business_id=3)
    assert cust_resp.id == 10
    assert cust_resp.business_id == 3


def test_inventory_product_models_support_business_id():
    prod_resp = ProductResponse(
        id=1,
        name='Widget A',
        sku='WGT-A',
        type='stockable',
        price=25.0,
        tax_rate=0.05,
        weight=1.0,
        volume=0.5,
        is_purchasable=True,
        is_saleable=True,
        is_active=True,
        business_id=7
    )
    assert prod_resp.business_id == 7
    assert prod_resp.sku == 'WGT-A'


def test_administration_system_models_support_business_id():
    u_create = UserCreate(username='johndoe', full_name='John Doe', business_id=12)
    assert u_create.business_id == 12

    audit_resp = AuditLogResponse(
        id=1,
        table_name='T0001',
        record_id=100,
        action='INSERT',
        business_id=12
    )
    assert audit_resp.business_id == 12

    notif_create = NotificationCreate(user_id=1, title='Alert', business_id=12)
    assert notif_create.business_id == 12

    notif_resp = NotificationResponse(
        id=1,
        user_id=1,
        title='Alert',
        notification_type='Info',
        is_read=False,
        business_id=12
    )
    assert notif_resp.business_id == 12


def test_sales_and_accounting_models_support_business_id():
    pl_create = PriceListCreate(name='Retail List', code='PL-01', business_id=4)
    assert pl_create.business_id == 4

    pl_resp = PriceListResponse(id=1, name='Retail List', code='PL-01', currency='USD', is_active=True, is_default=False, business_id=4)
    assert pl_resp.business_id == 4

    inv_resp = InvoiceResponse(
        id=1,
        invoice_number='INV-2026-001',
        invoice_type='Sales',
        partner_id=10,
        issue_date=datetime.now().date(),
        due_date=datetime.now().date(),
        total_amount=500.0,
        status='Unpaid',
        business_id=4
    )
    assert inv_resp.business_id == 4


def test_maintenance_models_support_business_id():
    from modules.maintenance.models.asset import (
        AssetCreate, AssetUpdate, AssetResponse,
        MaintenanceScheduleCreate, MaintenanceScheduleResponse,
        MaintenanceWorkOrderCreate, MaintenanceWorkOrderResponse
    )
    ac = AssetCreate(asset_code='AST-001', asset_name='Forklift A', business_id=8)
    assert ac.business_id == 8
    ar = AssetResponse(id=1, asset_code='AST-001', asset_name='Forklift A', purchase_cost=5000.0, status='Operational', is_active=True, business_id=8)
    assert ar.business_id == 8

    msc = MaintenanceScheduleCreate(asset_id=1, schedule_code='MSC-001', business_id=8)
    assert msc.business_id == 8
    msr = MaintenanceScheduleResponse(id=1, asset_id=1, schedule_code='MSC-001', frequency_type='Monthly', frequency_value=1, is_active=True, business_id=8)
    assert msr.business_id == 8

    woc = MaintenanceWorkOrderCreate(asset_id=1, work_order_code='MWO-001', business_id=8)
    assert woc.business_id == 8
    wor = MaintenanceWorkOrderResponse(id=1, asset_id=1, work_order_code='MWO-001', description='Oil change', priority='Medium', status='Open', cost=150.0, is_active=True, business_id=8)
    assert wor.business_id == 8


def test_project_models_support_business_id():
    from modules.projects.models.project import (
        ProjectCreate, ProjectResponse,
        ProjectTaskCreate, ProjectTaskResponse,
        TimesheetCreate, TimesheetResponse,
        ContractCreate, ContractResponse,
        SLADefinitionCreate, SLADefinitionResponse
    )
    pc = ProjectCreate(project_code='PRJ-001', project_name='ERP Rollout', business_id=9)
    assert pc.business_id == 9
    pr = ProjectResponse(id=1, project_code='PRJ-001', project_name='ERP Rollout', budget=100000.0, status='Active', is_active=True, business_id=9)
    assert pr.business_id == 9

    tc = ProjectTaskCreate(project_id=1, task_code='TSK-01', task_name='Data Migration', business_id=9)
    assert tc.business_id == 9

    tsc = TimesheetCreate(employee_id=1, date=datetime.now().date(), hours=8.0, business_id=9)
    assert tsc.business_id == 9

    cc = ContractCreate(contract_code='CNT-01', contract_name='Support Agreement', start_date=datetime.now().date(), business_id=9)
    assert cc.business_id == 9

    slac = SLADefinitionCreate(contract_id=1, sla_code='SLA-01', sla_name='P1 Support', business_id=9)
    assert slac.business_id == 9


def test_purchasing_and_manufacturing_models_support_business_id():
    from modules.purchasing.models.purchase import (
        PurchaseOrderCreate, PurchaseOrderResponse,
        RequisitionCreate, RequisitionResponse,
        RFQCreate, RFQResponse
    )
    from modules.manufacturing.models.bom import BOMCreate, BOMResponse, BOMLineCreate
    from modules.manufacturing.models.manufacturing import MfgOrderCreate, MfgOrderResponse, QCInspectionCreate, ShopJobCreate

    poc = PurchaseOrderCreate(order_number='PO-001', supplier_id=2, business_id=11)
    assert poc.business_id == 11
    por = PurchaseOrderResponse(id=1, order_number='PO-001', supplier_id=2, total=1200.0, status='Pending', order_date=datetime.now().date(), business_id=11)
    assert por.business_id == 11

    rc = RequisitionCreate(req_number='REQ-001', title='New Monitors', requested_by=1, business_id=11)
    assert rc.business_id == 11

    rfqc = RFQCreate(rfq_number='RFQ-001', business_id=11)
    assert rfqc.business_id == 11

    bomc = BOMCreate(bom_code='BOM-001', bom_name='Custom PC', product_id=10, business_id=11)
    assert bomc.business_id == 11

    mfgc = MfgOrderCreate(order_number='MO-001', product_name='Custom PC', quantity=10, business_id=11)
    assert mfgc.business_id == 11

    qcc = QCInspectionCreate(inspection_no='QC-001', product_name='Custom PC', business_id=11)
    assert qcc.business_id == 11

    sjc = ShopJobCreate(job_number='SJ-001', product_name='Custom PC', quantity=10, business_id=11)
    assert sjc.business_id == 11


def test_warehouse_and_sales_models_support_business_id():
    from modules.warehouse.models.warehouse import WarehouseCreate, GoodsReceiptCreate, GoodsReceiptResponse
    from modules.warehouse.models.pick_list import PickListCreate, PickListResponse
    from modules.warehouse.models.serial_batch import SerialNumberCreate, BatchNumberCreate
    from modules.sales.models.delivery import DeliveryCreate, DeliveryResponse
    from modules.sales.models.quotations import QuotationCreate, QuotationResponse
    from modules.sales.models.sales_return import SalesReturnCreate, SalesReturnResponse
    from modules.sales.models.tax import TaxRateCreate, TaxRateResponse
    from modules.search.models.search import SearchIndexCreate, SearchIndexResponse
    from modules.inventory.models.counts import InventoryCountCreate, CountItemCreate
    from modules.pos.models.pos import PosCheckoutRequest, PosCartItem

    wc = WarehouseCreate(name='Main Hub', business_id=15)
    assert wc.business_id == 15

    grc = GoodsReceiptCreate(receipt_number='GR-001', business_id=15)
    assert grc.business_id == 15

    plc = PickListCreate(pick_list_number='PK-001', sales_order_id=5, business_id=15)
    assert plc.business_id == 15

    snc = SerialNumberCreate(product_id=1, serial_number='SN12345', business_id=15)
    assert snc.business_id == 15

    bnc = BatchNumberCreate(product_id=1, batch_number='BAT12345', business_id=15)
    assert bnc.business_id == 15

    dc = DeliveryCreate(delivery_number='DLV-001', sales_order_id=5, business_id=15)
    assert dc.business_id == 15

    qc = QuotationCreate(quote_number='QT-001', customer_id=3, business_id=15)
    assert qc.business_id == 15

    src = SalesReturnCreate(return_number='SR-001', customer_id=3, business_id=15)
    assert src.business_id == 15

    trc = TaxRateCreate(name='VAT Standard', code='VAT15', rate=15.0, business_id=15)
    assert trc.business_id == 15

    sic = SearchIndexCreate(entity_type='Product', entity_id=1, business_id=15)
    assert sic.business_id == 15

    icc = InventoryCountCreate(count_number='CNT-01', count_date=datetime.now().date(), business_id=15)
    assert icc.business_id == 15

    pos_req = PosCheckoutRequest(
        cart_items=[PosCartItem(product_id=1, product_name='Item A', qty=2, unit_price=10.0)],
        business_id=15
    )
    assert pos_req.business_id == 15

from modules.core.models.base import AuditMixin

# Administration
from modules.administration.models.system import (
    UserCreate, UserUpdate, UserResponse,
    NavPermissionCreate, NavPermissionUpdate, NavPermissionResponse,
    AuditLogCreate, AuditLogResponse,
)
from modules.administration.models.notification import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
)
from modules.administration.models.scheduler import (
    ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskResponse,
)
from modules.administration.models.module_registry import (
    ModuleRegistryCreate, ModuleRegistryUpdate, ModuleRegistryResponse,
)

# Inventory
from modules.inventory.models.product import (
    UOMCreate, UOMUpdate, UOMResponse,
    UOMConvCreate, UOMConvUpdate, UOMConvResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    BarcodeCreate, BarcodeUpdate, BarcodeResponse,
    AttrDefCreate, AttrDefUpdate, AttrDefResponse,
    AttrValueCreate, AttrValueUpdate, AttrValueResponse,
    ProductUOMCreate, ProductUOMUpdate, ProductUOMResponse,
)
from modules.inventory.models.stock_movement import (
    StockMovementCreate, StockMovementResponse,
)

# Warehouse
from modules.warehouse.models.warehouse import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    InventoryCreate, InventoryUpdate, InventoryResponse,
    GoodsReceiptCreate, GoodsReceiptUpdate, GoodsReceiptResponse,
    GoodsReceiptLineCreate, GoodsReceiptLineUpdate, GoodsReceiptLineResponse,
)
from modules.warehouse.models.serial_batch import (
    SerialNumberCreate, SerialNumberUpdate, SerialNumberResponse,
    BatchNumberCreate, BatchNumberUpdate, BatchNumberResponse,
)

# CRM
from modules.crm.models.crm import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    SupplierCreate, SupplierUpdate, SupplierResponse,
)
from modules.crm.models.crm_lead import (
    LeadCreate, LeadUpdate, LeadResponse,
    LeadActivityCreate, LeadActivityUpdate, LeadActivityResponse,
    OpportunityCreate, OpportunityUpdate, OpportunityResponse,
    OpportunityLineCreate, OpportunityLineUpdate, OpportunityLineResponse,
)

# Sales
from modules.sales.models.sales import (
    SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse,
    SalesLineCreate, SalesLineUpdate, SalesLineResponse,
    InstallmentPlanCreate, InstallmentPlanUpdate, InstallmentPlanResponse,
    InstallPaymentCreate, InstallPaymentUpdate, InstallPaymentResponse,
)
from modules.sales.models.quotations import (
    QuotationCreate, QuotationUpdate, QuotationResponse,
    QuotationLineCreate, QuotationLineUpdate, QuotationLineResponse,
)
from modules.sales.models.delivery import (
    DeliveryCreate, DeliveryUpdate, DeliveryResponse,
    DeliveryLineCreate, DeliveryLineUpdate, DeliveryLineResponse,
)
from modules.sales.models.sales_return import (
    SalesReturnCreate, SalesReturnUpdate, SalesReturnResponse,
    SalesReturnLineCreate, SalesReturnLineUpdate, SalesReturnLineResponse,
)
from modules.sales.models.tax import (
    TaxRateCreate, TaxRateUpdate, TaxRateResponse,
    TaxRuleCreate, TaxRuleUpdate, TaxRuleResponse,
)
from modules.sales.models.price_list import (
    PriceListCreate, PriceListUpdate, PriceListResponse,
    PriceListItemCreate, PriceListItemUpdate, PriceListItemResponse,
)

# Purchasing
from modules.purchasing.models.purchase import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    PurchaseLineCreate, PurchaseLineUpdate, PurchaseLineResponse,
    RequisitionCreate, RequisitionUpdate, RequisitionResponse,
    RequisitionLineCreate, RequisitionLineUpdate, RequisitionLineResponse,
    RFQCreate, RFQUpdate, RFQResponse,
    RFQLineCreate, RFQLineUpdate, RFQLineResponse,
    RFQVendorCreate, RFQVendorUpdate, RFQVendorResponse,
    RFQQuoteCreate, RFQQuoteUpdate, RFQQuoteResponse,
)
from modules.purchasing.models.purchase_return import (
    PurchaseReturnCreate, PurchaseReturnUpdate, PurchaseReturnResponse,
    PurchaseReturnLineCreate, PurchaseReturnLineUpdate, PurchaseReturnLineResponse,
)

# Manufacturing
from modules.manufacturing.models.manufacturing import (
    MfgOrderCreate, MfgOrderUpdate, MfgOrderResponse,
    QCInspectionCreate, QCInspectionUpdate, QCInspectionResponse,
    ShopJobCreate, ShopJobUpdate, ShopJobResponse,
)
from modules.manufacturing.models.bom import (
    BOMCreate, BOMUpdate, BOMResponse,
    BOMLineCreate, BOMLineUpdate, BOMLineResponse,
)

# Accounting
from modules.accounting.models.finance import (
    COACreate, COAUpdate, COAResponse,
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    JournalLineCreate, JournalLineUpdate, JournalLineResponse,
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    PaymentCreate, PaymentUpdate, PaymentResponse,
)
from modules.accounting.models.payment_term import (
    PaymentTermCreate, PaymentTermUpdate, PaymentTermResponse,
    PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse,
)

# HR
from modules.hr.models.employee import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    DesignationCreate, DesignationUpdate, DesignationResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeContractCreate, EmployeeContractUpdate, EmployeeContractResponse,
    EmployeeDocumentCreate, EmployeeDocumentUpdate, EmployeeDocumentResponse,
    ShiftCreate, ShiftUpdate, ShiftResponse,
    AttendanceCreate, AttendanceUpdate, AttendanceResponse,
    LeaveTypeCreate, LeaveTypeUpdate, LeaveTypeResponse,
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    PayrollPeriodCreate, PayrollPeriodUpdate, PayrollPeriodResponse,
    PayrollEntryCreate, PayrollEntryUpdate, PayrollEntryResponse,
    JobOpeningCreate, JobOpeningUpdate, JobOpeningResponse,
    CandidateCreate, CandidateUpdate, CandidateResponse,
)

# Maintenance
from modules.maintenance.models.asset import (
    AssetCreate, AssetUpdate, AssetResponse,
    MaintenanceScheduleCreate, MaintenanceScheduleUpdate, MaintenanceScheduleResponse,
    MaintenanceWorkOrderCreate, MaintenanceWorkOrderUpdate, MaintenanceWorkOrderResponse,
)

# Projects
from modules.projects.models.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectTaskCreate, ProjectTaskUpdate, ProjectTaskResponse,
    ResourceAllocationCreate, ResourceAllocationUpdate, ResourceAllocationResponse,
    TimesheetCreate, TimesheetUpdate, TimesheetResponse,
    ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestResponse,
    ContractCreate, ContractUpdate, ContractResponse,
    SLADefinitionCreate, SLADefinitionUpdate, SLADefinitionResponse,
)

# Planning
from modules.planning.models.planning import PlanCreate, PlanUpdate, PlanResponse

# Search
from modules.search.models.search import (
    SearchIndexCreate, SearchIndexUpdate, SearchIndexResponse,
)

# BI
from modules.bi.models.analytics import (
    KPIDefinitionCreate, KPIDefinitionUpdate, KPIDefinitionResponse,
    KPIValueCreate, KPIValueUpdate, KPIValueResponse,
    BIDashboardCreate, BIDashboardUpdate, BIDashboardResponse,
    DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse,
)

# Integrations
from modules.integrations.models.integration import (
    ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse,
    IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigResponse,
    SyncLogCreate, SyncLogResponse,
)

# Enterprise
from modules.enterprise.models.enterprise import (
    TenantCreate, TenantUpdate, TenantResponse,
    WorkflowDefinitionCreate, WorkflowDefinitionUpdate, WorkflowDefinitionResponse,
    WorkflowInstanceCreate, WorkflowInstanceUpdate, WorkflowInstanceResponse,
    DocumentCreate, DocumentUpdate, DocumentResponse,
    ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse,
)

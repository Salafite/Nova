window.controllers = window.controllers || {}
window._dataReady = false
window._dataReadyCallbacks = window._dataReadyCallbacks || []

function onDataReady(fn) {
  if (window._dataReady) fn()
  else window._dataReadyCallbacks.push(fn)
}

;(async function bootstrap() {
  var productClient = new ProductClient()
  var customerClient = new CustomerClient()
  var supplierClient = new SupplierClient()
  var inventoryClient = new InventoryClient()
  var salesOrderClient = new SalesOrderClient()
  var purchaseOrderClient = new PurchaseOrderClient()

  try {
    await Promise.all([
      productClient.load(),
      customerClient.load(),
      supplierClient.load(),
      inventoryClient.load(),
      salesOrderClient.load(),
      purchaseOrderClient.load(),
    ])
  } catch (e) {
    console.warn('Data load failed, using empty caches', e)
  }

  window.productService = new ProductService(productClient, null)
  window.inventoryService = new InventoryService(inventoryClient)
  window.salesService = new SalesService(salesOrderClient, customerClient)
  window.purchaseService = new PurchaseService(purchaseOrderClient, inventoryService)
  window.customerService = new CustomerService(customerClient)
  window.supplierService = new SupplierService(supplierClient)
  window.financeService = new FinanceService(salesService, purchaseService, customerService)
  window.posService = new PosService(inventoryService, salesService, productService)

  window.manufacturingService = new ManufacturingService(productService)
  window.qualityService = new QualityService()
  window.shopfloorService = new ShopfloorService()
  window.planningService = new PlanningService()
  window.adminService = new AdminService()
  window.warehouseService = new WarehouseService(inventoryService)
  window.maintenanceService = new MaintenanceService()
  window.projectService = new ProjectService()
  window.resourcePlanningService = new ResourcePlanningService()
  window.timesheetService = new TimesheetService()
  window.serviceManagementService = new ServiceManagementService()
  window.analyticsService = new AnalyticsService()
  window.dashboardService = new DashboardService()
  window.operationalAnalyticsService = new OperationalAnalyticsService()
  window.forecastService = new ForecastService()
  window.insightService = new InsightService()
  window.contractService = new ContractService()
  window.assetService = new AssetService()
  window.slaService = new SLAService()

  window.employeeService = new EmployeeService()
  window.attendanceService = new AttendanceService()
  window.leaveService = new LeaveService()
  window.payrollService = new PayrollService()
  window.recruitmentService = new RecruitmentService()

  window.tenantService = new TenantService()
  window.workflowEngineService = new WorkflowEngineService()
  window.documentService = new DocumentService()
  window.complianceService = new ComplianceService()
  window.platformService = new PlatformService()

  window.productClient = productClient
  window.customerClient = customerClient
  window.inventoryClient = inventoryClient

  window.leadService = new LeadService()
  window.opportunityService = new OpportunityService()
  window.quotationService = new QuotationService()
  window.purchaseRequisitionService = new PurchaseRequisitionService()
  window.rfqService = new RFQService()
  window.goodsReceiptService = new GoodsReceiptService()
  window.deliveryService = new DeliveryService()
  window.salesReturnService = new SalesReturnService()
  window.purchaseReturnService = new PurchaseReturnService()
  window.taxRateService = new TaxRateService()
  window.mobileApiService = new MobileApiService()
  window.mobilePOSService = new MobilePOSService()
  window.eCommerceService = new ECommerceService()
  window.paymentGatewayService = new PaymentGatewayService()
  window.shippingService = new ShippingService()
  window.apiGatewayService = new ApiGatewayService()
  window.serialNumberService = new SerialNumberService()
  window.batchNumberService = new BatchNumberService()
  window.chartOfAccountService = new ChartOfAccountService()
  window.journalEntryService = new JournalEntryService()
  window.invoiceService = new InvoiceService()
  window.paymentService = new PaymentService()
  window.paymentTermService = new PaymentTermService()
  window.paymentMethodService = new PaymentMethodService()
  window.priceListService = new PriceListService()
  window.notificationService = new NotificationService()
  window.scheduledTaskService = new ScheduledTaskService()
  window.auditLogService = new AuditLogService()
  window.moduleRegistryService = new ModuleRegistryService()

  window._dataReady = true
  window._dataReadyCallbacks.forEach(function(fn) { fn() })
  window._dataReadyCallbacks = []
})()

app.init = async function() {
  if (!Auth.isLoggedIn) { this.renderAuth('login'); return }
  if (this._started) return
  this._started = true
  if (!window._dataReady) {
    window._dataReadyCallbacks = window._dataReadyCallbacks || []
    await new Promise(function(resolve) { window._dataReadyCallbacks.push(resolve) })
  }
  document.querySelector('.app-shell').style.display = 'flex'
  document.getElementById('authOverlay').classList.remove('active')
  document.getElementById('userRole').textContent = CurrentUser.role
  await this.loadNavData()
  this.renderNav()
  await this.loadModule('home')
  if (this._onF2) document.removeEventListener('keydown', this._onF2)
  this._onF2 = function(e) {
    if (e.key === 'F2') { e.preventDefault(); app.loadModule('pos') }
  }
  document.addEventListener('keydown', this._onF2)
}

app.logout = function() {
  Auth.logout()
  this.renderAuth('login')
}

app._loaded = {}
app._moduleSvcs = {
  home: [],
  dashboard: ['analyticsService'],
  pos: [],
  products: [], inventory: [], warehouse: [],
  leads: ['leadService'], opportunities: ['opportunityService'],
  customers: [], suppliers: [], purchasing: [],
  purchase_requisitions: ['purchaseRequisitionService'],
  rfqs: ['rfqService'], goods_receipt: ['goodsReceiptService'],
  purchase_returns: ['purchaseReturnService'],
  delivery: ['deliveryService'], tax_rates: ['taxRateService'],
  sales_returns: ['salesReturnService'],
  sales: ['priceListService', 'taxRateService'],
  serial_numbers: ['serialNumberService'],
  batch_numbers: ['batchNumberService'],
  price_lists: ['priceListService'],
  quotations: ['quotationService'],
  invoices: ['invoiceService'], payments: ['paymentService'],
  chart_of_accounts: ['chartOfAccountService'],
  journal_entries: ['journalEntryService'],
  finance: [], settings: ['adminService'],
  admin: ['adminService'],
  module_manager: ['moduleRegistryService'],
  notifications: ['notificationService'],
  scheduled_tasks: ['scheduledTaskService'],
  audit_log: ['auditLogService'],
  manufacturing: ['manufacturingService'],
  planning: ['planningService'], shopfloor: ['shopfloorService'],
  quality: ['qualityService'],
  hr: ['employeeService'], attendance: ['attendanceService'],
  leave: ['leaveService'], payroll: ['payrollService'],
  recruitment: ['recruitmentService'],
  maintenance: ['maintenanceService', 'assetService'],
  project: ['projectService'], resource: ['resourcePlanningService'],
  timesheets: ['timesheetService'],
  service: ['serviceManagementService'],
  contracts: ['contractService', 'slaService'],
  bi: ['analyticsService'], executive: ['dashboardService'],
  operational: ['operationalAnalyticsService'],
  forecast: ['forecastService'], insights: ['insightService'],
  mobile: ['mobileApiService'], mobilepos: ['mobilePOSService'],
  ecommerce: ['eCommerceService'],
  integrations: ['paymentGatewayService', 'shippingService'],
  api: ['apiGatewayService'], tenant: ['tenantService'],
  workflow: ['workflowEngineService'],
  documents: ['documentService'], governance: ['complianceService'],
  platform: ['platformService'],
}

app._loadModuleData = async function(name) {
  var names = app._moduleSvcs[name] || []
  await Promise.all(names.map(function(n) {
    if (app._loaded[n]) return
    app._loaded[n] = true
    var svc = window[n]
    return svc && svc.load && svc.load()
  }))
  var mod = window.NovaModules && window.NovaModules[name]
  if (mod && mod.load && !app._loaded['_mod_' + name]) {
    app._loaded['_mod_' + name] = true
    await mod.load()
  }
}

app._renderModule = function(name, content) {
  const mod = window.NovaModules && window.NovaModules[name]
  if (!mod) return false
  content.innerHTML = mod.render ? mod.render() : '<div class="card"><h2>' + name + '</h2></div>'
  
  if (window.i18n) {
      window.i18n.translate(content)
  }

  if (mod.mount) mod.mount()
  return true
}

app._highlightNav = function(name) {
  document.querySelectorAll('#nav a').forEach(function(a) {
    if (a.dataset.id === name) {
      a.classList.add('active-tab', 'text-on-primary-container')
      a.classList.remove('text-on-surface-variant')
    } else {
      a.classList.remove('active-tab', 'text-on-primary-container')
      a.classList.add('text-on-surface-variant')
    }
  })
}

app._loadScript = async function(name, content) {
  const script = document.createElement('script')
  script.src = 'js/controllers/' + name + '.js?v=' + new Date().getTime()
  script.onload = function() {
    if (!app._renderModule(name, content)) {
      content.innerHTML = '<div class="card"><h2>' + name + '</h2><p style="color:var(--color-danger)">Module failed to load</p></div>'
    }
  }
  script.onerror = function() {
    content.innerHTML = '<div class="card"><h2>' + name + '</h2><p style="color:var(--color-danger)">Failed to load module</p></div>'
  }
  document.body.appendChild(script)
}

app.loadModule = async function(name) {
  this.current = name
  this._highlightNav(name)
  
  var navItem = (this.nav || []).find(function(i) { return i.id === name || i.module === name; })
  var titleEl = document.getElementById('page-title')
  if (titleEl) {
    const isAr = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl'
    titleEl.textContent = navItem ? ((isAr && navItem.label_ar) ? navItem.label_ar : navItem.label) : (name.charAt(0).toUpperCase() + name.slice(1))
  }

  const content = document.getElementById('content')

  await this._loadModuleData(name)

  if (this._renderModule(name, content)) return

  content.innerHTML = '<div class="card"><h2>' + name + '</h2><p>Loading...</p></div>'
  await this._loadScript(name, content)
}

;(async function() {
  const loggedIn = await Auth.restoreSession()
  if (loggedIn) { app.init() } else { app.renderAuth('login') }
})()

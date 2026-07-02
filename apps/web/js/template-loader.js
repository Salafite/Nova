window.NovaHtml = {}
window.pendingTemplates = 0

function escapeHtml(str) {
  if (typeof str !== 'string' && typeof str !== 'number') return ''
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

function renderHtml(path, data) {
  var html = window.NovaHtml[path]
  if (!html) return '<div class="error">Template not found: ' + path + '</div>'
  for (var key in data) {
    if (data.hasOwnProperty(key)) {
      html = html.split('{{' + key + '}}').join(data[key])
    }
  }
  return html
}

var templatePaths = [
  'models/product/list','models/product/form','models/product/detail',
  'models/customer/list','models/customer/form','models/customer/detail',
  'models/supplier/list','models/supplier/form',
  'models/inventoryentry/list','models/inventoryentry/form',
  'models/salesorder/list','models/salesorder/detail',
  'models/purchaseorder/list','models/purchaseorder/form','models/purchaseorder/detail',
  'models/user/form','models/manufacturingorder/form','models/inspection/form','models/job/form','models/plan/form',
  'screens/home','screens/settings','screens/dashboard','screens/pos','screens/admin','screens/finance',
  'screens/manufacturing','screens/planning','screens/quality','screens/shopfloor','screens/warehouse',
  'screens/customers','screens/suppliers','screens/inventory','screens/products','screens/sales','screens/purchasing',
  'screens/hrms_foundation','screens/attendance___time_tracking','screens/leave_management','screens/payroll_management','screens/recruitment___onboarding',
  'screens/nova_maintenance_management',
  'screens/project_management','screens/resource_planning','screens/timesheets','screens/service_management','screens/contracts___slas',
  'screens/business_intelligence_foundation','screens/executive_dashboards','screens/operational_analytics','screens/forecasting','screens/ai___insights',
  'screens/mobile_foundation','screens/mobile_pos','screens/e_commerce_integration','screens/third_party_integrations','screens/public_api_platform',
  'screens/multi_tenant_architecture','screens/workflow_automation','screens/document_management','screens/enterprise_governance','screens/enterprise_platform_completion',
  'screens/quotations','screens/quotations_form',
  'screens/purchase_requisitions','screens/purchase_requisitions_form',
  'screens/rfqs','screens/rfqs_form',
  'screens/goods_receipt','screens/goods_receipt_form',
  'screens/delivery','screens/delivery_form',
  'screens/sales_returns','screens/sales_returns_form',
  'screens/purchase_returns','screens/purchase_returns_form',
  'screens/price_lists','screens/price_lists_form',
  'screens/invoices','screens/invoices_form',
  'screens/payments','screens/payments_form',
  'screens/tax_rates','screens/tax_rates_form',
  'screens/serial_numbers','screens/serial_numbers_form',
  'screens/batch_numbers','screens/batch_numbers_form',
  'screens/chart_of_accounts','screens/chart_of_accounts_form',
  'screens/journal_entries','screens/journal_entries_form',
  'screens/payment_terms','screens/payment_terms_form',
  'screens/payment_methods','screens/payment_methods_form',
  'screens/leads','screens/leads_form',
  'screens/opportunities','screens/opportunities_form',
  'screens/notifications',
  'screens/scheduled_tasks','screens/scheduled_tasks_form',
  'screens/audit_log',
  'screens/module_manager'
]

window.pendingTemplates = templatePaths.length

templatePaths.forEach(function(path) {
  var xhr = new XMLHttpRequest()
  var url = 'templates/' + path + '.html?v=' + new Date().getTime()
  xhr.open('GET', url, true)
  xhr.onload = function() {
    window.NovaHtml[path] = xhr.responseText
    window.pendingTemplates--
    if (window.pendingTemplates === 0) {
      if (window.app && !window.app._started && typeof window.app.init === 'function') {
        window.app._started = true
        window.app.init()
      }
    }
  }
  xhr.onerror = function() {
    window.NovaHtml[path] = '<div class="error">Failed to load template: ' + path + '</div>'
    window.pendingTemplates--
    if (window.pendingTemplates === 0) {
      if (window.app && !window.app._started && typeof window.app.init === 'function') {
        window.app._started = true
        window.app.init()
      }
    }
  }
  xhr.send()
})

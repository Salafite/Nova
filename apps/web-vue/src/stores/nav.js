import { defineStore } from 'pinia'
import { api, CONFIG } from '../api/client.js'

export const useNavStore = defineStore('nav', {
  state: () => ({
    items: [],
    navStyle: 'sidebar',
  }),

  actions: {
    async load() {
      try {
        const res = await fetch(CONFIG.apiBase + '/NavigationData.json')
        const data = await res.json()
        this.items = data?.nav?.length ? data.nav : this.getFallback()
      } catch {
        this.items = this.getFallback()
      }
      await this.loadNavStyle()
    },

    getFallback() {
      return [
          { section: 'Foundation', section_ar: 'أساسيات' },
          { id: 'home', icon: 'home', label: 'Home', label_ar: 'الرئيسية', permission: 'DASHBOARD_VIEW', module: 'home' },
          { id: 'dashboard', icon: 'analytics', label: 'Dashboard', label_ar: 'لوحة البيانات', permission: 'DASHBOARD_VIEW', module: 'dashboard' },
          { id: 'pos', icon: 'point_of_sale', label: 'POS', label_ar: 'نقطة البيع', permission: 'POS_VIEW', module: 'pos' },
          { section: 'Inventory', section_ar: 'المخزون' },
          { id: 'products', icon: 'inventory_2', label: 'Products', label_ar: 'المنتجات', permission: 'PRODUCTS_VIEW', module: 'products' },
          { id: 'uom', icon: 'straighten', label: 'UOM', label_ar: 'وحدات القياس', permission: 'PRODUCTS_VIEW', module: 'uom' },
          { id: 'uom-conversions', icon: 'swap_horiz', label: 'UOM Conversions', label_ar: 'تحويلات الوحدات', permission: 'PRODUCTS_VIEW', module: 'uom-conversions' },
          { id: 'barcodes', icon: 'qr_code_scanner', label: 'Barcodes', label_ar: 'الباركود', permission: 'PRODUCTS_VIEW', module: 'barcodes' },
          { id: 'categories', icon: 'category', label: 'Categories', label_ar: 'التصنيفات', permission: 'PRODUCTS_VIEW', module: 'categories' },
          { id: 'attributes', icon: 'list_alt', label: 'Attributes', label_ar: 'الخصائص', permission: 'PRODUCTS_VIEW', module: 'attributes' },
          { id: 'product-types', icon: 'schema', label: 'Product Types', label_ar: 'أنواع المنتجات', permission: 'PRODUCTS_VIEW', module: 'product-types' },
          { id: 'batch-numbers', icon: 'inventory_2', label: 'Batch Numbers', label_ar: 'أرقام الدفعات', permission: 'INVENTORY_VIEW', module: 'batch-numbers' },
          { id: 'serial-numbers', icon: 'qr_code', label: 'Serial Numbers', label_ar: 'الأرقام التسلسلية', permission: 'INVENTORY_VIEW', module: 'serial-numbers' },
          { id: 'inventory', icon: 'warehouse', label: 'Stock Levels', label_ar: 'مستويات المخزون', permission: 'INVENTORY_VIEW', module: 'inventory' },
          { id: 'warehouses', icon: 'factory', label: 'Warehouses', label_ar: 'المستودعات', permission: 'WAREHOUSE_VIEW', module: 'warehouses' },
          { id: 'stock-movements', icon: 'swap_vert', label: 'Stock Movements', label_ar: 'حركات المخزون', permission: 'INVENTORY_VIEW', module: 'stock-movements' },
          { id: 'stock-adjustments', icon: 'swipe_up_alt', label: 'Stock Adjustments', label_ar: 'تسوية المخزون', permission: 'INVENTORY_VIEW', module: 'stock-adjustments' },
          { id: 'inventory-counts', icon: 'fact_check', label: 'Inventory Counts', label_ar: 'جرد المخزون', permission: 'INVENTORY_VIEW', module: 'inventory-counts' },
          { id: 'pick-lists', icon: 'assignment', label: 'Pick Lists', label_ar: 'قوائم التجهيز', permission: 'WAREHOUSE_VIEW', module: 'pick-lists' },
          { section: 'Accounting & Finance', section_ar: 'المحاسبة والمالية' },
          { id: 'finance', icon: 'account_balance', label: 'Invoices', label_ar: 'الفواتير', permission: 'FINANCE_VIEW', module: 'finance' },
          { id: 'chart-of-accounts', icon: 'account_tree', label: 'Chart of Accounts', label_ar: 'دليل الحسابات', permission: 'FINANCE_VIEW', module: 'chart-of-accounts' },
          { id: 'journal-entries', icon: 'menu_book', label: 'Journal Entries', label_ar: 'قيود اليومية', permission: 'FINANCE_VIEW', module: 'journal-entries' },
          { id: 'payments', icon: 'payments', label: 'Payments', label_ar: 'المدفوعات', permission: 'FINANCE_VIEW', module: 'payments' },
          { id: 'payment-terms', icon: 'payments', label: 'Payment Terms', label_ar: 'شروط الدفع', permission: 'FINANCE_VIEW', module: 'payment-terms' },
          { id: 'payment-methods', icon: 'credit_card', label: 'Payment Methods', label_ar: 'طرق الدفع', permission: 'FINANCE_VIEW', module: 'payment-methods' },
          { section: 'CRM & Sales', section_ar: 'CRM والمبيعات' },
          { id: 'leads', icon: 'person_search', label: 'Leads', label_ar: 'العملاء المتوقعون', permission: 'CRM_VIEW', module: 'leads' },
          { id: 'opportunities', icon: 'trending_up', label: 'Opportunities', label_ar: 'الفرص', permission: 'CRM_VIEW', module: 'opportunities' },
          { id: 'customers', icon: 'group', label: 'Customers', label_ar: 'العملاء', permission: 'CRM_VIEW', module: 'customers' },
          { id: 'sales', icon: 'payments', label: 'Sales Orders', label_ar: 'أوامر البيع', permission: 'SALES_VIEW', module: 'sales' },
          { id: 'sales-quotations', icon: 'request_quote', label: 'Quotations', label_ar: 'عروض الأسعار', permission: 'SALES_VIEW', module: 'sales-quotations' },
          { id: 'sales-deliveries', icon: 'local_shipping', label: 'Deliveries', label_ar: 'التسليمات', permission: 'SALES_VIEW', module: 'sales-deliveries' },
          { id: 'sales-returns', icon: 'assignment_return', label: 'Returns', label_ar: 'المرتجعات', permission: 'SALES_VIEW', module: 'sales-returns' },
          { id: 'sales-price-lists', icon: 'price_change', label: 'Price Lists', label_ar: 'قوائم الأسعار', permission: 'SALES_VIEW', module: 'sales-price-lists' },
          { id: 'sales-tax-rates', icon: 'percent', label: 'Tax Rates', label_ar: 'معدلات الضرائب', permission: 'SALES_VIEW', module: 'sales-tax-rates' },
          { section: 'Procurement', section_ar: 'المشتريات' },
          { id: 'suppliers', icon: 'local_shipping', label: 'Suppliers', label_ar: 'الموردون', permission: 'PURCHASING_VIEW', module: 'suppliers' },
          { id: 'purchasing', icon: 'receipt_long', label: 'Purchase Orders', label_ar: 'أوامر الشراء', permission: 'PURCHASING_VIEW', module: 'purchasing' },
          { id: 'purchasing-requisitions', icon: 'description', label: 'Requisitions', label_ar: 'طلبات الشراء', permission: 'PURCHASING_VIEW', module: 'purchasing-requisitions' },
          { id: 'purchasing-rfqs', icon: 'rate_review', label: 'RFQs', label_ar: 'طلبات العروض', permission: 'PURCHASING_VIEW', module: 'purchasing-rfqs' },
          { id: 'goods-receipt', icon: 'inventory_2', label: 'Goods Receipt', label_ar: 'استلام البضائع', permission: 'WAREHOUSE_VIEW', module: 'goods-receipt' },
          { id: 'purchasing-returns', icon: 'assignment_returned', label: 'Purchase Returns', label_ar: 'مرتجعات المشتريات', permission: 'PURCHASING_VIEW', module: 'purchasing-returns' },
          { section: 'Administration', section_ar: 'إدارة' },
          { id: 'admin', icon: 'admin_panel_settings', label: 'Users & Roles', label_ar: 'المستخدمون والصلاحيات', permission: 'ADMIN_VIEW', module: 'admin' },
          { id: 'modules', icon: 'extension', label: 'Modules', label_ar: 'الوحدات', permission: 'ADMIN_VIEW', module: 'modules' },
          { id: 'settings', icon: 'settings', label: 'Settings', label_ar: 'الإعدادات', permission: 'ADMIN_VIEW', module: 'settings' },
          { id: 'notifications', icon: 'notifications', label: 'Notifications', label_ar: 'الإشعارات', permission: 'ADMIN_VIEW', module: 'notifications' },
          { id: 'audit-log', icon: 'history', label: 'Audit Log', label_ar: 'سجل التدقيق', permission: 'ADMIN_VIEW', module: 'audit-log' },
          { id: 'scheduled-tasks', icon: 'schedule', label: 'Scheduled Tasks', label_ar: 'المهام المجدولة', permission: 'ADMIN_VIEW', module: 'scheduled-tasks' },
          { id: 'workflow', icon: 'alt_route', label: 'Workflow Automation', label_ar: 'أتمتة سير العمل', permission: 'ADMIN_VIEW', module: 'workflow' },
          { id: 'migration', icon: 'file_upload', label: 'Data Migration', label_ar: 'ترحيل البيانات', permission: 'ADMIN_VIEW', module: 'migration' },
          { id: 'subscription', icon: 'credit_card', label: 'Subscription', label_ar: 'الاشتراك', permission: 'ADMIN_VIEW', module: 'subscription' },
          { section: 'HR & Organization', section_ar: 'الموارد البشرية والتنظيم' },
          { id: 'departments', icon: 'business', label: 'Departments', label_ar: 'الأقسام', permission: 'HR_VIEW', module: 'departments' },
          { id: 'designations', icon: 'badge', label: 'Designations', label_ar: 'المسميات الوظيفية', permission: 'HR_VIEW', module: 'designations' },
          { id: 'employees', icon: 'people', label: 'Employees', label_ar: 'الموظفون', permission: 'HR_VIEW', module: 'employees' },
          { id: 'hr-attendance', icon: 'calendar_clock', label: 'Attendance', label_ar: 'الحضور والانصراف', permission: 'HR_VIEW', module: 'hr-attendance' },
          { id: 'hr-leaves', icon: 'event', label: 'Leave Requests', label_ar: 'طلبات الإجازات', permission: 'HR_VIEW', module: 'hr-leaves' },
          { id: 'hr-payroll', icon: 'payments', label: 'Payroll', label_ar: 'الرواتب', permission: 'HR_VIEW', module: 'hr-payroll' },
          { id: 'hr-timesheets', icon: 'timer', label: 'Timesheets', label_ar: 'ساعات العمل', permission: 'HR_VIEW', module: 'hr-timesheets' },
          { id: 'hr-jobs', icon: 'work', label: 'Job Openings', label_ar: 'الوظائف الشاغرة', permission: 'HR_VIEW', module: 'hr-jobs' },
          { id: 'hr-candidates', icon: 'person_search', label: 'Candidates', label_ar: 'المرشحون', permission: 'HR_VIEW', module: 'hr-candidates' },
          { section: 'Projects & Services', section_ar: 'المشاريع والخدمات' },
          { id: 'projects', icon: 'assignment', label: 'Projects', label_ar: 'المشاريع', permission: 'PROJECTS_VIEW', module: 'projects' },
          { id: 'project-tasks', icon: 'checklist', label: 'Tasks', label_ar: 'المهام', permission: 'PROJECTS_VIEW', module: 'project-tasks' },
          { id: 'project-milestones', icon: 'flag', label: 'Milestones', label_ar: 'المعالم', permission: 'PROJECTS_VIEW', module: 'project-milestones' },
          { id: 'contracts', icon: 'description', label: 'Contracts & SLAs', label_ar: 'العقود', permission: 'PROJECTS_VIEW', module: 'contracts' },
          { id: 'documents', icon: 'folder', label: 'Documents', label_ar: 'المستندات', permission: 'PROJECTS_VIEW', module: 'documents' },
          { section: 'Maintenance', section_ar: 'الصيانة' },
          { id: 'maintenance-assets', icon: 'build', label: 'Assets', label_ar: 'الأصول', permission: 'MAINTENANCE_VIEW', module: 'maintenance-assets' },
          { id: 'maintenance-schedules', icon: 'calendar_month', label: 'Schedules', label_ar: 'جداول الصيانة', permission: 'MAINTENANCE_VIEW', module: 'maintenance-schedules' },
          { id: 'maintenance-work-orders', icon: 'assignment', label: 'Work Orders', label_ar: 'أوامر العمل', permission: 'MAINTENANCE_VIEW', module: 'maintenance-work-orders' },
          { section: 'BI & Reporting', section_ar: 'ذكاء الأعمال والتقارير' },
          { id: 'bi-kpis', icon: 'monitoring', label: 'KPI Management', label_ar: 'إدارة مؤشرات الأداء', permission: 'BI_VIEW', module: 'bi-kpis' },
          { id: 'bi-dashboards', icon: 'dashboard_customize', label: 'Dashboard Builder', label_ar: 'منشئ لوحات البيانات', permission: 'BI_VIEW', module: 'bi-dashboards' },
          { id: 'bi-reports', icon: 'description', label: 'Reports', label_ar: 'التقارير', permission: 'BI_VIEW', module: 'bi-reports' },
          { id: 'bi-forecasting', icon: 'trending_up', label: 'Forecasting', label_ar: 'التوقعات', permission: 'BI_VIEW', module: 'bi-forecasting' },
          { section: 'Manufacturing', section_ar: 'التصنيع' },
          { id: 'mfg-bom', icon: 'account_tree', label: 'Bill of Materials', label_ar: 'قائمة المكونات', permission: 'MFG_VIEW', module: 'mfg-bom' },
          { id: 'mfg-orders', icon: 'precision_manufacturing', label: 'Manufacturing Orders', label_ar: 'أوامر التصنيع', permission: 'MFG_VIEW', module: 'mfg-orders' },
          { id: 'mfg-qc', icon: 'fact_check', label: 'QC Inspections', label_ar: 'فحص الجودة', permission: 'MFG_VIEW', module: 'mfg-qc' },
          { id: 'mfg-shopfloor', icon: 'construction', label: 'Shop Floor', label_ar: 'أرضية المصنع', permission: 'MFG_VIEW', module: 'mfg-shopfloor' },
          { section: 'Planning', section_ar: 'التخطيط' },
          { id: 'production-plans', icon: 'calendar_month', label: 'Production Plans', label_ar: 'خطط الإنتاج', permission: 'PLANNING_VIEW', module: 'production-plans' },
          { id: 'resource-planning', icon: 'groups', label: 'Resource Planning', label_ar: 'تخطيط الموارد', permission: 'PLANNING_VIEW', module: 'resource-planning' },
          { section: 'Integrations', section_ar: 'التكاملات' },
          { id: 'integrations', icon: 'extension', label: 'Integrations', label_ar: 'التكاملات', permission: 'INTEGRATIONS_VIEW', module: 'integrations' },
          { id: 'integrations-ecommerce', icon: 'shopping_cart', label: 'E-Commerce', label_ar: 'التجارة الإلكترونية', permission: 'INTEGRATIONS_VIEW', module: 'integrations-ecommerce' },
          { id: 'integrations-api', icon: 'api', label: 'API Platform', label_ar: 'منصة API', permission: 'INTEGRATIONS_VIEW', module: 'integrations-api' },
          { section: 'Enterprise', section_ar: 'المؤسسة' },
          { id: 'enterprise-tenants', icon: 'business', label: 'Multi-Tenant', label_ar: 'المستأجرون', permission: 'ADMIN_VIEW', module: 'enterprise-tenants' },
          { id: 'enterprise-governance', icon: 'gavel', label: 'Governance', label_ar: 'الحوكمة', permission: 'ADMIN_VIEW', module: 'enterprise-governance' },
          { id: 'enterprise-platform', icon: 'cloud', label: 'Platform', label_ar: 'المنصة', permission: 'ADMIN_VIEW', module: 'enterprise-platform' },
        ]
    },

    async loadNavStyle() {
      try {
        const res = await api.get('/T0025I/', { params: { group: 'App Preferences' } })
        const settings = res.data || []
        const navStyleSetting = settings.find(s => s.setting_key === 'NAV_STYLE')
        if (navStyleSetting) {
          this.navStyle = navStyleSetting.setting_value || 'sidebar'
        }
      } catch {
        // use default
      }
    },

    setNavStyle(value) {
      this.navStyle = value
    },
  },
})

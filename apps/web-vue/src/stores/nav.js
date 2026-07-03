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
          { id: 'home', icon: 'home', label: 'Home', label_ar: 'الرئيسية', module: 'home' },
          { id: 'dashboard', icon: 'analytics', label: 'Dashboard', label_ar: 'لوحة البيانات', module: 'dashboard' },
          { id: 'uom', icon: 'straighten', label: 'UOM', label_ar: 'وحدات القياس', module: 'uom' },
          { id: 'uom-conversions', icon: 'swap_horiz', label: 'UOM Conversions', label_ar: 'تحويلات الوحدات', module: 'uom-conversions' },
          { id: 'products', icon: 'inventory_2', label: 'Products', label_ar: 'المنتجات', module: 'products' },
          { id: 'barcodes', icon: 'qr_code_scanner', label: 'Barcodes', label_ar: 'الباركود', module: 'barcodes' },
          { id: 'categories', icon: 'category', label: 'Categories', label_ar: 'التصنيفات', module: 'categories' },
          { id: 'attributes', icon: 'list_alt', label: 'Attributes', label_ar: 'الخصائص', module: 'attributes' },
          { id: 'inventory', icon: 'warehouse', label: 'Stock Levels', label_ar: 'مستويات المخزون', module: 'inventory' },
          { id: 'warehouses', icon: 'factory', label: 'Warehouses', label_ar: 'المستودعات', module: 'warehouses' },
          { id: 'stock-movements', icon: 'swap_vert', label: 'Stock Movements', label_ar: 'حركات المخزون', module: 'stock-movements' },
          { id: 'inventory-counts', icon: 'fact_check', label: 'Inventory Counts', label_ar: 'جرد المخزون', module: 'inventory-counts' },
          { id: 'pick-lists', icon: 'assignment', label: 'Pick Lists', label_ar: 'قوائم التجهيز', module: 'pick-lists' },
          { section: 'Accounting & Finance', section_ar: 'المحاسبة والمالية' },
          { id: 'finance', icon: 'account_balance', label: 'Invoices', label_ar: 'الفواتير', module: 'finance' },
          { id: 'chart-of-accounts', icon: 'account_tree', label: 'Chart of Accounts', label_ar: 'دليل الحسابات', module: 'chart-of-accounts' },
          { id: 'journal-entries', icon: 'menu_book', label: 'Journal Entries', label_ar: 'قيود اليومية', module: 'journal-entries' },
          { id: 'payments', icon: 'payments', label: 'Payments', label_ar: 'المدفوعات', module: 'payments' },
          { id: 'payment-terms', icon: 'payments', label: 'Payment Terms', label_ar: 'شروط الدفع', module: 'payment-terms' },
          { id: 'payment-methods', icon: 'credit_card', label: 'Payment Methods', label_ar: 'طرق الدفع', module: 'payment-methods' },
          { section: 'CRM & Procurement', section_ar: 'CRM والمشتريات' },
          { id: 'customers', icon: 'group', label: 'Customers', label_ar: 'العملاء', module: 'customers' },
          { id: 'suppliers', icon: 'local_shipping', label: 'Suppliers', label_ar: 'الموردون', module: 'suppliers' },
          { id: 'purchasing', icon: 'receipt_long', label: 'Purchasing', label_ar: 'المشتريات', module: 'purchasing' },
          { id: 'sales', icon: 'payments', label: 'Sales Orders', label_ar: 'أوامر البيع', module: 'sales' },
          { id: 'sales-quotations', icon: 'request_quote', label: 'Quotations', label_ar: 'عروض الأسعار', module: 'sales-quotations' },
          { id: 'sales-deliveries', icon: 'local_shipping', label: 'Deliveries', label_ar: 'التسليمات', module: 'sales-deliveries' },
          { id: 'sales-returns', icon: 'assignment_return', label: 'Returns', label_ar: 'المرتجعات', module: 'sales-returns' },
          { id: 'sales-price-lists', icon: 'price_change', label: 'Price Lists', label_ar: 'قوائم الأسعار', module: 'sales-price-lists' },
          { id: 'sales-tax-rates', icon: 'percent', label: 'Tax Rates', label_ar: 'معدلات الضرائب', module: 'sales-tax-rates' },
          { section: 'Administration', section_ar: 'إدارة' },
          { id: 'admin', icon: 'admin_panel_settings', label: 'Users & Roles', label_ar: 'المستخدمون والصلاحيات', module: 'admin' },
          { id: 'migration', icon: 'file_upload', label: 'Data Migration', label_ar: 'ترحيل البيانات', module: 'migration' },
          { id: 'modules', icon: 'extension', label: 'Modules', label_ar: 'الوحدات', module: 'modules' },
          { id: 'notifications', icon: 'notifications', label: 'Notifications', label_ar: 'الإشعارات', module: 'notifications' },
          { id: 'settings', icon: 'settings', label: 'Settings', label_ar: 'الإعدادات', module: 'settings' },
          { id: 'subscription', icon: 'credit_card', label: 'Subscription', label_ar: 'الاشتراك', module: 'subscription' },
          { section: 'HR & Organization', section_ar: 'الموارد البشرية والتنظيم' },
          { id: 'departments', icon: 'business', label: 'Departments', label_ar: 'الأقسام', module: 'departments' },
          { id: 'designations', icon: 'badge', label: 'Designations', label_ar: 'المسميات الوظيفية', module: 'designations' },
          { id: 'employees', icon: 'people', label: 'Employees', label_ar: 'الموظفون', module: 'employees' },
          { id: 'hr-leaves', icon: 'event', label: 'Leave Requests', label_ar: 'طلبات الإجازات', module: 'hr-leaves' },
          { id: 'hr-attendance', icon: 'calendar_clock', label: 'Attendance', label_ar: 'الحضور والانصراف', module: 'hr-attendance' },
          { id: 'hr-payroll', icon: 'payments', label: 'Payroll', label_ar: 'الرواتب', module: 'hr-payroll' },
          { id: 'hr-jobs', icon: 'work', label: 'Job Openings', label_ar: 'الوظائف الشاغرة', module: 'hr-jobs' },
          { id: 'hr-candidates', icon: 'person_search', label: 'Candidates', label_ar: 'المرشحون', module: 'hr-candidates' },
          { section: 'BI & Reporting', section_ar: 'ذكاء الأعمال والتقارير' },
          { id: 'bi-kpis', icon: 'monitoring', label: 'KPI Management', label_ar: 'إدارة مؤشرات الأداء', module: 'bi-kpis' },
          { id: 'bi-dashboards', icon: 'dashboard_customize', label: 'Dashboard Builder', label_ar: 'منشئ لوحات البيانات', module: 'bi-dashboards' },
          { id: 'bi-reports', icon: 'description', label: 'Report Builder', label_ar: 'منشئ التقارير', module: 'bi-reports' },
          { section: 'Manufacturing', section_ar: 'التصنيع' },
          { id: 'mfg-bom', icon: 'account_tree', label: 'Bill of Materials', label_ar: 'قائمة المكونات', module: 'mfg-bom' },
          { id: 'mfg-orders', icon: 'precision_manufacturing', label: 'Manufacturing Orders', label_ar: 'أوامر التصنيع', module: 'mfg-orders' },
          { id: 'mfg-qc', icon: 'fact_check', label: 'QC Inspections', label_ar: 'فحص الجودة', module: 'mfg-qc' },
          { section: 'Planning', section_ar: 'التخطيط' },
          { id: 'production-plans', icon: 'calendar_month', label: 'Production Plans', label_ar: 'خطط الإنتاج', module: 'production-plans' },
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

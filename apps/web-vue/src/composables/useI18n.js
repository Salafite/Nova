import { computed, watch } from 'vue'
import { useSettingsStore } from '../stores/settings.js'

const LS_KEY = 'nova_locale'

function loadLocale() {
  return localStorage.getItem(LS_KEY) || 'en-US'
}

function saveLocale(v) {
  localStorage.setItem(LS_KEY, v)
}

const dict = {
  // Global
  loading: { en: 'Loading...', ar: 'جاري التحميل...' },
  'no-records': { en: 'No records found', ar: 'لا توجد سجلات' },
  'no-data': { en: 'No data available', ar: 'لا توجد بيانات' },
  'no-modules': { en: 'No modules installed', ar: 'لا توجد وحدات مثبتة' },
  'scan-hint': { en: 'Click "Scan for Modules" to discover available modules', ar: 'انقر "البحث عن الوحدات" لاكتشاف الوحدات المتاحة' },
  edit: { en: 'Edit', ar: 'تعديل' },
  delete: { en: 'Delete', ar: 'حذف' },
  cancel: { en: 'Cancel', ar: 'إلغاء' },
  save: { en: 'Save', ar: 'حفظ' },
  saving: { en: 'Saving...', ar: 'جاري الحفظ...' },
  'add-new': { en: 'Add New', ar: 'إضافة جديد' },
  'confirm-delete': { en: 'Confirm Delete', ar: 'تأكيد الحذف' },
  retry: { en: 'Retry', ar: 'إعادة المحاولة' },
  actions: { en: 'Actions', ar: 'إجراءات' },
  status: { en: 'Status', ar: 'الحالة' },
  active: { en: 'Active', ar: 'نشط' },
  inactive: { en: 'Inactive', ar: 'غير نشط' },
  disabled: { en: 'Disabled', ar: 'معطل' },
  search: { en: 'Search', ar: 'بحث' },
  close: { en: 'Close', ar: 'إغلاق' },
  new: { en: 'New', ar: 'جديد' },
  total: { en: 'Total', ar: 'الإجمالي' },
  name: { en: 'Name', ar: 'الاسم' },
  category: { en: 'Category', ar: 'التصنيف' },
  price: { en: 'Price', ar: 'السعر' },
  sku: { en: 'SKU', ar: 'رمز SKU' },
  code: { en: 'Code', ar: 'الكود' },
  version: { en: 'Version', ar: 'الإصدار' },
  description: { en: 'Description', ar: 'الوصف' },
  module: { en: 'Module', ar: 'الوحدة' },
  install: { en: 'Install', ar: 'تثبيت' },
  installed: { en: 'Installed', ar: 'مثبت' },
  uninstall: { en: 'Uninstall', ar: 'إلغاء التثبيت' },
  enable: { en: 'Enable', ar: 'تمكين' },
  disable: { en: 'Disable', ar: 'تعطيل' },
  yes: { en: 'Yes', ar: 'نعم' },
  no: { en: 'No', ar: 'لا' },
  'base-unit': { en: 'Base Unit', ar: 'وحدة أساسية' },
  // Home
  welcome: { en: 'Welcome,', ar: 'مرحباً،' },
  'select-app': { en: 'Select an application to start your workflow.', ar: 'اختر تطبيقاً لبدء سير عملك.' },
  // Errors
  'failed-load': { en: 'Failed to load data.', ar: 'فشل تحميل البيانات.' },
  'failed-save': { en: 'Failed to save', ar: 'فشل الحفظ' },
  'saved-ok': { en: 'saved', ar: 'تم الحفظ' },
  // Settings
  settings: { en: 'Settings', ar: 'الإعدادات' },
  'search-settings': { en: 'Search settings...', ar: 'بحث في الإعدادات...' },
  'unsaved-changes': { en: 'unsaved change', ar: 'تغيير غير محفوظ' },
  'unsaved': { en: 'Unsaved', ar: 'غير محفوظ' },
  'save-all': { en: 'Save All Changes', ar: 'حفظ الكل' },
  'save-group': { en: 'Save Group', ar: 'حفظ المجموعة' },
  'reset-value': { en: 'Reset to saved value', ar: 'إعادة إلى القيمة المحفوظة' },
  // Module Manager
  'module-manager': { en: 'Module Manager', ar: 'مدير الوحدات' },
  'module-sub': { en: 'Install, enable, or disable Nova ERP modules', ar: 'تثبيت أو تمكين أو تعطيل وحدات Nova' },
  'scan-modules': { en: 'Scan for Modules', ar: 'البحث عن الوحدات' },
  'available': { en: 'Available', ar: 'متاح' },
  'installed-modules': { en: 'Installed Modules', ar: 'الوحدات المثبتة' },
  'available-modules': { en: 'Available Modules', ar: 'الوحدات المتاحة' },
  'controllers': { en: 'Controllers', ar: 'وحدات التحكم' },
  'module-installed': { en: 'Module installed', ar: 'تم تثبيت الوحدة' },
  'module-uninstalled': { en: 'Module uninstalled', ar: 'تم إلغاء تثبيت الوحدة' },
  'module-enabled': { en: 'Module enabled', ar: 'تم تمكين الوحدة' },
  'module-disabled': { en: 'Module disabled', ar: 'تم تعطيل الوحدة' },
  'install-failed': { en: 'Install failed', ar: 'فشل التثبيت' },
  'uninstall-failed': { en: 'Uninstall failed', ar: 'فشل إلغاء التثبيت' },
  'toggle-failed': { en: 'Toggle failed', ar: 'فشل التبديل' },
  // UOM
  'uom-title': { en: 'Units of Measure', ar: 'وحدات القياس' },
  'uom-sub': { en: 'Manage UOM codes, names, categories, and base unit flags', ar: 'إدارة أكواد وأسماء وتصنيفات ووحدات القياس الأساسية' },
  'new-uom': { en: 'New UOM', ar: 'وحدة قياس جديدة' },
  'edit-uom': { en: 'Edit UOM', ar: 'تعديل وحدة القياس' },
  // UOM Conversions
  'uom-conv-title': { en: 'UOM Conversions', ar: 'تحويلات وحدات القياس' },
  'uom-conv-sub': { en: 'Manage conversion factors between units of measure', ar: 'إدارة عوامل التحويل بين وحدات القياس' },
  'new-uom-conv': { en: 'New Conversion', ar: 'تحويل جديد' },
  'edit-uom-conv': { en: 'Edit Conversion', ar: 'تعديل التحويل' },
  'conv-factor': { en: 'Factor', ar: 'عامل التحويل' },
  // Barcodes
  'barcodes-title': { en: 'Barcodes', ar: 'الباركود' },
  'barcodes-sub': { en: 'Manage product barcodes and scanning identifiers', ar: 'إدارة الباركود ومعرفات المسح للمنتجات' },
  'new-barcode': { en: 'New Barcode', ar: 'باركود جديد' },
  'edit-barcode': { en: 'Edit Barcode', ar: 'تعديل الباركود' },
  'barcode-type': { en: 'Type', ar: 'النوع' },
  'barcode-primary': { en: 'Primary', ar: 'أساسي' },
  // Attributes
  'attr-title': { en: 'Attributes', ar: 'الخصائص' },
  'attr-sub': { en: 'Define product attributes like size, color, material, etc.', ar: 'تعريف خصائص المنتج مثل الحجم واللون والخامة' },
  'new-attr': { en: 'New Attribute', ar: 'خاصية جديدة' },
  'edit-attr': { en: 'Edit Attribute', ar: 'تعديل الخاصية' },
  'attr-type': { en: 'Type', ar: 'النوع' },
  'attr-required': { en: 'Required', ar: 'إجباري' },
  'attr-sort': { en: 'Sort', ar: 'الترتيب' },
  // Stock Movements
  'stock-move-title': { en: 'Stock Movements', ar: 'حركات المخزون' },
  'stock-move-sub': { en: 'View stock movement history across warehouses', ar: 'عرض تاريخ حركات المخزون في المستودعات' },
  'new-movement': { en: 'New Movement', ar: 'حركة جديدة' },
  'edit-movement': { en: 'Edit Movement', ar: 'تعديل الحركة' },
  'stock-move-type': { en: 'Movement Type', ar: 'نوع الحركة' },
  'stock-qty-change': { en: 'Qty Change', ar: 'تغير الكمية' },
  'stock-balance': { en: 'Balance', ar: 'الرصيد' },
  'stock-move-ref': { en: 'Reference', ar: 'المرجع' },
  'stock-move-ref-id': { en: 'Reference ID', ar: 'رقم المرجع' },
  'date': { en: 'Date', ar: 'التاريخ' },
  // Warehouses
  'warehouse-title': { en: 'Warehouses', ar: 'المستودعات' },
  'warehouse-sub': { en: 'Manage warehouse locations and storage facilities', ar: 'إدارة مواقع المستودعات ومرافق التخزين' },
  'new-warehouse': { en: 'New Warehouse', ar: 'مستودع جديد' },
  'edit-warehouse': { en: 'Edit Warehouse', ar: 'تعديل المستودع' },
  'warehouse-location': { en: 'Location', ar: 'الموقع' },
  // Inventory
  'inventory-title': { en: 'Inventory', ar: 'المخزون' },
  'inventory-sub': { en: 'View stock levels by product and warehouse', ar: 'عرض مستويات المخزون حسب المنتج والمستودع' },
  'inventory-warehouse': { en: 'Warehouse', ar: 'المستودع' },
  'inventory-qty': { en: 'Qty', ar: 'الكمية' },
  'inventory-reorder': { en: 'Reorder Level', ar: 'حد إعادة الطلب' },
  // Customers
  'customers-title': { en: 'Customers', ar: 'العملاء' },
  'customers-sub': { en: 'Manage customer accounts, credit limits, and balances', ar: 'إدارة حسابات العملاء والحدود الائتمانية والأرصدة' },
  'new-customer': { en: 'New Customer', ar: 'عميل جديد' },
  'edit-customer': { en: 'Edit Customer', ar: 'تعديل العميل' },
  'customer-group': { en: 'Group', ar: 'المجموعة' },
  'customer-phone': { en: 'Phone', ar: 'الهاتف' },
  'customer-email': { en: 'Email', ar: 'البريد الإلكتروني' },
  'customer-credit': { en: 'Credit Limit', ar: 'الحد الائتماني' },
  'customer-balance': { en: 'Balance', ar: 'الرصيد' },
  // Suppliers
  'suppliers-title': { en: 'Suppliers', ar: 'الموردون' },
  'suppliers-sub': { en: 'Manage supplier information and ratings', ar: 'إدارة بيانات الموردين والتقييمات' },
  'new-supplier': { en: 'New Supplier', ar: 'مورد جديد' },
  'edit-supplier': { en: 'Edit Supplier', ar: 'تعديل المورد' },
  'supplier-phone': { en: 'Phone', ar: 'الهاتف' },
  'supplier-email': { en: 'Email', ar: 'البريد الإلكتروني' },
  'supplier-payment-terms': { en: 'Payment Terms', ar: 'شروط الدفع' },
  'supplier-rating': { en: 'Rating', ar: 'التقييم' },
  // Products
  'products-title': { en: 'Products', ar: 'المنتجات' },
  'products-sub': { en: 'Manage your product catalog', ar: 'إدارة كتالوج المنتجات' },
  'new-product': { en: 'New Product', ar: 'منتج جديد' },
  'edit-product': { en: 'Edit Product', ar: 'تعديل المنتج' },
  'product-category': { en: 'Category', ar: 'التصنيف' },
  'product-saved': { en: 'Product saved successfully', ar: 'تم حفظ المنتج بنجاح' },
  'product-deleted': { en: 'Product deleted', ar: 'تم حذف المنتج' },
  'product-delete-confirm': { en: 'Delete this product?', ar: 'حذف هذا المنتج؟' },
  // Sales Orders
  'sales-title': { en: 'Sales Orders', ar: 'أوامر البيع' },
  'sales-sub': { en: 'Manage sales orders, customers, and order status', ar: 'إدارة أوامر البيع والعملاء وحالة الطلبات' },
  'new-sales-order': { en: 'New Sales Order', ar: 'أمر بيع جديد' },
  'edit-sales-order': { en: 'Edit Sales Order', ar: 'تعديل أمر البيع' },
  'sales-order-number': { en: 'Order #', ar: 'رقم الطلب' },
  'sales-customer': { en: 'Customer', ar: 'العميل' },
  'sales-subtotal': { en: 'Subtotal', ar: 'المجموع الفرعي' },
  'sales-tax': { en: 'Tax', ar: 'الضريبة' },
  'sales-grand-total': { en: 'Grand Total', ar: 'الإجمالي الكلي' },
  'sales-order-date': { en: 'Order Date', ar: 'تاريخ الطلب' },
  'sales-notes': { en: 'Notes', ar: 'ملاحظات' },
  // Purchase Orders
  'purchasing-title': { en: 'Purchase Orders', ar: 'أوامر الشراء' },
  'purchasing-sub': { en: 'Manage purchase orders, suppliers, and procurement', ar: 'إدارة أوامر الشراء والموردين والمشتريات' },
  'new-purchase-order': { en: 'New Purchase Order', ar: 'أمر شراء جديد' },
  'edit-purchase-order': { en: 'Edit Purchase Order', ar: 'تعديل أمر الشراء' },
  'purchase-order-number': { en: 'PO #', ar: 'رقم الأمر' },
  'purchase-supplier': { en: 'Supplier', ar: 'المورد' },
  'purchase-total': { en: 'Total', ar: 'الإجمالي' },
  'purchase-order-date': { en: 'Order Date', ar: 'تاريخ الطلب' },
  'purchase-expected-date': { en: 'Expected Date', ar: 'تاريخ التسليم المتوقع' },
  'purchase-notes': { en: 'Notes', ar: 'ملاحظات' },
  // Admin / Users
  'admin-title': { en: 'System Users', ar: 'مستخدمو النظام' },
  'admin-sub': { en: 'Manage user accounts, roles, and access permissions', ar: 'إدارة حسابات المستخدمين والأدوار وصلاحيات الوصول' },
  'admin-username': { en: 'Username', ar: 'اسم المستخدم' },
  'admin-full-name': { en: 'Full Name', ar: 'الاسم الكامل' },
  'admin-email': { en: 'Email', ar: 'البريد الإلكتروني' },
  'admin-role': { en: 'Role', ar: 'الدور' },
  'admin-password': { en: 'Password', ar: 'كلمة المرور' },
  'admin-last-login': { en: 'Last Login', ar: 'آخر تسجيل دخول' },
  'admin-delete-confirm': { en: 'Delete user', ar: 'حذف المستخدم' },
  'new-user': { en: 'New User', ar: 'مستخدم جديد' },
  'edit-user': { en: 'Edit User', ar: 'تعديل المستخدم' },
  deleting: { en: 'Deleting...', ar: 'جاري الحذف...' },
  // Chart of Accounts
  'coa-title': { en: 'Chart of Accounts', ar: 'دليل الحسابات' },
  'coa-sub': { en: 'Manage chart of accounts, account codes, and types', ar: 'إدارة دليل الحسابات وأكواد الحسابات وأنواعها' },
  'new-account': { en: 'New Account', ar: 'حساب جديد' },
  'edit-account': { en: 'Edit Account', ar: 'تعديل الحساب' },
  'coa-code': { en: 'Account Code', ar: 'رمز الحساب' },
  'coa-name': { en: 'Account Name', ar: 'اسم الحساب' },
  'coa-type': { en: 'Type', ar: 'النوع' },
  'coa-currency': { en: 'Currency', ar: 'العملة' },
  'coa-delete-confirm': { en: 'Delete account', ar: 'حذف الحساب' },
  // Payment Terms
  'payterm-title': { en: 'Payment Terms', ar: 'شروط الدفع' },
  'payterm-sub': { en: 'Manage payment terms, due days, and discount rules', ar: 'إدارة شروط الدفع وأيام الاستحقاق وقواعد الخصم' },
  'new-payterm': { en: 'New Payment Term', ar: 'شرط دفع جديد' },
  'edit-payterm': { en: 'Edit Payment Term', ar: 'تعديل شرط الدفع' },
  'payterm-due-days': { en: 'Due Days', ar: 'أيام الاستحقاق' },
  'payterm-discount': { en: 'Discount %', ar: 'نسبة الخصم' },
  'payterm-discount-days': { en: 'Discount Days', ar: 'أيام الخصم' },
  'payterm-default': { en: 'Default', ar: 'افتراضي' },
  'payterm-delete-confirm': { en: 'Delete payment term', ar: 'حذف شرط الدفع' },
  // Payment Methods
  'paymethod-title': { en: 'Payment Methods', ar: 'طرق الدفع' },
  'paymethod-sub': { en: 'Manage payment methods like cash, bank transfer, card', ar: 'إدارة طرق الدفع مثل النقد والتحويل البنكي والبطاقة' },
  'new-paymethod': { en: 'New Payment Method', ar: 'طريقة دفع جديدة' },
  'edit-paymethod': { en: 'Edit Payment Method', ar: 'تعديل طريقة الدفع' },
  'paymethod-default': { en: 'Default', ar: 'افتراضي' },
  'paymethod-delete-confirm': { en: 'Delete payment method', ar: 'حذف طريقة الدفع' },
  // Invoices
  'invoices-title': { en: 'Invoices', ar: 'الفواتير' },
  'invoices-sub': { en: 'Manage sales and purchase invoices', ar: 'إدارة فواتير المبيعات والمشتريات' },
  'new-invoice': { en: 'New Invoice', ar: 'فاتورة جديدة' },
  'edit-invoice': { en: 'Edit Invoice', ar: 'تعديل الفاتورة' },
  'invoices-number': { en: 'Invoice #', ar: 'رقم الفاتورة' },
  'invoices-type': { en: 'Type', ar: 'النوع' },
  'invoices-partner': { en: 'Partner', ar: 'الشريك' },
  'invoices-issue-date': { en: 'Issue Date', ar: 'تاريخ الإصدار' },
  'invoices-due-date': { en: 'Due Date', ar: 'تاريخ الاستحقاق' },
  'invoices-total': { en: 'Total', ar: 'الإجمالي' },
  'invoices-delete-confirm': { en: 'Delete invoice', ar: 'حذف الفاتورة' },
  // Departments
  'dept-title': { en: 'Departments', ar: 'الأقسام' },
  'dept-sub': { en: 'Manage organization departments and hierarchy', ar: 'إدارة أقسام المؤسسة والتسلسل الهرمي' },
  'new-dept': { en: 'New Department', ar: 'قسم جديد' },
  'edit-dept': { en: 'Edit Department', ar: 'تعديل القسم' },
  'dept-code': { en: 'Code', ar: 'الكود' },
  'dept-name': { en: 'Department', ar: 'القسم' },
  'dept-parent': { en: 'Parent Dept', ar: 'القسم الرئيسي' },
  'dept-manager': { en: 'Manager', ar: 'المدير' },
  'dept-delete-confirm': { en: 'Delete department', ar: 'حذف القسم' },
  // Journal Entries
  'je-title': { en: 'Journal Entries', ar: 'قيود اليومية' },
  'je-sub': { en: 'Manage accounting journal entries', ar: 'إدارة قيود اليومية المحاسبية' },
  'new-je': { en: 'New Journal Entry', ar: 'قيد يومية جديد' },
  'edit-je': { en: 'Edit Journal Entry', ar: 'تعديل قيد اليومية' },
  'je-date': { en: 'Entry Date', ar: 'تاريخ القيد' },
  'je-reference': { en: 'Reference', ar: 'المرجع' },
  'je-delete-confirm': { en: 'Delete journal entry', ar: 'حذف قيد اليومية' },
  // Payments
  'payments-title': { en: 'Payments', ar: 'المدفوعات' },
  'payments-sub': { en: 'Manage payments, transactions, and reconciliations', ar: 'إدارة المدفوعات والمعاملات والتسويات' },
  'new-payment': { en: 'New Payment', ar: 'دفعة جديدة' },
  'edit-payment': { en: 'Edit Payment', ar: 'تعديل الدفعة' },
  'payment-date': { en: 'Payment Date', ar: 'تاريخ الدفع' },
  'payment-invoice': { en: 'Invoice ID', ar: 'رقم الفاتورة' },
  'payment-partner': { en: 'Partner ID', ar: 'رقم الشريك' },
  'payment-method': { en: 'Payment Method', ar: 'طريقة الدفع' },
  'payment-amount': { en: 'Amount', ar: 'المبلغ' },
  'payment-reference': { en: 'Reference', ar: 'المرجع' },
  'payment-delete-confirm': { en: 'Delete payment', ar: 'حذف الدفعة' },
  // Designations
  'desig-title': { en: 'Designations', ar: 'المسميات الوظيفية' },
  'desig-sub': { en: 'Manage job designations and job titles', ar: 'إدارة المسميات الوظيفية والمسميات' },
  'new-desig': { en: 'New Designation', ar: 'مسمى وظيفي جديد' },
  'edit-desig': { en: 'Edit Designation', ar: 'تعديل المسمى الوظيفي' },
  'desig-code': { en: 'Code', ar: 'الكود' },
  'desig-name': { en: 'Designation', ar: 'المسمى الوظيفي' },
  'desig-department': { en: 'Department ID', ar: 'رقم القسم' },
  'desig-delete-confirm': { en: 'Delete designation', ar: 'حذف المسمى الوظيفي' },
  // Employees
  'emp-title': { en: 'Employees', ar: 'الموظفون' },
  'emp-sub': { en: 'Manage employee records, personal info, and employment details', ar: 'إدارة سجلات الموظفين والمعلومات الشخصية والتفاصيل الوظيفية' },
  'new-emp': { en: 'New Employee', ar: 'موظف جديد' },
  'edit-emp': { en: 'Edit Employee', ar: 'تعديل الموظف' },
  'emp-code': { en: 'Employee Code', ar: 'كود الموظف' },
  'emp-name': { en: 'Full Name', ar: 'الاسم الكامل' },
  'emp-arabic-name': { en: 'Arabic Name', ar: 'الاسم بالعربية' },
  'emp-email': { en: 'Email', ar: 'البريد الإلكتروني' },
  'emp-phone': { en: 'Phone', ar: 'الهاتف' },
  'emp-address': { en: 'Address', ar: 'العنوان' },
  'emp-national-id': { en: 'National ID', ar: 'الرقم القومي' },
  'emp-passport': { en: 'Passport No', ar: 'رقم الجواز' },
  'emp-gender': { en: 'Gender', ar: 'الجنس' },
  'emp-marital': { en: 'Marital Status', ar: 'الحالة الاجتماعية' },
  'emp-birth-date': { en: 'Date of Birth', ar: 'تاريخ الميلاد' },
  'emp-hire-date': { en: 'Hire Date', ar: 'تاريخ التعيين' },
  'emp-term-date': { en: 'Termination Date', ar: 'تاريخ إنهاء الخدمة' },
  'emp-employment-status': { en: 'Employment Status', ar: 'حالة التوظيف' },
  'emp-department': { en: 'Department ID', ar: 'رقم القسم' },
  'emp-designation': { en: 'Designation ID', ar: 'رقم المسمى' },
  'emp-manager': { en: 'Manager ID', ar: 'رقم المدير' },
  'emp-delete-confirm': { en: 'Delete employee', ar: 'حذف الموظف' },

  'dash-title': { en: 'Dashboard', ar: 'لوحة القيادة' },
  'dash-total-products': { en: 'Total Products', ar: 'إجمالي المنتجات' },
  'dash-total-customers': { en: 'Total Customers', ar: 'إجمالي العملاء' },
  'dash-total-suppliers': { en: 'Total Suppliers', ar: 'إجمالي الموردين' },
  'dash-active-orders': { en: 'Active Orders', ar: 'الطلبات النشطة' },
  'dash-total-invoices': { en: 'Invoices', ar: 'الفواتير' },
  'dash-total-payments': { en: 'Payments', ar: 'المدفوعات' },
  'dash-total-employees': { en: 'Employees', ar: 'الموظفين' },
  'dash-total-users': { en: 'Users', ar: 'المستخدمين' },
  'dash-recent-activity': { en: 'Recent Activity', ar: 'النشاط الأخير' },
  'dash-revenue': { en: 'Revenue', ar: 'الإيرادات' },
  'dash-load-error': { en: 'Failed to load dashboard data', ar: 'فشل تحميل بيانات لوحة القيادة' },

  'login-title': { en: 'Sign in to your account', ar: 'تسجيل الدخول إلى حسابك' },
  'login-username': { en: 'Username', ar: 'اسم المستخدم' },
  'login-password': { en: 'Password', ar: 'كلمة المرور' },
  'login-signin': { en: 'Sign In', ar: 'تسجيل الدخول' },
  'login-signing-in': { en: 'Signing in...', ar: 'جارٍ تسجيل الدخول...' },
  'login-invalid': { en: 'Invalid username or password', ar: 'اسم المستخدم أو كلمة المرور غير صحيحة' },

  'logout': { en: 'Logout', ar: 'تسجيل الخروج' },

  // Notifications
  'notifications-title': { en: 'Notifications', ar: 'الإشعارات' },
  'notifications-sub': { en: 'View and manage system notifications', ar: 'عرض وإدارة إشعارات النظام' },
  'notifications-mark-read': { en: 'Mark All Read', ar: 'تحديد الكل كمقروء' },
  'notifications-unread': { en: 'Unread', ar: 'غير مقروء' },
  'notifications-read': { en: 'Read', ar: 'مقروء' },

  // HR - Attendance (future)
  'attendance-title': { en: 'Attendance', ar: 'الحضور' },
  'attendance-sub': { en: 'Track employee attendance and working hours', ar: 'تتبع حضور الموظفين وساعات العمل' },
  'new-attendance': { en: 'New Attendance', ar: 'تسجيل حضور جديد' },
  'edit-attendance': { en: 'Edit Attendance', ar: 'تعديل الحضور' },
  'attendance-employee': { en: 'Employee', ar: 'الموظف' },
  'attendance-date': { en: 'Date', ar: 'التاريخ' },
  'attendance-check-in': { en: 'Check In', ar: 'تسجيل الدخول' },
  'attendance-check-out': { en: 'Check Out', ar: 'تسجيل الخروج' },
  'attendance-delete-confirm': { en: 'Delete this attendance record?', ar: 'حذف سجل الحضور هذا؟' },

  // HR - Leave (future)
  'leave-title': { en: 'Leave', ar: 'الإجازات' },
  'leave-sub': { en: 'Manage employee leave requests and balances', ar: 'إدارة طلبات إجازات الموظفين والأرصدة' },
  'new-leave': { en: 'New Leave Request', ar: 'طلب إجازة جديد' },
  'edit-leave': { en: 'Edit Leave Request', ar: 'تعديل طلب الإجازة' },
  'leave-employee': { en: 'Employee', ar: 'الموظف' },
  'leave-type': { en: 'Leave Type', ar: 'نوع الإجازة' },
  'leave-from': { en: 'From Date', ar: 'من تاريخ' },
  'leave-to': { en: 'To Date', ar: 'إلى تاريخ' },
  'leave-days': { en: 'Days', ar: 'الأيام' },
  'leave-reason': { en: 'Reason', ar: 'السبب' },
  'leave-status': { en: 'Status', ar: 'الحالة' },
  'leave-approve': { en: 'Approve', ar: 'موافقة' },
  'leave-reject': { en: 'Reject', ar: 'رفض' },
  'leave-pending': { en: 'Pending', ar: 'معلق' },
  'leave-approved': { en: 'Approved', ar: 'تمت الموافقة' },
  'leave-rejected': { en: 'Rejected', ar: 'مرفوض' },
  'leave-delete-confirm': { en: 'Delete this leave request?', ar: 'حذف طلب الإجازة هذا؟' },

  // HR - Payroll (future)
  'payroll-title': { en: 'Payroll', ar: 'الرواتب' },
  'payroll-sub': { en: 'Manage employee salaries, deductions, and payments', ar: 'إدارة رواتب الموظفين والخصميات والمدفوعات' },
  'new-payroll': { en: 'New Payroll', ar: 'راتب جديد' },
  'edit-payroll': { en: 'Edit Payroll', ar: 'تعديل الراتب' },
  'payroll-employee': { en: 'Employee', ar: 'الموظف' },
  'payroll-period': { en: 'Period', ar: 'الفترة' },
  'payroll-basic': { en: 'Basic Salary', ar: 'الراتب الأساسي' },
  'payroll-allowances': { en: 'Allowances', ar: 'البدلات' },
  'payroll-deductions': { en: 'Deductions', ar: 'الخصومات' },
  'payroll-net': { en: 'Net Salary', ar: 'صافي الراتب' },
  'payroll-status': { en: 'Status', ar: 'الحالة' },
  'payroll-paid': { en: 'Paid', ar: 'مدفوع' },
  'payroll-unpaid': { en: 'Unpaid', ar: 'غير مدفوع' },
  'payroll-delete-confirm': { en: 'Delete this payroll record?', ar: 'حذف سجل الراتب هذا؟' },

  // HR - Recruitment (future)
  'recruitment-title': { en: 'Recruitment', ar: 'التوظيف' },
  'recruitment-sub': { en: 'Manage job postings, candidates, and hiring', ar: 'إدارة إعلانات الوظائف والمرشحين والتوظيف' },
  'new-job': { en: 'New Job Posting', ar: 'إعلان وظيفي جديد' },
  'edit-job': { en: 'Edit Job Posting', ar: 'تعديل الإعلان الوظيفي' },
  'recruitment-position': { en: 'Position', ar: 'المنصب' },
  'recruitment-department': { en: 'Department', ar: 'القسم' },
  'recruitment-location': { en: 'Location', ar: 'الموقع' },
  'recruitment-type': { en: 'Type', ar: 'النوع' },
  'recruitment-full-time': { en: 'Full Time', ar: 'دوام كامل' },
  'recruitment-part-time': { en: 'Part Time', ar: 'دوام جزئي' },
  'recruitment-closing-date': { en: 'Closing Date', ar: 'تاريخ الإغلاق' },
  'recruitment-status': { en: 'Status', ar: 'الحالة' },
  'recruitment-open': { en: 'Open', ar: 'مفتوح' },
  'recruitment-closed': { en: 'Closed', ar: 'مغلق' },
  'recruitment-delete-confirm': { en: 'Delete this job posting?', ar: 'حذف هذا الإعلان الوظيفي؟' },

  // Entity Toast Messages
  'dept-saved': { en: 'Department saved successfully', ar: 'تم حفظ القسم بنجاح' },
  'dept-deleted': { en: 'Department deleted', ar: 'تم حذف القسم' },
  'desig-saved': { en: 'Designation saved successfully', ar: 'تم حفظ المسمى الوظيفي بنجاح' },
  'desig-deleted': { en: 'Designation deleted', ar: 'تم حذف المسمى الوظيفي' },
  'emp-saved': { en: 'Employee saved successfully', ar: 'تم حفظ الموظف بنجاح' },
  'emp-deleted': { en: 'Employee deleted', ar: 'تم حذف الموظف' },
  'customer-saved': { en: 'Customer saved successfully', ar: 'تم حفظ العميل بنجاح' },
  'customer-deleted': { en: 'Customer deleted', ar: 'تم حذف العميل' },
  'supplier-saved': { en: 'Supplier saved successfully', ar: 'تم حفظ المورد بنجاح' },
  'supplier-deleted': { en: 'Supplier deleted', ar: 'تم حذف المورد' },
  'sales-saved': { en: 'Sales order saved successfully', ar: 'تم حفظ أمر البيع بنجاح' },
  'sales-deleted': { en: 'Sales order deleted', ar: 'تم حذف أمر البيع' },
  'purchasing-saved': { en: 'Purchase order saved successfully', ar: 'تم حفظ أمر الشراء بنجاح' },
  'purchasing-deleted': { en: 'Purchase order deleted', ar: 'تم حذف أمر الشراء' },
  'invoice-saved': { en: 'Invoice saved successfully', ar: 'تم حفظ الفاتورة بنجاح' },
  'invoice-deleted': { en: 'Invoice deleted', ar: 'تم حذف الفاتورة' },
  'payment-saved': { en: 'Payment saved successfully', ar: 'تم حفظ الدفعة بنجاح' },
  'payment-deleted': { en: 'Payment deleted', ar: 'تم حذف الدفعة' },
  'je-saved': { en: 'Journal entry saved successfully', ar: 'تم حفظ قيد اليومية بنجاح' },
  'je-deleted': { en: 'Journal entry deleted', ar: 'تم حذف قيد اليومية' },
  'warehouse-saved': { en: 'Warehouse saved successfully', ar: 'تم حفظ المستودع بنجاح' },
  'warehouse-deleted': { en: 'Warehouse deleted', ar: 'تم حذف المستودع' },
  'coa-saved': { en: 'Account saved successfully', ar: 'تم حفظ الحساب بنجاح' },
  'coa-deleted': { en: 'Account deleted', ar: 'تم حذف الحساب' },
  'payterm-saved': { en: 'Payment term saved successfully', ar: 'تم حفظ شرط الدفع بنجاح' },
  'payterm-deleted': { en: 'Payment term deleted', ar: 'تم حذف شرط الدفع' },
  'paymethod-saved': { en: 'Payment method saved successfully', ar: 'تم حفظ طريقة الدفع بنجاح' },
  'paymethod-deleted': { en: 'Payment method deleted', ar: 'تم حذف طريقة الدفع' },
  'uom-saved': { en: 'UOM saved successfully', ar: 'تم حفظ وحدة القياس بنجاح' },
  'uom-deleted': { en: 'UOM deleted', ar: 'تم حذف وحدة القياس' },
  'uom-conv-saved': { en: 'Conversion saved successfully', ar: 'تم حفظ التحويل بنجاح' },
  'uom-conv-deleted': { en: 'Conversion deleted', ar: 'تم حذف التحويل' },
  'barcode-saved': { en: 'Barcode saved successfully', ar: 'تم حفظ الباركود بنجاح' },
  'barcode-deleted': { en: 'Barcode deleted', ar: 'تم حذف الباركود' },
  'attr-saved': { en: 'Attribute saved successfully', ar: 'تم حفظ الخاصية بنجاح' },
  'attr-deleted': { en: 'Attribute deleted', ar: 'تم حذف الخاصية' },
  'user-saved': { en: 'User saved successfully', ar: 'تم حفظ المستخدم بنجاح' },
  'user-deleted': { en: 'User deleted', ar: 'تم حذف المستخدم' },
  'stock-move-saved': { en: 'Stock movement saved successfully', ar: 'تم حفظ حركة المخزون بنجاح' },
  'stock-move-deleted': { en: 'Stock movement deleted', ar: 'تم حذف حركة المخزون' },

  // Gender & Marital Status Options
  'gender-male': { en: 'Male', ar: 'ذكر' },
  'gender-female': { en: 'Female', ar: 'أنثى' },
  'marital-single': { en: 'Single', ar: 'أعزب' },
  'marital-married': { en: 'Married', ar: 'متزوج' },
  'marital-divorced': { en: 'Divorced', ar: 'مطلق' },
  'marital-widowed': { en: 'Widowed', ar: 'أرمل' },

  // Employment Status Options
  'emp-status-active': { en: 'Active', ar: 'نشط' },
  'emp-status-terminated': { en: 'Terminated', ar: 'منتهي' },
  'emp-status-suspended': { en: 'Suspended', ar: 'موقوف' },
  'emp-status-resigned': { en: 'Resigned', ar: 'مستقيل' },

  'logout': { en: 'Logout', ar: 'تسجيل الخروج' },

  'confirm-title': { en: 'Confirm', ar: 'تأكيد' },
  'confirm-delete': { en: 'Delete', ar: 'حذف' },
  'confirm-cancel': { en: 'Cancel', ar: 'إلغاء' },
  'confirm-delete-msg': { en: 'Are you sure you want to delete', ar: 'هل أنت متأكد من حذف' },
}

export function useI18n() {
  const settings = useSettingsStore()

  const locale = computed(() => {
    const v = settings.values['SYSTEM_LANGUAGE']
    if (v === 'ar-EG' || v === 'en-US') {
      saveLocale(v)
      return v
    }
    return loadLocale()
  })

  const dir = computed(() => locale.value === 'ar-EG' ? 'rtl' : 'ltr')
  const isRTL = computed(() => dir.value === 'rtl')

  function t(key, fallback) {
    const entry = dict[key]
    if (!entry) return fallback || key
    return locale.value === 'ar-EG' ? entry.ar : entry.en
  }

  function apply() {
    document.documentElement.setAttribute('dir', dir.value)
    document.documentElement.setAttribute('lang', locale.value)
  }

  watch(locale, apply, { immediate: true })

  watch(() => settings.values['SYSTEM_LANGUAGE'], (v) => {
    if (v) saveLocale(v)
  })

  return { locale, dir, isRTL, t, apply }
}

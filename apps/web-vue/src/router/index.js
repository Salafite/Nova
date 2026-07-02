import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue') },
  { path: '/landing', name: 'landing', component: () => import('../views/landing/LandingView.vue') },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    children: [
      { path: '', name: 'home', meta: { requiresAuth: true }, component: () => import('../views/home/HomeView.vue') },
      { path: 'dashboard', name: 'dashboard', meta: { requiresAuth: true }, component: () => import('../views/dashboard/DashboardView.vue') },
      { path: 'products', name: 'products', meta: { requiresAuth: true }, component: () => import('../views/products/ProductsView.vue') },
      { path: 'products/:id', name: 'product-detail', meta: { requiresAuth: true }, component: () => import('../views/products/ProductDetailView.vue') },
      { path: 'categories', name: 'categories', meta: { requiresAuth: true }, component: () => import('../views/categories/CategoriesView.vue') },
      { path: 'customers', name: 'customers', meta: { requiresAuth: true }, component: () => import('../views/customers/CustomersView.vue') },
      { path: 'customers/:id', name: 'customer-detail', meta: { requiresAuth: true }, component: () => import('../views/customers/CustomerDetailView.vue') },
      { path: 'suppliers', name: 'suppliers', meta: { requiresAuth: true }, component: () => import('../views/suppliers/SuppliersView.vue') },
      { path: 'sales', name: 'sales', meta: { requiresAuth: true }, component: () => import('../views/sales/SalesView.vue') },
      { path: 'sales/:id', name: 'sales-detail', meta: { requiresAuth: true }, component: () => import('../views/sales/OrderDetailView.vue') },
      { path: 'purchasing', name: 'purchasing', meta: { requiresAuth: true }, component: () => import('../views/purchasing/PurchasingView.vue') },
      { path: 'inventory', name: 'inventory', meta: { requiresAuth: true }, component: () => import('../views/inventory/InventoryView.vue') },
      { path: 'warehouse', meta: { requiresAuth: true }, redirect: { name: 'warehouses' } },
      { path: 'finance', name: 'finance', meta: { requiresAuth: true }, component: () => import('../views/finance/FinanceView.vue') },
      { path: 'finance/:id', name: 'invoice-detail', meta: { requiresAuth: true }, component: () => import('../views/finance/InvoiceDetailView.vue') },
      { path: 'admin', name: 'admin', meta: { requiresAuth: true }, component: () => import('../views/admin/AdminView.vue') },
      { path: 'modules', name: 'modules', meta: { requiresAuth: true }, component: () => import('../views/admin/ModuleManagerView.vue') },
      { path: 'settings', name: 'settings', meta: { requiresAuth: true }, component: () => import('../views/settings/SettingsView.vue') },
      { path: 'admin/subscription', name: 'subscription', meta: { requiresAuth: true }, component: () => import('../views/admin/SubscriptionView.vue') },
      { path: 'uom', name: 'uom', meta: { requiresAuth: true }, component: () => import('../views/uom/UOMView.vue') },
      { path: 'uom-conversions', name: 'uom-conversions', meta: { requiresAuth: true }, component: () => import('../views/uom-conversions/UOMConvView.vue') },
      { path: 'barcodes', name: 'barcodes', meta: { requiresAuth: true }, component: () => import('../views/barcodes/BarcodesView.vue') },
      { path: 'attributes', name: 'attributes', meta: { requiresAuth: true }, component: () => import('../views/attributes/AttributesView.vue') },
      { path: 'stock-movements', name: 'stock-movements', meta: { requiresAuth: true }, component: () => import('../views/stock-movements/StockMovementsView.vue') },
      { path: 'warehouses', name: 'warehouses', meta: { requiresAuth: true }, component: () => import('../views/warehouses/WarehouseView.vue') },
      { path: 'chart-of-accounts', name: 'chart-of-accounts', meta: { requiresAuth: true }, component: () => import('../views/chart-of-accounts/ChartOfAccountsView.vue') },
      { path: 'payment-terms', name: 'payment-terms', meta: { requiresAuth: true }, component: () => import('../views/payment-terms/PaymentTermsView.vue') },
      { path: 'payment-methods', name: 'payment-methods', meta: { requiresAuth: true }, component: () => import('../views/payment-methods/PaymentMethodsView.vue') },
      { path: 'departments', name: 'departments', meta: { requiresAuth: true }, component: () => import('../views/departments/DepartmentsView.vue') },
      { path: 'journal-entries', name: 'journal-entries', meta: { requiresAuth: true }, component: () => import('../views/journal-entries/JournalEntriesView.vue') },
      { path: 'payments', name: 'payments', meta: { requiresAuth: true }, component: () => import('../views/payments/PaymentsView.vue') },
      { path: 'designations', name: 'designations', meta: { requiresAuth: true }, component: () => import('../views/designations/DesignationsView.vue') },
      { path: 'employees', name: 'employees', meta: { requiresAuth: true }, component: () => import('../views/employees/EmployeesView.vue') },
      { path: 'notifications', name: 'notifications', meta: { requiresAuth: true }, component: () => import('../views/notifications/NotificationsView.vue') },
      { path: 'warehouse/pick-lists', name: 'pick-lists', meta: { requiresAuth: true }, component: () => import('../views/warehouse/PickListsView.vue') },
      { path: 'warehouse/pick-lists/:id', name: 'pick-list-detail', meta: { requiresAuth: true }, component: () => import('../views/warehouse/PickListDetailView.vue') },
      { path: 'migration', name: 'migration', meta: { requiresAuth: true }, component: () => import('../views/migration/MigrateView.vue') },
    ]
  }
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('nova_token')
  if (to.meta.requiresAuth && !token) next('/login')
  else next()
})

export default router

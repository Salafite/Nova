<template>
  <div :dir="dir">
    <h1 class="page-title mb-6">{{ t('dash-title', 'Dashboard') }}</h1>

    <div v-if="globalLoading" class="text-center py-12 text-gray-400">{{ t('loading', 'Loading...') }}</div>

    <template v-else>
      <div class="stats-grid">
        <StatsCard
          v-for="(card, i) in statsCards"
          :key="i"
          :label="t(card.labelKey, card.fallback)"
          :value="card.value"
          :color="card.color"
          :to="card.to"
        />
      </div>

      <div v-if="quickLinks.length" class="action-card">
        <h3 class="section-title">{{ t('dash-quick-links', 'Quick Links') }}</h3>
        <div class="action-chips">
          <router-link
            v-for="(link, i) in quickLinks"
            :key="i"
            :to="{ name: link.route }"
            class="action-chip"
          >
            {{ t(link.labelKey, link.fallback) }}
          </router-link>
        </div>
      </div>

      <div v-for="(tbl, i) in tables" :key="i" class="data-card">
        <h3 class="section-title">{{ t(tbl.titleKey, tbl.titleFallback) }}</h3>

        <div v-if="tbl.loading" class="section-message">{{ t('loading', 'Loading...') }}</div>

        <div v-else-if="tbl.error" class="section-error">
          <span>{{ t('dash-load-error', 'Failed to load') }}</span>
          <button class="retry-btn" @click="tbl.loadFn?.()">{{ t('retry', 'Retry') }}</button>
        </div>

        <div v-else-if="tbl.items.length === 0" class="section-message">
          {{ t('no-records', 'No records found') }}
        </div>

        <table v-else-if="tbl.columns" class="dash-table">
          <thead>
            <tr>
              <th v-for="(col, j) in tbl.columns" :key="j">{{ t(col.labelKey || col.field, col.fallback) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, j) in tbl.items" :key="j">
              <td v-for="(col, k) in tbl.columns" :key="k">
                {{ col.format ? col.format(row) : (row[col.field] ?? '-') }}
              </td>
            </tr>
          </tbody>
        </table>

        <ul v-else class="item-list">
          <li v-for="(item, j) in tbl.items" :key="j" class="item-row">
            <span class="item-label">{{ item.label }}</span>
            <span :class="['item-value', item.valueClass]">{{ item.value }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { useAuthStore } from '../../stores/auth.js'
import { useWebSocket } from '../../composables/useWebSocket.js'
import { api } from '../../api/client.js'
import StatsCard from '../../components/StatsCard.vue'

const { t, dir } = useI18n()
const auth = useAuthStore()

const role = computed(() => {
  const r = auth.role?.toLowerCase() || ''
  if (r === 'sales rep') return 'salesman'
  return r
})

const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
const wsOrders = useWebSocket(`/ws/orders/${businessId}`)

function refreshDashboard() {
  const r = role.value
  if (r === 'salesman') loadSalesmanData()
  else if (r === 'warehouse') loadWarehouseData()
  else if (r === 'accountant') loadAccountantData()
  else loadAdminData()
}

wsInventory.on('stock_updated', () => {
  console.log('[WS] stock_updated received, refreshing dashboard')
  refreshDashboard()
})
wsOrders.on('order_status_changed', () => {
  console.log('[WS] order_status_changed received, refreshing dashboard')
  refreshDashboard()
})

const globalLoading = ref(true)
const statsCards = reactive([])
const quickLinks = reactive([])
const tables = reactive([])

function clearReactive(arr) {
  arr.splice(0, arr.length)
}

function fmtDate(d) {
  if (!d) return '-'
  try { return new Date(d).toLocaleDateString() } catch { return String(d) }
}

async function loadSalesmanData() {
  clearReactive(statsCards)
  clearReactive(tables)
  globalLoading.value = true

  const salesIdx = tables.length
  tables.push({ titleKey: 'dash-recent-orders', titleFallback: 'Recent Orders', columns: null, items: [], loading: true, error: false, loadFn: null })

  try {
    const [ordersRes, stockRes] = await Promise.allSettled([
      api.get('/T0012I/', { params: { status: 'open', limit: 100 } }),
      api.get('/T0009I/', { params: { limit: 200 } })
    ])

    const openOrders = ordersRes.status === 'fulfilled' ? ordersRes.value.data?.data || ordersRes.value.data?.records || [] : []
    const stockItems = stockRes.status === 'fulfilled' ? stockRes.value.data?.data || stockRes.value.data?.records || [] : []

    const lowStock = stockItems.filter(item => {
      const qty = parseFloat(item.qty_on_hand || item.quantity || item.QtyOnHand || 0)
      const reorder = parseFloat(item.reorder_level || item.reorderPoint || item.ReorderLevel || 0)
      return reorder > 0 && qty <= reorder
    })

    statsCards.push(
      { labelKey: 'dash-open-orders', fallback: 'Open Orders', value: openOrders.length, color: '#008080', to: 'sales' },
      { labelKey: 'dash-low-stock', fallback: 'Low Stock Alerts', value: lowStock.length, color: '#ba1a1a', to: 'products' }
    )

    const recentOrders = openOrders
      .sort((a, b) => new Date(b.created_at || b.order_date || 0) - new Date(a.created_at || a.order_date || 0))
      .slice(0, 10)

    const tbl = tables[salesIdx]
    tbl.loading = false
    tbl.columns = [
      { field: 'order_no', labelKey: 'sales-order-number', fallback: 'Order #' },
      { field: 'customer_name', labelKey: 'sales-customer', fallback: 'Customer' },
      { field: 'total_amount', labelKey: 'sales-grand-total', fallback: 'Amount', format: r => r.total_amount ?? r.grand_total ?? '-' },
      { field: 'created_at', labelKey: 'date', fallback: 'Date', format: r => fmtDate(r.created_at || r.order_date) }
    ]
    tbl.items = recentOrders
    tbl.loadFn = loadSalesmanData
  } catch {
    statsCards.push(
      { labelKey: 'dash-open-orders', fallback: 'Open Orders', value: '--', color: '#008080', to: 'sales' },
      { labelKey: 'dash-low-stock', fallback: 'Low Stock Alerts', value: '--', color: '#ba1a1a', to: 'products' }
    )
    const tbl = tables[salesIdx]
    if (tbl) { tbl.loading = false; tbl.error = true; tbl.loadFn = loadSalesmanData }
  } finally {
    globalLoading.value = false
  }
}

async function loadWarehouseData() {
  clearReactive(statsCards)
  clearReactive(tables)
  globalLoading.value = true

  try {
    const res = await api.get('/T0101I/', { params: { limit: 500 } })
    const picks = res.data?.data || res.data?.records || []

    const pending = picks.filter(p => (p.status || '').toLowerCase() === 'pending')
    const active = picks.filter(p => (p.status || '').toLowerCase() === 'active' || (p.status || '').toLowerCase() === 'in_progress')
    const today = new Date().toISOString().slice(0, 10)
    const completedToday = picks.filter(p => {
      const s = (p.status || '').toLowerCase()
      const completedDate = p.completed_date || p.completed_at || p.updated_at || ''
      return s === 'completed' && completedDate.startsWith(today)
    })

    statsCards.push(
      { labelKey: 'dash-pending-picks', fallback: 'Pending Pick Lists', value: pending.length, color: '#e67e22', to: 'warehouse' },
      { labelKey: 'dash-active-picks', fallback: 'Active Picks', value: active.length, color: '#008080', to: 'warehouse' },
      { labelKey: 'dash-completed-today', fallback: 'Completed Today', value: completedToday.length, color: '#27ae60', to: 'warehouse' }
    )
  } catch {
    statsCards.push(
      { labelKey: 'dash-pending-picks', fallback: 'Pending Pick Lists', value: '--', color: '#e67e22', to: '' },
      { labelKey: 'dash-active-picks', fallback: 'Active Picks', value: '--', color: '#008080', to: '' },
      { labelKey: 'dash-completed-today', fallback: 'Completed Today', value: '--', color: '#27ae60', to: '' }
    )
  } finally {
    globalLoading.value = false
  }
}

async function loadAccountantData() {
  clearReactive(statsCards)
  clearReactive(tables)
  globalLoading.value = true

  const overdueIdx = tables.length
  tables.push({ titleKey: 'dash-overdue-alerts', titleFallback: 'Overdue Alerts', columns: null, items: [], loading: true, error: false, loadFn: null })

  try {
    const [invRes, payRes] = await Promise.allSettled([
      api.get('/T0090I/', { params: { limit: 500 } }),
      api.get('/payments/', { params: { limit: 200 } })
    ])

    const invoices = invRes.status === 'fulfilled' ? invRes.value.data?.data || invRes.value.data?.records || [] : []
    const payments = payRes.status === 'fulfilled' ? payRes.value.data?.data || payRes.value.data?.records || [] : []

    const today = new Date().toISOString().slice(0, 10)
    const pendingRec = invoices.filter(inv => {
      const s = (inv.status || '').toLowerCase()
      return s === 'unpaid' || s === 'pending' || s === 'overdue'
    })
    const overdue = invoices.filter(inv => {
      const s = (inv.status || '').toLowerCase()
      const due = inv.due_date || inv.dueDate || ''
      return (s === 'unpaid' || s === 'pending' || s === 'overdue') && due < today
    })
    const todayPayments = payments.filter(p => {
      const d = p.payment_date || p.date || p.created_at || ''
      return String(d).startsWith(today)
    })

    statsCards.push(
      { labelKey: 'dash-pending-receivables', fallback: 'Pending Receivables', value: pendingRec.length, color: '#e67e22', to: 'finance' },
      { labelKey: 'dash-overdue-count', fallback: 'Overdue Alerts', value: overdue.length, color: '#ba1a1a', to: 'finance' },
      { labelKey: 'dash-payments-today', fallback: "Today's Payments", value: todayPayments.length, color: '#27ae60', to: 'payments' }
    )

    const tbl = tables[overdueIdx]
    tbl.loading = false
    tbl.columns = [
      { field: 'invoice_no', labelKey: 'invoices-number', fallback: 'Invoice #' },
      { field: 'partner_name', labelKey: 'invoices-partner', fallback: 'Partner', format: r => r.partner_name || r.customer_name || '-' },
      { field: 'due_date', labelKey: 'invoices-due-date', fallback: 'Due Date', format: r => fmtDate(r.due_date || r.dueDate) },
      { field: 'total_amount', labelKey: 'invoices-total', fallback: 'Total', format: r => r.total_amount ?? r.total ?? '-' }
    ]
    tbl.items = overdue.slice(0, 10)
    tbl.loadFn = loadAccountantData
  } catch {
    statsCards.push(
      { labelKey: 'dash-pending-receivables', fallback: 'Pending Receivables', value: '--', color: '#e67e22', to: '' },
      { labelKey: 'dash-overdue-count', fallback: 'Overdue Alerts', value: '--', color: '#ba1a1a', to: '' },
      { labelKey: 'dash-payments-today', fallback: "Today's Payments", value: '--', color: '#27ae60', to: '' }
    )
    const tbl = tables[overdueIdx]
    if (tbl) { tbl.loading = false; tbl.error = true; tbl.loadFn = loadAccountantData }
  } finally {
    globalLoading.value = false
  }
}

async function loadAdminData() {
  clearReactive(statsCards)
  clearReactive(quickLinks)
  clearReactive(tables)
  globalLoading.value = true

  const activityIdx = tables.length
  tables.push({ titleKey: 'dash-recent-activity', titleFallback: 'Recent Activity', columns: null, items: [], loading: true, error: false, loadFn: null })

  quickLinks.push(
    { labelKey: 'admin-title', fallback: 'User Management', route: 'admin' }
  )

  try {
    const res = await api.get('/bi/dashboard/summary')
    const data = res.data

    statsCards.push(
      { labelKey: 'dash-total-products', fallback: 'Total Products', value: data.stats.products || 0, color: undefined, to: 'products' },
      { labelKey: 'dash-total-customers', fallback: 'Total Customers', value: data.stats.customers || 0, color: undefined, to: 'customers' },
      { labelKey: 'dash-total-suppliers', fallback: 'Total Suppliers', value: data.stats.suppliers || 0, color: undefined, to: 'suppliers' },
      { labelKey: 'dash-active-orders', fallback: 'Active Orders', value: data.stats.salesOrders || 0, color: '#008080', to: 'sales' },
      { labelKey: 'dash-total-invoices', fallback: 'Invoices', value: data.stats.invoices || 0, color: '#ba1a1a', to: 'finance' },
      { labelKey: 'dash-total-payments', fallback: 'Payments', value: data.stats.payments || 0, color: '#1a6bba', to: 'payments' },
      { labelKey: 'dash-total-employees', fallback: 'Employees', value: data.stats.employees || 0, color: '#6bba1a', to: 'employees' },
      { labelKey: 'dash-total-users', fallback: 'Users', value: data.stats.users || 0, color: '#9b1aba', to: 'admin' }
    )

    const tbl = tables[activityIdx]
    tbl.loading = false
    tbl.items = (data.recentActivity || []).map(r => ({
      label: r.label,
      value: fmtDate(r.date)
    }))
    tbl.loadFn = loadAdminData
  } catch {
    statsCards.push(
      { labelKey: 'dash-total-products', fallback: 'Total Products', value: '--', color: undefined, to: '' },
      { labelKey: 'dash-total-customers', fallback: 'Total Customers', value: '--', color: undefined, to: '' },
      { labelKey: 'dash-total-suppliers', fallback: 'Total Suppliers', value: '--', color: undefined, to: '' },
      { labelKey: 'dash-active-orders', fallback: 'Active Orders', value: '--', color: '#008080', to: '' },
      { labelKey: 'dash-total-invoices', fallback: 'Invoices', value: '--', color: '#ba1a1a', to: '' },
      { labelKey: 'dash-total-payments', fallback: 'Payments', value: '--', color: '#1a6bba', to: '' },
      { labelKey: 'dash-total-employees', fallback: 'Employees', value: '--', color: '#6bba1a', to: '' },
      { labelKey: 'dash-total-users', fallback: 'Users', value: '--', color: '#9b1aba', to: '' }
    )
    const tbl = tables[activityIdx]
    if (tbl) { tbl.loading = false; tbl.error = true; tbl.loadFn = loadAdminData }
  } finally {
    globalLoading.value = false
  }
}

onMounted(() => {
  const r = role.value
  if (r === 'salesman') loadSalesmanData()
  else if (r === 'warehouse') loadWarehouseData()
  else if (r === 'accountant') loadAccountantData()
  else loadAdminData()
})
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 32px; }
@media (min-width: 640px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 1024px) { .stats-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 400px) { .stats-grid { grid-template-columns: 1fr; } }

.action-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; }
.action-chips { display: flex; flex-wrap: wrap; gap: 12px; }
.action-chip { display: inline-block; padding: 8px 20px; background: var(--bg-subtle); border: 1px solid var(--border-default); border-radius: 8px; color: var(--text-primary); font-size: 13px; font-weight: 500; text-decoration: none; transition: background 0.15s, border-color 0.15s; }
.action-chip:hover { background: var(--bg-hover); border-color: var(--border-strong); }

.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
.section-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; }
.section-message { color: var(--text-faint); font-size: 13px; padding: 12px 0; text-align: center; }
.section-error { color: #ba1a1a; font-size: 13px; padding: 12px 0; text-align: center; }
.retry-btn { background: none; border: 1px solid currentColor; border-radius: 6px; color: inherit; cursor: pointer; font-size: 12px; margin-left: 12px; padding: 4px 12px; }

.item-list { list-style: none; padding: 0; margin: 0; }
.item-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-light); }
.item-row:last-child { border-bottom: none; }
.item-label { color: var(--text-secondary); font-size: 13px; }
.item-value { color: var(--text-primary); font-size: 13px; font-weight: 500; }

.dash-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dash-table th { text-align: left; padding: 10px 12px; color: var(--text-faint); font-weight: 500; border-bottom: 1px solid var(--border-light); white-space: nowrap; }
.dash-table td { padding: 10px 12px; color: var(--text-primary); border-bottom: 1px solid var(--border-light); }
.dash-table tr:last-child td { border-bottom: none; }
</style>

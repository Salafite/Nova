<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="order">
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/sales')">&larr; {{ t('back-to-orders') }}</button>
          <h1 class="page-title">{{ t('sales-order') }} #{{ order.order_number }}</h1>
        </div>
        <div class="flex gap-2">
          <button v-if="order.status === 'Pending'" class="btn-primary" @click="confirmOrder">{{ t('confirm') }}</button>
          <button v-if="canCancel" class="btn-outline btn-outline-danger" @click="cancelOrder">{{ t('cancel-order') }}</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('order-info') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('status') }}:</span><span class="badge" :class="statusBadge">{{ order.status }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('sales-customer') }}:</span><span>{{ customerName }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('sales-order-date') }}:</span><span>{{ order.order_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('warehouse') }}:</span><span>{{ warehouseName }}</span></div>
          <div class="info-row" v-if="order.notes"><span class="info-label">{{ t('sales-notes') }}:</span><span>{{ order.notes }}</span></div>
        </div>
        <div class="detail-card">
          <h3 class="card-title">{{ t('totals') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('sales-subtotal') }}:</span><span class="col-num">${{ (order.subtotal || 0).toFixed(2) }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('sales-tax') }}:</span><span class="col-num">${{ (order.tax || 0).toFixed(2) }}</span></div>
          <div class="info-row total-row"><span class="info-label">{{ t('sales-grand-total') }}:</span><span class="col-num">${{ (order.grand_total || 0).toFixed(2) }}</span></div>
        </div>
      </div>

      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('order-lines') }}</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('product') }}</th>
                <th class="col-num">{{ t('qty') }}</th>
                <th class="col-num">{{ t('unit-price') }}</th>
                <th class="col-num">{{ t('line-total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in lines" :key="line.id">
                <td class="cell-mono">{{ line.line_number }}</td>
                <td>{{ line.product_name || `#${line.product_id}` }}</td>
                <td class="col-num">{{ line.qty }}</td>
                <td class="col-num">${{ (line.unit_price || 0).toFixed(2) }}</td>
                <td class="col-num">${{ (line.line_total || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('status-history') }}</h3></div>
        <div class="timeline" v-if="statusHistory.length">
          <div v-for="(entry, i) in statusHistory" :key="i" class="timeline-item">
            <div class="timeline-dot" :class="entry.class"></div>
            <div class="timeline-content">
              <span class="badge" :class="entry.class">{{ entry.status }}</span>
              <span class="timeline-date">{{ entry.date }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-sm">{{ t('no-records') }}</div>
      </div>
    </template>
    <ConfirmDialog v-if="showConfirmCancel" title="Cancel Order" message="Are you sure you want to cancel this order? This will release any reserved stock." @confirm="executeCancel" @cancel="showConfirmCancel = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const order = ref(null)
const lines = ref([])
const customers = ref([])
const warehouses = ref([])
const showConfirmCancel = ref(false)

const customerName = computed(() => {
  if (!order.value) return ''
  const c = customers.value.find(x => x.id === order.value.customer_id)
  return c ? c.name : `#${order.value.customer_id}`
})

const warehouseName = computed(() => {
  if (!order.value || !order.value.warehouse_id) return '-'
  const w = warehouses.value.find(x => x.id === order.value.warehouse_id)
  return w ? w.name : `#${order.value.warehouse_id}`
})

const statusBadge = computed(() => {
  const map = { Pending: 'badge-warning', Confirmed: 'badge-info', Shipped: 'badge-active', Delivered: 'badge-active', Cancelled: 'badge-inactive', Paid: 'badge-active', Invoiced: 'badge-active' }
  return map[order.value?.status] || 'badge-inactive'
})

const canCancel = computed(() => {
  return order.value && ['Pending', 'Confirmed'].includes(order.value.status)
})

const statusHistory = computed(() => {
  if (!order.value) return []
  const allStatuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Invoiced', 'Paid', 'Cancelled']
  const current = order.value.status
  const idx = allStatuses.indexOf(current)
  if (idx === -1) return [{ status: current, date: order.value.updated_at || order.value.created_at, class: 'badge-info' }]
  const classMap = { Pending: 'badge-warning', Confirmed: 'badge-info', Shipped: 'badge-active', Delivered: 'badge-active', Invoiced: 'badge-active', Paid: 'badge-active', Cancelled: 'badge-inactive' }
  return allStatuses.slice(0, idx + 1).map((s, i) => ({
    status: s,
    date: i === idx ? (order.value.updated_at || order.value.created_at) : order.value.created_at,
    class: classMap[s] || 'badge-info',
  }))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [orderRes, lineRes, custRes, whRes] = await Promise.all([
      api.get(`/T0012I/${id}`),
      api.get('/T0013I/', { params: { sales_order_id: id } }),
      api.get('/T0010I/'),
      api.get('/T0008I/'),
    ])
    order.value = orderRes.data
    lines.value = lineRes.data || []
    customers.value = custRes.data || []
    warehouses.value = whRes.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

async function confirmOrder() {
  try {
    await api.post(`/T0012I/${order.value.id}/confirm`)
    toast('Order confirmed — stock reserved', 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Confirmation failed', 'error')
  }
}

function cancelOrder() {
  showConfirmCancel.value = true
}

async function executeCancel() {
  showConfirmCancel.value = false
  try {
    await api.post(`/T0012I/${order.value.id}/cancel`)
    toast('Order cancelled — stock released', 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Cancellation failed', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-state-sm { text-align: center; padding: 24px; color: #999; font-size: 13px; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-outline-danger { color: #dc2626; border-color: #fca5a5; }
.btn-outline-danger:hover { background: #fee2e2; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0 0 12px; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-header .card-title { margin: 0; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 100px; }
.total-row { border-top: 1px solid #eee; margin-top: 8px; padding-top: 8px; font-weight: 700; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }

.timeline { padding: 16px; }
.timeline-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-left: 2px solid #e0e0e0; margin-left: 8px; padding-left: 20px; position: relative; }
.timeline-item:last-child { border-left-color: transparent; }
.timeline-dot { width: 10px; height: 10px; border-radius: 50%; position: absolute; left: -6px; }
.timeline-dot.badge-active { background: #16a34a; }
.timeline-dot.badge-warning { background: #d97706; }
.timeline-dot.badge-info { background: #0284c7; }
.timeline-dot.badge-inactive { background: #888; }
.timeline-content { display: flex; align-items: center; gap: 10px; }
.timeline-date { font-size: 11px; color: #999; }

[dir="rtl"] .timeline-item { border-left: none; border-right: 2px solid #e0e0e0; margin-left: 0; margin-right: 8px; padding-left: 0; padding-right: 20px; }
[dir="rtl"] .timeline-dot { left: auto; right: -6px; }
[dir="rtl"] .data-table th { text-align: right; }
</style>

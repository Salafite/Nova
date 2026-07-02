<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="order">
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/purchasing')">&larr; {{ t('back-to-orders', 'Back to Orders') }}</button>
          <h2 class="page-title">{{ t('purchase-order', 'Purchase Order') }} #{{ order.order_number }}</h2>
        </div>
        <div class="flex gap-2">
          <button v-if="order.status === 'Pending'" class="btn-primary" @click="approveOrder">{{ t('approve', 'Approve') }}</button>
          <button v-if="order.status === 'Approved'" class="btn-primary" @click="receiveOrder">{{ t('receive', 'Receive') }}</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('order-info', 'Order Info') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('status', 'Status') }}:</span><span class="badge" :class="statusBadge">{{ order.status }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('supplier', 'Supplier') }}:</span><span>{{ supplierName }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('purchase-order-date', 'Order Date') }}:</span><span>{{ order.order_date }}</span></div>
          <div class="info-row" v-if="order.expected_date"><span class="info-label">{{ t('purchase-expected-date', 'Expected') }}:</span><span>{{ order.expected_date }}</span></div>
          <div class="info-row" v-if="order.notes"><span class="info-label">{{ t('notes', 'Notes') }}:</span><span>{{ order.notes }}</span></div>
        </div>
        <div class="detail-card">
          <h3 class="card-title">{{ t('totals', 'Totals') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('subtotal', 'Subtotal') }}:</span><span class="col-num">${{ (order.subtotal || 0).toFixed(2) }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('tax', 'Tax') }}:</span><span class="col-num">${{ (order.tax || 0).toFixed(2) }}</span></div>
          <div class="info-row total-row"><span class="info-label">{{ t('grand-total', 'Total') }}:</span><span class="col-num"><strong>${{ (order.grand_total || order.total || 0).toFixed(2) }}</strong></span></div>
        </div>
      </div>

      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('order-lines', 'Order Lines') }}</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('product', 'Product') }}</th>
                <th class="col-num">{{ t('qty', 'Qty') }}</th>
                <th class="col-num">{{ t('unit-price', 'Unit Price') }}</th>
                <th class="col-num">{{ t('line-total', 'Line Total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in lines" :key="line.id">
                <td class="cell-mono">{{ line.line_number || line.id }}</td>
                <td>{{ line.product_name || `#${line.product_id}` }}</td>
                <td class="col-num">{{ line.qty || line.quantity }}</td>
                <td class="col-num">${{ (line.unit_price || 0).toFixed(2) }}</td>
                <td class="col-num">${{ (line.line_total || line.total || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <ConfirmDialog v-if="showConfirmApprove" :title="t('confirm-approve', 'Approve Order?')" :message="t('confirm-approve-msg', 'Approve this purchase order?')" @confirm="executeApprove" @cancel="showConfirmApprove = false" />
    <ConfirmDialog v-if="showConfirmReceive" :title="t('confirm-receive', 'Receive Order?')" :message="t('confirm-receive-msg', 'Mark this purchase order as received?')" @confirm="executeReceive" @cancel="showConfirmReceive = false" />
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
const suppliers = ref([])
const showConfirmApprove = ref(false)
const showConfirmReceive = ref(false)

const supplierName = computed(() => {
  if (!order.value) return ''
  const s = suppliers.value.find(x => x.id === order.value.supplier_id)
  return s ? s.name : `#${order.value.supplier_id}`
})

const statusBadge = computed(() => {
  const map = { Pending: 'badge-warning', Approved: 'badge-info', Sent: 'badge-info', Received: 'badge-active', Cancelled: 'badge-inactive' }
  return map[order.value?.status] || 'badge-inactive'
})

async function load() {
  loading.value = true; error.value = ''
  try {
    const id = route.params.id
    const [orderRes, lineRes, supRes] = await Promise.all([
      api.get(`/T0014I/${id}`),
      api.get('/T0015I/', { params: { purchase_order_id: id } }),
      api.get('/T0011I/'),
    ])
    order.value = orderRes.data
    lines.value = lineRes.data || []
    suppliers.value = supRes.data || []
  } catch { error.value = t('failed-load', 'Failed to load') }
  finally { loading.value = false }
}

function approveOrder() { showConfirmApprove.value = true }
function receiveOrder() { showConfirmReceive.value = true }

async function executeApprove() {
  showConfirmApprove.value = false
  try {
    await api.post(`/T0014I/${order.value.id}/approve`)
    toast(t('approved', 'Order approved'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-action', 'Action failed'), 'error')
  }
}

async function executeReceive() {
  showConfirmReceive.value = false
  try {
    await api.post(`/T0014I/${order.value.id}/receive`)
    toast(t('received', 'Order received'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-action', 'Action failed'), 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.btn-link { background: none; border: none; color: var(--color-primary); font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; }
.card-header { padding: 14px 18px; border-bottom: 1px solid var(--border-light); }
.card-header .card-title { margin: 0; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: var(--text-subtle); font-weight: 500; min-width: 100px; }
.total-row { border-top: 1px solid var(--border-default); margin-top: 8px; padding-top: 8px; font-weight: 700; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }
.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }
.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-subtle); }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
</style>

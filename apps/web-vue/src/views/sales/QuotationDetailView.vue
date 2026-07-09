<template>
  <div :dir="dir">
    <div v-if="loading"><SkeletonCard /></div>

    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else>
      <div class="page-header">
        <div>
          <a class="back-link" @click="router.push('/sales/quotations')">&larr; {{ t('back', 'Back') }}</a>
          <h1 class="page-title">{{ t('quotation', 'Quotation') }} #{{ item.quote_number }}</h1>
        </div>
        <div class="header-actions">
          <button v-if="item.status === 'Draft'" class="btn-outline" @click="sendQuote">{{ t('send', 'Send') }}</button>
          <button v-if="item.status === 'Accepted'" class="btn-primary" @click="convertToOrder" :disabled="converting">{{ converting ? t('converting', 'Converting...') : t('convert-to-order', 'Convert to Order') }}</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3>{{ t('quote-info', 'Quote Info') }}</h3>
          <div class="detail-row"><span class="detail-label">{{ t('status', 'Status') }}</span><span class="badge" :class="statusBadge">{{ item.status }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ t('customer', 'Customer') }}</span><span>{{ customerName }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ t('quote-date', 'Date') }}</span><span>{{ item.quote_date }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ t('valid-until', 'Valid Until') }}</span><span>{{ item.valid_until || '-' }}</span></div>
          <div class="detail-row" v-if="item.notes"><span class="detail-label">{{ t('notes', 'Notes') }}</span><span>{{ item.notes }}</span></div>
          <div class="detail-row" v-if="item.converted_order_id"><span class="detail-label">{{ t('converted-to', 'Converted To') }}</span><a class="order-link" @click="router.push(`/sales/${item.converted_order_id}`)">{{ t('view-order', 'View Order') }}</a></div>
        </div>

        <div class="detail-card">
          <h3>{{ t('totals', 'Totals') }}</h3>
          <div class="detail-row"><span class="detail-label">{{ t('subtotal', 'Subtotal') }}</span><span class="col-num">${{ (item.subtotal || 0).toFixed(2) }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ t('tax', 'Tax') }}</span><span class="col-num">${{ (item.tax || 0).toFixed(2) }}</span></div>
          <div class="detail-row total-row"><span class="detail-label">{{ t('grand-total', 'Grand Total') }}</span><span class="col-num">${{ (item.grand_total || 0).toFixed(2) }}</span></div>
        </div>
      </div>

      <div class="data-card" style="margin-top: 20px;">
        <div class="card-head"><h3>{{ t('quote-lines', 'Quote Lines') }}</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>#</th><th>{{ t('product', 'Product') }}</th><th class="col-num">{{ t('qty', 'Qty') }}</th><th class="col-num">{{ t('unit-price', 'Unit Price') }}</th><th class="col-num">{{ t('line-total', 'Total') }}</th></tr></thead>
            <tbody>
              <tr v-for="line in lines" :key="line.id">
                <td>{{ line.line_number || '-' }}</td>
                <td>{{ line.product_name }}</td>
                <td class="col-num">{{ line.qty }}</td>
                <td class="col-num">${{ (line.unit_price || 0).toFixed(2) }}</td>
                <td class="col-num">${{ (line.line_total || 0).toFixed(2) }}</td>
              </tr>
              <tr v-if="!lines.length"><td colspan="5" class="text-center" style="padding: 24px; color: var(--text-faint);">{{ t('no-lines', 'No lines') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const item = ref({})
const lines = ref([])
const customers = ref([])
const converting = ref(false)

const customerName = computed(() => {
  const c = customers.value.find(x => x.id === item.value.customer_id)
  return c ? c.name : `#${item.value.customer_id}`
})

const statusBadge = computed(() => {
  const map = { Draft: 'badge-inactive', Sent: 'badge-info', Accepted: 'badge-active', Rejected: 'badge-danger', Converted: 'badge-active', Cancelled: 'badge-inactive' }
  return map[item.value.status] || 'badge-inactive'
})

async function load() {
  loading.value = true; error.value = ''
  try {
    const id = route.params.id
    const [itemRes, lineRes, custRes] = await Promise.all([
      api.get(`/T0067I/${id}`),
      api.get('/T0068I/'),
      api.get('/T0010I/')
    ])
    item.value = itemRes.data || {}
    customers.value = custRes.data || []
    lines.value = (lineRes.data || []).filter(l => l.quotation_id === parseInt(id))
  } catch { error.value = t('failed-load', 'Failed to load') }
  finally { loading.value = false }
}

async function sendQuote() {
  try {
    const payload = { ...item.value, status: 'Sent' }
    await api.put(`/T0067I/${item.value.id}`, payload)
    toast(t('sent', 'Quotation marked as Sent'), 'success')
    await load()
  } catch { toast(t('failed-save', 'Failed to update'), 'error') }
}

async function convertToOrder() {
  converting.value = true
  try {
    const res = await api.post(`/T0067I/${item.value.id}/convert`)
    const orderId = res.data?.id
    toast(t('converted', 'Converted to order'), 'success')
    router.push(`/sales/${orderId}`)
  } catch { toast(t('failed-convert', 'Conversion failed'), 'error') }
  finally { converting.value = false }
}

onMounted(() => { load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 4px 0 0; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.header-actions { display: flex; gap: 8px; }
.back-link { font-size: 13px; color: var(--color-primary); cursor: pointer; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.detail-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 20px; }
.detail-card h3 { font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 14px; }
.detail-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.detail-label { color: var(--text-muted); }
.total-row { border-top: 1px solid var(--border-default); margin-top: 8px; padding-top: 10px; font-weight: 700; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }
.card-head { padding: 14px 20px; border-bottom: 1px solid var(--border-default); }
.card-head h3 { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.text-center { text-align: center; }
.order-link { color: var(--color-primary); cursor: pointer; text-decoration: none; }
.order-link:hover { text-decoration: underline; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }

@media (max-width: 640px) { .detail-grid { grid-template-columns: 1fr; } }
[dir="rtl"] .detail-row { flex-direction: row-reverse; }
</style>

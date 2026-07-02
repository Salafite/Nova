<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="customer">
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/customers')">&larr; {{ t('back-to-customers') }}</button>
          <h2 class="page-title">{{ customer.name }}</h2>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('customer-info') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('phone') }}:</span><span>{{ customer.phone || '-' }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('email') }}:</span><span>{{ customer.email || '-' }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('group') }}:</span><span>{{ customer.group_name || '-' }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('credit-limit') }}:</span><span>${{ (customer.credit_limit || 0).toFixed(2) }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('balance') }}:</span><span class="col-num" :class="balanceClass">${{ (customer.balance || 0).toFixed(2) }}</span></div>
        </div>
        <div class="detail-card">
          <h3 class="card-title">{{ t('aging-breakdown') }}</h3>
          <div v-if="aging" class="aging-list">
            <div class="aging-row"><span>{{ t('current') }}</span><span class="col-num">${{ aging.current.toFixed(2) }}</span></div>
            <div class="aging-row"><span>1-30 {{ t('days') }}</span><span class="col-num">${{ aging['30'].toFixed(2) }}</span></div>
            <div class="aging-row"><span>31-60 {{ t('days') }}</span><span class="col-num">${{ aging['60'].toFixed(2) }}</span></div>
            <div class="aging-row"><span>61-90+ {{ t('days') }}</span><span class="col-num">${{ aging['90_plus'].toFixed(2) }}</span></div>
            <div class="aging-row total-row"><span>{{ t('total-outstanding') }}</span><span class="col-num">${{ aging.total_outstanding.toFixed(2) }}</span></div>
          </div>
          <div v-else class="empty-state-sm">{{ t('loading') }}...</div>
        </div>
      </div>

      <div class="tabs mt-4">
        <button class="tab" :class="{ active: activeTab === 'invoices' }" @click="activeTab = 'invoices'">{{ t('invoices') }} ({{ invoices.length }})</button>
        <button class="tab" :class="{ active: activeTab === 'payments' }" @click="activeTab = 'payments'">{{ t('payments') }} ({{ payments.length }})</button>
      </div>

      <div v-if="activeTab === 'invoices'" class="data-card mt-2">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('invoice-number') }}</th>
                <th class="col-num">{{ t('amount') }}</th>
                <th>{{ t('issue-date') }}</th>
                <th>{{ t('due-date') }}</th>
                <th class="text-center">{{ t('status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inv in invoices" :key="inv.id">
                <td class="cell-mono">{{ inv.invoice_number }}</td>
                <td class="col-num">${{ (inv.total_amount || 0).toFixed(2) }}</td>
                <td>{{ inv.issue_date }}</td>
                <td>{{ inv.due_date }}</td>
                <td class="text-center">
                  <span class="badge" :class="invStatusBadge(inv.status)">{{ inv.status }}</span>
                </td>
              </tr>
              <tr v-if="!invoices.length"><td colspan="5" class="empty-cell">{{ t('no-records') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'payments'" class="data-card mt-2">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('payment-date') }}</th>
                <th class="col-num">{{ t('amount') }}</th>
                <th>{{ t('payment-method') }}</th>
                <th>{{ t('reference') }}</th>
                <th class="text-center">{{ t('status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pay in payments" :key="pay.id">
                <td>{{ pay.payment_date }}</td>
                <td class="col-num">${{ (pay.amount || 0).toFixed(2) }}</td>
                <td>{{ pay.payment_method }}</td>
                <td class="cell-mono">{{ pay.reference || '-' }}</td>
                <td class="text-center">
                  <span class="badge" :class="pay.status === 'Completed' ? 'badge-active' : 'badge-warning'">{{ pay.status }}</span>
                </td>
              </tr>
              <tr v-if="!payments.length"><td colspan="5" class="empty-cell">{{ t('no-records') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const customer = ref(null)
const aging = ref(null)
const invoices = ref([])
const payments = ref([])
const activeTab = ref('invoices')

const balanceClass = computed(() => {
  const b = customer.value?.balance || 0
  const cl = customer.value?.credit_limit || 0
  if (cl > 0 && b > cl * 0.8) return 'text-danger'
  if (b > 0) return 'text-warning'
  return ''
})

function invStatusBadge(status) {
  const map = { Unpaid: 'badge-warning', Paid: 'badge-active', Overdue: 'badge-danger', Cancelled: 'badge-inactive', Draft: 'badge-info' }
  return map[status] || 'badge-inactive'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [custRes, agingRes, invRes, payRes] = await Promise.all([
      api.get(`/T0010I/${id}`),
      api.get(`/T0010I/${id}/aging`),
      api.get(`/T0010I/${id}/invoices`),
      api.get(`/T0010I/${id}/payments`),
    ])
    customer.value = custRes.data
    aging.value = agingRes.data?.aging || null
    invoices.value = invRes.data || []
    payments.value = payRes.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
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
.empty-cell { text-align: center; color: #999; padding: 24px !important; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.mt-2 { margin-top: 8px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0 0 12px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }
.text-danger { color: #dc2626; }
.text-warning { color: #d97706; }

.aging-list { display: flex; flex-direction: column; gap: 4px; }
.aging-row { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; }
.total-row { border-top: 1px solid #eee; margin-top: 4px; padding-top: 8px; font-weight: 700; }

.tabs { display: flex; gap: 0; border-bottom: 1px solid #e0e0e0; }
.tab { padding: 10px 20px; border: none; background: none; font-size: 13px; font-weight: 600; color: #888; cursor: pointer; border-bottom: 2px solid transparent; }
.tab.active { color: #5d3fd3; border-bottom-color: #5d3fd3; }
.tab:hover { color: #333; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-danger { background: #fee2e2; color: #dc2626; }

[dir="rtl"] .data-table th { text-align: right; }
</style>

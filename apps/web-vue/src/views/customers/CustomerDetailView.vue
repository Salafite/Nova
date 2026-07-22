<template>
  <div class="page" :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="customer">
      <div class="page-head">
        <div>
          <button class="back-link" @click="$router.push('/customers')">
            <span class="material-symbols-outlined">arrow_back</span>
            {{ t('back-to-customers') }}
          </button>
          <h1 class="page-title">{{ customer.name }}</h1>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('customer-info') }}</h3>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">{{ t('phone') }}</span>
              <span class="info-value">{{ customer.phone || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('email') }}</span>
              <span class="info-value">{{ customer.email || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('group') }}</span>
              <span class="info-value">{{ customer.group_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('credit-limit') }}</span>
              <span class="info-value mono">${{ (customer.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('balance') }}</span>
              <span class="info-value mono" :class="balanceClass">${{ (customer.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-card">
          <h3 class="card-title">{{ t('aging-breakdown') }}</h3>
          <div v-if="aging" class="aging-list">
            <div class="aging-row">
              <span class="aging-label">{{ t('current') }}</span>
              <span class="mono">${{ aging.current.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">1–30 {{ t('days') }}</span>
              <span class="mono">${{ aging['30'].toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">31–60 {{ t('days') }}</span>
              <span class="mono">${{ aging['60'].toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">61–90+ {{ t('days') }}</span>
              <span class="mono">${{ aging['90_plus'].toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row total-row">
              <span class="aging-label">{{ t('total-outstanding') }}</span>
              <span class="mono">${{ aging.total_outstanding.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
          <div v-else class="empty-sm">{{ t('loading') }}</div>
        </div>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'invoices' }" @click="activeTab = 'invoices'">{{ t('invoices') }} ({{ invoices.length }})</button>
        <button class="tab" :class="{ active: activeTab === 'payments' }" @click="activeTab = 'payments'">{{ t('payments') }} ({{ payments.length }})</button>
      </div>

      <div v-if="activeTab === 'invoices'" class="data-card">
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
                <td class="col-num cell-mono">${{ (inv.total_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
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

      <div v-if="activeTab === 'payments'" class="data-card">
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
                <td class="col-num cell-mono">${{ (pay.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
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
.page { }
.page-head { margin-bottom: 20px; }
.back-link { display: inline-flex; align-items: center; gap: 4px; background: none; border: none; color: var(--color-primary); font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.back-link:hover { text-decoration: underline; }
.back-link .material-symbols-outlined { font-size: 16px; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; }

.info-rows { display: flex; flex-direction: column; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--text-muted); font-weight: 500; }
.info-value { color: var(--text-primary); font-weight: 600; }

.mono { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.col-num { text-align: right; }
.text-danger { color: var(--color-error); }
.text-warning { color: var(--color-warning, #d97706); }
.text-center { text-align: center; }

.empty-sm { text-align: center; padding: 24px; color: var(--text-faint); font-size: 13px; }
.empty-cell { text-align: center; color: var(--text-faint); padding: 24px !important; }

.aging-list { display: flex; flex-direction: column; }
.aging-row { display: flex; justify-content: space-between; font-size: 13px; padding: 7px 0; border-bottom: 1px solid var(--border-light); }
.aging-row:last-child { border-bottom: none; }
.total-row { border-top: 1px solid var(--border-default); margin-top: 4px; padding-top: 10px; font-weight: 700; }
.aging-label { color: var(--text-muted); }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-default); margin-bottom: 8px; }
.tab { padding: 10px 20px; border: none; background: none; font-size: 13px; font-weight: 600; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; transition: color 0.15s; }
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
.tab:hover { color: var(--text-primary); }

.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 700; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:hover td { background: var(--bg-surface-hover); }
.data-table tr:last-child td { border-bottom: none; }
.cell-mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.col-num { font-family: 'JetBrains Mono', monospace; font-weight: 600; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: var(--color-success); }
.badge-warning { background: #fef3c7; color: var(--color-warning, #d97706); }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-faint); }
.badge-danger { background: #fee2e2; color: var(--color-error); }

@media (max-width: 767px) {
  .detail-grid { grid-template-columns: 1fr; }
  .data-card { border-radius: 0; margin: 0 -16px; border-left: none; border-right: none; }
}

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .back-link .material-symbols-outlined { transform: scaleX(-1); }
</style>

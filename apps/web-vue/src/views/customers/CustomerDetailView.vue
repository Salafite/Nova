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
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="page-title">{{ customer.name }}</h1>
            <span :class="customer.is_active ? 'badge badge-active' : 'badge badge-inactive'">
              {{ customer.is_active ? t('active') : t('inactive') }}
            </span>
            <span v-if="isDelinquent" class="badge badge-danger" :title="t('delinquent-hold', 'Financial Hold Active')">
              <span class="material-symbols-outlined icon-xs">gpp_bad</span>
              {{ t('delinquent-hold', 'Financial Hold') }}
            </span>
            <span v-else-if="isOverLimit" class="badge badge-danger" :title="t('credit-limit-exceeded', 'Credit Limit Exceeded')">
              {{ t('over-limit', 'Over Limit') }}
            </span>
            <span v-else-if="isNearLimit" class="badge badge-warning" :title="t('near-credit-limit', 'Near Credit Limit')">
              {{ t('near-limit', 'Near Limit') }}
            </span>
            <span v-else-if="(customer.credit_limit || 0) > 0" class="badge badge-active" :title="t('good-standing', 'Good Standing')">
              {{ t('good-standing', 'Good Standing') }}
            </span>
            <span v-else class="badge badge-info" :title="t('unlimited-credit', 'Unlimited Credit')">
              {{ t('unlimited-credit', 'Unlimited') }}
            </span>
          </div>
        </div>
      </div>

      <!-- Delinquent Account & Financial Hold Alert Banner -->
      <div v-if="isDelinquent" class="delinquent-banner mb-4">
        <div class="flex items-start gap-3">
          <span class="material-symbols-outlined delinquent-icon">gpp_bad</span>
          <div class="flex-1">
            <div class="flex items-center justify-between flex-wrap gap-2 mb-1">
              <h4 class="delinquent-title">
                {{ t('delinquent-account-alert', 'Delinquent Account & Credit Hold Notice') }}
                <span class="badge badge-danger">{{ t('delinquent-hold', 'Financial Hold Active') }}</span>
              </h4>
              <button
                v-if="creditStatus && creditStatus.hold_orders_count > 0"
                class="btn-sm btn-outline-danger flex items-center gap-1"
                @click="$router.push('/sales')"
              >
                <span class="material-symbols-outlined icon-xs">lock</span>
                {{ creditStatus.hold_orders_count }} {{ t('orders-on-credit-hold-notice', 'order(s) on hold') }}
              </button>
            </div>
            <div v-if="creditStatus && creditStatus.hold_reasons && creditStatus.hold_reasons.length" class="delinquent-reasons">
              <ul class="reason-list">
                <li v-for="(reason, idx) in creditStatus.hold_reasons" :key="idx">
                  {{ reason }}
                </li>
              </ul>
            </div>
            <p class="delinquent-desc">
              {{ t('delinquent-banner-desc', 'Automated credit controls are enforced: New sales orders exceeding credit limits or customers with invoices overdue by >30 days are automatically placed on Credit Hold.') }}
            </p>
          </div>
        </div>
      </div>

      <div class="detail-grid">
        <!-- Customer Info Card -->
        <div class="detail-card">
          <h3 class="card-title">{{ t('customer-info') }}</h3>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">{{ t('phone') }}</span>
              <span class="info-value cell-mono">{{ customer.phone || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('email') }}</span>
              <span class="info-value">{{ customer.email || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('group') }}</span>
              <span class="info-value"><span class="group-tag">{{ customer.group_name || '-' }}</span></span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('status') }}</span>
              <span class="info-value">
                <span :class="customer.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ customer.is_active ? t('active') : t('inactive') }}
                </span>
              </span>
            </div>
          </div>
        </div>

        <!-- Credit Limit & Utilization Card -->
        <div class="detail-card">
          <div class="flex justify-between items-center mb-2">
            <h3 class="card-title mb-0">{{ t('credit-utilization', 'Credit Limit & Utilization') }}</h3>
            <span v-if="isDelinquent" class="badge badge-danger badge-xs">{{ t('credit-risk', 'Credit Risk') }}</span>
            <span v-else-if="isNearLimit" class="badge badge-warning badge-xs">{{ t('near-limit', 'Near Limit') }}</span>
            <span v-else-if="(customer.credit_limit || 0) > 0" class="badge badge-active badge-xs">{{ t('good-standing', 'Good Standing') }}</span>
            <span v-else class="badge badge-info badge-xs">{{ t('unlimited', 'Unlimited') }}</span>
          </div>

          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">{{ t('credit-limit') }}</span>
              <span class="info-value mono">${{ (customer.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('balance') }}</span>
              <span class="info-value mono" :class="balanceClass">${{ (customer.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('available-credit', 'Available Credit') }}</span>
              <span class="info-value mono" :class="availableCredit > 0 ? 'text-success font-bold' : 'text-danger font-bold'">
                ${{ availableCredit.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('overdue-30-days', 'Overdue (>30 Days)') }}</span>
              <span class="info-value mono" :class="(creditStatus?.overdue_invoices_count || 0) > 0 ? 'text-danger font-bold' : 'text-muted'">
                <template v-if="(creditStatus?.overdue_invoices_count || 0) > 0">
                  ${{ (creditStatus.overdue_invoices_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }} ({{ creditStatus.overdue_invoices_count }})
                </template>
                <template v-else>
                  $0.00
                </template>
              </span>
            </div>
          </div>

          <!-- Credit Utilization Progress Bar -->
          <div v-if="(customer.credit_limit || 0) > 0" class="util-container">
            <div class="util-header">
              <span class="util-label">{{ t('credit-utilization', 'Credit Utilization') }}</span>
              <span class="util-pct" :class="utilTextClass">
                {{ actualUtilPct }}%
                <span v-if="isOverLimit" class="badge badge-danger badge-xs ml-1">{{ t('exceeded', 'Exceeded') }}</span>
              </span>
            </div>
            <div class="util-track">
              <div class="util-fill" :class="utilLevel" :style="{ width: utilBarPct + '%' }"></div>
            </div>
            <div class="util-subtext">
              ${{ (customer.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }} {{ t('used-of-limit', 'used of') }} ${{ (customer.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
            </div>
          </div>
          <div v-else class="util-na-box mt-2">
            <span class="util-na">{{ t('unlimited-credit', 'No Limit / Unlimited Credit') }}</span>
          </div>
        </div>

        <!-- Aging Breakdown Card -->
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
            <div class="aging-row" :class="{ 'aging-row-overdue': aging['60'] > 0 }">
              <span class="aging-label flex items-center gap-1">
                31–60 {{ t('days') }}
                <span v-if="aging['60'] > 0" class="badge badge-danger badge-xs" :title="t('hold-trigger-hint', 'Triggers automatic credit hold (>30 days overdue)')">>30d</span>
              </span>
              <span class="mono" :class="aging['60'] > 0 ? 'text-danger font-bold' : ''">${{ aging['60'].toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row" :class="{ 'aging-row-overdue': aging['90_plus'] > 0 }">
              <span class="aging-label flex items-center gap-1">
                61–90+ {{ t('days') }}
                <span v-if="aging['90_plus'] > 0" class="badge badge-danger badge-xs" :title="t('hold-trigger-hint', 'Triggers automatic credit hold (>30 days overdue)')">>30d</span>
              </span>
              <span class="mono" :class="aging['90_plus'] > 0 ? 'text-danger font-bold' : ''">${{ aging['90_plus'].toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="aging-row total-row">
              <span class="aging-label font-bold">{{ t('total-outstanding') }}</span>
              <span class="mono font-bold">${{ aging.total_outstanding.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
          <div v-else class="empty-sm">{{ t('loading') }}</div>
        </div>
      </div>

      <!-- Tabs for Invoices and Payments -->
      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'invoices' }" @click="activeTab = 'invoices'">
          {{ t('invoices') }} ({{ invoices.length }})
          <span v-if="(creditStatus?.overdue_invoices_count || 0) > 0" class="badge badge-danger badge-xs ml-1">
            {{ creditStatus.overdue_invoices_count }} {{ t('overdue', 'Overdue') }}
          </span>
        </button>
        <button class="tab" :class="{ active: activeTab === 'payments' }" @click="activeTab = 'payments'">
          {{ t('payments') }} ({{ payments.length }})
        </button>
      </div>

      <!-- Invoices Tab -->
      <div v-if="activeTab === 'invoices'" class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('invoice-number') }}</th>
                <th class="col-num">{{ t('amount') }}</th>
                <th>{{ t('issue-date') }}</th>
                <th>{{ t('due-date') }}</th>
                <th class="text-center">{{ t('credit-standing', 'Credit Impact') }}</th>
                <th class="text-center">{{ t('status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inv in invoices" :key="inv.id" :class="{ 'row-delinquent': isInvoiceOverdue30(inv) }">
                <td class="cell-mono">
                  <div class="flex items-center gap-2">
                    <span>{{ inv.invoice_number }}</span>
                    <span v-if="isInvoiceOverdue30(inv)" class="badge badge-danger badge-xs" :title="t('invoice-overdue-30-hint', 'Overdue by >30 days — triggers credit hold')">
                      >30d {{ t('overdue', 'Overdue') }}
                    </span>
                  </div>
                </td>
                <td class="col-num cell-mono">${{ (inv.total_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
                <td>{{ inv.issue_date }}</td>
                <td>
                  <span :class="{ 'text-danger font-bold': isInvoiceOverdue30(inv) }">{{ inv.due_date }}</span>
                  <span v-if="isInvoiceOverdue30(inv)" class="text-xs text-danger ml-1">
                    ({{ getInvoiceDaysOverdue(inv) }}d)
                  </span>
                </td>
                <td class="text-center">
                  <span v-if="isInvoiceOverdue30(inv)" class="badge badge-danger badge-xs" :title="t('hold-trigger-hint', 'Triggers automatic credit hold (>30 days overdue)')">
                    {{ t('overdue-hold-threshold', '>30d Hold') }}
                  </span>
                  <span v-else-if="inv.status === 'Paid'" class="badge badge-active badge-xs">
                    {{ t('settled', 'Settled') }}
                  </span>
                  <span v-else class="text-muted text-xs">-</span>
                </td>
                <td class="text-center">
                  <span class="badge" :class="invStatusBadge(inv.status)">{{ inv.status }}</span>
                </td>
              </tr>
              <tr v-if="!invoices.length"><td colspan="6" class="empty-cell">{{ t('no-records') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Payments Tab -->
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
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const customer = ref(null)
const creditStatus = ref(null)
const aging = ref(null)
const invoices = ref([])
const payments = ref([])
const activeTab = ref('invoices')

const isOverLimit = computed(() => {
  if (creditStatus.value) {
    return Boolean(creditStatus.value.credit_limit_exceeded)
  }
  const cl = customer.value?.credit_limit || 0
  const bal = customer.value?.balance || 0
  return cl > 0 && bal > cl
})

const isNearLimit = computed(() => {
  const cl = creditStatus.value?.credit_limit ?? customer.value?.credit_limit ?? 0
  const bal = creditStatus.value?.balance ?? customer.value?.balance ?? 0
  return cl > 0 && !isOverLimit.value && bal >= cl * 0.8
})

const isDelinquent = computed(() => {
  return Boolean(
    creditStatus.value?.is_delinquent ||
    creditStatus.value?.on_hold ||
    creditStatus.value?.credit_limit_exceeded ||
    creditStatus.value?.has_overdue_invoices ||
    isOverLimit.value
  )
})

const actualUtilPct = computed(() => {
  const cl = creditStatus.value?.credit_limit ?? customer.value?.credit_limit ?? 0
  const bal = creditStatus.value?.balance ?? customer.value?.balance ?? 0
  if (cl <= 0) return 0
  return Math.round((bal / cl) * 100)
})

const utilBarPct = computed(() => {
  const cl = creditStatus.value?.credit_limit ?? customer.value?.credit_limit ?? 0
  const bal = creditStatus.value?.balance ?? customer.value?.balance ?? 0
  if (cl <= 0) return 0
  return Math.min(Math.round((bal / cl) * 100), 100)
})

const utilLevel = computed(() => {
  const cl = creditStatus.value?.credit_limit ?? customer.value?.credit_limit ?? 0
  const bal = creditStatus.value?.balance ?? customer.value?.balance ?? 0
  if (cl <= 0) return ''
  const pct = bal / cl
  if (pct >= 1) return 'util-danger'
  if (pct >= 0.8) return 'util-warning'
  return 'util-ok'
})

const utilTextClass = computed(() => {
  const cl = creditStatus.value?.credit_limit ?? customer.value?.credit_limit ?? 0
  const bal = creditStatus.value?.balance ?? customer.value?.balance ?? 0
  if (cl <= 0) return 'text-muted'
  const pct = bal / cl
  if (pct >= 1) return 'text-danger font-bold'
  if (pct >= 0.8) return 'text-warning font-semibold'
  return 'text-success font-semibold'
})

const availableCredit = computed(() => {
  if (creditStatus.value?.available_credit !== undefined) {
    return creditStatus.value.available_credit
  }
  const cl = customer.value?.credit_limit || 0
  const bal = customer.value?.balance || 0
  return cl > 0 ? Math.max(0, cl - bal) : 0
})

const balanceClass = computed(() => {
  const b = customer.value?.balance || 0
  const cl = customer.value?.credit_limit || 0
  if (cl > 0 && b > cl) return 'text-danger font-bold'
  if (cl > 0 && b >= cl * 0.8) return 'text-warning font-semibold'
  if (b > 0) return 'text-warning'
  return ''
})

function isInvoiceOverdue30(inv) {
  if (!inv || inv.status === 'Paid' || inv.status === 'Cancelled') return false
  if (!inv.due_date) return false
  const due = new Date(inv.due_date)
  const today = new Date()
  const diffDays = Math.floor((today - due) / (1000 * 60 * 60 * 24))
  return diffDays > 30
}

function getInvoiceDaysOverdue(inv) {
  if (!inv || !inv.due_date || inv.status === 'Paid' || inv.status === 'Cancelled') return 0
  const due = new Date(inv.due_date)
  const today = new Date()
  const diffDays = Math.floor((today - due) / (1000 * 60 * 60 * 24))
  return Math.max(0, diffDays)
}

function invStatusBadge(status) {
  const map = { Unpaid: 'badge-warning', Paid: 'badge-active', Overdue: 'badge-danger', Cancelled: 'badge-inactive', Draft: 'badge-info' }
  return map[status] || 'badge-inactive'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [custRes, agingRes, invRes, payRes, creditRes] = await Promise.all([
      api.get(`/T0010I/${id}`),
      api.get(`/T0010I/${id}/aging`),
      api.get(`/T0010I/${id}/invoices`),
      api.get(`/T0010I/${id}/payments`),
      api.get(`/T0010I/${id}/credit-status`).catch(() => ({ data: null })),
    ])
    customer.value = custRes.data
    aging.value = agingRes.data?.aging || null
    invoices.value = invRes.data || []
    payments.value = payRes.data || []
    creditStatus.value = creditRes.data || null
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

.delinquent-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left: 4px solid var(--color-error, #ef4444);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.delinquent-icon {
  font-size: 28px;
  color: var(--color-error, #ef4444);
  flex-shrink: 0;
}
.delinquent-title {
  font-size: 15px;
  font-weight: 700;
  color: #991b1b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.delinquent-reasons {
  margin: 8px 0;
}
.reason-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #b91c1c;
}
[dir="rtl"] .reason-list {
  padding-left: 0;
  padding-right: 20px;
}
.reason-list li {
  margin-bottom: 3px;
}
.delinquent-desc {
  font-size: 12px;
  color: #7f1d1d;
  margin: 6px 0 0;
  line-height: 1.4;
}

.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 20px; }
.detail-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; }

.info-rows { display: flex; flex-direction: column; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--text-muted); font-weight: 500; }
.info-value { color: var(--text-primary); font-weight: 600; }

.group-tag { display: inline-block; padding: 2px 8px; background: var(--bg-surface-low); border-radius: 4px; font-size: 12px; color: var(--text-muted); }

.util-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
}
.util-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}
.util-label {
  font-weight: 500;
  color: var(--text-muted);
}
.util-pct {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
}
.util-track {
  width: 100%;
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  overflow: hidden;
}
.util-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.util-fill.util-ok { background: var(--color-success); }
.util-fill.util-warning { background: var(--color-warning, #d97706); }
.util-fill.util-danger { background: var(--color-error); }
.util-subtext {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.util-na-box {
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
}
.util-na {
  font-size: 12px;
  color: var(--text-faint);
}

.aging-list { display: flex; flex-direction: column; }
.aging-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 7px 0; border-bottom: 1px solid var(--border-light); }
.aging-row:last-child { border-bottom: none; }
.aging-row-overdue { background: rgba(239, 68, 68, 0.04); }
.total-row { border-top: 1px solid var(--border-default); margin-top: 4px; padding-top: 10px; font-weight: 700; }
.aging-label { color: var(--text-muted); }

.mono { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.col-num { text-align: right; }
.text-danger { color: var(--color-error); }
.text-warning { color: var(--color-warning, #d97706); }
.text-success { color: var(--color-success); }
.text-muted { color: var(--text-muted); }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.text-center { text-align: center; }

.empty-sm { text-align: center; padding: 24px; color: var(--text-faint); font-size: 13px; }
.empty-cell { text-align: center; color: var(--text-faint); padding: 24px !important; }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-default); margin-bottom: 8px; }
.tab { padding: 10px 20px; border: none; background: none; font-size: 13px; font-weight: 600; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; transition: color 0.15s; display: inline-flex; align-items: center; }
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
.tab:hover { color: var(--text-primary); }

.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 700; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:hover td { background: var(--bg-surface-hover); }
.data-table tr:last-child td { border-bottom: none; }
.row-delinquent { background: rgba(239, 68, 68, 0.04); }
.cell-mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: var(--color-success); }
.badge-warning { background: #fef3c7; color: var(--color-warning, #d97706); }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-faint); }
.badge-danger { background: #fee2e2; color: var(--color-error); }
.badge-xs { padding: 1px 6px; font-size: 10px; line-height: 1.2; border-radius: 4px; }

.icon-xs { font-size: 14px; }
.btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 6px; cursor: pointer; }
.btn-outline-danger { background: transparent; border: 1px solid var(--color-error); color: var(--color-error); }
.btn-outline-danger:hover { background: rgba(239, 68, 68, 0.1); }
.flex { display: flex; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.justify-between { justify-content: space-between; }
.flex-wrap { flex-wrap: wrap; }
.flex-1 { flex: 1; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-4 { margin-bottom: 16px; }
.mt-2 { margin-top: 8px; }
.ml-1 { margin-left: 4px; }
.text-xs { font-size: 12px; }

@media (max-width: 767px) {
  .detail-grid { grid-template-columns: 1fr; }
  .data-card { border-radius: 0; margin: 0 -16px; border-left: none; border-right: none; }
}

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .back-link .material-symbols-outlined { transform: scaleX(-1); }
[dir="rtl"] .ml-1 { margin-left: 0; margin-right: 4px; }
</style>

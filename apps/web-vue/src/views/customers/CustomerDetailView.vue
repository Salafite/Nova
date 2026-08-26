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
        <button class="btn-primary" @click="openEditModal">
          <span class="material-symbols-outlined">edit</span>
          {{ t('edit-customer') }}
        </button>
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
              <span class="info-label">{{ t('payment-terms') }}</span>
              <span class="info-value">{{ paymentTermDisplay }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('credit-limit') }}</span>
              <span class="info-value mono">${{ (customer.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('balance') }}</span>
              <span class="info-value mono" :class="balanceClass">${{ (customer.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div v-if="creditStatus" class="info-row">
              <span class="info-label">Available Credit</span>
              <span class="info-value mono">${{ formatAmount(creditStatus.available_credit || 0) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-card">
          <h3 class="card-title">{{ t('aging-breakdown') }}</h3>
          <div v-if="creditStatus" class="credit-standing-section">
            <div class="credit-standing-row">
              <span class="info-label">Credit Standing</span>
              <span class="badge" :class="creditStanding.class">{{ creditStanding.label }}</span>
            </div>
            <div class="credit-standing-row">
              <span class="info-label">Utilization</span>
              <span class="mono" :class="utilizationClass">{{ creditUtilization }}%</span>
              <span v-if="creditUtilization >= 100" class="badge badge-danger badge-xs">Exceeded</span>
            </div>
            <div class="utilization-bar-wrap">
              <div class="utilization-bar" :class="utilizationClass" :style="{ width: creditUtilization + '%' }"></div>
            </div>
          </div>
          <div v-if="aging" class="aging-list">
            <div class="aging-row">
              <span class="aging-label">{{ t('current') }}</span>
              <span class="mono">${{ formatAmount(aging.current) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">1–30 {{ t('days') }}</span>
              <span class="mono">${{ formatAmount(aging['1_30'] != null ? aging['1_30'] : aging['30']) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">31–60 {{ t('days') }}</span>
              <span class="mono">${{ formatAmount(aging['31_60'] != null ? aging['31_60'] : aging['60']) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">61–90 {{ t('days') }}</span>
              <span class="mono">${{ formatAmount(aging['61_90'] != null ? aging['61_90'] : aging['90']) }}</span>
            </div>
            <div class="aging-row">
              <span class="aging-label">90+ {{ t('days') }}</span>
              <span class="mono">${{ formatAmount(aging['90_plus'] != null ? aging['90_plus'] : (aging['90'] || 0)) }}</span>
            </div>
            <div class="aging-row total-row">
              <span class="aging-label">{{ t('total-outstanding') }}</span>
              <span class="mono">${{ formatAmount(aging.total_outstanding) }}</span>
            </div>
          </div>
          <div v-else class="empty-sm">{{ t('loading') }}</div>
        </div>
      </div>

      <div v-if="creditStatus && creditStatus.on_hold" class="delinquent-banner">
        <div class="banner-header">
          <span class="material-symbols-outlined banner-icon">warning</span>
          <h3>Delinquent Account & Credit Hold Notice</h3>
        </div>
        <div class="banner-body">
          <div v-if="creditStatus.hold_reasons && creditStatus.hold_reasons.length" class="hold-reasons">
            <div v-for="(reason, idx) in creditStatus.hold_reasons" :key="idx" class="hold-reason-item">
              <span class="material-symbols-outlined reason-icon">info</span>
              <span>{{ reason }}</span>
            </div>
          </div>
          <div v-if="creditStatus.hold_orders_count > 0" class="hold-orders-notice">
            <span class="material-symbols-outlined reason-icon">inventory_2</span>
            <span>{{ creditStatus.hold_orders_count }} active sales order(s) currently held</span>
          </div>
        </div>
      </div>

      <div v-if="creditStatus && creditStatus.on_hold" class="data-card overdue-section">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Invoice Number</th>
                <th class="col-num">Amount</th>
                <th>Issue Date</th>
                <th>Due Date</th>
                <th class="text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inv in (creditStatus.overdue_invoices || [])" :key="inv.id">
                <td class="cell-mono">{{ inv.invoice_number }}</td>
                <td class="col-num cell-mono">${{ (inv.total_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
                <td>{{ inv.issue_date }}</td>
                <td>{{ inv.due_date }}</td>
                <td class="text-center">
                  <span class="badge badge-danger">&gt;30d Overdue</span>
                </td>
              </tr>
            </tbody>
          </table>
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

      <!-- Edit Customer Slide Panel -->
      <div v-if="editOpen" class="panel-overlay" :class="{ 'panel-shown': editOpen }" @click.self="closeEditModal"></div>
      <div class="slide-panel" :class="{ 'panel-shown': editOpen }" :dir="dir">
        <div class="panel-header">
          <h3>{{ t('edit-customer') }}</h3>
          <button class="btn-icon" @click="closeEditModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="panel-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('name') }} <span class="required">*</span></label>
              <input type="text" v-model="editForm.name" required class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('customer-group') }}</label>
              <select v-model="editForm.group_name" class="form-input">
                <option value="Retail">Retail</option>
                <option value="Wholesale">Wholesale</option>
                <option value="Corporate">Corporate</option>
                <option value="VIP">VIP</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('customer-phone') }}</label>
              <input type="text" v-model="editForm.phone" class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('customer-email') }}</label>
              <input type="email" v-model="editForm.email" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payment-terms') }}</label>
              <select v-model="editForm.payment_term_id" class="form-input">
                <option :value="null">{{ t('no-term') }}</option>
                <option v-for="pt in paymentTerms" :key="pt.id" :value="pt.id">
                  {{ pt.name }} ({{ pt.due_days }} {{ t('days') }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('customer-credit') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="editForm.credit_limit" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('customer-balance') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="editForm.balance" class="form-input" />
            </div>
            <div class="form-group checkbox-group" style="align-self: center; margin-top: 18px;">
              <label class="checkbox-label">
                <input type="checkbox" v-model="editForm.is_active" />
                <span>{{ t('active') }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="panel-footer">
          <button class="btn-outline" @click="closeEditModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveCustomer">
            {{ saving ? t('saving') : t('save') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const customer = ref(null)
const creditStatus = ref(null)
const aging = ref(null)
const invoices = ref([])
const payments = ref([])
const paymentTerms = ref([])
const activeTab = ref('invoices')

const editOpen = ref(false)
const saving = ref(false)
const editForm = ref({
  name: '',
  group_name: 'Retail',
  phone: '',
  email: '',
  payment_term_id: null,
  credit_limit: 0,
  balance: 0,
  is_active: true,
})

const paymentTermDisplay = computed(() => {
  if (!customer.value?.payment_term_id) return '-'
  const term = paymentTerms.value.find(pt => pt.id === customer.value.payment_term_id)
  if (!term) return `Term #${customer.value.payment_term_id}`
  if (term.discount_percentage > 0 && term.discount_days > 0) {
    return `${term.name} (${term.discount_percentage}% / ${term.discount_days}d, Net ${term.due_days}d)`
  }
  return `${term.name} (Net ${term.due_days}d)`
})

function formatAmount(val) {
  return Number(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const balanceClass = computed(() => {
  const b = customer.value?.balance || 0
  const cl = customer.value?.credit_limit || 0
  if (cl > 0 && b > cl * 0.8) return 'text-danger'
  if (b > 0) return 'text-warning'
  return ''
})

const creditStanding = computed(() => {
  if (!creditStatus.value) return { label: '-', class: '' }
  if (creditStatus.value.on_hold) return { label: 'Financial Hold', class: 'badge-danger' }
  if (creditStatus.value.is_delinquent) return { label: 'Delinquent', class: 'badge-danger' }
  if (creditStatus.value.credit_limit_exceeded) return { label: 'Exceeded', class: 'badge-warning' }
  return { label: 'Good Standing', class: 'badge-active' }
})

const creditUtilization = computed(() => {
  if (!creditStatus.value) return 0
  const cl = creditStatus.value.credit_limit || 0
  const bal = creditStatus.value.balance || 0
  if (cl <= 0) return 0
  return Math.round((bal / cl) * 100)
})

const utilizationClass = computed(() => {
  const pct = creditUtilization.value
  if (pct >= 100) return 'util-exceeded'
  if (pct >= 80) return 'util-warning'
  return 'util-ok'
})

function invStatusBadge(status) {
  const map = { Unpaid: 'badge-warning', Paid: 'badge-active', Overdue: 'badge-danger', Cancelled: 'badge-inactive', Draft: 'badge-info' }
  return map[status] || 'badge-inactive'
}

function openEditModal() {
  if (!customer.value) return
  editForm.value = {
    name: customer.value.name || '',
    group_name: customer.value.group_name || 'Retail',
    phone: customer.value.phone || '',
    email: customer.value.email || '',
    payment_term_id: customer.value.payment_term_id ?? null,
    credit_limit: customer.value.credit_limit || 0,
    balance: customer.value.balance || 0,
    is_active: customer.value.is_active ?? true,
  }
  editOpen.value = true
}

function closeEditModal() {
  editOpen.value = false
}

async function saveCustomer() {
  saving.value = true
  try {
    const payload = {
      ...editForm.value,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
      payment_term_id: editForm.value.payment_term_id ? Number(editForm.value.payment_term_id) : null,
    }
    const res = await api.put(`/T0010I/${customer.value.id}`, payload)
    customer.value = res.data
    toast(t('customer-saved'), 'success')
    closeEditModal()
    await load()
  } catch {
    toast(t('failed-save'), 'error')
  } finally {
    saving.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [custRes, creditRes, agingRes, invRes, payRes, termsRes] = await Promise.all([
      api.get(`/T0010I/${id}`),
      api.get(`/T0010I/${id}/credit-status`).catch(() => ({ data: null })),
      api.get(`/T0010I/${id}/aging`),
      api.get(`/T0010I/${id}/invoices`),
      api.get(`/T0010I/${id}/payments`),
      api.get('/T0096I/').catch(() => ({ data: [] })),
    ])
    customer.value = custRes.data
    creditStatus.value = creditRes.data
    aging.value = agingRes.data?.aging || null
    invoices.value = invRes.data || []
    payments.value = payRes.data || []
    paymentTerms.value = termsRes.data || []
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
.page-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.back-link { display: inline-flex; align-items: center; gap: 4px; background: none; border: none; color: var(--color-primary); font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.back-link:hover { text-decoration: underline; }
.back-link .material-symbols-outlined { font-size: 16px; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--color-primary); color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { padding: 8px 16px; background: transparent; border: 1px solid var(--border-default); border-radius: 8px; font-size: 13px; font-weight: 600; color: var(--text-secondary); cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover); }
.btn-icon { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; display: inline-flex; align-items: center; justify-content: center; border-radius: 6px; }
.btn-icon:hover { color: var(--text-primary); background: var(--bg-surface-hover); }

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

.credit-standing-section { margin-bottom: 16px; }
.credit-standing-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; font-size: 13px; }
.utilization-bar-wrap { height: 6px; background: var(--bg-surface-low); border-radius: 3px; overflow: hidden; margin-top: 4px; }
.utilization-bar { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.util-ok { background: var(--color-success); }
.util-warning { background: var(--color-warning, #d97706); }
.util-exceeded { background: var(--color-error); }

.delinquent-banner { background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.banner-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.banner-icon { color: var(--color-error); font-size: 24px; }
.banner-header h3 { font-size: 15px; font-weight: 700; color: #991b1b; margin: 0; }
.banner-body { display: flex; flex-direction: column; gap: 8px; }
.hold-reasons { display: flex; flex-direction: column; gap: 6px; }
.hold-reason-item { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #7f1d1d; }
.reason-icon { font-size: 16px; color: var(--color-error); flex-shrink: 0; margin-top: 1px; }
.hold-orders-notice { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #7f1d1d; font-weight: 600; }

.overdue-section { margin-bottom: 16px; }

.panel-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }
.panel-overlay.panel-shown { opacity: 1; pointer-events: auto; }

.slide-panel { position: fixed; top: 0; inset-inline-end: 0; width: 480px; height: 100vh; background: var(--bg-surface); z-index: 101; transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1); display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,0.1); }
.slide-panel.panel-shown { transform: translateX(0); }
[dir="rtl"] .slide-panel { transform: translateX(-100%); box-shadow: 4px 0 24px rgba(0,0,0,0.1); }
[dir="rtl"] .slide-panel.panel-shown { transform: translateX(0); }

.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); flex-shrink: 0; }
.panel-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.panel-body { padding: 24px; overflow-y: auto; flex: 1; }
.panel-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border-default); flex-shrink: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; background: var(--bg-surface); color: var(--text-primary); outline: none; }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { cursor: pointer; }
.required { color: var(--color-error); }
.checkbox-group { display: flex; margin-top: 4px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; color: var(--text-primary); }
.checkbox-label input { width: 16px; height: 16px; accent-color: var(--color-primary); }

@media (max-width: 767px) {
  .page-head { flex-direction: column; align-items: flex-start; gap: 12px; }
  .page-head .btn-primary { align-self: stretch; justify-content: center; }
  .detail-grid { grid-template-columns: 1fr; }
  .data-card { border-radius: 0; margin: 0 -16px; border-left: none; border-right: none; }
  .slide-panel { width: 100%; }
  .form-row { grid-template-columns: 1fr; }
}

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .back-link .material-symbols-outlined { transform: scaleX(-1); }
[dir="rtl"] .panel-header { flex-direction: row-reverse; }
</style>

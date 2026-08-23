<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="invoice">
      <!-- Top header & actions -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/finance')">&larr; {{ t('back-to-invoices', 'Back to Invoices') }}</button>
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="page-title">{{ t('invoice', 'Invoice') }} {{ invoice.invoice_number }}</h1>
            <span class="badge" :class="statusBadge">{{ invoice.status }}</span>
            <span v-if="isCatchWeightInvoice" class="badge badge-cw" :title="t('cw-invoice-hint', 'Invoiced based on certified scale weight')">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ t('catch-weight-invoice', 'Catch-Weight / Dual UOM') }}
            </span>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap items-center">
          <button
            v-if="invoice.sales_order_id && invoice.status !== 'Paid'"
            class="btn-outline btn-cw"
            @click="syncWithOrder"
            :disabled="syncing"
            :title="t('sync-order-weights-hint', 'Sync and refresh invoice amounts with sales order scale weights')"
          >
            <span v-if="syncing" class="material-symbols-outlined spin icon-xs">progress_activity</span>
            <span v-else class="material-symbols-outlined icon-xs">refresh</span>
            {{ syncing ? t('syncing', 'Syncing...') : t('sync-weights', 'Refresh Catch-Weight') }}
          </button>
          <button v-if="invoice.status === 'Unpaid'" class="btn-primary" @click="showPayForm = true">
            <span class="material-symbols-outlined icon-xs">payments</span>
            {{ t('record-payment', 'Record Payment') }}
          </button>
        </div>
      </div>

      <!-- Catch-Weight Billing Notice Banner -->
      <div v-if="isCatchWeightInvoice" class="cw-notice-banner mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined cw-banner-icon">scale</span>
          <div class="flex-1">
            <h4 class="cw-banner-title">
              {{ t('cw-billing-notice', 'Dual UOM Physical Scale Weight Billing') }}
              <span v-if="invoice.weight_adjustment_amount !== 0" class="badge" :class="invoice.weight_adjustment_amount >= 0 ? 'badge-adjustment-pos' : 'badge-adjustment-neg'">
                {{ invoice.weight_adjustment_amount >= 0 ? '+' : '' }}${{ Number(invoice.weight_adjustment_amount || 0).toFixed(2) }}
              </span>
            </h4>
            <p class="cw-banner-desc">
              {{ t('cw-invoice-desc', 'This invoice has been calculated from certified physical scale weights rather than nominal package estimates.') }}
              <span v-if="invoice.nominal_total_weight || invoice.actual_total_weight" class="font-medium">
                {{ t('nominal', 'Nominal') }}: {{ formatNumber(invoice.nominal_total_weight) }} kg &rarr;
                {{ t('actual', 'Actual Weighed') }}: {{ formatNumber(invoice.actual_total_weight) }} kg
                <span v-if="weightVariancePct !== null">({{ formatVariance(weightVariancePct) }}%)</span>
              </span>
            </p>
          </div>
        </div>
      </div>

      <!-- Detail Grid: Info & Totals -->
      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('invoice-info', 'Invoice Information') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('invoices-number', 'Invoice #') }}:</span><span class="cell-mono">{{ invoice.invoice_number }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-type', 'Type') }}:</span><span>{{ invoice.invoice_type }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-partner', 'Partner / Customer') }}:</span><span>{{ partnerName }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-issue-date', 'Issue Date') }}:</span><span>{{ invoice.issue_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-due-date', 'Due Date') }}:</span><span>{{ invoice.due_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('status', 'Status') }}:</span><span class="badge" :class="statusBadge">{{ invoice.status }}</span></div>
          <div class="info-row" v-if="invoice.sales_order_id">
            <span class="info-label">{{ t('sales-order', 'Sales Order') }}:</span>
            <a class="order-link flex items-center gap-1" @click="$router.push(`/sales/${invoice.sales_order_id}`)">
              <span>#{{ invoice.sales_order_id }}</span>
              <span class="material-symbols-outlined icon-xs">open_in_new</span>
            </a>
          </div>
          <div v-if="isCatchWeightInvoice" class="info-row">
            <span class="info-label">{{ t('billing-basis', 'Billing Basis') }}:</span>
            <span class="badge badge-cw">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ t('scale-weight-billing', 'Actual Weighed Weight') }}
            </span>
          </div>
          <div class="info-row" v-if="invoice.notes"><span class="info-label">{{ t('notes', 'Notes') }}:</span><span>{{ invoice.notes }}</span></div>
        </div>

        <div class="detail-card">
          <h3 class="card-title">{{ t('payment-summary', 'Payment & Catch-Weight Summary') }}</h3>
          
          <template v-if="isCatchWeightInvoice">
            <div class="info-row">
              <span class="info-label">{{ t('nominal-weight', 'Nominal Weight') }}:</span>
              <span class="col-num text-muted">{{ formatNumber(invoice.nominal_total_weight || cwBreakdown?.nominal_total_weight) }} kg</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('actual-weight', 'Actual Weighed Weight') }}:</span>
              <span class="col-num font-bold text-cw">{{ formatNumber(invoice.actual_total_weight || cwBreakdown?.actual_total_weight) }} kg</span>
            </div>
            <div v-if="weightVariancePct !== null" class="info-row">
              <span class="info-label">{{ t('weight-variance', 'Weight Variance') }}:</span>
              <span class="col-num font-bold" :class="weightVariancePct >= 0 ? 'text-green' : 'text-amber'">
                {{ formatVariance(weightVariancePct) }}%
              </span>
            </div>
            <div v-if="invoice.weight_adjustment_amount !== undefined && invoice.weight_adjustment_amount !== null && invoice.weight_adjustment_amount !== 0" class="info-row cw-adj-row">
              <span class="info-label text-cw font-medium">{{ t('weight-adjustment', 'Weight Adjustment') }}:</span>
              <span class="col-num font-bold" :class="invoice.weight_adjustment_amount >= 0 ? 'text-green' : 'text-danger'">
                {{ invoice.weight_adjustment_amount >= 0 ? '+' : '' }}${{ Number(invoice.weight_adjustment_amount).toFixed(2) }}
              </span>
            </div>
          </template>

          <div class="info-row"><span class="info-label">{{ t('total-amount', 'Total Amount') }}:</span><span class="col-num font-bold">${{ (invoice.total_amount || 0).toFixed(2) }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('amount-paid', 'Amount Paid') }}:</span><span class="col-num text-success">${{ totalPaid.toFixed(2) }}</span></div>
          <div class="info-row total-row">
            <span class="info-label">{{ t('balance-due', 'Balance Due') }}:</span>
            <span class="col-num font-bold" :class="balanceDue > 0 ? 'text-danger' : 'text-success'">${{ balanceDue.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- Itemized Catch-Weight & Sales Line Breakdown (if linked to order) -->
      <div v-if="orderLines.length" class="data-card mt-4">
        <div class="card-header flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 class="card-title">{{ t('itemized-breakdown', 'Itemized Weighed Lines Breakdown') }}</h3>
            <p class="card-subtitle text-xs text-muted" v-if="isCatchWeightInvoice">
              {{ t('itemized-cw-subtitle', 'Detailed scale weights and pricing rates applied per line item.') }}
            </p>
          </div>
          <div v-if="isCatchWeightInvoice" class="flex items-center gap-2">
            <span class="badge badge-cw">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ cwLinesCount }} / {{ orderLines.length }} Weighed Items
            </span>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-8">#</th>
                <th>{{ t('product', 'Product') }}</th>
                <th class="col-num">{{ t('ordered-qty', 'Stocking Qty') }}</th>
                <th>{{ t('pricing-rate', 'Pricing Rate') }}</th>
                <th class="col-num">{{ t('nominal-weight', 'Nominal Weight') }}</th>
                <th class="col-num">{{ t('actual-scale-weight', 'Actual Scale Weight') }}</th>
                <th class="text-center">{{ t('variance', 'Variance') }}</th>
                <th class="col-num">{{ t('line-total', 'Billed Total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in orderLines" :key="line.id" :class="{ 'row-cw': isLineCatchWeight(line) }">
                <td class="cell-mono">{{ line.line_number }}</td>
                <td>
                  <div class="flex items-center gap-2 flex-wrap">
                    <strong>{{ line.product_name || `#${line.product_id}` }}</strong>
                    <span v-if="isLineCatchWeight(line)" class="badge badge-cw">
                      <span class="material-symbols-outlined icon-xs">scale</span>
                      {{ t('catch-weight', 'Catch Weight') }}
                    </span>
                  </div>
                  <div class="text-muted text-xs flex items-center gap-2 mt-1">
                    <span v-if="line.product_id">ID: #{{ line.product_id }}</span>
                    <span v-if="getLineUomName(line)" class="text-secondary">UOM: {{ getLineUomName(line) }}</span>
                  </div>
                </td>
                <td class="col-num font-bold">{{ line.qty }} <span class="text-xs text-muted">{{ getLineUomCode(line) }}</span></td>

                <!-- Pricing Rate -->
                <td>
                  <div v-if="isLineCatchWeight(line) && line.unit_price_pricing_uom">
                    <span class="font-bold text-primary">${{ Number(line.unit_price_pricing_uom).toFixed(2) }}</span>
                    <span class="text-xs text-muted"> / {{ getPricingUomCode(line) }}</span>
                  </div>
                  <div v-else-if="isLineCatchWeight(line)">
                    <span class="font-bold text-primary">${{ Number(line.unit_price || 0).toFixed(2) }}</span>
                    <span class="text-xs text-muted"> / {{ getPricingUomCode(line) }}</span>
                  </div>
                  <div v-else class="text-muted text-xs">
                    ${{ (line.unit_price || 0).toFixed(2) }} / {{ getLineUomCode(line) }}
                  </div>
                </td>

                <!-- Nominal Weight -->
                <td class="col-num">
                  <span v-if="line.nominal_weight !== null && line.nominal_weight !== undefined">
                    {{ formatNumber(line.nominal_weight) }} <span class="text-xs text-muted">{{ getPricingUomCode(line) }}</span>
                  </span>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Actual Weighed Weight -->
                <td class="col-num">
                  <div v-if="line.catch_weight_actual !== null && line.catch_weight_actual !== undefined">
                    <span class="font-bold text-cw">{{ formatNumber(line.catch_weight_actual) }}</span>
                    <span class="text-xs text-muted"> {{ getPricingUomCode(line) }}</span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Weight Variance -->
                <td class="text-center">
                  <div v-if="isLineCatchWeight(line) && getLineVariance(line) !== null">
                    <span class="badge" :class="Math.abs(getLineVariance(line)) <= 10 ? 'badge-tolerance-within' : 'badge-tolerance-out'">
                      {{ formatVariance(getLineVariance(line)) }}%
                    </span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Billed Total -->
                <td class="col-num">
                  <div class="font-bold text-primary">
                    ${{ Number(line.recalculated_total !== null && line.recalculated_total !== undefined ? line.recalculated_total : line.line_total || 0).toFixed(2) }}
                  </div>
                  <div v-if="line.recalculated_total !== null && line.recalculated_total !== undefined && Number(line.recalculated_total) !== Number(line.line_total)" class="text-xs strike-original">
                    ${{ Number(line.line_total || 0).toFixed(2) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Payment History Table -->
      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('payment-history', 'Payment History') }} ({{ payments.length }})</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('payment-date', 'Payment Date') }}</th>
                <th class="col-num">{{ t('amount', 'Amount') }}</th>
                <th>{{ t('payment-method', 'Payment Method') }}</th>
                <th>{{ t('reference', 'Reference') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pay in payments" :key="pay.id">
                <td>{{ pay.payment_date }}</td>
                <td class="col-num font-bold text-success">${{ (pay.amount || 0).toFixed(2) }}</td>
                <td>{{ pay.payment_method }}</td>
                <td class="cell-mono">{{ pay.reference || '-' }}</td>
              </tr>
              <tr v-if="!payments.length"><td colspan="4" class="empty-cell">{{ t('no-payments-recorded', 'No payments recorded') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Record Payment Modal -->
      <div v-if="showPayForm" class="modal-overlay" @click.self="showPayForm = false">
        <div class="modal-content" :dir="dir">
          <div class="modal-header">
            <h3>{{ t('record-payment', 'Record Payment') }}</h3>
            <button class="btn-icon" @click="showPayForm = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('payment-date', 'Payment Date') }} <span class="required">*</span></label>
                <input type="date" v-model="payForm.payment_date" required class="form-input" />
              </div>
              <div class="form-group">
                <label>{{ t('payment-amount', 'Amount') }} <span class="required">*</span></label>
                <input type="number" step="0.01" min="0" v-model.number="payForm.amount" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('payment-method', 'Payment Method') }} <span class="required">*</span></label>
                <select v-model="payForm.payment_method" class="form-input">
                  <option value="Cash">Cash</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="Card">Card</option>
                  <option value="Check">Check</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ t('payment-reference', 'Reference') }}</label>
                <input type="text" v-model="payForm.reference" class="form-input" maxlength="100" />
              </div>
            </div>
            <div class="modal-actions">
              <button class="btn-outline" @click="showPayForm = false">{{ t('cancel', 'Cancel') }}</button>
              <button class="btn-primary" :disabled="saving" @click="savePayment">
                <span v-if="saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                <span v-else class="material-symbols-outlined icon-xs">check</span>
                {{ saving ? t('saving', 'Saving...') : t('save', 'Save Payment') }}
              </button>
            </div>
          </div>
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
const syncing = ref(false)
const error = ref('')
const invoice = ref(null)
const payments = ref([])
const customers = ref([])
const orderLines = ref([])
const cwBreakdown = ref(null)
const uoms = ref([])
const showPayForm = ref(false)
const saving = ref(false)
const payForm = ref({ payment_date: '', amount: 0, payment_method: 'Cash', reference: '' })

const partnerName = computed(() => {
  if (!invoice.value) return `#${invoice.value?.partner_id}`
  const c = customers.value.find(x => x.id === invoice.value.partner_id)
  return c ? c.name : `#${invoice.value.partner_id}`
})

const isCatchWeightInvoice = computed(() => {
  if (!invoice.value) return false
  return Boolean(
    invoice.value.is_catch_weight ||
    invoice.value.nominal_total_weight !== null && invoice.value.nominal_total_weight !== undefined ||
    invoice.value.actual_total_weight !== null && invoice.value.actual_total_weight !== undefined ||
    (invoice.value.weight_adjustment_amount && invoice.value.weight_adjustment_amount !== 0) ||
    cwBreakdown.value?.is_catch_weight
  )
})

const cwLinesCount = computed(() => {
  return orderLines.value.filter(isLineCatchWeight).length
})

const weightVariancePct = computed(() => {
  const nom = invoice.value?.nominal_total_weight || cwBreakdown.value?.nominal_total_weight
  const act = invoice.value?.actual_total_weight || cwBreakdown.value?.actual_total_weight
  if (nom === null || nom === undefined || act === null || act === undefined || nom <= 0) {
    return null
  }
  return Number((((Number(act) - Number(nom)) / Number(nom)) * 100).toFixed(2))
})

const totalPaid = computed(() => payments.value.reduce((s, p) => s + (p.amount || 0), 0))
const balanceDue = computed(() => (invoice.value?.total_amount || 0) - totalPaid.value)

const statusBadge = computed(() => {
  const map = {
    Draft: 'badge-info',
    Unpaid: 'badge-warning',
    Paid: 'badge-active',
    Cancelled: 'badge-inactive',
    Overdue: 'badge-danger'
  }
  return map[invoice.value?.status] || 'badge-inactive'
})

function isLineCatchWeight(line) {
  if (!line) return false
  return Boolean(
    line.is_catch_weight ||
    line.pricing_uom_id !== null && line.pricing_uom_id !== undefined ||
    line.unit_price_pricing_uom !== null && line.unit_price_pricing_uom !== undefined ||
    line.nominal_weight !== null && line.nominal_weight !== undefined ||
    line.catch_weight_actual !== null && line.catch_weight_actual !== undefined
  )
}

function getLineUomCode(line) {
  if (!line || !line.uom_id) return 'units'
  const u = uoms.value.find(x => x.id === line.uom_id)
  return u ? (u.uom_code || u.uom_name) : 'units'
}

function getLineUomName(line) {
  if (!line || !line.uom_id) return ''
  const u = uoms.value.find(x => x.id === line.uom_id)
  return u ? u.uom_name : ''
}

function getPricingUomCode(line) {
  if (!line) return 'kg'
  if (line.pricing_uom_id) {
    const u = uoms.value.find(x => x.id === line.pricing_uom_id)
    if (u) return u.uom_code || u.uom_name
  }
  return 'kg'
}

function formatNumber(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val) || val === '') return '-'
  return Number(val).toFixed(decimals)
}

function formatVariance(val) {
  if (val === null || val === undefined || isNaN(val)) return '0.00'
  const num = Number(val)
  return num > 0 ? `+${num.toFixed(2)}` : num.toFixed(2)
}

function getLineVariance(line) {
  if (!line || line.nominal_weight === null || line.nominal_weight === undefined || line.catch_weight_actual === null || line.catch_weight_actual === undefined) {
    return null
  }
  const nom = Number(line.nominal_weight)
  const act = Number(line.catch_weight_actual)
  if (nom <= 0) return null
  return Number((((act - nom) / nom) * 100).toFixed(2))
}

function today() { return new Date().toISOString().split('T')[0] }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [invRes, payRes, custRes, uomRes] = await Promise.all([
      api.get(`/T0090I/${id}`),
      api.get('/T0091I/', { params: { invoice_id: id } }),
      api.get('/T0010I/'),
      api.get('/T0001I/').catch(() => ({ data: [] })),
    ])
    invoice.value = invRes.data
    payments.value = payRes.data || []
    customers.value = custRes.data || []
    uoms.value = uomRes.data || []
    payForm.value.payment_date = today()
    payForm.value.amount = balanceDue.value > 0 ? balanceDue.value : 0

    // Fetch catch-weight breakdown & order lines if linked to a sales order
    if (invoice.value.sales_order_id) {
      try {
        const [bdRes, linesRes] = await Promise.all([
          api.get(`/T0090I/${id}/catch-weight-breakdown`).catch(() => null),
          api.get('/T0013I/', { params: { sales_order_id: invoice.value.sales_order_id } }).catch(() => ({ data: [] })),
        ])
        if (bdRes?.data) cwBreakdown.value = bdRes.data
        orderLines.value = linesRes.data || cwBreakdown.value?.lines || []
      } catch (err) {
        console.warn('Could not load catch-weight breakdown details:', err)
      }
    }
  } catch {
    error.value = t('failed-load', 'Failed to load invoice')
  } finally {
    loading.value = false
  }
}

async function syncWithOrder() {
  if (!invoice.value?.sales_order_id) return
  syncing.value = true
  try {
    const res = await api.get(`/T0090I/${invoice.value.id}/catch-weight-breakdown`)
    cwBreakdown.value = res.data
    toast(t('weights-synced', 'Catch-weight breakdown refreshed'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Sync failed', 'error')
  } finally {
    syncing.value = false
  }
}

async function savePayment() {
  if (!payForm.value.payment_date || !payForm.value.amount) {
    toast('Please fill all required fields', 'error')
    return
  }
  saving.value = true
  try {
    await api.post('/T0091I/', {
      payment_date: payForm.value.payment_date,
      invoice_id: invoice.value.id,
      partner_id: invoice.value.partner_id,
      amount: payForm.value.amount,
      payment_method: payForm.value.payment_method,
      reference: payForm.value.reference || null,
      status: 'Completed',
    })
    const totalAfter = totalPaid.value + payForm.value.amount
    if (totalAfter >= invoice.value.total_amount) {
      await api.put(`/T0090I/${invoice.value.id}`, { status: 'Paid' })
    }
    toast(t('payment-recorded', 'Payment recorded successfully'), 'success')
    showPayForm.value = false
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Failed to record payment', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-cell { text-align: center; color: #999; padding: 24px !important; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-wrap { flex-wrap: wrap; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.order-link { color: #5d3fd3; cursor: pointer; }
.order-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-cw { color: #0284c7; border-color: #bae6fd; background: #f0f9ff; }
.btn-cw:hover { background: #e0f2fe; }

.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; }

/* Catch-Weight Banner */
.cw-notice-banner { background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px 18px; }
.cw-banner-icon { font-size: 28px; color: #16a34a; }
.cw-banner-title { font-size: 14px; font-weight: 700; color: #14532d; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
.cw-banner-desc { font-size: 12px; color: #166534; margin: 0; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 120px; }
.total-row { border-top: 1px solid #eee; margin-top: 8px; padding-top: 8px; }
.cw-adj-row { background: #f8fafc; padding: 6px 8px; border-radius: 6px; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.strike-original { text-decoration: line-through; color: #94a3b8; }
.text-success { color: #16a34a; }
.text-green { color: #16a34a; }
.text-amber { color: #d97706; }
.text-danger { color: #dc2626; }
.text-primary { color: #5d3fd3; }
.text-cw { color: #0284c7; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.row-cw { background: #fcfdfe; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-cw { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-tolerance-within { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.badge-tolerance-out { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
.badge-adjustment-pos { background: #dcfce7; color: #16a34a; font-family: monospace; }
.badge-adjustment-neg { background: #fee2e2; color: #dc2626; font-family: monospace; }

.icon-xs { font-size: 14px !important; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 500px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
.required { color: #dc2626; }

[dir="rtl"] .data-table th { text-align: right; }
</style>


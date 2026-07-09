<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="invoice">
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/finance')">&larr; {{ t('back-to-invoices') }}</button>
          <h1 class="page-title">{{ t('invoice') }} {{ invoice.invoice_number }}</h1>
        </div>
        <div class="flex gap-2">
          <button v-if="invoice.status === 'Unpaid'" class="btn-primary" @click="showPayForm = true">{{ t('record-payment') }}</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('invoice-info') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('invoices-number') }}:</span><span class="cell-mono">{{ invoice.invoice_number }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-type') }}:</span><span>{{ invoice.invoice_type }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-partner') }}:</span><span>{{ partnerName }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-issue-date') }}:</span><span>{{ invoice.issue_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('invoices-due-date') }}:</span><span>{{ invoice.due_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('status') }}:</span><span class="badge" :class="statusBadge">{{ invoice.status }}</span></div>
          <div class="info-row" v-if="invoice.sales_order_id"><span class="info-label">{{ t('sales-order') }}:</span><a class="order-link" @click="$router.push(`/sales/${invoice.sales_order_id}`)">#{{ invoice.sales_order_id }}</a></div>
          <div class="info-row" v-if="invoice.notes"><span class="info-label">{{ t('notes') }}:</span><span>{{ invoice.notes }}</span></div>
        </div>
        <div class="detail-card">
          <h3 class="card-title">{{ t('payment-summary') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('total-amount') }}:</span><span class="col-num">${{ (invoice.total_amount || 0).toFixed(2) }}</span></div>
          <div class="info-row total-row"><span class="info-label">{{ t('amount-paid') }}:</span><span class="col-num text-success">${{ totalPaid.toFixed(2) }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('balance-due') }}:</span><span class="col-num" :class="balanceDue > 0 ? 'text-danger' : 'text-success'">${{ balanceDue.toFixed(2) }}</span></div>
        </div>
      </div>

      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('payment-history') }} ({{ payments.length }})</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('payment-date') }}</th>
                <th class="col-num">{{ t('amount') }}</th>
                <th>{{ t('payment-method') }}</th>
                <th>{{ t('reference') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pay in payments" :key="pay.id">
                <td>{{ pay.payment_date }}</td>
                <td class="col-num">${{ (pay.amount || 0).toFixed(2) }}</td>
                <td>{{ pay.payment_method }}</td>
                <td class="cell-mono">{{ pay.reference || '-' }}</td>
              </tr>
              <tr v-if="!payments.length"><td colspan="4" class="empty-cell">{{ t('no-payments-recorded') }}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="showPayForm" class="modal-overlay" @click.self="showPayForm = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ t('record-payment') }}</h3>
            <button class="btn-icon" @click="showPayForm = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('payment-date') }} <span class="required">*</span></label>
                <input type="date" v-model="payForm.payment_date" required class="form-input" />
              </div>
              <div class="form-group">
                <label>{{ t('payment-amount') }} <span class="required">*</span></label>
                <input type="number" step="0.01" min="0" v-model.number="payForm.amount" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('payment-method') }} <span class="required">*</span></label>
                <select v-model="payForm.payment_method" class="form-input">
                  <option value="Cash">Cash</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                  <option value="Card">Card</option>
                  <option value="Check">Check</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ t('payment-reference') }}</label>
                <input type="text" v-model="payForm.reference" class="form-input" maxlength="100" />
              </div>
            </div>
            <div class="modal-actions">
              <button class="btn-outline" @click="showPayForm = false">{{ t('cancel') }}</button>
              <button class="btn-primary" :disabled="saving" @click="savePayment">
                {{ saving ? t('saving') : t('save') }}
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
const error = ref('')
const invoice = ref(null)
const payments = ref([])
const customers = ref([])
const showPayForm = ref(false)
const saving = ref(false)
const payForm = ref({ payment_date: '', amount: 0, payment_method: 'Cash', reference: '' })

const partnerName = computed(() => {
  if (!invoice.value) return `#${invoice.value?.partner_id}`
  const c = customers.value.find(x => x.id === invoice.value.partner_id)
  return c ? c.name : `#${invoice.value.partner_id}`
})

const totalPaid = computed(() => payments.value.reduce((s, p) => s + (p.amount || 0), 0))
const balanceDue = computed(() => (invoice.value?.total_amount || 0) - totalPaid.value)

const statusBadge = computed(() => {
  const map = { Draft: 'badge-info', Unpaid: 'badge-warning', Paid: 'badge-active', Cancelled: 'badge-inactive', Overdue: 'badge-danger' }
  return map[invoice.value?.status] || 'badge-inactive'
})

function today() { return new Date().toISOString().split('T')[0] }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [invRes, payRes, custRes] = await Promise.all([
      api.get(`/T0090I/${id}`),
      api.get('/T0091I/', { params: { invoice_id: id } }),
      api.get('/T0010I/'),
    ])
    invoice.value = invRes.data
    payments.value = payRes.data || []
    customers.value = custRes.data || []
    payForm.value.payment_date = today()
    payForm.value.amount = balanceDue.value > 0 ? balanceDue.value : 0
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
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
    toast('Payment recorded', 'success')
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
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.order-link { color: #5d3fd3; cursor: pointer; }
.order-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0 0 12px; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-header .card-title { margin: 0; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 100px; }
.total-row { border-top: 1px solid #eee; margin-top: 8px; padding-top: 8px; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.text-success { color: #16a34a; }
.text-danger { color: #dc2626; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-danger { background: #fee2e2; color: #dc2626; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 500px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
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

<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('payments-title', 'Payments') }}</h1>
        <p class="page-subtitle">{{ t('payments-sub', 'Manage payments, transactions, and reconciliations') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-payment', 'New Payment') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">payments</span>
      <p>{{ t('no-records', 'No records found') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('payment-date', 'Payment Date') }}</th>
              <th>{{ t('payment-partner', 'Partner / Customer') }}</th>
              <th>{{ t('payment-invoice', 'Invoice #') }}</th>
              <th class="col-num">{{ t('payment-amount', 'Amount') }}</th>
              <th>{{ t('payment-method', 'Payment Method') }}</th>
              <th>{{ t('payment-reference', 'Reference') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-mono">{{ item.payment_date }}</td>
              <td>
                <span class="font-medium">{{ getPartnerName(item.partner_id) }}</span>
              </td>
              <td>
                <span v-if="item.invoice_id" class="cell-mono">
                  <a class="inv-link" @click="router.push(`/finance/${item.invoice_id}`)">
                    {{ getInvoiceNumber(item.invoice_id) }}
                  </a>
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="col-num">
                <div class="font-bold text-success">${{ Number(item.amount || 0).toFixed(2) }}</div>
                <div v-if="hasEarlyDiscountNote(item)" class="discount-badge-wrapper mt-1">
                  <span class="badge badge-discount-xs" :title="item.notes">
                    <span class="material-symbols-outlined icon-2xs">savings</span>
                    {{ extractDiscountText(item.notes) }}
                  </span>
                </div>
              </td>
              <td>{{ item.payment_method }}</td>
              <td class="cell-mono">{{ item.reference || '-' }}</td>
              <td class="text-center">
                <span :class="statusBadge(item.status)">{{ item.status }}</span>
              </td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- New / Edit Payment Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content" :dir="dir">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-payment', 'Edit Payment') : t('new-payment', 'New Payment') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <!-- Early Discount Preview Notice in Modal -->
          <div v-if="discountPreview && isDiscountEligible" class="modal-discount-card mb-4">
            <div class="flex items-start gap-3">
              <span class="material-symbols-outlined discount-card-icon">savings</span>
              <div class="flex-1">
                <div class="flex items-center gap-2 flex-wrap mb-1">
                  <h4 class="discount-card-title">{{ t('early-discount-available', 'Early Payment Discount Available') }}</h4>
                  <span class="badge badge-discount-rate">
                    {{ discountPreview.discount_percentage }}% {{ t('early-discount', 'Discount') }}
                  </span>
                  <span v-if="daysLeftForDiscount !== null && daysLeftForDiscount >= 0" class="badge badge-discount-days">
                    <span class="material-symbols-outlined icon-2xs">schedule</span>
                    {{ daysLeftForDiscount === 0 ? t('today', 'Today') : `${daysLeftForDiscount} ${daysLeftForDiscount === 1 ? t('day-left', 'day left') : t('days-left', 'days left')}` }}
                  </span>
                </div>
                <p class="discount-card-desc mb-2">
                  {{ t('early-discount-prompt', 'Pay on or before') }}
                  <strong class="discount-date">{{ discountPreview.discount_due_date || discountPreview.cutoff_date }}</strong>
                  {{ t('to-pay-discounted', 'to pay only') }}
                  <strong class="discount-price">${{ Number(discountPreview.net_amount_due || 0).toFixed(2) }}</strong>
                  {{ t('instead-of', 'instead of') }}
                  <span class="strike">${{ Number(discountPreview.balance_due || discountPreview.invoice_total || 0).toFixed(2) }}</span>
                  <span class="discount-savings font-bold">({{ t('save', 'Save') }} ${{ Number(discountPreview.discount_amount || 0).toFixed(2) }})</span>
                </p>
                <div class="flex gap-2 flex-wrap items-center">
                  <button type="button" class="btn-xs btn-discount" @click="applyDiscountedAmount">
                    <span class="material-symbols-outlined icon-2xs">check_circle</span>
                    {{ t('apply-discounted-balance', 'Apply Discounted Balance') }} (${{ Number(discountPreview.net_amount_due || 0).toFixed(2) }})
                  </button>
                  <button type="button" class="btn-xs btn-outline-muted" @click="applyFullAmount">
                    {{ t('apply-full-balance', 'Apply Full Balance') }} (${{ Number(discountPreview.balance_due || 0).toFixed(2) }})
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Early Discount Expired Notice in Modal -->
          <div v-else-if="discountPreview && isDiscountExpired" class="modal-expired-card mb-4">
            <div class="flex items-start gap-3">
              <span class="material-symbols-outlined expired-card-icon">event_busy</span>
              <div class="flex-1">
                <div class="flex items-center gap-2 flex-wrap mb-1">
                  <h4 class="expired-card-title">{{ t('early-discount-expired', 'Early Discount Window Closed') }}</h4>
                  <span class="badge badge-inactive">{{ discountPreview.discount_percentage }}% {{ t('early-discount', 'Discount') }}</span>
                </div>
                <p class="expired-card-desc mb-2">
                  {{ t('early-discount-window', 'Early discount window closed on') }}
                  <strong>{{ discountPreview.discount_due_date || discountPreview.cutoff_date }}</strong>.
                  {{ t('full-balance-due-by', 'Full invoice amount of') }}
                  <strong>${{ Number(discountPreview.balance_due || 0).toFixed(2) }}</strong>
                  {{ t('is-due-by', 'is due.') }}
                </p>
                <button type="button" class="btn-xs btn-outline-muted" @click="applyFullAmount">
                  {{ t('apply-full-balance', 'Apply Full Balance') }} (${{ Number(discountPreview.balance_due || 0).toFixed(2) }})
                </button>
              </div>
            </div>
          </div>

          <!-- Form Fields -->
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payment-date', 'Payment Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.payment_date" @change="onPaymentDateChange" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('payment-partner', 'Partner / Customer') }} <span class="required">*</span></label>
              <select v-model.number="form.partner_id" @change="onCustomerChange" class="form-input">
                <option :value="null">{{ t('select-customer', '-- Select Customer / Partner --') }}</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">
                  {{ c.name }} (#{{ c.id }})
                </option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payment-invoice', 'Invoice') }}</label>
              <select v-model.number="form.invoice_id" @change="onInvoiceChange" class="form-input">
                <option :value="null">{{ t('no-invoice', 'None (On Account / No Invoice)') }}</option>
                <option v-for="inv in selectableInvoices" :key="inv.id" :value="inv.id">
                  {{ inv.invoice_number }} — ${{ Number(inv.total_amount || 0).toFixed(2) }} ({{ inv.status }}){{ getInvoiceDiscountLabel(inv) }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('payment-reference', 'Reference') }}</label>
              <input type="text" v-model="form.reference" class="form-input" maxlength="100" placeholder="e.g. Wire REF-88301" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payment-amount', 'Amount') }} ($) <span class="required">*</span></label>
              <input type="number" step="0.01" min="0.01" v-model.number="form.amount" class="form-input" />
              <div v-if="discountPreview && isDiscountEligible && form.amount" class="amount-hint text-xs text-green mt-1">
                <span class="material-symbols-outlined icon-2xs">savings</span>
                <span>{{ t('eligible-discount-notice', 'Early payment discount will be applied automatically upon save.') }}</span>
              </div>
            </div>
            <div class="form-group">
              <label>{{ t('payment-method', 'Payment Method') }} <span class="required">*</span></label>
              <select v-model="form.payment_method" class="form-input">
                <option value="Cash">Cash</option>
                <option value="Bank Transfer">Bank Transfer</option>
                <option value="Card">Card</option>
                <option value="Check">Check</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group" :class="editing ? 'full-width' : ''">
              <label>{{ t('notes', 'Notes') }}</label>
              <input type="text" v-model="form.notes" class="form-input" maxlength="255" placeholder="Optional payment notes..." />
            </div>
            <div class="form-group" v-if="!editing">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Completed">Completed</option>
                <option value="Pending">Pending</option>
                <option value="Failed">Failed</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">
              <span v-if="saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
              <span v-else class="material-symbols-outlined icon-xs">check</span>
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm" :dir="dir">
        <div class="modal-header">
          <h3>{{ t('confirm-delete', 'Delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="delete-text">
            {{ t('payment-delete-confirm', 'Delete payment') }} <strong>${{ (deleteTarget?.amount || 0).toFixed(2) }}</strong>?
          </p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
              <span v-if="deleting" class="material-symbols-outlined spin icon-xs">progress_activity</span>
              {{ deleting ? t('deleting', 'Deleting...') : t('delete', 'Delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const items = ref([])
const customers = ref([])
const invoices = ref([])
const paymentTerms = ref([])

const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const editId = ref(null)

const discountPreview = ref(null)

const form = ref({
  payment_date: '',
  partner_id: null,
  amount: 0,
  payment_method: 'Cash',
  invoice_id: null,
  reference: '',
  notes: '',
  status: 'Completed',
})

function today() {
  return new Date().toISOString().split('T')[0]
}

function getPartnerName(partnerId) {
  if (!partnerId) return '-'
  const c = customers.value.find(x => x.id === partnerId)
  return c ? c.name : `#${partnerId}`
}

function getInvoiceNumber(invoiceId) {
  if (!invoiceId) return '-'
  const inv = invoices.value.find(x => x.id === invoiceId)
  return inv ? inv.invoice_number : `#${invoiceId}`
}

function hasEarlyDiscountNote(item) {
  if (!item?.notes) return false
  const n = item.notes.toLowerCase()
  return n.includes('early payment discount') || n.includes('discount applied')
}

function extractDiscountText(notes) {
  if (!notes) return 'Early Discount'
  const match = notes.match(/Early payment discount applied:\s*(\$[\d.]+\s*(?:\([^)]+\))?)/i)
  if (match && match[1]) {
    return match[1]
  }
  return 'Early Discount'
}

function getInvoiceDiscountLabel(inv) {
  if (!inv) return ''
  if (inv.discount_percentage > 0 && inv.discount_due_date) {
    return ` [${inv.discount_percentage}% early discount until ${inv.discount_due_date}]`
  }
  return ''
}

const selectableInvoices = computed(() => {
  if (form.value.partner_id) {
    const custInvs = invoices.value.filter(x => x.partner_id === form.value.partner_id)
    if (custInvs.length) return custInvs
  }
  return invoices.value
})

const isDiscountEligible = computed(() => {
  if (!discountPreview.value) return false
  if (discountPreview.value.is_eligible !== undefined) {
    return Boolean(discountPreview.value.is_eligible && discountPreview.value.discount_amount > 0)
  }
  const cutoff = discountPreview.value.discount_due_date || discountPreview.value.cutoff_date
  if (!cutoff) return false
  const pDate = form.value.payment_date || today()
  return pDate <= cutoff && (discountPreview.value.discount_percentage > 0)
})

const isDiscountExpired = computed(() => {
  if (!discountPreview.value) return false
  const cutoff = discountPreview.value.discount_due_date || discountPreview.value.cutoff_date
  if (!cutoff) return false
  const pDate = form.value.payment_date || today()
  return pDate > cutoff && (discountPreview.value.discount_percentage > 0 || discountPreview.value.early_discount_amount > 0)
})

const daysLeftForDiscount = computed(() => {
  const cutoff = discountPreview.value?.discount_due_date || discountPreview.value?.cutoff_date
  if (!cutoff) return null
  const current = new Date(form.value.payment_date || today())
  const deadline = new Date(cutoff)
  const diffTime = deadline.getTime() - current.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
})

function statusBadge(status) {
  if (status === 'Completed' || status === 'Settled' || status === 'Paid') return 'badge badge-active'
  if (status === 'Pending' || status === 'Failed') return 'badge badge-warning'
  if (status === 'Cancelled') return 'badge badge-inactive'
  return 'badge badge-inactive'
}

async function fetchDiscountPreview() {
  if (!form.value.invoice_id) {
    discountPreview.value = null
    return
  }
  const invoiceId = Number(form.value.invoice_id)
  const pDate = form.value.payment_date || today()
  
  try {
    const res = await api.get(`/T0091I/invoice/${invoiceId}/discount-preview`, {
      params: {
        payment_date: pDate,
        payment_amount: form.value.amount > 0 ? form.value.amount : undefined,
      },
    })
    discountPreview.value = res.data
  } catch (err) {
    // Fallback: calculate discount preview locally from invoice record
    const inv = invoices.value.find(x => x.id === invoiceId)
    if (inv) {
      const invTotal = Number(inv.total_amount || 0)
      const pct = Number(inv.discount_percentage || 0)
      const cutoff = inv.discount_due_date
      const isEligible = cutoff ? pDate <= cutoff : false
      const discAmt = isEligible && pct > 0 ? Number(((invTotal * pct) / 100).toFixed(2)) : 0
      const netDue = Math.max(0, Number((invTotal - discAmt).toFixed(2)))
      
      discountPreview.value = {
        invoice_id: invoiceId,
        invoice_number: inv.invoice_number,
        partner_id: inv.partner_id,
        invoice_total: invTotal,
        balance_due: invTotal,
        discount_percentage: pct,
        discount_due_date: cutoff,
        is_eligible: isEligible,
        discount_amount: discAmt,
        net_amount_due: netDue,
        payment_date: pDate,
      }
    } else {
      discountPreview.value = null
    }
  }
}

async function onInvoiceChange() {
  if (!form.value.invoice_id) {
    discountPreview.value = null
    return
  }
  const inv = invoices.value.find(x => x.id === Number(form.value.invoice_id))
  if (inv && inv.partner_id && !form.value.partner_id) {
    form.value.partner_id = inv.partner_id
  }
  await fetchDiscountPreview()
  if (discountPreview.value) {
    if (isDiscountEligible.value && discountPreview.value.net_amount_due > 0) {
      form.value.amount = discountPreview.value.net_amount_due
    } else if (discountPreview.value.balance_due > 0) {
      form.value.amount = discountPreview.value.balance_due
    }
  }
}

function onCustomerChange() {
  if (form.value.partner_id && form.value.invoice_id) {
    const inv = invoices.value.find(x => x.id === Number(form.value.invoice_id))
    if (inv && inv.partner_id !== form.value.partner_id) {
      form.value.invoice_id = null
      discountPreview.value = null
    }
  }
}

async function onPaymentDateChange() {
  if (form.value.invoice_id) {
    await fetchDiscountPreview()
  }
}

function applyDiscountedAmount() {
  if (discountPreview.value?.net_amount_due !== undefined) {
    form.value.amount = discountPreview.value.net_amount_due
  }
}

function applyFullAmount() {
  if (discountPreview.value?.balance_due !== undefined) {
    form.value.amount = discountPreview.value.balance_due
  } else if (discountPreview.value?.invoice_total !== undefined) {
    form.value.amount = discountPreview.value.invoice_total
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [payRes, custRes, invRes, termsRes] = await Promise.all([
      api.get('/T0091I/'),
      api.get('/T0010I/').catch(() => ({ data: [] })),
      api.get('/T0090I/').catch(() => ({ data: [] })),
      api.get('/T0096I/').catch(() => ({ data: [] })),
    ])
    items.value = payRes.data || []
    customers.value = custRes.data || []
    invoices.value = invRes.data || []
    paymentTerms.value = termsRes.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load data.')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  discountPreview.value = null
  const curDate = today()
  form.value = {
    payment_date: curDate,
    partner_id: null,
    amount: 0,
    payment_method: 'Cash',
    invoice_id: null,
    reference: '',
    notes: '',
    status: 'Completed',
  }
  showModal.value = true
}

async function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    payment_date: item.payment_date,
    partner_id: item.partner_id,
    amount: item.amount,
    payment_method: item.payment_method || 'Cash',
    invoice_id: item.invoice_id ?? null,
    reference: item.reference || '',
    notes: item.notes || '',
    status: item.status || 'Completed',
  }
  showModal.value = true
  if (item.invoice_id) {
    await fetchDiscountPreview()
  } else {
    discountPreview.value = null
  }
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  if (!form.value.payment_date || !form.value.partner_id || !form.value.amount) {
    toast(t('fill-required', 'Please fill all required fields'), 'error')
    return
  }
  saving.value = true
  try {
    const payload = {
      payment_date: form.value.payment_date,
      partner_id: Number(form.value.partner_id),
      invoice_id: form.value.invoice_id ? Number(form.value.invoice_id) : null,
      amount: Number(form.value.amount),
      payment_method: form.value.payment_method,
      reference: form.value.reference ? form.value.reference.trim() : null,
      notes: form.value.notes ? form.value.notes.trim() : null,
      status: form.value.status || 'Completed',
    }
    if (editing.value) {
      await api.put(`/T0091I/${editId.value}`, payload)
      toast('Payment ' + t('saved-ok', 'saved successfully'), 'success')
    } else {
      await api.post('/T0091I/', payload)
      toast('Payment ' + t('saved-ok', 'saved successfully'), 'success')
    }
    closeModal()
    await load()
  } catch (err) {
    toast(err?.response?.data?.detail || t('failed-save', 'Failed to save') + ' Payment', 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  deleteTarget.value = item
  showDelete.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/T0091I/${deleteTarget.value.id}`)
    items.value = items.value.filter(i => i.id !== deleteTarget.value.id)
    toast('Payment deleted', 'success')
    showDelete.value = false
  } catch {
    toast(t('failed-save', 'Failed to save') + ' Payment', 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }

.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }
.inv-link { color: #5d3fd3; cursor: pointer; font-weight: 600; }
.inv-link:hover { text-decoration: underline; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-discount-xs { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 2px 6px; font-size: 10px; font-weight: 600; border-radius: 12px; }
.badge-discount-rate { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.badge-discount-days { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px; }

.discount-badge-wrapper { display: flex; justify-content: flex-end; }
.icon-2xs { font-size: 13px !important; }
.icon-xs { font-size: 16px !important; }

/* Modal Discount Banners */
.modal-discount-card { background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px 16px; }
.discount-card-icon { font-size: 26px; color: #16a34a; }
.discount-card-title { font-size: 13px; font-weight: 700; color: #14532d; margin: 0; }
.discount-card-desc { font-size: 12px; color: #166534; margin: 0; }
.discount-date { color: #15803d; text-decoration: underline; }
.discount-price { color: #15803d; font-size: 13px; }
.discount-savings { color: #16a34a; margin-left: 4px; }

.modal-expired-card { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 14px 16px; }
.expired-card-icon { font-size: 26px; color: #d97706; }
.expired-card-title { font-size: 13px; font-weight: 700; color: #92400e; margin: 0; }
.expired-card-desc { font-size: 12px; color: #b45309; margin: 0; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: #dc2626; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.btn-xs { padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
.btn-discount { background: #16a34a; color: #fff; border: none; }
.btn-discount:hover { background: #15803d; }
.btn-outline-muted { background: #fff; color: #475569; border: 1px solid #cbd5e1; }
.btn-outline-muted:hover { background: #f8fafc; }

.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-wrap { flex-wrap: wrap; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-1 { margin-top: 4px; }

.text-success { color: #16a34a; }
.text-green { color: #16a34a; }
.text-danger { color: #dc2626; }
.text-muted { color: #94a3b8; }
.font-medium { font-weight: 500; }
.font-bold { font-weight: 700; }
.strike { text-decoration: line-through; opacity: 0.65; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 620px; max-width: 90vw; max-height: 88vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.delete-text { font-size: 14px; color: #555; margin: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group.full-width { grid-column: span 2; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
.required { color: #dc2626; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .discount-badge-wrapper { justify-content: flex-start; }
</style>

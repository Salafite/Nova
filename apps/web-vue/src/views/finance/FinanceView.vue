<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('invoices-title') }}</h1>
        <p class="page-subtitle">{{ t('invoices-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-invoice') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">receipt_long</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('invoices-number', 'Invoice #') }}</th>
              <th>{{ t('invoices-type', 'Type') }}</th>
              <th>{{ t('invoices-partner', 'Partner / Customer') }}</th>
              <th>{{ t('payment-terms', 'Payment Terms') }}</th>
              <th>{{ t('invoices-issue-date', 'Issue Date') }}</th>
              <th>{{ t('invoices-due-date', 'Due Date') }}</th>
              <th>{{ t('discount-due-date', 'Discount Deadline') }}</th>
              <th class="col-num">{{ t('invoices-total', 'Total') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-mono"><a class="inv-link" @click="router.push(`/finance/${item.id}`)">{{ item.invoice_number }}</a></td>
              <td><span :class="'inv-type inv-' + item.invoice_type.toLowerCase()">{{ item.invoice_type }}</span></td>
              <td>{{ getPartnerName(item.partner_id) }}</td>
              <td>
                <span class="font-medium text-primary">{{ getPaymentTermName(item.payment_term_id) }}</span>
              </td>
              <td class="cell-mono">{{ item.issue_date }}</td>
              <td class="cell-mono">
                <span :class="isOverdue(item) ? 'text-danger font-bold' : ''">{{ item.due_date }}</span>
              </td>
              <td>
                <div v-if="item.discount_due_date || item.discount_percentage > 0" class="flex items-center gap-1">
                  <span class="cell-mono" :class="isDiscountExpired(item) ? 'strike text-muted' : 'text-success font-medium'">
                    {{ item.discount_due_date || '-' }}
                  </span>
                  <span v-if="item.discount_percentage > 0" class="badge badge-discount-xs">
                    {{ item.discount_percentage }}%
                  </span>
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="col-num">${{ (item.total_amount || 0).toFixed(2) }}</td>
              <td class="text-center">
                <span :class="statusBadge(item.status)">{{ item.status }}</span>
              </td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')" :aria-label="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')" :aria-label="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-invoice', 'Edit Invoice') : t('new-invoice', 'New Invoice') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-number', 'Invoice #') }} <span class="required">*</span></label>
              <input type="text" v-model="form.invoice_number" class="form-input" maxlength="50" />
            </div>
            <div class="form-group">
              <label>{{ t('invoices-type', 'Type') }} <span class="required">*</span></label>
              <select v-model="form.invoice_type" class="form-input">
                <option value="Sales">Sales</option>
                <option value="Purchase">Purchase</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-partner', 'Partner') }} (ID) <span class="required">*</span></label>
              <input type="number" min="1" v-model.number="form.partner_id" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('payment-terms', 'Payment Terms') }}</label>
              <select v-model="form.payment_term_id" @change="onPaymentTermChange" class="form-input">
                <option :value="null">{{ t('no-term', 'None (No Term)') }}</option>
                <option v-for="pt in paymentTerms" :key="pt.id" :value="pt.id">
                  {{ pt.name }} (Net {{ pt.due_days }}d{{ pt.discount_percentage > 0 ? `, ${pt.discount_percentage}% / ${pt.discount_days}d` : '' }})
                </option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-total', 'Total Amount') }} <span class="required">*</span></label>
              <input type="number" step="0.01" min="0" v-model.number="form.total_amount" @input="recalcDiscountAmount" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('invoices-issue-date', 'Issue Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.issue_date" @change="onIssueDateChange" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-due-date', 'Due Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.due_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('discount-due-date', 'Discount Deadline') }}</label>
              <input type="date" v-model="form.discount_due_date" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('discount-percentage', 'Discount %') }}</label>
              <input type="number" step="0.01" min="0" max="100" v-model.number="form.discount_percentage" @input="recalcDiscountAmount" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('early-discount-amount', 'Early Discount Amount') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.early_discount_amount" class="form-input" />
            </div>
          </div>
          <div class="form-row" v-if="!editing">
            <div class="form-group">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Draft">Draft</option>
                <option value="Unpaid">Unpaid</option>
                <option value="Paid">Paid</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">
              {{ saving ? t('saving') : t('save') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="delete-text">{{ t('invoices-delete-confirm') }} <strong>{{ deleteTarget?.invoice_number }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? t('deleting') : t('delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
const paymentTerms = ref([])
const customers = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const editId = ref(null)

const form = ref({
  invoice_number: '',
  invoice_type: 'Sales',
  partner_id: null,
  payment_term_id: null,
  issue_date: '',
  due_date: '',
  discount_due_date: '',
  discount_percentage: 0,
  discount_days: 0,
  early_discount_amount: 0,
  total_amount: 0,
  status: 'Draft'
})

function today() {
  return new Date().toISOString().split('T')[0]
}

function addDays(dateStr, days) {
  if (!dateStr || days === undefined || days === null) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''
  d.setDate(d.getDate() + Number(days))
  return d.toISOString().split('T')[0]
}

function getPartnerName(partnerId) {
  if (!partnerId) return '-'
  const c = customers.value.find(x => x.id === partnerId)
  return c ? c.name : `#${partnerId}`
}

function getPaymentTermName(termId) {
  if (!termId) return '-'
  const term = paymentTerms.value.find(x => x.id === termId)
  return term ? term.name : `#${termId}`
}

function isOverdue(item) {
  if (!item || item.status === 'Paid' || item.status === 'Cancelled' || !item.due_date) return false
  return today() > item.due_date
}

function isDiscountExpired(item) {
  if (!item || item.status === 'Paid' || item.status === 'Cancelled' || !item.discount_due_date) return false
  return today() > item.discount_due_date
}

function statusBadge(status) {
  if (status === 'Paid') return 'badge badge-active'
  if (status === 'Unpaid' || status === 'Draft') return 'badge badge-warning'
  if (status === 'Cancelled') return 'badge badge-inactive'
  return 'badge badge-inactive'
}

function onPaymentTermChange() {
  const issue = form.value.issue_date || today()
  if (!form.value.payment_term_id) {
    if (!form.value.due_date) form.value.due_date = issue
    form.value.discount_due_date = ''
    form.value.discount_percentage = 0
    form.value.discount_days = 0
    form.value.early_discount_amount = 0
    return
  }
  const term = paymentTerms.value.find(p => p.id === form.value.payment_term_id)
  if (term) {
    form.value.due_date = addDays(issue, term.due_days || 0)
    if (term.discount_percentage > 0 && term.discount_days > 0) {
      form.value.discount_due_date = addDays(issue, term.discount_days)
      form.value.discount_percentage = term.discount_percentage
      form.value.discount_days = term.discount_days
      form.value.early_discount_amount = Number(((form.value.total_amount || 0) * (term.discount_percentage / 100)).toFixed(2))
    } else {
      form.value.discount_due_date = ''
      form.value.discount_percentage = 0
      form.value.discount_days = 0
      form.value.early_discount_amount = 0
    }
  }
}

function onIssueDateChange() {
  if (form.value.payment_term_id) {
    onPaymentTermChange()
  }
}

function recalcDiscountAmount() {
  const pct = Number(form.value.discount_percentage || 0)
  const tot = Number(form.value.total_amount || 0)
  if (pct > 0 && tot > 0) {
    form.value.early_discount_amount = Number(((tot * pct) / 100).toFixed(2))
  } else {
    form.value.early_discount_amount = 0
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [invRes, termsRes, custRes] = await Promise.all([
      api.get('/T0090I/'),
      api.get('/T0096I/').catch(() => ({ data: [] })),
      api.get('/T0010I/').catch(() => ({ data: [] }))
    ])
    items.value = invRes.data || []
    paymentTerms.value = termsRes.data || []
    customers.value = custRes.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load invoices')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  const curDate = today()
  form.value = {
    invoice_number: '',
    invoice_type: 'Sales',
    partner_id: null,
    payment_term_id: null,
    issue_date: curDate,
    due_date: curDate,
    discount_due_date: '',
    discount_percentage: 0,
    discount_days: 0,
    early_discount_amount: 0,
    total_amount: 0,
    status: 'Draft'
  }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    invoice_number: item.invoice_number,
    invoice_type: item.invoice_type,
    partner_id: item.partner_id,
    payment_term_id: item.payment_term_id ?? null,
    issue_date: item.issue_date,
    due_date: item.due_date,
    discount_due_date: item.discount_due_date || '',
    discount_percentage: item.discount_percentage || 0,
    discount_days: item.discount_days || 0,
    early_discount_amount: item.early_discount_amount || 0,
    total_amount: item.total_amount,
    status: item.status,
  }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  if (!form.value.invoice_number || !form.value.partner_id || !form.value.issue_date || !form.value.due_date) return
  saving.value = true
  try {
    const payload = {
      ...form.value,
      payment_term_id: form.value.payment_term_id ? Number(form.value.payment_term_id) : null,
      discount_due_date: form.value.discount_due_date || null,
      discount_percentage: Number(form.value.discount_percentage || 0),
      discount_days: Number(form.value.discount_days || 0),
      early_discount_amount: Number(form.value.early_discount_amount || 0),
    }
    if (editing.value) {
      await api.put(`/T0090I/${editId.value}`, payload)
      toast('Invoice ' + t('saved-ok', 'saved successfully'), 'success')
    } else {
      await api.post('/T0090I/', payload)
      toast('Invoice ' + t('saved-ok', 'saved successfully'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save', 'Failed to save') + ' Invoice', 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  deleteTarget.value = item
  showDelete.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await api.delete(`/T0090I/${deleteTarget.value.id}`)
    items.value = items.value.filter(i => i.id !== deleteTarget.value.id)
    toast('Invoice deleted', 'success')
    showDelete.value = false
  } catch {
    toast(t('failed-save', 'Failed to save') + ' Invoice', 'error')
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
.inv-link { color: #5d3fd3; cursor: pointer; font-weight: 600; }
.inv-link:hover { text-decoration: underline; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-discount-xs { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 1px 6px; font-size: 10px; font-weight: 600; border-radius: 12px; }

.inv-type { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.inv-sales { background: #dbeafe; color: #2563eb; }
.inv-purchase { background: #ede9fe; color: #7c3aed; }

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
.mb-6 { margin-bottom: 24px; }
.flex { display: flex; }
.items-center { align-items: center; }
.gap-1 { gap: 4px; }

.text-success { color: #16a34a; }
.text-danger { color: #dc2626; }
.text-primary { color: #5d3fd3; }
.text-muted { color: #94a3b8; }
.font-medium { font-weight: 500; }
.font-bold { font-weight: 700; }
.strike { text-decoration: line-through; opacity: 0.6; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.delete-text { font-size: 14px; color: #555; margin: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
.required { color: #dc2626; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
</style>

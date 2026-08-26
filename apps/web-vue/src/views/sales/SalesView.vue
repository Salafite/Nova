<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('sales-title') }}</h1>
        <p class="page-subtitle">{{ t('sales-sub') }}</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn-outline" @click="router.push('/mobile/field-sales')">
          <span class="material-symbols-outlined">point_of_sale</span> {{ isRTL ? 'مبيعات الميدان' : 'Field Sales' }}
        </button>
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-sales-order') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">payments</span>
      <p>{{ t('no-records') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-sales-order') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('sales-order-number') }}</th>
              <th>{{ t('sales-customer') }}</th>
              <th class="col-num">{{ t('sales-subtotal') }}</th>
              <th class="col-num">{{ t('sales-tax') }}</th>
              <th class="col-num">{{ t('sales-grand-total') }}</th>
              <th class="text-center">{{ t('status') }}</th>
              <th>{{ t('sales-order-date') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-order"><a class="order-link" @click="router.push(`/sales/${item.id}`)">{{ item.order_number }}</a></td>
              <td>{{ customerName(item.customer_id) }}</td>
              <td class="col-num">${{ (item.subtotal || 0).toFixed(2) }}</td>
              <td class="col-num">${{ (item.tax || 0).toFixed(2) }}</td>
              <td class="col-num"><strong>${{ (item.grand_total || 0).toFixed(2) }}</strong></td>
              <td class="text-center">
                <span class="badge" :class="statusBadge(item.status)">{{ item.status }}</span>
              </td>
              <td class="cell-mono">{{ item.order_date }}</td>
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
          <h3>{{ editing ? t('edit-sales-order') : t('new-sales-order') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('sales-order-number') }} <span class="required">*</span></label>
              <input type="text" v-model="form.order_number" required class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('sales-customer') }} <span class="required">*</span></label>
              <select v-model="form.customer_id" required class="form-input" @change="onCustomerChange">
                <option value="">-- Select --</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>

          <!-- Customer Live Credit Standing Panel -->
          <div v-if="form.customer_id" class="credit-status-panel">
            <div v-if="loadingCredit" class="credit-loading">
              <span class="material-symbols-outlined spin icon-xs">progress_activity</span>
              <span>{{ t('credit-status-loading', 'Checking customer credit standing...') }}</span>
            </div>

            <template v-else-if="customerCredit">
              <!-- Overdue invoices banner (>30 days overdue) -->
              <div v-if="customerCredit.has_overdue_invoices" class="credit-alert credit-alert-danger">
                <span class="material-symbols-outlined alert-icon">warning</span>
                <div class="alert-content">
                  <strong>{{ t('credit-hold-status', 'Credit Hold') }}:</strong>
                  <span>
                    {{ t('credit-hold-alert-delinquent', 'Delinquent Account: Customer has overdue invoices (>30 days). Orders will be placed on Credit Hold.') }}
                    ({{ customerCredit.overdue_invoices_count }} {{ customerCredit.overdue_invoices_count === 1 ? 'invoice' : 'invoices' }} &bull; ${{ (customerCredit.overdue_invoices_amount || 0).toFixed(2) }})
                  </span>
                </div>
              </div>

              <!-- Credit Limit Exceeded Banner (if balance already exceeds limit) -->
              <div v-else-if="customerCredit.credit_limit_exceeded" class="credit-alert credit-alert-danger">
                <span class="material-symbols-outlined alert-icon">gpp_bad</span>
                <div class="alert-content">
                  <strong>{{ t('credit-hold-status', 'Credit Hold') }}:</strong>
                  <span>{{ t('credit-hold-alert-limit', 'Credit Limit Exceeded: Current balance exceeds limit. Orders will be placed on Credit Hold.') }}</span>
                </div>
              </div>

              <!-- Exposure warning (if this order pushes balance over limit) -->
              <div v-else-if="willExceedCredit" class="credit-alert credit-alert-warning">
                <span class="material-symbols-outlined alert-icon">priority_high</span>
                <div class="alert-content">
                  <strong>{{ t('credit-warning', 'Approaching Limit') }}:</strong>
                  <span>{{ t('credit-hold-alert-exposure', 'Exposure Warning: Proposed order total will exceed available credit line. Order will enter Credit Hold status.') }}</span>
                </div>
              </div>

              <!-- Good standing banner -->
              <div v-else class="credit-alert credit-alert-healthy">
                <span class="material-symbols-outlined alert-icon">check_circle</span>
                <div class="alert-content">
                  <span>{{ t('credit-healthy', 'Customer credit standing is healthy.') }}</span>
                </div>
              </div>

              <!-- 4-Stat Metric Pill Grid -->
              <div class="credit-metrics-grid">
                <div class="credit-metric-box">
                  <span class="metric-label">{{ t('credit-balance', 'Balance') }}</span>
                  <span class="metric-value font-mono">${{ (customerCredit.balance || 0).toFixed(2) }}</span>
                </div>
                <div class="credit-metric-box">
                  <span class="metric-label">{{ t('credit-limit', 'Credit Limit') }}</span>
                  <span class="metric-value font-mono">
                    {{ customerCredit.is_credit_limit_enforced ? `$${(customerCredit.credit_limit || 0).toFixed(2)}` : t('no-credit-limit', 'No Limit') }}
                  </span>
                </div>
                <div class="credit-metric-box">
                  <span class="metric-label">{{ t('credit-available', 'Available Credit') }}</span>
                  <span class="metric-value font-mono" :class="customerCredit.available_credit > 0 ? 'text-green' : 'text-danger'">
                    ${{ (customerCredit.available_credit || 0).toFixed(2) }}
                  </span>
                </div>
                <div class="credit-metric-box">
                  <span class="metric-label">{{ t('credit-overdue-30', 'Overdue (>30d)') }}</span>
                  <span class="metric-value font-mono" :class="customerCredit.has_overdue_invoices ? 'text-danger font-bold' : 'text-muted'">
                    ${{ (customerCredit.overdue_invoices_amount || 0).toFixed(2) }}
                  </span>
                </div>
              </div>
            </template>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('sales-subtotal') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.subtotal" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('sales-tax') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.tax" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('sales-grand-total') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.grand_total" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Pending">Pending</option>
                <option value="Credit Hold">Credit Hold</option>
                <option value="Confirmed">Confirmed</option>
                <option value="Processing">Processing</option>
                <option value="Shipped">Shipped</option>
                <option value="Delivered">Delivered</option>
                <option value="Cancelled">Cancelled</option>
                <option value="Paid">Paid</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('sales-order-date') }}</label>
            <input type="date" v-model="form.order_date" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('sales-notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2"></textarea>
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
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.order_number" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir, isRTL } = useI18n()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const items = ref([])
const customers = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ order_number: '', customer_id: null, subtotal: 0, tax: 0, grand_total: 0, status: 'Pending', order_date: '', notes: '' })
const editId = ref(null)
const confirmTarget = ref(null)

const customerCredit = ref(null)
const loadingCredit = ref(false)
const creditError = ref('')

const willExceedCredit = computed(() => {
  if (!customerCredit.value || !customerCredit.value.is_credit_limit_enforced) return false
  const orderAmt = Number(form.value.grand_total) || 0
  const balance = Number(customerCredit.value.balance) || 0
  const limit = Number(customerCredit.value.credit_limit) || 0
  return (balance + orderAmt) > limit
})

function statusBadge(status) {
  const map = {
    Pending: 'badge-warning',
    Confirmed: 'badge-info',
    Processing: 'badge-info',
    Shipped: 'badge-active',
    Delivered: 'badge-active',
    Cancelled: 'badge-inactive',
    Paid: 'badge-active',
    'Credit Hold': 'badge-danger',
  }
  return map[status] || 'badge-inactive'
}

function customerName(id) {
  const c = customers.value.find(x => x.id === id)
  return c ? c.name : `#${id}`
}

async function loadCustomers() {
  try {
    const res = await api.get('/T0010I/')
    customers.value = res.data || []
  } catch {}
}

async function fetchCustomerCredit(customerId) {
  if (!customerId) {
    customerCredit.value = null
    creditError.value = ''
    return
  }
  loadingCredit.value = true
  creditError.value = ''
  try {
    const res = await api.get(`/T0010I/${customerId}/credit-status`)
    customerCredit.value = res.data
  } catch (err) {
    customerCredit.value = null
    creditError.value = 'Failed to load customer credit status'
  } finally {
    loadingCredit.value = false
  }
}

function onCustomerChange() {
  if (form.value.customer_id) {
    fetchCustomerCredit(form.value.customer_id)
  } else {
    customerCredit.value = null
  }
}

function today() {
  return new Date().toISOString().split('T')[0]
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [res] = await Promise.all([api.get('/T0012I/')])
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  customerCredit.value = null
  form.value = { order_number: '', customer_id: null, subtotal: 0, tax: 0, grand_total: 0, status: 'Pending', order_date: today(), notes: '' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  customerCredit.value = null
  form.value = {
    order_number: item.order_number,
    customer_id: item.customer_id,
    subtotal: item.subtotal || 0,
    tax: item.tax || 0,
    grand_total: item.grand_total || 0,
    status: item.status || 'Pending',
    order_date: item.order_date || today(),
    notes: item.notes || '',
  }
  if (item.customer_id) {
    fetchCustomerCredit(item.customer_id)
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  customerCredit.value = null
}

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, notes: form.value.notes || null }
    if (editing.value) {
      await api.put(`/T0012I/${editId.value}`, payload)
      toast('Sales Order ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0012I/', payload)
      toast('Sales Order ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Sales Order', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0012I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Sales Order deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Sales Order', 'error')
  }
}

onMounted(() => { loadCustomers(); load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-order { font-family: monospace; font-weight: 600; }
.order-link { color: #5d3fd3; cursor: pointer; text-decoration: none; }
.order-link:hover { text-decoration: underline; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-danger { background: #fee2e2; color: #dc2626; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 620px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
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
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }

/* Credit Status Panel Styles */
.credit-status-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.credit-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  padding: 4px 0;
}
.credit-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 10px;
}
.credit-alert-danger {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}
.credit-alert-warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}
.credit-alert-healthy {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}
.alert-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}
.alert-content {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.4;
}
.credit-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
@media (max-width: 600px) {
  .credit-metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.credit-metric-box {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
}
.metric-label {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.text-green { color: #16a34a; }
.text-danger { color: #dc2626; }
.text-muted { color: #64748b; }
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
</style>

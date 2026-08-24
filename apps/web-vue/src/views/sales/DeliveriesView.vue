<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('deliveries-title', 'Deliveries') }}</h1>
        <p class="page-subtitle">{{ t('deliveries-sub', 'Manage order shipments, scale-weight fulfillment, and deliveries') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined icon-xs">add</span> {{ t('new-delivery', 'New Delivery') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">local_shipping</span>
      <p>{{ t('no-records', 'No records found') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('delivery-number', 'Delivery #') }}</th>
              <th>{{ t('sales-order', 'Sales Order') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th>{{ t('delivery-date', 'Date') }}</th>
              <th>{{ t('warehouse', 'Warehouse') }}</th>
              <th>{{ t('weight-fulfillment', 'Dual UOM & Weighed Fulfillment') }}</th>
              <th>{{ t('notes', 'Notes') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-order">{{ item.delivery_number }}</td>
              <td>
                <div class="flex items-center gap-2 flex-wrap">
                  <a class="order-link font-semibold" @click="$router.push(`/sales/${item.sales_order_id}`)">
                    {{ orderLink(item.sales_order_id) }}
                  </a>
                  <span v-if="isOrderCatchWeight(item.sales_order_id)" class="badge badge-cw" :title="t('cw-order-hint', 'Sales order contains catch-weight items priced by scale weight')">
                    <span class="material-symbols-outlined icon-xs">scale</span>
                    {{ t('catch-weight', 'Catch-Weight') }}
                  </span>
                </div>
              </td>
              <td class="text-center"><span class="badge" :class="statusBadge(item.status)">{{ item.status }}</span></td>
              <td class="cell-mono">{{ item.delivery_date }}</td>
              <td class="cell-mono">{{ warehouseName(item.warehouse_id) }}</td>

              <!-- Dual UOM & Weighed Fulfillment column -->
              <td>
                <div v-if="isOrderCatchWeight(item.sales_order_id)" class="cw-cell">
                  <div v-if="getOrderWeightSummary(item.sales_order_id).actualWeight !== null" class="flex items-center gap-1 flex-wrap">
                    <span class="font-bold text-cw text-xs">
                      {{ formatNumber(getOrderWeightSummary(item.sales_order_id).actualWeight) }} kg
                    </span>
                    <span class="text-muted text-xs">
                      / {{ formatNumber(getOrderWeightSummary(item.sales_order_id).nominalWeight) }} kg
                    </span>
                    <span v-if="getOrderWeightSummary(item.sales_order_id).variance !== null" class="badge text-xs" :class="getOrderWeightSummary(item.sales_order_id).varianceClass">
                      {{ formatVariance(getOrderWeightSummary(item.sales_order_id).variance) }}%
                    </span>
                  </div>
                  <div v-else class="text-xs text-muted flex items-center gap-1">
                    <span class="badge badge-pending-weigh text-xs">{{ t('nominal', 'Nominal') }}: {{ formatNumber(getOrderWeightSummary(item.sales_order_id).nominalWeight) }} kg</span>
                  </div>
                </div>
                <div v-else class="text-muted text-xs">
                  {{ t('standard-fulfillment', 'Standard (Fixed Units)') }}
                </div>
              </td>

              <td class="cell-mono" style="max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ item.notes || '-' }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content" :dir="dir">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-delivery', 'Edit Delivery') : t('new-delivery', 'New Delivery') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('delivery-number', 'Delivery #') }} <span class="required">*</span></label>
              <input type="text" v-model="form.delivery_number" required class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('sales-order', 'Sales Order') }} <span class="required">*</span></label>
              <select v-model="form.sales_order_id" required class="form-input" @change="onOrderSelected">
                <option value="">-- Select --</option>
                <option v-for="o in orders" :key="o.id" :value="o.id">
                  {{ o.order_number }} {{ isOrderCatchWeight(o.id) ? '⚖ (Catch-Weight)' : '' }}
                </option>
              </select>
            </div>
          </div>

          <!-- Catch Weight Information Preview for Selected Order -->
          <div v-if="selectedOrderCatchWeight" class="cw-preview-box mb-3">
            <div class="flex items-center gap-2 mb-1">
              <span class="material-symbols-outlined text-cw icon-xs">scale</span>
              <strong class="text-xs text-cw">{{ t('cw-order-selected', 'Dual UOM Catch-Weight Order') }}</strong>
            </div>
            <p class="text-xs text-muted mb-2">
              {{ t('cw-delivery-hint', 'Delivering this order finalizes scale weights and recalculates customer invoice billing.') }}
            </p>
            <div class="grid-preview text-xs">
              <div><span class="text-muted">{{ t('nominal-weight', 'Nominal Weight') }}:</span> <strong>{{ formatNumber(selectedOrderWeightSummary.nominalWeight) }} kg</strong></div>
              <div>
                <span class="text-muted">{{ t('actual-scale-weight', 'Scale Weight') }}:</span>
                <strong class="text-cw">{{ selectedOrderWeightSummary.actualWeight !== null ? `${formatNumber(selectedOrderWeightSummary.actualWeight)} kg` : t('pending-weighing', 'Pending') }}</strong>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('delivery-date', 'Delivery Date') }}</label>
              <input type="date" v-model="form.delivery_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('warehouse', 'Warehouse') }}</label>
              <select v-model="form.warehouse_id" class="form-input">
                <option value="">-- Select --</option>
                <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name || w.warehouse_name || `#${w.id}` }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('status', 'Status') }}</label>
            <select v-model="form.status" class="form-input">
              <option value="Draft">Draft</option>
              <option value="Shipped">Shipped</option>
              <option value="Delivered">Delivered</option>
              <option value="Cancelled">Cancelled</option>
            </select>
            <span v-if="form.status === 'Delivered' && selectedOrderCatchWeight" class="text-xs text-amber mt-1 block">
              {{ t('delivered-cw-notice', 'Note: Marking status as Delivered will trigger catch-weight invoice generation.') }}
            </span>
          </div>
          <div class="form-group">
            <label>{{ t('notes', 'Notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">
              <span v-if="saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
              <span v-else class="material-symbols-outlined icon-xs">check</span>
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save Delivery') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-if="confirmTarget"
      :title="t('confirm-delete', 'Delete Delivery?')"
      :message="t('confirm-delete-msg', 'Delete delivery') + ' ' + confirmTarget.delivery_number + '?'"
      @confirm="executeDelete"
      @cancel="confirmTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])
const orders = ref([])
const warehouses = ref([])
const salesLines = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ delivery_number: '', sales_order_id: null, delivery_date: '', warehouse_id: null, status: 'Draft', notes: '' })
const editId = ref(null)
const confirmTarget = ref(null)

function statusBadge(status) {
  const map = { Draft: 'badge-inactive', Shipped: 'badge-info', Delivered: 'badge-active', Cancelled: 'badge-inactive' }
  return map[status] || 'badge-inactive'
}

function orderLink(id) {
  const o = orders.value.find(x => x.id === id)
  return o ? o.order_number : `#${id}`
}

function warehouseName(id) {
  if (!id) return '-'
  const w = warehouses.value.find(x => x.id === id)
  return w ? (w.name || w.warehouse_name || `#${id}`) : `#${id}`
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

function isOrderCatchWeight(orderId) {
  if (!orderId) return false
  const order = orders.value.find(o => o.id === orderId)
  if (order?.is_catch_weight) return true
  const lines = salesLines.value.filter(l => l.sales_order_id === orderId)
  return lines.some(l => l.is_catch_weight || l.nominal_weight != null || l.catch_weight_actual != null)
}

function getOrderWeightSummary(orderId) {
  if (!orderId) return { nominalWeight: null, actualWeight: null, variance: null, varianceClass: 'badge-inactive' }
  const lines = salesLines.value.filter(l => l.sales_order_id === orderId && (l.is_catch_weight || l.nominal_weight != null || l.catch_weight_actual != null))
  if (!lines.length) return { nominalWeight: null, actualWeight: null, variance: null, varianceClass: 'badge-inactive' }

  let nom = 0
  let act = 0
  let hasAct = false
  let hasNom = false

  for (const l of lines) {
    if (l.nominal_weight != null) {
      nom += Number(l.nominal_weight)
      hasNom = true
    }
    if (l.catch_weight_actual != null) {
      act += Number(l.catch_weight_actual)
      hasAct = true
    }
  }

  const nominalWeight = hasNom ? nom : null
  const actualWeight = hasAct ? act : null
  let variance = null
  let varianceClass = 'badge-inactive'

  if (nominalWeight && actualWeight && nominalWeight > 0) {
    variance = Number((((actualWeight - nominalWeight) / nominalWeight) * 100).toFixed(2))
    varianceClass = Math.abs(variance) <= 10 ? 'badge-tolerance-within' : 'badge-tolerance-out'
  }

  return { nominalWeight, actualWeight, variance, varianceClass }
}

const selectedOrderCatchWeight = computed(() => {
  return isOrderCatchWeight(form.value.sales_order_id)
})

const selectedOrderWeightSummary = computed(() => {
  return getOrderWeightSummary(form.value.sales_order_id)
})

function onOrderSelected() {
  if (!form.value.sales_order_id) return
  const ord = orders.value.find(o => o.id === form.value.sales_order_id)
  if (ord && ord.warehouse_id && !form.value.warehouse_id) {
    form.value.warehouse_id = ord.warehouse_id
  }
}

function today() { return new Date().toISOString().split('T')[0] }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [delRes, ordRes, whRes, lineRes] = await Promise.all([
      api.get('/T0077I/'),
      api.get('/T0012I/'),
      api.get('/T0008I/'),
      api.get('/T0013I/').catch(() => ({ data: [] })),
    ])
    items.value = delRes.data || []
    orders.value = ordRes.data || []
    warehouses.value = whRes.data || []
    salesLines.value = lineRes.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load deliveries')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  form.value = {
    delivery_number: 'DEL-' + Date.now().toString().slice(-6),
    sales_order_id: orders.value.length ? orders.value[0].id : null,
    delivery_date: today(),
    warehouse_id: warehouses.value.length ? warehouses.value[0].id : null,
    status: 'Draft',
    notes: ''
  }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    delivery_number: item.delivery_number,
    sales_order_id: item.sales_order_id,
    delivery_date: item.delivery_date || today(),
    warehouse_id: item.warehouse_id,
    status: item.status || 'Draft',
    notes: item.notes || ''
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  if (!form.value.delivery_number || !form.value.sales_order_id) {
    toast(t('fill-required', 'Please fill all required fields'), 'error')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form.value,
      notes: form.value.notes || null,
      warehouse_id: form.value.warehouse_id || null
    }
    if (editing.value) {
      await api.put(`/T0077I/${editId.value}`, payload)
      toast(t('saved-ok', 'Delivery saved successfully'), 'success')
    } else {
      await api.post('/T0077I/', payload)
      toast(t('created', 'Delivery created successfully'), 'success')
    }
    closeModal()
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || t('failed-save', 'Failed to save delivery'), 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  confirmTarget.value = item
}

async function executeDelete() {
  const item = confirmTarget.value
  confirmTarget.value = null
  try {
    await api.delete(`/T0077I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast(t('deleted', 'Delivery deleted successfully'), 'success')
  } catch {
    toast(t('failed-save', 'Failed to delete delivery'), 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; margin-bottom: 20px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-order { font-family: monospace; font-weight: 600; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.text-center { text-align: center; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ddd; margin-bottom: 16px; display: block; }
.order-link { color: #5d3fd3; cursor: pointer; }
.order-link:hover { text-decoration: underline; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-cw { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-tolerance-within { background: #dcfce7; color: #15803d; }
.badge-tolerance-out { background: #fee2e2; color: #b91c1c; }
.badge-pending-weigh { background: #fef3c7; color: #b45309; }

.icon-xs { font-size: 14px !important; }
.text-cw { color: #0284c7; }
.text-amber { color: #d97706; }
.block { display: block; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }

.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; background: #fff; color: #1a1a2e; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }

/* Catch Weight Preview Box in Modal */
.cw-preview-box { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 12px; }
.grid-preview { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
</style>


<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('stock-move-title', 'Stock Movements') }}</h2>
        <p class="page-subtitle">{{ t('stock-move-sub', 'View stock movement history across warehouses') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-movement', 'New Movement') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">swap_vert</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('date', 'Date') }}</th>
              <th>Product</th>
              <th>Warehouse</th>
              <th>{{ t('stock-move-type', 'Type') }}</th>
              <th class="text-center">{{ t('stock-qty-change', 'Qty Change') }}</th>
              <th class="text-center">{{ t('stock-balance', 'Balance') }}</th>
              <th>{{ t('description') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="mono">{{ formatDate(item.movement_date) }}</td>
              <td>{{ productName(item.product_id) }}</td>
              <td>{{ warehouseName(item.warehouse_id) }}</td>
              <td><span class="badge" :class="movementBadge(item.movement_type)">{{ item.movement_type }}</span></td>
              <td class="text-center" :class="item.qty_change >= 0 ? 'text-green' : 'text-red'">
                {{ item.qty_change >= 0 ? '+' : '' }}{{ item.qty_change }}
              </td>
              <td class="text-center mono">{{ item.balance_after }}</td>
              <td class="cell-desc">{{ item.description || '-' }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon text-red-500" @click="deleteItem(item)" :title="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-movement', 'Edit Movement') : t('new-movement', 'New Movement') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Product <span class="text-red-500">*</span></label>
            <select v-model="form.product_id" class="form-input">
              <option value="">-- Select --</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.sku }} - {{ p.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Warehouse <span class="text-red-500">*</span></label>
            <select v-model="form.warehouse_id" class="form-input">
              <option value="">-- Select --</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('stock-move-type', 'Movement Type') }}</label>
            <select v-model="form.movement_type" class="form-input">
              <option value="IN">IN - Stock Receipt</option>
              <option value="OUT">OUT - Stock Issue</option>
              <option value="TRANSFER_IN">TRANSFER_IN</option>
              <option value="TRANSFER_OUT">TRANSFER_OUT</option>
              <option value="ADJUSTMENT">ADJUSTMENT</option>
              <option value="RETURN">RETURN</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('stock-qty-change', 'Quantity Change') }} <span class="text-red-500">*</span></label>
            <input type="number" step="0.01" v-model.number="form.qty_change" class="form-input" />
            <small style="color:#888;font-size:11px;">Positive = stock in, Negative = stock out</small>
          </div>
          <div class="form-group">
            <label>{{ t('description') }}</label>
            <input type="text" v-model="form.description" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('stock-move-ref', 'Reference Type') }}</label>
            <input type="text" v-model="form.reference_type" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('stock-move-ref-id', 'Reference ID') }}</label>
            <input type="number" v-model.number="form.reference_id" class="form-input" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveItem">
            {{ saving ? t('saving') : t('save') }}
          </button>
        </div>
      </div>
    </div>
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + (confirmTarget.description || confirmTarget.id)" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
const products = ref([])
const warehouses = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ product_id: null, warehouse_id: null, movement_type: 'IN', qty_change: 0, description: '', reference_type: '', reference_id: null })
const editId = ref(null)
const confirmTarget = ref(null)

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function productName(id) {
  const p = products.value.find(x => x.id === id)
  return p ? p.name : `#${id}`
}

function warehouseName(id) {
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : `#${id}`
}

function movementBadge(type) {
  if (type === 'IN' || type === 'TRANSFER_IN' || type === 'RETURN') return 'badge-active'
  if (type === 'OUT' || type === 'TRANSFER_OUT') return 'badge-danger'
  return 'badge-disabled'
}

async function loadLookups() {
  try {
    const [pRes, wRes] = await Promise.all([
      api.get('/T0003I/'),
      api.get('/T0008I/').catch(() => ({ data: [] })),
    ])
    products.value = pRes.data || []
    warehouses.value = wRes.data || []
  } catch {}
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0064I/')
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
  form.value = { product_id: null, warehouse_id: null, movement_type: 'IN', qty_change: 0, description: '', reference_type: '', reference_id: null }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    product_id: item.product_id,
    warehouse_id: item.warehouse_id,
    movement_type: item.movement_type,
    qty_change: item.qty_change,
    description: item.description || '',
    reference_type: item.reference_type || '',
    reference_id: item.reference_id,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      reference_type: form.value.reference_type || null,
      reference_id: form.value.reference_id || null,
      description: form.value.description || null,
    }
    if (editing.value) {
      await api.put(`/T0064I/${editId.value}`, payload)
      toast('Movement ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0064I/', payload)
      toast('Movement ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Movement', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0064I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Movement deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Movement', 'error')
  }
}

onMounted(() => { loadLookups(); load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.text-red-500 { color: #e53935; }
.text-green { color: #16a34a; font-weight: 600; }
.text-red { color: #dc2626; font-weight: 600; }
.cell-desc { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #666; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-disabled { background: #f5f5f5; color: #999; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #f0f0f4; color: #333; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-secondary:hover { background: #e0e0e0; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; transition: all 0.15s; color: #666; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal { background: #fff; border-radius: 12px; width: 520px; max-width: 90vw; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid #eee; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; transition: border-color 0.15s; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
</style>

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('price-lists-title', 'Price Lists') }}</h2>
        <p class="page-subtitle">{{ t('price-lists-sub', 'Manage pricing tiers and product prices') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-price-list', 'New Price List') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">price_change</span>
      <p>{{ t('no-records', 'No records found') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('code', 'Code') }}</th>
              <th>{{ t('name', 'Name') }}</th>
              <th>{{ t('currency', 'Currency') }}</th>
              <th class="text-center">{{ t('default', 'Default') }}</th>
              <th class="text-center">{{ t('active', 'Active') }}</th>
              <th>{{ t('description', 'Description') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" @click="selectItem(item)" :class="{ 'row-selected': selectedId === item.id }">
              <td class="cell-mono">{{ item.code }}</td>
              <td class="cell-name">{{ item.name }}</td>
              <td>{{ item.currency }}</td>
              <td class="text-center"><span v-if="item.is_default" class="material-symbols-outlined" style="color: var(--color-primary);">star</span></td>
              <td class="text-center"><span class="badge" :class="item.is_active ? 'badge-active' : 'badge-inactive'">{{ item.is_active ? t('yes', 'Yes') : t('no', 'No') }}</span></td>
              <td class="cell-mono" style="max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ item.description || '-' }}</td>
              <td class="text-center">
                <button class="btn-icon" @click.stop="editItem(item)" :title="t('edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click.stop="deleteItem(item)" :title="t('delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-price-list', 'Edit Price List') : t('new-price-list', 'New Price List') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('code', 'Code') }} <span class="required">*</span></label>
            <input type="text" v-model="form.code" required class="form-input" maxlength="20" />
          </div>
          <div class="form-group">
            <label>{{ t('name', 'Name') }} <span class="required">*</span></label>
            <input type="text" v-model="form.name" required class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('currency', 'Currency') }}</label>
            <input type="text" v-model="form.currency" class="form-input" maxlength="3" />
          </div>
          <div class="form-group">
            <label>{{ t('description', 'Description') }}</label>
            <textarea v-model="form.description" class="form-input" rows="2"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="checkbox-label"><input type="checkbox" v-model="form.is_active" /> {{ t('active', 'Active') }}</label>
            </div>
            <div class="form-group">
              <label class="checkbox-label"><input type="checkbox" v-model="form.is_default" /> {{ t('default', 'Default') }}</label>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectedItems.length && !showModal" class="data-card" style="margin-top: 20px;">
      <div class="card-head">
        <h3>{{ t('price-items', 'Price Items') }} — {{ selectedName }}</h3>
        <button class="btn-primary btn-xs" @click="openAddItem"><span class="material-symbols-outlined">add</span> {{ t('add-item', 'Add Item') }}</button>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>{{ t('product', 'Product') }}</th><th class="col-num">{{ t('unit-price', 'Unit Price') }}</th><th class="col-num">{{ t('min-qty', 'Min Qty') }}</th><th>{{ t('effective-from', 'From') }}</th><th>{{ t('effective-to', 'To') }}</th><th class="text-center">{{ t('actions', 'Actions') }}</th></tr></thead>
          <tbody>
            <tr v-for="line in selectedItems" :key="line.id">
              <td>{{ productName(line.product_id) }}</td>
              <td class="col-num">${{ (line.unit_price || 0).toFixed(2) }}</td>
              <td class="col-num">{{ line.min_qty || 1 }}</td>
              <td class="cell-mono">{{ line.effective_from || '-' }}</td>
              <td class="cell-mono">{{ line.effective_to || '-' }}</td>
              <td class="text-center"><button class="btn-icon btn-icon-danger" @click="deleteItemLine(line)" :title="t('delete')"><span class="material-symbols-outlined">delete</span></button></td>
            </tr>
            <tr v-if="!selectedItems.length"><td colspan="6" class="text-center" style="padding: 24px; color: var(--text-faint);">{{ t('no-items', 'No items') }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showItemModal" class="modal-overlay" @click.self="showItemModal = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('add-item', 'Add Price Item') }}</h3>
          <button class="btn-icon" @click="showItemModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('product', 'Product') }} <span class="required">*</span></label>
            <select v-model="itemForm.product_id" required class="form-input">
              <option value="">-- Select --</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name || p.product_name || `#${p.id}` }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('unit-price', 'Unit Price') }} <span class="required">*</span></label>
            <input type="number" step="0.01" min="0" v-model.number="itemForm.unit_price" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('min-qty', 'Min Qty') }}</label>
              <input type="number" min="1" v-model.number="itemForm.min_qty" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('uom', 'UOM') }}</label>
              <select v-model="itemForm.uom_id" class="form-input">
                <option value="">--</option>
                <option v-for="u in uoms" :key="u.id" :value="u.id">{{ u.name || u.uom_name || `#${u.id}` }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('effective-from', 'From') }}</label>
              <input type="date" v-model="itemForm.effective_from" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('effective-to', 'To') }}</label>
              <input type="date" v-model="itemForm.effective_to" class="form-input" />
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showItemModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="savingItem" @click="saveItemLine">{{ savingItem ? t('saving', 'Saving...') : t('save', 'Save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete?')" :message="t('confirm-delete-msg', 'Delete') + ' ' + confirmTarget.name + '?'" @confirm="executeDelete" @cancel="confirmTarget = null" />
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
const selectedItems = ref([])
const selectedId = ref(null)
const selectedName = ref('')
const products = ref([])
const uoms = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showItemModal = ref(false)
const savingItem = ref(false)
const form = ref({ code: '', name: '', currency: 'USD', description: '', is_active: true, is_default: false })
const itemForm = ref({ product_id: null, unit_price: 0, min_qty: 1, uom_id: null, effective_from: '', effective_to: '' })
const editId = ref(null)
const confirmTarget = ref(null)

async function load() {
  loading.value = true; error.value = ''
  try {
    const [plRes, prodRes, uomRes] = await Promise.all([
      api.get('/T0083I/'),
      api.get('/T0003I/'),
      api.get('/T0001I/')
    ])
    items.value = plRes.data || []
    products.value = prodRes.data || []
    uoms.value = uomRes.data || []
  } catch { error.value = t('failed-load', 'Failed to load') }
  finally { loading.value = false }
}

function productName(id) {
  const p = products.value.find(x => x.id === id)
  return p ? (p.name || p.product_name || `#${id}`) : `#${id}`
}

async function selectItem(item) {
  selectedId.value = item.id
  selectedName.value = item.name
  try {
    const res = await api.get('/T0084I/')
    selectedItems.value = (res.data || []).filter(l => l.price_list_id === item.id)
  } catch { selectedItems.value = [] }
}

function openAdd() {
  editing.value = false; editId.value = null
  form.value = { code: '', name: '', currency: 'USD', description: '', is_active: true, is_default: false }
  showModal.value = true
}

function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = { code: item.code, name: item.name, currency: item.currency || 'USD', description: item.description || '', is_active: item.is_active, is_default: item.is_default }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, description: form.value.description || null }
    if (editing.value) { await api.put(`/T0083I/${editId.value}`, payload); toast(t('saved-ok', 'Saved'), 'success') }
    else { await api.post('/T0083I/', payload); toast(t('created', 'Created'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save', 'Failed to save'), 'error') }
  finally { saving.value = false }
}

function openAddItem() {
  itemForm.value = { product_id: null, unit_price: 0, min_qty: 1, uom_id: null, effective_from: '', effective_to: '' }
  showItemModal.value = true
}

async function saveItemLine() {
  savingItem.value = true
  try {
    const payload = {
      price_list_id: selectedId.value,
      product_id: itemForm.value.product_id,
      unit_price: itemForm.value.unit_price,
      min_qty: itemForm.value.min_qty || 1,
      uom_id: itemForm.value.uom_id || null,
      effective_from: itemForm.value.effective_from || null,
      effective_to: itemForm.value.effective_to || null
    }
    await api.post('/T0084I/', payload)
    toast(t('created', 'Created'), 'success')
    showItemModal.value = false
    await selectItem(items.value.find(i => i.id === selectedId.value))
  } catch { toast(t('failed-save', 'Failed to save'), 'error') }
  finally { savingItem.value = false }
}

async function deleteItemLine(line) {
  try { await api.delete(`/T0084I/${line.id}`); selectedItems.value = selectedItems.value.filter(l => l.id !== line.id); toast(t('deleted', 'Deleted'), 'success') }
  catch { toast(t('failed-save', 'Failed to delete'), 'error') }
}

function deleteItem(item) { confirmTarget.value = item }
async function executeDelete() {
  const item = confirmTarget.value; confirmTarget.value = null
  try { await api.delete(`/T0083I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); if (selectedId.value === item.id) { selectedId.value = null; selectedItems.value = [] }; toast(t('deleted', 'Deleted'), 'success') }
  catch { toast(t('failed-save', 'Failed to delete'), 'error') }
}

onMounted(() => { load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; margin-bottom: 20px; }
.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.card-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; border-bottom: 1px solid var(--border-default); }
.card-head h3 { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr { cursor: pointer; transition: background 0.1s; }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }
.data-table tbody tr.row-selected { background: var(--bg-primary-faded); }
.cell-name { font-weight: 600; color: var(--text-primary); }
.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-subtle); }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.text-center { text-align: center; }
.empty-state { text-align: center; padding: 48px; color: var(--text-faint); font-size: 14px; }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 16px; display: block; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-secondary); }
.checkbox-label input { width: 16px; height: 16px; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
[dir="rtl"] .card-head { flex-direction: row-reverse; }
</style>

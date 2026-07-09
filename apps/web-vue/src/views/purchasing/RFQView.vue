<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('rfq-title', 'Requests for Quotation') }}</h1>
        <p class="page-subtitle">{{ t('rfq-sub', 'Manage RFQs and vendor quotes') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-rfq', 'New RFQ') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">request_quote</span>
      <p>{{ t('no-records', 'No records found') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-rfq', 'New RFQ') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('rfq-number', 'RFQ #') }}</th>
              <th>{{ t('supplier', 'Supplier') }}</th>
              <th>{{ t('rfq-date', 'Date') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="col-num">{{ t('total', 'Total') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-order">{{ item.rfq_number || item.number }}</td>
              <td>{{ supplierName(item.supplier_id) }}</td>
              <td class="cell-mono">{{ item.rfq_date || item.date }}</td>
              <td class="text-center"><span class="badge" :class="statusBadge(item.status)">{{ item.status }}</span></td>
              <td class="col-num"><strong>${{ (item.total || 0).toFixed(2) }}</strong></td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')" :aria-label="t('edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')" :aria-label="t('delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-rfq', 'Edit RFQ') : t('new-rfq', 'New RFQ') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('rfq-number', 'RFQ #') }} <span class="required">*</span></label>
              <input type="text" v-model="form.rfq_number" required class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier', 'Supplier') }} <span class="required">*</span></label>
              <select v-model="form.supplier_id" required class="form-input">
                <option value="">-- {{ t('select', 'Select') }} --</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('rfq-date', 'RFQ Date') }}</label>
              <input type="date" v-model="form.rfq_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Open">Open</option>
                <option value="Sent">Sent</option>
                <option value="Received">Received</option>
                <option value="Closed">Closed</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('total', 'Total') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.total" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('notes', 'Notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete?')" :message="t('confirm-delete-msg', 'Delete') + ' ' + (confirmTarget.rfq_number || confirmTarget.number) + '?'" @confirm="executeDelete" @cancel="confirmTarget = null" />
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
const suppliers = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ rfq_number: '', supplier_id: null, rfq_date: '', status: 'Open', total: 0, notes: '' })
const editId = ref(null)
const confirmTarget = ref(null)

function statusBadge(status) {
  const map = { Open: 'badge-info', Sent: 'badge-warning', Received: 'badge-active', Closed: 'badge-inactive' }
  return map[status] || 'badge-inactive'
}

function supplierName(id) {
  const s = suppliers.value.find(x => x.id === id)
  return s ? s.name : `#${id}`
}

function today() { return new Date().toISOString().split('T')[0] }

async function loadSuppliers() {
  try { const res = await api.get('/T0011I/'); suppliers.value = res.data || [] } catch {}
}

async function load() {
  loading.value = true; error.value = ''
  try {
    const res = await api.get('/T0071I/')
    items.value = res.data || []
  } catch { error.value = t('failed-load', 'Failed to load') }
  finally { loading.value = false }
}

function openAdd() {
  editing.value = false; editId.value = null
  form.value = { rfq_number: '', supplier_id: null, rfq_date: today(), status: 'Open', total: 0, notes: '' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = {
    rfq_number: item.rfq_number || item.number || '',
    supplier_id: item.supplier_id,
    rfq_date: item.rfq_date || item.date || today(),
    status: item.status || 'Open',
    total: item.total || 0,
    notes: item.notes || '',
  }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, notes: form.value.notes || null }
    if (editing.value) { await api.put(`/T0071I/${editId.value}`, payload); toast(t('saved-ok', 'Saved'), 'success') }
    else { await api.post('/T0071I/', payload); toast(t('created', 'Created'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save', 'Failed to save'), 'error') }
  finally { saving.value = false }
}

function deleteItem(item) { confirmTarget.value = item }
async function executeDelete() {
  const item = confirmTarget.value; confirmTarget.value = null
  try { await api.delete(`/T0071I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); toast(t('deleted', 'Deleted'), 'success') }
  catch { toast(t('failed-save', 'Failed to delete'), 'error') }
}

onMounted(() => { loadSuppliers(); load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; margin-bottom: 20px; }
.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }
.cell-order { font-family: monospace; font-weight: 600; }
.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-subtle); }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.text-center { text-align: center; }
.empty-state { text-align: center; padding: 48px; color: var(--text-faint); font-size: 14px; }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 16px; display: block; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
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
.required { color: #dc2626; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
</style>

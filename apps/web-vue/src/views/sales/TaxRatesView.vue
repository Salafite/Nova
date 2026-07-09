<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('tax-rates-title', 'Tax Rates') }}</h1>
        <p class="page-subtitle">{{ t('tax-rates-sub', 'Configure sales tax rates and rules') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-tax-rate', 'New Tax Rate') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">percent</span>
      <p>{{ t('no-records', 'No records found') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('code', 'Code') }}</th>
              <th>{{ t('name', 'Name') }}</th>
              <th class="col-num">{{ t('rate', 'Rate %') }}</th>
              <th>{{ t('type', 'Type') }}</th>
              <th class="text-center">{{ t('default', 'Default') }}</th>
              <th class="text-center">{{ t('active', 'Active') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-mono">{{ item.code }}</td>
              <td class="cell-name">{{ item.name }}</td>
              <td class="col-num">{{ item.rate }}%</td>
              <td>{{ item.type }}</td>
              <td class="text-center"><span v-if="item.is_default" class="material-symbols-outlined" style="color: var(--color-primary);">star</span></td>
              <td class="text-center"><span class="badge" :class="item.is_active ? 'badge-active' : 'badge-inactive'">{{ item.is_active ? t('yes', 'Yes') : t('no', 'No') }}</span></td>
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
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-tax-rate', 'Edit Tax Rate') : t('new-tax-rate', 'New Tax Rate') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('code', 'Code') }} <span class="required">*</span></label>
            <input type="text" v-model="form.code" required class="form-input" maxlength="20" />
          </div>
          <div class="form-group">
            <label>{{ t('name', 'Name') }} <span class="required">*</span></label>
            <input type="text" v-model="form.name" required class="form-input" maxlength="100" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('rate', 'Rate %') }} <span class="required">*</span></label>
              <input type="number" step="0.01" min="0" max="100" v-model.number="form.rate" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('type', 'Type') }}</label>
              <select v-model="form.type" class="form-input">
                <option value="Sales">Sales</option>
                <option value="Purchase">Purchase</option>
                <option value="Both">Both</option>
              </select>
            </div>
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

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete?')" :message="t('confirm-delete-msg', 'Delete') + ' ' + confirmTarget.name + '?'" @confirm="executeDelete" @cancel="confirmTarget = null" />
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
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ code: '', name: '', rate: 0, type: 'Sales', is_active: true, is_default: false, description: '' })
const editId = ref(null)
const confirmTarget = ref(null)

async function load() {
  loading.value = true; error.value = ''
  try { const res = await api.get('/T0085I/'); items.value = res.data || [] }
  catch { error.value = t('failed-load', 'Failed to load') }
  finally { loading.value = false }
}

function openAdd() {
  editing.value = false; editId.value = null
  form.value = { code: '', name: '', rate: 0, type: 'Sales', is_active: true, is_default: false, description: '' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = { code: item.code, name: item.name, rate: item.rate, type: item.type || 'Sales', is_active: item.is_active, is_default: item.is_default, description: item.description || '' }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, description: form.value.description || null }
    if (editing.value) { await api.put(`/T0085I/${editId.value}`, payload); toast(t('saved-ok', 'Saved'), 'success') }
    else { await api.post('/T0085I/', payload); toast(t('created', 'Created'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save', 'Failed to save'), 'error') }
  finally { saving.value = false }
}

function deleteItem(item) { confirmTarget.value = item }
async function executeDelete() {
  const item = confirmTarget.value; confirmTarget.value = null
  try { await api.delete(`/T0085I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); toast(t('deleted', 'Deleted'), 'success') }
  catch { toast(t('failed-save', 'Failed to delete'), 'error') }
}

onMounted(() => { load() })
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
</style>

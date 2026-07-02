<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('warehouse-title', 'Warehouses') }}</h2>
        <p class="page-subtitle">{{ t('warehouse-sub', 'Manage warehouse locations and storage facilities') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-warehouse', 'New Warehouse') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">factory</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('name') }}</th>
            <th>{{ t('warehouse-location', 'Location') }}</th>
            <th class="text-center">{{ t('status') }}</th>
            <th class="text-center">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="fw-600">{{ item.name }}</td>
            <td>{{ item.location || '-' }}</td>
            <td class="text-center">
              <span v-if="item.is_active" class="badge badge-active">{{ t('active') }}</span>
              <span v-else class="badge badge-disabled">{{ t('inactive') }}</span>
            </td>
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

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-warehouse', 'Edit Warehouse') : t('new-warehouse', 'New Warehouse') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('name') }} <span class="text-red-500">*</span></label>
            <input type="text" v-model="form.name" class="form-input" maxlength="100" />
          </div>
          <div class="form-group">
            <label>{{ t('warehouse-location', 'Location') }}</label>
            <input type="text" v-model="form.location" class="form-input" maxlength="200" />
          </div>
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              <span>{{ t('active') }}</span>
            </label>
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
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.name" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
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
const form = ref({ name: '', location: '', is_active: true })
const editId = ref(null)
const confirmTarget = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0008I/')
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
  form.value = { name: '', location: '', is_active: true }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = { name: item.name, location: item.location || '', is_active: item.is_active }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, location: form.value.location || null }
    if (editing.value) {
      await api.put(`/T0008I/${editId.value}`, payload)
      toast('Warehouse ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0008I/', payload)
      toast('Warehouse ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Warehouse', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0008I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Warehouse deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Warehouse', 'error')
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
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; }
.fw-600 { font-weight: 600; }
.text-red-500 { color: #e53935; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
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
.modal { background: #fff; border-radius: 12px; width: 480px; max-width: 90vw; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid #eee; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; transition: border-color 0.15s; }
.form-input:focus { border-color: #5d3fd3; }
.checkbox-group { display: flex; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; color: #333; text-transform: none; letter-spacing: 0px; }
.checkbox-label input[type="checkbox"] { width: 16px; height: 16px; accent-color: #5d3fd3; }
</style>

<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('attr-title', 'Attributes') }}</h1>
        <p class="page-subtitle">{{ t('attr-sub', 'Define product attributes like size, color, material, etc.') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-attr', 'New Attribute') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">list_alt</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('name') }}</th>
            <th>{{ t('attr-type', 'Type') }}</th>
            <th class="text-center">{{ t('attr-required', 'Required') }}</th>
            <th class="text-center">{{ t('attr-sort', 'Sort') }}</th>
            <th class="text-center">{{ t('status') }}</th>
            <th class="text-center">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="fw-600">{{ item.attribute_name }}</td>
            <td><span class="mono">{{ item.attribute_type }}</span></td>
            <td class="text-center">
              <span v-if="item.is_required" class="badge badge-active">{{ t('yes') }}</span>
              <span v-else class="badge badge-disabled">{{ t('no') }}</span>
            </td>
            <td class="text-center mono">{{ item.sort_order }}</td>
            <td class="text-center">
              <span v-if="item.is_active" class="badge badge-active">{{ t('active') }}</span>
              <span v-else class="badge badge-disabled">{{ t('inactive') }}</span>
            </td>
            <td class="text-center">
              <button class="btn-icon" @click="editItem(item)" :title="t('edit')" :aria-label="t('edit')">
                <span class="material-symbols-outlined">edit</span>
              </button>
              <button class="btn-icon text-red-500" @click="deleteItem(item)" :title="t('delete')" :aria-label="t('delete')">
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
          <h3>{{ editing ? t('edit-attr', 'Edit Attribute') : t('new-attr', 'New Attribute') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('name') }} <span class="text-red-500">*</span></label>
            <input type="text" v-model="form.attribute_name" class="form-input" maxlength="50" />
          </div>
          <div class="form-group">
            <label>{{ t('attr-type', 'Type') }}</label>
            <select v-model="form.attribute_type" class="form-input">
              <option value="Text">Text</option>
              <option value="Number">Number</option>
              <option value="Date">Date</option>
              <option value="Boolean">Boolean</option>
              <option value="Select">Select</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('attr-sort', 'Sort Order') }}</label>
            <input type="number" min="0" v-model.number="form.sort_order" class="form-input" />
          </div>
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_required" />
              <span>{{ t('attr-required', 'Required') }}</span>
            </label>
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
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.attribute_name" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
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
const form = ref({ attribute_name: '', attribute_type: 'Text', is_required: false, sort_order: 0, is_active: true })
const editId = ref(null)
const confirmTarget = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0005I/')
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
  form.value = { attribute_name: '', attribute_type: 'Text', is_required: false, sort_order: 0, is_active: true }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    attribute_name: item.attribute_name,
    attribute_type: item.attribute_type,
    is_required: item.is_required,
    sort_order: item.sort_order,
    is_active: item.is_active,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    if (editing.value) {
      await api.put(`/T0005I/${editId.value}`, form.value)
      toast('Attribute ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0005I/', form.value)
      toast('Attribute ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Attribute', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0005I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Attribute deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Attribute', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.fw-600 { font-weight: 600; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal { background: var(--bg-surface); border-radius: 12px; width: 480px; max-width: 90vw; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-light); }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: var(--text-primary); }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid var(--border-light); }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid var(--border-input); border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; transition: border-color 0.15s; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
.checkbox-group { display: flex; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; color: var(--text-primary); text-transform: none; letter-spacing: 0px; }
.checkbox-label input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--color-primary); }
</style>

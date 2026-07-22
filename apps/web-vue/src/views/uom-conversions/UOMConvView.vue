<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('uom-conv-title', 'UOM Conversions') }}</h1>
        <p class="page-subtitle">{{ t('uom-conv-sub', 'Manage conversion factors between units of measure') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-uom-conv', 'New Conversion') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">swap_horiz</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>From UOM</th>
            <th>To UOM</th>
            <th class="text-center">{{ t('conv-factor', 'Factor') }}</th>
            <th class="text-center">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ uomName(item.from_uom_id) }}</td>
            <td>{{ uomName(item.to_uom_id) }}</td>
            <td class="text-center mono">{{ item.factor }}</td>
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
          <h3>{{ editing ? t('edit-uom-conv', 'Edit Conversion') : t('new-uom-conv', 'New Conversion') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>From UOM</label>
            <select v-model="form.from_uom_id" class="form-input">
              <option value="">-- Select --</option>
              <option v-for="uom in uoms" :key="uom.id" :value="uom.id">{{ uom.uom_code }} - {{ uom.uom_name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>To UOM</label>
            <select v-model="form.to_uom_id" class="form-input">
              <option value="">-- Select --</option>
              <option v-for="uom in uoms" :key="uom.id" :value="uom.id">{{ uom.uom_code }} - {{ uom.uom_name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('conv-factor', 'Factor') }}</label>
            <input type="number" step="0.000001" min="0.000001" v-model.number="form.factor" class="form-input" />
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
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.id" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
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
const uoms = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ from_uom_id: null, to_uom_id: null, factor: 1 })
const editId = ref(null)
const confirmTarget = ref(null)

function uomName(id) {
  const uom = uoms.value.find(u => u.id === id)
  return uom ? `${uom.uom_code} - ${uom.uom_name}` : `#${id}`
}

async function loadUOMs() {
  try {
    const res = await api.get('/T0001I/')
    uoms.value = res.data || []
  } catch {}
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [convRes] = await Promise.all([api.get('/T0002I/')])
    items.value = convRes.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  form.value = { from_uom_id: null, to_uom_id: null, factor: 1 }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    from_uom_id: item.from_uom_id,
    to_uom_id: item.to_uom_id,
    factor: item.factor,
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
      await api.put(`/T0002I/${editId.value}`, form.value)
      toast('Conversion ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0002I/', form.value)
      toast('Conversion ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Conversion', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0002I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Conversion deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Conversion', 'error')
  }
}

onMounted(() => { loadUOMs(); load() })
</script>

<style scoped>
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
</style>

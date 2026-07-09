<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('suppliers-title') }}</h1>
        <p class="page-subtitle">{{ t('suppliers-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-supplier') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">local_shipping</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('name') }}</th>
              <th>{{ t('category') }}</th>
              <th>{{ t('supplier-phone') }}</th>
              <th>{{ t('supplier-email') }}</th>
              <th>{{ t('supplier-payment-terms') }}</th>
              <th class="text-center">{{ t('supplier-rating') }}</th>
              <th class="text-center">{{ t('status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ item.name }}</td>
              <td>{{ item.category || '-' }}</td>
              <td class="cell-mono">{{ item.phone || '-' }}</td>
              <td class="cell-mono">{{ item.email || '-' }}</td>
              <td>{{ item.payment_terms || '-' }}</td>
              <td class="text-center">
                <span v-if="item.rating > 0" class="badge" :class="ratingBadge(item.rating)">{{ item.rating }}/5</span>
                <span v-else class="badge badge-inactive">-</span>
              </td>
              <td class="text-center">
                <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ item.is_active ? t('active') : t('inactive') }}
                </span>
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
          <h3>{{ editing ? t('edit-supplier') : t('new-supplier') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('name') }} <span class="required">*</span></label>
              <input type="text" v-model="form.name" required class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('category') }}</label>
              <input type="text" v-model="form.category" class="form-input" maxlength="100" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('supplier-phone') }}</label>
              <input type="text" v-model="form.phone" class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier-email') }}</label>
              <input type="email" v-model="form.email" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('supplier-payment-terms') }}</label>
              <input type="text" v-model="form.payment_terms" class="form-input" maxlength="100" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier-rating') }} (0-5)</label>
              <input type="number" min="0" max="5" v-model.number="form.rating" class="form-input" />
            </div>
          </div>
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              <span>{{ t('active') }}</span>
            </label>
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
const form = ref({ name: '', category: '', phone: '', email: '', payment_terms: '', rating: 0, is_active: true })
const editId = ref(null)
const confirmTarget = ref(null)

function ratingBadge(rating) {
  if (rating >= 4) return 'badge-active'
  if (rating >= 2) return 'badge-warning'
  return 'badge-inactive'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0011I/')
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
  form.value = { name: '', category: '', phone: '', email: '', payment_terms: '', rating: 0, is_active: true }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    name: item.name,
    category: item.category || '',
    phone: item.phone || '',
    email: item.email || '',
    payment_terms: item.payment_terms || '',
    rating: item.rating || 0,
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
    const payload = {
      ...form.value,
      phone: form.value.phone || null,
      email: form.value.email || null,
      category: form.value.category || null,
      payment_terms: form.value.payment_terms || null,
    }
    if (editing.value) {
      await api.put(`/T0011I/${editId.value}`, payload)
      toast('Supplier ' + t('saved-ok'), 'success')
    } else {
      await api.post('/T0011I/', payload)
      toast('Supplier ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' Supplier', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0011I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Supplier deleted', 'success')
  } catch {
    toast(t('failed-save') + ' Supplier', 'error')
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
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-inactive { background: #f3f4f6; color: #888; }

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
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; }
.form-input:focus { border-color: #5d3fd3; }
.required { color: #dc2626; }
.checkbox-group { display: flex; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-top: 8px; }
.checkbox-label input { width: 16px; height: 16px; accent-color: #5d3fd3; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
</style>

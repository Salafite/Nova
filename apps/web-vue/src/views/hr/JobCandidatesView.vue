<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('recruitment-title') }}</h1>
        <p class="page-subtitle">{{ t('recruitment-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-job') }} {{ t('recruitment-candidate') }}
      </button>
    </div>
    <SkeletonTable v-if="loading" columns="6" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">person_search</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('name') }}</th>
              <th>{{ t('customer-email') }}</th>
              <th>{{ t('supplier-phone') }}</th>
              <th>{{ t('recruitment-position') }}</th>
              <th class="text-center">{{ t('recruitment-status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ locale === 'ar-EG' ? (item.arabic_name || item.full_name) : item.full_name }}</td>
              <td>{{ item.email || '-' }}</td>
              <td>{{ item.phone || '-' }}</td>
              <td>{{ jobTitle(item.job_opening_id) }}</td>
              <td class="text-center">
                <span :class="candidateStatusBadge(item.status)">{{ candidateStatusLabel(item.status) }}</span>
              </td>
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
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-job') : t('new-job') }} {{ t('recruitment-candidate') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('name') }} <span class="required">*</span></label>
              <input type="text" v-model="form.full_name" class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('emp-arabic-name') }}</label>
              <input type="text" v-model="form.arabic_name" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('customer-email') }}</label>
              <input type="email" v-model="form.email" class="form-input" maxlength="100" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier-phone') }}</label>
              <input type="text" v-model="form.phone" class="form-input" maxlength="30" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('recruitment-position') }} <span class="required">*</span></label>
              <select v-model="form.job_opening_id" class="form-input">
                <option value="">{{ t('search') }}...</option>
                <option v-for="job in jobOpenings" :key="job.id" :value="job.id">{{ job.job_title || job.title }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('recruitment-status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="New">New</option>
                <option value="Reviewed">Reviewed</option>
                <option value="Interviewed">Interviewed</option>
                <option value="Accepted">Accepted</option>
                <option value="Rejected">Rejected</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('description') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="3"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="delete-text">{{ t('recruitment-delete-confirm') }}</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">{{ deleting ? t('deleting') : t('delete') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
const { show: toast } = useToast()
const { t, dir, locale } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])
const jobOpenings = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ full_name: '', arabic_name: '', email: '', phone: '', job_opening_id: '', status: 'New', notes: '' })
const editId = ref(null)
function candidateStatusBadge(status) {
  if (status === 'Accepted') return 'badge badge-active'
  if (status === 'Rejected') return 'badge badge-inactive'
  if (status === 'Interviewed') return 'badge badge-warning'
  return 'badge badge-pending'
}
function candidateStatusLabel(status) {
  return status || 'New'
}
function jobTitle(id) {
  if (!id) return '-'
  const j = jobOpenings.value.find(o => o.id === id)
  return j ? (j.job_title || j.title) : id
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const [res, jobRes] = await Promise.all([
      api.get('/T0040I/'),
      api.get('/T0039I/')
    ])
    items.value = res.data || []
    jobOpenings.value = jobRes.data || []
  } catch { error.value = t('failed-load') }
  finally { loading.value = false }
}
function openAdd() {
  editing.value = false; editId.value = null
  form.value = { full_name: '', arabic_name: '', email: '', phone: '', job_opening_id: '', status: 'New', notes: '' }
  showModal.value = true
}
function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = {
    full_name: item.full_name, arabic_name: item.arabic_name || '',
    email: item.email || '', phone: item.phone || '',
    job_opening_id: item.job_opening_id, status: item.status || 'New',
    notes: item.notes || ''
  }
  showModal.value = true
}
function closeModal() { showModal.value = false }
async function saveItem() {
  if (!form.value.full_name || !form.value.job_opening_id) return
  saving.value = true
  try {
    const payload = {
      ...form.value,
      arabic_name: form.value.arabic_name || null, email: form.value.email || null,
      phone: form.value.phone || null, notes: form.value.notes || null
    }
    if (editing.value) { await api.put(`/T0040I/${editId.value}`, payload); toast(t('recruitment-title'), 'success') }
    else { await api.post('/T0040I/', payload); toast(t('recruitment-title'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { saving.value = false }
}
function deleteItem(item) { deleteTarget.value = item; showDelete.value = true }
async function confirmDelete() {
  deleting.value = true
  try { await api.delete(`/T0040I/${deleteTarget.value.id}`); items.value = items.value.filter(i => i.id !== deleteTarget.value.id); toast(t('recruitment-title'), 'success'); showDelete.value = false }
  catch { toast(t('failed-save'), 'error') }
  finally { deleting.value = false }
}
onMounted(load)
</script>
<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.text-center { text-align: center; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-pending { background: #dbeafe; color: #2563eb; }
.badge-inactive { background: #f3f4f6; color: #888; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: #dc2626; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-wide { width: 780px; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.delete-text { font-size: 14px; color: #555; margin: 0; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
</style>

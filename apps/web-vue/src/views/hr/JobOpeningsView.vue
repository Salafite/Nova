<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('recruitment-title') }}</h2>
        <p class="page-subtitle">{{ t('recruitment-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-job') }}
      </button>
    </div>
    <SkeletonTable v-if="loading" columns="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">work</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('recruitment-position') }}</th>
              <th>{{ t('recruitment-department') }}</th>
              <th class="text-center">{{ t('emp-code') }} {{ t('recruitment-open') }}</th>
              <th class="text-center">{{ t('recruitment-status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ item.job_title || item.title }}</td>
              <td>{{ departmentName(item.department_id) }}</td>
              <td class="text-center">{{ item.openings || 1 }}</td>
              <td class="text-center">
                <span :class="item.status === 'Open' ? 'badge badge-active' : 'badge badge-inactive'">{{ item.status === 'Open' ? t('recruitment-open') : t('recruitment-closed') }}</span>
              </td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-job') : t('new-job') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('recruitment-position') }} <span class="required">*</span></label>
              <input type="text" v-model="form.job_title" class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('recruitment-department') }} <span class="required">*</span></label>
              <select v-model="form.department_id" class="form-input">
                <option value="">{{ t('search') }}...</option>
                <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.department_name }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('recruitment-location') }}</label>
              <input type="text" v-model="form.location" class="form-input" maxlength="100" />
            </div>
            <div class="form-group">
              <label>{{ t('recruitment-type') }}</label>
              <select v-model="form.employment_type" class="form-input">
                <option value="Full Time">{{ t('recruitment-full-time') }}</option>
                <option value="Part Time">{{ t('recruitment-part-time') }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('emp-code') }} {{ t('recruitment-open') }}</label>
              <input type="number" min="1" v-model.number="form.openings" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('recruitment-closing-date') }}</label>
              <input type="date" v-model="form.closing_date" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('recruitment-status') }}</label>
            <select v-model="form.status" class="form-input">
              <option value="Open">{{ t('recruitment-open') }}</option>
              <option value="Closed">{{ t('recruitment-closed') }}</option>
            </select>
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
          <button class="btn-icon" @click="showDelete = false"><span class="material-symbols-outlined">close</span></button>
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
const { t, dir } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])
const departments = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ job_title: '', department_id: '', location: '', employment_type: 'Full Time', openings: 1, closing_date: '', status: 'Open' })
const editId = ref(null)
function departmentName(id) {
  if (!id) return '-'
  const d = departments.value.find(dept => dept.id === id)
  return d ? d.department_name : id
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const [res, deptRes] = await Promise.all([
      api.get('/T0039I/'),
      api.get('/T0028I/')
    ])
    items.value = res.data || []
    departments.value = deptRes.data || []
  } catch { error.value = t('failed-load') }
  finally { loading.value = false }
}
function openAdd() {
  editing.value = false; editId.value = null
  form.value = { job_title: '', department_id: '', location: '', employment_type: 'Full Time', openings: 1, closing_date: '', status: 'Open' }
  showModal.value = true
}
function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = {
    job_title: item.job_title || item.title, department_id: item.department_id,
    location: item.location || '', employment_type: item.employment_type || 'Full Time',
    openings: item.openings || 1, closing_date: item.closing_date || '', status: item.status || 'Open'
  }
  showModal.value = true
}
function closeModal() { showModal.value = false }
async function saveItem() {
  if (!form.value.job_title || !form.value.department_id) return
  saving.value = true
  try {
    const payload = { ...form.value, location: form.value.location || null, closing_date: form.value.closing_date || null }
    if (editing.value) { await api.put(`/T0039I/${editId.value}`, payload); toast(t('recruitment-title'), 'success') }
    else { await api.post('/T0039I/', payload); toast(t('recruitment-title'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { saving.value = false }
}
function deleteItem(item) { deleteTarget.value = item; showDelete.value = true }
async function confirmDelete() {
  deleting.value = true
  try { await api.delete(`/T0039I/${deleteTarget.value.id}`); items.value = items.value.filter(i => i.id !== deleteTarget.value.id); toast(t('recruitment-title'), 'success'); showDelete.value = false }
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
.required { color: #dc2626; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
</style>

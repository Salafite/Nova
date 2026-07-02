<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('payroll-title') }}</h2>
        <p class="page-subtitle">{{ t('payroll-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-payroll') }}
      </button>
    </div>
    <SkeletonTable v-if="loading" columns="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">payments</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('payroll-period') }}</th>
              <th>{{ t('date') }} {{ t('leave-from') }}</th>
              <th>{{ t('date') }} {{ t('leave-to') }}</th>
              <th class="text-center">{{ t('payroll-status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ item.period_name || item.name }}</td>
              <td>{{ item.start_date }}</td>
              <td>{{ item.end_date }}</td>
              <td class="text-center">
                <span :class="periodStatusBadge(item.status)">{{ periodStatusLabel(item.status) }}</span>
              </td>
              <td class="text-center">
                <button class="btn-icon" @click="toggleEntries(item)" :title="t('edit')">
                  <span class="material-symbols-outlined">{{ expandedId === item.id ? 'expand_less' : 'expand_more' }}</span>
                </button>
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
            <tr v-if="expandedId === item.id" :key="'exp-'+item.id">
              <td colspan="5" class="p-0">
                <div class="expanded-section">
                  <h4 class="expanded-title">{{ t('payroll-title') }} {{ t('payroll-employee') }}</h4>
                  <table class="data-table sub-table">
                    <thead>
                      <tr>
                        <th>{{ t('payroll-employee') }}</th>
                        <th class="text-center">{{ t('payroll-basic') }}</th>
                        <th class="text-center">{{ t('payroll-allowances') }}</th>
                        <th class="text-center">{{ t('payroll-deductions') }}</th>
                        <th class="text-center">{{ t('payroll-net') }}</th>
                        <th class="text-center">{{ t('payroll-status') }}</th>
                        <th class="text-center">{{ t('actions') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="entry in item.entries || []" :key="entry.id">
                        <td class="cell-name">{{ entry.employee_id || '-' }}</td>
                        <td class="text-center">{{ entry.basic_salary || 0 }}</td>
                        <td class="text-center">{{ entry.allowances || 0 }}</td>
                        <td class="text-center">{{ entry.deductions || 0 }}</td>
                        <td class="text-center">{{ entry.net_salary || 0 }}</td>
                        <td class="text-center">
                          <span :class="entry.status === 'Paid' ? 'badge badge-active' : 'badge badge-inactive'">{{ entry.status === 'Paid' ? t('payroll-paid') : t('payroll-unpaid') }}</span>
                        </td>
                        <td class="text-center">
                          <button class="btn-icon" @click="editEntry(entry, item.id)" :title="t('edit')"><span class="material-symbols-outlined">edit</span></button>
                          <button class="btn-icon btn-icon-danger" @click="deleteEntry(entry, item.id)" :title="t('delete')"><span class="material-symbols-outlined">delete</span></button>
                        </td>
                      </tr>
                      <tr v-if="!item.entries || !item.entries.length">
                        <td colspan="7" class="text-center text-muted">{{ t('no-records') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-payroll') : t('new-payroll') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payroll-period') }} <span class="required">*</span></label>
              <input type="text" v-model="form.period_name" class="form-input" maxlength="100" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('date') }} {{ t('leave-from') }} <span class="required">*</span></label>
              <input type="date" v-model="form.start_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('date') }} {{ t('leave-to') }} <span class="required">*</span></label>
              <input type="date" v-model="form.end_date" class="form-input" />
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showEntryModal" class="modal-overlay" @click.self="showEntryModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingEntry ? t('edit-payroll') : t('new-payroll') }} {{ t('payroll-employee') }}</h3>
          <button class="btn-icon" @click="showEntryModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('payroll-employee') }} (ID) <span class="required">*</span></label>
            <input type="number" min="0" v-model.number="entryForm.employee_id" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payroll-basic') }}</label>
              <input type="number" min="0" v-model.number="entryForm.basic_salary" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('payroll-allowances') }}</label>
              <input type="number" min="0" v-model.number="entryForm.allowances" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('payroll-deductions') }}</label>
              <input type="number" min="0" v-model.number="entryForm.deductions" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('payroll-net') }}</label>
              <input type="number" min="0" v-model.number="entryForm.net_salary" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('payroll-status') }}</label>
            <select v-model="entryForm.status" class="form-input">
              <option value="Unpaid">{{ t('payroll-unpaid') }}</option>
              <option value="Paid">{{ t('payroll-paid') }}</option>
            </select>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showEntryModal = false">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="savingEntry" @click="saveEntry">{{ savingEntry ? t('saving') : t('save') }}</button>
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
          <p class="delete-text">{{ deletingEntry ? t('payroll-delete-confirm') : t('payroll-delete-confirm') }}</p>
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
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ period_name: '', start_date: '', end_date: '' })
const editId = ref(null)
const expandedId = ref(null)
const showEntryModal = ref(false)
const editingEntry = ref(false)
const savingEntry = ref(false)
const entryForm = ref({ employee_id: null, basic_salary: 0, allowances: 0, deductions: 0, net_salary: 0, status: 'Unpaid' })
const entryEditId = ref(null)
const entryPeriodId = ref(null)
const deleteEntryTarget = ref(null)
const deletingEntry = ref(false)
function periodStatusBadge(status) {
  if (status === 'Closed') return 'badge badge-inactive'
  return 'badge badge-active'
}
function periodStatusLabel(status) {
  if (status === 'Closed') return t('inactive')
  return t('active')
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const res = await api.get('/T0037I/')
    const periods = res.data || []
    for (const p of periods) {
      try {
        const eres = await api.get('/T0038I/', { params: { payroll_period_id: p.id } })
        p.entries = eres.data || []
      } catch { p.entries = [] }
    }
    items.value = periods
  } catch { error.value = t('failed-load') }
  finally { loading.value = false }
}
function toggleEntries(item) {
  expandedId.value = expandedId.value === item.id ? null : item.id
}
function openAdd() {
  editing.value = false; editId.value = null
  form.value = { period_name: '', start_date: '', end_date: '' }
  showModal.value = true
}
function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = { period_name: item.period_name || item.name, start_date: item.start_date, end_date: item.end_date }
  showModal.value = true
}
function closeModal() { showModal.value = false }
async function saveItem() {
  if (!form.value.period_name || !form.value.start_date || !form.value.end_date) return
  saving.value = true
  try {
    if (editing.value) { await api.put(`/T0037I/${editId.value}`, form.value); toast(t('payroll-title'), 'success') }
    else { await api.post('/T0037I/', form.value); toast(t('payroll-title'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { saving.value = false }
}
function deleteItem(item) { deleteTarget.value = item; deletingEntry.value = false; showDelete.value = true }
async function confirmDelete() {
  deleting.value = true
  try {
    if (deleteEntryTarget.value) {
      await api.delete(`/T0038I/${deleteEntryTarget.value.id}`)
      const period = items.value.find(p => p.id === entryPeriodId.value)
      if (period && period.entries) period.entries = period.entries.filter(e => e.id !== deleteEntryTarget.value.id)
      toast(t('payroll-title'), 'success')
    } else {
      await api.delete(`/T0037I/${deleteTarget.value.id}`); items.value = items.value.filter(i => i.id !== deleteTarget.value.id)
      toast(t('payroll-title'), 'success')
    }
    showDelete.value = false
  } catch { toast(t('failed-save'), 'error') }
  finally { deleting.value = false; deleteEntryTarget.value = null }
}
function openEntryAdd(periodId) {
  editingEntry.value = false; entryEditId.value = null; entryPeriodId.value = periodId
  entryForm.value = { employee_id: null, basic_salary: 0, allowances: 0, deductions: 0, net_salary: 0, status: 'Unpaid' }
  showEntryModal.value = true
}
function editEntry(entry, periodId) {
  editingEntry.value = true; entryEditId.value = entry.id; entryPeriodId.value = periodId
  entryForm.value = {
    employee_id: entry.employee_id, basic_salary: entry.basic_salary || 0,
    allowances: entry.allowances || 0, deductions: entry.deductions || 0,
    net_salary: entry.net_salary || 0, status: entry.status || 'Unpaid'
  }
  showEntryModal.value = true
}
async function saveEntry() {
  if (!entryForm.value.employee_id) return
  savingEntry.value = true
  try {
    const payload = { ...entryForm.value, payroll_period_id: entryPeriodId.value }
    if (editingEntry.value) { await api.put(`/T0038I/${entryEditId.value}`, payload); toast(t('payroll-title'), 'success') }
    else { await api.post('/T0038I/', payload); toast(t('payroll-title'), 'success') }
    showEntryModal.value = false; await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { savingEntry.value = false }
}
function deleteEntry(entry, periodId) {
  deleteEntryTarget.value = entry; entryPeriodId.value = periodId; deletingEntry.value = true; showDelete.value = true
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
.p-0 { padding: 0 !important; }
.text-muted { color: #999; font-size: 13px; padding: 16px; }
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
.expanded-section { background: #f9fafb; padding: 16px 24px; }
.expanded-title { font-size: 13px; font-weight: 700; color: #1a1a2e; margin: 0 0 12px; }
.sub-table { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.sub-table th { background: #f0f0f0; }
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

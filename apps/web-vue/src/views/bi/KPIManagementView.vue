<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('kpi-title', 'KPI Management') }}</h1>
        <p class="page-subtitle">{{ t('kpi-subtitle', 'Define and track Key Performance Indicators') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('kpi-new', 'New KPI') }}
      </button>
    </div>

    <SkeletonTable v-if="store.loading" :rows="5" :columns="6" />
    <div v-else-if="!store.kpis.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">analytics</span>
      <p>{{ t('kpi-empty', 'No KPIs defined yet') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('kpi-add-first', 'Add your first KPI') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('kpi-col-code', 'Code') }}</th>
              <th>{{ t('kpi-col-name', 'Name') }}</th>
              <th>{{ t('kpi-col-category', 'Category') }}</th>
              <th>{{ t('kpi-col-unit', 'Unit') }}</th>
              <th>{{ t('kpi-col-target', 'Target') }}</th>
              <th>{{ t('kpi-col-status', 'Status') }}</th>
              <th class="col-actions">{{ t('kpi-col-actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="kpi in store.kpis" :key="kpi.id" :class="{ 'row-inactive': !kpi.is_active }" @click="selectKpi(kpi)">
              <td class="cell-code">{{ kpi.kpi_code }}</td>
              <td class="cell-name">{{ kpi.kpi_name }}</td>
              <td>{{ kpi.category || '-' }}</td>
              <td class="cell-unit">{{ kpi.metric_unit || '-' }}</td>
              <td class="cell-target">{{ kpi.target_value != null ? kpi.target_value : '-' }}</td>
              <td>
                <span :class="kpi.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ kpi.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                </span>
              </td>
              <td class="cell-actions" @click.stop>
                <button class="btn-icon" @click="openEdit(kpi)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="confirmDelete(kpi)" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selectedKpi" class="kpi-detail">
      <div class="detail-header">
        <h3>{{ selectedKpi.kpi_name }} <span class="detail-code">{{ selectedKpi.kpi_code }}</span></h3>
        <button class="btn-icon" @click="selectedKpi = null" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
      </div>
      <div class="detail-body">
        <div class="detail-info">
          <div><strong>{{ t('kpi-category', 'Category') }}:</strong> {{ selectedKpi.category || '-' }}</div>
          <div><strong>{{ t('kpi-unit', 'Unit') }}:</strong> {{ selectedKpi.metric_unit || '-' }}</div>
          <div><strong>{{ t('kpi-target', 'Target') }}:</strong> {{ selectedKpi.target_value != null ? selectedKpi.target_value : '-' }}</div>
          <div><strong>{{ t('kpi-formula', 'Formula') }}:</strong> <code>{{ selectedKpi.formula || '-' }}</code></div>
        </div>
        <div v-if="chartLabels.length" class="chart-section">
          <h4 class="chart-section-title">{{ t('kpi-trend', 'Trend') }}</h4>
          <LineChart :labels="chartLabels" :datasets="chartDatasets" :height="220" />
        </div>
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>{{ t('kpi-values', 'KPI Values') }}</h4>
            <button class="btn-primary btn-xs" @click="openAddValue">{{ t('add-value', 'Add Value') }}</button>
          </div>
          <div v-if="!kpiValues.length" class="empty-section">{{ t('no-values', 'No values recorded') }}</div>
          <table v-else class="data-table mini-table">
            <thead>
              <tr>
                <th>{{ t('period', 'Period') }}</th>
                <th>{{ t('period-type', 'Type') }}</th>
                <th>{{ t('actual', 'Actual') }}</th>
                <th>{{ t('target', 'Target') }}</th>
                <th class="col-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="v in kpiValues" :key="v.id">
                <td>{{ v.period }}</td>
                <td>{{ v.period_type }}</td>
                <td class="cell-mono">{{ v.actual_value != null ? v.actual_value : '-' }}</td>
                <td class="cell-mono">{{ v.target_value != null ? v.target_value : '-' }}</td>
                <td class="cell-actions">
                  <button class="btn-icon btn-icon-danger btn-xs" @click="deleteValue(v)"><span class="material-symbols-outlined">delete</span></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? t('kpi-edit', 'Edit KPI') : t('kpi-new', 'New KPI') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="save" class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('kpi-code', 'Code') }} <span class="required">*</span></label>
              <input type="text" v-model="form.kpi_code" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('kpi-name', 'Name') }} <span class="required">*</span></label>
              <input type="text" v-model="form.kpi_name" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('kpi-category', 'Category') }}</label>
              <input type="text" v-model="form.category" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('kpi-unit', 'Unit') }}</label>
              <input type="text" v-model="form.metric_unit" class="form-input" placeholder="%, $, count..." />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('kpi-target', 'Target Value') }}</label>
              <input type="number" step="any" v-model.number="form.target_value" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('kpi-formula', 'Formula') }}</label>
              <input type="text" v-model="form.formula" class="form-input" placeholder="e.g. revenue / employees" />
            </div>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              {{ t('active', 'Active') }}
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showValueModal" class="modal-overlay" @click.self="showValueModal = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('add-value', 'Add KPI Value') }}</h3>
          <button class="btn-icon" @click="showValueModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="saveValue" class="modal-body">
          <div class="form-group">
            <label>{{ t('period', 'Period') }} <span class="required">*</span></label>
            <input type="date" v-model="valueForm.period" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('period-type', 'Period Type') }}</label>
            <select v-model="valueForm.period_type" class="form-input">
              <option value="Daily">Daily</option>
              <option value="Weekly">Weekly</option>
              <option value="Monthly">Monthly</option>
              <option value="Quarterly">Quarterly</option>
              <option value="Yearly">Yearly</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('actual', 'Actual Value') }}</label>
              <input type="number" step="any" v-model.number="valueForm.actual_value" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('target', 'Target Value') }}</label>
              <input type="number" step="any" v-model.number="valueForm.target_value" class="form-input" />
            </div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="showValueModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary">{{ t('save', 'Save') }}</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog v-if="showDelete" :message="t('kpi-delete-msg', 'Delete this KPI?')" @confirm="doDelete" @cancel="showDelete = false" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { useBiStore } from '../../stores/bi.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import LineChart from '../../components/charts/LineChart.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const store = useBiStore()

const loading = ref(true)
const selectedKpi = ref(null)
const kpiValues = ref([])
const showModal = ref(false)

const chartLabels = computed(() => kpiValues.value.map(v => v.period).filter(Boolean))
const chartDatasets = computed(() => [
  { label: 'Actual', data: kpiValues.value.map(v => v.actual_value), borderColor: '#5d3fd3', backgroundColor: '#5d3fd31a', fill: true, tension: 0.4, pointBackgroundColor: '#5d3fd3', pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2 },
  { label: 'Target', data: kpiValues.value.map(v => v.target_value), borderColor: '#dc2626', backgroundColor: 'transparent', fill: false, tension: 0.4, pointBackgroundColor: '#dc2626', pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2, borderDash: [5, 5] }
])
const showValueModal = ref(false)
const showDelete = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const deletingItem = ref(null)
const editingId = ref(null)

const form = reactive({ kpi_code: '', kpi_name: '', category: '', metric_unit: '', target_value: null, formula: '', is_active: true })
const valueForm = reactive({ kpi_id: null, period: '', period_type: 'Monthly', actual_value: null, target_value: null })

function resetForm() {
  form.kpi_code = ''; form.kpi_name = ''; form.category = ''
  form.metric_unit = ''; form.target_value = null; form.formula = ''
  form.is_active = true
}

function openAdd() {
  isEditing.value = false; editingId.value = null; resetForm(); showModal.value = true
}

function openEdit(kpi) {
  isEditing.value = true; editingId.value = kpi.id
  form.kpi_code = kpi.kpi_code; form.kpi_name = kpi.kpi_name
  form.category = kpi.category || ''; form.metric_unit = kpi.metric_unit || ''
  form.target_value = kpi.target_value; form.formula = kpi.formula || ''
  form.is_active = kpi.is_active
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function save() {
  if (!form.kpi_code || !form.kpi_name) {
    toast(t('kpi-required', 'Code and name are required'), 'error'); return
  }
  saving.value = true
  try {
    const payload = { ...form, category: form.category || null, metric_unit: form.metric_unit || null, formula: form.formula || null }
    if (isEditing.value) {
      await store.updateKpi(editingId.value, payload)
      toast(t('kpi-updated', 'KPI updated'), 'success')
    } else {
      await store.createKpi(payload)
      toast(t('kpi-created', 'KPI created'), 'success')
    }
    closeModal()
  } catch { toast(t('kpi-save-error', 'Failed to save KPI'), 'error') }
  finally { saving.value = false }
}

function confirmDelete(kpi) { deletingItem.value = kpi; showDelete.value = true }

async function doDelete() {
  try {
    await store.deleteKpi(deletingItem.value.id)
    toast(t('kpi-deleted', 'KPI deleted'), 'success')
    showDelete.value = false
    if (selectedKpi.value?.id === deletingItem.value.id) selectedKpi.value = null
  } catch { toast(t('kpi-delete-error', 'Failed to delete KPI'), 'error') }
}

async function selectKpi(kpi) {
  selectedKpi.value = kpi
  await store.loadKpiValues(kpi.id)
  kpiValues.value = store.kpiValues
}

function openAddValue() {
  valueForm.kpi_id = selectedKpi.value.id
  valueForm.period = new Date().toISOString().slice(0, 10)
  valueForm.period_type = 'Monthly'
  valueForm.actual_value = null
  valueForm.target_value = null
  showValueModal.value = true
}

async function saveValue() {
  try {
    await store.createKpiValue({ ...valueForm })
    kpiValues.value = store.kpiValues
    toast(t('value-added', 'Value added'), 'success')
    showValueModal.value = false
  } catch { toast(t('value-error', 'Failed to add value'), 'error') }
}

async function deleteValue(v) {
  try {
    await store.deleteKpiValue(v.id, selectedKpi.value.id)
    kpiValues.value = store.kpiValues
    toast(t('value-deleted', 'Value deleted'), 'success')
  } catch { toast(t('value-delete-error', 'Failed to delete value'), 'error') }
}

onMounted(async () => {
  await store.loadKpis()
  loading.value = false
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-subtitle { font-size: 13px; color: var(--text-subtle); margin-top: 2px; }

.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr { cursor: pointer; }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }
.row-inactive { opacity: 0.55; }
.cell-code { font-family: monospace; font-size: 12px; color: var(--text-subtle); }
.cell-name { font-weight: 600; }
.cell-unit { color: var(--text-muted); font-family: monospace; }
.cell-target { font-family: monospace; font-weight: 600; }
.col-actions { text-align: right; }
.cell-actions { text-align: right; white-space: nowrap; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }

.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.btn-xs { padding: 4px 12px !important; font-size: 12px !important; }

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
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
.required { color: #dc2626; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-secondary); }
.checkbox-label input { width: 16px; height: 16px; }

.empty-state { text-align: center; padding: 80px 0; color: var(--text-faint); }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 12px; }
.empty-state p { margin-bottom: 16px; }
.empty-section { font-size: 12px; color: var(--text-faint); padding: 16px 0; text-align: center; }

.kpi-detail { margin-top: 24px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.detail-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-default); }
.detail-header h3 { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.detail-code { font-size: 12px; color: var(--text-subtle); font-weight: 400; font-family: monospace; }
.detail-body { padding: 20px; }
.detail-info { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }
.detail-info strong { color: var(--text-muted); font-size: 12px; }
.detail-info code { background: var(--bg-body); padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.chart-section { margin: 16px 0; padding: 16px; background: var(--bg-chart); border: 1px solid var(--border-default); border-radius: 8px; }
.chart-section-title { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }
.detail-section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.detail-section-head h4 { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.mini-table td, .mini-table th { padding: 6px 10px; font-size: 12px; }
.cell-mono { font-family: monospace; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-actions, [dir="rtl"] .cell-actions { text-align: left; }
[dir="rtl"] .modal-actions { flex-direction: row-reverse; }
[dir="rtl"] .form-row { direction: rtl; }
[dir="rtl"] .detail-header { flex-direction: row-reverse; }
[dir="rtl"] .detail-section-head { flex-direction: row-reverse; }
</style>

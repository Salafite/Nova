<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('bom-title') }}</h2>
        <p class="page-subtitle">{{ t('bom-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-bom') }}
      </button>
    </div>
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">account_tree</span>
      <p>{{ t('no-records') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-bom') }}</button>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('bom-code') }}</th>
              <th>{{ t('bom-name') }}</th>
              <th>{{ t('product') }}</th>
              <th class="text-center">{{ t('status') }}</th>
              <th class="col-num">{{ t('bom-total-cost') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-mono">{{ item.bom_code || item.code }}</td>
              <td class="cell-name">{{ item.bom_name || item.name }}</td>
              <td>{{ productName(item.product_id) }}</td>
              <td class="text-center">
                <span class="badge" :class="statusBadge(item.status)">{{ item.status }}</span>
              </td>
              <td class="col-num">${{ (item.total_cost || 0).toFixed(2) }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="toggleExpand(item)" :title="t('bom-lines')">
                  <span class="material-symbols-outlined">{{ expandedId === item.id ? 'expand_less' : 'expand_more' }}</span>
                </button>
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
            <tr v-for="item in items" :key="'lines-' + item.id" v-if="expandedId === item.id">
              <td colspan="6" class="lines-cell">
                <div class="bom-lines-wrap">
                  <div class="bom-lines-header">
                    <strong>{{ t('bom-lines') }}</strong>
                    <button class="btn-outline btn-sm" @click="openAddLine(item)">
                      <span class="material-symbols-outlined">add</span> {{ t('add-line') }}
                    </button>
                  </div>
                  <table class="data-table lines-table" v-if="item.lines && item.lines.length">
                    <thead>
                      <tr>
                        <th>{{ t('product') }}</th>
                        <th class="col-num">{{ t('bom-line-qty') }}</th>
                        <th class="col-num">{{ t('bom-line-unit-cost') }}</th>
                        <th class="col-num">{{ t('bom-line-total') }}</th>
                        <th class="text-center">{{ t('actions') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="line in item.lines" :key="line.id">
                        <td>{{ productName(line.product_id) }}</td>
                        <td class="col-num">{{ line.quantity }}</td>
                        <td class="col-num">${{ (line.unit_cost || 0).toFixed(2) }}</td>
                        <td class="col-num">${{ ((line.quantity || 0) * (line.unit_cost || 0)).toFixed(2) }}</td>
                        <td class="text-center">
                          <button class="btn-icon btn-icon-danger" @click="deleteLine(item, line)">
                            <span class="material-symbols-outlined">delete</span>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="no-lines">{{ t('bom-no-lines') }}</p>
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
          <h3>{{ editing ? t('edit-bom') : t('new-bom') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('bom-code') }} <span class="required">*</span></label>
              <input type="text" v-model="form.bom_code" class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('bom-name') }} <span class="required">*</span></label>
              <input type="text" v-model="form.bom_name" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('product') }} <span class="required">*</span></label>
              <select v-model="form.product_id" class="form-input">
                <option value="">-- {{ t('select') }} --</option>
                <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="Draft">Draft</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('bom-total-cost') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="form.total_cost" class="form-input" />
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showLineModal" class="modal-overlay" @click.self="showLineModal = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('add-line') }}</h3>
          <button class="btn-icon" @click="showLineModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('product') }} <span class="required">*</span></label>
            <select v-model="lineForm.product_id" class="form-input">
              <option value="">-- {{ t('select') }} --</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('bom-line-qty') }} <span class="required">*</span></label>
            <input type="number" step="0.01" min="0" v-model.number="lineForm.quantity" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('bom-line-unit-cost') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="lineForm.unit_cost" class="form-input" />
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showLineModal = false">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="savingLine" @click="saveLine">{{ savingLine ? t('saving') : t('save') }}</button>
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
          <p class="delete-text">{{ t('bom-delete-confirm') }} <strong>{{ deleteTarget?.bom_name || deleteTarget?.name }}</strong>?</p>
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
const products = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ bom_code: '', bom_name: '', product_id: null, status: 'Active', total_cost: 0 })
const editId = ref(null)
const expandedId = ref(null)
const showLineModal = ref(false)
const savingLine = ref(false)
const lineForm = ref({ product_id: null, quantity: 1, unit_cost: 0 })
const lineParentBom = ref(null)

function statusBadge(status) {
  const map = { Active: 'badge badge-active', Inactive: 'badge badge-inactive', Draft: 'badge badge-warning' }
  return map[status] || 'badge badge-inactive'
}

function productName(id) {
  if (!id) return '-'
  const p = products.value.find(x => x.id === id)
  return p ? p.name : `#${id}`
}

async function loadProducts() {
  try { const res = await api.get('/T0003I/'); products.value = res.data || [] } catch {}
}

async function loadLines(bomId) {
  try {
    const res = await api.get('/T0066I/', { params: { bom_id: bomId } })
    const bom = items.value.find(i => i.id === bomId)
    if (bom) bom.lines = res.data || []
  } catch {
    const bom = items.value.find(i => i.id === bomId)
    if (bom) bom.lines = []
  }
}

function toggleExpand(item) {
  if (expandedId.value === item.id) {
    expandedId.value = null
  } else {
    expandedId.value = item.id
    if (!item.lines) loadLines(item.id)
  }
}

async function load() {
  loading.value = true; error.value = ''
  try { const res = await api.get('/T0065I/'); items.value = (res.data || []).map(i => ({ ...i, lines: null })) }
  catch { error.value = t('failed-load') }
  finally { loading.value = false }
}

function openAdd() {
  editing.value = false; editId.value = null
  form.value = { bom_code: '', bom_name: '', product_id: null, status: 'Active', total_cost: 0 }
  showModal.value = true
}

function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = {
    bom_code: item.bom_code || item.code || '',
    bom_name: item.bom_name || item.name || '',
    product_id: item.product_id,
    status: item.status || 'Active',
    total_cost: item.total_cost || 0
  }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  if (!form.value.bom_code || !form.value.bom_name) return
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editing.value) { await api.put(`/T0065I/${editId.value}`, payload); toast(t('bom-saved'), 'success') }
    else { await api.post('/T0065I/', payload); toast(t('bom-saved'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { saving.value = false }
}

function deleteItem(item) { deleteTarget.value = item; showDelete.value = true }

async function confirmDelete() {
  deleting.value = true
  try { await api.delete(`/T0065I/${deleteTarget.value.id}`); items.value = items.value.filter(i => i.id !== deleteTarget.value.id); toast(t('bom-deleted'), 'success'); showDelete.value = false }
  catch { toast(t('failed-save'), 'error') }
  finally { deleting.value = false }
}

function openAddLine(bom) {
  lineParentBom.value = bom
  lineForm.value = { product_id: null, quantity: 1, unit_cost: 0 }
  showLineModal.value = true
}

async function saveLine() {
  if (!lineForm.value.product_id || !lineForm.value.quantity) return
  savingLine.value = true
  try {
    const payload = { ...lineForm.value, bom_id: lineParentBom.value.id }
    await api.post('/T0066I/', payload)
    toast(t('line-saved'), 'success')
    showLineModal.value = false
    if (expandedId.value === lineParentBom.value.id) await loadLines(lineParentBom.value.id)
  } catch { toast(t('failed-save'), 'error') }
  finally { savingLine.value = false }
}

async function deleteLine(bom, line) {
  try {
    await api.delete(`/T0066I/${line.id}`)
    if (bom.lines) bom.lines = bom.lines.filter(l => l.id !== line.id)
    toast(t('line-deleted'), 'success')
  } catch { toast(t('failed-save'), 'error') }
}

onMounted(() => { loadProducts(); load() })
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
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.text-center { text-align: center; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
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
.btn-sm { padding: 4px 12px; font-size: 12px; }
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
.lines-cell { padding: 0 !important; background: #fafbfc; }
.bom-lines-wrap { padding: 14px 20px; }
.bom-lines-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.bom-lines-header strong { font-size: 13px; color: #333; }
.lines-table { font-size: 12px; }
.lines-table th { background: #f0f2f5; font-size: 10px; padding: 6px 10px; }
.lines-table td { padding: 6px 10px; }
.no-lines { color: #999; font-size: 13px; text-align: center; padding: 12px; margin: 0; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
[dir="rtl"] .bom-lines-header { flex-direction: row-reverse; }
</style>

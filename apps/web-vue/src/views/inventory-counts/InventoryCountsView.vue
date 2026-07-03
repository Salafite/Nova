<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('ic-title', 'Inventory Counts') }}</h2>
        <p class="page-subtitle">{{ t('ic-sub', 'Create and manage physical inventory counts') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-ic', 'New Count') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" :rows="5" :columns="6" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!counts.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">fact_check</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('ic-number', 'Count #') }}</th>
              <th>{{ t('ic-warehouse', 'Warehouse') }}</th>
              <th>{{ t('ic-date', 'Count Date') }}</th>
              <th>{{ t('ic-items', 'Items') }}</th>
              <th>{{ t('ic-diff', 'Differences') }}</th>
              <th>{{ t('status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in counts" :key="c.id"
                :class="{ 'row-selected': selectedId === c.id }"
                @click="selectCount(c)">
              <td class="cell-mono">{{ c.count_number }}</td>
              <td>{{ warehouseName(c.warehouse_id) }}</td>
              <td class="cell-date">{{ c.count_date }}</td>
              <td class="col-num">{{ itemCounts[c.id]?.total ?? '-' }}</td>
              <td class="col-num">{{ itemCounts[c.id]?.diffs ?? '-' }}</td>
              <td><span class="badge" :class="statusBadge(c.status)">{{ c.status }}</span></td>
              <td class="text-center">
                <button class="btn-icon" @click.stop="editCount(c)" :title="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click.stop="deleteCount(c)" :title="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selectedId" class="detail-section">
      <div class="detail-header">
        <h3>{{ t('ic-items', 'Count Items') }}</h3>
        <div class="detail-actions">
          <button v-if="selectedStatus === 'Draft'" class="btn-outline btn-sm" @click="populateItems">
            <span class="material-symbols-outlined">refresh</span> {{ t('ic-populate', 'Populate from Stock') }}
          </button>
          <button v-if="selectedStatus === 'Draft'" class="btn-primary btn-sm" @click="startCount">
            {{ t('ic-start', 'Start Count') }}
          </button>
          <button v-if="selectedStatus === 'In Progress'" class="btn-primary btn-sm" @click="completeCount" :disabled="completing">
            {{ completing ? t('completing') : t('ic-complete', 'Complete Count') }}
          </button>
        </div>
      </div>

      <SkeletonTable v-if="itemsLoading" :rows="3" :columns="4" />
      <ErrorState v-else-if="itemsError" :message="itemsError" @retry="loadItems" />
      <div v-else-if="!items.length" class="empty-state-sm">
        <p>{{ t('ic-no-items', 'No items. Click "Populate from Stock" to add items.') }}</p>
      </div>
      <div v-else class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('sku') }}</th>
                <th>{{ t('name') }}</th>
                <th class="col-num">{{ t('ic-expected', 'Expected') }}</th>
                <th class="col-num">{{ t('ic-counted', 'Counted') }}</th>
                <th class="col-num">{{ t('ic-difference', 'Diff') }}</th>
                <th>{{ t('ic-item-notes', 'Notes') }}</th>
                <th class="text-center">{{ t('actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id"
                  :class="{ 'row-diff': item.counted_qty !== null && Math.abs(item.counted_qty - item.expected_qty) > 0.001 }">
                <td class="cell-mono">{{ item.sku }}</td>
                <td class="cell-name">{{ item.product_name }}</td>
                <td class="col-num">{{ item.expected_qty }}</td>
                <td class="col-num">
                  <input v-if="selectedStatus === 'In Progress'"
                         type="number" step="0.01"
                         class="form-input form-input-sm"
                         :value="item.counted_qty"
                         @input="updateCounted(item.id, $event)" />
                  <span v-else>{{ item.counted_qty ?? '-' }}</span>
                </td>
                <td class="col-num" :class="diffClass(item)">{{ diffText(item) }}</td>
                <td>
                  <input v-if="selectedStatus === 'In Progress'"
                         type="text" class="form-input form-input-sm"
                         :value="item.notes || ''"
                         @input="updateItemNotes(item.id, $event)"
                         :placeholder="t('ic-item-notes', 'Notes')" />
                  <span v-else>{{ item.notes || '-' }}</span>
                </td>
                <td class="text-center">
                  <button v-if="selectedStatus === 'Draft'" class="btn-icon btn-icon-danger" @click.stop="deleteItem(item)" :title="t('delete')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
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
          <h3>{{ editing ? t('edit-ic', 'Edit Count') : t('new-ic', 'New Count') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('ic-number', 'Count #') }}</label>
              <input type="text" v-model="form.count_number" class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('ic-warehouse', 'Warehouse') }}</label>
              <select v-model="form.warehouse_id" class="form-input">
                <option value="">-- {{ t('select') }} --</option>
                <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('ic-date', 'Count Date') }}</label>
              <input type="date" v-model="form.count_date" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2"></textarea>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? t('saving') : t('save') }}</button>
        </div>
      </div>
    </div>

    <ConfirmDialog ref="confirmRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const counts = ref([])
const warehouses = ref([])
const selectedId = ref(null)
const selectedStatus = ref('')
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const itemsLoading = ref(false)
const itemsError = ref('')
const items = ref([])
const itemCounts = reactive({})
const pendingUpdates = reactive({})
const completing = ref(false)
const confirmRef = ref(null)

const form = reactive({
  count_number: '',
  warehouse_id: null,
  count_date: new Date().toISOString().split('T')[0],
  notes: ''
})

function genCountNumber() {
  const ts = Date.now().toString(36).toUpperCase()
  return `IC-${ts}`
}

function statusBadge(s) {
  const map = { Draft: 'badge-warning', 'In Progress': 'badge-info', Completed: 'badge-active', Cancelled: 'badge-inactive' }
  return map[s] || 'badge-inactive'
}

function warehouseName(id) {
  if (!id) return '-'
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : `#${id}`
}

function diffText(item) {
  if (item.counted_qty === null || item.counted_qty === undefined) return '-'
  const d = item.counted_qty - item.expected_qty
  return (d >= 0 ? '+' : '') + d.toFixed(2)
}

function diffClass(item) {
  if (item.counted_qty === null || item.counted_qty === undefined) return ''
  const d = item.counted_qty - item.expected_qty
  if (Math.abs(d) < 0.001) return 'col-neutral'
  return d > 0 ? 'col-positive' : 'col-negative'
}

async function load() {
  loading.value = true; error.value = ''
  try {
    const [cRes, wRes] = await Promise.all([
      api.get('/T0105I/'),
      api.get('/T0008I/')
    ])
    counts.value = cRes.data || []
    warehouses.value = wRes.data || []
    await loadItemCounts()
  } catch { error.value = t('failed-load') }
  finally { loading.value = false }
}

async function loadItemCounts() {
  for (const c of counts.value) {
    try {
      const res = await api.get(`/T0106I/by-count/${c.id}`)
      const data = res.data || []
      const total = data.length
      const diffs = data.filter(i => i.counted_qty !== null && Math.abs(i.counted_qty - i.expected_qty) > 0.001).length
      itemCounts[c.id] = { total, diffs }
    } catch { itemCounts[c.id] = { total: 0, diffs: 0 } }
  }
}

async function selectCount(c) {
  selectedId.value = c.id
  selectedStatus.value = c.status
  await loadItems()
}

async function loadItems() {
  if (!selectedId.value) return
  itemsLoading.value = true; itemsError.value = ''
  try {
    const res = await api.get(`/T0106I/by-count/${selectedId.value}`)
    items.value = res.data || []
  } catch { itemsError.value = t('failed-load') }
  finally { itemsLoading.value = false }
}

async function populateItems() {
  if (!selectedId.value) return
  try {
    await api.post(`/T0105I/${selectedId.value}/populate`)
    toast(t('ic-populated', 'Items populated'), 'success')
    await loadItems()
    await loadItemCounts()
  } catch { toast(t('failed-save'), 'error') }
}

async function startCount() {
  if (!selectedId.value) return
  try {
    await api.put(`/T0105I/${selectedId.value}`, { status: 'In Progress' })
    selectedStatus.value = 'In Progress'
    const c = counts.value.find(x => x.id === selectedId.value)
    if (c) c.status = 'In Progress'
    toast(t('ic-started', 'Count started'), 'success')
  } catch { toast(t('failed-save'), 'error') }
}

async function completeCount() {
  if (!selectedId.value) return
  completing.value = true
  try {
    await api.post(`/T0105I/${selectedId.value}/complete`)
    toast(t('ic-completed', 'Count completed'), 'success')
    selectedStatus.value = 'Completed'
    const c = counts.value.find(x => x.id === selectedId.value)
    if (c) c.status = 'Completed'
    await loadItems()
    await loadItemCounts()
  } catch { toast(t('failed-save'), 'error') }
  finally { completing.value = false }
}

function updateCounted(itemId, event) {
  const val = event.target.value
  pendingUpdates[itemId] = { ...(pendingUpdates[itemId] || {}), counted_qty: val === '' ? null : parseFloat(val) }
  debounceSave(itemId)
}

function updateItemNotes(itemId, event) {
  pendingUpdates[itemId] = { ...(pendingUpdates[itemId] || {}), notes: event.target.value }
  debounceSave(itemId)
}

const debounceTimers = {}
function debounceSave(itemId) {
  clearTimeout(debounceTimers[itemId])
  debounceTimers[itemId] = setTimeout(async () => {
    const updates = pendingUpdates[itemId]
    if (!updates) return
    try {
      await api.put(`/T0106I/${itemId}`, updates)
      delete pendingUpdates[itemId]
      const item = items.value.find(i => i.id === itemId)
      if (item) Object.assign(item, updates)
      await loadItemCounts()
    } catch { toast(t('failed-save'), 'error') }
  }, 500)
}

function openAdd() {
  editing.value = false
  form.count_number = genCountNumber()
  form.warehouse_id = null
  form.count_date = new Date().toISOString().split('T')[0]
  form.notes = ''
  showModal.value = true
}

function editCount(c) {
  editing.value = true
  form.count_number = c.count_number
  form.warehouse_id = c.warehouse_id
  form.count_date = c.count_date
  form.notes = c.notes || ''
  editId.value = c.id
  showModal.value = true
}

const editId = ref(null)

function closeModal() { showModal.value = false }

async function save() {
  saving.value = true
  try {
    const payload = { count_number: form.count_number, warehouse_id: form.warehouse_id || null, count_date: form.count_date, notes: form.notes || null }
    if (editing.value) {
      await api.put(`/T0105I/${editId.value}`, payload)
      toast(t('ic-saved', 'Count saved'), 'success')
    } else {
      await api.post('/T0105I/', payload)
      toast(t('ic-saved', 'Count saved'), 'success')
    }
    closeModal(); await load()
  } catch { toast(t('failed-save'), 'error') }
  finally { saving.value = false }
}

async function deleteCount(c) {
  const confirmed = await confirmRef.value?.show(t('confirm-delete'), `${t('confirm-delete-msg')} ${c.count_number}?`)
  if (!confirmed) return
  try {
    await api.delete(`/T0105I/${c.id}`)
    toast(t('ic-deleted', 'Count deleted'), 'success')
    if (selectedId.value === c.id) { selectedId.value = null; items.value = [] }
    await load()
  } catch { toast(t('failed-save'), 'error') }
}

async function deleteItem(item) {
  const confirmed = await confirmRef.value?.show(t('confirm-delete'), `${t('confirm-delete-msg')} ${item.product_name || item.sku}?`)
  if (!confirmed) return
  try {
    await api.delete(`/T0106I/${item.id}`)
    toast(t('ic-item-deleted', 'Item removed'), 'success')
    await loadItems()
    await loadItemCounts()
  } catch { toast(t('failed-save'), 'error') }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state, .empty-state-sm { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-state-sm { padding: 24px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.data-table tbody tr.row-selected { background: #eef2ff; }
.data-table tbody tr.row-diff { background: #fff7ed; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.cell-date { font-family: monospace; font-size: 12px; white-space: nowrap; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.col-positive { color: #16a34a; }
.col-negative { color: #dc2626; }
.col-neutral { color: #999; }
.text-center { text-align: center; }
.detail-section { margin-top: 8px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.detail-header h3 { font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0; }
.detail-actions { display: flex; gap: 8px; }
.form-input-sm { width: 100px; padding: 4px 8px; font-size: 12px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 12px; width: 520px; max-width: 95vw; max-height: 85vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.15); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px 0; }
.modal-header h3 { font-size: 18px; font-weight: 600; color: #1a1a2e; margin: 0; }
.modal-body { padding: 20px 24px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; padding: 0 24px 20px; }
.form-row { display: flex; gap: 16px; }
.form-group { flex: 1; margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #555; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
</style>

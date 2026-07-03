<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('adj-title', 'Stock Adjustments') }}</h1>
        <p class="page-subtitle">{{ t('adj-sub', 'Adjust stock quantities by entering the desired new quantity') }}</p>
      </div>
      <button class="btn-primary" @click="openAdjust">
        <span class="material-symbols-outlined">add</span> {{ t('adj-new', 'New Adjustment') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">swipe_up_alt</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('date', 'Date') }}</th>
              <th>Product</th>
              <th>Warehouse</th>
              <th class="text-center">{{ t('adj-current-qty', 'Current Qty') }}</th>
              <th class="text-center">{{ t('adj-new-qty', 'New Qty') }}</th>
              <th class="text-center">{{ t('stock-qty-change', 'Qty Change') }}</th>
              <th>{{ t('description') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="mono">{{ formatDate(item.created_at) }}</td>
              <td>{{ productName(item.product_id) }}</td>
              <td>{{ warehouseName(item.warehouse_id) }}</td>
              <td class="text-center mono">{{ calcPrevQty(item) }}</td>
              <td class="text-center mono">{{ calcNewQty(item) }}</td>
              <td class="text-center" :class="item.qty_change >= 0 ? 'text-green' : 'text-red'">
                {{ item.qty_change >= 0 ? '+' : '' }}{{ item.qty_change }}
              </td>
              <td class="cell-desc">{{ item.description || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ t('adj-new', 'New Adjustment') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Product <span class="text-red-500">*</span></label>
            <select v-model="form.product_id" class="form-input" @change="onProductOrWarehouseChange">
              <option value="">-- Select --</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.sku }} - {{ p.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Warehouse <span class="text-red-500">*</span></label>
            <select v-model="form.warehouse_id" class="form-input" @change="onProductOrWarehouseChange">
              <option value="">-- Select --</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ t('adj-current-qty', 'Current Quantity') }}</label>
            <div class="form-input readonly-bg">{{ currentQtyText }}</div>
          </div>
          <div class="form-group">
            <label>{{ t('adj-new-qty', 'New Quantity') }} <span class="text-red-500">*</span></label>
            <input type="number" step="0.01" v-model.number="form.new_qty" class="form-input" @input="calcDiff" />
          </div>
          <div v-if="diff !== null" class="form-group">
            <label>{{ t('adj-diff', 'Difference') }}</label>
            <div class="form-input readonly-bg" :class="diff >= 0 ? 'text-green' : 'text-red'">
              {{ diff >= 0 ? '+' : '' }}{{ diff }}
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('description') }}</label>
            <input type="text" v-model="form.description" class="form-input" :placeholder="t('adj-placeholder', 'e.g. Cycle count correction')" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving || !canSave" @click="saveAdjustment">
            {{ saving ? t('saving') : t('save') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
const warehouses = ref([])
const stockLevels = ref({})
const showModal = ref(false)
const saving = ref(false)
const form = ref({ product_id: null, warehouse_id: null, new_qty: 0, description: '' })
const diff = ref(null)
const currentQty = ref(null)

const currentQtyText = computed(() => {
  if (currentQty.value === null) return '-'
  return currentQty.value.toString()
})

const canSave = computed(() => form.value.product_id && form.value.warehouse_id && form.value.new_qty !== '' && form.value.new_qty !== null)

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function productName(id) {
  const p = products.value.find(x => x.id === id)
  return p ? p.name : `#${id}`
}

function warehouseName(id) {
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : `#${id}`
}

function calcPrevQty(item) {
  const before = item.balance_after - item.qty_change
  return Math.round(before * 100) / 100
}

function calcNewQty(item) {
  return item.balance_after
}

function calcDiff() {
  if (currentQty.value !== null && form.value.new_qty !== '' && form.value.new_qty !== null) {
    diff.value = Math.round((form.value.new_qty - currentQty.value) * 100) / 100
  } else {
    diff.value = null
  }
}

async function onProductOrWarehouseChange() {
  diff.value = null
  currentQty.value = null
  if (!form.value.product_id || !form.value.warehouse_id) return
  const key = `${form.value.product_id}-${form.value.warehouse_id}`
  if (stockLevels.value[key] !== undefined) {
    currentQty.value = stockLevels.value[key]
  } else {
    try {
      const res = await api.get('/T0009I/', { params: { product_id: form.value.product_id, warehouse_id: form.value.warehouse_id } })
      const rows = res.data || []
      currentQty.value = rows.length ? Number(rows[0].qty) : 0
      stockLevels.value[key] = currentQty.value
    } catch {
      currentQty.value = 0
    }
  }
  calcDiff()
}

async function loadLookups() {
  try {
    const [pRes, wRes] = await Promise.all([
      api.get('/T0003I/'),
      api.get('/T0008I/').catch(() => ({ data: [] })),
    ])
    products.value = pRes.data || []
    warehouses.value = wRes.data || []
  } catch {}
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0064I/adjustments')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openAdjust() {
  form.value = { product_id: null, warehouse_id: null, new_qty: 0, description: '' }
  diff.value = null
  currentQty.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveAdjustment() {
  saving.value = true
  try {
    await api.post('/T0064I/adjust', {
      product_id: form.value.product_id,
      warehouse_id: form.value.warehouse_id,
      new_qty: form.value.new_qty,
      description: form.value.description || null,
    })
    toast(t('adj-saved', 'Stock adjustment saved'), 'success')
    closeModal()
    await load()
  } catch {
    toast(t('failed-save'), 'error')
  } finally {
    saving.value = false
  }
}

onMounted(() => { loadLookups(); load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.text-red-500 { color: #e53935; }
.text-green { color: #16a34a; font-weight: 600; }
.text-red { color: #dc2626; font-weight: 600; }
.cell-desc { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #666; }

.readonly-bg { background: #f9f9fb !important; color: #555; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; min-height: 16px; }

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
.modal { background: #fff; border-radius: 12px; width: 520px; max-width: 90vw; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid #eee; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; transition: border-color 0.15s; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
</style>

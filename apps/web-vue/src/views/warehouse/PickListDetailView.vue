<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load(true)" />
    <template v-else-if="pickList">
      <!-- Top navigation & header -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/warehouse/pick-lists')">&larr; {{ t('back-to-pick-lists', 'Back to Pick Lists') }}</button>
          <div class="flex items-center gap-3">
            <h1 class="page-title">{{ t('pick-list', 'Pick List') }} {{ pickList.pick_list_number }}</h1>
            <span class="badge badge-fefo">
              <span class="material-symbols-outlined icon-xs">bolt</span>
              FEFO Picking
            </span>
          </div>
        </div>
        <div class="flex gap-2">
          <button v-if="pickList.status === 'Pending'" class="btn-primary" @click="startPicking">
            <span class="material-symbols-outlined">play_arrow</span> {{ t('start-picking', 'Start Picking') }}
          </button>
          <button v-if="pickList.status === 'In Progress'" class="btn-primary" @click="completePicking" :disabled="!allPicked || completing">
            <span v-if="completing" class="material-symbols-outlined spin">progress_activity</span>
            <span v-else class="material-symbols-outlined">check_circle</span>
            {{ completing ? t('completing', 'Completing...') : t('complete-picking', 'Complete Picking') }}
          </button>
        </div>
      </div>

      <!-- Pick List Summary Card -->
      <div class="detail-card mb-4">
        <div class="grid-stats">
          <div class="info-row">
            <span class="info-label">{{ t('status', 'Status') }}:</span>
            <span class="badge" :class="statusBadge">{{ pickList.status }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('order', 'Order') }}:</span>
            <a class="order-link" @click="$router.push(`/sales/${pickList.sales_order_id}`)">#{{ pickList.sales_order_id }}</a>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('warehouse', 'Warehouse') }}:</span>
            <span>{{ warehouseName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('progress', 'Progress') }}:</span>
            <span class="font-bold">{{ pickList.progress_pct || 0 }}%</span>
          </div>
        </div>

        <div class="progress-bar-wrap mt-3">
          <div class="progress-bar" :style="{ width: (pickList.progress_pct || 0) + '%' }"></div>
        </div>
        <div class="flex justify-between text-xs text-muted mt-1">
          <span>{{ pickedLinesCount }} / {{ items.length }} {{ t('items-picked', 'lines completed') }}</span>
          <span>{{ totalPickedQty }} / {{ totalOrderedQty }} {{ t('units-picked', 'units picked') }}</span>
        </div>
      </div>

      <!-- Quick Barcode / Lot Scanner Bar for In Progress Picking -->
      <div v-if="pickList.status === 'In Progress'" class="scanner-card mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined scanner-icon">qr_code_scanner</span>
          <div class="flex-1">
            <label class="scanner-label">{{ t('quick-scan', 'Quick Lot / Barcode Scan') }}</label>
            <div class="flex gap-2">
              <input
                type="text"
                v-model="globalScan"
                class="form-input scanner-input"
                :placeholder="t('scan-placeholder', 'Scan barcode or type lot number then press Enter to pick...')"
                @keyup.enter="onGlobalScan"
              />
              <button class="btn-secondary" @click="onGlobalScan" :disabled="!globalScan.trim()">
                <span class="material-symbols-outlined">search</span> {{ t('match-lot', 'Match & Pick') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Items to Pick Table -->
      <div class="data-card">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3 class="card-title">{{ t('items-to-pick', 'Items to Pick') }}</h3>
            <p class="card-subtitle">{{ t('items-fefo-desc', 'FEFO-suggested lots based on earliest expiration dates. Pickers can select or scan alternative lots if needed.') }}</p>
          </div>
          <div v-if="pickList.status === 'In Progress'" class="flex gap-2">
            <button class="btn-outline btn-sm" @click="pickAllRemaining">
              <span class="material-symbols-outlined icon-xs">done_all</span> {{ t('pick-all-suggested', 'Pick All Suggested') }}
            </button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-8">#</th>
                <th>{{ t('product', 'Product') }}</th>
                <th>{{ t('suggested-fefo-lot', 'Suggested Lot (FEFO)') }}</th>
                <th>{{ t('expiry-date', 'Expiry Date') }}</th>
                <th>{{ t('picked-lot-override', 'Picked Lot Selection') }}</th>
                <th class="col-num">{{ t('qty-ordered', 'Ordered') }}</th>
                <th class="col-num">{{ t('qty-picked', 'Picked') }}</th>
                <th class="text-center" v-if="pickList.status === 'In Progress'">{{ t('pick-action', 'Action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id" :class="{ 'row-picked': isItemFullyPicked(item) }">
                <td class="cell-mono">{{ item.line_number }}</td>
                <td>
                  <strong>{{ item.product_name || `#${item.product_id}` }}</strong>
                  <span v-if="item.product_id" class="text-muted text-xs block">ID: #{{ item.product_id }}</span>
                </td>

                <!-- Suggested FEFO Lot -->
                <td>
                  <div v-if="item.batch_number" class="flex items-center gap-1">
                    <span class="badge badge-batch">
                      <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                      {{ item.batch_number }}
                    </span>
                  </div>
                  <span v-else class="text-muted text-xs">{{ t('none', 'Standard Stock') }}</span>
                </td>

                <!-- Suggested Expiry Date -->
                <td>
                  <div v-if="item.expiry_date" :class="getExpiryClass(item.expiry_date)">
                    <span>{{ formatDate(item.expiry_date) }}</span>
                    <span v-if="isExpired(item.expiry_date)" class="badge-tag-danger">EXPIRED</span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Picked Lot / Alternative Lot Selector -->
                <td>
                  <!-- While picking is In Progress: dropdown + scan override -->
                  <div v-if="pickList.status === 'In Progress'" class="lot-picker-cell">
                    <div class="lot-controls">
                      <!-- Dropdown of available lots -->
                      <select
                        class="form-input form-input-sm lot-select"
                        :value="lineState[item.id]?.selectedBatchId || ''"
                        @change="onBatchSelect(item, $event.target.value)"
                      >
                        <option value="">
                          {{ item.batch_number ? `Suggested (${item.batch_number})` : '-- Select Alternative Lot --' }}
                        </option>
                        <option
                          v-for="b in (availableBatches[item.id] || [])"
                          :key="b.id"
                          :value="b.id"
                        >
                          Lot: {{ b.batch_number }} (Exp: {{ formatDate(b.expiry_date) }}, Stock: {{ b.quantity }})
                        </option>
                      </select>

                      <!-- Inline Scan or manual entry toggle/input -->
                      <div class="flex items-center gap-1 mt-1">
                        <input
                          type="text"
                          class="form-input form-input-xs batch-input"
                          :placeholder="t('scan-lot-or-manual', 'Scan / Manual Lot #')"
                          v-model="lineState[item.id].scanInput"
                          @keyup.enter="onScanLot(item)"
                        />
                        <button
                          type="button"
                          class="btn-icon btn-xs"
                          :title="t('apply-lot', 'Apply Scanned Lot')"
                          @click="onScanLot(item)"
                          :disabled="!lineState[item.id]?.scanInput?.trim()"
                        >
                          <span class="material-symbols-outlined icon-xs">check</span>
                        </button>
                      </div>

                      <!-- Current active selection indicator -->
                      <div v-if="lineState[item.id]?.selectedBatchNumber" class="selected-batch-indicator mt-1">
                        <span class="badge badge-picked-lot" :class="{ 'badge-override': lineState[item.id]?.selectedBatchNumber !== item.batch_number }">
                          <span class="material-symbols-outlined icon-xs">
                            {{ lineState[item.id]?.selectedBatchNumber === item.batch_number ? 'check_circle' : 'swap_horiz' }}
                          </span>
                          Picked Lot: {{ lineState[item.id]?.selectedBatchNumber }}
                          <span v-if="lineState[item.id]?.selectedBatchNumber !== item.batch_number" class="override-tag">OVERRIDE</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- Completed or Pending: Display picked lot -->
                  <div v-else>
                    <span v-if="item.picked_batch_number" class="badge badge-batch badge-batch-completed">
                      <span class="material-symbols-outlined icon-xs">verified</span>
                      {{ item.picked_batch_number }}
                    </span>
                    <span v-else-if="item.batch_number" class="badge badge-batch">
                      <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                      {{ item.batch_number }}
                    </span>
                    <span v-else class="text-muted text-xs">-</span>
                  </div>
                </td>

                <td class="col-num font-bold">{{ item.qty_ordered }}</td>
                <td class="col-num" :class="{ 'text-green': item.qty_picked >= item.qty_ordered }">
                  {{ item.qty_picked }}
                </td>

                <!-- In Progress Pick Actions -->
                <td class="text-center" v-if="pickList.status === 'In Progress'">
                  <div class="pick-actions-wrap">
                    <input
                      type="number"
                      class="pick-input"
                      step="any"
                      min="0"
                      :max="item.qty_ordered"
                      v-model.number="lineState[item.id].pickQty"
                      @keyup.enter="savePick(item)"
                    />
                    <button
                      class="btn-primary btn-sm btn-pick"
                      :disabled="lineState[item.id]?.saving"
                      @click="savePick(item)"
                      :title="t('save-pick', 'Update Pick Quantity')"
                    >
                      <span v-if="lineState[item.id]?.saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                      <span v-else class="material-symbols-outlined icon-xs">check</span>
                      {{ t('pick', 'Pick') }}
                    </button>
                    <button
                      v-if="item.qty_picked < item.qty_ordered"
                      class="btn-outline btn-xs"
                      :title="t('pick-full', 'Pick Full Qty')"
                      @click="pickFullQty(item)"
                    >
                      All
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const completing = ref(false)
const error = ref('')
const pickList = ref(null)
const items = ref([])
const warehouses = ref([])
const availableBatches = ref({})
const lineState = reactive({})
const globalScan = ref('')

const statusBadge = computed(() => {
  const map = {
    Pending: 'badge-warning',
    'In Progress': 'badge-info',
    Completed: 'badge-active',
    Cancelled: 'badge-inactive'
  }
  return map[pickList.value?.status] || 'badge-inactive'
})

const warehouseName = computed(() => {
  if (!pickList.value?.warehouse_id) return '-'
  const w = warehouses.value.find(x => x.id === pickList.value.warehouse_id)
  return w ? w.name : `#${pickList.value.warehouse_id}`
})

const allPicked = computed(() => {
  return items.value.length > 0 && items.value.every(i => (i.qty_picked || 0) >= (i.qty_ordered || 0))
})

const pickedLinesCount = computed(() => {
  return items.value.filter(i => (i.qty_picked || 0) >= (i.qty_ordered || 0)).length
})

const totalOrderedQty = computed(() => {
  return items.value.reduce((acc, i) => acc + (Number(i.qty_ordered) || 0), 0)
})

const totalPickedQty = computed(() => {
  return items.value.reduce((acc, i) => acc + (Number(i.qty_picked) || 0), 0)
})

function isItemFullyPicked(item) {
  return (item.qty_picked || 0) >= (item.qty_ordered || 0) && item.qty_ordered > 0
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function isExpired(d) {
  if (!d) return false
  return new Date(d) < new Date()
}

function getExpiryClass(d) {
  if (!d) return ''
  if (isExpired(d)) return 'text-red font-semibold'
  const exp = new Date(d)
  const daysUntil = (exp - new Date()) / (1000 * 60 * 60 * 24)
  if (daysUntil <= 30) return 'text-amber font-semibold'
  return 'text-green'
}

async function load(showSkeleton = true) {
  if (showSkeleton) loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [detailRes, whRes] = await Promise.all([
      api.get(`/T0101I/${id}/detail`),
      api.get('/T0008I/').catch(() => ({ data: [] })),
    ])
    const data = detailRes.data
    pickList.value = { ...data }
    items.value = data.items || []
    warehouses.value = whRes.data || []

    // Initialize lineState
    for (const item of items.value) {
      const existing = lineState[item.id]
      lineState[item.id] = {
        pickQty: existing ? existing.pickQty : (item.qty_picked !== undefined && item.qty_picked !== null ? item.qty_picked : item.qty_ordered),
        selectedBatchId: item.picked_batch_id || item.batch_id || null,
        selectedBatchNumber: item.picked_batch_number || item.batch_number || '',
        scanInput: '',
        saving: false
      }
    }

    // Fetch available batches for all items if In Progress
    if (pickList.value.status === 'In Progress') {
      await Promise.all(
        items.value.map(item => fetchAvailableBatches(item.id))
      )
    }
  } catch (err) {
    console.error('Error loading pick list:', err)
    error.value = t('failed-load', 'Failed to load pick list')
  } finally {
    loading.value = false
  }
}

async function fetchAvailableBatches(itemId) {
  try {
    const res = await api.get(`/T0101I/${pickList.value.id}/items/${itemId}/available-batches`)
    availableBatches.value[itemId] = res.data || []
  } catch {
    availableBatches.value[itemId] = []
  }
}

function onBatchSelect(item, batchId) {
  const state = lineState[item.id]
  if (!state) return

  if (!batchId) {
    // Reset to suggested batch
    state.selectedBatchId = item.batch_id || null
    state.selectedBatchNumber = item.batch_number || ''
    return
  }

  const numId = Number(batchId)
  const batches = availableBatches.value[item.id] || []
  const found = batches.find(b => b.id === numId)
  if (found) {
    state.selectedBatchId = found.id
    state.selectedBatchNumber = found.batch_number
    toast(`Selected lot ${found.batch_number}`, 'info')
  }
}

function onScanLot(item) {
  const state = lineState[item.id]
  if (!state) return
  const scanned = (state.scanInput || '').trim()
  if (!scanned) return

  const batches = availableBatches.value[item.id] || []
  const matched = batches.find(b => (b.batch_number || '').toLowerCase() === scanned.toLowerCase())

  if (matched) {
    state.selectedBatchId = matched.id
    state.selectedBatchNumber = matched.batch_number
    toast(`Matched available lot ${matched.batch_number}`, 'success')
  } else {
    // Custom/external lot barcode
    state.selectedBatchId = null
    state.selectedBatchNumber = scanned
    toast(`Lot override set to "${scanned}"`, 'info')
  }
  state.scanInput = ''
}

function onGlobalScan() {
  const code = globalScan.value.trim()
  if (!code) return

  const lowerCode = code.toLowerCase()
  let matchedItem = null
  let matchedBatch = null

  // 1. Try matching with available lots or suggested lot across items
  for (const item of items.value) {
    const batches = availableBatches.value[item.id] || []
    const b = batches.find(x => (x.batch_number || '').toLowerCase() === lowerCode)
    if (b) {
      matchedItem = item
      matchedBatch = b
      break
    }
    if ((item.batch_number || '').toLowerCase() === lowerCode) {
      matchedItem = item
      break
    }
  }

  // 2. If not found by lot, try matching by product name / ID
  if (!matchedItem) {
    matchedItem = items.value.find(i =>
      String(i.product_id) === code ||
      (i.product_name && i.product_name.toLowerCase().includes(lowerCode))
    )
  }

  if (matchedItem) {
    const state = lineState[matchedItem.id]
    if (state) {
      if (matchedBatch) {
        state.selectedBatchId = matchedBatch.id
        state.selectedBatchNumber = matchedBatch.batch_number
      }
      state.pickQty = matchedItem.qty_ordered
      savePick(matchedItem)
      toast(`Scanned code matched for "${matchedItem.product_name || 'item'}"`, 'success')
      globalScan.value = ''
      return
    }
  }

  toast(`No matching item or lot found for "${code}"`, 'error')
}

async function savePick(item) {
  const state = lineState[item.id]
  if (!state) return

  const qty = parseFloat(state.pickQty)
  if (isNaN(qty) || qty < 0) {
    toast(t('invalid-qty', 'Please enter a valid pick quantity'), 'error')
    return
  }
  if (qty > item.qty_ordered) {
    toast(`Picked quantity (${qty}) cannot exceed ordered quantity (${item.qty_ordered})`, 'error')
    return
  }

  state.saving = true
  try {
    const payload = {
      qty_picked: qty,
      picked_batch_id: state.selectedBatchId !== null && state.selectedBatchId !== undefined ? Number(state.selectedBatchId) : null,
      picked_batch_number: state.selectedBatchNumber ? String(state.selectedBatchNumber).trim() : null
    }

    const res = await api.post(`/T0101I/${pickList.value.id}/pick-item/${item.id}`, payload)
    item.qty_picked = res.data.qty_picked
    item.picked_batch_id = res.data.picked_batch_id
    item.picked_batch_number = res.data.picked_batch_number

    toast(t('pick-updated', `Line #${item.line_number} pick recorded`), 'success')
    await load(false)
  } catch (e) {
    console.error('Pick error:', e)
    toast(e.response?.data?.detail || t('failed-pick', 'Failed to update pick'), 'error')
  } finally {
    state.saving = false
  }
}

function pickFullQty(item) {
  const state = lineState[item.id]
  if (!state) return
  state.pickQty = item.qty_ordered
  if (!state.selectedBatchId && item.batch_id) {
    state.selectedBatchId = item.batch_id
    state.selectedBatchNumber = item.batch_number
  }
  savePick(item)
}

async function pickAllRemaining() {
  const pendingItems = items.value.filter(i => (i.qty_picked || 0) < (i.qty_ordered || 0))
  if (!pendingItems.length) {
    toast(t('all-already-picked', 'All items are already fully picked'), 'info')
    return
  }

  for (const item of pendingItems) {
    const state = lineState[item.id]
    if (state) {
      state.pickQty = item.qty_ordered
      if (!state.selectedBatchId && item.batch_id) {
        state.selectedBatchId = item.batch_id
        state.selectedBatchNumber = item.batch_number
      }
      try {
        await api.post(`/T0101I/${pickList.value.id}/pick-item/${item.id}`, {
          qty_picked: item.qty_ordered,
          picked_batch_id: state.selectedBatchId,
          picked_batch_number: state.selectedBatchNumber
        })
      } catch (err) {
        console.error('Error picking item:', err)
      }
    }
  }
  toast(t('all-picked-success', 'All suggested lots picked successfully'), 'success')
  await load(false)
}

async function startPicking() {
  try {
    await api.post(`/T0101I/${pickList.value.id}/start`)
    toast(t('picking-started', 'Picking started'), 'success')
    await load(false)
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-start', 'Failed to start picking'), 'error')
  }
}

async function completePicking() {
  completing.value = true
  try {
    await api.post(`/T0101I/${pickList.value.id}/complete`)
    toast(t('picking-completed', 'Pick list completed — sales order marked as shipped and lot inventory deducted'), 'success')
    await load(false)
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-complete', 'Failed to complete picking'), 'error')
  } finally {
    completing.value = false
  }
}

onMounted(() => {
  load(true)
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mb-4 { margin-bottom: 16px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.block { display: block; }
.w-8 { width: 32px; }

.text-muted { color: #888; }
.text-xs { font-size: 11px; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.text-green { color: #16a34a; }
.text-amber { color: #d97706; }
.text-red { color: #dc2626; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.order-link { color: #5d3fd3; cursor: pointer; font-weight: 600; }
.order-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { display: inline-flex; align-items: center; gap: 6px; background: #f0f0f4; color: #333; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover:not(:disabled) { background: #e2e2ea; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-outline { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; background: transparent; color: #5d3fd3; border: 1px solid #ddd6fe; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f3ff; }

.btn-sm { padding: 5px 12px; font-size: 12px; }
.btn-xs { padding: 3px 8px; font-size: 11px; }

.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; cursor: pointer; color: #555; }
.btn-icon:hover:not(:disabled) { background: #f1f5f9; color: #5d3fd3; border-color: #5d3fd3; }
.btn-icon:disabled { opacity: 0.4; cursor: not-allowed; }

.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.info-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 75px; }

.progress-bar-wrap { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.progress-bar { height: 100%; background: #5d3fd3; border-radius: 4px; transition: width 0.3s; }

/* Quick Scanner Card */
.scanner-card { background: #fdfaff; border: 1px dashed #c4b5fd; border-radius: 12px; padding: 14px 18px; }
.scanner-icon { font-size: 32px; color: #5d3fd3; }
.scanner-label { display: block; font-size: 11px; font-weight: 700; color: #5d3fd3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.scanner-input { background: #fff; border-color: #c4b5fd; font-family: monospace; font-size: 13px; }

/* Data Card & Table */
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0; }
.card-subtitle { font-size: 12px; color: #64748b; margin: 2px 0 0; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
.data-table tbody tr:hover { background: #fafaff; }
.row-picked { background: #f8fdf9 !important; }

.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }

/* Lot selector & picking inputs */
.lot-picker-cell { min-width: 220px; }
.lot-controls { display: flex; flex-direction: column; }
.lot-select { width: 100%; font-size: 11px; padding: 4px 6px; }
.batch-input { width: 100%; font-family: monospace; font-size: 11px; color: #5d3fd3; }

.pick-actions-wrap { display: flex; align-items: center; justify-content: center; gap: 6px; }
.pick-input { width: 64px; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; text-align: center; font-weight: 600; font-family: monospace; }
.pick-input:focus { border-color: #5d3fd3; outline: none; }
.btn-pick { padding: 4px 10px; }

/* Badges */
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-fefo { background: #ede9fe; color: #5d3fd3; font-size: 11px; padding: 3px 10px; border-radius: 6px; border: 1px solid #ddd6fe; }

.badge-batch { background: #f3f0ff; color: #5d3fd3; border: 1px solid #ddd6fe; padding: 2px 8px; border-radius: 6px; font-family: monospace; font-size: 11px; font-weight: 600; }
.badge-batch-completed { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.badge-picked-lot { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 10px; font-weight: 600; }
.badge-picked-lot.badge-override { background: #fffbeb; color: #b45309; border-color: #fde68a; }
.override-tag { margin-left: 4px; padding: 1px 3px; font-size: 8px; background: #fbbf24; color: #78350f; border-radius: 3px; font-weight: 800; }
.badge-tag-danger { display: inline-block; margin-left: 6px; padding: 1px 4px; font-size: 9px; background: #fee2e2; color: #b91c1c; border-radius: 4px; font-weight: 700; }

.form-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
.form-input-sm { padding: 4px 8px; font-size: 12px; border-radius: 6px; }
.form-input-xs { padding: 3px 6px; font-size: 11px; border-radius: 4px; }
select.form-input { appearance: auto; }

.icon-xs { font-size: 14px !important; vertical-align: middle; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
</style>


<template>
  <div :dir="dir" class="replenishment-view">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('replenishment-title', 'Inter-Branch Replenishment Suggestions') }}</h1>
        <p class="page-subtitle">{{ t('replenishment-sub', 'Automated inventory rebalancing recommendations based on branch reorder points and central hub surplus') }}</p>
      </div>
      <div class="page-actions">
        <router-link to="/warehouse/transfers" class="btn-outline">
          <span class="material-symbols-outlined">local_shipping</span>
          {{ t('stock-transfers', 'Stock Transfers') }}
        </router-link>
        <button class="btn-outline" @click="loadData(true)" :disabled="loading">
          <span :class="['material-symbols-outlined', { 'animate-spin': loading }]">refresh</span>
          {{ t('refresh-suggestions', 'Refresh') }}
        </button>
        <button
          class="btn-primary"
          :disabled="loading || (!filteredSuggestions.length && !selectedSuggestions.length)"
          @click="openGenerateModal(selectedSuggestions.length ? 'selected' : 'all')"
        >
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ selectedSuggestions.length ? t('generate-selected', `Generate Transfers (${selectedSuggestions.length})`).replace('{count}', selectedSuggestions.length) : t('generate-transfers-btn', 'Generate Transfers') }}
        </button>
      </div>
    </div>

    <!-- Summary KPI Metrics Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ summary.total_deficits }}</div>
        <div class="stat-lbl">{{ t('total-deficits', 'Total Deficits') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num critical">{{ summary.critical_deficits }}</div>
        <div class="stat-lbl">{{ t('critical-deficits', 'Critical Stockouts') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num high">{{ summary.high_deficits }}</div>
        <div class="stat-lbl">{{ t('high-deficits', 'High Priority') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num in-transit">{{ summary.active_in_transit_transfers }}</div>
        <div class="stat-lbl">{{ t('active-transfers', 'In-Transit Shipments') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num monitored">{{ summary.total_products }}</div>
        <div class="stat-lbl">{{ t('monitored-skus', 'Monitored SKUs') }}</div>
      </div>
    </div>

    <!-- Filters & Evaluation Parameters Toolbar -->
    <div class="filters-bar data-card">
      <div class="filters-top">
        <div class="search-box">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            v-model="searchQuery"
            class="form-input search-input"
            :placeholder="t('search-suggestions-ph', 'Search by SKU, product name, warehouse, or reason...')"
          />
          <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''" type="button">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="filter-controls">
          <!-- Destination Warehouse Filter -->
          <select v-model="destWarehouseFilter" class="form-input filter-select">
            <option :value="null">{{ t('all-destinations', 'All Destination Branches') }}</option>
            <option v-for="wh in branchWarehouses" :key="'dest-' + wh.id" :value="wh.id">
              {{ wh.name }}
            </option>
          </select>

          <!-- Source Warehouse Filter -->
          <select v-model="sourceWarehouseFilter" class="form-input filter-select">
            <option :value="null">{{ t('all-sources', 'All Source Hubs') }}</option>
            <option v-for="wh in sourceWarehouses" :key="'src-' + wh.id" :value="wh.id">
              {{ wh.name }}
            </option>
          </select>

          <!-- Priority Filter -->
          <select v-model="priorityFilter" class="form-input filter-select">
            <option value="">{{ t('all-priorities', 'All Priorities') }}</option>
            <option value="Critical">{{ t('priority-critical', 'Critical') }}</option>
            <option value="High">{{ t('priority-high', 'High') }}</option>
            <option value="Normal">{{ t('priority-normal', 'Normal') }}</option>
            <option value="Low">{{ t('priority-low', 'Low') }}</option>
          </select>

          <button
            class="btn-outline btn-sm toggle-params-btn"
            :class="{ active: showParamControls }"
            @click="showParamControls = !showParamControls"
            type="button"
          >
            <span class="material-symbols-outlined">tune</span>
            {{ t('tuning-parameters', 'Parameters') }}
          </button>

          <button v-if="hasActiveFilters" class="btn-outline btn-sm reset-btn" @click="resetFilters" type="button">
            <span class="material-symbols-outlined">filter_alt_off</span>
            {{ t('reset-filters', 'Reset') }}
          </button>
        </div>
      </div>

      <!-- Advanced Calculation Tuning Parameters Bar (Collapsible) -->
      <div v-if="showParamControls" class="params-panel">
        <div class="params-header">
          <span class="material-symbols-outlined icon-sm">settings_suggest</span>
          <span class="params-title">{{ t('tuning-parameters', 'Replenishment Calculation Parameters') }}</span>
        </div>
        <div class="params-grid">
          <div class="param-field">
            <label>{{ t('safety-stock-ratio', 'Safety Stock Ratio') }} ({{ Math.round(params.safety_stock_ratio * 100) }}%)</label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              v-model.number="params.safety_stock_ratio"
              class="form-range"
            />
          </div>
          <div class="param-field">
            <label>{{ t('target-multiplier', 'Target Coverage Multiplier') }} ({{ params.target_coverage_multiplier }}x)</label>
            <input
              type="range"
              min="1.0"
              max="3.0"
              step="0.1"
              v-model.number="params.target_coverage_multiplier"
              class="form-range"
            />
          </div>
          <div class="param-field">
            <label>{{ t('min-deficit', 'Min Deficit Qty') }}</label>
            <input
              type="number"
              min="0"
              step="1"
              v-model.number="params.min_deficit"
              class="form-input form-input-sm"
            />
          </div>
          <div class="param-actions">
            <button class="btn-primary btn-sm" @click="applyParameters" :disabled="loading">
              <span class="material-symbols-outlined icon-xs">check</span>
              {{ t('apply-params', 'Apply') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Table & State Handlers -->
    <SkeletonTable v-if="loading" :rows="6" :columns="8" />
    <ErrorState v-else-if="error" :message="error" @retry="loadData(true)" />

    <!-- Empty State: Healthy Network or Filtered Out -->
    <div v-else-if="!filteredSuggestions.length" class="empty-state data-card">
      <span class="material-symbols-outlined empty-icon healthy-icon">verified</span>
      <p class="empty-title">
        {{ hasActiveFilters ? t('no-suggestions-filtered', 'No replenishment recommendations match the active filter criteria.') : t('no-suggestions-title', 'All Warehouses Adequately Stocked') }}
      </p>
      <p class="empty-subtitle">
        {{ hasActiveFilters ? t('no-transfers-filtered', 'Try clearing your filters to see more results.') : t('no-suggestions-sub', 'No replenishment deficits detected across the branch network. All product inventory is above reorder thresholds.') }}
      </p>
      <div class="empty-actions">
        <button v-if="hasActiveFilters" class="btn-outline" @click="resetFilters">
          {{ t('clear-filters', 'Clear Filters') }}
        </button>
        <button class="btn-outline" @click="loadData(true)">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('refresh-suggestions', 'Refresh') }}
        </button>
      </div>
    </div>

    <!-- Recommendations Table -->
    <div v-else class="data-card">
      <div class="table-actions-header">
        <div class="selection-info">
          <label class="checkbox-container">
            <input
              type="checkbox"
              :checked="isAllSelected"
              :indeterminate="isIndeterminate"
              @change="toggleSelectAll"
            />
            <span class="checkmark"></span>
          </label>
          <span class="text-sm font-medium">
            <template v-if="selectedSuggestions.length">
              {{ selectedSuggestions.length }} of {{ filteredSuggestions.length }} items selected
            </template>
            <template v-else>
              {{ filteredSuggestions.length }} replenishment recommendations
            </template>
          </span>
        </div>

        <div v-if="selectedSuggestions.length" class="bulk-actions">
          <button class="btn-outline btn-xs" @click="clearSelection">
            {{ t('deselect-all', 'Deselect All') }}
          </button>
          <button class="btn-primary btn-sm" @click="openGenerateModal('selected')">
            <span class="material-symbols-outlined icon-xs">auto_awesome</span>
            {{ t('generate-selected', `Generate Transfers (${selectedSuggestions.length})`).replace('{count}', selectedSuggestions.length) }}
          </button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="col-checkbox"></th>
              <th>{{ t('product', 'Product SKU & Name') }}</th>
              <th>{{ t('dest-branch', 'Destination Branch') }}</th>
              <th class="text-center">{{ t('status', 'Stock Position') }}</th>
              <th class="text-center">{{ t('priority', 'Priority & Deficit') }}</th>
              <th>{{ t('source-hub', 'Matched Source Hub') }}</th>
              <th class="text-center">{{ t('suggested-qty', 'Suggested Qty') }}</th>
              <th class="col-actions">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredSuggestions"
              :key="itemKey(item)"
              :class="{
                'row-critical': item.priority === 'Critical',
                'row-selected': isItemSelected(item),
              }"
            >
              <!-- Checkbox -->
              <td class="col-checkbox">
                <label class="checkbox-container">
                  <input
                    type="checkbox"
                    :checked="isItemSelected(item)"
                    @change="toggleItemSelection(item)"
                  />
                  <span class="checkmark"></span>
                </label>
              </td>

              <!-- Product Info -->
              <td class="cell-product">
                <div class="prod-code font-mono">{{ item.product_code || `#${item.product_id}` }}</div>
                <div class="prod-name font-semibold">{{ item.product_name || `Product #${item.product_id}` }}</div>
              </td>

              <!-- Destination Branch -->
              <td class="cell-destination">
                <div class="branch-name">{{ item.destination_warehouse_name || getWarehouseName(item.destination_warehouse_id) }}</div>
                <div class="stock-pills">
                  <span class="stock-pill" :class="{ 'pill-zero': item.available_stock <= 0 }">
                    Avail: {{ item.available_stock }}
                  </span>
                  <span v-if="item.in_transit_stock > 0" class="stock-pill pill-transit">
                    +{{ item.in_transit_stock }} In Transit
                  </span>
                </div>
              </td>

              <!-- Stock Position / Health Meter -->
              <td class="cell-position">
                <div class="stock-meter-wrap">
                  <div class="meter-labels">
                    <span class="text-xs text-muted">Reorder: {{ item.reorder_point }}</span>
                    <span class="text-xs text-muted">Safety: {{ item.safety_stock }}</span>
                  </div>
                  <div class="meter-bar">
                    <div
                      class="meter-fill"
                      :class="meterFillClass(item)"
                      :style="{ width: meterPercent(item) + '%' }"
                    ></div>
                  </div>
                </div>
              </td>

              <!-- Priority & Deficit Badge -->
              <td class="cell-priority text-center">
                <span :class="['priority-badge', priorityBadgeClass(item.priority)]">
                  <span class="material-symbols-outlined priority-icon">{{ priorityIcon(item.priority) }}</span>
                  {{ item.priority }}
                </span>
                <div class="reason-text" :title="item.reason">{{ item.reason }}</div>
              </td>

              <!-- Matched Source Warehouse -->
              <td class="cell-source">
                <template v-if="item.source_warehouse_id">
                  <div class="source-name font-medium">
                    {{ item.source_warehouse_name || getWarehouseName(item.source_warehouse_id) }}
                  </div>
                  <div class="source-avail-badge">
                    <span class="material-symbols-outlined icon-xs">warehouse</span>
                    {{ item.source_available_stock !== undefined ? `${item.source_available_stock} avail` : 'Available' }}
                  </div>
                </template>
                <template v-else>
                  <span class="text-muted text-xs italic">{{ t('no-source-avail', 'No surplus stock in network') }}</span>
                </template>
              </td>

              <!-- Suggested Transfer Qty (Editable) -->
              <td class="cell-qty text-center">
                <div class="qty-input-wrap">
                  <input
                    type="number"
                    min="1"
                    step="1"
                    v-model.number="item.suggested_transfer_qty"
                    class="form-input form-input-sm qty-input text-center font-mono font-bold"
                  />
                </div>
              </td>

              <!-- Row Action -->
              <td class="col-actions">
                <button
                  type="button"
                  class="btn-outline btn-xs"
                  :disabled="!item.source_warehouse_id"
                  @click="openSingleTransferModal(item)"
                  :title="t('single-transfer-btn', 'Transfer Now')"
                >
                  <span class="material-symbols-outlined icon-xs">arrow_forward</span>
                  {{ t('single-transfer-btn', 'Transfer Now') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- Batch Generate Transfers Modal                                       -->
    <!-- =================================================================== -->
    <div v-if="showGenerateModal" class="modal-overlay" @click.self="closeGenerateModal">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">{{ t('generate-modal-title', 'Generate Replenishment Stock Transfers') }}</h3>
            <p class="modal-subtitle">{{ t('generate-modal-sub', 'The following items will be automatically grouped into transfer orders by source and destination warehouses.') }}</p>
          </div>
          <button class="btn-icon" @click="closeGenerateModal" aria-label="Close" type="button">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="submitGenerateTransfers" class="modal-body">
          <!-- Grouped Routes Preview -->
          <div class="grouped-preview-section">
            <h4 class="section-subtitle">
              <span class="material-symbols-outlined">fork_right</span>
              {{ t('grouped-orders-preview', 'Transfer Orders Grouping Preview') }} ({{ transferGroups.length }} {{ transferGroups.length === 1 ? 'Order' : 'Orders' }})
            </h4>

            <div class="groups-grid">
              <div
                v-for="(group, gIdx) in transferGroups"
                :key="'grp-' + gIdx"
                class="group-card"
              >
                <div class="group-header">
                  <div class="group-title">
                    <span class="group-tag">{{ t('transfer-order-count', `Transfer Order #${gIdx + 1}`).replace('{index}', gIdx + 1) }}</span>
                    <span class="font-semibold">{{ group.source_name }}</span>
                    <span class="material-symbols-outlined route-arrow">arrow_forward</span>
                    <span class="font-semibold">{{ group.dest_name }}</span>
                  </div>
                  <div class="group-meta">
                    <span class="badge badge-info">{{ group.items.length }} {{ group.items.length === 1 ? 'item' : 'items' }}</span>
                    <span class="badge badge-default font-mono">{{ group.totalQty }} units</span>
                  </div>
                </div>

                <div class="group-items-list">
                  <div
                    v-for="(itm, iIdx) in group.items"
                    :key="'itm-' + iIdx"
                    class="group-item-row"
                  >
                    <span class="item-name font-mono text-xs">{{ itm.product_code || `#${itm.product_id}` }} - {{ itm.product_name }}</span>
                    <span class="item-qty font-mono font-bold">{{ itm.suggested_transfer_qty }} units</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Transfer Order Logistics Parameters -->
          <div class="modal-form-grid">
            <div class="form-group">
              <label>{{ t('transfer-date', 'Transfer Date') }} <span class="required">*</span></label>
              <input type="date" v-model="generateForm.transfer_date" class="form-input" required />
            </div>

            <div class="form-group">
              <label>{{ t('expected-delivery-date', 'Expected Delivery Date') }}</label>
              <input type="date" v-model="generateForm.expected_delivery_date" class="form-input" />
            </div>

            <div class="form-group">
              <label>{{ t('carrier-name', 'Logistics Carrier / Transport Provider') }}</label>
              <input
                type="text"
                v-model="generateForm.carrier"
                class="form-input"
                placeholder="e.g. Internal Fleet, Central Hub Logistics"
              />
            </div>

            <div class="form-group">
              <label>{{ t('notes', 'Transfer Notes / Reference') }}</label>
              <input
                type="text"
                v-model="generateForm.notes"
                class="form-input"
                placeholder="e.g. Weekly automated branch replenishment"
              />
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeGenerateModal">
              {{ t('cancel', 'Cancel') }}
            </button>
            <button type="submit" class="btn-primary" :disabled="generating || !transferGroups.length">
              <span v-if="generating" class="material-symbols-outlined animate-spin icon-xs">progress_activity</span>
              <span v-else class="material-symbols-outlined icon-xs">auto_awesome</span>
              {{ generating ? t('generating-transfers', 'Generating Transfers...') : t('confirm-generate-btn', 'Create Draft Transfer Orders') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- Success Confirmation Dialog                                         -->
    <!-- =================================================================== -->
    <div v-if="showSuccessModal" class="modal-overlay" @click.self="showSuccessModal = false">
      <div class="modal-content modal-md">
        <div class="modal-header">
          <div class="success-header-wrap">
            <span class="material-symbols-outlined success-icon">check_circle</span>
            <div>
              <h3 class="modal-title">{{ t('generation-success-title', 'Transfers Generated Successfully') }}</h3>
              <p class="modal-subtitle">
                {{ t('generation-success-desc', `Created ${generatedTransfers.length} draft stock transfer orders ready for review and dispatch.`).replace('{count}', generatedTransfers.length) }}
              </p>
            </div>
          </div>
        </div>

        <div class="modal-body">
          <div class="created-transfers-list">
            <div
              v-for="trf in generatedTransfers"
              :key="trf.id"
              class="created-transfer-card"
            >
              <div class="trf-info">
                <span class="trf-number font-mono font-bold">{{ trf.transfer_number }}</span>
                <span class="trf-route text-sm text-muted">
                  {{ trf.source_warehouse_name || getWarehouseName(trf.source_warehouse_id) }}
                  &rarr;
                  {{ trf.destination_warehouse_name || getWarehouseName(trf.destination_warehouse_id) }}
                </span>
              </div>
              <router-link
                :to="`/warehouse/transfers/${trf.id}`"
                class="btn-outline btn-xs"
                @click="showSuccessModal = false"
              >
                <span class="material-symbols-outlined icon-xs">visibility</span>
                {{ t('view-transfer', 'View Transfer') }}
              </router-link>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="showSuccessModal = false">
              {{ t('close', 'Close') }}
            </button>
            <router-link to="/warehouse/transfers" class="btn-primary" @click="showSuccessModal = false">
              <span class="material-symbols-outlined icon-xs">local_shipping</span>
              {{ t('view-transfers', 'View Stock Transfers') }}
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import { useWebSocket } from '../../composables/useWebSocket.js'
import { useAuthStore } from '../../stores/auth.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// Data state
const loading = ref(true)
const generating = ref(false)
const error = ref('')
const suggestions = ref([])
const warehouses = ref([])
const products = ref([])

// Summary health state
const summary = reactive({
  total_deficits: 0,
  critical_deficits: 0,
  high_deficits: 0,
  active_in_transit_transfers: 0,
  total_products: 0,
  total_warehouses: 0,
})

// Filters
const searchQuery = ref('')
const destWarehouseFilter = ref(null)
const sourceWarehouseFilter = ref(null)
const priorityFilter = ref('')
const showParamControls = ref(false)

// Calculation Parameters
const params = reactive({
  safety_stock_ratio: 0.5,
  target_coverage_multiplier: 1.5,
  min_deficit: 0,
})

// Selection state for batch transfer generation
const selectedKeys = ref(new Set())

// Modal states
const showGenerateModal = ref(false)
const showSuccessModal = ref(false)
const itemsToGenerate = ref([])
const generatedTransfers = ref([])

// Batch generation form
const generateForm = reactive({
  transfer_date: new Date().toISOString().split('T')[0],
  expected_delivery_date: '',
  carrier: '',
  notes: 'Automated inter-branch replenishment order',
})

// Multi-tenant & Real-time WebSockets
const auth = useAuthStore()
const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
wsInventory.on('stock_transfers_updated', () => {
  loadData(false)
})
wsInventory.on('stock_updated', () => {
  loadData(false)
})

// ---------------------------------------------------------------------------
// Computed Properties
// ---------------------------------------------------------------------------

const branchWarehouses = computed(() => {
  return warehouses.value.filter(w => !w.is_virtual)
})

const sourceWarehouses = computed(() => {
  return warehouses.value.filter(w => !w.is_virtual)
})

const hasActiveFilters = computed(() => {
  return !!(
    searchQuery.value ||
    destWarehouseFilter.value !== null ||
    sourceWarehouseFilter.value !== null ||
    priorityFilter.value
  )
})

const filteredSuggestions = computed(() => {
  let list = suggestions.value || []

  if (destWarehouseFilter.value !== null) {
    list = list.filter(s => s.destination_warehouse_id === Number(destWarehouseFilter.value))
  }

  if (sourceWarehouseFilter.value !== null) {
    list = list.filter(s => s.source_warehouse_id === Number(sourceWarehouseFilter.value))
  }

  if (priorityFilter.value) {
    list = list.filter(s => s.priority.toLowerCase() === priorityFilter.value.toLowerCase())
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(s => {
      const code = (s.product_code || '').toLowerCase()
      const name = (s.product_name || '').toLowerCase()
      const dest = (s.destination_warehouse_name || getWarehouseName(s.destination_warehouse_id) || '').toLowerCase()
      const src = (s.source_warehouse_name || getWarehouseName(s.source_warehouse_id) || '').toLowerCase()
      const reason = (s.reason || '').toLowerCase()
      return code.includes(q) || name.includes(q) || dest.includes(q) || src.includes(q) || reason.includes(q)
    })
  }

  return list
})

const selectedSuggestions = computed(() => {
  return (suggestions.value || []).filter(s => selectedKeys.value.has(itemKey(s)))
})

const isAllSelected = computed(() => {
  const filtered = filteredSuggestions.value
  if (!filtered.length) return false
  return filtered.every(s => selectedKeys.value.has(itemKey(s)))
})

const isIndeterminate = computed(() => {
  const filtered = filteredSuggestions.value
  if (!filtered.length) return false
  const selectedCount = filtered.filter(s => selectedKeys.value.has(itemKey(s))).length
  return selectedCount > 0 && selectedCount < filtered.length
})

// Groups for modal preview
const transferGroups = computed(() => {
  const items = itemsToGenerate.value || []
  const map = new Map()

  for (const item of items) {
    const srcId = item.source_warehouse_id
    const destId = item.destination_warehouse_id
    if (!srcId || !destId) continue

    const key = `${srcId}-${destId}`
    if (!map.has(key)) {
      map.set(key, {
        source_id: srcId,
        source_name: item.source_warehouse_name || getWarehouseName(srcId),
        dest_id: destId,
        dest_name: item.destination_warehouse_name || getWarehouseName(destId),
        items: [],
        totalQty: 0,
      })
    }
    const grp = map.get(key)
    grp.items.push(item)
    grp.totalQty += Number(item.suggested_transfer_qty || 0)
  }

  return Array.from(map.values())
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function itemKey(item) {
  return `${item.product_id}-${item.destination_warehouse_id}`
}

function isItemSelected(item) {
  return selectedKeys.value.has(itemKey(item))
}

function toggleItemSelection(item) {
  const key = itemKey(item)
  if (selectedKeys.value.has(key)) {
    selectedKeys.value.delete(key)
  } else {
    selectedKeys.value.add(key)
  }
}

function toggleSelectAll(e) {
  if (e.target.checked) {
    filteredSuggestions.value.forEach(s => selectedKeys.value.add(itemKey(s)))
  } else {
    filteredSuggestions.value.forEach(s => selectedKeys.value.delete(itemKey(s)))
  }
}

function clearSelection() {
  selectedKeys.value.clear()
}

function getWarehouseName(id) {
  if (!id) return '-'
  const wh = warehouses.value.find(w => w.id === id)
  return wh ? wh.name : `#${id}`
}

function priorityBadgeClass(priority) {
  switch (priority) {
    case 'Critical':
      return 'priority-critical'
    case 'High':
      return 'priority-high'
    case 'Normal':
      return 'priority-normal'
    case 'Low':
      return 'priority-low'
    default:
      return 'priority-normal'
  }
}

function priorityIcon(priority) {
  switch (priority) {
    case 'Critical':
      return 'error'
    case 'High':
      return 'warning'
    case 'Normal':
      return 'info'
    case 'Low':
      return 'check_circle'
    default:
      return 'help'
  }
}

function meterPercent(item) {
  if (!item.reorder_point || item.reorder_point <= 0) return 100
  const effective = Number(item.available_stock || 0) + Number(item.in_transit_stock || 0)
  const pct = (effective / item.reorder_point) * 100
  return Math.min(100, Math.max(5, Math.round(pct)))
}

function meterFillClass(item) {
  const effective = Number(item.available_stock || 0) + Number(item.in_transit_stock || 0)
  if (effective <= 0) return 'meter-zero'
  if (effective < (item.safety_stock || item.reorder_point * 0.5)) return 'meter-critical'
  if (effective < item.reorder_point) return 'meter-warning'
  return 'meter-ok'
}

function resetFilters() {
  searchQuery.value = ''
  destWarehouseFilter.value = null
  sourceWarehouseFilter.value = null
  priorityFilter.value = ''
}

// ---------------------------------------------------------------------------
// API Data Loaders
// ---------------------------------------------------------------------------

async function loadData(showSpinner = true) {
  if (showSpinner) loading.value = true
  error.value = ''
  try {
    await Promise.all([
      loadSuggestions(),
      loadSummary(),
      loadWarehouses(),
      loadProducts(),
    ])
  } catch (err) {
    error.value = t('failed-load', 'Failed to load replenishment recommendations. Please try again.')
  } finally {
    if (showSpinner) loading.value = false
  }
}

async function loadSuggestions() {
  const queryParams = {
    safety_stock_ratio: params.safety_stock_ratio,
    target_coverage_multiplier: params.target_coverage_multiplier,
    min_deficit: params.min_deficit,
  }
  const res = await api.get('/inventory/replenishment/suggestions', { params: queryParams })
  suggestions.value = res.data?.items || []
  if (res.data) {
    summary.total_deficits = res.data.total_suggestions || 0
    summary.critical_deficits = res.data.critical_count || 0
    summary.high_deficits = res.data.high_count || 0
  }
}

async function loadSummary() {
  try {
    const res = await api.get('/inventory/replenishment/summary')
    if (res.data) {
      summary.total_products = res.data.total_products || 0
      summary.total_warehouses = res.data.total_warehouses || 0
      summary.active_in_transit_transfers = res.data.active_in_transit_transfers || 0
    }
  } catch (err) {
    console.warn('Failed to load replenishment summary KPI:', err)
  }
}

async function loadWarehouses() {
  try {
    const res = await api.get('/T0008I/')
    warehouses.value = res.data || []
  } catch {
    warehouses.value = []
  }
}

async function loadProducts() {
  try {
    const res = await api.get('/T0003I/')
    products.value = res.data || []
  } catch {
    products.value = []
  }
}

async function applyParameters() {
  loading.value = true
  try {
    await loadSuggestions()
    toast(t('params-applied', 'Replenishment parameters applied'), 'success')
  } catch {
    toast(t('failed-apply-params', 'Failed to apply calculation parameters'), 'error')
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Generate Transfers Workflow
// ---------------------------------------------------------------------------

function openGenerateModal(mode = 'all') {
  if (mode === 'selected') {
    itemsToGenerate.value = selectedSuggestions.value.filter(s => s.source_warehouse_id)
  } else {
    itemsToGenerate.value = filteredSuggestions.value.filter(s => s.source_warehouse_id)
  }

  if (!itemsToGenerate.value.length) {
    toast(t('no-eligible-items', 'No items with available source hubs to generate transfers'), 'warning')
    return
  }

  generateForm.transfer_date = new Date().toISOString().split('T')[0]
  generateForm.expected_delivery_date = ''
  generateForm.carrier = ''
  generateForm.notes = 'Automated inter-branch replenishment order'

  showGenerateModal.value = true
}

function openSingleTransferModal(item) {
  itemsToGenerate.value = [item]
  generateForm.transfer_date = new Date().toISOString().split('T')[0]
  generateForm.expected_delivery_date = ''
  generateForm.carrier = ''
  generateForm.notes = `Replenishment transfer for ${item.product_code || item.product_name}`
  showGenerateModal.value = true
}

function closeGenerateModal() {
  showGenerateModal.value = false
}

async function submitGenerateTransfers() {
  if (!itemsToGenerate.value.length) return
  generating.value = true

  const payload = {
    transfer_date: generateForm.transfer_date,
    expected_delivery_date: generateForm.expected_delivery_date || null,
    carrier: generateForm.carrier || null,
    notes: generateForm.notes || null,
    items: itemsToGenerate.value.map(item => ({
      product_id: item.product_id,
      destination_warehouse_id: item.destination_warehouse_id,
      source_warehouse_id: item.source_warehouse_id,
      suggested_transfer_qty: Number(item.suggested_transfer_qty),
    })),
  }

  try {
    const res = await api.post('/inventory/replenishment/generate-transfers', payload)
    const data = res.data || {}
    generatedTransfers.value = data.transfers || []

    toast(
      t('transfers-created-toast', `Successfully generated ${data.transfers_created || 0} transfer orders`),
      'success'
    )

    closeGenerateModal()
    clearSelection()
    showSuccessModal.value = true

    // Refresh recommendations after generation
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-generate-transfers', 'Failed to generate transfer orders')
    toast(msg, 'error')
  } finally {
    generating.value = false
  }
}

onMounted(() => {
  loadData(true)
})
</script>

<style scoped>
.replenishment-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* KPI Summary Cards */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-primary);
}

.stat-num.critical { color: #dc2626; }
.stat-num.high { color: #f59e0b; }
.stat-num.in-transit { color: #0284c7; }
.stat-num.monitored { color: #64748b; }

.stat-lbl {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 3px;
}

/* Filter Toolbar */
.filters-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 18px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
}

.filters-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 260px;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  top: 50%;
  inset-inline-start: 10px;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 18px;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding-inline-start: 34px;
  padding-inline-end: 32px;
}

.clear-search {
  position: absolute;
  top: 50%;
  inset-inline-end: 8px;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.clear-search span {
  font-size: 16px;
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  min-width: 160px;
  font-size: 13px;
}

.toggle-params-btn.active {
  background: var(--bg-primary-faded);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.reset-btn {
  color: var(--text-muted);
}

/* Calculation Parameters Panel */
.params-panel {
  padding: 12px 16px;
  background: var(--bg-surface-hover, #f8fafc);
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  margin-top: 4px;
}

.params-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) auto;
  gap: 16px;
  align-items: flex-end;
}

.param-field label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.form-range {
  width: 100%;
  accent-color: var(--color-primary);
}

.param-actions {
  display: flex;
  align-items: flex-end;
}

/* Recommendations Table */
.table-actions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-checkbox {
  width: 40px;
  text-align: center;
}

.checkbox-container {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.checkbox-container input {
  cursor: pointer;
}

.cell-product {
  min-width: 180px;
}

.prod-code {
  font-size: 11px;
  color: var(--text-muted);
}

.prod-name {
  font-size: 13px;
  color: var(--text-primary);
}

.cell-destination {
  min-width: 160px;
}

.branch-name {
  font-size: 13px;
  font-weight: 500;
}

.stock-pills {
  display: flex;
  gap: 4px;
  margin-top: 3px;
  flex-wrap: wrap;
}

.stock-pill {
  font-size: 10px;
  padding: 2px 6px;
  background: var(--bg-surface-hover, #f1f5f9);
  border-radius: 4px;
  color: var(--text-secondary);
}

.stock-pill.pill-zero {
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 600;
}

.stock-pill.pill-transit {
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 600;
}

.cell-position {
  min-width: 140px;
}

.stock-meter-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.meter-labels {
  display: flex;
  justify-content: space-between;
}

.meter-bar {
  height: 6px;
  background: var(--bg-surface-hover, #e2e8f0);
  border-radius: 3px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.meter-fill.meter-zero { background: #dc2626; }
.meter-fill.meter-critical { background: #ea580c; }
.meter-fill.meter-warning { background: #f59e0b; }
.meter-fill.meter-ok { background: #16a34a; }

/* Priority Badges */
.priority-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}

.priority-icon {
  font-size: 14px;
}

.priority-critical {
  background: #fee2e2;
  color: #b91c1c;
}

.priority-high {
  background: #ffedd5;
  color: #c2410c;
}

.priority-normal {
  background: #e0f2fe;
  color: #0369a1;
}

.priority-low {
  background: #f1f5f9;
  color: #475569;
}

.reason-text {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 3px;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-source {
  min-width: 160px;
}

.source-name {
  font-size: 13px;
}

.source-avail-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  color: #16a34a;
  background: #dcfce7;
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 3px;
  font-weight: 600;
}

.qty-input {
  width: 75px;
  padding: 4px 6px;
  font-size: 13px;
}

.row-critical {
  background: rgba(239, 68, 68, 0.03);
}

.row-selected {
  background: var(--bg-primary-faded, rgba(37, 99, 235, 0.05));
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 16px;
}

.modal-content {
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
}

.modal-sm { width: 100%; max-width: 440px; }
.modal-md { width: 100%; max-width: 580px; }
.modal-lg { width: 100%; max-width: 780px; }

.modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.grouped-preview-section {
  background: var(--bg-surface-hover, #f8fafc);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 14px;
}

.section-subtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 10px 0;
}

.groups-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 10px 14px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.group-tag {
  background: var(--bg-surface-hover, #e2e8f0);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.route-arrow {
  font-size: 14px;
  color: var(--text-muted);
}

.group-meta {
  display: flex;
  gap: 6px;
}

.group-items-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px dashed var(--border-default);
  padding-top: 6px;
}

.group-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

/* Success Modal Styles */
.success-header-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.success-icon {
  font-size: 36px;
  color: #16a34a;
}

.created-transfers-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.created-transfer-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-surface-hover, #f8fafc);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.trf-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.empty-icon.healthy-icon {
  color: #16a34a;
}

.required {
  color: #dc2626;
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .modal-form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }
  .page-header {
    flex-direction: column;
    gap: 12px;
  }
}
</style>

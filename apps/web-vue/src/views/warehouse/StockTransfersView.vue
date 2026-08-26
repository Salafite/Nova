<template>
  <div :dir="dir" class="stock-transfers-view">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('stock-transfers-title', 'Stock Transfers') }}</h1>
        <p class="page-subtitle">{{ t('stock-transfers-sub', 'Manage multi-warehouse transfer orders, in-transit shipments, and inter-branch movements') }}</p>
      </div>
      <div class="page-actions">
        <router-link to="/inventory/replenishment" class="btn-outline">
          <span class="material-symbols-outlined">auto_awesome</span>
          {{ t('replenishment-suggestions', 'Replenishment Suggestions') }}
        </router-link>
        <button class="btn-primary" @click="openCreateModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-transfer', 'New Transfer') }}
        </button>
      </div>
    </div>

    <!-- Summary KPI Metrics Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-lbl">{{ t('total-transfers', 'Total Transfers') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num draft">{{ stats.draft }}</div>
        <div class="stat-lbl">{{ t('draft-pending', 'Draft / Pending') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num in-transit">{{ stats.inTransit }}</div>
        <div class="stat-lbl">{{ t('in-transit', 'In Transit') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num received">{{ stats.received }}</div>
        <div class="stat-lbl">{{ t('received-completed', 'Received') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num discrepancies">{{ stats.discrepancies }}</div>
        <div class="stat-lbl">{{ t('discrepancies', 'Discrepancies') }}</div>
      </div>
    </div>

    <!-- Filters & Search Toolbar -->
    <div class="filters-bar data-card">
      <div class="search-box">
        <span class="material-symbols-outlined search-icon">search</span>
        <input
          type="text"
          v-model="searchQuery"
          class="form-input search-input"
          :placeholder="t('search-transfers-ph', 'Search by TRF#, carrier, tracking, warehouse...')"
        />
        <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>

      <div class="filter-controls">
        <select v-model="statusFilter" class="form-input filter-select">
          <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
          <option value="Draft">{{ t('status-draft', 'Draft') }}</option>
          <option value="In Transit">{{ t('status-in-transit', 'In Transit') }}</option>
          <option value="Received">{{ t('status-received', 'Received') }}</option>
          <option value="Partially Received">{{ t('status-partial', 'Partially Received') }}</option>
          <option value="Cancelled">{{ t('status-cancelled', 'Cancelled') }}</option>
        </select>

        <select v-model="sourceWarehouseFilter" class="form-input filter-select">
          <option :value="null">{{ t('all-sources', 'All Source Warehouses') }}</option>
          <option v-for="wh in warehouses" :key="'src-' + wh.id" :value="wh.id">
            {{ wh.name }}
          </option>
        </select>

        <select v-model="destWarehouseFilter" class="form-input filter-select">
          <option :value="null">{{ t('all-destinations', 'All Destinations') }}</option>
          <option v-for="wh in warehouses" :key="'dest-' + wh.id" :value="wh.id">
            {{ wh.name }}
          </option>
        </select>

        <button v-if="hasActiveFilters" class="btn-outline btn-sm reset-btn" @click="resetFilters">
          <span class="material-symbols-outlined">filter_alt_off</span>
          {{ t('reset-filters', 'Reset') }}
        </button>
      </div>
    </div>

    <!-- Data Table & State Handlers -->
    <SkeletonTable v-if="loading" :rows="6" :columns="7" />
    <ErrorState v-else-if="error" :message="error" @retry="loadData" />

    <div v-else-if="!filteredTransfers.length" class="empty-state data-card">
      <span class="material-symbols-outlined empty-icon">local_shipping</span>
      <p class="empty-title">{{ t('no-transfers-found', 'No stock transfers found') }}</p>
      <p class="empty-subtitle">
        {{ hasActiveFilters ? t('no-transfers-filtered', 'Try clearing your filters to see more results.') : t('no-transfers-yet', 'Create your first inter-warehouse stock transfer to start moving inventory.') }}
      </p>
      <div class="empty-actions">
        <button v-if="hasActiveFilters" class="btn-outline" @click="resetFilters">
          {{ t('clear-filters', 'Clear Filters') }}
        </button>
        <button class="btn-primary" @click="openCreateModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('create-transfer', 'Create Transfer') }}
        </button>
      </div>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('transfer-number', 'Transfer #') }}</th>
              <th>{{ t('transfer-date', 'Date') }}</th>
              <th>{{ t('route', 'Origin & Destination') }}</th>
              <th class="text-center">{{ t('items-qty', 'Items & Qty') }}</th>
              <th>{{ t('carrier-tracking', 'Logistics') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('discrepancy', 'Discrepancy') }}</th>
              <th class="col-actions">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredTransfers"
              :key="item.id"
              :class="{ 'row-cancelled': item.status === 'Cancelled' }"
            >
              <!-- Transfer # -->
              <td class="cell-transfer-no">
                <router-link :to="`/warehouse/transfers/${item.id}`" class="transfer-link font-mono font-bold">
                  {{ item.transfer_number || `#TRF-${item.id}` }}
                </router-link>
              </td>

              <!-- Date -->
              <td class="cell-date">
                <div class="date-main">{{ formatDate(item.transfer_date) }}</div>
                <div v-if="item.expected_delivery_date" class="date-sub">
                  <span class="text-muted text-xs">{{ t('exp', 'Exp') }}: {{ formatDate(item.expected_delivery_date) }}</span>
                </div>
              </td>

              <!-- Route -->
              <td class="cell-route">
                <div class="route-badge-wrap">
                  <span class="wh-tag origin-tag" :title="item.source_warehouse_name">
                    <span class="material-symbols-outlined icon-xs">warehouse</span>
                    {{ item.source_warehouse_name || getWarehouseName(item.source_warehouse_id) }}
                  </span>
                  <span class="material-symbols-outlined route-arrow">arrow_forward</span>
                  <span class="wh-tag dest-tag" :title="item.destination_warehouse_name">
                    <span class="material-symbols-outlined icon-xs">domain</span>
                    {{ item.destination_warehouse_name || getWarehouseName(item.destination_warehouse_id) }}
                  </span>
                </div>
              </td>

              <!-- Items & Quantity -->
              <td class="text-center cell-qty">
                <div class="font-semibold text-sm">
                  {{ item.lines_count || (item.lines ? item.lines.length : 0) }} {{ t('lines', 'lines') }}
                </div>
                <div class="text-xs text-muted">
                  <span v-if="item.status === 'Draft' || item.status === 'Pending'">
                    {{ item.total_requested_qty || 0 }} {{ t('req-units', 'units req') }}
                  </span>
                  <span v-else-if="item.status === 'In Transit'">
                    {{ item.total_dispatched_qty || item.total_requested_qty || 0 }} {{ t('in-transit-units', 'units in-transit') }}
                  </span>
                  <span v-else>
                    {{ item.total_received_qty || 0 }} / {{ item.total_dispatched_qty || item.total_requested_qty || 0 }} {{ t('received-units', 'rec') }}
                  </span>
                </div>
              </td>

              <!-- Logistics / Carrier -->
              <td class="cell-logistics">
                <div v-if="item.carrier" class="carrier-name font-medium">
                  <span class="material-symbols-outlined icon-xs">local_shipping</span>
                  {{ item.carrier }}
                </div>
                <div v-if="item.tracking_number" class="tracking-no font-mono text-xs text-muted">
                  {{ item.tracking_number }}
                </div>
                <div v-if="!item.carrier && !item.tracking_number" class="text-muted text-xs">—</div>
              </td>

              <!-- Status Badge -->
              <td class="text-center">
                <span class="badge" :class="statusBadgeClass(item.status)">
                  <span class="material-symbols-outlined icon-xs">{{ statusIcon(item.status) }}</span>
                  {{ item.status }}
                </span>
              </td>

              <!-- Discrepancy / Loss Indicator -->
              <td class="text-center">
                <span v-if="item.total_lost_qty > 0" class="badge badge-loss" :title="`Transit loss: ${item.total_lost_qty} units`">
                  <span class="material-symbols-outlined icon-xs">warning</span>
                  {{ item.total_lost_qty }} {{ t('lost-short', 'lost') }}
                </span>
                <span v-else-if="item.status === 'Received'" class="badge badge-match">
                  <span class="material-symbols-outlined icon-xs">check</span>
                  {{ t('matched', 'Matched') }}
                </span>
                <span v-else class="text-muted text-xs">—</span>
              </td>

              <!-- Actions -->
              <td class="cell-actions">
                <div class="actions-group">
                  <router-link
                    :to="`/warehouse/transfers/${item.id}`"
                    class="btn-icon"
                    :title="t('view-details', 'View Details')"
                  >
                    <span class="material-symbols-outlined">visibility</span>
                  </router-link>

                  <!-- Quick Dispatch Button for Draft -->
                  <button
                    v-if="item.status === 'Draft' || item.status === 'Pending'"
                    class="btn-icon btn-icon-dispatch"
                    @click="openDispatchModal(item)"
                    :title="t('dispatch-transfer', 'Dispatch Transfer')"
                  >
                    <span class="material-symbols-outlined">flight_takeoff</span>
                  </button>

                  <!-- Quick Receive Button for In Transit -->
                  <button
                    v-if="item.status === 'In Transit'"
                    class="btn-icon btn-icon-receive"
                    @click="openReceiveModal(item)"
                    :title="t('receive-transfer', 'Receive Transfer')"
                  >
                    <span class="material-symbols-outlined">fact_check</span>
                  </button>

                  <!-- Cancel Button for Draft/In Transit -->
                  <button
                    v-if="item.status === 'Draft' || item.status === 'Pending' || item.status === 'In Transit'"
                    class="btn-icon btn-icon-danger"
                    @click="openCancelModal(item)"
                    :title="t('cancel-transfer', 'Cancel Transfer')"
                  >
                    <span class="material-symbols-outlined">cancel</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- Create Stock Transfer Modal                                         -->
    <!-- =================================================================== -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">{{ t('new-stock-transfer', 'New Stock Transfer Order') }}</h3>
            <p class="modal-subtitle">{{ t('new-stock-transfer-sub', 'Select origin and destination warehouses and add line items') }}</p>
          </div>
          <button class="btn-icon" @click="closeCreateModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="submitCreateTransfer" class="modal-body">
          <!-- Warehouse & Date Settings -->
          <div class="form-section">
            <h4 class="section-title">
              <span class="material-symbols-outlined icon-sm">sync_alt</span>
              {{ t('transfer-route-details', 'Transfer Route & Schedule') }}
            </h4>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('source-warehouse', 'Source Warehouse (Origin)') }} <span class="required">*</span></label>
                <select
                  v-model.number="form.source_warehouse_id"
                  class="form-input"
                  :class="{ 'input-error': formErrors.source_warehouse_id }"
                  required
                >
                  <option :value="null">{{ t('select-source-wh', '-- Select Origin Warehouse --') }}</option>
                  <option
                    v-for="wh in warehouses"
                    :key="'modal-src-' + wh.id"
                    :value="wh.id"
                    :disabled="wh.id === form.destination_warehouse_id"
                  >
                    {{ wh.name }} ({{ wh.location || t('main', 'Main') }})
                  </option>
                </select>
                <div v-if="formErrors.source_warehouse_id" class="field-error">{{ formErrors.source_warehouse_id }}</div>
              </div>

              <div class="form-group">
                <label>{{ t('destination-warehouse', 'Destination Warehouse') }} <span class="required">*</span></label>
                <select
                  v-model.number="form.destination_warehouse_id"
                  class="form-input"
                  :class="{ 'input-error': formErrors.destination_warehouse_id }"
                  required
                >
                  <option :value="null">{{ t('select-dest-wh', '-- Select Destination Warehouse --') }}</option>
                  <option
                    v-for="wh in warehouses"
                    :key="'modal-dest-' + wh.id"
                    :value="wh.id"
                    :disabled="wh.id === form.source_warehouse_id"
                  >
                    {{ wh.name }} ({{ wh.location || t('branch', 'Branch') }})
                  </option>
                </select>
                <div v-if="formErrors.destination_warehouse_id" class="field-error">{{ formErrors.destination_warehouse_id }}</div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ t('transfer-date', 'Transfer Date') }} <span class="required">*</span></label>
                <input type="date" v-model="form.transfer_date" class="form-input" required />
              </div>
              <div class="form-group">
                <label>{{ t('expected-delivery-date', 'Expected Delivery Date') }}</label>
                <input type="date" v-model="form.expected_delivery_date" class="form-input" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ t('carrier-name', 'Logistics Carrier / Transport Provider') }}</label>
                <input
                  type="text"
                  v-model="form.carrier"
                  class="form-input"
                  :placeholder="t('carrier-ph', 'e.g. DHL Express, Internal Fleet #3, Aramex')"
                />
              </div>
              <div class="form-group">
                <label>{{ t('tracking-number', 'Tracking / Waybill Number') }}</label>
                <input
                  type="text"
                  v-model="form.tracking_number"
                  class="form-input"
                  :placeholder="t('tracking-ph', 'e.g. TRK-987654321')"
                />
              </div>
            </div>

            <div class="form-group">
              <label>{{ t('notes-instructions', 'Transfer Notes & Instructions') }}</label>
              <textarea
                v-model="form.notes"
                rows="2"
                class="form-input form-textarea"
                :placeholder="t('notes-ph', 'Optional special handling instructions or transfer justification...')"
              ></textarea>
            </div>
          </div>

          <!-- Line Items Section -->
          <div class="form-section">
            <div class="section-header-flex">
              <h4 class="section-title">
                <span class="material-symbols-outlined icon-sm">inventory_2</span>
                {{ t('line-items', 'Transfer Line Items') }}
              </h4>
              <button type="button" class="btn-outline btn-sm" @click="addLineItem">
                <span class="material-symbols-outlined">add</span>
                {{ t('add-line', 'Add Item') }}
              </button>
            </div>

            <div v-if="formErrors.lines" class="lines-error-box">
              <span class="material-symbols-outlined icon-xs">error</span>
              {{ formErrors.lines }}
            </div>

            <div class="lines-table-wrap">
              <table class="lines-table">
                <thead>
                  <tr>
                    <th style="width: 35%;">{{ t('product', 'Product (SKU / Name)') }} <span class="required">*</span></th>
                    <th style="width: 20%;">{{ t('qty-requested', 'Quantity') }} <span class="required">*</span></th>
                    <th style="width: 20%;">{{ t('batch-lot', 'Batch / Lot #') }}</th>
                    <th style="width: 20%;">{{ t('line-notes', 'Notes') }}</th>
                    <th style="width: 5%;" class="text-center">{{ t('del', '') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, index) in form.lines" :key="'line-' + index">
                    <!-- Product Selection -->
                    <td>
                      <select
                        v-model.number="line.product_id"
                        class="form-input form-input-sm"
                        @change="onProductSelect(line)"
                        required
                      >
                        <option :value="null">{{ t('select-product', '-- Select Product --') }}</option>
                        <option v-for="prod in products" :key="'prod-' + prod.id" :value="prod.id">
                          {{ prod.sku ? `[${prod.sku}] ` : '' }}{{ prod.name }}
                        </option>
                      </select>
                    </td>

                    <!-- Quantity Requested -->
                    <td>
                      <div class="input-with-hint">
                        <input
                          type="number"
                          step="any"
                          min="0.001"
                          v-model.number="line.qty_requested"
                          class="form-input form-input-sm"
                          placeholder="0.00"
                          required
                        />
                      </div>
                    </td>

                    <!-- Batch / Lot -->
                    <td>
                      <input
                        type="text"
                        v-model="line.batch_number"
                        class="form-input form-input-sm"
                        placeholder="Optional Lot#"
                      />
                    </td>

                    <!-- Notes -->
                    <td>
                      <input
                        type="text"
                        v-model="line.notes"
                        class="form-input form-input-sm"
                        placeholder="Item remarks..."
                      />
                    </td>

                    <!-- Delete Row Button -->
                    <td class="text-center">
                      <button
                        type="button"
                        class="btn-icon btn-icon-danger btn-xs"
                        :disabled="form.lines.length <= 1"
                        @click="removeLineItem(index)"
                        title="Remove line"
                      >
                        <span class="material-symbols-outlined">delete</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Transfer Items Summary Footer -->
            <div class="transfer-summary-bar">
              <div class="summary-item">
                <span class="summary-lbl">{{ t('total-lines', 'Total Lines') }}:</span>
                <span class="summary-val">{{ form.lines.length }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-lbl">{{ t('total-units-requested', 'Total Requested Units') }}:</span>
                <span class="summary-val font-mono">{{ totalFormRequestedQty }}</span>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeCreateModal">
              {{ t('cancel', 'Cancel') }}
            </button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              <span v-if="submitting" class="material-symbols-outlined animate-spin icon-xs">progress_activity</span>
              {{ submitting ? t('creating', 'Creating Transfer...') : t('create-transfer-btn', 'Create Transfer') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- Quick Dispatch Modal                                                -->
    <!-- =================================================================== -->
    <div v-if="showDispatchModal" class="modal-overlay" @click.self="showDispatchModal = false">
      <div class="modal-content modal-md">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">{{ t('dispatch-transfer-title', 'Dispatch Stock Transfer') }}</h3>
            <p class="modal-subtitle font-mono">{{ activeTransfer?.transfer_number }}</p>
          </div>
          <button class="btn-icon" @click="showDispatchModal = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="submitDispatch" class="modal-body">
          <div class="dispatch-alert">
            <span class="material-symbols-outlined icon-md">info</span>
            <div>
              <p class="alert-title">{{ t('dispatch-info-title', 'Stock Deduction & In-Transit Movement') }}</p>
              <p class="alert-desc">
                {{ t('dispatch-info-desc', 'Dispatching will deduct stock from the source warehouse and allocate it to In-Transit inventory until acknowledged by destination warehouse.') }}
              </p>
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('carrier', 'Carrier / Transport Provider') }}</label>
            <input type="text" v-model="dispatchForm.carrier" class="form-input" placeholder="e.g. DHL Express, Fleet Truck #2" />
          </div>

          <div class="form-group">
            <label>{{ t('tracking-number', 'Tracking / Waybill Number') }}</label>
            <input type="text" v-model="dispatchForm.tracking_number" class="form-input" placeholder="e.g. TRK-1002349" />
          </div>

          <div class="form-group">
            <label>{{ t('dispatch-notes', 'Dispatch Remarks / Waybill Notes') }}</label>
            <textarea v-model="dispatchForm.notes" rows="2" class="form-input form-textarea" placeholder="Optional notes..."></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="showDispatchModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              <span class="material-symbols-outlined icon-xs">flight_takeoff</span>
              {{ submitting ? t('dispatching', 'Dispatching...') : t('confirm-dispatch', 'Confirm Dispatch') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- Quick Cancel Confirmation Modal                                     -->
    <!-- =================================================================== -->
    <div v-if="showCancelModal" class="modal-overlay" @click.self="showCancelModal = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3 class="modal-title">{{ t('confirm-cancel-transfer', 'Cancel Stock Transfer') }}</h3>
          <button class="btn-icon" @click="showCancelModal = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="mb-3">
            {{ t('cancel-transfer-confirm-msg', 'Are you sure you want to cancel stock transfer') }}
            <strong class="font-mono">{{ activeTransfer?.transfer_number }}</strong>?
          </p>
          <p v-if="activeTransfer?.status === 'In Transit'" class="text-sm text-warning mb-3">
            <span class="material-symbols-outlined icon-xs">warning</span>
            {{ t('cancel-in-transit-warn', 'This transfer is currently In Transit. Cancelling will reverse the dispatch and restore stock to the source warehouse.') }}
          </p>
          <div class="form-group">
            <label>{{ t('cancellation-reason', 'Cancellation Reason') }}</label>
            <input type="text" v-model="cancelReason" class="form-input" placeholder="e.g. Duplicate order, order cancelled by manager" />
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showCancelModal = false">{{ t('back', 'Back') }}</button>
            <button class="btn-danger" :disabled="submitting" @click="submitCancel">
              {{ submitting ? t('cancelling', 'Cancelling...') : t('cancel-transfer-btn', 'Cancel Transfer') }}
            </button>
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
const submitting = ref(false)
const error = ref('')
const transfers = ref([])
const warehouses = ref([])
const products = ref([])

// Filters
const searchQuery = ref('')
const statusFilter = ref('')
const sourceWarehouseFilter = ref(null)
const destWarehouseFilter = ref(null)

// Modal states
const showCreateModal = ref(false)
const showDispatchModal = ref(false)
const showCancelModal = ref(false)
const activeTransfer = ref(null)
const cancelReason = ref('')

// Form states
const form = reactive({
  source_warehouse_id: null,
  destination_warehouse_id: null,
  transfer_date: new Date().toISOString().split('T')[0],
  expected_delivery_date: '',
  carrier: '',
  tracking_number: '',
  notes: '',
  lines: [
    { product_id: null, qty_requested: 1, batch_number: '', notes: '' }
  ]
})

const dispatchForm = reactive({
  carrier: '',
  tracking_number: '',
  notes: '',
})

const formErrors = reactive({
  source_warehouse_id: '',
  destination_warehouse_id: '',
  lines: '',
})

// Multi-tenant & Real-time WebSockets
const auth = useAuthStore()
const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
wsInventory.on('stock_transfers_updated', () => {
  loadTransfers(false)
})
wsInventory.on('stock_updated', () => {
  loadTransfers(false)
})

// ---------------------------------------------------------------------------
// Computed KPI Metrics & Filtering
// ---------------------------------------------------------------------------

const stats = computed(() => {
  const list = transfers.value || []
  return {
    total: list.length,
    draft: list.filter(t => t.status === 'Draft' || t.status === 'Pending').length,
    inTransit: list.filter(t => t.status === 'In Transit').length,
    received: list.filter(t => t.status === 'Received' || t.status === 'Partially Received').length,
    discrepancies: list.filter(t => (t.total_lost_qty && Number(t.total_lost_qty) > 0)).length,
  }
})

const hasActiveFilters = computed(() => {
  return !!(searchQuery.value || statusFilter.value || sourceWarehouseFilter.value !== null || destWarehouseFilter.value !== null)
})

const filteredTransfers = computed(() => {
  let result = transfers.value || []

  if (statusFilter.value) {
    result = result.filter(t => t.status === statusFilter.value)
  }

  if (sourceWarehouseFilter.value !== null) {
    result = result.filter(t => t.source_warehouse_id === Number(sourceWarehouseFilter.value))
  }

  if (destWarehouseFilter.value !== null) {
    result = result.filter(t => t.destination_warehouse_id === Number(destWarehouseFilter.value))
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase().trim()
    result = result.filter(t => {
      const num = (t.transfer_number || '').toLowerCase()
      const carrier = (t.carrier || '').toLowerCase()
      const trk = (t.tracking_number || '').toLowerCase()
      const notes = (t.notes || '').toLowerCase()
      const srcName = (t.source_warehouse_name || getWarehouseName(t.source_warehouse_id) || '').toLowerCase()
      const destName = (t.destination_warehouse_name || getWarehouseName(t.destination_warehouse_id) || '').toLowerCase()
      return num.includes(q) || carrier.includes(q) || trk.includes(q) || notes.includes(q) || srcName.includes(q) || destName.includes(q)
    })
  }

  return result
})

const totalFormRequestedQty = computed(() => {
  return form.lines.reduce((sum, l) => sum + (Number(l.qty_requested) || 0), 0).toFixed(2)
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWarehouseName(id) {
  if (!id) return '-'
  const wh = warehouses.value.find(w => w.id === id)
  return wh ? wh.name : `#${id}`
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

function statusBadgeClass(status) {
  switch (status) {
    case 'Draft':
    case 'Pending':
      return 'badge-draft'
    case 'In Transit':
      return 'badge-transit'
    case 'Received':
      return 'badge-received'
    case 'Partially Received':
      return 'badge-partial'
    case 'Cancelled':
      return 'badge-cancelled'
    default:
      return 'badge-default'
  }
}

function statusIcon(status) {
  switch (status) {
    case 'Draft':
    case 'Pending':
      return 'edit_note'
    case 'In Transit':
      return 'local_shipping'
    case 'Received':
      return 'task_alt'
    case 'Partially Received':
      return 'hourglass_top'
    case 'Cancelled':
      return 'cancel'
    default:
      return 'info'
  }
}

function resetFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
  sourceWarehouseFilter.value = null
  destWarehouseFilter.value = null
}

// ---------------------------------------------------------------------------
// Line Items in Form
// ---------------------------------------------------------------------------

function addLineItem() {
  form.lines.push({ product_id: null, qty_requested: 1, batch_number: '', notes: '' })
}

function removeLineItem(index) {
  if (form.lines.length > 1) {
    form.lines.splice(index, 1)
  }
}

function onProductSelect(line) {
  if (!line.qty_requested || line.qty_requested <= 0) {
    line.qty_requested = 1
  }
}

// ---------------------------------------------------------------------------
// API Data Loaders
// ---------------------------------------------------------------------------

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([
      loadTransfers(false),
      loadWarehouses(),
      loadProducts(),
    ])
  } catch (err) {
    error.value = t('failed-load-transfers', 'Failed to load stock transfer orders. Please try again.')
  } finally {
    loading.value = false
  }
}

async function loadTransfers(showSpinner = true) {
  if (showSpinner) loading.value = true
  try {
    const res = await api.get('/T0108I/')
    transfers.value = res.data || []
  } catch (err) {
    if (showSpinner) throw err
  } finally {
    if (showSpinner) loading.value = false
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

// ---------------------------------------------------------------------------
// Create Transfer Modal Actions
// ---------------------------------------------------------------------------

function openCreateModal() {
  form.source_warehouse_id = warehouses.value.length > 0 ? warehouses.value[0].id : null
  form.destination_warehouse_id = warehouses.value.length > 1 ? warehouses.value[1].id : null
  form.transfer_date = new Date().toISOString().split('T')[0]
  form.expected_delivery_date = ''
  form.carrier = ''
  form.tracking_number = ''
  form.notes = ''
  form.lines = [
    { product_id: products.value.length > 0 ? products.value[0].id : null, qty_requested: 10, batch_number: '', notes: '' }
  ]
  formErrors.source_warehouse_id = ''
  formErrors.destination_warehouse_id = ''
  formErrors.lines = ''
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
}

function validateForm() {
  let valid = true
  formErrors.source_warehouse_id = ''
  formErrors.destination_warehouse_id = ''
  formErrors.lines = ''

  if (!form.source_warehouse_id) {
    formErrors.source_warehouse_id = t('err-source-wh-required', 'Source warehouse is required')
    valid = false
  }

  if (!form.destination_warehouse_id) {
    formErrors.destination_warehouse_id = t('err-dest-wh-required', 'Destination warehouse is required')
    valid = false
  }

  if (form.source_warehouse_id && form.destination_warehouse_id && form.source_warehouse_id === form.destination_warehouse_id) {
    formErrors.destination_warehouse_id = t('err-wh-same', 'Destination warehouse must be different from source warehouse')
    valid = false
  }

  if (!form.lines || form.lines.length === 0) {
    formErrors.lines = t('err-at-least-one-line', 'At least one line item is required')
    valid = false
  } else {
    for (let i = 0; i < form.lines.length; i++) {
      const l = form.lines[i]
      if (!l.product_id) {
        formErrors.lines = t('err-line-product-missing', `Line #${i + 1}: Please select a product`)
        valid = false
        break
      }
      if (!l.qty_requested || Number(l.qty_requested) <= 0) {
        formErrors.lines = t('err-line-qty-invalid', `Line #${i + 1}: Requested quantity must be greater than 0`)
        valid = false
        break
      }
    }
  }

  return valid
}

async function submitCreateTransfer() {
  if (!validateForm()) return

  submitting.value = true
  try {
    const payload = {
      source_warehouse_id: Number(form.source_warehouse_id),
      destination_warehouse_id: Number(form.destination_warehouse_id),
      status: 'Draft',
      transfer_date: form.transfer_date || null,
      expected_delivery_date: form.expected_delivery_date || null,
      carrier: form.carrier || null,
      tracking_number: form.tracking_number || null,
      notes: form.notes || null,
      lines: form.lines.map((l, idx) => ({
        product_id: Number(l.product_id),
        qty_requested: Number(l.qty_requested),
        batch_number: l.batch_number || null,
        line_number: idx + 1,
        notes: l.notes || null,
      }))
    }

    const res = await api.post('/T0108I/', payload)
    toast(t('transfer-created-success', 'Stock transfer order created successfully'), 'success')
    closeCreateModal()
    await loadTransfers(false)
    if (res.data?.id) {
      router.push(`/warehouse/transfers/${res.data.id}`)
    }
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-create-transfer', 'Failed to create stock transfer order')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// Quick Dispatch / Receive / Cancel Actions
// ---------------------------------------------------------------------------

function openDispatchModal(item) {
  activeTransfer.value = item
  dispatchForm.carrier = item.carrier || ''
  dispatchForm.tracking_number = item.tracking_number || ''
  dispatchForm.notes = ''
  showDispatchModal.value = true
}

async function submitDispatch() {
  if (!activeTransfer.value) return
  submitting.value = true
  try {
    await api.post(`/T0108I/${activeTransfer.value.id}/dispatch`, {
      carrier: dispatchForm.carrier || null,
      tracking_number: dispatchForm.tracking_number || null,
      notes: dispatchForm.notes || null,
    })
    toast(t('transfer-dispatched-success', 'Stock transfer dispatched and moved to In-Transit'), 'success')
    showDispatchModal.value = false
    await loadTransfers(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-dispatch-transfer', 'Failed to dispatch stock transfer')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

function openReceiveModal(item) {
  // Navigate to detailed receive workflow on detail page
  router.push(`/warehouse/transfers/${item.id}`)
}

function openCancelModal(item) {
  activeTransfer.value = item
  cancelReason.value = ''
  showCancelModal.value = true
}

async function submitCancel() {
  if (!activeTransfer.value) return
  submitting.value = true
  try {
    await api.post(`/T0108I/${activeTransfer.value.id}/cancel`, {
      reason: cancelReason.value || 'Cancelled by user'
    })
    toast(t('transfer-cancelled-success', 'Stock transfer cancelled successfully'), 'success')
    showCancelModal.value = false
    await loadTransfers(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-cancel-transfer', 'Failed to cancel stock transfer')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.stock-transfers-view {
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

.stat-num.draft { color: #f59e0b; }
.stat-num.in-transit { color: #0284c7; }
.stat-num.received { color: #16a34a; }
.stat-num.discrepancies { color: #dc2626; }

.stat-lbl {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 3px;
}

/* Filter Toolbar */
.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
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
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--text-muted);
}

.search-input {
  padding-left: 36px;
  padding-right: 32px;
}

.clear-search {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  width: auto;
  min-width: 170px;
}

.reset-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Data Table Styles */
.data-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.data-table th {
  background: var(--bg-surface-hover);
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.data-table tr:hover {
  background-color: rgba(93, 63, 211, 0.02);
}

.row-cancelled {
  opacity: 0.6;
}

.cell-transfer-no .transfer-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 13px;
}

.cell-transfer-no .transfer-link:hover {
  text-decoration: underline;
}

.route-badge-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.wh-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.route-arrow {
  font-size: 16px;
  color: var(--text-muted);
}

.date-main {
  font-weight: 500;
  color: var(--text-primary);
}

.date-sub {
  margin-top: 2px;
}

.carrier-name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.actions-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.btn-icon-dispatch:hover {
  background: #e0f2fe;
  color: #0284c7;
}

.btn-icon-receive:hover {
  background: #dcfce7;
  color: #16a34a;
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}

.badge-draft { background: #fef3c7; color: #b45309; }
.badge-transit { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
.badge-received { background: #dcfce7; color: #15803d; }
.badge-partial { background: #ffedd5; color: #c2410c; }
.badge-cancelled { background: #f3f4f6; color: #6b7280; }
.badge-loss { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-match { background: #f0fdf4; color: #15803d; }

/* Empty State */
.empty-state {
  text-align: center;
  padding: 48px 24px;
}

.empty-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.empty-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 18px;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: var(--bg-surface);
  border-radius: 12px;
  width: 92%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-sm { max-width: 440px; }
.modal-md { max-width: 580px; }
.modal-xl { max-width: 860px; }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-light);
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
  margin-bottom: 0;
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.section-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-input-sm {
  padding: 6px 10px;
  font-size: 12px;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.field-error {
  font-size: 11px;
  color: var(--color-error);
  margin-top: 2px;
}

.input-error {
  border-color: var(--color-error) !important;
}

.required {
  color: var(--color-error);
}

/* Lines Table inside Modal */
.lines-table-wrap {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.lines-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.lines-table th {
  background: var(--bg-surface-hover);
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.lines-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.lines-error-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: var(--color-error);
  font-size: 12px;
}

.transfer-summary-bar {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
  padding: 10px 14px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.summary-lbl {
  color: var(--text-muted);
}

.summary-val {
  font-weight: 700;
  color: var(--text-primary);
}

.dispatch-alert {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  color: #0369a1;
}

.alert-title {
  font-weight: 600;
  font-size: 13px;
  margin: 0 0 2px 0;
}

.alert-desc {
  font-size: 12px;
  margin: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

.icon-xs { font-size: 14px; }
.icon-sm { font-size: 18px; }
.icon-md { font-size: 24px; }

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-primary);
  color: #fff;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}

.btn-outline:hover {
  background: var(--bg-surface-hover);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-error);
  color: #fff;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-danger:hover {
  background: #b91c1c;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}

.btn-icon:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.btn-icon-danger:hover {
  background: #fee2e2;
  color: var(--color-error);
}

.btn-xs {
  padding: 2px 4px !important;
}

.font-mono {
  font-family: 'JetBrains Mono', monospace;
}

.text-center { text-align: center; }
.text-xs { font-size: 11px; }
.text-sm { font-size: 12px; }
.text-muted { color: var(--text-muted); }
.text-warning { color: #d97706; }
.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.mb-3 { margin-bottom: 12px; }

/* RTL support */
[dir="rtl"] .search-input {
  padding-left: 32px;
  padding-right: 36px;
}

[dir="rtl"] .search-icon {
  left: auto;
  right: 10px;
}

[dir="rtl"] .clear-search {
  right: auto;
  left: 8px;
}

[dir="rtl"] .data-table th,
[dir="rtl"] .data-table td,
[dir="rtl"] .lines-table th,
[dir="rtl"] .lines-table td {
  text-align: right;
}

[dir="rtl"] .data-table .text-center,
[dir="rtl"] .lines-table .text-center {
  text-align: center;
}

[dir="rtl"] .route-arrow {
  transform: rotate(180deg);
}

[dir="rtl"] .page-actions,
[dir="rtl"] .modal-actions,
[dir="rtl"] .transfer-summary-bar {
  flex-direction: row-reverse;
}

[dir="rtl"] .form-row {
  direction: rtl;
}
</style>

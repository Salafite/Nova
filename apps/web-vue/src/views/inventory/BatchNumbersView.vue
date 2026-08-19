<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('batch-title', 'Batch & Lot Numbers') }}</h1>
        <p class="page-subtitle">{{ t('batch-sub', 'Manage product batch numbers for FEFO picking and food safety traceability') }}</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-recall" @click="openRecallModal(null)">
          <span class="material-symbols-outlined">crisis_alert</span> {{ t('recall-tool', 'Batch Recall & Traceability') }}
        </button>
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-batch', 'New Batch') }}
        </button>
      </div>
    </div>

    <!-- Search and Filters Bar -->
    <div class="filter-card mb-4">
      <div class="flex items-center gap-3">
        <div class="search-input-wrap flex-1">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            v-model="searchQuery"
            class="form-input search-input"
            :placeholder="t('search-batches', 'Search by batch #, product SKU or name...')"
          />
        </div>
        <select v-model="filterStatus" class="form-input filter-select">
          <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
          <option value="Available">Available</option>
          <option value="Partially Used">Partially Used</option>
          <option value="Depleted">Depleted</option>
          <option value="Expired">Expired</option>
        </select>
        <select v-model="filterWarehouse" class="form-input filter-select">
          <option value="">{{ t('all-warehouses', 'All Warehouses') }}</option>
          <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filteredItems.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">inventory_2</span>
      <p>{{ items.length ? t('no-matching-records', 'No matching batch records found') : t('no-records', 'No batch records yet') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('batch-number', 'Batch/Lot #') }}</th>
              <th>Product</th>
              <th>Warehouse</th>
              <th class="text-center">Available Qty</th>
              <th>{{ t('mfg-date', 'Mfg Date') }}</th>
              <th>{{ t('expiry-date', 'Expiry Date') }}</th>
              <th class="text-center">Status</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id">
              <td>
                <span class="mono lot-pill">{{ item.batch_number }}</span>
              </td>
              <td>
                <div class="product-info">
                  <span class="font-medium">{{ productName(item.product_id) }}</span>
                </div>
              </td>
              <td>{{ warehouseName(item.warehouse_id) }}</td>
              <td class="text-center">
                <span class="font-bold" :class="item.quantity > 0 ? 'text-emerald-700' : 'text-gray-400'">
                  {{ item.quantity }}
                </span>
              </td>
              <td>{{ item.manufacturing_date ? formatDate(item.manufacturing_date) : '-' }}</td>
              <td>
                <span :class="getExpiryClass(item.expiry_date)">
                  {{ item.expiry_date ? formatDate(item.expiry_date) : '-' }}
                </span>
              </td>
              <td class="text-center">
                <span class="badge" :class="getStatusBadgeClass(item.status, item.expiry_date)">
                  {{ item.status || 'Available' }}
                </span>
              </td>
              <td class="text-center">
                <div class="flex justify-center gap-1">
                  <button
                    class="btn-icon text-amber-600"
                    @click="openRecallModal(item)"
                    :title="t('trace-recall', 'Trace & Recall Report')"
                  >
                    <span class="material-symbols-outlined">crisis_alert</span>
                  </button>
                  <button
                    class="btn-icon"
                    @click="editItem(item)"
                    :title="t('edit', 'Edit')"
                  >
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button
                    class="btn-icon text-red-500"
                    @click="deleteItem(item)"
                    :title="t('delete', 'Delete')"
                  >
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Batch Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-batch', 'Edit Batch') : t('new-batch', 'New Batch') }}</h3>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('batch-number', 'Batch/Lot #') }} <span class="text-red-500">*</span></label>
            <input type="text" v-model="form.batch_number" class="form-input" placeholder="e.g. LOT-2026-0819" />
          </div>
          <div class="form-group">
            <label>Product <span class="text-red-500">*</span></label>
            <select v-model="form.product_id" class="form-input">
              <option :value="null">-- Select Product --</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.sku }} - {{ p.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Warehouse</label>
            <select v-model="form.warehouse_id" class="form-input">
              <option :value="null">-- Select Warehouse --</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-group">
              <label>Quantity</label>
              <input type="number" step="0.01" v-model.number="form.quantity" class="form-input" />
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="form.status" class="form-input">
                <option value="Available">Available</option>
                <option value="Partially Used">Partially Used</option>
                <option value="Depleted">Depleted</option>
                <option value="Expired">Expired</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-group">
              <label>{{ t('mfg-date', 'Manufacturing Date') }}</label>
              <input type="date" v-model="form.manufacturing_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('expiry-date', 'Expiry Date') }}</label>
              <input type="date" v-model="form.expiry_date" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('notes', 'Notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2" placeholder="Storage instructions, quality notes..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="saving || !form.batch_number || !form.product_id" @click="saveItem">
            {{ saving ? t('saving', 'Saving...') : t('save', 'Save Batch') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Batch Recall & Traceability Modal -->
    <div v-if="showRecallModal" class="modal-overlay" @click.self="closeRecallModal">
      <div class="modal modal-xl">
        <div class="modal-header bg-recall-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-amber-500 font-bold">crisis_alert</span>
            <div>
              <h3 class="text-lg font-bold">{{ t('recall-title', 'Batch Traceability & Food Recall Report') }}</h3>
              <p class="text-xs text-muted">{{ t('recall-subtitle', 'Instantly identify all suppliers, inventory stock, and customer shipments for lot recall') }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="closeRecallModal"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <!-- Search lot header bar inside modal -->
          <div class="recall-search-bar mb-4">
            <div class="flex gap-2">
              <div class="flex-1 relative">
                <input
                  type="text"
                  v-model="recallSearchQuery"
                  class="form-input recall-search-input"
                  :placeholder="t('enter-lot-number', 'Enter Batch / Lot # to trace (e.g. LOT-001)...')"
                  @keyup.enter="runRecallReport"
                />
              </div>
              <button class="btn-primary" :disabled="recallLoading || !recallSearchQuery.trim()" @click="runRecallReport">
                <span v-if="recallLoading" class="material-symbols-outlined spin">progress_activity</span>
                <span v-else class="material-symbols-outlined">search</span>
                {{ recallLoading ? t('tracing', 'Tracing...') : t('generate-report', 'Trace Lot') }}
              </button>
            </div>
          </div>

          <!-- Loading state -->
          <div v-if="recallLoading" class="text-center py-12">
            <span class="material-symbols-outlined spin text-3xl text-purple-600">progress_activity</span>
            <p class="mt-2 text-sm text-muted">Tracing upstream suppliers and downstream customer shipments...</p>
          </div>

          <!-- Error state -->
          <div v-else-if="recallError" class="recall-error-alert mb-4">
            <span class="material-symbols-outlined">error</span>
            <div class="flex-1">
              <div class="font-bold">Lot Not Found</div>
              <div class="text-xs">{{ recallError }}</div>
            </div>
          </div>

          <!-- Recall Report Content -->
          <template v-else-if="recallReport">
            <!-- Lot Metadata Summary Banner -->
            <div class="recall-banner mb-4">
              <div class="flex flex-wrap justify-between items-center gap-3">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="mono font-bold text-base text-purple-900">{{ recallReport.batch?.batch_number }}</span>
                    <span class="badge" :class="getStatusBadgeClass(recallReport.batch?.status, recallReport.batch?.expiry_date)">
                      {{ recallReport.batch?.status || 'Active' }}
                    </span>
                  </div>
                  <div class="text-sm font-semibold text-gray-800 mt-1">
                    {{ recallReport.batch?.product_name || 'Product' }}
                    <span v-if="recallReport.batch?.product_sku" class="text-xs text-muted font-mono">({{ recallReport.batch?.product_sku }})</span>
                  </div>
                </div>
                <div class="flex flex-wrap gap-4 text-xs">
                  <div>
                    <span class="text-muted block">Warehouse:</span>
                    <span class="font-medium">{{ recallReport.batch?.warehouse_name || 'All Warehouses' }}</span>
                  </div>
                  <div>
                    <span class="text-muted block">Mfg Date:</span>
                    <span class="font-medium">{{ recallReport.batch?.manufacturing_date ? formatDate(recallReport.batch?.manufacturing_date) : '-' }}</span>
                  </div>
                  <div>
                    <span class="text-muted block">Expiry Date:</span>
                    <span class="font-medium" :class="getExpiryClass(recallReport.batch?.expiry_date)">
                      {{ recallReport.batch?.expiry_date ? formatDate(recallReport.batch?.expiry_date) : '-' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- KPI Metric Stat Cards -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
              <div class="stat-card">
                <div class="stat-icon-wrap bg-blue-50 text-blue-600">
                  <span class="material-symbols-outlined">input</span>
                </div>
                <div>
                  <div class="stat-val">{{ recallReport.summary?.total_qty_received || 0 }}</div>
                  <div class="stat-lbl">Total Inbound Received</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon-wrap bg-purple-50 text-purple-600">
                  <span class="material-symbols-outlined">output</span>
                </div>
                <div>
                  <div class="stat-val">{{ recallReport.summary?.total_qty_picked || 0 }}</div>
                  <div class="stat-lbl">Total Outbound Shipped</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon-wrap bg-emerald-50 text-emerald-600">
                  <span class="material-symbols-outlined">warehouse</span>
                </div>
                <div>
                  <div class="stat-val">{{ recallReport.summary?.current_quantity || 0 }}</div>
                  <div class="stat-lbl">Warehouse Stock Left</div>
                </div>
              </div>
              <div class="stat-card" :class="(recallReport.summary?.total_affected_customers || 0) > 0 ? 'border-amber-400 bg-amber-50/40' : ''">
                <div class="stat-icon-wrap bg-amber-50 text-amber-600">
                  <span class="material-symbols-outlined">group</span>
                </div>
                <div>
                  <div class="stat-val text-amber-700 font-extrabold">{{ recallReport.summary?.total_affected_customers || 0 }}</div>
                  <div class="stat-lbl text-amber-900 font-semibold">Affected Customers</div>
                </div>
              </div>
            </div>

            <!-- Trace Sections Tabs -->
            <div class="tab-nav mb-3">
              <button
                class="tab-btn"
                :class="{ active: recallTab === 'customers' }"
                @click="recallTab = 'customers'"
              >
                <span class="material-symbols-outlined icon-xs">group</span>
                {{ t('affected-customers', 'Affected Customers') }}
                <span class="tab-badge" v-if="recallReport.affected_customers?.length">{{ recallReport.affected_customers.length }}</span>
              </button>
              <button
                class="tab-btn"
                :class="{ active: recallTab === 'outbound' }"
                @click="recallTab = 'outbound'"
              >
                <span class="material-symbols-outlined icon-xs">local_shipping</span>
                {{ t('outbound-trace', 'Sales & Shipments Trace') }}
                <span class="tab-badge" v-if="recallReport.outbound_trace?.length">{{ recallReport.outbound_trace.length }}</span>
              </button>
              <button
                class="tab-btn"
                :class="{ active: recallTab === 'inbound' }"
                @click="recallTab = 'inbound'"
              >
                <span class="material-symbols-outlined icon-xs">inventory</span>
                {{ t('inbound-trace', 'Supplier Receipts Trace') }}
                <span class="tab-badge" v-if="recallReport.inbound_trace?.length">{{ recallReport.inbound_trace.length }}</span>
              </button>
            </div>

            <!-- Tab 1: Affected Customers -->
            <div v-if="recallTab === 'customers'">
              <div v-if="!recallReport.affected_customers?.length" class="empty-trace-state">
                <span class="material-symbols-outlined text-gray-400">check_circle</span>
                <p class="text-sm font-semibold mt-1">No customer shipments have been fulfilled with this lot yet.</p>
                <p class="text-xs text-muted">All available quantity is currently stored in warehouse inventory.</p>
              </div>
              <div v-else class="table-wrap border rounded-lg overflow-hidden">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Customer Name</th>
                      <th>Contact Info</th>
                      <th>Group</th>
                      <th class="text-center">Qty Received</th>
                      <th>Sales Orders</th>
                      <th>Invoices</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="cust in recallReport.affected_customers" :key="cust.customer_id || cust.customer_name">
                      <td>
                        <div class="font-bold text-gray-900">{{ cust.customer_name }}</div>
                        <div class="text-xs text-muted">ID: #{{ cust.customer_id }}</div>
                      </td>
                      <td>
                        <div class="text-xs">
                          <div v-if="cust.email" class="flex items-center gap-1">
                            <span class="material-symbols-outlined icon-2xs text-gray-400">mail</span>
                            <a :href="'mailto:' + cust.email" class="text-blue-600 hover:underline">{{ cust.email }}</a>
                          </div>
                          <div v-if="cust.phone" class="flex items-center gap-1 text-gray-600">
                            <span class="material-symbols-outlined icon-2xs text-gray-400">phone</span>
                            <span>{{ cust.phone }}</span>
                          </div>
                          <span v-if="!cust.email && !cust.phone" class="text-muted">-</span>
                        </div>
                      </td>
                      <td>
                        <span class="badge badge-secondary">{{ cust.group_name || 'Standard' }}</span>
                      </td>
                      <td class="text-center">
                        <span class="font-bold text-amber-700">{{ cust.total_qty_picked }}</span>
                      </td>
                      <td>
                        <div class="flex flex-wrap gap-1">
                          <span
                            v-for="ord in cust.orders"
                            :key="ord.sales_order_id || ord.order_number"
                            class="badge badge-outline"
                          >
                            {{ ord.order_number || ('SO#' + ord.sales_order_id) }} ({{ ord.qty_picked }} qty)
                          </span>
                        </div>
                      </td>
                      <td>
                        <div class="flex flex-wrap gap-1">
                          <span
                            v-for="inv in cust.invoices"
                            :key="inv.invoice_id || inv.invoice_number"
                            class="badge badge-outline text-emerald-700"
                          >
                            {{ inv.invoice_number || ('INV#' + inv.invoice_id) }}
                          </span>
                          <span v-if="!cust.invoices?.length" class="text-xs text-muted">-</span>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Tab 2: Outbound Sales & Shipments Trace -->
            <div v-if="recallTab === 'outbound'">
              <div v-if="!recallReport.outbound_trace?.length" class="empty-trace-state">
                <span class="material-symbols-outlined text-gray-400">inventory</span>
                <p class="text-sm font-semibold mt-1">No pick list items or customer orders recorded for this lot.</p>
              </div>
              <div v-else class="table-wrap border rounded-lg overflow-hidden">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Pick List #</th>
                      <th>Sales Order #</th>
                      <th>Customer</th>
                      <th>Order Date</th>
                      <th class="text-center">Qty Picked</th>
                      <th>Order Status</th>
                      <th>Invoice #</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(entry, idx) in recallReport.outbound_trace" :key="idx">
                      <td>
                        <span class="mono font-semibold">{{ entry.pick_list_number || ('PL#' + entry.pick_list_id) }}</span>
                        <span v-if="entry.pick_list_status" class="badge ml-1 text-2xs">{{ entry.pick_list_status }}</span>
                      </td>
                      <td>
                        <span class="font-medium">{{ entry.sales_order_number || ('SO#' + entry.sales_order_id) }}</span>
                      </td>
                      <td>{{ entry.customer_name }}</td>
                      <td>{{ entry.order_date ? formatDate(entry.order_date) : '-' }}</td>
                      <td class="text-center font-bold text-purple-700">{{ entry.qty_picked }}</td>
                      <td>
                        <span class="badge badge-outline">{{ entry.order_status || 'Pending' }}</span>
                      </td>
                      <td>
                        <span v-if="entry.invoice_number" class="mono text-xs text-emerald-700">{{ entry.invoice_number }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Tab 3: Inbound Supplier Receipts Trace -->
            <div v-if="recallTab === 'inbound'">
              <div v-if="!recallReport.inbound_trace?.length" class="empty-trace-state">
                <span class="material-symbols-outlined text-gray-400">local_shipping</span>
                <p class="text-sm font-semibold mt-1">No inbound goods receipt records found for this lot number.</p>
              </div>
              <div v-else class="table-wrap border rounded-lg overflow-hidden">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Goods Receipt #</th>
                      <th>Receipt Date</th>
                      <th>Purchase Order #</th>
                      <th>Supplier Name</th>
                      <th>Supplier Contact</th>
                      <th class="text-center">Qty Received</th>
                      <th>Warehouse</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(entry, idx) in recallReport.inbound_trace" :key="idx">
                      <td>
                        <span class="mono font-semibold text-blue-700">{{ entry.receipt_number || ('GRN#' + entry.receipt_id) }}</span>
                      </td>
                      <td>{{ entry.receipt_date ? formatDate(entry.receipt_date) : '-' }}</td>
                      <td>
                        <span v-if="entry.po_number" class="font-medium">{{ entry.po_number }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                      <td>
                        <div class="font-semibold">{{ entry.supplier_name }}</div>
                        <div v-if="entry.supplier_category" class="text-xs text-muted">{{ entry.supplier_category }}</div>
                      </td>
                      <td>
                        <div class="text-xs">
                          <div v-if="entry.supplier_email">{{ entry.supplier_email }}</div>
                          <div v-if="entry.supplier_phone" class="text-muted">{{ entry.supplier_phone }}</div>
                          <span v-if="!entry.supplier_email && !entry.supplier_phone">-</span>
                        </div>
                      </td>
                      <td class="text-center font-bold text-blue-700">{{ entry.qty_received }}</td>
                      <td>{{ entry.warehouse_name || ('WH #' + (entry.warehouse_id || 1)) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </div>

        <div class="modal-footer flex justify-between items-center">
          <div class="text-xs text-muted">
            <span v-if="recallReport">Traceability report generated for food safety compliance</span>
          </div>
          <button class="btn-secondary" @click="closeRecallModal">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-if="confirmTarget"
      :title="t('confirm-delete', 'Confirm Delete')"
      :message="t('confirm-delete-msg', 'Are you sure you want to delete batch') + ' ' + confirmTarget.batch_number + '?'"
      @confirm="executeDelete(confirmTarget)"
      @cancel="confirmTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const items = ref([])
const products = ref([])
const warehouses = ref([])

const searchQuery = ref('')
const filterStatus = ref('')
const filterWarehouse = ref('')

const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({
  batch_number: '',
  product_id: null,
  warehouse_id: null,
  quantity: 0,
  manufacturing_date: '',
  expiry_date: '',
  status: 'Available',
  notes: ''
})
const editId = ref(null)
const confirmTarget = ref(null)

// Recall & Traceability Modal state
const showRecallModal = ref(false)
const recallSearchQuery = ref('')
const recallLoading = ref(false)
const recallError = ref('')
const recallReport = ref(null)
const recallTab = ref('customers')

const filteredItems = computed(() => {
  return items.value.filter(item => {
    if (filterStatus.value && item.status !== filterStatus.value) return false
    if (filterWarehouse.value && item.warehouse_id !== Number(filterWarehouse.value)) return false
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim()
      const matchBatch = (item.batch_number || '').toLowerCase().includes(q)
      const p = products.value.find(x => x.id === item.product_id)
      const matchProduct = p && ((p.name || '').toLowerCase().includes(q) || (p.sku || '').toLowerCase().includes(q))
      return matchBatch || matchProduct
    }
    return true
  })
})

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function productName(id) {
  const p = products.value.find(x => x.id === id)
  return p ? `${p.sku} - ${p.name}` : `#${id}`
}

function warehouseName(id) {
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : (id ? `#${id}` : '-')
}

function getExpiryClass(expDate) {
  if (!expDate) return 'text-muted'
  const exp = new Date(expDate)
  const now = new Date()
  const diffDays = Math.ceil((exp - now) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return 'text-red-600 font-bold'
  if (diffDays <= 30) return 'text-amber-600 font-semibold'
  return 'text-gray-700'
}

function getStatusBadgeClass(status, expDate) {
  if (expDate && new Date(expDate) < new Date()) {
    return 'badge-danger'
  }
  switch (status) {
    case 'Available':
      return 'badge-success'
    case 'Partially Used':
      return 'badge-warning'
    case 'Depleted':
      return 'badge-secondary'
    case 'Expired':
      return 'badge-danger'
    default:
      return 'badge-info'
  }
}

async function loadLookups() {
  try {
    const [pRes, wRes] = await Promise.all([
      api.get('/T0003I/'),
      api.get('/T0008I/').catch(() => ({ data: [] }))
    ])
    products.value = pRes.data || []
    warehouses.value = wRes.data || []
  } catch {}
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0088I/')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load batch numbers')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  form.value = {
    batch_number: '',
    product_id: null,
    warehouse_id: warehouses.value[0]?.id || null,
    quantity: 0,
    manufacturing_date: '',
    expiry_date: '',
    status: 'Available',
    notes: ''
  }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    batch_number: item.batch_number,
    product_id: item.product_id,
    warehouse_id: item.warehouse_id,
    quantity: item.quantity,
    manufacturing_date: item.manufacturing_date || '',
    expiry_date: item.expiry_date || '',
    status: item.status || 'Available',
    notes: item.notes || ''
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    if (editing.value) {
      await api.put(`/T0088I/${editId.value}`, form.value)
      toast('Batch ' + t('saved-ok', 'saved successfully'), 'success')
    } else {
      await api.post('/T0088I/', form.value)
      toast('Batch ' + t('saved-ok', 'created successfully'), 'success')
    }
    closeModal()
    await load()
  } catch (err) {
    toast(err?.response?.data?.detail || t('failed-save', 'Failed to save batch'), 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) {
  confirmTarget.value = item
}

async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0088I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Batch deleted', 'success')
  } catch {
    toast(t('failed-save', 'Failed to delete batch'), 'error')
  }
}

// Recall Modal Handlers
function openRecallModal(item) {
  showRecallModal.value = true
  recallTab.value = 'customers'
  recallError.value = ''
  if (item && item.batch_number) {
    recallSearchQuery.value = item.batch_number
    runRecallReport()
  } else {
    recallReport.value = null
  }
}

function closeRecallModal() {
  showRecallModal.value = false
}

async function runRecallReport() {
  const q = recallSearchQuery.value.trim()
  if (!q) return
  recallLoading.value = true
  recallError.value = ''
  try {
    const res = await api.get('/T0088I/recall-report', {
      params: { batch_number: q }
    })
    recallReport.value = res.data
  } catch (err) {
    recallReport.value = null
    recallError.value = err?.response?.data?.detail || `No recall information found for batch '${q}'`
  } finally {
    recallLoading.value = false
  }
}

onMounted(() => {
  loadLookups()
  load()
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.filter-card { background: #fff; border: 1px solid #e8e8ee; border-radius: 10px; padding: 12px 16px; }
.search-input-wrap { position: relative; }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #999; }
.search-input { padding-left: 36px; }
.filter-select { width: 180px; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 16px; font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; vertical-align: middle; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fcfcff; }
.text-center { text-align: center; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.lot-pill { color: #5d3fd3; font-weight: 700; background: #ede7f6; padding: 3px 8px; border-radius: 6px; }
.text-red-500 { color: #e53935; }
.text-red-600 { color: #d32f2f; }
.text-amber-600 { color: #d97706; }
.text-amber-700 { color: #b45309; }
.text-amber-900 { color: #78350f; }
.text-emerald-700 { color: #047857; }
.text-purple-700 { color: #6b21a8; }
.text-purple-900 { color: #3b0764; }
.text-gray-400 { color: #9ca3af; }
.text-gray-600 { color: #4b5563; }
.text-gray-800 { color: #1f2937; }
.text-gray-900 { color: #111827; }
.text-muted { color: #6b7280; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
.font-extrabold { font-weight: 800; }

.badge { display: inline-flex; align-items: center; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff8e1; color: #f57f17; }
.badge-danger { background: #ffebee; color: #c62828; }
.badge-info { background: #e3f2fd; color: #1565c0; }
.badge-secondary { background: #f3f4f6; color: #4b5563; }
.badge-outline { background: #fff; border: 1px solid #e5e7eb; color: #374151; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 9px 16px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.btn-recall { display: inline-flex; align-items: center; gap: 6px; padding: 9px 16px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; }
.btn-recall:hover { background: #fef3c7; color: #92400e; }
.btn-recall .material-symbols-outlined { font-size: 18px; color: #d97706; }

.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 9px 16px; background: #f0f0f4; color: #333; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover { background: #e0e0e0; }

.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; color: #666; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 16px; }
.modal { background: #fff; border-radius: 12px; width: 520px; max-width: 95vw; max-height: 88vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.25); }
.modal-xl { width: 920px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.bg-recall-header { background: #fefce8; border-bottom: 1px solid #fef08a; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 20px; border-top: 1px solid #eee; background: #fafafa; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 11px; font-weight: 700; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }

.recall-banner { background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 10px; padding: 14px 18px; }
.recall-search-bar { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
.recall-search-input { font-size: 14px; font-family: 'JetBrains Mono', monospace; }
.recall-error-alert { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; color: #991b1b; }

.stat-card { display: flex; align-items: center; gap: 10px; padding: 12px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; }
.stat-icon-wrap { width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.stat-val { font-size: 18px; font-weight: 700; color: #111827; }
.stat-lbl { font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px; }

.tab-nav { display: flex; gap: 4px; border-bottom: 2px solid #e5e7eb; }
.tab-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 12px; font-weight: 600; color: #6b7280; background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; }
.tab-btn.active { color: #5d3fd3; border-bottom-color: #5d3fd3; }
.tab-badge { background: #e5e7eb; color: #374151; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 10px; }
.tab-btn.active .tab-badge { background: #ede7f6; color: #5d3fd3; }

.empty-trace-state { text-align: center; padding: 32px; color: #6b7280; background: #f9fafb; border-radius: 8px; }
.icon-xs { font-size: 16px; }
.icon-2xs { font-size: 13px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
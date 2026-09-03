<template>
  <div :dir="dir" class="batch-recall-view">
    <InventorySubNav />

    <div class="p-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-amber-600 text-3xl">crisis_alert</span>
            <h1 class="page-title">{{ t('batch-recall-title', 'Batch Recall & Traceability Report') }}</h1>
          </div>
          <p class="page-subtitle">
            {{ t('batch-recall-sub', 'Trace upstream supplier receipts, current warehouse stock, and downstream customer shipments for food safety compliance') }}
          </p>
        </div>

        <div class="flex items-center gap-2" v-if="recallReport">
          <button class="btn-secondary flex items-center gap-1" @click="exportRecallCsv">
            <span class="material-symbols-outlined text-sm">download</span>
            {{ t('export-csv', 'Export Customers CSV') }}
          </button>
          <button class="btn-primary flex items-center gap-1" @click="printReport">
            <span class="material-symbols-outlined text-sm">print</span>
            {{ t('print-report', 'Print Recall Report') }}
          </button>
        </div>
      </div>

      <!-- Search & Input Card -->
      <div class="filter-card mb-6">
        <form @submit.prevent="runRecallReport" class="flex flex-col md:flex-row items-end gap-3">
          <div class="flex-1 w-full">
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
              {{ t('search-batch-number', 'Batch / Lot Number') }}
            </label>
            <div class="search-input-wrap">
              <span class="material-symbols-outlined search-icon">search</span>
              <input
                type="text"
                v-model="searchBatchNumber"
                class="form-input search-input w-full"
                :placeholder="t('placeholder-batch-num', 'Enter Batch / Lot # (e.g. LOT-2026-0819)...')"
              />
            </div>
          </div>

          <div class="w-full md:w-56">
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
              {{ t('select-quick-batch', 'Or Select Registered Batch') }}
            </label>
            <select v-model="selectedBatchId" class="form-input w-full" @change="onSelectBatchId">
              <option :value="null">-- Select Batch --</option>
              <option v-for="b in registeredBatches" :key="b.id" :value="b.id">
                {{ b.batch_number }} (Qty: {{ b.quantity }})
              </option>
            </select>
          </div>

          <div class="flex gap-2 w-full md:w-auto">
            <button
              type="submit"
              class="btn-primary flex-1 md:flex-none flex items-center justify-center gap-1"
              :disabled="loading || (!searchBatchNumber.trim() && !selectedBatchId)"
            >
              <span v-if="loading" class="material-symbols-outlined spin">progress_activity</span>
              <span v-else class="material-symbols-outlined">search</span>
              {{ loading ? t('tracing', 'Tracing...') : t('run-trace', 'Run Trace Report') }}
            </button>
            <button
              type="button"
              class="btn-secondary"
              @click="resetSearch"
              v-if="searchBatchNumber || selectedBatchId || recallReport"
            >
              {{ t('reset', 'Reset') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-16 data-card">
        <span class="material-symbols-outlined spin text-4xl text-purple-600 mb-3">progress_activity</span>
        <h3 class="text-base font-bold text-gray-800">{{ t('loading-trace', 'Generating End-to-End Recall Trace Report...') }}</h3>
        <p class="text-xs text-muted mt-1">{{ t('loading-sub', 'Tracing supplier receipts, warehouse inventory, and customer shipments') }}</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="recall-error-alert mb-6">
        <span class="material-symbols-outlined text-red-600 text-2xl">error</span>
        <div class="flex-1">
          <h4 class="font-bold text-red-900 text-sm">{{ t('lot-not-found', 'Batch / Lot Record Not Found') }}</h4>
          <p class="text-xs text-red-700 mt-0.5">{{ error }}</p>
        </div>
      </div>

      <!-- Empty State before search -->
      <div v-else-if="!recallReport" class="data-card p-12 text-center">
        <span class="material-symbols-outlined empty-icon text-amber-500">shield_with_heart</span>
        <h3 class="text-lg font-bold text-gray-800 mb-1">{{ t('ready-to-trace', 'Food Safety & Lot Recall Traceability') }}</h3>
        <p class="text-sm text-gray-500 max-w-md mx-auto mb-6">
          {{ t('ready-desc', 'Enter a batch/lot number or select a batch from inventory above to instantly identify all affected customers, sales orders, and supplier receipts.') }}
        </p>

        <!-- Quick Batch Badges -->
        <div v-if="registeredBatches.length" class="max-w-2xl mx-auto border-t pt-4">
          <div class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            {{ t('recent-batches', 'Quick Select Recent Batches') }}
          </div>
          <div class="flex flex-wrap justify-center gap-2">
            <button
              v-for="b in registeredBatches.slice(0, 8)"
              :key="b.id"
              class="quick-batch-chip"
              @click="quickSelectBatch(b)"
            >
              <span class="mono font-semibold">{{ b.batch_number }}</span>
              <span class="badge badge-sm ml-1">{{ b.status || 'Available' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Traceability Report Contents -->
      <div v-else class="space-y-6 printable-area">
        <!-- Lot Metadata Card -->
        <div class="recall-banner p-4 rounded-xl border">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span class="mono text-xl font-bold text-purple-950">{{ recallReport.batch?.batch_number }}</span>
                <span class="badge" :class="getStatusBadgeClass(recallReport.batch?.status, recallReport.batch?.expiry_date)">
                  {{ recallReport.batch?.status || 'Active' }}
                </span>
              </div>
              <div class="text-base font-bold text-gray-900 mt-1">
                {{ recallReport.batch?.product_name || 'Product' }}
                <span v-if="recallReport.batch?.product_sku" class="text-sm text-muted font-mono font-normal">({{ recallReport.batch?.product_sku }})</span>
              </div>
              <div v-if="recallReport.batch?.product_category" class="text-xs text-gray-600 mt-0.5">
                Category: {{ recallReport.batch.product_category }}
              </div>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <span class="text-muted block font-medium">Warehouse:</span>
                <span class="font-bold text-gray-800">{{ recallReport.batch?.warehouse_name || 'All Warehouses' }}</span>
              </div>
              <div>
                <span class="text-muted block font-medium">Manufacturing Date:</span>
                <span class="font-bold text-gray-800">{{ recallReport.batch?.manufacturing_date ? formatDate(recallReport.batch?.manufacturing_date) : '-' }}</span>
              </div>
              <div>
                <span class="text-muted block font-medium">Expiration Date:</span>
                <span class="font-bold" :class="getExpiryClass(recallReport.batch?.expiry_date)">
                  {{ recallReport.batch?.expiry_date ? formatDate(recallReport.batch?.expiry_date) : '-' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Metric Stat Cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="stat-card">
            <div class="stat-icon-wrap bg-blue-50 text-blue-600">
              <span class="material-symbols-outlined">input</span>
            </div>
            <div>
              <div class="stat-val text-blue-900">{{ recallReport.summary?.total_qty_received || 0 }}</div>
              <div class="stat-lbl">{{ t('stat-received', 'Total Inbound Received') }}</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon-wrap bg-purple-50 text-purple-600">
              <span class="material-symbols-outlined">output</span>
            </div>
            <div>
              <div class="stat-val text-purple-900">{{ recallReport.summary?.total_qty_picked || 0 }}</div>
              <div class="stat-lbl">{{ t('stat-shipped', 'Total Outbound Shipped') }}</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon-wrap bg-emerald-50 text-emerald-600">
              <span class="material-symbols-outlined">warehouse</span>
            </div>
            <div>
              <div class="stat-val text-emerald-900">{{ recallReport.summary?.current_quantity || 0 }}</div>
              <div class="stat-lbl">{{ t('stat-warehouse-stock', 'Current Warehouse Stock') }}</div>
            </div>
          </div>

          <div class="stat-card" :class="(recallReport.summary?.total_affected_customers || 0) > 0 ? 'border-amber-400 bg-amber-50/50' : ''">
            <div class="stat-icon-wrap bg-amber-100 text-amber-700">
              <span class="material-symbols-outlined">group</span>
            </div>
            <div>
              <div class="stat-val text-amber-800 font-extrabold">{{ recallReport.summary?.total_affected_customers || 0 }}</div>
              <div class="stat-lbl text-amber-950 font-bold">{{ t('stat-affected-customers', 'Affected Customers') }}</div>
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'customers' }"
            @click="activeTab = 'customers'"
          >
            <span class="material-symbols-outlined icon-xs">group</span>
            {{ t('tab-customers', 'Affected Customers') }}
            <span class="tab-badge" v-if="recallReport.affected_customers?.length">
              {{ recallReport.affected_customers.length }}
            </span>
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeTab === 'outbound' }"
            @click="activeTab = 'outbound'"
          >
            <span class="material-symbols-outlined icon-xs">local_shipping</span>
            {{ t('tab-outbound', 'Sales & Shipments Trace') }}
            <span class="tab-badge" v-if="recallReport.outbound_trace?.length">
              {{ recallReport.outbound_trace.length }}
            </span>
          </button>

          <button
            class="tab-btn"
            :class="{ active: activeTab === 'inbound' }"
            @click="activeTab = 'inbound'"
          >
            <span class="material-symbols-outlined icon-xs">inventory</span>
            {{ t('tab-inbound', 'Supplier Receipts Trace') }}
            <span class="tab-badge" v-if="recallReport.inbound_trace?.length">
              {{ recallReport.inbound_trace.length }}
            </span>
          </button>
        </div>

        <!-- Tab 1: Affected Customers -->
        <div v-if="activeTab === 'customers'" class="data-card">
          <div v-if="!recallReport.affected_customers?.length" class="empty-trace-state p-8 text-center">
            <span class="material-symbols-outlined text-gray-400 text-4xl mb-2">check_circle</span>
            <h4 class="text-sm font-bold text-gray-800">{{ t('no-customers-affected', 'No Customers Affected Yet') }}</h4>
            <p class="text-xs text-muted mt-1">{{ t('no-customers-sub', 'No customer shipments have been fulfilled with this lot. All available quantity is currently stored in warehouse inventory.') }}</p>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('customer-name', 'Customer Name') }}</th>
                  <th>{{ t('contact-info', 'Contact Information') }}</th>
                  <th>{{ t('group', 'Customer Group') }}</th>
                  <th class="text-center">{{ t('qty-shipped', 'Qty Shipped') }}</th>
                  <th>{{ t('sales-orders', 'Affected Sales Orders') }}</th>
                  <th>{{ t('invoices', 'Invoices') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cust in recallReport.affected_customers" :key="cust.customer_id || cust.customer_name">
                  <td>
                    <div class="font-bold text-gray-900">{{ cust.customer_name }}</div>
                    <div class="text-xs text-muted">ID: #{{ cust.customer_id }}</div>
                  </td>
                  <td>
                    <div class="text-xs space-y-0.5">
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
                    <span class="font-bold text-amber-700 text-sm">{{ cust.total_qty_picked }}</span>
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
        <div v-if="activeTab === 'outbound'" class="data-card">
          <div v-if="!recallReport.outbound_trace?.length" class="empty-trace-state p-8 text-center">
            <span class="material-symbols-outlined text-gray-400 text-4xl mb-2">inventory</span>
            <h4 class="text-sm font-bold text-gray-800">{{ t('no-outbound-trace', 'No Outbound Pick List Entries') }}</h4>
            <p class="text-xs text-muted mt-1">{{ t('no-outbound-sub', 'No pick list items or sales orders recorded for this lot.') }}</p>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('pick-list-num', 'Pick List #') }}</th>
                  <th>{{ t('sales-order-num', 'Sales Order #') }}</th>
                  <th>{{ t('customer', 'Customer') }}</th>
                  <th>{{ t('order-date', 'Order Date') }}</th>
                  <th class="text-center">{{ t('qty-picked', 'Qty Picked') }}</th>
                  <th>{{ t('status', 'Status') }}</th>
                  <th>{{ t('invoice-num', 'Invoice #') }}</th>
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
        <div v-if="activeTab === 'inbound'" class="data-card">
          <div v-if="!recallReport.inbound_trace?.length" class="empty-trace-state p-8 text-center">
            <span class="material-symbols-outlined text-gray-400 text-4xl mb-2">local_shipping</span>
            <h4 class="text-sm font-bold text-gray-800">{{ t('no-inbound-trace', 'No Inbound Goods Receipts') }}</h4>
            <p class="text-xs text-muted mt-1">{{ t('no-inbound-sub', 'No inbound PO goods receipt records found for this lot.') }}</p>
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ t('grn-num', 'Goods Receipt #') }}</th>
                  <th>{{ t('receipt-date', 'Receipt Date') }}</th>
                  <th>{{ t('po-num', 'Purchase Order #') }}</th>
                  <th>{{ t('supplier-name', 'Supplier Name') }}</th>
                  <th>{{ t('supplier-contact', 'Supplier Contact') }}</th>
                  <th class="text-center">{{ t('qty-received', 'Qty Received') }}</th>
                  <th>{{ t('warehouse', 'Warehouse') }}</th>
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import InventorySubNav from '../../components/InventorySubNav.vue'

const route = useRoute()
const router = useRouter()
const { t, dir } = useI18n()
const { show: toast } = useToast()

const searchBatchNumber = ref('')
const selectedBatchId = ref(null)
const registeredBatches = ref([])

const loading = ref(false)
const error = ref('')
const recallReport = ref(null)
const activeTab = ref('customers')

async function loadBatches() {
  try {
    const res = await api.get('/T0088I/')
    registeredBatches.value = res.data || []
  } catch (err) {
    registeredBatches.value = []
  }
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
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

function onSelectBatchId() {
  if (selectedBatchId.value) {
    const found = registeredBatches.value.find(b => b.id === selectedBatchId.value)
    if (found && found.batch_number) {
      searchBatchNumber.value = found.batch_number
      runRecallReport()
    }
  }
}

function quickSelectBatch(batch) {
  selectedBatchId.value = batch.id
  searchBatchNumber.value = batch.batch_number
  runRecallReport()
}

function resetSearch() {
  searchBatchNumber.value = ''
  selectedBatchId.value = null
  recallReport.value = null
  error.value = ''
  router.replace({ name: 'batch-recall' })
}

async function runRecallReport() {
  const q = searchBatchNumber.value.trim()
  const bId = selectedBatchId.value

  if (!q && !bId) return

  loading.value = true
  error.value = ''
  recallReport.value = null

  try {
    const params = {}
    if (q) params.batch_number = q
    if (bId) params.batch_id = bId

    const res = await api.get('/T0088I/recall-report', { params })
    recallReport.value = res.data
    activeTab.value = 'customers'

    // Sync query parameters in router URL
    router.replace({
      name: 'batch-recall',
      query: { batch_number: q || undefined, batch_id: bId || undefined }
    })
  } catch (err) {
    recallReport.value = null
    error.value = err?.response?.data?.detail || `No recall trace data found for batch '${q || bId}'`
  } finally {
    loading.value = false
  }
}

function exportRecallCsv() {
  if (!recallReport.value || !recallReport.value.affected_customers?.length) {
    toast('No affected customers data to export', 'error')
    return
  }

  const batchNum = recallReport.value.batch?.batch_number || 'BATCH'
  const headers = ['Customer ID', 'Customer Name', 'Email', 'Phone', 'Customer Group', 'Qty Shipped', 'Sales Orders', 'Invoices']

  const rows = recallReport.value.affected_customers.map(c => [
    c.customer_id || '',
    `"${(c.customer_name || '').replace(/"/g, '""')}"`,
    c.email || '',
    c.phone || '',
    c.group_name || '',
    c.total_qty_picked || 0,
    `"${(c.orders || []).map(o => o.order_number || o.sales_order_id).join(', ')}"`,
    `"${(c.invoices || []).map(i => i.invoice_number || i.invoice_id).join(', ')}"`
  ])

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `Batch_Recall_${batchNum}_Customers.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  toast('Recall customer report exported to CSV', 'success')
}

function printReport() {
  window.print()
}

onMounted(() => {
  loadBatches()

  // Check URL query parameters
  const qBatchNumber = route.query.batch_number
  const qBatchId = route.query.batch_id

  if (qBatchNumber) {
    searchBatchNumber.value = String(qBatchNumber)
    runRecallReport()
  } else if (qBatchId) {
    selectedBatchId.value = Number(qBatchId)
    runRecallReport()
  }
})

watch(() => route.query.batch_number, (newVal) => {
  if (newVal && newVal !== searchBatchNumber.value) {
    searchBatchNumber.value = String(newVal)
    runRecallReport()
  }
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.filter-card { background: #fff; border: 1px solid #e8e8ee; border-radius: 10px; padding: 16px; }
.search-input-wrap { position: relative; }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #999; }
.search-input { padding-left: 36px; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 16px; font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; vertical-align: middle; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fcfcff; }

.recall-banner { background: linear-gradient(135deg, #fef3c7 0%, #ede9fe 100%); border-color: #fcd34d; }
.recall-error-alert { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 10px; padding: 14px 18px; display: flex; align-items: flex-start; gap: 12px; }

.stat-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; gap: 14px; }
.stat-icon-wrap { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-val { font-size: 20px; font-weight: 800; line-height: 1.1; }
.stat-lbl { font-size: 11px; color: #64748b; margin-top: 2px; font-weight: 500; }

.quick-batch-chip { display: inline-flex; align-items: center; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 20px; padding: 4px 12px; font-size: 12px; color: #334155; cursor: pointer; transition: all 0.15s; }
.quick-batch-chip:hover { background: #e2e8f0; border-color: #94a3b8; }

.tab-nav { display: flex; gap: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }
.tab-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border: 1px solid transparent; border-radius: 8px; font-size: 13px; font-weight: 600; color: #64748b; background: transparent; cursor: pointer; transition: all 0.15s; }
.tab-btn:hover { background: #f8fafc; color: #1e293b; }
.tab-btn.active { background: #ede9fe; color: #5b21b6; border-color: #ddd6fe; }
.tab-badge { background: #7c3aed; color: #fff; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 10px; }

.mono { font-family: 'JetBrains Mono', monospace; }
.icon-2xs { font-size: 14px; }
.icon-xs { font-size: 16px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@media print {
  body * { visibility: hidden; }
  .printable-area, .printable-area * { visibility: visible; }
  .printable-area { position: absolute; left: 0; top: 0; width: 100%; }
}
</style>

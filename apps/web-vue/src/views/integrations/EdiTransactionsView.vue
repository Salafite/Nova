<template>
  <div :dir="dir" class="edi-transactions-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('edi-transactions-title', 'EDI Transactions & Interchange Logs') }}</h1>
        <p class="page-subtitle">{{ t('edi-transactions-sub', 'Live Electronic Data Interchange Audit Log, Raw Payload Inspection, Functional ACK (997/CONTRL) & Reprocessing (T0126)') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="router.push('/integrations/edi-gateway')">
          <span class="material-symbols-outlined">hub</span>
          {{ t('edi-gateway', 'EDI Gateway') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-partners')">
          <span class="material-symbols-outlined">corporate_fare</span>
          {{ t('trading-partners', 'Trading Partners') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-sku-mapping')">
          <span class="material-symbols-outlined">dataset</span>
          {{ t('sku-matrix', 'SKU Matrix') }}
        </button>
        <button class="btn-outline" @click="exportTransactions">
          <span class="material-symbols-outlined">download</span>
          {{ t('export-logs', 'Export Logs') }}
        </button>
        <button class="btn-icon" @click="loadData" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="kpi-grid mb-6">
      <div class="kpi-card">
        <div class="kpi-icon icon-purple"><span class="material-symbols-outlined">swap_horiz</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-transactions', 'Total Transacted') }}</span>
          <span class="kpi-value">{{ kpis.total }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-blue"><span class="material-symbols-outlined">shopping_cart</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('inbound-orders', 'Inbound POs (850)') }}</span>
          <span class="kpi-value">{{ kpis.inboundOrders }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-teal"><span class="material-symbols-outlined">local_shipping</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('outbound-asns', 'Outbound ASNs (856)') }}</span>
          <span class="kpi-value">{{ kpis.outboundAsns }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-green"><span class="material-symbols-outlined">receipt_long</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('outbound-invoices', 'Outbound Invoices (810)') }}</span>
          <span class="kpi-value">{{ kpis.outboundInvoices }}</span>
        </div>
      </div>
      <div class="kpi-card" :class="{ 'kpi-alert': kpis.discrepancyHolds > 0 }">
        <div class="kpi-icon icon-amber"><span class="material-symbols-outlined">warning</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('price-holds', 'Price Discrepancy Holds') }}</span>
          <span class="kpi-value">{{ kpis.discrepancyHolds }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-indigo"><span class="material-symbols-outlined">fact_check</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('ack-accepted', 'ACKs Accepted') }}</span>
          <span class="kpi-value">{{ kpis.ackAccepted }}</span>
        </div>
      </div>
    </div>

    <!-- Filter & Table Section -->
    <div class="data-card">
      <div class="card-filter-bar">
        <div class="search-wrap">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('search-transactions', 'Search Transaction #, Control #, PO #, Partner...')"
          />
        </div>

        <div class="filters-wrap">
          <select v-model="filterDirection" class="filter-select">
            <option value="">{{ t('all-directions', 'All Directions') }}</option>
            <option value="INBOUND">{{ t('inbound', 'Inbound (↓)') }}</option>
            <option value="OUTBOUND">{{ t('outbound', 'Outbound (↑)') }}</option>
          </select>

          <select v-model="filterStandard" class="filter-select">
            <option value="">{{ t('all-standards', 'All Standards') }}</option>
            <option value="ANSI_X12">ANSI X12</option>
            <option value="EDIFACT">UN/EDIFACT</option>
          </select>

          <select v-model="filterDocType" class="filter-select">
            <option value="">{{ t('all-doc-types', 'All Document Types') }}</option>
            <option value="850">850 / ORDERS (PO)</option>
            <option value="856">856 / DESADV (ASN)</option>
            <option value="810">810 / INVOIC (Invoice)</option>
            <option value="832">832 / PRICAT (Catalog)</option>
            <option value="997">997 / CONTRL (ACK)</option>
          </select>

          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="PRICE_DISCREPANCY_HOLD">PRICE_DISCREPANCY_HOLD</option>
            <option value="FAILED">FAILED</option>
            <option value="PENDING">PENDING</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
          </select>

          <select v-model="filterPartner" class="filter-select">
            <option value="">{{ t('all-partners', 'All Partners') }}</option>
            <option v-for="p in partners" :key="p.id" :value="p.id">
              {{ p.partner_code }}
            </option>
          </select>
        </div>
      </div>

      <SkeletonTable v-if="loading" />
      <ErrorState v-else-if="error" :message="error" @retry="loadData" />

      <div v-else-if="!filteredTransactions.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">receipt_long</span>
        <p>{{ t('no-transactions-found', 'No EDI transactions found.') }}</p>
        <button class="btn-primary" @click="router.push('/integrations/edi-gateway')">
          {{ t('go-to-gateway', 'Go to EDI Gateway') }}
        </button>
      </div>

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('direction', 'Dir') }}</th>
              <th>{{ t('transaction-no', 'Transaction #') }}</th>
              <th>{{ t('doc-type', 'Doc Type') }}</th>
              <th>{{ t('standard', 'Standard') }}</th>
              <th>{{ t('partner', 'Partner') }}</th>
              <th>{{ t('control-no', 'Control #') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th>{{ t('linked-record', 'Linked Record') }}</th>
              <th>{{ t('ack-status', 'ACK') }}</th>
              <th>{{ t('processed-at', 'Timestamp') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in filteredTransactions" :key="tx.id">
              <td>
                <span
                  class="direction-pill"
                  :class="tx.direction === 'INBOUND' ? 'dir-in' : 'dir-out'"
                  :title="tx.direction"
                >
                  {{ tx.direction === 'INBOUND' ? '↓ IN' : '↑ OUT' }}
                </span>
              </td>
              <td>
                <strong
                  class="font-mono text-primary cursor-pointer hover:underline"
                  @click="inspectTransaction(tx)"
                >
                  {{ tx.transaction_number }}
                </strong>
              </td>
              <td>
                <span class="badge badge-doc">{{ tx.document_type }}</span>
              </td>
              <td>
                <span
                  class="badge"
                  :class="tx.standard === 'EDIFACT' ? 'badge-edifact' : 'badge-x12'"
                >
                  {{ tx.standard }}
                </span>
              </td>
              <td>
                <span class="font-semibold text-slate-800">{{ getPartnerCode(tx.partner_id) }}</span>
                <span class="text-xs text-muted block">{{ getPartnerName(tx.partner_id) }}</span>
              </td>
              <td class="font-mono text-xs">{{ tx.control_number || '-' }}</td>
              <td class="text-center">
                <span class="badge" :class="statusBadge(tx.status)">{{ tx.status }}</span>
              </td>
              <td>
                <div v-if="tx.sales_order_id" class="text-xs">
                  <span class="text-muted">SO:</span>
                  <a class="link-bold font-mono" @click="goToSalesOrder(tx.sales_order_id)">
                    #{{ tx.sales_order_id }}
                  </a>
                </div>
                <div v-else-if="tx.delivery_id" class="text-xs">
                  <span class="text-muted">Shipment:</span>
                  <span class="font-mono font-semibold">#{{ tx.delivery_id }}</span>
                </div>
                <div v-else-if="tx.invoice_id" class="text-xs">
                  <span class="text-muted">Invoice:</span>
                  <span class="font-mono font-semibold">#{{ tx.invoice_id }}</span>
                </div>
                <span v-else class="text-muted text-xs">-</span>
              </td>
              <td>
                <span class="badge badge-xs" :class="ackBadge(tx.ack_status)">
                  {{ tx.ack_status || 'PENDING' }}
                </span>
              </td>
              <td class="text-xs text-muted whitespace-nowrap">
                {{ formatDate(tx.processed_at || tx.created_at) }}
              </td>
              <td class="text-center">
                <div class="action-buttons">
                  <button
                    class="btn-icon"
                    :title="t('inspect-edi', 'Inspect EDI & ACK')"
                    @click="inspectTransaction(tx)"
                  >
                    <span class="material-symbols-outlined text-purple-600">visibility</span>
                  </button>
                  <button
                    v-if="tx.status === 'PRICE_DISCREPANCY_HOLD' || tx.status === 'FAILED'"
                    class="btn-icon"
                    :title="t('reprocess', 'Reprocess')"
                    @click="openReprocessModal(tx)"
                  >
                    <span class="material-symbols-outlined text-amber-600">restart_alt</span>
                  </button>
                  <button
                    class="btn-icon"
                    :title="t('copy-raw-edi', 'Copy Raw EDI')"
                    @click="copyRawEdi(tx)"
                  >
                    <span class="material-symbols-outlined text-slate-500">content_copy</span>
                  </button>
                  <button
                    class="btn-icon"
                    :title="t('download-edi', 'Download .edi file')"
                    @click="downloadEdiFile(tx)"
                  >
                    <span class="material-symbols-outlined text-blue-500">download</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal 1: Deep Inspector Modal (Raw, Parsed, ACK, Errors) -->
    <div v-if="inspectorTx" class="modal-overlay" @click.self="inspectorTx = null">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <div>
            <div class="flex items-center gap-2">
              <span class="badge" :class="statusBadge(inspectorTx.status)">{{ inspectorTx.status }}</span>
              <h3 class="modal-title">{{ inspectorTx.transaction_number }}</h3>
            </div>
            <p class="text-xs text-muted mt-1">
              {{ inspectorTx.standard }} {{ inspectorTx.document_type }} |
              {{ inspectorTx.direction }} |
              Control #: <strong>{{ inspectorTx.control_number || '-' }}</strong> |
              Partner: <strong>{{ getPartnerCode(inspectorTx.partner_id) }}</strong>
            </p>
          </div>
          <button class="btn-icon" @click="inspectorTx = null"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <div class="tabs mb-4">
            <button class="tab-btn" :class="{ active: inspectTab === 'raw' }" @click="inspectTab = 'raw'">
              <span class="material-symbols-outlined">code</span> {{ t('raw-payload', 'Raw EDI Payload') }}
            </button>
            <button class="tab-btn" :class="{ active: inspectTab === 'parsed' }" @click="inspectTab = 'parsed'">
              <span class="material-symbols-outlined">data_object</span> {{ t('parsed-json', 'Parsed JSON Structure') }}
            </button>
            <button class="tab-btn" :class="{ active: inspectTab === 'ack' }" @click="inspectTab = 'ack'">
              <span class="material-symbols-outlined">fact_check</span> {{ t('ack-message', 'Functional ACK (997/CONTRL)') }}
            </button>
            <button
              v-if="inspectorTx.error_details || inspectorTx.status === 'PRICE_DISCREPANCY_HOLD' || inspectorTx.status === 'FAILED'"
              class="tab-btn text-amber-600"
              :class="{ active: inspectTab === 'errors' }"
              @click="inspectTab = 'errors'"
            >
              <span class="material-symbols-outlined">error</span> {{ t('errors-holds', 'Errors & Holds') }}
            </button>
          </div>

          <!-- Raw EDI tab -->
          <div v-if="inspectTab === 'raw'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-muted">{{ t('edi-stream', 'EDI Segment Stream') }}</span>
                <span class="badge badge-doc badge-xs">{{ rawSegmentCount }} Segments</span>
                <span class="text-xs text-muted">{{ (inspectorTx.raw_payload || '').length }} chars</span>
              </div>
              <div class="flex gap-2">
                <button class="btn-sm btn-outline" @click="copyToClipboard(inspectorTx.raw_payload)">
                  <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy') }}
                </button>
                <button class="btn-sm btn-outline" @click="downloadEdiFile(inspectorTx)">
                  <span class="material-symbols-outlined">download</span> {{ t('download', 'Download .edi') }}
                </button>
              </div>
            </div>
            <pre class="code-viewer">{{ inspectorTx.raw_payload || 'No raw payload stored' }}</pre>
          </div>

          <!-- Parsed JSON tab -->
          <div v-if="inspectTab === 'parsed'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-semibold text-muted">{{ t('parsed-document-tree', 'Extracted Document Structure') }}</span>
              <button class="btn-sm btn-outline" @click="copyToClipboard(JSON.stringify(inspectorTx.parsed_data, null, 2))">
                <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy JSON') }}
              </button>
            </div>
            <pre class="code-viewer">{{ JSON.stringify(inspectorTx.parsed_data || {}, null, 2) }}</pre>
          </div>

          <!-- ACK tab -->
          <div v-if="inspectTab === 'ack'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-muted">{{ t('ack-status-label', 'ACK Status:') }}</span>
                <span class="badge" :class="ackBadge(inspectorTx.ack_status)">{{ inspectorTx.ack_status || 'NONE' }}</span>
              </div>
              <button v-if="inspectorTx.ack_payload" class="btn-sm btn-outline" @click="copyToClipboard(inspectorTx.ack_payload)">
                <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy') }}
              </button>
            </div>
            <pre class="code-viewer">{{ inspectorTx.ack_payload || 'No functional acknowledgment payload recorded.' }}</pre>
          </div>

          <!-- Errors & Holds tab -->
          <div v-if="inspectTab === 'errors'" class="inspector-tab-content">
            <div class="alert-box-warning mb-4">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-amber-700">warning</span>
                <strong class="text-sm text-amber-900">{{ t('discrepancy-notice', 'Order held or failed during ingestion') }}</strong>
              </div>
              <p class="text-xs text-amber-800 mt-2 font-mono whitespace-pre-wrap">
                {{ inspectorTx.error_details || 'Transaction marked with price discrepancies against contract thresholds.' }}
              </p>
            </div>

            <button class="btn-primary btn-sm" @click="openReprocessModal(inspectorTx)">
              <span class="material-symbols-outlined">restart_alt</span> {{ t('reprocess-now', 'Reprocess / Force Confirm') }}
            </button>
          </div>
        </div>

        <div class="modal-footer">
          <button
            v-if="inspectorTx.status === 'PRICE_DISCREPANCY_HOLD' || inspectorTx.status === 'FAILED'"
            class="btn-outline text-amber-700"
            @click="openReprocessModal(inspectorTx)"
          >
            <span class="material-symbols-outlined">restart_alt</span> {{ t('reprocess', 'Reprocess') }}
          </button>
          <button class="btn-primary" @click="inspectorTx = null">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>

    <!-- Modal 2: Reprocess Transaction Modal -->
    <div v-if="reprocessTarget" class="modal-overlay" @click.self="reprocessTarget = null">
      <div class="modal-content">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-amber-600">restart_alt</span>
            <h3 class="modal-title">{{ t('reprocess-title', 'Reprocess EDI Transaction') }}</h3>
          </div>
          <button class="btn-icon" @click="reprocessTarget = null"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <p class="text-sm text-slate-700 mb-4">
            {{ t('reprocess-desc', 'Re-evaluate cross-referencing and sales order generation for') }}
            <strong>{{ reprocessTarget.transaction_number }}</strong>.
          </p>

          <div class="form-group mb-4">
            <label class="checkbox-label font-medium">
              <input type="checkbox" v-model="reprocessForm.force_confirm" />
              <span>{{ t('force-confirm-override', 'Force Confirm (Bypass Price Discrepancy Holds)') }}</span>
            </label>
            <span class="text-xs text-muted block mt-1">
              Creates sales order in Confirmed status even if buyer price deviates beyond partner threshold.
            </span>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('override-price-tol', 'Override Price Discrepancy Tolerance (%)') }}</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              v-model.number="reprocessForm.override_price_tolerance"
              class="form-control"
              placeholder="e.g. 5.0"
            />
            <span class="text-xs text-muted block mt-1">
              Leave blank to use trading partner's configured tolerance percentage.
            </span>
          </div>

          <div v-if="reprocessResult" class="mt-3 p-3 rounded-lg border" :class="reprocessResult.status === 'CONFIRMED' || reprocessResult.status === 'PROCESSED' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-amber-50 border-amber-200 text-amber-800'">
            <strong>{{ t('reprocess-result', 'Outcome:') }}</strong> {{ reprocessResult.status }}
            <span v-if="reprocessResult.sales_order_number" class="ml-1">
              (Order: {{ reprocessResult.sales_order_number }})
            </span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="reprocessTarget = null">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="executeReprocess" :disabled="reprocessing">
            <span v-if="reprocessing" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">play_arrow</span>
            {{ reprocessing ? t('reprocessing', 'Reprocessing...') : t('execute-reprocess', 'Execute Reprocess') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// State
const loading = ref(true)
const error = ref('')
const transactions = ref([])
const partners = ref([])

// Filters
const searchQuery = ref('')
const filterDirection = ref('')
const filterStandard = ref('')
const filterDocType = ref('')
const filterStatus = ref('')
const filterPartner = ref('')

// Inspector Modal
const inspectorTx = ref(null)
const inspectTab = ref('raw')

// Reprocess Modal
const reprocessTarget = ref(null)
const reprocessForm = ref({
  force_confirm: true,
  override_price_tolerance: null,
})
const reprocessing = ref(false)
const reprocessResult = ref(null)

// Computed KPIs
const kpis = computed(() => {
  const total = transactions.value.length
  let inboundOrders = 0
  let outboundAsns = 0
  let outboundInvoices = 0
  let discrepancyHolds = 0
  let ackAccepted = 0

  for (const tx of transactions.value) {
    const doc = (tx.document_type || '').toUpperCase()
    const status = (tx.status || '').toUpperCase()
    const ack = (tx.ack_status || '').toUpperCase()

    if (doc === '850' || doc === 'ORDERS') inboundOrders++
    if (doc === '856' || doc === 'DESADV') outboundAsns++
    if (doc === '810' || doc === 'INVOIC') outboundInvoices++
    if (status === 'PRICE_DISCREPANCY_HOLD' || status === 'FAILED') discrepancyHolds++
    if (ack === 'ACCEPTED' || ack === 'ACKNOWLEDGED') ackAccepted++
  }

  return {
    total,
    inboundOrders,
    outboundAsns,
    outboundInvoices,
    discrepancyHolds,
    ackAccepted,
  }
})

// Filtered Transactions
const filteredTransactions = computed(() => {
  return transactions.value.filter(tx => {
    if (filterDirection.value && tx.direction !== filterDirection.value) return false
    if (filterStandard.value && tx.standard !== filterStandard.value) return false
    if (filterDocType.value && tx.document_type !== filterDocType.value) return false
    if (filterStatus.value && tx.status !== filterStatus.value) return false
    if (filterPartner.value && String(tx.partner_id) !== String(filterPartner.value)) return false

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const txn = (tx.transaction_number || '').toLowerCase()
      const ctrl = (tx.control_number || '').toLowerCase()
      const doc = (tx.document_type || '').toLowerCase()
      const std = (tx.standard || '').toLowerCase()
      const pCode = getPartnerCode(tx.partner_id).toLowerCase()
      return txn.includes(q) || ctrl.includes(q) || doc.includes(q) || std.includes(q) || pCode.includes(q)
    }
    return true
  })
})

// Raw Segment Count
const rawSegmentCount = computed(() => {
  if (!inspectorTx.value || !inspectorTx.value.raw_payload) return 0
  const raw = inspectorTx.value.raw_payload.trim()
  const sep = inspectorTx.value.standard === 'EDIFACT' ? "'" : '~'
  return raw.split(sep).filter(s => s.trim().length > 0).length
})

// Helper Functions
function formatDate(d) {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d
  }
}

function getPartnerCode(partnerId) {
  if (!partnerId) return 'GLOBAL'
  const found = partners.value.find(p => p.id === partnerId)
  return found ? found.partner_code : `Partner #${partnerId}`
}

function getPartnerName(partnerId) {
  if (!partnerId) return ''
  const found = partners.value.find(p => p.id === partnerId)
  return found ? found.partner_name : ''
}

function statusBadge(status) {
  const s = (status || '').toUpperCase()
  if (s === 'PROCESSED' || s === 'CONFIRMED' || s === 'SYNCED' || s === 'DISPATCHED' || s === 'DELIVERED') return 'badge-success'
  if (s === 'PRICE_DISCREPANCY_HOLD') return 'badge-warning'
  if (s === 'FAILED') return 'badge-danger'
  if (s === 'PENDING') return 'badge-pending'
  return 'badge-doc'
}

function ackBadge(ack) {
  const a = (ack || '').toUpperCase()
  if (a === 'ACCEPTED' || a === 'ACKNOWLEDGED') return 'badge-success'
  if (a === 'ACCEPTED_WITH_ERRORS') return 'badge-warning'
  if (a === 'REJECTED') return 'badge-danger'
  return 'badge-disabled'
}

function copyToClipboard(text) {
  if (!text) return
  navigator.clipboard.writeText(text)
  toast(t('copied-to-clipboard', 'Copied to clipboard'))
}

function copyRawEdi(tx) {
  if (!tx.raw_payload) {
    toast(t('no-raw-payload', 'No raw payload stored for this transaction'), 'warning')
    return
  }
  copyToClipboard(tx.raw_payload)
}

function downloadEdiFile(tx) {
  if (!tx || !tx.raw_payload) {
    toast(t('no-raw-payload', 'No raw payload available to download'), 'warning')
    return
  }
  const filename = `${tx.transaction_number || 'edi_document'}.edi`
  const blob = new Blob([tx.raw_payload], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function goToSalesOrder(soId) {
  if (!soId) return
  router.push(`/sales/orders?id=${soId}`)
}

// Data Loading
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [txRes, pRes] = await Promise.allSettled([
      api.get('/T0126I/?limit=300'),
      api.get('/T0124I/?limit=100'),
    ])

    if (txRes.status === 'fulfilled') {
      transactions.value = Array.isArray(txRes.value.data) ? txRes.value.data : (txRes.value.data?.items || [])
    }
    if (pRes.status === 'fulfilled') {
      partners.value = Array.isArray(pRes.value.data) ? pRes.value.data : (pRes.value.data?.items || [])
    }
  } catch (err) {
    console.error('Failed to load EDI transactions:', err)
    error.value = t('failed-load', 'Failed to load EDI transactions')
  } finally {
    loading.value = false
  }
}

// Inspector Modal
async function inspectTransaction(tx) {
  inspectorTx.value = { ...tx }
  inspectTab.value = 'raw'

  // Fetch full details if raw_payload is missing
  if (!tx.raw_payload) {
    try {
      const res = await api.get(`/edi/transactions/${tx.id}/raw`)
      if (res.data) {
        inspectorTx.value.raw_payload = res.data.raw_payload
        inspectorTx.value.parsed_data = res.data.parsed_data
      }
    } catch (err) {
      console.warn('Could not fetch transaction raw payload:', err)
    }
  }

  // Fetch ACK payload if missing
  if (!inspectorTx.value.ack_payload) {
    try {
      const ackRes = await api.get(`/edi/transactions/${tx.id}/ack`)
      if (ackRes.data) {
        inspectorTx.value.ack_payload = ackRes.data.ack_payload
        inspectorTx.value.ack_status = ackRes.data.ack_status || inspectorTx.value.ack_status
        if (ackRes.data.error_details) {
          inspectorTx.value.error_details = ackRes.data.error_details
        }
      }
    } catch (err) {
      console.warn('Could not fetch transaction ack payload:', err)
    }
  }
}

// Reprocess Modal
function openReprocessModal(tx) {
  reprocessTarget.value = tx
  reprocessResult.value = null
  reprocessForm.value = {
    force_confirm: true,
    override_price_tolerance: null,
  }
}

async function executeReprocess() {
  if (!reprocessTarget.value) return
  reprocessing.value = true
  reprocessResult.value = null
  try {
    const res = await api.post(`/edi/transactions/${reprocessTarget.value.id}/reprocess`, {
      transaction_id: reprocessTarget.value.id,
      force_confirm: reprocessForm.value.force_confirm,
      override_price_tolerance: reprocessForm.value.override_price_tolerance,
    })
    reprocessResult.value = res.data
    toast(t('reprocess-success', 'Transaction reprocessed successfully'))
    await loadData()
    if (inspectorTx.value && inspectorTx.value.id === reprocessTarget.value.id) {
      inspectorTx.value.status = res.data.status
    }
  } catch (err) {
    console.error('Reprocess failed:', err)
    toast(err.response?.data?.detail || t('reprocess-failed', 'Transaction reprocess failed'), 'error')
  } finally {
    reprocessing.value = false
  }
}

function exportTransactions() {
  if (!transactions.value.length) {
    toast(t('no-data-export', 'No transactions to export'), 'warning')
    return
  }

  const exportData = transactions.value.map(tx => ({
    transaction_number: tx.transaction_number,
    direction: tx.direction,
    standard: tx.standard,
    document_type: tx.document_type,
    partner: getPartnerCode(tx.partner_id),
    control_number: tx.control_number,
    status: tx.status,
    ack_status: tx.ack_status,
    sales_order_id: tx.sales_order_id,
    processed_at: tx.processed_at || tx.created_at,
  }))

  const jsonStr = JSON.stringify(exportData, null, 2)
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `edi_transactions_${new Date().toISOString().slice(0,10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  toast(t('export-downloaded', 'EDI transactions exported'))
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.edi-transactions-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 800;
  color: #1e293b;
  margin: 0 0 4px 0;
}
.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* KPI Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.kpi-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #f1f5f9;
}
.kpi-alert {
  border-color: #fed7aa;
  background: #fffbeb;
}
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.icon-purple { background: #f3e8ff; color: #7e22ce; }
.icon-green { background: #e8f5e9; color: #2e7d32; }
.icon-blue { background: #e0f2fe; color: #0284c7; }
.icon-teal { background: #ccfbf1; color: #0f766e; }
.icon-indigo { background: #e0e7ff; color: #4338ca; }
.icon-amber { background: #fff3e0; color: #d97706; }

.kpi-info {
  display: flex;
  flex-direction: column;
}
.kpi-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}
.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: #1e293b;
  margin-top: 2px;
}

/* Data Card & Tables */
.data-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #f1f5f9;
  overflow: hidden;
}
.card-filter-bar {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 260px;
  max-width: 440px;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 18px;
}
.search-input {
  width: 100%;
  padding: 7px 12px 7px 34px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}
.search-input:focus {
  border-color: #5d3fd3;
  box-shadow: 0 0 0 2px rgba(93, 63, 211, 0.1);
}
.filters-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-select {
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  color: #334155;
  background: #fff;
  outline: none;
}
.table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  background: #f8fafc;
  color: #64748b;
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}
.data-table tbody tr:hover {
  background: #fbfbfe;
}

/* Direction Pills & Badges */
.direction-pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}
.dir-in { background: #e0f2fe; color: #0369a1; }
.dir-out { background: #ede9fe; color: #6d28d9; }

.badge { display: inline-block; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; }
.badge-xs { display: inline-block; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 600; }
.badge-x12 { background: #f3e8ff; color: #7e22ce; }
.badge-edifact { background: #e0f2fe; color: #0369a1; }
.badge-doc { background: #f1f5f9; color: #475569; font-family: monospace; font-weight: 700; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #d97706; }
.badge-danger { background: #fee2e2; color: #b91c1c; }
.badge-pending { background: #fef3c7; color: #92400e; }
.badge-disabled { background: #f1f5f9; color: #94a3b8; }

.link-bold {
  color: #5d3fd3;
  font-weight: 600;
  cursor: pointer;
}
.link-bold:hover {
  text-decoration: underline;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #5d3fd3;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #fff;
  color: #4b5563;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }

.btn-sm { padding: 5px 10px; font-size: 12px; }
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: #666;
}
.btn-icon:hover { background: #f0f0f4; }

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: #fff;
  border-radius: 14px;
  width: 90%;
  max-width: 580px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}
.modal-xl { max-width: 920px; }
.modal-header {
  padding: 16px 22px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-body { padding: 20px 22px; overflow-y: auto; flex: 1; }
.modal-footer {
  padding: 14px 22px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: #fafafa;
}

.tabs { display: flex; gap: 4px; border-bottom: 1px solid #e2e8f0; padding-bottom: 2px; }
.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: none;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
}
.tab-btn.active {
  color: #5d3fd3;
  border-bottom: 2px solid #5d3fd3;
  background: #f5f3ff;
}

.code-viewer {
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.alert-box-warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 14px;
}

/* Forms */
.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }
</style>

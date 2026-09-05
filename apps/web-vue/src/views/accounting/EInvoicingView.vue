<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6 flex-wrap gap-3">
      <div>
        <h1 class="page-title">{{ t('einvoicing-title', 'E-Invoicing & Fiscal Clearance') }}</h1>
        <p class="page-subtitle">{{ t('einvoicing-subtitle', 'Manage government tax authority clearance, ZATCA Phase 1 & 2 UBL XML, and TLV QR compliance.') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-outline" @click="$router.push('/accounting/fiscal-settings')">
          <span class="material-symbols-outlined icon-xs">settings_suggest</span>
          {{ t('fiscal-profiles', 'Fiscal Authority Settings') }}
        </button>
        <button class="btn-primary" @click="$router.push('/finance')">
          <span class="material-symbols-outlined icon-xs">receipt_long</span>
          {{ t('invoices', 'Invoices List') }}
        </button>
      </div>
    </div>

    <!-- Quick Stats Cards -->
    <div class="stats-grid mb-6">
      <div class="stat-card">
        <div class="stat-icon-wrap stat-blue">
          <span class="material-symbols-outlined">receipt_long</span>
        </div>
        <div class="stat-info">
          <span class="stat-label">{{ t('total-invoices', 'Total Invoices') }}</span>
          <span class="stat-value">{{ items.length }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap stat-green">
          <span class="material-symbols-outlined">verified</span>
        </div>
        <div class="stat-info">
          <span class="stat-label">{{ t('cleared-b2b', 'Cleared (B2B)') }}</span>
          <span class="stat-value">{{ clearedCount }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap stat-teal">
          <span class="material-symbols-outlined">mark_email_read</span>
        </div>
        <div class="stat-info">
          <span class="stat-label">{{ t('reported-b2c', 'Reported (B2C)') }}</span>
          <span class="stat-value">{{ reportedCount }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap stat-amber">
          <span class="material-symbols-outlined">hourglass_top</span>
        </div>
        <div class="stat-info">
          <span class="stat-label">{{ t('pending-clearance', 'Draft / Pending') }}</span>
          <span class="stat-value">{{ pendingCount }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap stat-red">
          <span class="material-symbols-outlined">gpp_bad</span>
        </div>
        <div class="stat-info">
          <span class="stat-label">{{ t('rejected', 'Rejected / Errors') }}</span>
          <span class="stat-value">{{ rejectedCount }}</span>
        </div>
      </div>
    </div>

    <!-- Filters and Search Bar -->
    <div class="filter-bar mb-4">
      <div class="filter-search">
        <span class="material-symbols-outlined search-icon">search</span>
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          :placeholder="t('search-einvoice-hint', 'Search by invoice #, customer, or UUID...')"
        />
      </div>
      <div class="filter-selects flex items-center gap-2">
        <select v-model="statusFilter" class="filter-select">
          <option value="ALL">{{ t('all-statuses', 'All Statuses') }}</option>
          <option value="CLEARED">{{ t('cleared', 'Cleared') }}</option>
          <option value="REPORTED">{{ t('reported', 'Reported') }}</option>
          <option value="SUBMITTED">{{ t('submitted', 'Submitted') }}</option>
          <option value="DRAFT">{{ t('draft', 'Draft / Pending') }}</option>
          <option value="REJECTED">{{ t('rejected', 'Rejected') }}</option>
        </select>
        <select v-model="subtypeFilter" class="filter-select">
          <option value="ALL">{{ t('all-types', 'All Types') }}</option>
          <option value="0100000">{{ t('standard-b2b', 'Standard Tax (B2B)') }}</option>
          <option value="0200000">{{ t('simplified-b2c', 'Simplified Tax (B2C)') }}</option>
        </select>
        <button class="btn-icon" @click="load" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filteredItems.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">receipt_long</span>
      <p>{{ t('no-einvoice-records', 'No e-invoicing records found') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('invoices-number', 'Invoice #') }}</th>
              <th>{{ t('invoices-partner', 'Partner / Customer') }}</th>
              <th>{{ t('subtype', 'Invoice Type') }}</th>
              <th class="text-center">{{ t('clearance-status', 'Clearance Status') }}</th>
              <th>{{ t('uuid-irn', 'UUID / IRN') }}</th>
              <th class="col-num">{{ t('invoices-total', 'Total Amount') }}</th>
              <th class="text-center">{{ t('qr-code', 'QR Code') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id">
              <td class="cell-mono">
                <a class="inv-link" @click="$router.push(`/finance/${item.invoice_id}`)">
                  {{ item.invoice_number || `#${item.invoice_id}` }}
                </a>
              </td>
              <td>{{ item.partner_name || item.customer_name || `#${item.partner_id || '-'}` }}</td>
              <td>
                <span class="badge" :class="item.subtype === '0200000' ? 'badge-simplified' : 'badge-standard'">
                  {{ item.subtype === '0200000' ? 'Simplified (B2C)' : 'Standard (B2B)' }}
                </span>
              </td>
              <td class="text-center">
                <span class="badge" :class="clearanceBadge(item.clearance_status)">
                  <span class="material-symbols-outlined icon-xs">{{ clearanceIcon(item.clearance_status) }}</span>
                  {{ item.clearance_status || 'Draft' }}
                </span>
              </td>
              <td class="cell-mono text-xs">
                <span v-if="item.invoice_uuid" :title="item.invoice_uuid" class="uuid-text">
                  {{ item.invoice_uuid.slice(0, 8) }}...{{ item.invoice_uuid.slice(-6) }}
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td class="col-num">${{ Number(item.total_amount || 0).toFixed(2) }}</td>
              <td class="text-center">
                <button
                  class="btn-icon"
                  @click="openQRModal(item)"
                  :title="t('view-qr', 'View Tax QR Code')"
                >
                  <span class="material-symbols-outlined">qr_code_2</span>
                </button>
              </td>
              <td class="text-center">
                <div class="action-buttons">
                  <button
                    class="btn-icon"
                    @click="openXMLModal(item)"
                    :title="t('view-xml', 'Inspect UBL 2.1 XML')"
                  >
                    <span class="material-symbols-outlined">code</span>
                  </button>
                  <button
                    class="btn-icon"
                    @click="downloadFiscalPdf(item.invoice_id)"
                    :title="t('download-pdf', 'Download Bilingual Fiscal PDF')"
                  >
                    <span class="material-symbols-outlined">picture_as_pdf</span>
                  </button>
                  <button
                    v-if="item.clearance_status !== 'CLEARED' && item.clearance_status !== 'REPORTED'"
                    class="btn-icon btn-icon-submit"
                    @click="submitClearance(item)"
                    :title="t('submit-clearance', 'Submit for Tax Authority Clearance')"
                    :disabled="submittingId === item.invoice_id"
                  >
                    <span v-if="submittingId === item.invoice_id" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                    <span v-else class="material-symbols-outlined">send</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- QR Code Preview Modal -->
    <div v-if="showQRModal" class="modal-overlay" @click.self="showQRModal = false">
      <div class="modal-content" :dir="dir">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">qr_code_2</span>
            <h3>{{ t('fiscal-qr-preview', 'Bilingual Fiscal QR Code') }}</h3>
          </div>
          <button class="btn-icon" @click="showQRModal = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div class="qr-container">
            <div v-if="qrLoading" class="loading-state">
              <span class="material-symbols-outlined spin">progress_activity</span>
              <p>{{ t('generating-qr', 'Generating TLV QR Code...') }}</p>
            </div>
            <template v-else-if="selectedQR">
              <div class="qr-image-wrapper mb-4">
                <img
                  v-if="selectedQR.qr_code_image || selectedQR.qr_image"
                  :src="selectedQR.qr_code_image || selectedQR.qr_image"
                  alt="Fiscal QR Code"
                  class="qr-img"
                />
                <div v-else class="qr-fallback-box">
                  <span class="material-symbols-outlined icon-xl text-primary">qr_code_2</span>
                  <span class="text-xs text-muted">{{ t('base64-tlv-encoded', 'Base64 TLV Encoded') }}</span>
                </div>
              </div>

              <!-- Decoded Tag Values Table -->
              <div class="tlv-tags-card">
                <h4 class="tlv-title">{{ t('tlv-breakdown', 'Decoded Tag-Length-Value (TLV) Metadata') }}</h4>
                <div class="tlv-row">
                  <span class="tlv-label">Tag 1 (Seller Name):</span>
                  <span class="tlv-value">{{ selectedQR.seller_name || selectedQR.seller || '-' }}</span>
                </div>
                <div class="tlv-row">
                  <span class="tlv-label">Tag 2 (VAT Number):</span>
                  <span class="tlv-value cell-mono">{{ selectedQR.vat_number || selectedQR.vat_registration || '-' }}</span>
                </div>
                <div class="tlv-row">
                  <span class="tlv-label">Tag 3 (Timestamp):</span>
                  <span class="tlv-value cell-mono">{{ selectedQR.timestamp || selectedQR.issue_date || '-' }}</span>
                </div>
                <div class="tlv-row">
                  <span class="tlv-label">Tag 4 (Total Amount):</span>
                  <span class="tlv-value col-num">${{ Number(selectedQR.total_amount || 0).toFixed(2) }}</span>
                </div>
                <div class="tlv-row">
                  <span class="tlv-label">Tag 5 (VAT Total):</span>
                  <span class="tlv-value col-num text-success">${{ Number(selectedQR.vat_total || selectedQR.tax_amount || 0).toFixed(2) }}</span>
                </div>
                <div v-if="selectedQR.invoice_hash" class="tlv-row">
                  <span class="tlv-label">Tag 6 (SHA-256 Hash):</span>
                  <span class="tlv-value cell-mono text-xs">{{ selectedQR.invoice_hash }}</span>
                </div>
              </div>

              <!-- Base64 Raw String -->
              <div class="raw-qr-wrap mt-3">
                <label class="text-xs text-muted font-medium mb-1 block">{{ t('base64-payload', 'Raw Base64 TLV Payload:') }}</label>
                <div class="raw-qr-box">
                  <code>{{ selectedQR.qr_code_base64 || selectedQR.qr_code || '-' }}</code>
                </div>
              </div>
            </template>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showQRModal = false">{{ t('close', 'Close') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- UBL XML Inspector Modal -->
    <div v-if="showXMLModal" class="modal-overlay" @click.self="showXMLModal = false">
      <div class="modal-content modal-lg" :dir="dir">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">code</span>
            <h3>{{ t('ubl-xml-inspector', 'OASIS UBL 2.1 XML Inspector') }}</h3>
          </div>
          <button class="btn-icon" @click="showXMLModal = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="xmlLoading" class="loading-state">
            <span class="material-symbols-outlined spin">progress_activity</span>
            <p>{{ t('loading-xml', 'Generating & formatting UBL 2.1 XML...') }}</p>
          </div>
          <template v-else>
            <div class="xml-metadata-banner mb-3">
              <div class="flex justify-between items-center flex-wrap gap-2">
                <div>
                  <span class="text-xs text-muted block">{{ t('invoice-uuid', 'Invoice UUID') }}:</span>
                  <strong class="cell-mono text-xs text-primary">{{ selectedItem?.invoice_uuid || '-' }}</strong>
                </div>
                <div>
                  <span class="text-xs text-muted block">{{ t('hash-digest', 'SHA-256 Hash Digest') }}:</span>
                  <strong class="cell-mono text-xs">{{ selectedItem?.invoice_hash ? selectedItem.invoice_hash.slice(0, 16) + '...' : '-' }}</strong>
                </div>
                <div class="flex items-center gap-2">
                  <button class="btn-xs btn-outline" @click="copyXML">
                    <span class="material-symbols-outlined icon-xs">content_copy</span>
                    {{ copied ? t('copied', 'Copied!') : t('copy-xml', 'Copy XML') }}
                  </button>
                  <button class="btn-xs btn-primary" @click="downloadXML(selectedItem?.invoice_id)">
                    <span class="material-symbols-outlined icon-xs">download</span>
                    {{ t('download-xml', 'Download .XML') }}
                  </button>
                </div>
              </div>
            </div>
            <pre class="xml-code-block"><code>{{ xmlContent }}</code></pre>
          </template>
          <div class="modal-actions">
            <button class="btn-outline" @click="showXMLModal = false">{{ t('close', 'Close') }}</button>
          </div>
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

const loading = ref(true)
const error = ref('')
const items = ref([])
const searchQuery = ref('')
const statusFilter = ref('ALL')
const subtypeFilter = ref('ALL')
const submittingId = ref(null)

const showQRModal = ref(false)
const qrLoading = ref(false)
const selectedQR = ref(null)

const showXMLModal = ref(false)
const xmlLoading = ref(false)
const xmlContent = ref('')
const selectedItem = ref(null)
const copied = ref(false)

const clearedCount = computed(() => items.value.filter(i => i.clearance_status === 'CLEARED').length)
const reportedCount = computed(() => items.value.filter(i => i.clearance_status === 'REPORTED').length)
const pendingCount = computed(() => items.value.filter(i => !i.clearance_status || i.clearance_status === 'DRAFT' || i.clearance_status === 'SUBMITTED').length)
const rejectedCount = computed(() => items.value.filter(i => i.clearance_status === 'REJECTED').length)

const filteredItems = computed(() => {
  return items.value.filter(item => {
    if (statusFilter.value !== 'ALL') {
      const st = (item.clearance_status || 'DRAFT').toUpperCase()
      if (st !== statusFilter.value) return false
    }
    if (subtypeFilter.value !== 'ALL') {
      if (item.subtype !== subtypeFilter.value) return false
    }
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const invNum = (item.invoice_number || '').toLowerCase()
      const cust = (item.partner_name || item.customer_name || '').toLowerCase()
      const uuid = (item.invoice_uuid || '').toLowerCase()
      if (!invNum.includes(q) && !cust.includes(q) && !uuid.includes(q)) return false
    }
    return true
  })
})

function clearanceBadge(status) {
  const map = {
    CLEARED: 'badge-cleared',
    REPORTED: 'badge-reported',
    SUBMITTED: 'badge-submitted',
    DRAFT: 'badge-draft',
    REJECTED: 'badge-rejected',
  }
  return map[status] || 'badge-draft'
}

function clearanceIcon(status) {
  const map = {
    CLEARED: 'verified',
    REPORTED: 'mark_email_read',
    SUBMITTED: 'hourglass_top',
    DRAFT: 'edit_document',
    REJECTED: 'gpp_bad',
  }
  return map[status] || 'receipt'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [einvoiceRes, invoiceRes, customerRes] = await Promise.all([
      api.get('/T0124I/').catch(() => ({ data: [] })),
      api.get('/T0090I/').catch(() => ({ data: [] })),
      api.get('/T0010I/').catch(() => ({ data: [] })),
    ])

    const invoices = invoiceRes.data || []
    const einvoices = einvoiceRes.data || []
    const customers = customerRes.data || []

    const customerMap = {}
    customers.forEach(c => { customerMap[c.id] = c.name })

    // Merge einvoicing records with invoice data
    const merged = []
    const invoiceMap = {}
    invoices.forEach(inv => { invoiceMap[inv.id] = inv })

    if (einvoices.length > 0) {
      einvoices.forEach(rec => {
        const inv = invoiceMap[rec.invoice_id] || {}
        merged.push({
          ...rec,
          invoice_number: inv.invoice_number || rec.invoice_number,
          partner_id: inv.partner_id,
          partner_name: customerMap[inv.partner_id] || `#${inv.partner_id || '-'}`,
          total_amount: inv.total_amount || rec.total_amount || 0,
        })
      })
    } else {
      // Fallback: list invoices as draft e-invoicing items
      invoices.forEach(inv => {
        merged.push({
          id: inv.id,
          invoice_id: inv.id,
          invoice_number: inv.invoice_number,
          partner_id: inv.partner_id,
          partner_name: customerMap[inv.partner_id] || `#${inv.partner_id || '-'}`,
          subtype: '0100000',
          clearance_status: 'DRAFT',
          total_amount: inv.total_amount || 0,
        })
      })
    }

    items.value = merged
  } catch {
    error.value = t('failed-load-einvoice', 'Failed to load e-invoicing records')
  } finally {
    loading.value = false
  }
}

async function openQRModal(item) {
  selectedQR.value = null
  showQRModal.value = true
  qrLoading.value = true
  try {
    const res = await api.get(`/T0090I/${item.invoice_id}/qr-code`)
    selectedQR.value = res.data
  } catch (err) {
    // Fallback directly to T0124I
    try {
      const res = await api.get(`/T0124I/qr-code/${item.invoice_id}`)
      selectedQR.value = res.data
    } catch {
      toast('Failed to load QR code', 'error')
      showQRModal.value = false
    }
  } finally {
    qrLoading.value = false
  }
}

async function openXMLModal(item) {
  selectedItem.value = item
  xmlContent.value = ''
  showXMLModal.value = true
  xmlLoading.value = true
  copied.value = false
  try {
    const res = await api.post(`/T0124I/generate-xml/${item.invoice_id}`)
    xmlContent.value = res.data?.ubl_xml || ''
    if (res.data?.invoice_uuid) {
      item.invoice_uuid = res.data.invoice_uuid
    }
  } catch {
    toast('Failed to generate UBL XML', 'error')
    showXMLModal.value = false
  } finally {
    xmlLoading.value = false
  }
}

function copyXML() {
  if (!xmlContent.value) return
  navigator.clipboard.writeText(xmlContent.value)
  copied.value = true
  toast('XML copied to clipboard', 'success')
  setTimeout(() => { copied.value = false }, 2000)
}

function downloadXML(invoiceId) {
  if (!invoiceId) return
  window.open(`/api/T0124I/xml/${invoiceId}`, '_blank')
}

function downloadFiscalPdf(invoiceId) {
  if (!invoiceId) return
  window.open(`/api/T0090I/${invoiceId}/fiscal-pdf`, '_blank')
}

async function submitClearance(item) {
  submittingId.value = item.invoice_id
  try {
    const res = await api.post(`/T0090I/${item.invoice_id}/clearance`)
    toast(`Clearance result: ${res.data?.status || 'Submitted'}`, 'success')
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || 'Clearance submission failed', 'error')
  } finally {
    submittingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px; display: flex; align-items: center; gap: 12px; }
.stat-icon-wrap { width: 42px; height: 42px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.stat-blue { background: #eff6ff; color: #2563eb; }
.stat-green { background: #f0fdf4; color: #16a34a; }
.stat-teal { background: #f0fdfa; color: #0d9488; }
.stat-amber { background: #fffbeb; color: #d97706; }
.stat-red { background: #fef2f2; color: #dc2626; }
.stat-info { display: flex; flex-direction: column; }
.stat-label { font-size: 12px; color: #64748b; font-weight: 500; }
.stat-value { font-size: 20px; font-weight: 700; color: #1e293b; }

.filter-bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.filter-search { position: relative; flex: 1; min-width: 240px; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #94a3b8; }
.search-input { width: 100%; padding: 8px 12px 8px 36px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.search-input:focus { border-color: #5d3fd3; }
.filter-select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; background: #fff; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-mono { font-family: monospace; font-size: 12px; }
.inv-link { color: #5d3fd3; cursor: pointer; font-weight: 600; }
.inv-link:hover { text-decoration: underline; }
.uuid-text { color: #64748b; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-cleared { background: #dcfce7; color: #16a34a; border: 1px solid #86efac; }
.badge-reported { background: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd; }
.badge-submitted { background: #fef3c7; color: #d97706; border: 1px solid #fde68a; }
.badge-draft { background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; }
.badge-rejected { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }
.badge-standard { background: #ede9fe; color: #7c3aed; }
.badge-simplified { background: #fef3c7; color: #b45309; }

.action-buttons { display: flex; align-items: center; justify-content: center; gap: 4px; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #64748b; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-submit:hover { color: #16a34a; background: #dcfce7; }
.icon-xs { font-size: 15px !important; }
.icon-xl { font-size: 64px !important; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 560px; max-width: 92vw; max-height: 85vh; overflow-y: auto; }
.modal-lg { width: 780px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 20px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }

.qr-container { text-align: center; }
.qr-image-wrapper { display: flex; justify-content: center; margin-bottom: 16px; }
.qr-img { width: 220px; height: 220px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; background: #fff; }
.qr-fallback-box { width: 220px; height: 220px; border: 2px dashed #cbd5e1; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; background: #f8fafc; }

.tlv-tags-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; text-align: left; }
.tlv-title { font-size: 13px; font-weight: 700; color: #1e293b; margin: 0 0 8px; }
.tlv-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; border-bottom: 1px solid #edf2f7; }
.tlv-row:last-child { border-bottom: none; }
.tlv-label { color: #64748b; font-weight: 500; }
.tlv-value { color: #1e293b; font-weight: 600; word-break: break-all; }

.raw-qr-box { background: #1e293b; color: #38bdf8; padding: 8px 12px; border-radius: 6px; font-size: 11px; max-height: 80px; overflow-y: auto; text-align: left; word-break: break-all; }
.xml-metadata-banner { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; }
.xml-code-block { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 8px; font-size: 12px; max-height: 380px; overflow: auto; text-align: left; }
.btn-xs { padding: 4px 10px; font-size: 11px; border-radius: 6px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }

[dir="rtl"] .search-input { padding: 8px 36px 8px 12px; }
[dir="rtl"] .search-icon { left: auto; right: 10px; }
[dir="rtl"] .data-table th, [dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
</style>

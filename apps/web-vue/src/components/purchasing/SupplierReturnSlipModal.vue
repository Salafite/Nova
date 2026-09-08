<template>
  <div v-if="show" class="slip-modal-overlay" :dir="dir" @click.self="emitClose">
    <div class="slip-modal-dialog">
      <!-- Modal Control Toolbar (Hidden during print) -->
      <div class="slip-toolbar no-print">
        <div class="toolbar-left">
          <span class="material-symbols-outlined toolbar-icon">receipt_long</span>
          <div>
            <h3 class="toolbar-title">{{ t('return-slip-title', 'Supplier Return Slip & Debit Claim') }}</h3>
            <span class="toolbar-subtitle">{{ slipData?.return_number }} — {{ slipData?.supplier_name }}</span>
          </div>
        </div>

        <div class="toolbar-actions">
          <label class="toggle-photos-label" :title="t('toggle-photos-print-desc', 'Include or omit inspection photo evidence in printed document')">
            <input type="checkbox" v-model="includePhotosInPrint" />
            <span>{{ t('include-photos-in-print', 'Include Photos in Print') }}</span>
          </label>

          <button type="button" class="btn-print" @click="handlePrint">
            <span class="material-symbols-outlined">print</span>
            <span>{{ t('print-return-slip', 'Print Slip (A4/Letter)') }}</span>
          </button>

          <button type="button" class="btn-close-modal" @click="emitClose" :title="t('close', 'Close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="slip-loading no-print">
        <span class="material-symbols-outlined spinner">progress_activity</span>
        <span>{{ t('loading-return-slip', 'Generating printable return slip data...') }}</span>
      </div>

      <!-- Printable Return Slip Document Viewport -->
      <div v-else-if="slipData" class="slip-viewport">
        <div class="printable-slip-wrapper" ref="slipContentRef">
          <!-- Document Header -->
          <div class="doc-header">
            <div class="company-brand">
              <div class="brand-logo-wrap">
                <span class="material-symbols-outlined brand-icon">inventory_2</span>
              </div>
              <div>
                <h1 class="company-name">{{ slipData.company_name || 'Nova Logistics & Wholesale Distribution' }}</h1>
                <p class="company-address">{{ slipData.company_address || '100 Logistics Blvd, Dock Area B, Suite 400' }}</p>
                <p class="company-contact">Tel: {{ slipData.company_phone || '+1 (800) 555-NOVA' }} | Email: returns@novadistribution.com</p>
              </div>
            </div>

            <div class="doc-title-block">
              <div class="doc-title-badge">{{ t('official-slip', 'OFFICIAL RETURN AUTHORIZATION') }}</div>
              <h2 class="doc-title">{{ t('supplier-return-slip-heading', 'VENDOR RETURN MERCHANDISE SLIP') }}</h2>
              <div class="doc-subtitle">{{ t('supplier-debit-claim-sub', 'Itemized Rejection & Supplier Debit Memo Notice') }}</div>
              <div class="rma-number-tag font-mono">{{ slipData.return_number }}</div>
            </div>
          </div>

          <div class="doc-divider"></div>

          <!-- Metadata Summary Strip -->
          <div class="meta-strip">
            <div class="meta-item">
              <span class="meta-label">{{ t('return-date', 'Return Date') }}:</span>
              <span class="meta-value font-mono font-bold">{{ slipData.return_date }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('rma-status', 'RMA Status') }}:</span>
              <span class="status-pill font-bold" :class="statusPillClass(slipData.status)">{{ slipData.status }}</span>
            </div>
            <div class="meta-item" v-if="slipData.approved_at">
              <span class="meta-label">{{ t('approved-by', 'Approved By') }}:</span>
              <span class="meta-value">{{ slipData.approved_by_name || 'Warehouse Quality Supervisor' }} ({{ formatDate(slipData.approved_at) }})</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('currency', 'Currency') }}:</span>
              <span class="meta-value font-mono">{{ slipData.currency || 'USD' }} ($)</span>
            </div>
          </div>

          <!-- Supplier Details & Reference Documents Grid -->
          <div class="info-columns-grid">
            <!-- Supplier Details Box -->
            <div class="info-panel">
              <div class="panel-header">
                <span class="material-symbols-outlined panel-icon">store</span>
                <span class="panel-title">{{ t('supplier-vendor-details', 'Supplier / Vendor Details') }}</span>
              </div>
              <div class="panel-content">
                <div class="info-row">
                  <span class="info-lbl">{{ t('vendor-name', 'Vendor Name') }}:</span>
                  <span class="info-val font-bold">{{ slipData.supplier_name }}</span>
                </div>
                <div class="info-row" v-if="slipData.supplier_code">
                  <span class="info-lbl">{{ t('vendor-code', 'Vendor Code') }}:</span>
                  <span class="info-val font-mono">{{ slipData.supplier_code }}</span>
                </div>
                <div class="info-row" v-if="slipData.supplier_contact">
                  <span class="info-lbl">{{ t('contact-person', 'Contact Person') }}:</span>
                  <span class="info-val">{{ slipData.supplier_contact }}</span>
                </div>
                <div class="info-row" v-if="slipData.supplier_phone">
                  <span class="info-lbl">{{ t('phone', 'Phone') }}:</span>
                  <span class="info-val font-mono">{{ slipData.supplier_phone }}</span>
                </div>
                <div class="info-row" v-if="slipData.supplier_email">
                  <span class="info-lbl">{{ t('email', 'Email') }}:</span>
                  <span class="info-val">{{ slipData.supplier_email }}</span>
                </div>
                <div class="info-row" v-if="slipData.supplier_address">
                  <span class="info-lbl">{{ t('address', 'Address') }}:</span>
                  <span class="info-val">{{ slipData.supplier_address }}</span>
                </div>
              </div>
            </div>

            <!-- Transaction & Document References Box -->
            <div class="info-panel">
              <div class="panel-header">
                <span class="material-symbols-outlined panel-icon">receipt</span>
                <span class="panel-title">{{ t('cross-references-debit', 'Cross-References & Debit Recovery') }}</span>
              </div>
              <div class="panel-content">
                <div class="info-row">
                  <span class="info-lbl">{{ t('purchase-order', 'Purchase Order (PO)') }}:</span>
                  <span class="info-val font-mono font-bold">{{ slipData.po_number || (slipData.purchase_order_id ? `PO #${slipData.purchase_order_id}` : 'Standalone Return') }}</span>
                </div>
                <div class="info-row">
                  <span class="info-lbl">{{ t('goods-receipt-grn', 'Goods Receipt (GRN)') }}:</span>
                  <span class="info-val font-mono font-bold">{{ slipData.grn_number || (slipData.goods_receipt_id ? `GRN #${slipData.goods_receipt_id}` : 'N/A') }}</span>
                </div>
                <div class="info-row debit-memo-highlight">
                  <span class="info-lbl text-purple font-bold">{{ t('linked-debit-memo', 'Posted Debit Memo') }}:</span>
                  <span class="info-val font-mono font-bold text-purple">
                    {{ slipData.debit_memo_number || (slipData.debit_memo_id ? `DM #${slipData.debit_memo_id}` : t('auto-posted-on-approval', 'Pending Approval')) }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-lbl">{{ t('recovery-amount', 'Debit Claim Total') }}:</span>
                  <span class="info-val font-mono font-bold text-lg text-primary">${{ (slipData.total_amount || 0).toFixed(2) }}</span>
                </div>
                <div class="info-row">
                  <span class="info-lbl">{{ t('disposition', 'Disposition') }}:</span>
                  <span class="info-val font-bold">{{ defaultDisposition }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Reason & Inspection Callout -->
          <div class="rejection-callout mb-4" v-if="slipData.reason || slipData.notes">
            <div class="rejection-callout-title">
              <span class="material-symbols-outlined icon-warning">warning</span>
              <strong>{{ t('rejection-reason-notes', 'Rejection Reason & Dock Inspection Notes') }}:</strong>
            </div>
            <p v-if="slipData.reason" class="rejection-text"><strong>{{ t('primary-reason', 'Primary Reason') }}:</strong> {{ slipData.reason }}</p>
            <p v-if="slipData.notes" class="notes-text"><strong>{{ t('supervisor-notes', 'Inspector Notes') }}:</strong> {{ slipData.notes }}</p>
          </div>

          <!-- Itemized Table of Returned Batches & Products -->
          <div class="table-section mb-4">
            <h3 class="table-section-heading">
              <span class="material-symbols-outlined section-hdr-icon">format_list_numbered</span>
              {{ t('itemized-batch-breakdown', 'Itemized Return Lines, Lot Numbers & Rejection Reasons') }}
            </h3>

            <table class="slip-items-table">
              <thead>
                <tr>
                  <th class="th-num">#</th>
                  <th class="th-desc">{{ t('product-desc', 'Product Description / SKU') }}</th>
                  <th class="th-batch">{{ t('batch-lot-exp', 'Batch / Lot # & Exp') }}</th>
                  <th class="th-qty col-num">{{ t('qty', 'Qty') }}</th>
                  <th class="th-uom">{{ t('uom', 'UOM') }}</th>
                  <th class="th-price col-num">{{ t('unit-cost', 'Unit Price ($)') }}</th>
                  <th class="th-total col-num">{{ t('claim-amount', 'Claim Amount ($)') }}</th>
                  <th class="th-reason">{{ t('return-reason', 'Return Reason') }}</th>
                  <th class="th-status">{{ t('quarantine-status', 'Quarantine') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in slipData.lines" :key="line.id || idx" class="slip-item-row">
                  <td class="cell-mono text-center">{{ line.line_number || (idx + 1) }}</td>
                  <td>
                    <div class="product-title font-bold">{{ line.product_name }}</div>
                    <div v-if="line.product_id" class="product-sku font-mono text-xs text-muted">ID: #{{ line.product_id }}</div>
                  </td>
                  <td>
                    <div v-if="line.batch_number" class="batch-box font-mono">
                      <span class="batch-num font-bold">{{ line.batch_number }}</span>
                      <span v-if="line.expiry_date" class="batch-exp">Exp: {{ line.expiry_date }}</span>
                    </div>
                    <span v-else class="text-muted text-xs">-</span>
                  </td>
                  <td class="col-num font-mono font-bold">{{ line.qty }}</td>
                  <td>{{ line.uom || 'Units' }}</td>
                  <td class="col-num font-mono">${{ (line.unit_price || 0).toFixed(2) }}</td>
                  <td class="col-num font-mono font-bold">${{ (line.line_total || (line.qty * line.unit_price) || 0).toFixed(2) }}</td>
                  <td>
                    <span class="reason-tag" :class="reasonTagClass(line.reason_code)">
                      {{ line.reason_label || formatReasonCode(line.reason_code) }}
                    </span>
                  </td>
                  <td>
                    <span class="quarantine-tag" :class="quarantineTagClass(line.quarantine_status)">
                      {{ line.quarantine_status || 'Quarantine' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!slipData.lines?.length">
                  <td colspan="9" class="text-center text-muted py-3">
                    {{ t('no-return-lines', 'No itemized return lines found.') }}
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="slip-table-footer">
                  <td colspan="3" class="text-right font-bold footer-label">
                    {{ t('total-quantities-claim', 'TOTAL RETURN UNITS & DEBIT CLAIM:') }}
                  </td>
                  <td class="col-num font-mono font-bold footer-qty">
                    {{ totalItemsQty }}
                  </td>
                  <td colspan="2"></td>
                  <td class="col-num font-mono font-bold footer-total text-primary">
                    ${{ (slipData.total_amount || calculatedTotalAmount).toFixed(2) }}
                  </td>
                  <td colspan="2" class="footer-note">
                    <span class="badge-posted-debit">{{ t('debit-memo-posted-note', 'Supplier AP Credit Claimed') }}</span>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          <!-- Financial Accounting Deduction Statement -->
          <div class="accounting-notice-card mb-4">
            <div class="accounting-notice-content">
              <span class="material-symbols-outlined acct-icon">account_balance_wallet</span>
              <div>
                <strong>{{ t('accounting-credit-statement', 'Automated Supplier Debit Memo Accounting Notice') }}:</strong>
                <p class="acct-text">
                  {{ t('acct-debit-desc', 'A debit memo in the amount of') }}
                  <strong class="font-mono text-purple">${{ (slipData.total_amount || calculatedTotalAmount).toFixed(2) }}</strong>
                  {{ t('acct-debit-desc-2', 'has been posted against supplier accounts payable and will be deducted on the next payment disbursement run.') }}
                </p>
              </div>
            </div>
          </div>

          <!-- Inspection Photo Evidence Gallery Section -->
          <div
            v-if="(slipData.attachments || []).length"
            class="photos-section mb-6"
            :class="{ 'hide-in-print': !includePhotosInPrint }"
          >
            <div class="section-hdr-wrap">
              <h3 class="table-section-heading">
                <span class="material-symbols-outlined section-hdr-icon">photo_library</span>
                {{ t('inspection-photos-evidence', 'Inspection Photo Evidence & Proof of Damage') }}
                <span class="badge-count">({{ slipData.attachments.length }} {{ t('photos', 'photos') }})</span>
              </h3>
              <span class="text-xs text-muted no-print">{{ t('click-photo-enlarge', 'Click any photo to view full resolution') }}</span>
            </div>

            <div class="photos-gallery-grid">
              <div
                v-for="(photo, pIdx) in slipData.attachments"
                :key="photo.id || pIdx"
                class="photo-card"
                @click="openLightbox(pIdx)"
                :title="t('click-to-enlarge', 'Click to enlarge full resolution photo')"
              >
                <div class="photo-img-wrap">
                  <img
                    v-if="photo.url || photo.thumbnail_url || photo.data_base64"
                    :src="photo.url || photo.thumbnail_url || (photo.data_base64 ? `data:${photo.content_type || 'image/jpeg'};base64,${photo.data_base64}` : '')"
                    :alt="photo.filename || 'Inspection Evidence'"
                    class="photo-img"
                  />
                  <div v-else class="photo-placeholder">
                    <span class="material-symbols-outlined">image</span>
                  </div>
                  <div class="photo-overlay-icon no-print">
                    <span class="material-symbols-outlined">zoom_in</span>
                  </div>
                </div>
                <div class="photo-caption-bar">
                  <span class="photo-caption-title font-bold">{{ photo.filename || ('Evidence Photo #' + (pIdx + 1)) }}</span>
                  <span v-if="photo.description" class="photo-caption-desc">{{ photo.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Driver & Warehouse Acknowledgment Sign-off Block -->
          <div class="signoff-section">
            <div class="legal-ack-text mb-4">
              <span class="material-symbols-outlined legal-icon">verified_user</span>
              <span>
                {{ slipData.acknowledgment_text || 'Received the returned merchandise listed above in the condition stated. Supplier acknowledgment verifies debit memo claims and authorizes inventory quarantine write-down.' }}
              </span>
            </div>

            <div class="signoff-grid">
              <!-- Warehouse Inspector Sign-off Box -->
              <div class="signoff-box">
                <div class="signoff-box-title">{{ t('warehouse-inspection-signoff', '1. Warehouse Quality / Dock Inspector') }}</div>
                <div class="signoff-fields">
                  <div class="sig-line-wrap">
                    <div class="sig-line"></div>
                    <span class="sig-label">{{ t('authorized-signature', 'Authorized Signature') }}</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('inspector-name', 'Inspector Name') }}:</span>
                    <span class="sig-val">{{ slipData.approved_by_name || 'Warehouse Quality Supervisor' }}</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('sign-date', 'Date & Time') }}:</span>
                    <span class="sig-val font-mono">{{ slipData.approved_at ? formatDateTime(slipData.approved_at) : today() }}</span>
                  </div>
                </div>
              </div>

              <!-- Carrier / Driver Sign-off Box -->
              <div class="signoff-box">
                <div class="signoff-box-title">{{ t('carrier-driver-signoff', '2. Driver / Carrier Representative Acknowledgment') }}</div>
                <div class="signoff-fields">
                  <div class="sig-line-wrap">
                    <div class="sig-line"></div>
                    <span class="sig-label">{{ t('driver-signature', 'Driver Signature (I acknowledge receipt of returned items)') }}</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('carrier-name', 'Carrier / Transport Co') }}:</span>
                    <span class="sig-val fill-line">__________________________________</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('driver-printed-name', 'Driver Printed Name') }}:</span>
                    <span class="sig-val fill-line">__________________________________</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('truck-trailer-bol', 'Truck / Trailer / BOL #') }}:</span>
                    <span class="sig-val fill-line">__________________________________</span>
                  </div>
                  <div class="sig-field-row">
                    <span class="sig-lbl">{{ t('driver-sign-date', 'Date & Time') }}:</span>
                    <span class="sig-val fill-line">__________________________________</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer Document Control -->
            <div class="doc-footer-meta">
              <span>Nova ERP Document Control System • RMA Ref: {{ slipData.return_number }} • Printed on {{ currentPrintDateTime }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Full Resolution Photo Lightbox Modal -->
    <PhotoLightboxModal
      :show="showLightbox"
      :photos="slipData?.attachments || []"
      :initial-index="lightboxIndex"
      @close="showLightbox = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import PhotoLightboxModal from '../PhotoLightboxModal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  returnId: {
    type: [Number, String],
    default: null,
  },
  initialData: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'approved'])

const { t, dir } = useI18n()
const { show: toast } = useToast()

const loading = ref(false)
const slipData = ref(null)
const includePhotosInPrint = ref(true)
const slipContentRef = ref(null)

// Lightbox state
const showLightbox = ref(false)
const lightboxIndex = ref(0)

watch(
  () => props.show,
  (val) => {
    if (val && props.returnId) {
      loadSlipData()
    } else if (!val) {
      slipData.value = null
      showLightbox.value = false
    }
  },
  { immediate: true }
)

watch(
  () => props.returnId,
  (newId) => {
    if (props.show && newId) {
      loadSlipData()
    }
  }
)

async function loadSlipData() {
  if (!props.returnId) return
  loading.value = true
  try {
    const res = await api.get(`/T0081I/${props.returnId}/slip-data`)
    slipData.value = res.data
  } catch {
    // Fallback: try loading details or using initialData
    if (props.initialData) {
      slipData.value = formatInitialDataAsSlip(props.initialData)
    } else {
      try {
        const detRes = await api.get(`/T0081I/${props.returnId}/details`)
        slipData.value = formatInitialDataAsSlip(detRes.data)
      } catch {
        toast(t('failed-load-slip', 'Failed to load return slip data'), 'error')
      }
    }
  } finally {
    loading.value = false
  }
}

function formatInitialDataAsSlip(data) {
  if (!data) return null
  return {
    return_id: data.id,
    return_number: data.return_number || `RMA-${data.id}`,
    return_date: data.return_date || today(),
    status: data.status || 'Draft',
    company_name: 'Nova Logistics & Wholesale Distribution',
    company_address: '100 Logistics Blvd, Dock Area B, Suite 400',
    company_phone: '+1 (800) 555-NOVA',
    supplier_id: data.supplier_id,
    supplier_name: data.supplier_name || `Supplier #${data.supplier_id}`,
    supplier_code: data.supplier_code || `SUP-${data.supplier_id}`,
    supplier_contact: data.supplier_contact || '',
    supplier_phone: data.supplier_phone || '',
    supplier_email: data.supplier_email || '',
    supplier_address: data.supplier_address || '',
    purchase_order_id: data.purchase_order_id,
    po_number: data.po_number || (data.purchase_order_id ? `PO #${data.purchase_order_id}` : null),
    goods_receipt_id: data.goods_receipt_id,
    grn_number: data.grn_number || (data.goods_receipt_id ? `GRN #${data.goods_receipt_id}` : null),
    debit_memo_id: data.debit_memo_id,
    debit_memo_number: data.debit_memo_number || (data.debit_memo_id ? `DM #${data.debit_memo_id}` : null),
    total_amount: Number(data.total_amount) || 0,
    currency: 'USD',
    reason: data.reason,
    notes: data.notes,
    approved_at: data.approved_at,
    approved_by_name: data.approved_by_name,
    lines: (data.lines || []).map((l, idx) => ({
      id: l.id,
      line_number: l.line_number || idx + 1,
      product_id: l.product_id,
      product_name: l.product_name || `Product #${l.product_id}`,
      qty: Number(l.qty) || 1,
      uom: l.uom || 'Units',
      unit_price: Number(l.unit_price) || 0,
      line_total: Number(l.line_total) || ((Number(l.qty) || 1) * (Number(l.unit_price) || 0)),
      batch_number: l.batch_number,
      expiry_date: l.expiry_date ? l.expiry_date.slice(0, 10) : null,
      reason_code: l.reason_code,
      reason_label: formatReasonCode(l.reason_code),
      quarantine_status: l.quarantine_status || 'Quarantine',
      disposition: l.disposition || 'Return to Vendor',
      photos: l.photos || [],
    })),
    attachments: data.attachments || [],
    acknowledgment_text:
      'Received the returned merchandise listed above in the condition stated. Supplier acknowledgment verifies debit memo claims and authorizes inventory quarantine write-down.',
  }
}

const totalItemsQty = computed(() => {
  if (!slipData.value?.lines?.length) return 0
  return slipData.value.lines.reduce((sum, line) => sum + (Number(line.qty) || 0), 0)
})

const calculatedTotalAmount = computed(() => {
  if (!slipData.value?.lines?.length) return 0
  return slipData.value.lines.reduce((sum, line) => {
    const qty = Number(line.qty) || 0
    const price = Number(line.unit_price) || 0
    return sum + (Number(line.line_total) || (qty * price))
  }, 0)
})

const defaultDisposition = computed(() => {
  if (!slipData.value?.lines?.length) return 'Return to Vendor'
  const firstDisp = slipData.value.lines[0].disposition
  return firstDisp || 'Return to Vendor'
})

const currentPrintDateTime = computed(() => {
  return new Date().toLocaleString()
})

function statusPillClass(status) {
  const map = {
    Draft: 'status-draft',
    Approved: 'status-approved',
    Returned: 'status-returned',
    Received: 'status-returned',
    Cancelled: 'status-cancelled',
  }
  return map[status] || 'status-draft'
}

function reasonTagClass(code) {
  const map = {
    damaged: 'tag-danger',
    expired: 'tag-warning',
    rejected: 'tag-danger',
    wrong_item: 'tag-info',
    qc_failed: 'tag-danger',
    defective: 'tag-warning',
    over_delivery: 'tag-neutral',
    other: 'tag-neutral',
  }
  return map[code] || 'tag-neutral'
}

function quarantineTagClass(status) {
  if (status === 'Quarantine') return 'tag-quarantine'
  if (status === 'Scrapped') return 'tag-danger'
  return 'tag-released'
}

function formatReasonCode(code) {
  if (!code) return ''
  return code.replace(/_/g, ' ').toUpperCase()
}

function today() {
  return new Date().toISOString().split('T')[0]
}

function formatDate(val) {
  if (!val) return ''
  try {
    return new Date(val).toLocaleDateString()
  } catch {
    return String(val)
  }
}

function formatDateTime(val) {
  if (!val) return ''
  try {
    return new Date(val).toLocaleString()
  } catch {
    return String(val)
  }
}

function openLightbox(index) {
  lightboxIndex.value = index
  showLightbox.value = true
}

function handlePrint() {
  window.print()
}

function emitClose() {
  emit('close')
}
</script>

<style scoped>
/* Modal Structure */
.slip-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(3px);
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow-y: auto;
}

.slip-modal-dialog {
  background: #f8fafc;
  border-radius: 12px;
  width: 1050px;
  max-width: 98vw;
  max-height: 94vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-default, #e2e8f0);
  overflow: hidden;
}

/* Modal Toolbar */
.slip-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #1e293b;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-icon {
  font-size: 28px;
  color: #38bdf8;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: #f8fafc;
}

.toolbar-subtitle {
  font-size: 12px;
  color: #94a3b8;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-photos-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #cbd5e1;
  cursor: pointer;
  user-select: none;
  background: rgba(255, 255, 255, 0.08);
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.toggle-photos-label input[type="checkbox"] {
  accent-color: #38bdf8;
}

.btn-print {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #0284c7;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-print:hover {
  background: #0369a1;
}

.btn-close-modal {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-close-modal:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* Loading state */
.slip-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: #64748b;
  font-size: 14px;
}

.spinner {
  animation: spin 1s linear infinite;
  font-size: 24px;
  color: #0284c7;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Viewport & Document Container */
.slip-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #64748b;
  display: flex;
  justify-content: center;
}

.printable-slip-wrapper {
  background: #ffffff;
  color: #0f172a;
  width: 100%;
  max-width: 900px;
  padding: 36px 40px;
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  font-size: 12px;
  line-height: 1.45;
  box-sizing: border-box;
}

/* Document Header */
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.company-brand {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
}

.brand-logo-wrap {
  width: 48px;
  height: 48px;
  background: #0f172a;
  color: #fff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-icon {
  font-size: 28px;
}

.company-name {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 2px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.company-address,
.company-contact {
  font-size: 11px;
  color: #475569;
  margin: 1px 0;
}

.doc-title-block {
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.doc-title-badge {
  font-size: 9px;
  font-weight: 800;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #475569;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.8px;
  margin-bottom: 4px;
}

.doc-title {
  font-size: 18px;
  font-weight: 900;
  color: #0f172a;
  margin: 0 0 2px 0;
  letter-spacing: 0.3px;
}

.doc-subtitle {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

.rma-number-tag {
  font-size: 15px;
  font-weight: 800;
  color: #0284c7;
  background: #e0f2fe;
  padding: 3px 10px;
  border-radius: 6px;
  margin-top: 6px;
  display: inline-block;
  border: 1px solid #bae6fd;
}

.doc-divider {
  height: 2px;
  background: #0f172a;
  margin: 16px 0;
}

/* Meta Strip */
.meta-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 14px;
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

.meta-value {
  font-size: 12px;
  color: #0f172a;
}

.status-pill {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.status-draft { background: #fef3c7; color: #b45309; }
.status-approved { background: #e0f2fe; color: #0369a1; }
.status-returned { background: #dcfce7; color: #15803d; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }

/* Info Panels */
.info-columns-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.info-panel {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.panel-header {
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-icon {
  font-size: 16px;
  color: #0f172a;
}

.panel-title {
  font-size: 11px;
  font-weight: 800;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.panel-content {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
}

.info-lbl {
  color: #64748b;
}

.info-val {
  color: #0f172a;
  text-align: right;
}

.debit-memo-highlight {
  background: #faf5ff;
  padding: 3px 6px;
  border-radius: 4px;
  border: 1px dashed #d8b4fe;
  margin: 2px 0;
}

.text-purple {
  color: #7e22ce !important;
}

.text-primary {
  color: #0284c7 !important;
}

.text-lg {
  font-size: 14px !important;
}

/* Rejection Callout */
.rejection-callout {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 4px solid #f59e0b;
  border-radius: 4px;
  padding: 10px 14px;
  font-size: 11.5px;
}

.rejection-callout-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #92400e;
  font-size: 12px;
  margin-bottom: 4px;
}

.icon-warning {
  font-size: 16px;
  color: #d97706;
}

.rejection-text,
.notes-text {
  margin: 2px 0;
  color: #78350f;
}

/* Itemized Table */
.table-section {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
}

.table-section-heading {
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  padding: 8px 12px;
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.section-hdr-icon {
  font-size: 18px;
  color: #0284c7;
}

.slip-items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.slip-items-table th {
  background: #f8fafc;
  padding: 7px 8px;
  border-bottom: 1px solid #cbd5e1;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.3px;
  text-align: left;
}

.slip-items-table td {
  padding: 7px 8px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}

.slip-item-row:nth-child(even) {
  background: #fbfcfe;
}

.th-num { width: 32px; text-align: center; }
.th-desc { width: 28%; }
.th-batch { width: 18%; }
.th-qty { width: 7%; }
.th-uom { width: 6%; }
.th-price { width: 11%; }
.th-total { width: 11%; }
.th-reason { width: 12%; }
.th-status { width: 8%; }

.col-num { text-align: right; }
.cell-mono { font-family: monospace; }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-xs { font-size: 10px; }
.text-muted { color: #64748b; }

.batch-box {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.batch-num {
  color: #0f172a;
}

.batch-exp {
  font-size: 9.5px;
  color: #b45309;
}

.reason-tag {
  display: inline-block;
  font-size: 9.5px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.tag-danger { background: #fee2e2; color: #b91c1c; }
.tag-warning { background: #fef3c7; color: #b45309; }
.tag-info { background: #e0f2fe; color: #0369a1; }
.tag-neutral { background: #f1f5f9; color: #475569; }

.quarantine-tag {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  text-transform: uppercase;
}

.tag-quarantine { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
.tag-released { background: #dcfce7; color: #15803d; }

.slip-table-footer td {
  background: #f1f5f9;
  border-top: 2px solid #0f172a;
  border-bottom: none;
  padding: 10px 8px;
}

.footer-label {
  font-size: 11px;
  letter-spacing: 0.4px;
  color: #0f172a;
}

.footer-qty {
  font-size: 13px;
}

.footer-total {
  font-size: 14px;
}

.badge-posted-debit {
  font-size: 9px;
  font-weight: 700;
  background: #ede9fe;
  color: #6d28d9;
  padding: 3px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

/* Accounting Statement Card */
.accounting-notice-card {
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
  border-radius: 6px;
  padding: 10px 14px;
}

.accounting-notice-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.acct-icon {
  font-size: 20px;
  color: #7c3aed;
  flex-shrink: 0;
  margin-top: 1px;
}

.acct-text {
  margin: 3px 0 0 0;
  font-size: 11.5px;
  color: #4c1d95;
}

/* Inspection Photos */
.photos-section {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.section-hdr-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  padding: 6px 12px;
}

.badge-count {
  font-size: 10px;
  color: #64748b;
  font-weight: 600;
  margin-left: 4px;
}

.photos-gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
  padding: 12px;
}

.photo-card {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.photo-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  border-color: #0284c7;
}

.photo-img-wrap {
  position: relative;
  height: 95px;
  background: #f8fafc;
}

.photo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.photo-placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.photo-overlay-icon {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.photo-card:hover .photo-overlay-icon {
  opacity: 1;
}

.photo-caption-bar {
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #ffffff;
}

.photo-caption-title {
  font-size: 10px;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.photo-caption-desc {
  font-size: 9px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Sign-off Block */
.signoff-section {
  page-break-inside: avoid;
  break-inside: avoid;
  margin-top: 16px;
}

.legal-ack-text {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 12px;
  line-height: 1.4;
}

.legal-icon {
  font-size: 16px;
  color: #0284c7;
  flex-shrink: 0;
  margin-top: 1px;
}

.signoff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 12px;
}

.signoff-box {
  border: 1px solid #94a3b8;
  border-radius: 6px;
  padding: 12px;
  background: #ffffff;
}

.signoff-box-title {
  font-size: 11px;
  font-weight: 800;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 1px solid #cbd5e1;
  padding-bottom: 6px;
  margin-bottom: 10px;
}

.signoff-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sig-line-wrap {
  margin-top: 14px;
  margin-bottom: 8px;
}

.sig-line {
  height: 1px;
  background: #0f172a;
  margin-bottom: 4px;
}

.sig-label {
  font-size: 9.5px;
  color: #64748b;
  text-transform: uppercase;
}

.sig-field-row {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
}

.sig-lbl {
  color: #64748b;
}

.sig-val {
  color: #0f172a;
  font-weight: 600;
}

.fill-line {
  color: #94a3b8;
  letter-spacing: -1px;
}

.doc-footer-meta {
  text-align: center;
  font-size: 9px;
  color: #94a3b8;
  margin-top: 12px;
}

.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.py-3 { padding-top: 12px; padding-bottom: 12px; }

/* RTL Adjustments */
[dir="rtl"] .doc-header { flex-direction: row-reverse; }
[dir="rtl"] .doc-title-block { text-align: left; align-items: flex-start; }
[dir="rtl"] .slip-items-table th { text-align: right; }
[dir="rtl"] .slip-items-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .info-val { text-align: left; }
[dir="rtl"] .rejection-callout { border-left: 1px solid #fde68a; border-right: 4px solid #f59e0b; }

/* Print Stylesheet */
@media print {
  @page {
    size: A4 portrait;
    margin: 10mm 12mm 10mm 12mm;
  }

  body {
    background: #ffffff !important;
    color: #000000 !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  /* Hide everything except the printable slip */
  body * {
    visibility: hidden;
  }

  .slip-modal-overlay,
  .slip-modal-dialog,
  .slip-viewport,
  .printable-slip-wrapper,
  .printable-slip-wrapper * {
    visibility: visible;
  }

  .slip-modal-overlay {
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    width: 100% !important;
    height: auto !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    backdrop-filter: none !important;
    z-index: 99999 !important;
    overflow: visible !important;
    display: block !important;
  }

  .slip-modal-dialog {
    width: 100% !important;
    max-width: 100% !important;
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
  }

  .slip-viewport {
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
  }

  .printable-slip-wrapper {
    box-shadow: none !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
  }

  .no-print,
  .slip-toolbar {
    display: none !important;
  }

  .hide-in-print {
    display: none !important;
  }

  .doc-header {
    margin-top: 0 !important;
  }

  .slip-items-table th {
    background: #f1f5f9 !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .table-section,
  .info-panel,
  .signoff-box,
  .rejection-callout,
  .accounting-notice-card {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .slip-item-row {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .signoff-section {
    page-break-inside: avoid;
    break-inside: avoid;
    margin-top: 14px;
  }

  .photos-gallery-grid {
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 8px !important;
  }

  .photo-img-wrap {
    height: 80px !important;
  }
}
</style>

<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('gr-title', 'Goods Receipt') }}</h1>
        <p class="page-subtitle">{{ t('gr-sub', 'Record and manage goods received with lot & expiration tracking') }}</p>
      </div>
      <div class="flex gap-2 items-center">
        <button
          class="btn-secondary flex items-center gap-1"
          @click="showCameraScanner = true"
          :title="t('open-camera-scanner', 'Open Camera Barcode Scanner')"
        >
          <span class="material-symbols-outlined icon-xs">photo_camera</span>
          {{ t('camera-scan', 'Camera Scan') }}
        </button>
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-gr', 'New Receipt') }}
        </button>
      </div>
    </div>

    <!-- Quick Barcode Scanner Card for Inbound Receiving Verification -->
    <div class="scanner-card mb-6" :class="{ 'flash-success': flashState === 'success', 'flash-error': flashState === 'error' }">
      <div class="flex items-center gap-3">
        <span class="material-symbols-outlined scanner-icon">qr_code_scanner</span>
        <div class="flex-1">
          <div class="flex justify-between items-center mb-1">
            <label class="scanner-label">{{ t('quick-scan-gr', 'USB / Bluetooth & Camera Inbound Goods Scanner') }}</label>
            <div class="flex items-center gap-2 text-xs">
              <span class="badge badge-scanner-active" :title="t('scanner-listener-active', 'Hardware scanner listener active')">
                <span class="status-pulse"></span>
                {{ t('scanner-ready', 'Scanner Active') }}
              </span>
              <button
                type="button"
                class="btn-icon btn-xs"
                @click="soundEnabled = !soundEnabled"
                :title="soundEnabled ? t('mute-audio', 'Mute scan audio') : t('unmute-audio', 'Unmute scan audio')"
              >
                <span class="material-symbols-outlined icon-xs">{{ soundEnabled ? 'volume_up' : 'volume_off' }}</span>
              </button>
            </div>
          </div>
          <div class="flex gap-2">
            <input
              type="text"
              v-model="globalScan"
              class="form-input scanner-input flex-1"
              :placeholder="t('scan-gr-placeholder', 'Scan product barcode, EAN-13, UPC, Code 128, or GS1-128 lot label...')"
              @keydown.enter.prevent="onManualGlobalScan"
            />
            <button type="button" class="btn-primary btn-sm px-4" @click="onManualGlobalScan">
              <span class="material-symbols-outlined icon-xs">search</span> {{ t('verify-scan', 'Scan / Verify') }}
            </button>
            <button type="button" class="btn-outline btn-sm px-3" @click="showCameraScanner = true" :title="t('camera-scan-hint', 'Use device camera to scan barcode')">
              <span class="material-symbols-outlined icon-xs">photo_camera</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats summary -->
    <div v-if="!loading && !error && items.length" class="stats-row mb-6">
      <div class="stat-card">
        <div class="stat-num">{{ items.length }}</div>
        <div class="stat-lbl">{{ t('total-receipts', 'Total Receipts') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num text-green">{{ completedCount }}</div>
        <div class="stat-lbl">{{ t('completed', 'Completed') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num text-purple">{{ trackedBatchesCount }}</div>
        <div class="stat-lbl">{{ t('tracked-batches', 'Tracked Batches / Lots') }}</div>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">inventory_2</span>
      <p>{{ t('no-records', 'No goods receipts found') }}</p>
      <button class="btn-primary mt-4" @click="openAdd">{{ t('new-gr', 'New Receipt') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="w-8"></th>
              <th>{{ t('gr-number', 'Receipt #') }}</th>
              <th>{{ t('po-ref', 'PO Ref') }}</th>
              <th>{{ t('supplier', 'Supplier') }}</th>
              <th>{{ t('warehouse', 'Warehouse') }}</th>
              <th class="text-center">{{ t('items', 'Items') }}</th>
              <th>{{ t('batches-lots', 'Batch / Lot #') }}</th>
              <th>{{ t('date', 'Date') }}</th>
              <th>{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in items" :key="item.id">
              <tr class="main-row" :class="{ 'row-expanded': expandedId === item.id }">
                <td class="text-center">
                  <button class="btn-icon btn-toggle" @click="toggleExpand(item.id)" :title="expandedId === item.id ? t('collapse') : t('expand')">
                    <span class="material-symbols-outlined">{{ expandedId === item.id ? 'expand_less' : 'expand_more' }}</span>
                  </button>
                </td>
                <td><span class="mono">{{ item.receipt_number }}</span></td>
                <td>{{ item.purchase_order_id ? `#${item.purchase_order_id}` : '-' }}</td>
                <td>{{ supplierName(item.supplier_id) }}</td>
                <td>{{ warehouseName(item.warehouse_id) }}</td>
                <td class="text-center">
                  <span class="items-count-badge">{{ item.lines?.length || 0 }}</span>
                </td>
                <td>
                  <div v-if="getBatches(item).length" class="batch-badges-wrap">
                    <span
                      v-for="b in getBatches(item)"
                      :key="b"
                      class="badge badge-batch"
                      :class="{ 'badge-batch-completed': isCompleted(item.status) }"
                      :title="'Lot: ' + b"
                    >
                      <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                      {{ b }}
                    </span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>
                <td>{{ formatDate(item.receipt_date || item.created_at) }}</td>
                <td>
                  <span class="badge" :class="isCompleted(item.status) ? 'badge-active' : 'badge-disabled'">
                    {{ item.status || 'Draft' }}
                  </span>
                </td>
                <td class="text-center">
                  <div class="actions-group">
                    <button class="btn-icon" @click="editItem(item)" :title="t('edit', 'Edit')">
                      <span class="material-symbols-outlined">edit</span>
                    </button>
                    <button class="btn-icon text-red-500" @click="deleteItem(item)" :title="t('delete', 'Delete')">
                      <span class="material-symbols-outlined">delete</span>
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Expanded Lines View -->
              <tr v-if="expandedId === item.id" class="expand-row">
                <td colspan="10" class="lines-cell">
                  <div class="receipt-lines-wrap">
                    <div class="receipt-lines-header">
                      <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-purple">list_alt</span>
                        <strong>{{ t('receipt-lines', 'Receipt Line Items & Lot Details') }}</strong>
                        <span class="badge badge-subtle">{{ item.lines?.length || 0 }} {{ t('lines', 'lines') }}</span>
                      </div>
                      <button v-if="!isCompleted(item.status)" class="btn-outline btn-sm" @click="editItem(item)">
                        <span class="material-symbols-outlined">edit_note</span> {{ t('edit-lines', 'Edit Lines') }}
                      </button>
                    </div>

                    <table v-if="item.lines && item.lines.length" class="data-table lines-table">
                      <thead>
                        <tr>
                          <th class="w-8">#</th>
                          <th>{{ t('product', 'Product') }}</th>
                          <th class="col-num">{{ t('qty-ordered', 'Qty Ordered') }}</th>
                          <th class="col-num">{{ t('qty-received', 'Qty Received') }}</th>
                          <th>{{ t('batch-lot', 'Batch / Lot #') }}</th>
                          <th>{{ t('mfg-date', 'Manufacturing Date') }}</th>
                          <th>{{ t('exp-date', 'Expiration Date') }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(line, idx) in item.lines" :key="line.id || idx">
                          <td class="cell-mono">{{ line.line_number || idx + 1 }}</td>
                          <td>
                            <strong>{{ line.product_name || productName(line.product_id) }}</strong>
                            <span v-if="line.product_id" class="text-muted text-xs block">ID: #{{ line.product_id }}</span>
                          </td>
                          <td class="col-num">{{ line.qty_ordered || '-' }}</td>
                          <td class="col-num font-bold">{{ line.qty_received }}</td>
                          <td>
                            <span v-if="line.batch_number" class="badge badge-batch" :class="{ 'badge-batch-completed': isCompleted(item.status) }">
                              <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                              {{ line.batch_number }}
                            </span>
                            <span v-else class="text-muted text-xs">{{ t('none', 'None') }}</span>
                          </td>
                          <td>{{ formatDate(line.manufacturing_date) }}</td>
                          <td>
                            <span v-if="line.expiry_date" :class="getExpiryClass(line.expiry_date)">
                              {{ formatDate(line.expiry_date) }}
                              <span v-if="isExpired(line.expiry_date)" class="badge-tag-danger">EXPIRED</span>
                            </span>
                            <span v-else class="text-muted text-xs">-</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-else class="no-lines">
                      <p>{{ t('no-lines-msg', 'No line items recorded for this receipt.') }}</p>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-purple">{{ editing ? 'edit' : 'add_box' }}</span>
            <h3>{{ editing ? t('edit-gr', 'Edit Goods Receipt') : t('new-gr', 'New Goods Receipt') }}</h3>
          </div>
          <button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <!-- Header Info Grid -->
          <div class="form-grid-2 mb-6">
            <div class="form-group">
              <label>{{ t('gr-number', 'Receipt #') }} <span class="text-red-500">*</span></label>
              <input type="text" v-model="form.receipt_number" class="form-input" placeholder="e.g. GRN-2026-001" />
            </div>
            <div class="form-group">
              <label>{{ t('po-ref', 'Purchase Order #') }}</label>
              <input type="number" v-model.number="form.purchase_order_id" class="form-input" placeholder="PO ID" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier', 'Supplier') }}</label>
              <select v-model="form.supplier_id" class="form-input">
                <option value="">-- {{ t('select-supplier', 'Select Supplier') }} --</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name || s.company_name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('warehouse', 'Warehouse') }}</label>
              <select v-model="form.warehouse_id" class="form-input">
                <option value="">-- {{ t('select-warehouse', 'Select Warehouse') }} --</option>
                <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('date', 'Receipt Date') }}</label>
              <input type="date" v-model="form.receipt_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Draft">Draft</option>
                <option value="Completed">Completed</option>
              </select>
            </div>
          </div>

          <div class="form-group mb-6">
            <label>{{ t('notes', 'Notes') }}</label>
            <input type="text" v-model="form.notes" class="form-input" placeholder="Optional receiving notes..." />
          </div>

          <!-- Line Items & Batch Capture Section -->
          <div class="line-items-section">
            <div class="flex justify-between items-center mb-3">
              <div>
                <h4 class="section-title">{{ t('line-items-batch', 'Line Items & Batch Information') }}</h4>
                <p class="section-desc">{{ t('line-items-desc', 'Capture batch/lot numbers and expiration dates for perishable and tracked inventory.') }}</p>
              </div>
              <button type="button" class="btn-outline btn-sm" @click="addLine">
                <span class="material-symbols-outlined">add</span> {{ t('add-line', 'Add Item') }}
              </button>
            </div>

            <div v-if="!form.lines.length" class="empty-lines-box">
              <p>{{ t('no-lines-added', 'No line items added yet. Click "Add Item" to record products.') }}</p>
            </div>

            <div v-else class="lines-editor-table-wrap">
              <table class="lines-editor-table">
                <thead>
                  <tr>
                    <th style="width: 25%">{{ t('product', 'Product') }} <span class="text-red-500">*</span></th>
                    <th style="width: 12%">{{ t('qty-ordered', 'Ordered') }}</th>
                    <th style="width: 12%">{{ t('qty-rcvd', 'Received') }} <span class="text-red-500">*</span></th>
                    <th style="width: 20%">{{ t('batch-lot', 'Batch / Lot #') }}</th>
                    <th style="width: 14%">{{ t('mfg-date', 'Mfg Date') }}</th>
                    <th style="width: 14%">{{ t('exp-date', 'Expiry Date') }}</th>
                    <th style="width: 3%"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, idx) in form.lines" :key="idx">
                    <td>
                      <select v-model="line.product_id" class="form-input form-input-sm" @change="onProductChange(line)">
                        <option value="">-- {{ t('select-product', 'Select') }} --</option>
                        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name || p.sku }}</option>
                      </select>
                    </td>
                    <td>
                      <input type="number" step="any" min="0" v-model.number="line.qty_ordered" class="form-input form-input-sm" placeholder="0" />
                    </td>
                    <td>
                      <input type="number" step="any" min="0.01" v-model.number="line.qty_received" class="form-input form-input-sm font-bold" placeholder="Qty" />
                    </td>
                    <td>
                      <div class="batch-input-wrap">
                        <input
                          type="text"
                          v-model="line.batch_number"
                          class="form-input form-input-sm batch-input"
                          placeholder="e.g. LOT-2026-A1"
                        />
                      </div>
                    </td>
                    <td>
                      <input type="date" v-model="line.manufacturing_date" class="form-input form-input-sm date-input" />
                    </td>
                    <td>
                      <input type="date" v-model="line.expiry_date" class="form-input form-input-sm date-input" />
                    </td>
                    <td class="text-center">
                      <button type="button" class="btn-icon btn-icon-danger" @click="removeLine(idx)" :title="t('remove-line', 'Remove')">
                        <span class="material-symbols-outlined">delete</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveItem">
            <span v-if="saving" class="material-symbols-outlined spin">progress_activity</span>
            {{ saving ? t('saving', 'Saving...') : t('save', 'Save Receipt') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <ConfirmDialog
      v-if="confirmTarget"
      :title="t('confirm-delete', 'Delete Receipt?')"
      :message="t('confirm-delete-msg', 'Are you sure you want to delete receipt') + ' ' + confirmTarget.receipt_number + '?'"
      @confirm="executeDelete(confirmTarget)"
      @cancel="confirmTarget = null"
    />
    <!-- Camera Barcode Scanner Modal -->
    <CameraBarcodeScannerModal
      v-model="showCameraScanner"
      @scan="(parsed, raw) => handleBarcodeScan(parsed, raw)"
    />

    <!-- Barcode Scan Mismatch Warning Modal -->
    <Teleport to="body">
      <div v-if="showMismatchModal" class="modal-overlay" @click.self="showMismatchModal = false">
        <div class="modal-dialog modal-dialog-warning" :dir="dir">
          <div class="modal-header header-danger">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-red">warning</span>
              <h3 class="modal-title text-red">{{ t('barcode-mismatch-title', 'Barcode Scan Mismatch Warning') }}</h3>
            </div>
            <button class="modal-close" @click="showMismatchModal = false">&times;</button>
          </div>
          <div class="modal-body text-center py-6">
            <div class="mismatch-icon-wrap mb-3">
              <span class="material-symbols-outlined icon-mismatch">qr_code_scanner</span>
            </div>
            <h4 class="font-bold text-lg text-slate-800 mb-2">
              {{ t('unrecognized-barcode', 'Unrecognized or Mismatched Item') }}
            </h4>
            <p class="text-sm text-slate-600 mb-4">
              {{ t('mismatch-gr-desc', 'Scanned barcode does not match any recognized product barcode, GTIN, or lot label for receiving:') }}
            </p>
            <div class="scanned-code-box mb-4">
              <code>{{ lastMismatchedCode }}</code>
            </div>
            <div class="alert-warning-box">
              <span class="material-symbols-outlined icon-xs">block</span>
              <span>{{ t('receiving-prevented', 'Inbound goods receipt entry prevented to avoid invalid inventory intake.') }}</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-primary btn-danger-action" @click="showMismatchModal = false">
              {{ t('acknowledge-dismiss', 'Acknowledge & Dismiss') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
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
import { useBarcodeScanner } from '../../composables/useBarcodeScanner.js'
import { useScanFeedback } from '../../composables/useScanFeedback.js'
import CameraBarcodeScannerModal from '../../components/CameraBarcodeScannerModal.vue'
import { parseBarcode, formatGS1Date } from '../../utils/barcodeParser.js'

const { show: toast } = useToast()
const { t, dir } = useI18n()

// Scan feedback & hardware scanner listeners
const feedback = useScanFeedback()
const { flashState, notifySuccess, notifyError, notifyWarning, soundEnabled } = feedback

const showCameraScanner = ref(false)
const showMismatchModal = ref(false)
const lastMismatchedCode = ref('')
const globalScan = ref('')

const scanner = useBarcodeScanner({
  onScan: (parsedBarcode, rawString) => {
    handleBarcodeScan(parsedBarcode, rawString)
  },
  ignoreInputs: false,
  endKeys: ['Enter']
})

const loading = ref(true)
const error = ref('')
const items = ref([])
const suppliers = ref([])
const warehouses = ref([])
const products = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const editId = ref(null)
const expandedId = ref(null)
const confirmTarget = ref(null)
const deletedLineIds = ref([])

const form = ref({
  receipt_number: '',
  purchase_order_id: null,
  supplier_id: '',
  warehouse_id: '',
  receipt_date: '',
  status: 'Draft',
  notes: '',
  lines: []
})

const completedCount = computed(() => {
  return items.value.filter(i => isCompleted(i.status)).length
})

const trackedBatchesCount = computed(() => {
  let count = 0
  for (const item of items.value) {
    count += getBatches(item).length
  }
  return count
})

function isCompleted(status) {
  if (!status) return false
  return String(status).toLowerCase() === 'completed'
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function isExpired(d) {
  if (!d) return false
  const exp = new Date(d)
  const now = new Date()
  return exp < now
}

function getExpiryClass(d) {
  if (!d) return ''
  if (isExpired(d)) return 'text-red font-semibold'
  const exp = new Date(d)
  const now = new Date()
  const daysUntil = (exp - now) / (1000 * 60 * 60 * 24)
  if (daysUntil <= 30) return 'text-amber font-semibold'
  return 'text-green'
}

function supplierName(id) {
  if (!id) return '-'
  const s = suppliers.value.find(x => x.id === id)
  return s ? (s.name || s.company_name) : `#${id}`
}

function warehouseName(id) {
  if (!id) return '-'
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : `#${id}`
}

function productName(id) {
  if (!id) return '-'
  const p = products.value.find(x => x.id === id)
  return p ? (p.name || p.sku) : `#${id}`
}

function getBatches(item) {
  if (!item.lines || !item.lines.length) return []
  const batches = item.lines
    .map(l => l.batch_number)
    .filter(b => b && String(b).trim().length > 0)
  return [...new Set(batches)]
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [gRes, sRes, wRes, pRes, lRes] = await Promise.all([
      api.get('/T0075I/'),
      api.get('/T0103I/').catch(() => api.get('/T0011I/').catch(() => ({ data: [] }))),
      api.get('/T0008I/').catch(() => ({ data: [] })),
      api.get('/T0003I/').catch(() => ({ data: [] })),
      api.get('/T0076I/').catch(() => ({ data: [] }))
    ])

    const receipts = gRes.data || []
    suppliers.value = sRes.data || []
    warehouses.value = wRes.data || []
    products.value = pRes.data || []
    const allLines = lRes.data || []

    const lineMap = {}
    for (const l of allLines) {
      if (!lineMap[l.receipt_id]) lineMap[l.receipt_id] = []
      lineMap[l.receipt_id].push(l)
    }

    items.value = receipts.map(r => ({
      ...r,
      lines: lineMap[r.id] || []
    }))
  } catch {
    error.value = t('failed-load', 'Failed to load goods receipts')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  deletedLineIds.value = []
  form.value = {
    receipt_number: 'GRN-' + Date.now().toString().slice(-6),
    purchase_order_id: null,
    supplier_id: '',
    warehouse_id: '',
    receipt_date: new Date().toISOString().slice(0, 10),
    status: 'Draft',
    notes: '',
    lines: [
      {
        product_id: '',
        product_name: '',
        qty_ordered: 1,
        qty_received: 1,
        batch_number: '',
        manufacturing_date: '',
        expiry_date: ''
      }
    ]
  }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  deletedLineIds.value = []

  const existingLines = (item.lines || []).map(l => ({
    id: l.id,
    product_id: l.product_id || '',
    product_name: l.product_name || '',
    qty_ordered: l.qty_ordered || 0,
    qty_received: l.qty_received || 0,
    batch_number: l.batch_number || '',
    manufacturing_date: l.manufacturing_date ? l.manufacturing_date.slice(0, 10) : '',
    expiry_date: l.expiry_date ? l.expiry_date.slice(0, 10) : ''
  }))

  form.value = {
    receipt_number: item.receipt_number || '',
    purchase_order_id: item.purchase_order_id || null,
    supplier_id: item.supplier_id || '',
    warehouse_id: item.warehouse_id || '',
    receipt_date: item.receipt_date ? item.receipt_date.slice(0, 10) : '',
    status: item.status || 'Draft',
    notes: item.notes || '',
    lines: existingLines.length ? existingLines : [
      {
        product_id: '',
        product_name: '',
        qty_ordered: 1,
        qty_received: 1,
        batch_number: '',
        manufacturing_date: '',
        expiry_date: ''
      }
    ]
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function addLine() {
  form.value.lines.push({
    product_id: '',
    product_name: '',
    qty_ordered: 1,
    qty_received: 1,
    batch_number: '',
    manufacturing_date: '',
    expiry_date: ''
  })
}

function removeLine(index) {
  const line = form.value.lines[index]
  if (line && line.id) {
    deletedLineIds.value.push(line.id)
  }
  form.value.lines.splice(index, 1)
}

function onProductChange(line) {
  if (!line.product_id) return
  const p = products.value.find(x => x.id === line.product_id)
  if (p) {
    line.product_name = p.name || p.sku || `Product #${p.id}`
  }
}

async function saveItem() {
  if (!form.value.receipt_number || !form.value.receipt_number.trim()) {
    toast(t('receipt-num-required', 'Receipt number is required'), 'error')
    return
  }

  saving.value = true
  try {
    const targetStatus = form.value.status || 'Draft'
    const validLines = form.value.lines.filter(l => l.product_id || (l.product_name && l.product_name.trim()))

    if (editing.value) {
      // 1. Delete removed lines
      for (const lineId of deletedLineIds.value) {
        await api.delete(`/T0076I/${lineId}`).catch(() => {})
      }

      // 2. Save or update lines
      for (let i = 0; i < validLines.length; i++) {
        const line = validLines[i]
        const linePayload = {
          receipt_id: editId.value,
          product_id: line.product_id ? Number(line.product_id) : null,
          product_name: line.product_name || productName(line.product_id),
          qty_ordered: Number(line.qty_ordered) || 0,
          qty_received: Number(line.qty_received) || 0,
          batch_number: line.batch_number ? line.batch_number.trim() : null,
          manufacturing_date: line.manufacturing_date || null,
          expiry_date: line.expiry_date || null,
          line_number: i + 1
        }

        if (line.id) {
          await api.put(`/T0076I/${line.id}`, linePayload)
        } else {
          await api.post('/T0076I/', linePayload)
        }
      }

      // 3. Update receipt header (will trigger stock movements & batch registration if status changed to Completed)
      const receiptPayload = {
        receipt_number: form.value.receipt_number,
        purchase_order_id: form.value.purchase_order_id ? Number(form.value.purchase_order_id) : null,
        supplier_id: form.value.supplier_id ? Number(form.value.supplier_id) : null,
        warehouse_id: form.value.warehouse_id ? Number(form.value.warehouse_id) : null,
        receipt_date: form.value.receipt_date || null,
        status: targetStatus,
        notes: form.value.notes || null
      }
      await api.put(`/T0075I/${editId.value}`, receiptPayload)

      toast(t('receipt-updated', 'Goods receipt updated successfully'), 'success')
    } else {
      // Create new receipt
      // To ensure lines exist when status becomes 'Completed', create receipt with Draft first if target is Completed
      const initPayload = {
        receipt_number: form.value.receipt_number,
        purchase_order_id: form.value.purchase_order_id ? Number(form.value.purchase_order_id) : null,
        supplier_id: form.value.supplier_id ? Number(form.value.supplier_id) : null,
        warehouse_id: form.value.warehouse_id ? Number(form.value.warehouse_id) : null,
        receipt_date: form.value.receipt_date || null,
        status: targetStatus === 'Completed' ? 'Draft' : targetStatus,
        notes: form.value.notes || null
      }

      const res = await api.post('/T0075I/', initPayload)
      const newId = res.data.id

      // Create lines
      for (let i = 0; i < validLines.length; i++) {
        const line = validLines[i]
        await api.post('/T0076I/', {
          receipt_id: newId,
          product_id: line.product_id ? Number(line.product_id) : null,
          product_name: line.product_name || productName(line.product_id),
          qty_ordered: Number(line.qty_ordered) || 0,
          qty_received: Number(line.qty_received) || 0,
          batch_number: line.batch_number ? line.batch_number.trim() : null,
          manufacturing_date: line.manufacturing_date || null,
          expiry_date: line.expiry_date || null,
          line_number: i + 1
        })
      }

      // If user selected Completed, now update receipt to Completed to trigger batch & stock sync
      if (targetStatus === 'Completed') {
        await api.put(`/T0075I/${newId}`, { status: 'Completed' })
      }

      toast(t('receipt-created', 'Goods receipt created successfully'), 'success')
    }

    closeModal()
    await load()
  } catch (err) {
    console.error('Error saving goods receipt:', err)
    toast(t('failed-save', 'Failed to save goods receipt'), 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  confirmTarget.value = item
}

async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0075I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast(t('receipt-deleted', 'Receipt deleted'), 'success')
  } catch {
    toast(t('failed-delete', 'Failed to delete receipt'), 'error')
  }
}

function onManualGlobalScan() {
  const code = (globalScan.value || '').trim()
  if (!code) return
  handleBarcodeScan(null, code)
  globalScan.value = ''
}

function handleBarcodeScan(parsed, rawString) {
  const rawCode = (rawString || (typeof parsed === 'string' ? parsed : parsed?.raw) || '').trim()
  if (!rawCode) return

  const parsedObj = (typeof parsed === 'object' && parsed !== null) ? parsed : parseBarcode(rawCode)

  const gtin = parsedObj.gtin || parsedObj.code || rawCode
  const aiBatch = parsedObj.batchNumber || parsedObj.attributes?.['10'] || parsedObj.aiData?.['10'] || null
  const aiMfg = parsedObj.productionDate || (parsedObj.attributes?.['11'] ? formatGS1Date(parsedObj.attributes['11']) : null) || (parsedObj.aiData?.['11'] ? formatGS1Date(parsedObj.aiData['11']) : null) || null
  const aiExpiry = parsedObj.expiryDate || parsedObj.bestBeforeDate || (parsedObj.attributes?.['17'] ? formatGS1Date(parsedObj.attributes['17']) : null) || (parsedObj.attributes?.['15'] ? formatGS1Date(parsedObj.attributes['15']) : null) || (parsedObj.aiData?.['17'] ? formatGS1Date(parsedObj.aiData['17']) : null) || (parsedObj.aiData?.['15'] ? formatGS1Date(parsedObj.aiData['15']) : null) || null

  const normRaw = rawCode.toLowerCase().replace(/^0+/, '')
  const normGtin = (gtin || '').toLowerCase().replace(/^0+/, '')

  const isProductMatch = (p) => {
    if (!p) return false
    const pCode = (p.barcode || p.product_barcode || p.gtin || p.sku || '').toLowerCase()
    const normPCode = pCode.replace(/^0+/, '')
    const rCode = rawCode.toLowerCase()
    const gCode = (gtin || '').toLowerCase()
    return (
      (pCode && (pCode === rCode || pCode === gCode || (normPCode && (normPCode === normRaw || normPCode === normGtin)))) ||
      String(p.id) === rawCode ||
      String(p.id) === gtin ||
      (normRaw && String(p.id) === normRaw) ||
      (p.sku && p.sku.toLowerCase() === rCode)
    )
  }

  // 1. If edit/create receipt modal is open, match or add to form.value.lines
  if (showModal.value) {
    let matchedLine = form.value.lines.find(l => {
      if (l.product_id) {
        const prod = products.value.find(x => x.id === l.product_id)
        if (prod && isProductMatch(prod)) {
          if (aiBatch) {
            return !l.batch_number || l.batch_number === aiBatch
          }
          return true
        }
      }
      const lName = (l.product_name || '').toLowerCase()
      return lName && (lName.includes(rawCode.toLowerCase()) || (gtin && lName.includes(gtin.toLowerCase())))
    })

    if (matchedLine) {
      matchedLine.qty_received = (Number(matchedLine.qty_received) || 0) + 1
      if (aiBatch) matchedLine.batch_number = aiBatch
      if (aiMfg) matchedLine.manufacturing_date = aiMfg
      if (aiExpiry) matchedLine.expiry_date = aiExpiry
      notifySuccess(t('scan-receipt-qty-inc', `Received 1x ${matchedLine.product_name || 'Item'} (Total: ${matchedLine.qty_received})`))
      return
    }

    // Line not found in form lines; search available products to add a line
    const matchedProduct = products.value.find(p => isProductMatch(p))
    if (matchedProduct) {
      const newLine = {
        product_id: matchedProduct.id,
        product_name: matchedProduct.name || matchedProduct.sku,
        qty_ordered: 1,
        qty_received: 1,
        batch_number: aiBatch || '',
        manufacturing_date: aiMfg || '',
        expiry_date: aiExpiry || ''
      }
      form.value.lines.push(newLine)
      notifySuccess(t('scan-receipt-line-added', `Added ${matchedProduct.name || matchedProduct.sku} to receipt`))
      return
    }

    // Product unrecognized
    lastMismatchedCode.value = rawCode
    showMismatchModal.value = true
    notifyError(t('unrecognized-receiving-barcode', `Unrecognized goods receipt barcode: ${rawCode}`))
    return
  }

  // 2. If modal is not open, but a receipt is currently expanded in list view
  if (expandedId.value) {
    const currentItem = items.value.find(i => i.id === expandedId.value)
    if (currentItem && !isCompleted(currentItem.status)) {
      editItem(currentItem)
      handleBarcodeScan(parsedObj, rawCode)
      return
    }
  }

  // 3. Main view scan: find product and open new receipt
  const matchedProduct = products.value.find(p => isProductMatch(p))
  if (matchedProduct) {
    openAdd()
    form.value.lines[0].product_id = matchedProduct.id
    form.value.lines[0].product_name = matchedProduct.name || matchedProduct.sku
    form.value.lines[0].qty_received = 1
    if (aiBatch) form.value.lines[0].batch_number = aiBatch
    if (aiMfg) form.value.lines[0].manufacturing_date = aiMfg
    if (aiExpiry) form.value.lines[0].expiry_date = aiExpiry
    notifySuccess(t('scan-new-receipt-started', `Started new receipt with ${matchedProduct.name || matchedProduct.sku}`))
    return
  }

  // Code unrecognized
  lastMismatchedCode.value = rawCode
  showMismatchModal.value = true
  notifyError(t('unrecognized-receiving-barcode', `Unrecognized goods receipt barcode: ${rawCode}`))
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 16px; font-size: 11px; font-weight: 700; color: #777; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; vertical-align: middle; }
.main-row:hover td { background: #fafafe; }
.row-expanded td { background: #f8f7fd !important; }
.text-center { text-align: center; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.text-red-500 { color: #e53935; }
.text-red { color: #dc2626; }
.text-amber { color: #d97706; }
.text-green { color: #16a34a; }
.text-purple { color: #5d3fd3; }
.text-muted { color: #999; }
.text-xs { font-size: 11px; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.block { display: block; }
.w-8 { width: 32px; }

/* Stats Row */
.stats-row { display: flex; gap: 16px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px 20px; flex: 1; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
.stat-num { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.stat-lbl { font-size: 12px; color: #888; margin-top: 2px; }

/* Badges */
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-disabled { background: #f5f5f5; color: #888; }
.badge-subtle { background: #ede9fe; color: #5d3fd3; }
.items-count-badge { display: inline-block; padding: 2px 8px; background: #f0f0f4; border-radius: 10px; font-size: 11px; font-weight: 600; color: #444; }

.batch-badges-wrap { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.badge-batch { background: #f3f0ff; color: #5d3fd3; border: 1px solid #ddd6fe; padding: 2px 8px; border-radius: 6px; font-family: monospace; font-size: 11px; font-weight: 600; }
.badge-batch-completed { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.badge-tag-danger { display: inline-block; margin-left: 6px; padding: 1px 4px; font-size: 9px; background: #fee2e2; color: #b91c1c; border-radius: 4px; font-weight: 700; }

.icon-xs { font-size: 13px !important; vertical-align: middle; }

/* Buttons */
.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px; background: #f0f0f4; color: #333; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover { background: #e0e0e0; }
.btn-outline { display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; background: transparent; color: #5d3fd3; border: 1px solid #ddd6fe; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f3ff; }
.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border: none; border-radius: 6px; background: none; cursor: pointer; color: #666; transition: background 0.15s; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-toggle { color: #5d3fd3; }

.actions-group { display: inline-flex; align-items: center; gap: 2px; }

/* Lines View */
.expand-row td { padding: 0 !important; }
.lines-cell { background: #fafbfc; border-bottom: 2px solid #e2e8f0 !important; }
.receipt-lines-wrap { padding: 16px 24px; }
.receipt-lines-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.receipt-lines-header strong { font-size: 13px; color: #1a1a2e; }
.lines-table { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; font-size: 12px; }
.lines-table th { background: #f1f5f9; padding: 8px 12px; font-size: 10px; }
.lines-table td { padding: 8px 12px; }
.no-lines { padding: 20px; text-align: center; color: #888; font-size: 13px; background: #fff; border-radius: 8px; border: 1px dashed #cbd5e1; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal { background: #fff; border-radius: 14px; width: 500px; max-width: 92vw; max-height: 88vh; overflow-y: auto; box-shadow: 0 12px 40px rgba(0,0,0,0.2); }
.modal-lg { width: 840px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid #eee; background: #fafafa; border-radius: 0 0 14px 14px; }

/* Form Controls */
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 11px; font-weight: 700; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.4px; }
.form-input { width: 100%; padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; transition: border-color 0.15s; }
.form-input:focus { border-color: #5d3fd3; box-shadow: 0 0 0 3px rgba(93,63,211,0.1); }
.form-input-sm { padding: 6px 8px; font-size: 12px; border-radius: 6px; }
select.form-input { appearance: auto; }

/* Line Items Editor Section */
.line-items-section { border-top: 1px solid #eee; padding-top: 18px; margin-top: 6px; }
.section-title { margin: 0; font-size: 13px; font-weight: 700; color: #1a1a2e; }
.section-desc { margin: 2px 0 0; font-size: 11px; color: #64748b; }
.empty-lines-box { padding: 20px; text-align: center; color: #64748b; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; font-size: 12px; }
.lines-editor-table-wrap { overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.lines-editor-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.lines-editor-table th { background: #f8fafc; padding: 8px 10px; font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.lines-editor-table td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.lines-editor-table tr:last-child td { border-bottom: none; }
.batch-input { font-family: monospace; font-weight: 600; color: #5d3fd3; }
.date-input { font-size: 11px; }

.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
.mb-3 { margin-bottom: 12px; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Quick Barcode Scanner Card */
.scanner-card { background: #fdfaff; border: 1px dashed #c4b5fd; border-radius: 12px; padding: 14px 18px; }
.scanner-icon { font-size: 32px; color: #5d3fd3; }
.scanner-label { display: block; font-size: 11px; font-weight: 700; color: #5d3fd3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.scanner-input { background: #fff; border-color: #c4b5fd; font-family: monospace; font-size: 13px; }

/* Scanner status badge & pulse */
.badge-scanner-active { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
.status-pulse { width: 7px; height: 7px; border-radius: 50%; background: #16a34a; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }

/* Visual Flash States */
.scanner-card.flash-success { border-color: #22c55e !important; box-shadow: 0 0 12px rgba(34, 197, 94, 0.4); background: #f0fdf4 !important; transition: all 0.2s ease; }
.scanner-card.flash-error { border-color: #ef4444 !important; box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); background: #fef2f2 !important; transition: all 0.2s ease; }

/* Mismatch Warning Modal */
.modal-dialog { background: #fff; border-radius: 12px; width: 90%; max-width: 580px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); overflow: hidden; }
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-close { background: none; border: none; font-size: 24px; color: #94a3b8; cursor: pointer; line-height: 1; }
.modal-close:hover { color: #1e293b; }
.modal-dialog-warning { max-width: 480px; }
.header-danger { background: #fef2f2; border-bottom: 1px solid #fee2e2; }
.mismatch-icon-wrap { width: 56px; height: 56px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; margin: 0 auto; }
.icon-mismatch { font-size: 32px; }
.scanned-code-box { background: #f1f5f9; padding: 8px 14px; border-radius: 8px; border: 1px solid #e2e8f0; display: inline-block; font-family: monospace; font-size: 15px; color: #0f172a; }
.alert-warning-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; color: #92400e; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; }
.btn-danger-action { background: #dc2626; color: #fff; border: none; }
.btn-danger-action:hover { background: #b91c1c; }

.flex-1 { flex: 1; }
.px-3 { padding-left: 12px; padding-right: 12px; }
.px-4 { padding-left: 16px; padding-right: 16px; }
.py-6 { padding-top: 24px; padding-bottom: 24px; }

[dir="rtl"] .data-table th, [dir="rtl"] .lines-table th, [dir="rtl"] .lines-editor-table th { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
</style>
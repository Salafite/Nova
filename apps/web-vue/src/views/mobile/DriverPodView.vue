<template>
  <div class="driver-pod-container" :dir="dir">
    <div class="header-card">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="page-title">{{ t('driver-pod-title', 'Proof of Delivery & COD') }}</h1>
          <p class="page-subtitle">{{ t('driver-pod-sub', 'Capture recipient signature, photo proof, and record payment collection') }}</p>
        </div>
        <button class="btn-outline" @click="$router.push('/sales/deliveries')">
          <span class="material-symbols-outlined icon-xs">arrow_back</span>
          {{ t('back', 'Back to Deliveries') }}
        </button>
      </div>
    </div>

    <!-- Delivery Selection / Details -->
    <div class="card mb-4">
      <div class="form-group">
        <label class="form-label">{{ t('select-delivery', 'Select Delivery Order') }}</label>
        <select v-model="selectedDeliveryId" class="form-input" @change="onDeliveryChange">
          <option :value="null">-- {{ t('select-delivery-placeholder', 'Select a Delivery') }} --</option>
          <option v-for="del in deliveries" :key="del.id" :value="del.id">
            {{ del.delivery_number }} (SO #{{ del.sales_order_id }}) - {{ del.status }}
          </option>
        </select>
      </div>

      <div v-if="currentDelivery" class="delivery-info-grid mt-3">
        <div class="info-item">
          <span class="info-label">{{ t('delivery-number', 'Delivery #') }}:</span>
          <span class="info-value font-mono">{{ currentDelivery.delivery_number }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('status', 'Status') }}:</span>
          <span class="badge" :class="statusBadge(currentDelivery.status)">{{ currentDelivery.status }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('payment-status', 'Payment Status') }}:</span>
          <span class="badge" :class="paymentStatusBadge(currentDelivery.payment_status)">{{ currentDelivery.payment_status || 'Pending' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ t('assigned-driver', 'Driver') }}:</span>
          <span class="info-value">{{ currentDelivery.assigned_driver || currentDelivery.driver_name || 'Driver #1' }}</span>
        </div>
      </div>
    </div>

    <div v-if="currentDelivery" class="pod-grid">
      <!-- Digital Signature Canvas Card -->
      <div class="card pod-section">
        <h3 class="section-title flex items-center gap-2">
          <span class="material-symbols-outlined icon-sm">draw</span>
          {{ t('recipient-signature', 'Recipient Signature') }}
        </h3>
        <p class="text-xs text-muted mb-2">{{ t('signature-hint', 'Draw recipient signature on the canvas below') }}</p>

        <div class="signature-wrapper">
          <canvas
            ref="signatureCanvas"
            class="signature-canvas"
            width="400"
            height="180"
            @mousedown="startDrawing"
            @mousemove="draw"
            @mouseup="stopDrawing"
            @mouseleave="stopDrawing"
            @touchstart.prevent="handleTouchStart"
            @touchmove.prevent="handleTouchMove"
            @touchend.prevent="stopDrawing"
          ></canvas>
        </div>

        <div class="flex justify-between items-center mt-2">
          <button class="btn-outline btn-sm" @click="clearSignature">
            <span class="material-symbols-outlined icon-xs">delete</span>
            {{ t('clear', 'Clear') }}
          </button>
          <span v-if="signatureCaptured" class="text-xs text-success flex items-center gap-1">
            <span class="material-symbols-outlined icon-xs">check_circle</span>
            {{ t('signature-ready', 'Signature Captured') }}
          </span>
        </div>
      </div>

      <!-- Photo Proof Section -->
      <div class="card pod-section">
        <h3 class="section-title flex items-center gap-2">
          <span class="material-symbols-outlined icon-sm">photo_camera</span>
          {{ t('photo-proof', 'Photo Proof of Delivery') }}
        </h3>
        <p class="text-xs text-muted mb-2">{{ t('photo-hint', 'Upload or paste image URL showing delivered goods at destination') }}</p>

        <div class="form-group mb-2">
          <input
            type="text"
            v-model="photoUrl"
            class="form-input"
            placeholder="https://example.com/photo-proof.jpg"
          />
        </div>

        <div class="form-group">
          <label class="btn-outline btn-sm file-upload-btn">
            <span class="material-symbols-outlined icon-xs">upload</span>
            {{ t('choose-photo', 'Choose Image File') }}
            <input type="file" accept="image/*" class="hidden-file-input" @change="handleFileUpload" />
          </label>
        </div>

        <div v-if="photoUrl" class="photo-preview mt-2">
          <img :src="photoUrl" alt="POD Proof" class="preview-img" />
        </div>
      </div>

      <!-- Location Input -->
      <div class="card pod-section col-span-full">
        <h3 class="section-title flex items-center gap-2">
          <span class="material-symbols-outlined icon-sm">location_on</span>
          {{ t('delivery-location', 'Delivery Location') }}
        </h3>
        <div class="form-group mb-0">
          <input
            type="text"
            v-model="locationText"
            class="form-input"
            placeholder="e.g. 123 Main St, Loading Dock 4 (GPS: 24.7136, 46.6753)"
          />
        </div>
      </div>

      <!-- COD Collection Form -->
      <div class="card pod-section col-span-full">
        <h3 class="section-title flex items-center gap-2">
          <span class="material-symbols-outlined icon-sm">payments</span>
          {{ t('cod-collection', 'COD Payment Collection') }}
        </h3>

        <div class="form-grid-2 mt-2">
          <div class="form-group">
            <label class="form-label">{{ t('cash-collected', 'Cash Amount Collected ($)') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="codCashAmount" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('check-collected', 'Check Amount Collected ($)') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="codCheckAmount" class="form-input" />
          </div>
          <div class="form-group" v-if="codCheckAmount > 0">
            <label class="form-label">{{ t('check-number', 'Check Number') }}</label>
            <input type="text" v-model="codCheckNumber" class="form-input" placeholder="CHK-991203" />
          </div>
          <div class="form-group" v-if="codCheckAmount > 0">
            <label class="form-label">{{ t('check-bank', 'Check Bank Name') }}</label>
            <input type="text" v-model="codCheckBank" class="form-input" placeholder="First National Bank" />
          </div>
          <div class="form-group col-span-full">
            <label class="form-label">{{ t('payment-status', 'Payment Status') }}</label>
            <select v-model="paymentStatus" class="form-input">
              <option value="Collected">Collected</option>
              <option value="In Transit">In Transit</option>
              <option value="Pending">Pending</option>
              <option value="Failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="col-span-full flex justify-end gap-3 mt-4">
        <button class="btn-outline" @click="resetForm">{{ t('reset', 'Reset') }}</button>
        <button class="btn-primary" :disabled="submitting" @click="submitPodAndCod">
          <span v-if="submitting" class="material-symbols-outlined spin icon-xs">progress_activity</span>
          <span v-else class="material-symbols-outlined icon-xs">check_circle</span>
          {{ submitting ? t('saving', 'Submitting...') : t('submit-pod-cod', 'Submit POD & COD Log') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const deliveries = ref([])
const selectedDeliveryId = ref(null)
const submitting = ref(false)

// Canvas state
const signatureCanvas = ref(null)
const isDrawing = ref(false)
const signatureCaptured = ref(false)

// Form fields
const photoUrl = ref('')
const locationText = ref('')
const codCashAmount = ref(0)
const codCheckAmount = ref(0)
const codCheckNumber = ref('')
const codCheckBank = ref('')
const paymentStatus = ref('Collected')

const currentDelivery = computed(() => {
  return deliveries.value.find(d => d.id === selectedDeliveryId.value) || null
})

watch(selectedDeliveryId, () => {
  onDeliveryChange()
})

function statusBadge(s) {
  if (s === 'Delivered') return 'badge-active'
  if (s === 'Shipped') return 'badge-info'
  return 'badge-inactive'
}

function paymentStatusBadge(s) {
  if (s === 'Collected' || s === 'Reconciled') return 'badge-active'
  if (s === 'In Transit') return 'badge-info'
  return 'badge-inactive'
}

onMounted(async () => {
  await loadDeliveries()
})

async function loadDeliveries() {
  try {
    const res = await api.get('/T0077I/')
    deliveries.value = res.data || []
    if (deliveries.value.length > 0) {
      selectedDeliveryId.value = deliveries.value[0].id
      onDeliveryChange()
    }
  } catch (err) {
    toast(t('failed-load', 'Failed to load delivery orders'), 'error')
  }
}

function onDeliveryChange() {
  clearSignature()
  photoUrl.value = ''
  locationText.value = ''
  codCashAmount.value = currentDelivery.value?.cod_cash_amount || 0
  codCheckAmount.value = currentDelivery.value?.cod_check_amount || 0
  codCheckNumber.value = currentDelivery.value?.cod_check_number || ''
  codCheckBank.value = currentDelivery.value?.cod_check_bank || ''
  const status = currentDelivery.value?.payment_status
  paymentStatus.value = (status && status !== 'Pending') ? status : 'Collected'
}

// Canvas Signature logic
function startDrawing(e) {
  isDrawing.value = true
  const canvas = signatureCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const rect = canvas.getBoundingClientRect()
  ctx.beginPath()
  ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top)
}

function draw(e) {
  if (!isDrawing.value) return
  const canvas = signatureCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const rect = canvas.getBoundingClientRect()
  ctx.lineWidth = 2.5
  ctx.lineCap = 'round'
  ctx.strokeStyle = '#1a1a2e'
  ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top)
  ctx.stroke()
  signatureCaptured.value = true
}

function stopDrawing() {
  isDrawing.value = false
}

function handleTouchStart(e) {
  if (e.touches.length > 0) {
    const touch = e.touches[0]
    isDrawing.value = true
    const canvas = signatureCanvas.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const rect = canvas.getBoundingClientRect()
    ctx.beginPath()
    ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top)
  }
}

function handleTouchMove(e) {
  if (!isDrawing.value || e.touches.length === 0) return
  const touch = e.touches[0]
  const canvas = signatureCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const rect = canvas.getBoundingClientRect()
  ctx.lineWidth = 2.5
  ctx.lineCap = 'round'
  ctx.strokeStyle = '#1a1a2e'
  ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top)
  ctx.stroke()
  signatureCaptured.value = true
}

function clearSignature() {
  const canvas = signatureCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  signatureCaptured.value = false
}

function handleFileUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (event) => {
    photoUrl.value = event.target.result
  }
  reader.readAsDataURL(file)
}

function resetForm() {
  clearSignature()
  photoUrl.value = ''
  locationText.value = ''
  codCashAmount.value = 0
  codCheckAmount.value = 0
  codCheckNumber.value = ''
  codCheckBank.value = ''
  paymentStatus.value = 'Collected'
}

async function submitPodAndCod() {
  if (!selectedDeliveryId.value) {
    toast(t('select-delivery-required', 'Please select a delivery'), 'error')
    return
  }

  submitting.value = true
  try {
    let signatureData = null
    if (signatureCanvas.value && signatureCaptured.value) {
      signatureData = signatureCanvas.value.toDataURL('image/png')
    }

    // 1. Submit POD endpoint
    await api.post(`/T0077I/${selectedDeliveryId.value}/pod`, {
      recipient_signature: signatureData,
      delivery_photo_url: photoUrl.value || null,
      delivery_location: locationText.value || null,
      pod_timestamp: new Date().toISOString()
    })

    // 2. Submit COD Collection endpoint
    await api.post(`/T0077I/${selectedDeliveryId.value}/cod`, {
      cod_cash_amount: Number(codCashAmount.value || 0),
      cod_check_amount: Number(codCheckAmount.value || 0),
      cod_check_number: codCheckNumber.value || null,
      cod_check_bank: codCheckBank.value || null,
      payment_status: paymentStatus.value || 'Collected'
    })

    toast(t('pod-saved-success', 'Proof of delivery & COD recorded successfully!'), 'success')
    await loadDeliveries()
  } catch (err) {
    toast(err.response?.data?.detail || t('pod-save-failed', 'Failed to record POD/COD'), 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.driver-pod-container { padding: 16px; max-width: 900px; margin: 0 auto; }
.header-card { margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }

.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.pod-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.col-span-full { grid-column: 1 / -1; }

.section-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-top: 0; margin-bottom: 8px; }
.icon-sm { font-size: 18px !important; color: #5d3fd3; }
.icon-xs { font-size: 14px !important; }

.signature-wrapper { border: 2px dashed #cbd5e1; border-radius: 8px; background: #f8fafc; overflow: hidden; display: flex; justify-content: center; }
.signature-canvas { cursor: crosshair; touch-action: none; background: #ffffff; }

.photo-preview { margin-top: 8px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; max-height: 180px; }
.preview-img { width: 100%; height: 180px; object-fit: cover; }

.hidden-file-input { display: none; }
.file-upload-btn { cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }

.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-group { margin-bottom: 12px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }

.delivery-info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; background: #f1f5f9; padding: 12px; border-radius: 8px; }
.info-item { display: flex; flex-direction: column; font-size: 12px; }
.info-label { color: #64748b; font-size: 11px; }
.info-value { font-weight: 600; color: #0f172a; }

.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; width: fit-content; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f1f5f9; color: #64748b; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: #fff; color: #334155; padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; cursor: pointer; }
.btn-outline:hover { background: #f8fafc; }
.btn-sm { padding: 4px 10px; font-size: 12px; }

.text-success { color: #16a34a; }
.text-muted { color: #64748b; }
.font-mono { font-family: monospace; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .pod-grid { grid-template-columns: 1fr; }
  .form-grid-2 { grid-template-columns: 1fr; }
}
</style>

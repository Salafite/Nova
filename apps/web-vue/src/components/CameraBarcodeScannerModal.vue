<template>
  <Teleport to="body">
    <div v-if="isVisible" class="scanner-modal-overlay" @click.self="handleClose">
      <div class="scanner-modal-container" :dir="dir">
        <!-- Modal Header -->
        <div class="scanner-modal-header">
          <div class="header-title">
            <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" />
              <rect x="7" y="7" width="10" height="10" rx="1" />
            </svg>
            <span>{{ title || t('scan-barcode', 'Scan Barcode') }}</span>
          </div>
          <button class="btn-close" @click="handleClose" aria-label="Close modal">
            &times;
          </button>
        </div>

        <!-- Camera Viewport Section -->
        <div class="scanner-viewport-wrapper">
          <video
            ref="videoRef"
            class="scanner-video"
            autoplay
            playsinline
            muted
          ></video>

          <!-- Reticle / Target Box Overlay -->
          <div class="scanner-reticle" :class="{ 'scan-success': isFlashActive }">
            <div class="reticle-corner top-left"></div>
            <div class="reticle-corner top-right"></div>
            <div class="reticle-corner bottom-left"></div>
            <div class="reticle-corner bottom-right"></div>
            <div class="scanner-laser-line"></div>
          </div>

          <!-- Camera Loading / Permission Error Overlay -->
          <div v-if="cameraError" class="scanner-status-overlay error">
            <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p>{{ cameraError }}</p>
            <button class="btn-retry" @click="startCamera">
              {{ t('retry-camera', 'Retry Camera') }}
            </button>
          </div>

          <div v-else-if="isLoading" class="scanner-status-overlay loading">
            <div class="spinner"></div>
            <p>{{ t('starting-camera', 'Initializing camera...') }}</p>
          </div>

          <!-- Top Toolbar: Torch & Camera Selector -->
          <div class="scanner-controls-top">
            <button
              v-if="hasTorch"
              class="btn-control-icon"
              :class="{ active: isTorchOn }"
              @click="toggleTorch"
              :title="t('toggle-flashlight', 'Toggle Flashlight')"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
              </svg>
            </button>

            <select
              v-if="videoDevices.length > 1"
              v-model="selectedDeviceId"
              class="camera-select"
              @change="onDeviceChange"
            >
              <option
                v-for="device in videoDevices"
                :key="device.deviceId"
                :value="device.deviceId"
              >
                {{ device.label || `Camera ${videoDevices.indexOf(device) + 1}` }}
              </option>
            </select>
          </div>
        </div>

        <!-- Modal Footer: Manual Entry & Scanned History Preview -->
        <div class="scanner-modal-footer">
          <div class="manual-input-group">
            <input
              type="text"
              v-model="manualBarcode"
              class="manual-input"
              :placeholder="t('enter-barcode-manually', 'Or enter barcode manually...')"
              @keyup.enter="handleManualSubmit"
            />
            <button class="btn-manual-submit" @click="handleManualSubmit">
              {{ t('submit', 'Submit') }}
            </button>
          </div>

          <p v-if="lastScannedBarcode" class="last-scanned-notice">
            {{ t('last-scanned', 'Last Scanned') }}: <strong>{{ lastScannedBarcode }}</strong>
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { parseBarcode } from '../utils/barcodeParser.js'
import { useScanFeedback } from '../composables/useScanFeedback.js'
import { useI18n } from '../composables/useI18n.js'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  show: { type: Boolean, default: false },
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  continuous: { type: Boolean, default: false },
  scanCooldownMs: { type: Number, default: 1500 }
})

const emit = defineEmits([
  'scan',
  'close',
  'update:isOpen',
  'update:show',
  'update:modelValue',
  'cancel'
])

const { t, dir } = useI18n()
const feedback = useScanFeedback()

// Internal reactive state
const videoRef = ref(null)
const isLoading = ref(false)
const cameraError = ref(null)
const videoDevices = ref([])
const selectedDeviceId = ref('')
const isTorchOn = ref(false)
const hasTorch = ref(false)
const manualBarcode = ref('')
const lastScannedBarcode = ref('')
const isFlashActive = ref(false)

let mediaStream = null
let videoTrack = null
let animationFrameId = null
let barcodeDetector = null
let lastScanTime = 0

// Computed property to support v-model, :is-open, or :show prop binding
const isVisible = computed(() => {
  return props.isOpen || props.show || props.modelValue
})

/**
 * Initializes and starts camera stream
 */
async function startCamera() {
  stopCamera()
  cameraError.value = null
  isLoading.value = true

  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    cameraError.value = t('camera-not-supported', 'Camera access is not supported on this browser/device.')
    isLoading.value = false
    return
  }

  try {
    await enumerateCameras()

    const constraints = {
      video: selectedDeviceId.value
        ? { deviceId: { exact: selectedDeviceId.value } }
        : { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }
    }

    mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
    videoTrack = mediaStream && typeof mediaStream.getVideoTracks === 'function' ? (mediaStream.getVideoTracks()[0] || null) : null

    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      await videoRef.value.play().catch(() => {})
    }

    // Check torch / flash capability
    if (videoTrack && typeof videoTrack.getCapabilities === 'function') {
      const caps = videoTrack.getCapabilities()
      hasTorch.value = !!caps.torch
    } else {
      hasTorch.value = false
    }

    isLoading.value = false

    // Initialize BarcodeDetector API if supported
    if (typeof window !== 'undefined' && 'BarcodeDetector' in window) {
      try {
        const supportedFormats = await window.BarcodeDetector.getSupportedFormats()
        barcodeDetector = new window.BarcodeDetector({
          formats: supportedFormats.length ? supportedFormats : ['ean_13', 'upc_a', 'code_128', 'qr_code']
        })
      } catch (e) {
        barcodeDetector = null
      }
    }

    startScanningLoop()
  } catch (err) {
    console.error('[CameraBarcodeScannerModal] Camera error:', err)
    isLoading.value = false
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      cameraError.value = t('camera-permission-denied', 'Camera permission denied. Please grant permission in browser settings.')
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      cameraError.value = t('no-camera-found', 'No camera device found on this system.')
    } else {
      cameraError.value = t('camera-init-failed', 'Failed to start camera. Please enter barcode manually.')
    }
  }
}

/**
 * Enumerates connected video devices
 */
async function enumerateCameras() {
  try {
    if (!navigator.mediaDevices?.enumerateDevices) return
    const devices = await navigator.mediaDevices.enumerateDevices()
    const videoInputs = devices.filter((d) => d.kind === 'videoinput')
    videoDevices.value = videoInputs

    if (videoInputs.length > 0 && !selectedDeviceId.value) {
      // Default to rear camera if present
      const backCamera = videoInputs.find((d) => d.label.toLowerCase().includes('back') || d.label.toLowerCase().includes('rear'))
      selectedDeviceId.value = backCamera ? backCamera.deviceId : videoInputs[0].deviceId
    }
  } catch (e) {
    console.warn('[CameraBarcodeScannerModal] Camera enumeration failed:', e)
  }
}

/**
 * Handles device selection change
 */
function onDeviceChange() {
  startCamera()
}

/**
 * Toggles camera torch / flashlight
 */
async function toggleTorch() {
  if (!videoTrack || !hasTorch.value) return
  try {
    isTorchOn.value = !isTorchOn.value
    await videoTrack.applyConstraints({
      advanced: [{ torch: isTorchOn.value }]
    })
  } catch (e) {
    console.warn('[CameraBarcodeScannerModal] Torch toggle failed:', e)
  }
}

/**
 * Main detection loop powered by BarcodeDetector API or video frame inspection
 */
function startScanningLoop() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  const loop = async () => {
    if (!isVisible.value || !videoRef.value || videoRef.value.readyState < 2) {
      if (isVisible.value) {
        animationFrameId = requestAnimationFrame(loop)
      }
      return
    }

    const now = Date.now()

    if (barcodeDetector && now - lastScanTime > props.scanCooldownMs) {
      try {
        const barcodes = await barcodeDetector.detect(videoRef.value)
        if (barcodes && barcodes.length > 0) {
          const rawCode = barcodes[0].rawValue
          if (rawCode) {
            handleScannedBarcode(rawCode)
          }
        }
      } catch (e) {
        // Ignore single-frame detection errors
      }
    }

    if (isVisible.value) {
      animationFrameId = requestAnimationFrame(loop)
    }
  }

  animationFrameId = requestAnimationFrame(loop)
}

/**
 * Processes a valid barcode scan (from camera detection or manual entry)
 */
function handleScannedBarcode(rawCode) {
  if (!rawCode) return
  lastScanTime = Date.now()
  lastScannedBarcode.value = rawCode

  const parsed = parseBarcode(rawCode)

  // Visual success flash on reticle
  isFlashActive.value = true
  setTimeout(() => {
    isFlashActive.value = false
  }, 400)

  // Audio confirmation
  feedback.playSuccessSound()

  // Emit scan event
  emit('scan', parsed, rawCode)

  if (!props.continuous) {
    handleClose()
  }
}

/**
 * Handles manual barcode text input submission
 */
function handleManualSubmit() {
  const code = manualBarcode.value.trim()
  if (!code) return
  manualBarcode.value = ''
  handleScannedBarcode(code)
}

/**
 * Stops camera stream and cleans up resources
 */
function stopCamera() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  videoTrack = null
  isTorchOn.value = false
  isLoading.value = false
}

/**
 * Closes modal and emits close events
 */
function handleClose() {
  stopCamera()
  emit('close')
  emit('cancel')
  emit('update:isOpen', false)
  emit('update:show', false)
  emit('update:modelValue', false)
}

// Watch modal visibility to start/stop camera stream dynamically
watch(
  isVisible,
  (newVal) => {
    if (newVal) {
      nextTick(() => {
        startCamera()
      })
    } else {
      stopCamera()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  stopCamera()
})
</script>

<style scoped>
.scanner-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 16px;
}

.scanner-modal-container {
  background: #1e293b;
  color: #f8fafc;
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

/* Header */
.scanner-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #0f172a;
  border-bottom: 1px solid #334155;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}

.header-icon {
  width: 22px;
  height: 22px;
  color: #38bdf8;
}

.btn-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.btn-close:hover {
  color: #ffffff;
  background: #334155;
}

/* Viewport Area */
.scanner-viewport-wrapper {
  position: relative;
  width: 100%;
  height: 320px;
  background: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.scanner-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Reticle Target Box */
.scanner-reticle {
  position: absolute;
  width: 240px;
  height: 160px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 0 0 4000px rgba(0, 0, 0, 0.45);
  pointer-events: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.scanner-reticle.scan-success {
  border-color: #22c55e;
  box-shadow: 0 0 0 4000px rgba(34, 197, 94, 0.2);
}

.reticle-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: #38bdf8;
  border-style: solid;
}

.scanner-reticle.scan-success .reticle-corner {
  border-color: #22c55e;
}

.top-left {
  top: -2px;
  left: -2px;
  border-width: 3px 0 0 3px;
  border-top-left-radius: 10px;
}

.top-right {
  top: -2px;
  right: -2px;
  border-width: 3px 3px 0 0;
  border-top-right-radius: 10px;
}

.bottom-left {
  bottom: -2px;
  left: -2px;
  border-width: 0 0 3px 3px;
  border-bottom-left-radius: 10px;
}

.bottom-right {
  bottom: -2px;
  right: -2px;
  border-width: 0 3px 3px 0;
  border-bottom-right-radius: 10px;
}

.scanner-laser-line {
  position: absolute;
  top: 10px;
  left: 10px;
  right: 10px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ef4444, transparent);
  box-shadow: 0 0 8px #ef4444;
  animation: scan-animate 2s infinite ease-in-out;
}

@keyframes scan-animate {
  0% { top: 10px; }
  50% { top: calc(100% - 12px); }
  100% { top: 10px; }
}

/* Status Overlays */
.scanner-status-overlay {
  position: absolute;
  inset: 0;
  background: #0f172a;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
  z-index: 10;
}

.scanner-status-overlay.error {
  color: #f87171;
}

.status-icon {
  width: 40px;
  height: 40px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  border-top-color: #38bdf8;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-retry {
  padding: 8px 16px;
  background: #0284c7;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-retry:hover {
  background: #0369a1;
}

/* Top Toolbar Controls */
.scanner-controls-top {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 5;
}

.btn-control-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: background 0.15s, border-color 0.15s;
}

.btn-control-icon svg {
  width: 18px;
  height: 18px;
}

.btn-control-icon.active {
  background: #eab308;
  color: #0f172a;
  border-color: #fde047;
}

.camera-select {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f1f5f9;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  backdrop-filter: blur(4px);
  outline: none;
}

/* Footer Section */
.scanner-modal-footer {
  padding: 16px 20px;
  background: #0f172a;
  border-top: 1px solid #334155;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.manual-input-group {
  display: flex;
  gap: 8px;
}

.manual-input {
  flex: 1;
  background: #1e293b;
  border: 1px solid #475569;
  border-radius: 8px;
  padding: 10px 14px;
  color: #f8fafc;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}

.manual-input:focus {
  border-color: #38bdf8;
}

.btn-manual-submit {
  padding: 10px 18px;
  background: #0284c7;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-manual-submit:hover {
  background: #0369a1;
}

.last-scanned-notice {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
  text-align: center;
}

.last-scanned-notice strong {
  color: #38bdf8;
  font-family: monospace;
}
</style>

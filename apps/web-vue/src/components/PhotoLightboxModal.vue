<template>
  <div v-if="show" class="lightbox-overlay" @click.self="emitClose" @keydown.esc="emitClose" tabindex="0" ref="overlayRef">
    <div class="lightbox-container">
      <!-- Top Action Bar -->
      <div class="lightbox-header">
        <div class="lightbox-title-wrap">
          <span class="material-symbols-outlined icon-photo">photo_camera</span>
          <div class="photo-meta">
            <span class="photo-title">{{ currentPhoto?.filename || currentPhoto?.description || t('inspection-photo', 'Inspection Photo') }}</span>
            <span class="photo-counter" v-if="photos.length > 1">{{ currentIndex + 1 }} / {{ photos.length }}</span>
          </div>
        </div>

        <div class="lightbox-actions">
          <button type="button" class="btn-ctrl" @click="zoomOut" :disabled="zoomLevel <= 0.5" :title="t('zoom-out', 'Zoom Out')">
            <span class="material-symbols-outlined">zoom_out</span>
          </button>
          <button type="button" class="btn-ctrl" @click="resetZoom" :title="t('reset-zoom', 'Reset Zoom')">
            <span class="material-symbols-outlined">restart_alt</span>
            <span class="zoom-pct">{{ Math.round(zoomLevel * 100) }}%</span>
          </button>
          <button type="button" class="btn-ctrl" @click="zoomIn" :disabled="zoomLevel >= 3" :title="t('zoom-in', 'Zoom In')">
            <span class="material-symbols-outlined">zoom_in</span>
          </button>
          <a
            v-if="currentPhotoSrc"
            :href="currentPhotoSrc"
            :download="currentPhoto?.filename || 'rma_evidence_photo.jpg'"
            class="btn-ctrl"
            :title="t('download-photo', 'Download Photo')"
            target="_blank"
          >
            <span class="material-symbols-outlined">download</span>
          </a>
          <button type="button" class="btn-ctrl btn-close" @click="emitClose" :title="t('close', 'Close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
      </div>

      <!-- Main Image Viewport -->
      <div class="lightbox-body" @wheel.prevent="onWheel">
        <!-- Prev Button -->
        <button
          v-if="photos.length > 1"
          type="button"
          class="nav-btn nav-prev"
          :disabled="currentIndex === 0"
          @click="prevPhoto"
          :title="t('previous', 'Previous Photo')"
        >
          <span class="material-symbols-outlined">chevron_left</span>
        </button>

        <div class="image-stage">
          <img
            v-if="currentPhotoSrc"
            :src="currentPhotoSrc"
            :alt="currentPhoto?.filename || 'Inspection Evidence'"
            class="lightbox-image"
            :style="{ transform: `scale(${zoomLevel})` }"
          />
          <div v-else class="image-missing">
            <span class="material-symbols-outlined icon-missing">broken_image</span>
            <p>{{ t('no-image-data', 'Unable to display photo image data') }}</p>
          </div>
        </div>

        <!-- Next Button -->
        <button
          v-if="photos.length > 1"
          type="button"
          class="nav-btn nav-next"
          :disabled="currentIndex === photos.length - 1"
          @click="nextPhoto"
          :title="t('next', 'Next Photo')"
        >
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>

      <!-- Photo Caption & Details Footer -->
      <div class="lightbox-footer" v-if="currentPhoto?.description || currentPhoto?.notes">
        <div class="caption-box">
          <span class="material-symbols-outlined caption-icon">info</span>
          <span class="caption-text">{{ currentPhoto.description || currentPhoto.notes }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from '../composables/useI18n.js'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  photos: {
    type: Array,
    default: () => [],
  },
  initialIndex: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['close'])
const { t } = useI18n()

const overlayRef = ref(null)
const currentIndex = ref(0)
const zoomLevel = ref(1)

watch(
  () => props.show,
  (val) => {
    if (val) {
      currentIndex.value = Math.max(0, Math.min(props.initialIndex, props.photos.length - 1))
      zoomLevel.value = 1
      nextTick(() => {
        if (overlayRef.value) {
          overlayRef.value.focus()
        }
      })
    }
  }
)

watch(
  () => props.initialIndex,
  (val) => {
    currentIndex.value = Math.max(0, Math.min(val, props.photos.length - 1))
    zoomLevel.value = 1
  }
)

const currentPhoto = computed(() => {
  if (!props.photos || !props.photos.length) return null
  return props.photos[currentIndex.value] || null
})

const currentPhotoSrc = computed(() => {
  const p = currentPhoto.value
  if (!p) return ''
  if (p.url) return p.url
  if (p.thumbnail_url) return p.thumbnail_url
  if (p.data_base64) {
    const mime = p.content_type || 'image/jpeg'
    return `data:${mime};base64,${p.data_base64}`
  }
  return ''
})

function prevPhoto() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    zoomLevel.value = 1
  }
}

function nextPhoto() {
  if (currentIndex.value < props.photos.length - 1) {
    currentIndex.value++
    zoomLevel.value = 1
  }
}

function zoomIn() {
  if (zoomLevel.value < 3) {
    zoomLevel.value = Math.min(3, zoomLevel.value + 0.25)
  }
}

function zoomOut() {
  if (zoomLevel.value > 0.5) {
    zoomLevel.value = Math.max(0.5, zoomLevel.value - 0.25)
  }
}

function resetZoom() {
  zoomLevel.value = 1
}

function onWheel(e) {
  if (e.deltaY < 0) {
    zoomIn()
  } else {
    zoomOut()
  }
}

function emitClose() {
  emit('close')
}

function onKeydown(e) {
  if (!props.show) return
  if (e.key === 'Escape') {
    emitClose()
  } else if (e.key === 'ArrowLeft') {
    prevPhoto()
  } else if (e.key === 'ArrowRight') {
    nextPhoto()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 25, 0.88);
  backdrop-filter: blur(6px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

.lightbox-container {
  width: 95vw;
  max-width: 1200px;
  height: 90vh;
  display: flex;
  flex-direction: column;
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.lightbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #1e293b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #f8fafc;
}

.lightbox-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-photo {
  font-size: 24px;
  color: #38bdf8;
}

.photo-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.photo-title {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.photo-counter {
  font-size: 12px;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
  color: #94a3b8;
  font-family: monospace;
}

.lightbox-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-ctrl {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #f1f5f9;
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  transition: all 0.15s;
  text-decoration: none;
}

.btn-ctrl:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  color: #38bdf8;
}

.btn-ctrl:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-close:hover {
  background: #dc2626 !important;
  color: #fff !important;
}

.zoom-pct {
  font-family: monospace;
  font-size: 11px;
}

.lightbox-body {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #020617;
  padding: 20px;
}

.image-stage {
  max-width: 100%;
  max-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.lightbox-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
  border-radius: 4px;
}

.image-missing {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

.icon-missing {
  font-size: 48px;
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f1f5f9;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.15s;
}

.nav-btn:hover:not(:disabled) {
  background: #38bdf8;
  color: #0f172a;
}

.nav-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.nav-prev {
  left: 20px;
}

.nav-next {
  right: 20px;
}

.lightbox-footer {
  background: #1e293b;
  padding: 12px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.caption-box {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-size: 13px;
}

.caption-icon {
  font-size: 18px;
  color: #38bdf8;
  flex-shrink: 0;
}
</style>

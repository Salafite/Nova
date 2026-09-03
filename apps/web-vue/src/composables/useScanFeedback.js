import { ref } from 'vue'
import { useToast } from './useToast.js'

// Lazy initialized Web Audio API context singleton
let audioCtx = null

/**
 * Obtain or initialize the browser AudioContext safely.
 * Handles suspended context resume and fallback for non-browser/unsupported environments.
 */
function getAudioContext() {
  if (typeof window === 'undefined') return null
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) return null

  try {
    if (!audioCtx) {
      audioCtx = new AudioContextClass()
    }
    if (audioCtx.state === 'suspended' && typeof audioCtx.resume === 'function') {
      audioCtx.resume().catch(() => {})
    }
    return audioCtx
  } catch (e) {
    console.warn('[useScanFeedback] AudioContext initialization failed:', e)
    return null
  }
}

// Reactive state shared across scanner views
const soundEnabled = ref(true)
const volume = ref(0.5) // Volume range: 0.0 to 1.0
const flashState = ref(null) // 'success' | 'error' | 'warning' | null
const lastScanResult = ref(null) // { type, message, timestamp }
let flashTimeout = null

/**
 * Composable for audio synthesized feedback and visual notifications during barcode scanning.
 */
export function useScanFeedback() {
  const toast = useToast()

  /**
   * Set flash state briefly for visual UI feedback (e.g., green/red border flash)
   */
  function triggerFlash(type, duration = 1000) {
    if (flashTimeout) clearTimeout(flashTimeout)
    flashState.value = type
    flashTimeout = setTimeout(() => {
      flashState.value = null
    }, duration)
  }

  /**
   * Play synthesized success chime using Web Audio API
   * Ascending 2-tone pleasant chime (C5 523.25Hz -> G5 783.99Hz)
   */
  function playSuccessSound() {
    if (!soundEnabled.value) return
    const ctx = getAudioContext()
    if (!ctx) return

    try {
      const now = ctx.currentTime
      const vol = Math.max(0, Math.min(1, volume.value)) * 0.3 // Normalized gain

      // First tone: C5 (523.25 Hz)
      const osc1 = ctx.createOscillator()
      const gain1 = ctx.createGain()
      osc1.type = 'sine'
      osc1.frequency.setValueAtTime(523.25, now)
      gain1.gain.setValueAtTime(vol, now)
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.12)
      osc1.connect(gain1)
      gain1.connect(ctx.destination)
      osc1.start(now)
      osc1.stop(now + 0.12)

      // Second tone: G5 (783.99 Hz)
      const osc2 = ctx.createOscillator()
      const gain2 = ctx.createGain()
      osc2.type = 'sine'
      osc2.frequency.setValueAtTime(783.99, now + 0.08)
      gain2.gain.setValueAtTime(vol, now + 0.08)
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.25)
      osc2.connect(gain2)
      gain2.connect(ctx.destination)
      osc2.start(now + 0.08)
      osc2.stop(now + 0.25)
    } catch (e) {
      console.warn('[useScanFeedback] playSuccessSound failed:', e)
    }
  }

  /**
   * Play synthesized error buzzer using Web Audio API
   * Low harsh sawtooth dual-pulse buzzer (150Hz / 130Hz)
   */
  function playErrorSound() {
    if (!soundEnabled.value) return
    const ctx = getAudioContext()
    if (!ctx) return

    try {
      const now = ctx.currentTime
      const vol = Math.max(0, Math.min(1, volume.value)) * 0.4

      // Pulse 1: 150 Hz sawtooth
      const osc1 = ctx.createOscillator()
      const gain1 = ctx.createGain()
      osc1.type = 'sawtooth'
      osc1.frequency.setValueAtTime(150, now)
      gain1.gain.setValueAtTime(vol, now)
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.15)
      osc1.connect(gain1)
      gain1.connect(ctx.destination)
      osc1.start(now)
      osc1.stop(now + 0.15)

      // Pulse 2: 130 Hz sawtooth
      const osc2 = ctx.createOscillator()
      const gain2 = ctx.createGain()
      osc2.type = 'sawtooth'
      osc2.frequency.setValueAtTime(130, now + 0.18)
      gain2.gain.setValueAtTime(vol, now + 0.18)
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.35)
      osc2.connect(gain2)
      gain2.connect(ctx.destination)
      osc2.start(now + 0.18)
      osc2.stop(now + 0.35)
    } catch (e) {
      console.warn('[useScanFeedback] playErrorSound failed:', e)
    }
  }

  /**
   * Play synthesized warning beep using Web Audio API
   * Mid-range triangle wave beep (440Hz)
   */
  function playWarningSound() {
    if (!soundEnabled.value) return
    const ctx = getAudioContext()
    if (!ctx) return

    try {
      const now = ctx.currentTime
      const vol = Math.max(0, Math.min(1, volume.value)) * 0.3

      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(440, now)
      gain.gain.setValueAtTime(vol, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.2)
    } catch (e) {
      console.warn('[useScanFeedback] playWarningSound failed:', e)
    }
  }

  /**
   * Trigger success audio chime + visual flash + toast notification
   */
  function notifySuccess(message = 'Scan successful') {
    playSuccessSound()
    triggerFlash('success')
    toast.show(message, 'success')
    lastScanResult.value = { type: 'success', message, timestamp: Date.now() }
  }

  /**
   * Trigger error audio buzzer + visual error flash + toast notification
   */
  function notifyError(message = 'Scan error / mismatch') {
    playErrorSound()
    triggerFlash('error')
    toast.show(message, 'error')
    lastScanResult.value = { type: 'error', message, timestamp: Date.now() }
  }

  /**
   * Trigger warning audio beep + visual warning flash + toast notification
   */
  function notifyWarning(message = 'Scan warning') {
    playWarningSound()
    triggerFlash('warning')
    toast.show(message, 'warning')
    lastScanResult.value = { type: 'warning', message, timestamp: Date.now() }
  }

  return {
    soundEnabled,
    volume,
    flashState,
    lastScanResult,
    playSuccessSound,
    playErrorSound,
    playWarningSound,
    notifySuccess,
    notifyError,
    notifyWarning,
    getAudioContext,
    resetAudioContext: () => { audioCtx = null }
  }
}


import { ref, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import { parseBarcode } from '../utils/barcodeParser.js'

/**
 * Hardware USB / Bluetooth Barcode Scanner Listener Composable
 *
 * Captures HID keyboard barcode scanner inputs with high-speed keystroke buffering
 * and inter-character timing detection. Distinguishes automated scanner bursts from
 * slow human typing.
 *
 * @param {Object} options Configuration options
 * @param {Function} [options.onScan] Callback function invoked when valid barcode is scanned: (parsedBarcode, rawString, event)
 * @param {number} [options.maxInterval=50] Max allowed interval (ms) between consecutive keystrokes for scanner burst
 * @param {number} [options.minLength=3] Minimum length of buffered string to qualify as a barcode scan
 * @param {Array<string>} [options.endKeys=['Enter']] Key identifiers that signal the end of a scan
 * @param {boolean} [options.preventDefault=true] Prevent default browser behavior on scanner completion key
 * @param {boolean} [options.stopPropagation=false] Stop propagation on scanner completion key
 * @param {boolean} [options.ignoreInputs=false] If true, ignore scanning events when typing inside form inputs unless rapid timing is detected
 * @param {boolean} [options.autoParse=true] Auto-parse raw barcode string into structured data via parseBarcode()
 * @param {EventTarget|Window} [options.target] Element to attach listener to (defaults to window)
 * @param {boolean} [options.autoStart=true] Auto-attach listener on mount
 *
 * @returns {Object} Reactive scanner state and control functions
 */
export function useBarcodeScanner(options = {}) {
  const {
    onScan = null,
    maxInterval = 50,
    minLength = 3,
    endKeys = ['Enter'],
    preventDefault = true,
    stopPropagation = false,
    ignoreInputs = false,
    autoParse = true,
    target = null,
    autoStart = true
  } = options

  // Reactive state
  const buffer = ref('')
  const lastScanned = ref(null)
  const isScanning = ref(false)
  const isEnabled = ref(true)
  const scanHistory = ref([])

  // Internal timing variables
  let lastKeyTime = 0
  let bufferTimeout = null
  let pendingInputKey = null
  let isListening = false
  let resolvedTarget = null

  /**
   * Clears current keystroke buffer and resets scanning flags.
   */
  function clearBuffer() {
    buffer.value = ''
    isScanning.value = false
    lastKeyTime = 0
    pendingInputKey = null
    if (bufferTimeout) {
      clearTimeout(bufferTimeout)
      bufferTimeout = null
    }
  }

  /**
   * Checks if an event target is an editable form input element.
   * @param {EventTarget} el
   * @returns {boolean}
   */
  function isEditableElement(el) {
    if (!el || !(el instanceof HTMLElement)) return false
    const tagName = el.tagName.toUpperCase()
    return (
      tagName === 'INPUT' ||
      tagName === 'TEXTAREA' ||
      tagName === 'SELECT' ||
      el.isContentEditable
    )
  }

  /**
   * Main Keydown Handler
   * @param {KeyboardEvent} event
   */
  function handleKeyDown(event) {
    if (!isEnabled.value) return

    const targetEl = event.target
    const isTargetInput = isEditableElement(targetEl)

    const now = Date.now()
    const timeDiff = lastKeyTime ? now - lastKeyTime : 0

    // If ignoreInputs is enabled and user is typing in an input:
    if (ignoreInputs && isTargetInput) {
      if (!lastKeyTime) {
        // First keypress in input -> save as candidate pendingInputKey
        if (event.key.length === 1 && !endKeys.includes(event.key)) {
          pendingInputKey = event.key
          lastKeyTime = now
        }
        return
      }

      if (timeDiff > maxInterval) {
        // Slow typing in input -> human typing, ignore
        clearBuffer()
        return
      }

      // Rapid keypress in input -> promote pendingInputKey to buffer if present
      if (pendingInputKey) {
        buffer.value = pendingInputKey
        pendingInputKey = null
      }
    }

    // Check if key is a scan terminator (e.g., 'Enter')
    if (endKeys.includes(event.key)) {
      if (buffer.value.length >= minLength) {
        const rawString = buffer.value
        const parsed = autoParse ? parseBarcode(rawString) : { raw: rawString, code: rawString, isValid: true }
        const scanResult = {
          raw: rawString,
          parsed,
          timestamp: Date.now()
        }

        lastScanned.value = scanResult
        scanHistory.value.unshift(scanResult)

        if (preventDefault) {
          event.preventDefault()
        }
        if (stopPropagation) {
          event.stopPropagation()
        }

        if (typeof onScan === 'function') {
          onScan(parsed, rawString, event)
        }

        clearBuffer()
        return
      } else {
        // Terminator pressed but buffer is too short, reset buffer
        clearBuffer()
        return
      }
    }

    // Ignore non-printable modifier / control keys (Shift, Ctrl, Alt, Meta, CapsLock, Tab, etc. unless Tab is an endKey)
    if (event.key.length > 1) {
      return
    }

    // Keystroke timing evaluation
    if (lastKeyTime && timeDiff > maxInterval) {
      // Time between keys exceeded maxInterval threshold -> clear buffer and start fresh with current key
      buffer.value = event.key
    } else {
      // Rapid keystroke -> append to buffer
      buffer.value += event.key
    }

    lastKeyTime = now
    isScanning.value = buffer.value.length > 0

    // Auto-clear buffer after inactivity period (3x maxInterval or minimum 200ms)
    if (bufferTimeout) clearTimeout(bufferTimeout)
    bufferTimeout = setTimeout(() => {
      clearBuffer()
    }, Math.max(maxInterval * 4, 250))
  }

  /**
   * Attaches the keydown event listener to target.
   */
  function startListening() {
    if (isListening) return
    resolvedTarget = target || (typeof window !== 'undefined' ? window : null)
    if (resolvedTarget && typeof resolvedTarget.addEventListener === 'function') {
      resolvedTarget.addEventListener('keydown', handleKeyDown, true)
      isListening = true
    }
  }

  /**
   * Detaches the keydown event listener.
   */
  function stopListening() {
    if (!isListening) return
    if (resolvedTarget && typeof resolvedTarget.removeEventListener === 'function') {
      resolvedTarget.removeEventListener('keydown', handleKeyDown, true)
    }
    isListening = false
    clearBuffer()
  }

  /**
   * Helper function to manually simulate a scanner input (useful for testing or manual triggers)
   * @param {string} rawString Barcode string to process
   */
  function simulateScan(rawString) {
    if (!rawString || typeof rawString !== 'string') return null
    const parsed = autoParse ? parseBarcode(rawString) : { raw: rawString, code: rawString, isValid: true }
    const scanResult = {
      raw: rawString,
      parsed,
      timestamp: Date.now()
    }
    lastScanned.value = scanResult
    scanHistory.value.unshift(scanResult)
    if (typeof onScan === 'function') {
      onScan(parsed, rawString, null)
    }
    return scanResult
  }

  // Vue lifecycle hooks integration & auto-start handling
  if (getCurrentInstance()) {
    onMounted(() => {
      if (autoStart) {
        startListening()
      }
    })
    onUnmounted(() => {
      stopListening()
    })
  } else if (autoStart) {
    startListening()
  }

  return {
    buffer,
    lastScanned,
    isScanning,
    isEnabled,
    scanHistory,
    startListening,
    stopListening,
    clearBuffer,
    simulateScan,
    handleKeyDown
  }
}

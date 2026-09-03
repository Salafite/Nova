import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useBarcodeScanner } from '../composables/useBarcodeScanner.js'

describe('useBarcodeScanner composable', () => {
  let targetElement

  beforeEach(() => {
    vi.useFakeTimers()
    targetElement = document.createElement('div')
    document.body.appendChild(targetElement)
  })

  afterEach(() => {
    vi.useRealTimers()
    if (targetElement && targetElement.parentNode) {
      targetElement.parentNode.removeChild(targetElement)
    }
  })

  function dispatchKey(key, target = targetElement) {
    const event = new KeyboardEvent('keydown', {
      key,
      bubbles: true,
      cancelable: true
    })
    target.dispatchEvent(event)
    return event
  }

  it('initializes with default reactive state', () => {
    const scanner = useBarcodeScanner({ target: targetElement, autoStart: false })
    expect(scanner.buffer.value).toBe('')
    expect(scanner.lastScanned.value).toBeNull()
    expect(scanner.isScanning.value).toBe(false)
    expect(scanner.isEnabled.value).toBe(true)
    expect(scanner.scanHistory.value).toEqual([])
  })

  it('buffers rapid keystrokes and completes scan on Enter', () => {
    const onScan = vi.fn()
    const scanner = useBarcodeScanner({
      target: targetElement,
      onScan,
      autoStart: true
    })

    // Simulate rapid barcode typing: 9 7 8 0 1 4 3 0 3 5 0 0 8 (EAN-13)
    const digits = '9780143035008'.split('')
    digits.forEach((digit) => {
      dispatchKey(digit)
      vi.advanceTimersByTime(10) // 10ms between keystrokes (< maxInterval of 50ms)
    })

    expect(scanner.buffer.value).toBe('9780143035008')
    expect(scanner.isScanning.value).toBe(true)

    // Press Enter to complete scan
    dispatchKey('Enter')

    expect(onScan).toHaveBeenCalledTimes(1)
    const [parsed, raw] = onScan.mock.calls[0]
    expect(raw).toBe('9780143035008')
    expect(parsed.type).toBe('EAN-13')
    expect(parsed.isValid).toBe(true)
    expect(scanner.buffer.value).toBe('')
    expect(scanner.isScanning.value).toBe(false)
    expect(scanner.lastScanned.value.raw).toBe('9780143035008')
    expect(scanner.scanHistory.value.length).toBe(1)
  })

  it('resets buffer when timing between keystrokes exceeds maxInterval', () => {
    const onScan = vi.fn()
    const scanner = useBarcodeScanner({
      target: targetElement,
      maxInterval: 50,
      onScan,
      autoStart: true
    })

    // Type 9 7 8 slowly (> 50ms interval)
    dispatchKey('9')
    vi.advanceTimersByTime(100) // 100ms > maxInterval
    expect(scanner.buffer.value).toBe('9')

    dispatchKey('7') // Exceeds interval -> buffer resets to '7'
    expect(scanner.buffer.value).toBe('7')

    dispatchKey('8')
    vi.advanceTimersByTime(10)
    expect(scanner.buffer.value).toBe('78')

    // Press Enter (buffer is '78', length 2 < minLength 3)
    dispatchKey('Enter')

    expect(onScan).not.toHaveBeenCalled()
    expect(scanner.buffer.value).toBe('')
  })

  it('ignores modifier keys like Shift and Control', () => {
    const scanner = useBarcodeScanner({
      target: targetElement,
      autoStart: true
    })

    dispatchKey('Shift')
    dispatchKey('Control')
    dispatchKey('Alt')
    expect(scanner.buffer.value).toBe('')

    dispatchKey('A')
    expect(scanner.buffer.value).toBe('A')
  })

  it('respects isEnabled flag', () => {
    const onScan = vi.fn()
    const scanner = useBarcodeScanner({
      target: targetElement,
      onScan,
      autoStart: true
    })

    scanner.isEnabled.value = false

    dispatchKey('1')
    dispatchKey('2')
    dispatchKey('3')
    dispatchKey('Enter')

    expect(scanner.buffer.value).toBe('')
    expect(onScan).not.toHaveBeenCalled()
  })

  it('supports simulateScan for manual scanning', () => {
    const onScan = vi.fn()
    const scanner = useBarcodeScanner({ onScan, autoStart: false })

    const result = scanner.simulateScan('(01)0036000291452(10)LOT123')

    expect(onScan).toHaveBeenCalledTimes(1)
    expect(result.raw).toBe('(01)0036000291452(10)LOT123')
    expect(result.parsed.type).toBe('GS1-128')
    expect(result.parsed.batchNumber).toBe('LOT123')
    expect(scanner.lastScanned.value.raw).toBe('(01)0036000291452(10)LOT123')
    expect(scanner.scanHistory.value.length).toBe(1)
  })

  it('clears buffer on inactivity timeout', () => {
    const scanner = useBarcodeScanner({
      target: targetElement,
      maxInterval: 50,
      autoStart: true
    })

    dispatchKey('1')
    dispatchKey('2')
    expect(scanner.buffer.value).toBe('12')

    // Wait for inactivity timeout (250ms)
    vi.advanceTimersByTime(300)

    expect(scanner.buffer.value).toBe('')
    expect(scanner.isScanning.value).toBe(false)
  })

  it('ignores input element typing when ignoreInputs is true and typing is slow', () => {
    const inputEl = document.createElement('input')
    document.body.appendChild(inputEl)
    const onScan = vi.fn()

    useBarcodeScanner({
      target: inputEl,
      ignoreInputs: true,
      onScan,
      autoStart: true
    })

    // Simulate slow typing in input field
    dispatchKey('A', inputEl)
    vi.advanceTimersByTime(200)
    dispatchKey('B', inputEl)
    vi.advanceTimersByTime(200)
    dispatchKey('C', inputEl)
    vi.advanceTimersByTime(200)
    dispatchKey('Enter', inputEl)

    expect(onScan).not.toHaveBeenCalled()

    document.body.removeChild(inputEl)
  })

  it('captures scanner input in input element when ignoreInputs is true if keystrokes are rapid', () => {
    const inputEl = document.createElement('input')
    document.body.appendChild(inputEl)
    const onScan = vi.fn()

    useBarcodeScanner({
      target: inputEl,
      ignoreInputs: true,
      onScan,
      autoStart: true
    })

    // Rapid keystrokes inside input element (< 50ms)
    dispatchKey('1', inputEl)
    vi.advanceTimersByTime(10)
    dispatchKey('2', inputEl)
    vi.advanceTimersByTime(10)
    dispatchKey('3', inputEl)
    vi.advanceTimersByTime(10)
    dispatchKey('4', inputEl)
    vi.advanceTimersByTime(10)
    dispatchKey('Enter', inputEl)

    expect(onScan).toHaveBeenCalledTimes(1)
    expect(onScan.mock.calls[0][1]).toBe('1234')

    document.body.removeChild(inputEl)
  })

  it('stops listening when stopListening is called', () => {
    const onScan = vi.fn()
    const scanner = useBarcodeScanner({
      target: targetElement,
      onScan,
      autoStart: true
    })

    scanner.stopListening()

    dispatchKey('1')
    dispatchKey('2')
    dispatchKey('3')
    dispatchKey('Enter')

    expect(onScan).not.toHaveBeenCalled()
  })

  it('supports custom endKeys and autoParse: false', () => {
    const onScan = vi.fn()
    useBarcodeScanner({
      target: targetElement,
      endKeys: ['Tab'],
      autoParse: false,
      onScan,
      autoStart: true
    })

    dispatchKey('A')
    vi.advanceTimersByTime(10)
    dispatchKey('B')
    vi.advanceTimersByTime(10)
    dispatchKey('C')
    vi.advanceTimersByTime(10)
    dispatchKey('Tab')

    expect(onScan).toHaveBeenCalledTimes(1)
    const [parsed, raw] = onScan.mock.calls[0]
    expect(raw).toBe('ABC')
    expect(parsed).toEqual({ raw: 'ABC', code: 'ABC', isValid: true })
  })
})

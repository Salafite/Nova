import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useScanFeedback } from '../composables/useScanFeedback.js'

describe('useScanFeedback composable', () => {
  let mockOscillator
  let mockGain
  let mockAudioCtx

  beforeEach(() => {
    mockOscillator = {
      type: 'sine',
      frequency: { setValueAtTime: vi.fn() },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn()
    }

    mockGain = {
      gain: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn()
      },
      connect: vi.fn()
    }

    mockAudioCtx = {
      currentTime: 0,
      state: 'running',
      destination: {},
      createOscillator: vi.fn().mockImplementation(() => mockOscillator),
      createGain: vi.fn().mockImplementation(() => mockGain),
      resume: vi.fn().mockResolvedValue()
    }

    function MockAudioContext() {
      return mockAudioCtx
    }

    global.window.AudioContext = MockAudioContext

    const feedback = useScanFeedback()
    feedback.resetAudioContext()
    feedback.soundEnabled.value = true
    feedback.volume.value = 0.5
    feedback.flashState.value = null
  })

  it('initializes with default values', () => {
    const feedback = useScanFeedback()
    expect(feedback.soundEnabled.value).toBe(true)
    expect(feedback.volume.value).toBe(0.5)
    expect(feedback.flashState.value).toBe(null)
  })

  it('triggers success notification with audio chime and toast', () => {
    const feedback = useScanFeedback()
    feedback.notifySuccess('Item scanned')

    expect(mockAudioCtx.createOscillator).toHaveBeenCalled()
    expect(mockAudioCtx.createGain).toHaveBeenCalled()
    expect(feedback.flashState.value).toBe('success')
    expect(feedback.lastScanResult.value).toEqual(
      expect.objectContaining({
        type: 'success',
        message: 'Item scanned'
      })
    )
  })

  it('triggers error notification with audio buzzer and toast', () => {
    const feedback = useScanFeedback()
    feedback.notifyError('Barcode mismatch')

    expect(mockAudioCtx.createOscillator).toHaveBeenCalled()
    expect(mockOscillator.type).toBe('sawtooth')
    expect(feedback.flashState.value).toBe('error')
    expect(feedback.lastScanResult.value).toEqual(
      expect.objectContaining({
        type: 'error',
        message: 'Barcode mismatch'
      })
    )
  })

  it('triggers warning notification', () => {
    const feedback = useScanFeedback()
    feedback.notifyWarning('Low stock warning')

    expect(mockAudioCtx.createOscillator).toHaveBeenCalled()
    expect(mockOscillator.type).toBe('triangle')
    expect(feedback.flashState.value).toBe('warning')
  })

  it('does not play audio when sound is disabled', () => {
    const feedback = useScanFeedback()
    feedback.soundEnabled.value = false
    mockAudioCtx.createOscillator.mockClear()

    feedback.playSuccessSound()
    expect(mockAudioCtx.createOscillator).not.toHaveBeenCalled()
  })
})

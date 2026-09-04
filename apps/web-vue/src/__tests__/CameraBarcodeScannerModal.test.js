import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CameraBarcodeScannerModal from '../components/CameraBarcodeScannerModal.vue'

describe('CameraBarcodeScannerModal.vue', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)

    // Mock navigator.mediaDevices if not present in jsdom
    if (!navigator.mediaDevices) {
      Object.defineProperty(navigator, 'mediaDevices', {
        value: {
          getUserMedia: vi.fn(),
          enumerateDevices: vi.fn().mockResolvedValue([])
        },
        writable: true,
        configurable: true
      })
    }
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders modal when isOpen is true', () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    expect(wrapper.find('.scanner-modal-overlay').exists()).toBe(true)
    expect(wrapper.find('.header-title').text()).toContain('Scan Barcode')
  })

  it('does not render modal when isOpen is false', () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: false },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    expect(wrapper.find('.scanner-modal-overlay').exists()).toBe(false)
  })

  it('renders custom title when title prop is provided', () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true, title: 'Pick Item Verification' },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    expect(wrapper.find('.header-title').text()).toContain('Pick Item Verification')
  })

  it('emits close, cancel, and update events on clicking close button', async () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    const closeBtn = wrapper.find('.btn-close')
    await closeBtn.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('update:isOpen')?.[0]).toEqual([false])
  })

  it('handles manual barcode submission and emits scan event', async () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    const input = wrapper.find('.manual-input')
    await input.setValue('010061414100003610BATCH123')

    const submitBtn = wrapper.find('.btn-manual-submit')
    await submitBtn.trigger('click')

    expect(wrapper.emitted('scan')).toBeTruthy()
    const scanArgs = wrapper.emitted('scan')[0]
    // scanArgs: [parsedBarcode, rawString]
    expect(scanArgs[1]).toBe('010061414100003610BATCH123')
    expect(scanArgs[0].type).toBe('GS1-128')
    expect(scanArgs[0].batchNumber).toBe('BATCH123')
  })

  it('submits manual barcode on pressing Enter in input field', async () => {
    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    const input = wrapper.find('.manual-input')
    await input.setValue('5012345678900')
    await input.trigger('keyup.enter')

    expect(wrapper.emitted('scan')).toBeTruthy()
    const scanArgs = wrapper.emitted('scan')[0]
    expect(scanArgs[1]).toBe('5012345678900')
    expect(scanArgs[0].type).toBe('EAN-13')
  })

  it('displays camera error message if getUserMedia fails or is unsupported', async () => {
    vi.spyOn(navigator.mediaDevices, 'getUserMedia').mockRejectedValue(
      new Error('PermissionDeniedError')
    )

    const wrapper = mount(CameraBarcodeScannerModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true
        }
      }
    })

    // Allow async camera start to complete
    await new Promise((r) => setTimeout(r, 50))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.scanner-status-overlay.error').exists()).toBe(true)
  })
})

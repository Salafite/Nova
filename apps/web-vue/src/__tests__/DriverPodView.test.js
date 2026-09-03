import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import DriverPodView from '../views/mobile/DriverPodView.vue'
import DriverHandoverView from '../views/sales/DriverHandoverView.vue'
import { api } from '../api/client.js'

// Mock api client
vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
  CONFIG: { apiBase: 'http://test.local' },
}))

// Mock router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('Driver POD & COD Mobile View (DriverPodView.vue)', () => {
  let pinia
  let wrapper

  const sampleDeliveries = [
    {
      id: 77,
      delivery_number: 'DEL-2026-001',
      sales_order_id: 101,
      status: 'Shipped',
      payment_status: 'Pending',
      cod_cash_amount: 150.0,
      cod_check_amount: 50.0,
      cod_check_number: 'CHK-12345',
      cod_check_bank: 'National Bank',
      assigned_driver: 'Driver Bob',
    },
    {
      id: 78,
      delivery_number: 'DEL-2026-002',
      sales_order_id: 102,
      status: 'Delivered',
      payment_status: 'Collected',
      cod_cash_amount: 0.0,
      cod_check_amount: 0.0,
      assigned_driver: 'Driver Bob',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    // Default API mocks
    api.get.mockImplementation((url) => {
      if (url.includes('/T0077I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleDeliveries)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockImplementation(() => Promise.resolve({ data: { success: true } }))
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  it('renders driver POD page title and loads delivery list', async () => {
    wrapper = mount(DriverPodView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Proof of Delivery & COD')
    expect(wrapper.text()).toContain('DEL-2026-001')
    expect(wrapper.find('select.form-input').exists()).toBe(true)
  })

  it('displays delivery status and prepopulates COD fields when delivery is selected', async () => {
    wrapper = mount(DriverPodView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('DEL-2026-001')
    expect(wrapper.text()).toContain('Driver Bob')
    expect(wrapper.text()).toContain('Pending')

    const cashInput = wrapper.find('input[type="number"]')
    expect(cashInput.exists()).toBe(true)
    expect(cashInput.element.value).toBe('150')
  })

  it('submits POD recipient signature, photo, location and COD collection details', async () => {
    wrapper = mount(DriverPodView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    // Fill photo URL and location
    const textInputs = wrapper.findAll('input[type="text"]')
    const photoInput = textInputs.find(i => i.attributes('placeholder')?.includes('example.com'))
    const locInput = textInputs.find(i => i.attributes('placeholder')?.includes('Loading Dock'))

    if (photoInput) await photoInput.setValue('https://storage.test/photo.jpg')
    if (locInput) await locInput.setValue('Warehouse Gate 3')

    // Submit button
    const submitBtn = wrapper.find('.btn-primary')
    expect(submitBtn.exists()).toBe(true)

    await submitBtn.trigger('click')
    await flushPromises()

    // Verify POD post endpoint was called
    expect(api.post).toHaveBeenCalledWith(
      '/T0077I/77/pod',
      expect.objectContaining({
        delivery_location: 'Warehouse Gate 3',
        delivery_photo_url: 'https://storage.test/photo.jpg',
      })
    )

    // Verify COD post endpoint was called
    expect(api.post).toHaveBeenCalledWith(
      '/T0077I/77/cod',
      expect.objectContaining({
        cod_cash_amount: 150,
        cod_check_amount: 50,
        payment_status: 'Collected',
      })
    )

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Proof of delivery & COD recorded successfully'),
      'success'
    )
  })
})

describe('Driver Handover Reconciliation View (DriverHandoverView.vue)', () => {
  let pinia
  let wrapper

  const sampleHandoverReport = {
    driver_id: 1,
    delivery_date: '2026-09-03',
    total_deliveries: 3,
    completed_deliveries: 2,
    expected_cash: 250.0,
    expected_check: 100.0,
    deliveries: [
      {
        id: 77,
        delivery_number: 'DEL-2026-001',
        status: 'Delivered',
        payment_status: 'Collected',
        cod_cash_amount: 150.0,
        cod_check_amount: 50.0,
        cod_check_number: 'CHK-001',
        cod_check_bank: 'City Bank'
      },
      {
        id: 78,
        delivery_number: 'DEL-2026-002',
        status: 'Delivered',
        payment_status: 'Collected',
        cod_cash_amount: 100.0,
        cod_check_amount: 50.0,
        cod_check_number: 'CHK-002',
        cod_check_bank: 'Metro Bank'
      }
    ]
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/sales/driver-handover/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleHandoverReport)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockImplementation(() => Promise.resolve({ data: { status: 'Reconciled' } }))
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  it('renders driver handover summary report and expected cash totals', async () => {
    wrapper = mount(DriverHandoverView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Driver EOD Handover Reconciliation')
    expect(wrapper.text()).toContain('Total Deliveries')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('$250.00') // Expected cash
    expect(wrapper.text()).toContain('$100.00') // Expected check
    expect(wrapper.text()).toContain('$350.00') // Total expected
  })

  it('calculates discrepancy warning box when submitted physical cash differs from expected', async () => {
    wrapper = mount(DriverHandoverView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    // Change submitted cash from 250 to 200 (shortage of 50)
    const inputs = wrapper.findAll('input[type="number"]')
    // cashSubmitted input is second number input after driverId
    const cashInput = inputs[1]
    await cashInput.setValue(200)

    expect(wrapper.text()).toContain('Cash Shortage (-)')
    expect(wrapper.text()).toContain('$50.00')
  })

  it('submits driver handover reconciliation endpoint on form click', async () => {
    wrapper = mount(DriverHandoverView, {
      global: { plugins: [pinia] }
    })
    await flushPromises()

    const reconcileBtn = wrapper.find('.btn-reconcile')
    await reconcileBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/sales/driver-handover/reconcile',
      expect.objectContaining({
        driver_id: 1,
        cash_submitted: 250,
        check_submitted: 100,
      })
    )

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Handover reconciled successfully'),
      'success'
    )
  })
})

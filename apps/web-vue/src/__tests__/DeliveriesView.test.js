import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import DeliveriesView from '../views/sales/DeliveriesView.vue'
import { api } from '../api/client.js'

// Mock api
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

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('DeliveriesView (Dual UOM & Catch-Weight Fulfillment)', () => {
  let pinia
  let wrapper

  const sampleDeliveries = [
    {
      id: 1,
      delivery_number: 'DEL-001',
      sales_order_id: 101,
      delivery_date: '2026-08-23',
      warehouse_id: 1,
      status: 'Shipped',
      notes: 'Cold chain shipping',
    }
  ]

  const sampleOrders = [
    {
      id: 101,
      order_number: 'SO-2026-0001',
      is_catch_weight: true,
      warehouse_id: 1,
    }
  ]

  const sampleWarehouses = [{ id: 1, name: 'Cold Warehouse A' }]

  const sampleSalesLines = [
    {
      id: 201,
      sales_order_id: 101,
      product_id: 501,
      nominal_weight: 40.0,
      catch_weight_actual: 41.5,
      is_catch_weight: true,
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0077I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleDeliveries)) })
      }
      if (url.includes('/T0012I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleOrders)) })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: sampleWarehouses })
      }
      if (url.includes('/T0013I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleSalesLines)) })
      }
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(DeliveriesView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders deliveries table with Catch-Weight badge and scale weight summary', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('DEL-001')
    expect(w.text()).toContain('SO-2026-0001')
    expect(w.text()).toContain('Catch-Weight')
    expect(w.text()).toContain('41.50 kg')
    expect(w.text()).toContain('/ 40.00 kg')
    expect(w.text()).toContain('+3.75%')
    expect(w.text()).toContain('Shipped')
  })

  it('displays catch-weight preview box in modal when a catch-weight order is selected', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click New Delivery button
    const addBtn = w.find('.page-header .btn-primary')
    await addBtn.trigger('click')
    await flushPromises()

    // Check modal open
    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Dual UOM Catch-Weight Order')
    expect(w.text()).toContain('Delivering this order finalizes scale weights')
    expect(w.text()).toContain('40.00 kg')
    expect(w.text()).toContain('41.50 kg')
  })
})

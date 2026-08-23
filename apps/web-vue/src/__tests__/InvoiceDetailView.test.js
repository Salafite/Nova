import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import InvoiceDetailView from '../views/finance/InvoiceDetailView.vue'
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
  useRoute: () => ({ params: { id: '1' } }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('InvoiceDetailView (Dual UOM & Catch-Weight)', () => {
  let pinia
  let wrapper

  const sampleInvoice = {
    id: 1,
    invoice_number: 'INV-2026-0001',
    invoice_type: 'Sales',
    partner_id: 10,
    sales_order_id: 101,
    issue_date: '2026-08-23',
    due_date: '2026-09-23',
    total_amount: 207.5,
    status: 'Unpaid',
    notes: 'Catch-weight adjustment: +7.50',
    is_catch_weight: true,
    nominal_total_weight: 40.0,
    actual_total_weight: 41.5,
    weight_adjustment_amount: 7.5,
  }

  const samplePayments = []
  const sampleCustomers = [{ id: 10, name: 'Artisan Cheese Mart' }]
  const sampleBreakdown = {
    invoice_id: 1,
    invoice_number: 'INV-2026-0001',
    is_catch_weight: true,
    nominal_total_weight: 40.0,
    actual_total_weight: 41.5,
    weight_adjustment_amount: 7.5,
    total_amount: 207.5,
    sales_order_id: 101,
    lines: [
      {
        id: 201,
        sales_order_id: 101,
        product_id: 501,
        product_name: 'Gouda Wheels (Nominal 20kg)',
        uom_id: 10,
        qty: 2,
        unit_price: 100.0,
        line_total: 200.0,
        line_number: 1,
        is_catch_weight: true,
        pricing_uom_id: 11,
        unit_price_pricing_uom: 5.0,
        nominal_weight: 40.0,
        catch_weight_actual: 41.5,
        recalculated_total: 207.5,
      }
    ]
  }
  const sampleUOMs = [
    { id: 10, uom_code: 'CS', uom_name: 'Case' },
    { id: 11, uom_code: 'kg', uom_name: 'Kilogram' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0090I/1/catch-weight-breakdown')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleBreakdown)) })
      }
      if (url.includes('/T0090I/1')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoice)) })
      }
      if (url.includes('/T0091I/')) {
        return Promise.resolve({ data: samplePayments })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: sampleCustomers })
      }
      if (url.includes('/T0013I/')) {
        return Promise.resolve({ data: sampleBreakdown.lines })
      }
      if (url.includes('/T0001I/')) {
        return Promise.resolve({ data: sampleUOMs })
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
    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders invoice header with Dual UOM badge and partner details', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('INV-2026-0001')
    expect(w.text()).toContain('Catch-Weight / Dual UOM')
    expect(w.text()).toContain('Artisan Cheese Mart')
    expect(w.text()).toContain('Unpaid')
  })

  it('renders physical scale weight banner and weight adjustment', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Dual UOM Physical Scale Weight Billing')
    expect(w.text()).toContain('+$7.50')
    expect(w.text()).toContain('Nominal: 40.00 kg')
    expect(w.text()).toContain('Actual Weighed: 41.50 kg')
    expect(w.text()).toContain('+3.75%')
  })

  it('renders itemized weighed lines table with pricing rate and actual weight', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Gouda Wheels')
    expect(w.text()).toContain('Catch Weight')
    expect(w.text()).toContain('$5.00')
    expect(w.text()).toContain('/ kg')
    expect(w.text()).toContain('40.00 kg')
    expect(w.text()).toContain('41.50 kg')
    expect(w.text()).toContain('$207.50')
  })
})

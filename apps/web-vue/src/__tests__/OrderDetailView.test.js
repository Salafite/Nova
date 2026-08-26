import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import OrderDetailView from '../views/sales/OrderDetailView.vue'
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
  useRoute: () => ({ params: { id: '101' } }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('OrderDetailView (Dual UOM & Catch-Weight)', () => {
  let pinia
  let wrapper

  const sampleOrder = {
    id: 101,
    order_number: 'SO-2026-0001',
    customer_id: 1,
    warehouse_id: 1,
    subtotal: 207.5,
    tax: 10.38,
    grand_total: 217.88,
    freight_amount: 0,
    discount_amount: 0,
    status: 'Confirmed',
    order_date: '2026-08-23',
    notes: 'Urgent catch-weight delivery',
    is_catch_weight: true,
  }

  const sampleLines = [
    {
      id: 201,
      sales_order_id: 101,
      product_id: 501,
      product_name: 'Cheddar Cheese Block (Nominal 20kg)',
      uom_id: 10,
      qty: 2,
      unit_price: 100.0,
      discount: 0,
      line_total: 200.0,
      line_number: 1,
      is_catch_weight: true,
      pricing_uom_id: 11,
      unit_price_pricing_uom: 5.0,
      nominal_weight: 40.0,
      catch_weight_actual: 41.5,
      recalculated_total: 207.5,
    },
    {
      id: 202,
      sales_order_id: 101,
      product_id: 502,
      product_name: 'Standard Olive Oil Box',
      uom_id: 10,
      qty: 1,
      unit_price: 50.0,
      discount: 0,
      line_total: 50.0,
      line_number: 2,
      is_catch_weight: false,
      pricing_uom_id: null,
      unit_price_pricing_uom: null,
      nominal_weight: null,
      catch_weight_actual: null,
      recalculated_total: null,
    }
  ]

  const sampleCustomers = [{ id: 1, name: 'Gourmet Foods LLC', balance: 500 }]
  const sampleWarehouses = [{ id: 1, name: 'Cold Storage DC' }]
  const sampleUOMs = [
    { id: 10, uom_code: 'CS', uom_name: 'Case' },
    { id: 11, uom_code: 'kg', uom_name: 'Kilogram' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/101')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleOrder)) })
      }
      if (url.includes('/T0013I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleLines)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: sampleCustomers })
      }
      if (url.includes('/T0008I/')) {
        return Promise.resolve({ data: sampleWarehouses })
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
    wrapper = mount(OrderDetailView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders sales order header with Dual UOM badge and customer details', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('SO-2026-0001')
    expect(w.text()).toContain('Confirmed')
    expect(w.text()).toContain('Dual UOM / Catch-Weight')
    expect(w.text()).toContain('Gourmet Foods LLC')
    expect(w.text()).toContain('Cold Storage DC')
  })

  it('renders catch-weight breakdown and weight adjustments in totals card', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Nominal Total Weight')
    expect(w.text()).toContain('40.00 kg')
    expect(w.text()).toContain('Actual Weighed Weight')
    expect(w.text()).toContain('41.50 kg')
    expect(w.text()).toContain('Net Weight Variance')
    expect(w.text()).toContain('+3.75%')
    expect(w.text()).toContain('Catch-Weight Adjustment')
    expect(w.text()).toContain('+$7.50')
    expect(w.text()).toContain('$217.88')
  })

  it('renders order lines table with dual UOM pricing rate, weights, and variance', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Cheddar Cheese Block')
    expect(w.text()).toContain('Catch Weight')
    expect(w.text()).toContain('$5.00')
    expect(w.text()).toContain('/ kg')
    expect(w.text()).toContain('40.00 kg')
    expect(w.text()).toContain('41.50 kg')
    expect(w.text()).toContain('+3.75%')
    expect(w.text()).toContain('$207.50')
  })

  it('allows recalculating catch-weight pricing via action button', async () => {
    api.post.mockResolvedValue({ data: { success: true } })

    const w = createWrapper()
    await flushPromises()

    const recalcBtn = w.find('.btn-cw')
    expect(recalcBtn.exists()).toBe(true)
    await recalcBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0012I/101/recalculate-catch-weight')
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Catch-weight pricing recalculated'), 'success')
  })

  it('renders Credit Hold badge, reason card, and customer credit info when order is on Credit Hold', async () => {
    const holdOrder = {
      ...sampleOrder,
      status: 'Credit Hold',
      hold_reason: 'Order grand total ($217.88) exceeds customer available credit ($100.00)',
    }
    const sampleCreditStatus = {
      customer_id: 1,
      customer_name: 'Gourmet Foods LLC',
      balance: 1400.0,
      credit_limit: 1500.0,
      is_credit_limit_enforced: true,
      available_credit: 100.0,
      credit_limit_exceeded: false,
      has_overdue_invoices: false,
      overdue_invoices_count: 0,
      overdue_invoices_amount: 0.0,
    }

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/101')) return Promise.resolve({ data: holdOrder })
      if (url.includes('/T0013I/')) return Promise.resolve({ data: sampleLines })
      if (url.includes('/T0010I/1/credit-status')) return Promise.resolve({ data: sampleCreditStatus })
      if (url.includes('/T0010I/')) return Promise.resolve({ data: sampleCustomers })
      if (url.includes('/T0008I/')) return Promise.resolve({ data: sampleWarehouses })
      if (url.includes('/T0001I/')) return Promise.resolve({ data: sampleUOMs })
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Credit Hold')
    expect(w.text()).toContain('Order Placed on Financial Credit Hold')
    expect(w.text()).toContain('Order grand total ($217.88) exceeds customer available credit ($100.00)')
    expect(w.text()).toContain('Available Credit')
    expect(w.text()).toContain('$100.00')
    expect(w.text()).toContain('Override Credit Hold')
    expect(w.text()).toContain('Reject Order')
  })

  it('allows financial manager to override credit hold via modal', async () => {
    const holdOrder = {
      ...sampleOrder,
      status: 'Credit Hold',
      hold_reason: 'Customer credit limit exceeded',
    }

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/101')) return Promise.resolve({ data: holdOrder })
      if (url.includes('/T0013I/')) return Promise.resolve({ data: sampleLines })
      if (url.includes('/T0010I/')) return Promise.resolve({ data: sampleCustomers })
      if (url.includes('/T0008I/')) return Promise.resolve({ data: sampleWarehouses })
      if (url.includes('/T0001I/')) return Promise.resolve({ data: sampleUOMs })
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { ...holdOrder, status: 'Confirmed', hold_released_by: 'admin' } })

    const w = createWrapper()
    await flushPromises()

    const overrideBtn = w.find('.btn-override')
    expect(overrideBtn.exists()).toBe(true)
    await overrideBtn.trigger('click')
    await flushPromises()

    // Modal dialog is mounted into document.body via Teleport
    const textarea = document.querySelector('textarea.form-textarea')
    expect(textarea).not.toBeNull()

    // Enter reason
    textarea.value = 'Approved by Financial Manager - wire payment confirmed'
    textarea.dispatchEvent(new Event('input'))
    await flushPromises()

    const confirmReleaseBtn = document.querySelector('.modal-footer .btn-override')
    expect(confirmReleaseBtn).not.toBeNull()
    confirmReleaseBtn.click()
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0012I/101/override-credit-hold', {
      reason: 'Approved by Financial Manager - wire payment confirmed',
      target_status: 'Confirmed',
    })
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Credit hold overridden'), 'success')
  })

  it('allows financial manager to reject credit hold and cancel order via modal', async () => {
    const holdOrder = {
      ...sampleOrder,
      status: 'Credit Hold',
      hold_reason: 'Delinquent account with >30 days overdue invoices',
    }

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/101')) return Promise.resolve({ data: holdOrder })
      if (url.includes('/T0013I/')) return Promise.resolve({ data: sampleLines })
      if (url.includes('/T0010I/')) return Promise.resolve({ data: sampleCustomers })
      if (url.includes('/T0008I/')) return Promise.resolve({ data: sampleWarehouses })
      if (url.includes('/T0001I/')) return Promise.resolve({ data: sampleUOMs })
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { ...holdOrder, status: 'Cancelled' } })

    const w = createWrapper()
    await flushPromises()

    const rejectBtn = w.find('.credit-hold-banner .btn-outline-danger')
    expect(rejectBtn.exists()).toBe(true)
    await rejectBtn.trigger('click')
    await flushPromises()

    const textarea = document.querySelector('textarea.form-textarea')
    expect(textarea).not.toBeNull()

    textarea.value = 'Rejected due to severe overdue aging > 60 days'
    textarea.dispatchEvent(new Event('input'))
    await flushPromises()

    const confirmRejectBtn = document.querySelector('.modal-footer .btn-danger')
    expect(confirmRejectBtn).not.toBeNull()
    confirmRejectBtn.click()
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0012I/101/reject-credit-hold', {
      reason: 'Rejected due to severe overdue aging > 60 days',
    })
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Credit hold rejected'), 'success')
  })

  it('renders credit hold release banner when order has hold_released_by details', async () => {
    const releasedOrder = {
      ...sampleOrder,
      status: 'Confirmed',
      hold_released_by: 'fin_manager_jane',
      hold_released_at: '2026-08-25T14:30:00Z',
      hold_release_reason: 'Customer provided bank letter of credit',
    }

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/101')) return Promise.resolve({ data: releasedOrder })
      if (url.includes('/T0013I/')) return Promise.resolve({ data: sampleLines })
      if (url.includes('/T0010I/')) return Promise.resolve({ data: sampleCustomers })
      if (url.includes('/T0008I/')) return Promise.resolve({ data: sampleWarehouses })
      if (url.includes('/T0001I/')) return Promise.resolve({ data: sampleUOMs })
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Credit Hold Overridden & Authorized')
    expect(w.text()).toContain('fin_manager_jane')
    expect(w.text()).toContain('Customer provided bank letter of credit')
  })
})


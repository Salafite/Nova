import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import CustomerDetailView from '../views/customers/CustomerDetailView.vue'
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
  useRoute: () => ({ params: { id: '10' } }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('CustomerDetailView (Payment Terms & AR Aging Breakdown)', () => {
  let pinia
  let wrapper

  const sampleCustomer = {
    id: 10,
    name: 'Artisan Gourmet Market',
    phone: '555-123-4567',
    email: 'accounts@artisangourmet.com',
    group_name: 'Wholesale',
    payment_term_id: 2,
    credit_limit: 15000,
    balance: 8500,
    is_active: true,
  }

  const sampleAging = {
    customer_id: 10,
    current: 2500.0,
    '1_30': 3000.0,
    '31_60': 1500.0,
    '61_90': 1000.0,
    '90_plus': 500.0,
    total_outstanding: 8500.0,
    total_invoiced: 12000.0,
    total_paid: 3500.0,
  }

  const samplePaymentTerms = [
    { id: 1, name: 'Net 30', term_type: 'net', due_days: 30, discount_days: 0, discount_percentage: 0 },
    { id: 2, name: '2/10 Net 30', term_type: 'early_discount', due_days: 30, discount_days: 10, discount_percentage: 2 },
    { id: 3, name: 'COD', term_type: 'cod', due_days: 0, discount_days: 0, discount_percentage: 0 },
  ]

  const sampleInvoices = [
    {
      id: 101,
      invoice_number: 'INV-2026-0101',
      total_amount: 2500.0,
      issue_date: '2026-08-20',
      due_date: '2026-09-19',
      status: 'Unpaid',
    },
    {
      id: 102,
      invoice_number: 'INV-2026-0099',
      total_amount: 3000.0,
      issue_date: '2026-07-20',
      due_date: '2026-08-19',
      status: 'Overdue',
    },
  ]

  const samplePayments = [
    {
      id: 50,
      payment_date: '2026-08-15',
      amount: 3500.0,
      payment_method: 'Bank Transfer',
      reference: 'TXN-998877',
      status: 'Completed',
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0010I/10/aging')) {
        return Promise.resolve({ data: { aging: JSON.parse(JSON.stringify(sampleAging)) } })
      }
      if (url.includes('/T0010I/10/invoices')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoices)) })
      }
      if (url.includes('/T0010I/10/payments')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePayments)) })
      }
      if (url.includes('/T0010I/10')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomer)) })
      }
      if (url.includes('/T0096I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePaymentTerms)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.put.mockResolvedValue({
      data: {
        ...sampleCustomer,
        payment_term_id: 1,
      },
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(CustomerDetailView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders customer header and payment terms description', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Artisan Gourmet Market')
    expect(w.text()).toContain('2/10 Net 30 (2% / 10d, Net 30d)')
    expect(w.text()).toContain('$15,000.00')
    expect(w.text()).toContain('$8,500.00')
  })

  it('renders all 5 AR aging buckets accurately', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Aging Breakdown')
    // Current bucket
    expect(w.text()).toContain('$2,500.00')
    // 1-30 days
    expect(w.text()).toContain('$3,000.00')
    // 31-60 days
    expect(w.text()).toContain('$1,500.00')
    // 61-90 days
    expect(w.text()).toContain('$1,000.00')
    // 90+ days
    expect(w.text()).toContain('$500.00')
    // Total outstanding
    expect(w.text()).toContain('$8,500.00')
  })

  it('opens edit modal and updates customer payment terms', async () => {
    const w = createWrapper()
    await flushPromises()

    // Find and click Edit Customer button
    const editBtn = w.find('.page-head .btn-primary')
    expect(editBtn.exists()).toBe(true)
    await editBtn.trigger('click')
    await flushPromises()

    // Check slide panel opened
    const slidePanel = w.find('.slide-panel')
    expect(slidePanel.exists()).toBe(true)

    // Select Net 30 (id 1) - the second select on the panel
    const selects = slidePanel.findAll('select.form-input')
    const termsSelect = selects[1]
    await termsSelect.setValue(1)

    // Save
    const saveBtn = slidePanel.find('.panel-footer .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith(
      '/T0010I/10',
      expect.objectContaining({
        name: 'Artisan Gourmet Market',
        payment_term_id: 1,
      })
    )
  })
})

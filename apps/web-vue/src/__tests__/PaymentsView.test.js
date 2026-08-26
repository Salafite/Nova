import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import PaymentsView from '../views/payments/PaymentsView.vue'
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
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('PaymentsView (Early Discount & Payment Modal)', () => {
  let pinia
  let wrapper

  const samplePayments = [
    {
      id: 1,
      payment_date: '2026-08-26',
      partner_id: 10,
      invoice_id: 1,
      amount: 196.0,
      payment_method: 'Bank Transfer',
      reference: 'WIRE-8891',
      status: 'Completed',
      notes: 'Early payment discount applied: $4.00 (2%)',
    },
    {
      id: 2,
      payment_date: '2026-08-25',
      partner_id: 20,
      invoice_id: null,
      amount: 500.0,
      payment_method: 'Cash',
      reference: 'DEP-001',
      status: 'Completed',
      notes: 'Customer deposit on account',
    },
  ]

  const sampleCustomers = [
    { id: 10, name: 'Artisan Gourmet Market' },
    { id: 20, name: 'Downtown Bistro' },
  ]

  const sampleInvoices = [
    {
      id: 1,
      invoice_number: 'INV-2026-0001',
      partner_id: 10,
      total_amount: 200.0,
      discount_percentage: 2.0,
      discount_days: 10,
      discount_due_date: '2099-12-31',
      early_discount_amount: 4.0,
      status: 'Unpaid',
    },
    {
      id: 2,
      invoice_number: 'INV-2026-0002',
      partner_id: 10,
      total_amount: 500.0,
      discount_percentage: 2.0,
      discount_days: 10,
      discount_due_date: '2020-01-01', // Expired
      early_discount_amount: 10.0,
      status: 'Unpaid',
    },
  ]

  const sampleTerms = [
    { id: 1, name: '2/10 Net 30', due_days: 30, discount_percentage: 2.0, discount_days: 10 },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url, config) => {
      if (url.includes('/T0091I/invoice/1/discount-preview')) {
        return Promise.resolve({
          data: {
            invoice_id: 1,
            invoice_number: 'INV-2026-0001',
            partner_id: 10,
            invoice_total: 200.0,
            balance_due: 200.0,
            is_eligible: true,
            discount_percentage: 2.0,
            discount_amount: 4.0,
            net_amount_due: 196.0,
            discount_due_date: '2099-12-31',
            cutoff_date: '2099-12-31',
            payment_date: '2026-08-26',
          },
        })
      }
      if (url.includes('/T0091I/invoice/2/discount-preview')) {
        return Promise.resolve({
          data: {
            invoice_id: 2,
            invoice_number: 'INV-2026-0002',
            partner_id: 10,
            invoice_total: 500.0,
            balance_due: 500.0,
            is_eligible: false,
            discount_percentage: 2.0,
            discount_amount: 0.0,
            net_amount_due: 500.0,
            discount_due_date: '2020-01-01',
            cutoff_date: '2020-01-01',
            payment_date: '2026-08-26',
          },
        })
      }
      if (url.includes('/T0091I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePayments)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      if (url.includes('/T0090I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoices)) })
      }
      if (url.includes('/T0096I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleTerms)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { id: 99, status: 'Completed' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(PaymentsView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders payments list with partner names, invoice links, amounts, and discount badges', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Artisan Gourmet Market')
    expect(w.text()).toContain('Downtown Bistro')
    expect(w.text()).toContain('INV-2026-0001')
    expect(w.text()).toContain('$196.00')
    expect(w.text()).toContain('$500.00')
    expect(w.text()).toContain('$4.00 (2%)')
  })

  it('opens new payment modal with default fields', async () => {
    const w = createWrapper()
    await flushPromises()

    const newBtn = w.find('button.btn-primary')
    await newBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('New Payment')
  })

  it('previews early discount and auto-applies discounted amount when selecting an eligible invoice', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('button.btn-primary').trigger('click')
    await flushPromises()

    // Select invoice 1
    const invoiceSelect = w.findAll('select').find(s => s.html().includes('INV-2026-0001'))
    expect(invoiceSelect).toBeDefined()
    await invoiceSelect.setValue(1)
    await flushPromises()

    // Expect discount banner to display
    expect(w.find('.modal-discount-card').exists()).toBe(true)
    expect(w.text()).toContain('Early Payment Discount Available')
    expect(w.text()).toContain('2% Early Discount')
    expect(w.text()).toContain('Save $4.00')

    // Expect amount to be auto-populated to discounted net amount (196.00)
    const amountInput = w.find('input[type="number"]')
    expect(Number(amountInput.element.value)).toBe(196)
  })

  it('allows toggling between discounted balance and full balance in the modal', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('button.btn-primary').trigger('click')
    await flushPromises()

    const invoiceSelect = w.findAll('select').find(s => s.html().includes('INV-2026-0001'))
    await invoiceSelect.setValue(1)
    await flushPromises()

    // Click "Apply Full Balance"
    const fullBtn = w.findAll('button').find(b => b.text().includes('Apply Full Balance'))
    expect(fullBtn).toBeDefined()
    await fullBtn.trigger('click')
    await flushPromises()

    let amountInput = w.find('input[type="number"]')
    expect(Number(amountInput.element.value)).toBe(200)

    // Click "Apply Discounted Balance"
    const discBtn = w.findAll('button').find(b => b.text().includes('Apply Discounted Balance'))
    expect(discBtn).toBeDefined()
    await discBtn.trigger('click')
    await flushPromises()

    amountInput = w.find('input[type="number"]')
    expect(Number(amountInput.element.value)).toBe(196)
  })

  it('displays expired early discount banner when selected invoice cutoff has passed', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('button.btn-primary').trigger('click')
    await flushPromises()

    const invoiceSelect = w.findAll('select').find(s => s.html().includes('INV-2026-0002'))
    await invoiceSelect.setValue(2)
    await flushPromises()

    expect(w.find('.modal-expired-card').exists()).toBe(true)
    expect(w.text()).toContain('Early Discount Window Closed')
    expect(w.text()).toContain('2020-01-01')

    const amountInput = w.find('input[type="number"]')
    expect(Number(amountInput.element.value)).toBe(500)
  })

  it('submits payment to /T0091I/ with payload including discount and invoice metadata', async () => {
    const w = createWrapper()
    await flushPromises()

    await w.find('button.btn-primary').trigger('click')
    await flushPromises()

    const invoiceSelect = w.findAll('select').find(s => s.html().includes('INV-2026-0001'))
    await invoiceSelect.setValue(1)
    await flushPromises()

    // Save
    const saveBtn = w.find('.modal-actions button.btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0091I/',
      expect.objectContaining({
        invoice_id: 1,
        partner_id: 10,
        amount: 196,
        status: 'Completed',
      })
    )
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('saved'), 'success')
  })
})

import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import FinanceView from '../views/finance/FinanceView.vue'
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

describe('FinanceView (Invoices & Payment Terms)', () => {
  let pinia
  let wrapper

  const sampleInvoices = [
    {
      id: 1,
      invoice_number: 'INV-2026-0001',
      invoice_type: 'Sales',
      partner_id: 10,
      payment_term_id: 1,
      issue_date: '2026-08-01',
      due_date: '2026-08-31',
      discount_due_date: '2026-08-11',
      discount_percentage: 2.0,
      discount_days: 10,
      early_discount_amount: 20.0,
      total_amount: 1000.0,
      status: 'Unpaid',
    },
    {
      id: 2,
      invoice_number: 'INV-2026-0002',
      invoice_type: 'Sales',
      partner_id: 11,
      payment_term_id: 2,
      issue_date: '2026-07-01',
      due_date: '2026-07-16',
      discount_due_date: null,
      discount_percentage: 0,
      discount_days: 0,
      early_discount_amount: 0,
      total_amount: 500.0,
      status: 'Unpaid',
    },
  ]

  const sampleTerms = [
    { id: 1, name: '2/10 Net 30', due_days: 30, discount_percentage: 2.0, discount_days: 10 },
    { id: 2, name: 'Net 15', due_days: 15, discount_percentage: 0, discount_days: 0 },
    { id: 3, name: 'COD', due_days: 0, discount_percentage: 0, discount_days: 0 },
  ]

  const sampleCustomers = [
    { id: 10, name: 'Acme Corp' },
    { id: 11, name: 'Global Tech' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0090I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleInvoices)) })
      }
      if (url.includes('/T0096I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleTerms)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
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
    wrapper = mount(FinanceView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders invoices list with payment terms, partner names, due dates, and discount deadlines', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('INV-2026-0001')
    expect(w.text()).toContain('Acme Corp')
    expect(w.text()).toContain('2/10 Net 30')
    expect(w.text()).toContain('2026-08-31')
    expect(w.text()).toContain('2026-08-11')
    expect(w.text()).toContain('2%')
    expect(w.text()).toContain('$1000.00')

    expect(w.text()).toContain('INV-2026-0002')
    expect(w.text()).toContain('Global Tech')
    expect(w.text()).toContain('Net 15')
    expect(w.text()).toContain('2026-07-16')
  })

  it('opens modal to create new invoice and calculates due date and discount deadline upon payment term selection', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click Add New Invoice button
    const addBtn = w.find('button.btn-primary')
    await addBtn.trigger('click')

    expect(w.find('.modal-overlay').exists()).toBe(true)

    // Set issue_date to 2026-09-01, total_amount to 500
    const issueDateInput = w.findAll('input[type="date"]')[0]
    await issueDateInput.setValue('2026-09-01')

    const amountInput = w.find('input[type="number"][step="0.01"]')
    await amountInput.setValue(500)

    // Select 2/10 Net 30 (id: 1)
    const termSelect = w.findAll('select')[1]
    await termSelect.setValue(1)
    await termSelect.trigger('change')

    // Due date should be 2026-10-01 (30 days after 2026-09-01)
    // Discount deadline should be 2026-09-11 (10 days after 2026-09-01)
    const dateInputs = w.findAll('input[type="date"]')
    const dueDateInput = dateInputs[1]
    const discountDateInput = dateInputs[2]

    expect(dueDateInput.element.value).toBe('2026-10-01')
    expect(discountDateInput.element.value).toBe('2026-09-11')

    // Discount percentage should be 2, early discount amount should be 10.00 (2% of 500)
    const numInputs = w.findAll('input[type="number"]')
    const discountPctInput = numInputs[2]
    const discountAmtInput = numInputs[3]
    expect(Number(discountPctInput.element.value)).toBe(2)
    expect(Number(discountAmtInput.element.value)).toBe(10)
  })

  it('submits new invoice with payment term and discount metadata to API', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 3 } })

    const w = createWrapper()
    await flushPromises()

    const addBtn = w.find('button.btn-primary')
    await addBtn.trigger('click')

    // Fill form
    const textInput = w.find('input[type="text"]')
    await textInput.setValue('INV-2026-0003')

    const partnerInput = w.find('input[type="number"][min="1"]')
    await partnerInput.setValue(10)

    const dateInputs = w.findAll('input[type="date"]')
    await dateInputs[0].setValue('2026-09-01')

    const termSelect = w.findAll('select')[1]
    await termSelect.setValue(1)
    await termSelect.trigger('change')

    const amountInput = w.find('input[type="number"][step="0.01"]')
    await amountInput.setValue(1000)
    await amountInput.trigger('input')

    // Click Save
    const saveBtn = w.find('.modal-actions .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0090I/', expect.objectContaining({
      invoice_number: 'INV-2026-0003',
      partner_id: 10,
      payment_term_id: 1,
      issue_date: '2026-09-01',
      due_date: '2026-10-01',
      discount_due_date: '2026-09-11',
      discount_percentage: 2,
      discount_days: 10,
      early_discount_amount: 20,
    }))
    expect(mockToast).toHaveBeenCalledWith('Invoice saved', 'success')
  })
})

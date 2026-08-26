import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import SalesView from '../views/sales/SalesView.vue'
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

describe('SalesView (Payment Terms Support)', () => {
  let pinia
  let wrapper

  const samplePaymentTerms = [
    { id: 1, name: 'Net 30', due_days: 30, discount_days: 0, discount_percentage: 0 },
    { id: 2, name: '2/10 Net 30', due_days: 30, discount_days: 10, discount_percentage: 2 },
    { id: 3, name: 'COD', due_days: 0, discount_days: 0, discount_percentage: 0 },
  ]

  const sampleCustomers = [
    { id: 10, name: 'Acme Corp', payment_term_id: 2 },
    { id: 20, name: 'Global Traders', payment_term_id: 1 },
    { id: 30, name: 'Walk-in Cash', payment_term_id: null },
  ]

  const sampleOrders = [
    {
      id: 101,
      order_number: 'SO-2026-0001',
      customer_id: 10,
      payment_term_id: 2,
      subtotal: 500,
      tax: 25,
      grand_total: 525,
      status: 'Confirmed',
      order_date: '2026-08-20',
      notes: 'Test order with 2/10 Net 30',
    },
    {
      id: 102,
      order_number: 'SO-2026-0002',
      customer_id: 20,
      payment_term_id: 1,
      subtotal: 1000,
      tax: 50,
      grand_total: 1050,
      status: 'Pending',
      order_date: '2026-08-21',
      notes: 'Test order with Net 30',
    },
    {
      id: 103,
      order_number: 'SO-2026-0003',
      customer_id: 30,
      payment_term_id: null,
      subtotal: 150,
      tax: 7.5,
      grand_total: 157.5,
      status: 'Pending',
      order_date: '2026-08-22',
      notes: 'No explicit term',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0012I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleOrders)) })
      }
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      if (url.includes('/T0096I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePaymentTerms)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { id: 104, order_number: 'SO-2026-0004' } })
    api.put.mockResolvedValue({ data: { success: true } })
    api.delete.mockResolvedValue({ data: { success: true } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(SalesView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders sales orders list with Payment Terms column and names', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('SO-2026-0001')
    expect(w.text()).toContain('Acme Corp')
    expect(w.text()).toContain('2/10 Net 30')
    expect(w.text()).toContain('Global Traders')
    expect(w.text()).toContain('Net 30')
  })

  it('opens new sales order modal and allows selecting payment terms', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click "New Sales Order" button
    const addBtn = w.findAll('button').find(b => b.text().includes('New Sales Order') || b.text().includes('sales-order'))
    expect(addBtn).toBeDefined()
    await addBtn.trigger('click')
    await flushPromises()

    // Check modal exists
    expect(w.find('.modal-content').exists()).toBe(true)

    // Select customer Acme Corp (customer_id 10, which has payment_term_id: 2)
    const custSelect = w.findAll('select').find(s => s.html().includes('Acme Corp'))
    expect(custSelect).toBeDefined()
    await custSelect.setValue(10)
    await custSelect.trigger('change')
    await flushPromises()

    // Fill order number
    const orderNumInput = w.find('input[type="text"]')
    await orderNumInput.setValue('SO-2026-0004')

    // Find and submit save button
    const saveBtn = w.findAll('button').find(b => b.text() === 'Save' || b.text().includes('save'))
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0012I/',
      expect.objectContaining({
        order_number: 'SO-2026-0004',
        customer_id: 10,
        payment_term_id: 2,
      })
    )
  })

  it('populates existing payment terms when editing a sales order', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click edit on first order
    const editBtns = w.findAll('button.btn-icon')
    await editBtns[0].trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)

    // Verify saving with edit sends PUT request
    const saveBtn = w.findAll('button').find(b => b.text() === 'Save' || b.text().includes('save'))
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith(
      '/T0012I/101',
      expect.objectContaining({
        order_number: 'SO-2026-0001',
        customer_id: 10,
        payment_term_id: 2,
      })
    )
  })
})

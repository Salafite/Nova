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

describe('SalesView (Customer Credit Limits & Hold Status)', () => {
  let pinia
  let wrapper

  const sampleOrders = [
    {
      id: 1,
      order_number: 'SO-2026-0001',
      customer_id: 10,
      subtotal: 1000.0,
      tax: 50.0,
      grand_total: 1050.0,
      status: 'Confirmed',
      order_date: '2026-08-20',
    },
    {
      id: 2,
      order_number: 'SO-2026-0002',
      customer_id: 20,
      subtotal: 5000.0,
      tax: 250.0,
      grand_total: 5250.0,
      status: 'Credit Hold',
      order_date: '2026-08-21',
    },
  ]

  const sampleCustomers = [
    { id: 10, name: 'Acme Corp', credit_limit: 10000, balance: 2000 },
    { id: 20, name: 'Delinquent Trader', credit_limit: 5000, balance: 6000 },
  ]

  const healthyCreditStatus = {
    customer_id: 10,
    customer_name: 'Acme Corp',
    credit_limit: 10000.0,
    balance: 2000.0,
    available_credit: 8000.0,
    raw_available_credit: 8000.0,
    credit_limit_exceeded: false,
    is_credit_limit_enforced: true,
    overdue_invoices_count: 0,
    overdue_invoices_amount: 0.0,
    has_overdue_invoices: false,
    overdue_invoices: [],
    is_delinquent: false,
    on_hold: false,
    has_hold_orders: false,
    hold_orders_count: 0,
    hold_reasons: [],
  }

  const delinquentCreditStatus = {
    customer_id: 20,
    customer_name: 'Delinquent Trader',
    credit_limit: 5000.0,
    balance: 6000.0,
    available_credit: 0.0,
    raw_available_credit: -1000.0,
    credit_limit_exceeded: true,
    is_credit_limit_enforced: true,
    overdue_invoices_count: 2,
    overdue_invoices_amount: 3500.0,
    has_overdue_invoices: true,
    overdue_invoices: [
      { id: 1, invoice_number: 'INV-001', days_overdue: 45, total_amount: 2000.0 },
      { id: 2, invoice_number: 'INV-002', days_overdue: 35, total_amount: 1500.0 },
    ],
    is_delinquent: true,
    on_hold: true,
    has_hold_orders: true,
    hold_orders_count: 1,
    hold_reasons: [
      'Customer credit limit exceeded: Balance $6,000.00 > Limit $5,000.00',
      'Customer has 2 invoices overdue by >30 days (total overdue: $3,500.00)',
    ],
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0012I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleOrders)) })
      }
      if (url === '/T0010I/') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      if (url === '/T0010I/10/credit-status') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(healthyCreditStatus)) })
      }
      if (url === '/T0010I/20/credit-status') {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(delinquentCreditStatus)) })
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
    wrapper = mount(SalesView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders sales orders list with Credit Hold badge', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('SO-2026-0001')
    expect(w.text()).toContain('SO-2026-0002')
    expect(w.text()).toContain('Credit Hold')

    // Verify badge styling for Credit Hold
    const holdBadge = w.findAll('.badge').find((el) => el.text() === 'Credit Hold')
    expect(holdBadge).toBeDefined()
    expect(holdBadge.classes()).toContain('badge-danger')
  })

  it('fetches and displays healthy customer credit standing upon customer selection in modal', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open Add Modal
    const addBtn = w.findAll('button').find((b) => b.text().includes('New Sales Order'))
    expect(addBtn).toBeDefined()
    await addBtn.trigger('click')
    await flushPromises()

    // Select customer 10 (Acme Corp)
    const select = w.find('select[required]')
    await select.setValue(10)
    await select.trigger('change')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/T0010I/10/credit-status')

    // Credit panel rendered
    const creditPanel = w.find('.credit-status-panel')
    expect(creditPanel.exists()).toBe(true)

    // Checks metrics: Balance $2000.00, Limit $10000.00, Available $8000.00
    expect(creditPanel.text()).toContain('$2000.00')
    expect(creditPanel.text()).toContain('$10000.00')
    expect(creditPanel.text()).toContain('$8000.00')
    expect(creditPanel.text()).toContain('healthy')
  })

  it('displays delinquent overdue invoices warning banner for delinquent accounts', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open Add Modal
    const addBtn = w.findAll('button').find((b) => b.text().includes('New Sales Order'))
    await addBtn.trigger('click')
    await flushPromises()

    // Select customer 20 (Delinquent Trader)
    const select = w.find('select[required]')
    await select.setValue(20)
    await select.trigger('change')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/T0010I/20/credit-status')

    const creditPanel = w.find('.credit-status-panel')
    expect(creditPanel.exists()).toBe(true)
    expect(creditPanel.find('.credit-alert-danger').exists()).toBe(true)
    expect(creditPanel.text()).toContain('Delinquent Account')
    expect(creditPanel.text()).toContain('2 invoices')
    expect(creditPanel.text()).toContain('$3500.00')
  })

  it('displays exposure warning when order total exceeds available credit line', async () => {
    const w = createWrapper()
    await flushPromises()

    // Open Add Modal
    const addBtn = w.findAll('button').find((b) => b.text().includes('New Sales Order'))
    await addBtn.trigger('click')
    await flushPromises()

    // Select customer 10 (Acme Corp with $8000 available credit)
    const select = w.find('select[required]')
    await select.setValue(10)
    await select.trigger('change')
    await flushPromises()

    // Enter grand total of 9000 (2000 balance + 9000 order = 11000 > 10000 limit)
    const inputs = w.findAll('input[type="number"]')
    const grandTotalInput = inputs[2]
    await grandTotalInput.setValue(9000)
    await grandTotalInput.trigger('input')
    await flushPromises()

    const creditPanel = w.find('.credit-status-panel')
    expect(creditPanel.find('.credit-alert-warning').exists()).toBe(true)
    expect(creditPanel.text()).toContain('Exposure Warning')
  })
})

import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import CustomersView from '../views/customers/CustomersView.vue'
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

describe('CustomersView (Payment Terms & Management)', () => {
  let pinia
  let wrapper

  const samplePaymentTerms = [
    { id: 1, name: 'Net 30', term_type: 'net', due_days: 30, discount_days: 0, discount_percentage: 0 },
    { id: 2, name: '2/10 Net 30', term_type: 'early_discount', due_days: 30, discount_days: 10, discount_percentage: 2 },
    { id: 3, name: 'COD', term_type: 'cod', due_days: 0, discount_days: 0, discount_percentage: 0 },
  ]

  const sampleCustomers = [
    {
      id: 1,
      name: 'Acme Corp',
      group_name: 'Corporate',
      phone: '123-456-7890',
      email: 'contact@acme.com',
      payment_term_id: 2,
      credit_limit: 5000,
      balance: 1200,
      is_active: true,
    },
    {
      id: 2,
      name: 'Globex Ltd',
      group_name: 'Wholesale',
      phone: '987-654-3210',
      email: 'sales@globex.com',
      payment_term_id: 1,
      credit_limit: 10000,
      balance: 0,
      is_active: true,
    },
    {
      id: 3,
      name: 'Solo Trader',
      group_name: 'Retail',
      phone: '555-555-5555',
      email: 'solo@retail.com',
      payment_term_id: null,
      credit_limit: 0,
      balance: 50,
      is_active: true,
    }
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/T0010I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleCustomers)) })
      }
      if (url.includes('/T0096I/')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(samplePaymentTerms)) })
      }
      return Promise.resolve({ data: [] })
    })
    api.put.mockResolvedValue({ data: { success: true } })
    api.post.mockResolvedValue({ data: { id: 4, name: 'New Customer' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(CustomersView, {
      global: {
        plugins: [pinia],
      },
    })
    return wrapper
  }

  it('renders customers list with payment term tags', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Acme Corp')
    expect(w.text()).toContain('2/10 Net 30')
    expect(w.text()).toContain('Globex Ltd')
    expect(w.text()).toContain('Net 30')
    expect(w.text()).toContain('Solo Trader')
    expect(w.text()).toContain('-')
  })

  it('opens edit slide-panel with populated customer payment term and saves changes', async () => {
    const w = createWrapper()
    await flushPromises()

    // Find edit button for first customer (Acme Corp with payment_term_id 2)
    const editButtons = w.findAll('.col-actions button.btn-icon')
    expect(editButtons.length).toBeGreaterThan(0)
    await editButtons[0].trigger('click')
    await flushPromises()

    // Check panel opened
    const slidePanel = w.find('.slide-panel')
    expect(slidePanel.exists()).toBe(true)

    // Check payment term select options and value
    const select = slidePanel.find('select.form-input')
    expect(select.exists()).toBe(true)
    expect(slidePanel.text()).toContain('Net 30 (30')
    expect(slidePanel.text()).toContain('2/10 Net 30 (30')
    expect(slidePanel.text()).toContain('COD (0')

    // Click Save button
    const saveBtn = slidePanel.find('.panel-footer .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith(
      '/T0010I/1',
      expect.objectContaining({
        name: 'Acme Corp',
        payment_term_id: 2,
      })
    )
  })

  it('creates new customer with selected payment term', async () => {
    const w = createWrapper()
    await flushPromises()

    // Click Add Customer button
    const addBtn = w.find('.page-head .btn-primary')
    await addBtn.trigger('click')
    await flushPromises()

    const slidePanel = w.find('.slide-panel')
    const nameInput = slidePanel.find('input[type="text"]')
    await nameInput.setValue('Wayne Enterprises')

    const saveBtn = slidePanel.find('.panel-footer .btn-primary')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith(
      '/T0010I/',
      expect.objectContaining({
        name: 'Wayne Enterprises',
      })
    )
  })
})

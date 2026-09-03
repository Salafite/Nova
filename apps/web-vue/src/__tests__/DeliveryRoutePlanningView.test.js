import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import DeliveryRoutePlanningView from '../views/sales/DeliveryRoutePlanningView.vue'
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

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: { id: '1' } }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('DeliveryRoutePlanningView.vue', () => {
  let pinia
  let wrapper

  const sampleUnassignedOrders = [
    {
      order_id: 101,
      order_number: 'SO-2026-001',
      customer_name: 'Metro Supermarket North',
      zone_name: 'North Zone',
      delivery_address: '123 North Ave',
      delivery_date: '2026-09-05',
      total_weight: 450.5,
      total_volume: 3.2,
      item_count: 12,
    },
    {
      order_id: 102,
      order_number: 'SO-2026-002',
      customer_name: 'Retail Hub Branch B',
      zone_name: 'North Zone',
      delivery_address: '456 Commercial Rd',
      delivery_date: '2026-09-05',
      total_weight: 320.0,
      total_volume: 2.1,
      item_count: 8,
    },
  ]

  const sampleDeliveryRuns = [
    {
      id: 1,
      run_code: 'RUN-2026-001',
      run_date: '2026-09-05',
      zone_name: 'North Zone',
      vehicle_code: 'TRK-01',
      vehicle_name: 'Isuzu 5-Ton Refrigerated Truck',
      driver_name: 'John Driver',
      stop_count: 2,
      total_weight: 770.5,
      max_weight_capacity: 3500.0,
      status: 'Planned',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url.includes('/unassigned-orders')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleUnassignedOrders)) })
      }
      if (url.includes('/runs')) {
        return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleDeliveryRuns)) })
      }
      return Promise.resolve({ data: [] })
    })

    api.post.mockResolvedValue({ data: { status: 'success' } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  function createWrapper() {
    wrapper = mount(DeliveryRoutePlanningView, {
      global: {
        plugins: [pinia],
        stubs: {
          SkeletonTable: true,
          ErrorState: true,
        },
      },
    })
    return wrapper
  }

  it('renders title and unassigned delivery orders tab by default', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Delivery Route Planning & Driver Dispatch')
    expect(w.text()).toContain('SO-2026-001')
    expect(w.text()).toContain('Metro Supermarket North')
    expect(w.text()).toContain('North Zone')
    expect(w.text()).toContain('450.5')
  })

  it('allows filtering unassigned orders by zone', async () => {
    const w = createWrapper()
    await flushPromises()

    const zoneInput = w.find('input[placeholder="e.g. North Zone"]')
    await zoneInput.setValue('North Zone')
    await zoneInput.trigger('change')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/api/sales/delivery-routes/unassigned-orders', expect.objectContaining({
      params: expect.objectContaining({ zone_name: 'North Zone' })
    }))
  })

  it('selects orders and opens create delivery run modal', async () => {
    const w = createWrapper()
    await flushPromises()

    const checkboxes = w.findAll('tbody input[type="checkbox"]')
    expect(checkboxes.length).toBe(2)
    await checkboxes[0].setValue(true)
    await flushPromises()

    const createBtn = w.find('.page-header .btn-primary')
    expect(createBtn.attributes('disabled')).toBeUndefined()
    await createBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Create Delivery Run')
  })

  it('submits new delivery run creation', async () => {
    const w = createWrapper()
    await flushPromises()

    const checkboxes = w.findAll('tbody input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await flushPromises()

    const createBtn = w.find('.page-header .btn-primary')
    await createBtn.trigger('click')
    await flushPromises()

    const form = w.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/api/sales/delivery-routes/runs', expect.objectContaining({
      order_ids: [101]
    }))
    expect(mockToast).toHaveBeenCalledWith('Delivery run created successfully')
  })

  it('switches to active delivery runs tab and displays runs table', async () => {
    const w = createWrapper()
    await flushPromises()

    const tabs = w.findAll('.tab-btn')
    await tabs[1].trigger('click')
    await flushPromises()

    expect(w.text()).toContain('RUN-2026-001')
    expect(w.text()).toContain('TRK-01')
    expect(w.text()).toContain('John Driver')
    expect(w.text()).toContain('Planned')
  })

  it('opens assign vehicle and driver modal for a run', async () => {
    const w = createWrapper()
    await flushPromises()

    const tabs = w.findAll('.tab-btn')
    await tabs[1].trigger('click')
    await flushPromises()

    const assignBtn = w.find('button[title="Assign Vehicle / Driver"]')
    await assignBtn.trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Assign Vehicle & Driver')
  })
})

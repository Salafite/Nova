import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import StockTransfersView from '../views/warehouse/StockTransfersView.vue'
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

// Mock useWebSocket
vi.mock('../composables/useWebSocket.js', () => ({
  useWebSocket: () => ({ on: vi.fn(), send: vi.fn(), close: vi.fn() }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('StockTransfersView (Multi-Warehouse Transfers & In-Transit)', () => {
  let pinia
  let wrapper

  const sampleTransfers = [
    {
      id: 1,
      transfer_number: 'TRF-20260826-0001',
      source_warehouse_id: 1,
      source_warehouse_name: 'Central Distribution Hub',
      destination_warehouse_id: 2,
      destination_warehouse_name: 'Regional Branch North',
      status: 'In Transit',
      transfer_date: '2026-08-26',
      expected_delivery_date: '2026-08-28',
      carrier: 'FastFreight Logistics',
      tracking_number: 'FF-883921',
      total_requested_qty: 100,
      total_dispatched_qty: 100,
      total_received_qty: 0,
      total_lost_qty: 0,
      lines_count: 2,
      notes: 'Urgent stock rebalance',
    },
    {
      id: 2,
      transfer_number: 'TRF-20260826-0002',
      source_warehouse_id: 1,
      source_warehouse_name: 'Central Distribution Hub',
      destination_warehouse_id: 3,
      destination_warehouse_name: 'Regional Branch South',
      status: 'Draft',
      transfer_date: '2026-08-26',
      carrier: 'Internal Fleet',
      total_requested_qty: 50,
      total_dispatched_qty: 0,
      total_received_qty: 0,
      total_lost_qty: 0,
      lines_count: 1,
    },
    {
      id: 3,
      transfer_number: 'TRF-20260825-0003',
      source_warehouse_id: 2,
      source_warehouse_name: 'Regional Branch North',
      destination_warehouse_id: 1,
      destination_warehouse_name: 'Central Distribution Hub',
      status: 'Received',
      transfer_date: '2026-08-25',
      total_requested_qty: 30,
      total_dispatched_qty: 30,
      total_received_qty: 28,
      total_lost_qty: 2,
      lines_count: 1,
    },
  ]

  const sampleWarehouses = [
    { id: 1, name: 'Central Distribution Hub', location: 'Main' },
    { id: 2, name: 'Regional Branch North', location: 'North DC' },
    { id: 3, name: 'Regional Branch South', location: 'South DC' },
  ]

  const sampleProducts = [
    { id: 101, sku: 'SKU-DAIRY-01', name: 'Fresh Milk 1L' },
    { id: 102, sku: 'SKU-CHEESE-02', name: 'Artisan Cheddar 500g' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0108I/') return Promise.resolve({ data: JSON.parse(JSON.stringify(sampleTransfers)) })
      if (url === '/T0008I/') return Promise.resolve({ data: sampleWarehouses })
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
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
    wrapper = mount(StockTransfersView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
            props: ['to'],
          },
          SkeletonTable: true,
          ErrorState: true,
        },
      },
    })
    return wrapper
  }

  it('renders stock transfers table and summary KPI stats', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Stock Transfers')
    expect(w.text()).toContain('TRF-20260826-0001')
    expect(w.text()).toContain('TRF-20260826-0002')
    expect(w.text()).toContain('TRF-20260825-0003')

    // Origin and destination names
    expect(w.text()).toContain('Central Distribution Hub')
    expect(w.text()).toContain('Regional Branch North')
    expect(w.text()).toContain('FastFreight Logistics')

    // Discrepancy indicator on TRF 3
    expect(w.text()).toContain('2 lost')

    // Stats values: total 3, draft 1, in-transit 1, received 1, discrepancy 1
    const statCards = w.findAll('.stat-card')
    expect(statCards.length).toBe(5)
    expect(statCards[0].text()).toContain('3')
    expect(statCards[1].text()).toContain('1')
    expect(statCards[2].text()).toContain('1')
    expect(statCards[3].text()).toContain('1')
    expect(statCards[4].text()).toContain('1')
  })

  it('filters transfers by status dropdown', async () => {
    const w = createWrapper()
    await flushPromises()

    const statusSelect = w.find('.filter-controls select')
    await statusSelect.setValue('In Transit')
    await flushPromises()

    expect(w.text()).toContain('TRF-20260826-0001')
    expect(w.text()).not.toContain('TRF-20260826-0002')
    expect(w.text()).not.toContain('TRF-20260825-0003')
  })

  it('filters transfers by search query', async () => {
    const w = createWrapper()
    await flushPromises()

    const searchInput = w.find('.search-input')
    await searchInput.setValue('FastFreight')
    await flushPromises()

    expect(w.text()).toContain('TRF-20260826-0001')
    expect(w.text()).not.toContain('TRF-20260826-0002')
  })

  it('opens create transfer modal and submits a new order', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        id: 4,
        transfer_number: 'TRF-20260826-0004',
        status: 'Draft',
      },
    })

    const w = createWrapper()
    await flushPromises()

    // Click New Transfer button
    const addBtn = w.findAll('button').find(b => b.text().includes('New Transfer'))
    expect(addBtn).toBeDefined()
    await addBtn.trigger('click')
    await flushPromises()

    // Verify modal opened
    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('New Stock Transfer Order')

    // Submit the form
    const form = w.find('form.modal-body')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/T0108I/', expect.objectContaining({
      source_warehouse_id: 1,
      destination_warehouse_id: 2,
      status: 'Draft',
    }))
  })
})

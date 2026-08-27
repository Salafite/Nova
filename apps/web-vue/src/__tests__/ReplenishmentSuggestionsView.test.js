import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ReplenishmentSuggestionsView from '../views/inventory/ReplenishmentSuggestionsView.vue'
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

describe('ReplenishmentSuggestionsView (Inter-Branch Replenishment)', () => {
  let pinia
  let wrapper

  const sampleSuggestions = [
    {
      product_id: 101,
      product_code: 'SKU-MILK-01',
      product_name: 'Fresh Whole Milk 1L',
      destination_warehouse_id: 2,
      destination_warehouse_name: 'Regional Branch North',
      current_stock: 0,
      reserved_stock: 0,
      in_transit_stock: 0,
      available_stock: 0,
      reorder_point: 50,
      safety_stock: 25,
      suggested_transfer_qty: 75,
      source_warehouse_id: 1,
      source_warehouse_name: 'Central Distribution Hub',
      source_available_stock: 450,
      priority: 'Critical',
      reason: 'Out of stock: available (0) below safety threshold (25.0)',
    },
    {
      product_id: 102,
      product_code: 'SKU-CHEESE-02',
      product_name: 'Artisan Cheddar 500g',
      destination_warehouse_id: 3,
      destination_warehouse_name: 'Regional Branch South',
      current_stock: 12,
      reserved_stock: 2,
      in_transit_stock: 0,
      available_stock: 10,
      reorder_point: 60,
      safety_stock: 30,
      suggested_transfer_qty: 80,
      source_warehouse_id: 1,
      source_warehouse_name: 'Central Distribution Hub',
      source_available_stock: 300,
      priority: 'High',
      reason: 'Effective stock (10) significantly below reorder point (60.0)',
    },
    {
      product_id: 103,
      product_code: 'SKU-YOGURT-03',
      product_name: 'Greek Yogurt 200g',
      destination_warehouse_id: 2,
      destination_warehouse_name: 'Regional Branch North',
      current_stock: 35,
      reserved_stock: 0,
      in_transit_stock: 5,
      available_stock: 35,
      reorder_point: 40,
      safety_stock: 20,
      suggested_transfer_qty: 20,
      source_warehouse_id: 1,
      source_warehouse_name: 'Central Distribution Hub',
      source_available_stock: 200,
      priority: 'Normal',
      reason: 'Effective stock (40) below reorder point (40.0)',
    },
  ]

  const sampleSummary = {
    total_products: 48,
    total_warehouses: 4,
    total_deficits: 3,
    critical_deficits: 1,
    high_deficits: 1,
    active_in_transit_transfers: 2,
  }

  const sampleWarehouses = [
    { id: 1, name: 'Central Distribution Hub', warehouse_type: 'Central Hub', is_virtual: false },
    { id: 2, name: 'Regional Branch North', warehouse_type: 'Branch', is_virtual: false },
    { id: 3, name: 'Regional Branch South', warehouse_type: 'Branch', is_virtual: false },
    { id: 99, name: 'In-Transit Virtual Location', warehouse_type: 'Virtual', is_virtual: true },
  ]

  const sampleProducts = [
    { id: 101, sku: 'SKU-MILK-01', name: 'Fresh Whole Milk 1L' },
    { id: 102, sku: 'SKU-CHEESE-02', name: 'Artisan Cheddar 500g' },
    { id: 103, sku: 'SKU-YOGURT-03', name: 'Greek Yogurt 200g' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/inventory/replenishment/suggestions') {
        return Promise.resolve({
          data: {
            total_suggestions: 3,
            critical_count: 1,
            high_count: 1,
            items: JSON.parse(JSON.stringify(sampleSuggestions)),
          },
        })
      }
      if (url === '/inventory/replenishment/summary') {
        return Promise.resolve({ data: sampleSummary })
      }
      if (url === '/T0008I/') {
        return Promise.resolve({ data: sampleWarehouses })
      }
      if (url === '/T0003I/') {
        return Promise.resolve({ data: sampleProducts })
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
    wrapper = mount(ReplenishmentSuggestionsView, {
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

  it('renders replenishment suggestions table and summary health KPI metrics', async () => {
    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('Inter-Branch Replenishment Suggestions')
    expect(w.text()).toContain('SKU-MILK-01')
    expect(w.text()).toContain('Fresh Whole Milk 1L')
    expect(w.text()).toContain('SKU-CHEESE-02')
    expect(w.text()).toContain('Artisan Cheddar 500g')
    expect(w.text()).toContain('Regional Branch North')
    expect(w.text()).toContain('Regional Branch South')
    expect(w.text()).toContain('Central Distribution Hub')

    // Stats values: total 3, critical 1, high 1, in-transit 2, monitored SKUs 48
    const statCards = w.findAll('.stat-card')
    expect(statCards.length).toBe(5)
    expect(statCards[0].text()).toContain('3')
    expect(statCards[1].text()).toContain('1')
    expect(statCards[2].text()).toContain('1')
    expect(statCards[3].text()).toContain('2')
    expect(statCards[4].text()).toContain('48')
  })

  it('filters recommendations by priority dropdown', async () => {
    const w = createWrapper()
    await flushPromises()

    const selects = w.findAll('.filter-controls select')
    // Priority select is the 3rd select
    const prioritySelect = selects[2]
    await prioritySelect.setValue('Critical')
    await flushPromises()

    expect(w.text()).toContain('SKU-MILK-01')
    expect(w.text()).not.toContain('SKU-CHEESE-02')
    expect(w.text()).not.toContain('SKU-YOGURT-03')
  })

  it('filters recommendations by search query', async () => {
    const w = createWrapper()
    await flushPromises()

    const searchInput = w.find('.search-input')
    await searchInput.setValue('Cheddar')
    await flushPromises()

    expect(w.text()).toContain('SKU-CHEESE-02')
    expect(w.text()).not.toContain('SKU-MILK-01')
  })

  it('toggles calculation parameters panel and applies updated values', async () => {
    const w = createWrapper()
    await flushPromises()

    // Parameters panel initially hidden
    expect(w.find('.params-panel').exists()).toBe(false)

    // Click toggle button
    const toggleBtn = w.find('.toggle-params-btn')
    await toggleBtn.trigger('click')
    await flushPromises()

    expect(w.find('.params-panel').exists()).toBe(true)

    // Click apply button
    const applyBtn = w.find('.params-panel button')
    await applyBtn.trigger('click')
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/inventory/replenishment/suggestions', expect.objectContaining({
      params: expect.objectContaining({
        safety_stock_ratio: 0.5,
        target_coverage_multiplier: 1.5,
      }),
    }))
  })

  it('selects items and opens batch transfer modal with grouping preview', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        transfers_created: 2,
        transfer_ids: [10, 11],
        transfer_numbers: ['TRF-20260826-0010', 'TRF-20260826-0011'],
        transfers: [
          {
            id: 10,
            transfer_number: 'TRF-20260826-0010',
            source_warehouse_id: 1,
            destination_warehouse_id: 2,
          },
          {
            id: 11,
            transfer_number: 'TRF-20260826-0011',
            source_warehouse_id: 1,
            destination_warehouse_id: 3,
          },
        ],
      },
    })

    const w = createWrapper()
    await flushPromises()

    // Check individual checkboxes for first two items
    const checkboxes = w.findAll('.data-table tbody input[type="checkbox"]')
    expect(checkboxes.length).toBe(3)
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await flushPromises()

    // Verify selection banner shows 2 items selected
    expect(w.text()).toContain('2 of 3 items selected')

    // Click Generate Transfers button
    const genBtn = w.find('.table-actions-header .btn-primary')
    await genBtn.trigger('click')
    await flushPromises()

    // Verify modal opened
    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Generate Replenishment Stock Transfers')
    expect(w.text()).toContain('Transfer Orders Grouping Preview')

    // Submit batch generation
    const form = w.find('form.modal-body')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/inventory/replenishment/generate-transfers', expect.objectContaining({
      items: expect.arrayContaining([
        expect.objectContaining({ product_id: 101, destination_warehouse_id: 2, source_warehouse_id: 1 }),
        expect.objectContaining({ product_id: 102, destination_warehouse_id: 3, source_warehouse_id: 1 }),
      ]),
    }))

    // Verify success modal appeared
    expect(w.text()).toContain('Transfers Generated Successfully')
    expect(w.text()).toContain('TRF-20260826-0010')
    expect(w.text()).toContain('TRF-20260826-0011')
  })

  it('handles single item quick transfer modal', async () => {
    const w = createWrapper()
    await flushPromises()

    const transferNowBtns = w.findAll('.col-actions button')
    expect(transferNowBtns.length).toBe(3)
    await transferNowBtns[0].trigger('click')
    await flushPromises()

    expect(w.find('.modal-content').exists()).toBe(true)
    expect(w.text()).toContain('Transfer Order #1')
    expect(w.text()).toContain('Regional Branch North')
  })

  it('renders healthy empty state when no suggestions exist', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/inventory/replenishment/suggestions') {
        return Promise.resolve({ data: { total_suggestions: 0, items: [] } })
      }
      if (url === '/inventory/replenishment/summary') {
        return Promise.resolve({ data: { total_products: 48, total_warehouses: 4, total_deficits: 0 } })
      }
      return Promise.resolve({ data: [] })
    })

    const w = createWrapper()
    await flushPromises()

    expect(w.text()).toContain('All Warehouses Adequately Stocked')
  })
})

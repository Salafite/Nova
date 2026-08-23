import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import InventoryConfigView from '../views/inventory/InventoryConfigView.vue'
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

describe('InventoryConfigView (Dual UOM & Catch-Weight Engine Configuration)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    {
      id: 1,
      name: 'Gouda Cheese Wheel (20kg)',
      sku: 'CHEESE-GOUDA-20KG',
      is_catch_weight: true,
      pricing_uom_id: 2,
      nominal_weight: 20.0,
      tolerance_pct: 5.0,
      pricing_basis: 'weight',
    },
  ]

  const sampleUoms = [
    { id: 1, uom_code: 'CASE', uom_name: 'Case', category: 'Quantity', is_base_unit: true, is_active: true },
    { id: 2, uom_code: 'KG', uom_name: 'Kilogram', category: 'Weight', is_base_unit: false, is_active: true },
  ]

  const sampleConversions = [
    { id: 1, from_uom_id: 1, to_uom_id: 2, factor: 20.0 },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
      if (url === '/T0001I/') return Promise.resolve({ data: sampleUoms })
      if (url === '/T0002I/') return Promise.resolve({ data: sampleConversions })
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
  })

  it('renders Dual UOM configuration dashboard with stats and rules', async () => {
    wrapper = mount(InventoryConfigView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          SkeletonTable: true,
          ErrorState: true,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Inventory & Dual UOM Configuration')
    expect(wrapper.text()).toContain('Catch-Weight Products')
    expect(wrapper.text()).toContain('Default Tolerance')
    expect(wrapper.text()).toContain('Configured UOMs')
    expect(wrapper.text()).toContain('Gouda Cheese Wheel (20kg)')
    expect(wrapper.text()).toContain('CHEESE-GOUDA-20KG')
    expect(wrapper.text()).toContain('±5%')
  })

  it('switches between tabs and allows saving configuration', async () => {
    wrapper = mount(InventoryConfigView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          SkeletonTable: true,
          ErrorState: true,
        },
      },
    })

    await flushPromises()

    // Switch to UOM Directory tab
    const uomTab = wrapper.findAll('.tab-btn').find(b => b.text().includes('Units of Measure Directory'))
    expect(uomTab).toBeDefined()
    await uomTab.trigger('click')
    expect(wrapper.text()).toContain('Units of Measure Directory')

    // Switch to Warehouse policies tab
    const whTab = wrapper.findAll('.tab-btn').find(b => b.text().includes('Warehouse & Stock Policies'))
    expect(whTab).toBeDefined()
    await whTab.trigger('click')
    expect(wrapper.text()).toContain('FEFO')

    // Click Save Configuration
    const saveBtn = wrapper.findAll('button').find(b => b.text().includes('Save Configuration'))
    expect(saveBtn).toBeDefined()
    await saveBtn.trigger('click')
    await flushPromises()

    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('configuration saved'), 'success')
  })
})

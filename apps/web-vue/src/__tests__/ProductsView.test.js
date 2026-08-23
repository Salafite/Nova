import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ProductsView from '../views/products/ProductsView.vue'
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

// Mock useWebSocket
vi.mock('../composables/useWebSocket.js', () => ({
  useWebSocket: () => ({ on: vi.fn(), send: vi.fn(), close: vi.fn() }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('ProductsView (Dual UOM & Catch-Weight)', () => {
  let pinia
  let wrapper

  const sampleProducts = [
    {
      id: 1,
      name: 'Standard Cheddar 500g',
      sku: 'STD-CHEDDAR-500G',
      type: 'stockable',
      category: 'Dairy',
      price: 5.99,
      is_active: true,
      is_catch_weight: false,
    },
    {
      id: 2,
      name: 'Artisan Wheel of Gouda (Nominal 20kg)',
      sku: 'CW-GOUDA-WHEEL-20K',
      type: 'stockable',
      category: 'Dairy',
      price: 18.5,
      is_active: true,
      is_catch_weight: true,
      pricing_uom_id: 2,
      nominal_weight: 20.0,
      tolerance_pct: 10.0,
      pricing_basis: 'weight',
    },
  ]

  const sampleUoms = [
    { id: 1, uom_code: 'CASE', uom_name: 'Case', category: 'Quantity' },
    { id: 2, uom_code: 'KG', uom_name: 'Kilogram', category: 'Weight' },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0003I/') return Promise.resolve({ data: sampleProducts })
      if (url === '/T0001I/') return Promise.resolve({ data: sampleUoms })
      if (url === '/T0011I/') return Promise.resolve({ data: [] })
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
  })

  it('renders products table with Catch-Weight badge and stats', async () => {
    wrapper = mount(ProductsView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          SkeletonTable: true,
          ErrorState: true,
          FormFieldError: true,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Standard Cheddar 500g')
    expect(wrapper.text()).toContain('Artisan Wheel of Gouda (Nominal 20kg)')
    expect(wrapper.text()).toContain('STD-CHEDDAR-500G')
    expect(wrapper.text()).toContain('CW-GOUDA-WHEEL-20K')
    // CW badge on catch-weight item
    expect(wrapper.text()).toContain('CW')
    // Catch-Weight count in stats
    expect(wrapper.text()).toContain('Catch-Weight')
  })

  it('allows configuring Dual UOM fields when creating a new product', async () => {
    api.post.mockResolvedValueOnce({ data: { id: 3, name: 'Parmesan Block', sku: 'PARM-10KG' } })

    wrapper = mount(ProductsView, {
      global: {
        plugins: [pinia],
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          SkeletonTable: true,
          ErrorState: true,
          FormFieldError: true,
        },
      },
    })

    await flushPromises()

    // Open Add modal
    const addBtn = wrapper.findAll('button').find(b => b.text().includes('New Product'))
    await addBtn.trigger('click')

    expect(wrapper.text()).toContain('New Product')

    // Find tab for Dual UOM
    const dualUomTab = wrapper.findAll('.tab-btn').find(b => b.text().includes('Dual UOM'))
    expect(dualUomTab).toBeDefined()
    await dualUomTab.trigger('click')

    // Verify modal contains dual UOM elements
    expect(wrapper.text()).toContain('Enable Catch-Weight & Dual Unit-of-Measure')
  })
})

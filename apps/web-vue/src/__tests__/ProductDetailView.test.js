import { mount, flushPromises } from '@vue/test-utils'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import ProductDetailView from '../views/products/ProductDetailView.vue'
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
  useRoute: () => ({ params: { id: '501' } }),
  useRouter: () => ({ push: mockPush }),
}))

// Mock useToast
const mockToast = vi.fn()
vi.mock('../composables/useToast.js', () => ({
  useToast: () => ({ show: mockToast }),
}))

describe('ProductDetailView (Dual UOM & Catch-Weight)', () => {
  let pinia
  let wrapper

  const sampleProduct = {
    id: 501,
    name: 'Gouda Cheese Block (Nominal 10kg)',
    sku: 'CHEESE-GOUDA-10KG',
    category: 'Dairy',
    brand: 'Artisan Farms',
    price: 15.0,
    cost_price: 10.0,
    tax_rate: 0.05,
    is_active: true,
    is_catch_weight: true,
    pricing_uom_id: 2,
    nominal_weight: 10.0,
    tolerance_pct: 5.0,
    pricing_basis: 'weight',
  }

  const sampleUoms = [
    { id: 1, uom_code: 'CASE', uom_name: 'Case of 1', category: 'Quantity', is_base_unit: true, is_active: true },
    { id: 2, uom_code: 'KG', uom_name: 'Kilogram', category: 'Weight', is_base_unit: false, is_active: true },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    api.get.mockImplementation((url) => {
      if (url === '/T0003I/501') return Promise.resolve({ data: sampleProduct })
      if (url === '/T0009I/') return Promise.resolve({ data: [{ id: 1, warehouse_id: 1, warehouse_name: 'Central Warehouse', qty: 25, reserved_qty: 2 }] })
      if (url === '/T0011I/') return Promise.resolve({ data: [{ id: 1, name: 'Dairy Direct Supplier' }] })
      if (url.includes('/T0103I/by-product/')) return Promise.resolve({ data: [] })
      if (url === '/T0001I/') return Promise.resolve({ data: sampleUoms })
      return Promise.resolve({ data: [] })
    })
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
  })

  it('renders product details with Dual UOM and Catch-Weight badges and parameters', async () => {
    wrapper = mount(ProductDetailView, {
      global: {
        plugins: [pinia],
        stubs: ['router-link', 'SkeletonCard', 'SkeletonTable', 'ErrorState'],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Gouda Cheese Block (Nominal 10kg)')
    expect(wrapper.text()).toContain('CHEESE-GOUDA-10KG')
    // Catch-Weight badge
    expect(wrapper.text()).toContain('Catch-Weight')
    // Dual UOM Card details
    expect(wrapper.text()).toContain('Dual UOM & Catch-Weight')
    expect(wrapper.text()).toContain('KG - Kilogram')
    expect(wrapper.text()).toContain('10 KG')
    expect(wrapper.text()).toContain('±5%')
    expect(wrapper.text()).toContain('weight')
  })

  it('opens edit modal with populated Dual UOM fields and saves successfully', async () => {
    api.put.mockResolvedValueOnce({ data: { ...sampleProduct, nominal_weight: 12.0 } })

    wrapper = mount(ProductDetailView, {
      global: {
        plugins: [pinia],
        stubs: ['router-link', 'SkeletonCard', 'SkeletonTable', 'ErrorState'],
      },
    })

    await flushPromises()

    // Click edit button
    const editBtn = wrapper.findAll('button').find(b => b.text().includes('Edit'))
    expect(editBtn).toBeDefined()
    await editBtn.trigger('click')

    // Modal is opened
    expect(wrapper.text()).toContain('Edit Product')

    // Submit edit form
    const form = wrapper.find('form')
    await form.trigger('submit')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith('/T0003I/501', expect.objectContaining({
      name: 'Gouda Cheese Block (Nominal 10kg)',
      sku: 'CHEESE-GOUDA-10KG',
      is_catch_weight: true,
      pricing_uom_id: 2,
      nominal_weight: 10.0,
      tolerance_pct: 5.0,
      pricing_basis: 'weight',
    }))
    expect(mockToast).toHaveBeenCalledWith(expect.stringContaining('Product updated'), 'success')
  })
})

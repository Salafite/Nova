import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PortalCatalogView from '../views/portal/PortalCatalogView.vue'
import PortalCartCheckoutView from '../views/portal/PortalCartCheckoutView.vue'
import { usePortalStore } from '../stores/portal.js'
import { api } from '../api/client.js'

// Mock API client
vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  CONFIG: { apiBase: 'http://test.local' },
}))

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  RouterLink: {
    name: 'RouterLink',
    props: ['to'],
    template: '<a :href="to"><slot /></a>',
  },
}))

describe('Portal Catalog & Checkout Views', () => {
  let pinia
  let portalStore

  const mockCatalogItems = [
    {
      id: 101,
      product_code: 'COF-001',
      product_name: 'Espresso Roast Beans 1kg',
      category_name: 'Beverages',
      uom_name: 'Bag',
      contracted_price: 24.50,
      base_price: 30.00,
      is_contracted: true,
      discount_percent: 18.3,
      stock_qty: 150,
      is_in_stock: true,
      description: 'Premium dark roast whole beans',
    },
    {
      id: 102,
      product_code: 'OAT-002',
      product_name: 'Barista Oat Milk 1L',
      category_name: 'Dairy & Plant Milk',
      uom_name: 'Carton',
      contracted_price: 3.80,
      base_price: 3.80,
      is_contracted: false,
      discount_percent: 0,
      stock_qty: 0,
      is_in_stock: false,
      description: 'Creamy plant-based milk',
    },
  ]

  const mockCategories = [
    { id: 1, name: 'Beverages', product_count: 1 },
    { id: 2, name: 'Dairy & Plant Milk', product_count: 1 },
  ]

  const mockSummary = {
    customer_id: 10,
    customer_name: 'Artisan Cafe Ltd',
    company_name: 'Artisan Cafe Ltd',
    min_order_amount: 100.00,
    current_balance: 450.00,
    available_credit: 2500.00,
    allow_reorders: true,
  }

  const mockCutoff = {
    is_past_cutoff: false,
    cutoff_time: '22:00:00',
    next_delivery_date: '2026-08-27',
    schedule_rule: 'D+1 Next-Day',
    message: 'Order before 22:00 for next-day delivery',
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    portalStore = usePortalStore()
    mockPush.mockClear()
    vi.clearAllMocks()

    api.get.mockImplementation(url => {
      if (url === '/portal/catalog') {
        return Promise.resolve({
          data: {
            items: mockCatalogItems,
            total: 2,
            page: 1,
            limit: 50,
            categories: mockCategories,
          },
        })
      }
      if (url === '/portal/account/summary') {
        return Promise.resolve({ data: mockSummary })
      }
      if (url === '/portal/cutoff-status') {
        return Promise.resolve({ data: mockCutoff })
      }
      return Promise.resolve({ data: {} })
    })

    // Initialize mock store data
    portalStore.catalog = [...mockCatalogItems]
    portalStore.catalogTotal = 2
    portalStore.categories = [...mockCategories]
    portalStore.accountSummary = { ...mockSummary }
    portalStore.cutoffStatus = { ...mockCutoff }
    portalStore.cart = []
  })

  // ------------------------------------------------------------------------
  // PortalCatalogView Tests
  // ------------------------------------------------------------------------
  describe('PortalCatalogView', () => {
    it('renders page header, cutoff banner, min order banner, and product catalog cards', async () => {
      const wrapper = mount(PortalCatalogView, {
        global: {
          plugins: [pinia],
          stubs: {
            RouterLink: { template: '<a><slot /></a>' },
          },
        },
      })

      expect(wrapper.text()).toContain('Order Supplies & Replenishment')
      expect(wrapper.text()).toContain('Order Cutoff Countdown')
      expect(wrapper.text()).toContain('Minimum Order Requirement')
      expect(wrapper.text()).toContain('Espresso Roast Beans 1kg')
      expect(wrapper.text()).toContain('$24.50')
      expect(wrapper.text()).toContain('Contracted Price')
      expect(wrapper.text()).toContain('Barista Oat Milk 1L')
      expect(wrapper.text()).toContain('Out of Stock')
    })

    it('displays strike-through base price and discount pill for contracted items', async () => {
      const wrapper = mount(PortalCatalogView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.find('.contracted-badge-top').exists()).toBe(true)
      expect(wrapper.text()).toContain('-18%')
      expect(wrapper.text()).toContain('Regular:')
      expect(wrapper.text()).toContain('$30.00')
    })

    it('adds product to cart when clicking Add to Cart button', async () => {
      const wrapper = mount(PortalCatalogView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const addBtn = wrapper.find('.btn-add-to-cart')
      expect(addBtn.exists()).toBe(true)
      await addBtn.trigger('click')

      expect(portalStore.cart).toHaveLength(1)
      expect(portalStore.cart[0].product_id).toBe(101)
      expect(portalStore.cart[0].qty).toBe(1)
      expect(portalStore.cartSubtotal).toBe(24.50)
    })

    it('renders quantity stepper and sticky cart bar when items are in cart', async () => {
      portalStore.addToCart(portalStore.catalog[0], 2)

      const wrapper = mount(PortalCatalogView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.find('.qty-stepper-container').exists()).toBe(true)
      expect(wrapper.find('.stepper-input').element.value).toBe('2')

      // Check sticky cart summary bar
      const stickyBar = wrapper.find('.sticky-cart-bar')
      expect(stickyBar.exists()).toBe(true)
      expect(stickyBar.text()).toContain('2 items in Cart')
      expect(stickyBar.text()).toContain('Subtotal:')
      expect(stickyBar.text()).toContain('$49.00')
    })

    it('switches between grid view and table view modes', async () => {
      const wrapper = mount(PortalCatalogView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.find('.catalog-products-grid').exists()).toBe(true)
      expect(wrapper.find('.catalog-table-container').exists()).toBe(false)

      const tableBtn = wrapper.findAll('.view-btn')[1]
      await tableBtn.trigger('click')

      expect(wrapper.find('.catalog-products-grid').exists()).toBe(false)
      expect(wrapper.find('.catalog-table-container').exists()).toBe(true)
      expect(wrapper.find('.catalog-table').exists()).toBe(true)
    })
  })

  // ------------------------------------------------------------------------
  // PortalCartCheckoutView Tests
  // ------------------------------------------------------------------------
  describe('PortalCartCheckoutView', () => {
    it('renders empty cart state when cart has no items', () => {
      portalStore.cart = []

      const wrapper = mount(PortalCartCheckoutView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('Your Replenishment Cart is Empty')
      expect(wrapper.find('.empty-cart-card').exists()).toBe(true)
      expect(wrapper.find('.cart-grid-layout').exists()).toBe(false)
    })

    it('renders cart line items, pricing, notes, and minimum order gauge when items in cart', () => {
      portalStore.addToCart(portalStore.catalog[0], 2) // $49.00 (under $100 min order)

      const wrapper = mount(PortalCartCheckoutView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.find('.empty-cart-card').exists()).toBe(false)
      expect(wrapper.find('.cart-grid-layout').exists()).toBe(true)
      expect(wrapper.text()).toContain('Espresso Roast Beans 1kg')
      expect(wrapper.text()).toContain('$24.50')
      expect(wrapper.text()).toContain('$49.00')
      expect(wrapper.find('.item-note-input').exists()).toBe(true)
      expect(wrapper.text()).toContain('Min Order Threshold')
      expect(wrapper.text()).toContain('+$51.00 needed')

      // Confirm button should be disabled due to minimum order requirement
      const confirmBtn = wrapper.find('.btn-submit-order')
      expect(confirmBtn.attributes('disabled')).toBeDefined()
    })

    it('enables order confirmation when minimum order requirement is satisfied', async () => {
      portalStore.addToCart(portalStore.catalog[0], 5) // $122.50 (exceeds $100 min)

      const wrapper = mount(PortalCartCheckoutView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(portalStore.meetsMinOrder).toBe(true)
      expect(wrapper.find('.min-order-alert-callout').exists()).toBe(false)

      const confirmBtn = wrapper.find('.btn-submit-order')
      expect(confirmBtn.attributes('disabled')).toBeUndefined()
    })

    it('submits confirmed order and opens success confirmation modal', async () => {
      portalStore.addToCart(portalStore.catalog[0], 5)

      const mockOrderRes = {
        id: 777,
        order_number: 'SO-2026-0777',
        customer_id: 10,
        status: 'Confirmed',
        total_amount: 122.50,
        requested_delivery_date: '2026-08-27',
      }

      vi.spyOn(portalStore, 'submitOrder').mockResolvedValueOnce(mockOrderRes)

      const wrapper = mount(PortalCartCheckoutView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const confirmBtn = wrapper.find('.btn-submit-order')
      await confirmBtn.trigger('click')

      expect(portalStore.submitOrder).toHaveBeenCalled()
      expect(wrapper.find('.order-success-modal').exists()).toBe(true)
      expect(wrapper.text()).toContain('Replenishment Order Submitted!')
      expect(wrapper.text()).toContain('SO-2026-0777')
    })
  })
})

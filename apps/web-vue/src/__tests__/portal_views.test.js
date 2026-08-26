import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PortalCatalogView from '../views/portal/PortalCatalogView.vue'
import PortalCartCheckoutView from '../views/portal/PortalCartCheckoutView.vue'
import PortalOrdersView from '../views/portal/PortalOrdersView.vue'
import PortalOrderDetailView from '../views/portal/PortalOrderDetailView.vue'
import PortalDashboardView from '../views/portal/PortalDashboardView.vue'
import PortalInvoicesView from '../views/portal/PortalInvoicesView.vue'
import PortalPaymentResultView from '../views/portal/PortalPaymentResultView.vue'
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
const mockRoute = {
  params: { id: '501' },
  query: {},
}

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => mockRoute,
  RouterLink: {
    name: 'RouterLink',
    props: ['to'],
    template: '<a :href="to"><slot /></a>',
  },
}))

describe('Portal Views Suite', () => {
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

  const mockOrders = [
    {
      id: 501,
      order_number: 'SO-20260825-001',
      customer_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      status: 'Confirmed',
      order_date: '2026-08-25',
      requested_delivery_date: '2026-08-26',
      subtotal: 147.00,
      tax: 0.00,
      grand_total: 147.00,
      notes: 'Deliver to rear kitchen entrance',
      lines: [
        {
          id: 1,
          sales_order_id: 501,
          product_id: 101,
          product_code: 'COF-001',
          product_name: 'Espresso Roast Beans 1kg',
          uom_name: 'Bag',
          qty: 6,
          unit_price: 24.50,
          line_total: 147.00,
        },
      ],
    },
    {
      id: 502,
      order_number: 'SO-20260820-002',
      customer_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      status: 'Delivered',
      order_date: '2026-08-20',
      requested_delivery_date: '2026-08-21',
      subtotal: 76.00,
      tax: 0.00,
      grand_total: 76.00,
      notes: 'Morning delivery',
      lines: [
        {
          id: 2,
          sales_order_id: 502,
          product_id: 102,
          product_code: 'OAT-002',
          product_name: 'Barista Oat Milk 1L',
          uom_name: 'Carton',
          qty: 20,
          unit_price: 3.80,
          line_total: 76.00,
        },
      ],
    },
    {
      id: 503,
      order_number: 'SO-20260815-003',
      customer_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      status: 'Cancelled',
      order_date: '2026-08-15',
      requested_delivery_date: '2026-08-16',
      subtotal: 50.00,
      tax: 0.00,
      grand_total: 50.00,
      notes: 'Cancelled duplicate order',
      lines: [],
    },
  ]

  const mockInvoices = [
    {
      id: 301,
      invoice_number: 'INV-2026-0301',
      partner_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      sales_order_id: 501,
      sales_order_number: 'SO-20260825-001',
      issue_date: '2026-08-25',
      due_date: '2026-09-25',
      total_amount: 147.00,
      paid_amount: 0.00,
      balance_due: 147.00,
      status: 'Unpaid',
    },
    {
      id: 302,
      invoice_number: 'INV-2026-0302',
      partner_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      sales_order_id: 502,
      sales_order_number: 'SO-20260820-002',
      issue_date: '2026-08-20',
      due_date: '2026-09-20',
      total_amount: 76.00,
      paid_amount: 76.00,
      balance_due: 0.00,
      status: 'Paid',
    },
    {
      id: 303,
      invoice_number: 'INV-2026-0303',
      partner_id: 10,
      customer_name: 'Artisan Cafe Ltd',
      sales_order_id: null,
      sales_order_number: null,
      issue_date: '2026-07-01',
      due_date: '2026-08-01',
      total_amount: 303.00,
      paid_amount: 0.00,
      balance_due: 303.00,
      status: 'Unpaid',
    },
  ]

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    portalStore = usePortalStore()
    mockPush.mockClear()
    mockRoute.params = { id: '501' }
    mockRoute.query = {}
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
      if (url === '/portal/orders') {
        return Promise.resolve({
          data: {
            items: mockOrders,
            total: 3,
            page: 1,
            limit: 20,
          },
        })
      }
      if (url === '/portal/orders/501') {
        return Promise.resolve({ data: mockOrders[0] })
      }
      if (url === '/portal/invoices') {
        return Promise.resolve({
          data: {
            items: mockInvoices,
            total: 3,
            page: 1,
            limit: 20,
          },
        })
      }
      if (url.startsWith('/portal/settlement/session/')) {
        return Promise.resolve({
          data: {
            session_id: 'cs_test_123',
            status: 'complete',
            payment_status: 'paid',
            amount_total: 14700,
            currency: 'usd',
            customer_email: 'buyer@artisancafe.com',
            customer_id: 10,
            invoice_id: 301,
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    // Initialize mock store data
    portalStore.catalog = [...mockCatalogItems]
    portalStore.catalogTotal = 2
    portalStore.categories = [...mockCategories]
    portalStore.accountSummary = { ...mockSummary }
    portalStore.cutoffStatus = { ...mockCutoff }
    portalStore.orders = [...mockOrders]
    portalStore.ordersTotal = 3
    portalStore.currentOrder = { ...mockOrders[0] }
    portalStore.invoices = [...mockInvoices]
    portalStore.invoicesTotal = 3
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

  // ------------------------------------------------------------------------
  // PortalOrdersView Tests
  // ------------------------------------------------------------------------
  describe('PortalOrdersView', () => {
    it('renders metrics summary cards, status tabs, and order history table', () => {
      const wrapper = mount(PortalOrdersView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('Order History & Replenishment')
      expect(wrapper.text()).toContain('Total Orders')
      expect(wrapper.text()).toContain('SO-20260825-001')
      expect(wrapper.text()).toContain('SO-20260820-002')
      expect(wrapper.text()).toContain('$147.00')
      expect(wrapper.text()).toContain('Confirmed')
      expect(wrapper.text()).toContain('Delivered')
    })

    it('filters orders by search query', async () => {
      const wrapper = mount(PortalOrdersView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('SO-20260825-001')

      expect(wrapper.text()).toContain('SO-20260825-001')
      expect(wrapper.text()).not.toContain('SO-20260820-002')
    })

    it('opens 1-click reorder modal and executes reorder', async () => {
      const wrapper = mount(PortalOrdersView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const reorderBtn = wrapper.findAll('.btn-reorder')[0]
      expect(reorderBtn.exists()).toBe(true)
      await reorderBtn.trigger('click')

      expect(wrapper.find('.reorder-modal-card').exists()).toBe(true)
      expect(wrapper.text()).toContain('SO-20260825-001')
      expect(wrapper.text()).toContain('Espresso Roast Beans 1kg')

      const reorderSpy = vi.spyOn(portalStore, 'reorderPastOrder').mockResolvedValueOnce({
        id: 999,
        order_number: 'SO-20260827-0999',
      })

      const submitReorderBtn = wrapper.find('.modal-footer .btn-primary')
      await submitReorderBtn.trigger('click')

      expect(reorderSpy).toHaveBeenCalledWith(501, expect.any(Object))
    })

    it('loads order lines into replenishment cart when cart mode chosen in reorder modal', async () => {
      const wrapper = mount(PortalOrdersView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const reorderBtn = wrapper.findAll('.btn-reorder')[0]
      await reorderBtn.trigger('click')

      // Switch to cart mode
      const cartRadio = wrapper.findAll('input[type="radio"]')[1]
      await cartRadio.setValue()

      const submitBtn = wrapper.find('.modal-footer .btn-primary')
      await submitBtn.trigger('click')

      expect(portalStore.cart).toHaveLength(1)
      expect(portalStore.cart[0].product_id).toBe(101)
      expect(portalStore.cart[0].qty).toBe(6)
      expect(mockPush).toHaveBeenCalledWith('/portal/cart')
    })

    it('opens cancel modal and executes cancellation for pending/confirmed order', async () => {
      const wrapper = mount(PortalOrdersView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const cancelBtn = wrapper.find('.btn-cancel')
      expect(cancelBtn.exists()).toBe(true)
      await cancelBtn.trigger('click')

      expect(wrapper.find('.cancel-modal-card').exists()).toBe(true)

      const cancelSpy = vi.spyOn(portalStore, 'cancelOrder').mockResolvedValueOnce({
        id: 501,
        status: 'Cancelled',
      })

      const confirmCancelBtn = wrapper.find('.cancel-modal-card .btn-danger')
      await confirmCancelBtn.trigger('click')

      expect(cancelSpy).toHaveBeenCalledWith(501, '')
    })
  })

  // ------------------------------------------------------------------------
  // PortalOrderDetailView Tests
  // ------------------------------------------------------------------------
  describe('PortalOrderDetailView', () => {
    it('renders order header, fulfillment tracker steps, summary cards, and itemized lines table', () => {
      const wrapper = mount(PortalOrderDetailView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('Sales Order #SO-20260825-001')
      expect(wrapper.text()).toContain('Fulfillment & Delivery Progress')
      expect(wrapper.text()).toContain('Order Information')
      expect(wrapper.text()).toContain('Payment & Invoice Summary')
      expect(wrapper.text()).toContain('Itemized Order Line Items (1)')
      expect(wrapper.text()).toContain('Espresso Roast Beans 1kg')
      expect(wrapper.text()).toContain('COF-001')
      expect(wrapper.text()).toContain('$147.00')
      expect(wrapper.find('.fulfillment-tracker-card').exists()).toBe(true)
    })

    it('loads items directly into replenishment cart from detail view', async () => {
      const wrapper = mount(PortalOrderDetailView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const loadCartBtn = wrapper.find('.btn-action-secondary')
      expect(loadCartBtn.exists()).toBe(true)
      await loadCartBtn.trigger('click')

      expect(portalStore.cart).toHaveLength(1)
      expect(portalStore.cart[0].product_id).toBe(101)
      expect(portalStore.cart[0].qty).toBe(6)
      expect(mockPush).toHaveBeenCalledWith('/portal/cart')
    })

    it('opens reorder modal from detail view and executes 1-click reorder', async () => {
      const wrapper = mount(PortalOrderDetailView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const reorderBtn = wrapper.find('.btn-action-primary')
      await reorderBtn.trigger('click')

      expect(wrapper.find('.reorder-modal-card').exists()).toBe(true)

      const reorderSpy = vi.spyOn(portalStore, 'reorderPastOrder').mockResolvedValueOnce({
        id: 998,
        order_number: 'SO-20260827-0998',
      })

      const confirmBtn = wrapper.find('.modal-footer .btn-primary')
      await confirmBtn.trigger('click')

      expect(reorderSpy).toHaveBeenCalledWith(501, expect.any(Object))
      expect(mockPush).toHaveBeenCalledWith('/portal/orders/998')
    })

    it('cancels order from detail view and updates view', async () => {
      const wrapper = mount(PortalOrderDetailView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const cancelBtn = wrapper.find('.btn-action-danger')
      expect(cancelBtn.exists()).toBe(true)
      await cancelBtn.trigger('click')

      expect(wrapper.find('.cancel-modal-card').exists()).toBe(true)

      const cancelSpy = vi.spyOn(portalStore, 'cancelOrder').mockResolvedValueOnce({
        id: 501,
        status: 'Cancelled',
      })

      const confirmCancelBtn = wrapper.find('.cancel-modal-card .btn-danger')
      await confirmCancelBtn.trigger('click')

      expect(cancelSpy).toHaveBeenCalledWith(501, '')
    })
  })

  // ------------------------------------------------------------------------
  // PortalDashboardView Tests
  // ------------------------------------------------------------------------
  describe('PortalDashboardView', () => {
    it('renders hero welcome, company name, meta tags, and financial KPI summary cards', () => {
      const wrapper = mount(PortalDashboardView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('Welcome back')
      expect(wrapper.text()).toContain('Artisan Cafe Ltd')
      expect(wrapper.text()).toContain('Outstanding Balance')
      expect(wrapper.text()).toContain('Available Credit')
      expect(wrapper.text()).toContain('$2500.00')
      expect(wrapper.text()).toContain('Next Scheduled Delivery')
      expect(wrapper.text()).toContain('Orders in Fulfillment')
      expect(wrapper.text()).toContain('Recent Orders & 1-Click Reorder')
      expect(wrapper.text()).toContain('Open Invoices & Settlement')
    })

    it('renders recent orders and open invoices list items', () => {
      const wrapper = mount(PortalDashboardView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('SO-20260825-001')
      expect(wrapper.text()).toContain('INV-2026-0301')
      expect(wrapper.text()).toContain('INV-2026-0303')
    })

    it('opens single invoice payment modal and initiates Stripe checkout', async () => {
      const wrapper = mount(PortalDashboardView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const payBtn = wrapper.findAll('.btn-mini-pay')[0]
      expect(payBtn.exists()).toBe(true)
      await payBtn.trigger('click')

      expect(wrapper.text()).toContain('Settle Invoice Online')
      expect(wrapper.text()).toContain('INV-2026-0301')

      const sessionSpy = vi.spyOn(portalStore, 'createInvoiceCheckoutSession').mockResolvedValueOnce({
        session_id: 'cs_test_inv_301',
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_inv_301',
      })

      const proceedBtn = wrapper.find('.modal-footer .btn-primary')
      await proceedBtn.trigger('click')

      expect(sessionSpy).toHaveBeenCalledWith(301, expect.any(Object))
    })

    it('opens balance settlement modal from hero/kpi and initiates balance Stripe checkout', async () => {
      const wrapper = mount(PortalDashboardView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const payBalanceBtn = wrapper.find('.btn-kpi-pay')
      expect(payBalanceBtn.exists()).toBe(true)
      await payBalanceBtn.trigger('click')

      expect(wrapper.text()).toContain('Settle Account Balance')

      const balanceSessionSpy = vi.spyOn(portalStore, 'createBalanceCheckoutSession').mockResolvedValueOnce({
        session_id: 'cs_test_bal_999',
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_bal_999',
      })

      const proceedBtn = wrapper.find('.modal-footer .btn-primary')
      await proceedBtn.trigger('click')

      expect(balanceSessionSpy).toHaveBeenCalledWith(expect.any(Number), expect.any(Object))
    })

    it('quick adds contracted product from dashboard highlight carousel to cart', async () => {
      const wrapper = mount(PortalDashboardView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const quickAddBtn = wrapper.find('.btn-quick-add')
      expect(quickAddBtn.exists()).toBe(true)
      await quickAddBtn.trigger('click')

      expect(portalStore.cart).toHaveLength(1)
      expect(portalStore.cart[0].product_id).toBe(101)
      expect(portalStore.cart[0].qty).toBe(1)
    })
  })

  // ------------------------------------------------------------------------
  // PortalInvoicesView Tests
  // ------------------------------------------------------------------------
  describe('PortalInvoicesView', () => {
    it('renders financial metrics, status tabs, search bar, and invoices table', () => {
      const wrapper = mount(PortalInvoicesView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      expect(wrapper.text()).toContain('Invoices & Online Settlement')
      expect(wrapper.text()).toContain('Total Balance Due')
      expect(wrapper.text()).toContain('Settled Invoices')
      expect(wrapper.text()).toContain('Payment Methods')
      expect(wrapper.text()).toContain('INV-2026-0301')
      expect(wrapper.text()).toContain('INV-2026-0302')
      expect(wrapper.text()).toContain('INV-2026-0303')
      expect(wrapper.text()).toContain('$147.00')
      expect(wrapper.text()).toContain('$76.00')
      expect(wrapper.text()).toContain('Paid')
      expect(wrapper.text()).toContain('Unpaid')
    })

    it('filters invoices by search query and status tabs', async () => {
      const wrapper = mount(PortalInvoicesView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      // Search filter
      const searchInput = wrapper.find('.filter-search-input')
      await searchInput.setValue('INV-2026-0302')

      expect(wrapper.text()).toContain('INV-2026-0302')
      expect(wrapper.text()).not.toContain('INV-2026-0301')

      // Clear search
      await searchInput.setValue('')

      // Status tab: Unpaid
      const unpaidTab = wrapper.findAll('.status-tab-btn')[1]
      await unpaidTab.trigger('click')

      expect(wrapper.text()).toContain('INV-2026-0301')
      expect(wrapper.text()).toContain('INV-2026-0303')
      expect(wrapper.text()).not.toContain('INV-2026-0302')

      // Status tab: Paid
      const paidTab = wrapper.findAll('.status-tab-btn')[2]
      await paidTab.trigger('click')

      expect(wrapper.text()).toContain('INV-2026-0302')
      expect(wrapper.text()).not.toContain('INV-2026-0301')
    })

    it('downloads PDF invoice when PDF button is clicked', async () => {
      const wrapper = mount(PortalInvoicesView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const pdfSpy = vi.spyOn(portalStore, 'downloadInvoicePdf').mockResolvedValueOnce(true)

      const pdfBtn = wrapper.findAll('.btn-action-pdf')[0]
      expect(pdfBtn.exists()).toBe(true)
      await pdfBtn.trigger('click')

      expect(pdfSpy).toHaveBeenCalledWith(301)
    })

    it('opens single invoice payment modal and proceeds to Stripe checkout', async () => {
      const wrapper = mount(PortalInvoicesView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const payBtn = wrapper.findAll('.btn-action-pay')[0]
      expect(payBtn.exists()).toBe(true)
      await payBtn.trigger('click')

      expect(wrapper.text()).toContain('Settle Invoice Online')
      expect(wrapper.text()).toContain('INV-2026-0301')

      const checkoutSpy = vi.spyOn(portalStore, 'createInvoiceCheckoutSession').mockResolvedValueOnce({
        session_id: 'cs_test_301',
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_301',
      })

      const proceedBtn = wrapper.find('.modal-footer .btn-primary')
      await proceedBtn.trigger('click')

      expect(checkoutSpy).toHaveBeenCalledWith(301, expect.any(Object))
    })

    it('opens balance settlement modal from header action and proceeds to checkout', async () => {
      const wrapper = mount(PortalInvoicesView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      const settleBalanceBtn = wrapper.find('.btn-pay-balance-hero')
      expect(settleBalanceBtn.exists()).toBe(true)
      await settleBalanceBtn.trigger('click')

      expect(wrapper.text()).toContain('Settle Full Account Balance')

      const balanceSpy = vi.spyOn(portalStore, 'createBalanceCheckoutSession').mockResolvedValueOnce({
        session_id: 'cs_test_bal_full',
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_bal_full',
      })

      const proceedBtn = wrapper.find('.modal-footer .btn-primary')
      await proceedBtn.trigger('click')

      expect(balanceSpy).toHaveBeenCalledWith(expect.any(Number), expect.any(Object))
    })
  })

  // ------------------------------------------------------------------------
  // PortalPaymentResultView Tests
  // ------------------------------------------------------------------------
  describe('PortalPaymentResultView', () => {
    it('verifies payment session and displays success state with reconciled amount', async () => {
      mockRoute.query = { session_id: 'cs_test_123', invoice_id: '301' }

      const wrapper = mount(PortalPaymentResultView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      // Wait for async verifyPayment
      await new Promise(resolve => setTimeout(resolve, 50))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Payment Successful & Reconciled!')
      expect(wrapper.text()).toContain('$147.00')
      expect(wrapper.text()).toContain('buyer@artisancafe.com')
      expect(wrapper.text()).toContain('cs_test_123')
      expect(wrapper.text()).toContain('#301')
      expect(wrapper.text()).toContain('Nova ERP accounts receivable records and balancing journal entries have been registered')
    })

    it('downloads invoice PDF receipt from payment result page', async () => {
      mockRoute.query = { session_id: 'cs_test_123', invoice_id: '301' }

      const wrapper = mount(PortalPaymentResultView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      await new Promise(resolve => setTimeout(resolve, 50))
      await wrapper.vm.$nextTick()

      const downloadPdfSpy = vi.spyOn(portalStore, 'downloadInvoicePdf').mockResolvedValueOnce(true)

      const downloadBtn = wrapper.find('.btn-result-download')
      expect(downloadBtn.exists()).toBe(true)
      await downloadBtn.trigger('click')

      expect(downloadPdfSpy).toHaveBeenCalledWith('301')
    })

    it('displays ACH processing state when status is processing/unpaid', async () => {
      mockRoute.query = { session_id: 'cs_test_ach_456' }

      api.get.mockImplementation(url => {
        if (url.startsWith('/portal/settlement/session/')) {
          return Promise.resolve({
            data: {
              session_id: 'cs_test_ach_456',
              status: 'processing',
              payment_status: 'unpaid',
              amount_total: 50000,
              currency: 'usd',
            },
          })
        }
        return Promise.resolve({ data: {} })
      })

      const wrapper = mount(PortalPaymentResultView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      await new Promise(resolve => setTimeout(resolve, 50))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('ACH Bank Transfer Initiated')
      expect(wrapper.text()).toContain('2-4 business days')
      expect(wrapper.text()).toContain('$500.00')
    })

    it('displays cancelled state when status query indicates cancellation', async () => {
      mockRoute.query = { status: 'cancelled' }

      const wrapper = mount(PortalPaymentResultView, {
        global: {
          plugins: [pinia],
          stubs: { RouterLink: { template: '<a><slot /></a>' } },
        },
      })

      await new Promise(resolve => setTimeout(resolve, 50))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('Payment Not Completed')
      expect(wrapper.text()).toContain('cancelled')
      expect(wrapper.find('.state-error').exists()).toBe(true)
    })
  })
})

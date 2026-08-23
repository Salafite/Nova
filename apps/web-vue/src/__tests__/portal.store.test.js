import { setActivePinia, createPinia } from 'pinia'
import { usePortalStore } from '../stores/portal.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
  CONFIG: { apiBase: 'http://test.local' },
}))

const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] ?? null),
    setItem: vi.fn((key, val) => { store[key] = val }),
    removeItem: vi.fn(key => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('Customer Portal Store (usePortalStore)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  // ------------------------------------------------------------------------
  // 1. Initial State & Cart Management
  // ------------------------------------------------------------------------
  describe('initial state and cart management', () => {
    it('initializes with empty cart and expected default state', () => {
      const store = usePortalStore()
      expect(store.cart).toEqual([])
      expect(store.cartCount).toBe(0)
      expect(store.cartItemCount).toBe(0)
      expect(store.cartUniqueItemCount).toBe(0)
      expect(store.cartSubtotal).toBe(0)
      expect(store.cartTaxTotal).toBe(0)
      expect(store.cartGrandTotal).toBe(0)
      expect(store.meetsMinimumOrder).toBe(true)
      expect(store.meetsMinOrder).toBe(true)
      expect(store.minOrderAmount).toBe(0)
      expect(store.minOrderDifference).toBe(0)
      expect(store.minOrderShortfall).toBe(0)
      expect(store.minOrderProgress).toBe(100)
      expect(store.allowReorders).toBe(true)
      expect(store.catalogCategories).toEqual([])
    })

    it('adds product with contracted pricing and tax calculation to cart', () => {
      const store = usePortalStore()
      const product = {
        id: 101,
        product_code: 'COF-001',
        product_name: 'Espresso Roast Beans',
        contracted_price: 24.50,
        base_price: 30.00,
        uom_name: 'Bag 1kg',
        tax_rate: 10.0,
        is_contracted: true,
      }

      store.addToCart(product, 2)

      expect(store.cart).toHaveLength(1)
      expect(store.cart[0].product_id).toBe(101)
      expect(store.cart[0].qty).toBe(2)
      expect(store.cart[0].quantity).toBe(2)
      expect(store.cart[0].unit_price).toBe(24.50)
      expect(store.cart[0].is_contracted).toBe(true)
      expect(store.cartCount).toBe(2)
      expect(store.cartItemCount).toBe(2)
      expect(store.cartUniqueItemCount).toBe(1)
      expect(store.cartSubtotal).toBe(49.00)
      expect(store.cartTaxTotal).toBe(4.90)
      expect(store.cartGrandTotal).toBe(53.90)
    })

    it('increments quantity and recalculates totals when adding same item multiple times', () => {
      const store = usePortalStore()
      const product = {
        id: 101,
        product_code: 'COF-001',
        product_name: 'Espresso Roast Beans',
        contracted_price: 20.00,
      }

      store.addToCart(product, 2)
      store.addToCart(product, 3)

      expect(store.cart).toHaveLength(1)
      expect(store.cart[0].qty).toBe(5)
      expect(store.cart[0].quantity).toBe(5)
      expect(store.cartCount).toBe(5)
      expect(store.cartSubtotal).toBe(100.00)
    })

    it('ignores non-positive quantities when adding to cart', () => {
      const store = usePortalStore()
      store.addToCart({ id: 1, contracted_price: 10.0 }, 0)
      store.addToCart({ id: 2, contracted_price: 10.0 }, -2)
      expect(store.cart).toHaveLength(0)
    })

    it('updates quantity and removes item when set to 0', () => {
      const store = usePortalStore()
      store.addToCart({ id: 101, contracted_price: 10.0 }, 3)

      store.updateCartQty(101, 7)
      expect(store.cart[0].qty).toBe(7)
      expect(store.cart[0].quantity).toBe(7)
      expect(store.cartSubtotal).toBe(70.00)

      store.updateCartQuantity(101, 0)
      expect(store.cart).toHaveLength(0)
      expect(store.cartCount).toBe(0)
      expect(store.cartSubtotal).toBe(0)
    })

    it('removes specific item from cart and clears cart completely', () => {
      const store = usePortalStore()
      store.addToCart({ id: 1, contracted_price: 10 }, 1)
      store.addToCart({ id: 2, contracted_price: 20 }, 2)

      expect(store.cart).toHaveLength(2)
      store.removeFromCart(1)
      expect(store.cart).toHaveLength(1)
      expect(store.cart[0].product_id).toBe(2)

      store.clearCart()
      expect(store.cart).toHaveLength(0)
      expect(store.cartSubtotal).toBe(0)
    })

    it('loads order lines into cart in replace mode and append mode', () => {
      const store = usePortalStore()
      store.addToCart({ id: 999, contracted_price: 50 }, 1)

      const pastOrder = {
        id: 42,
        lines: [
          { product_id: 10, product_name: 'Oat Milk 1L', qty: 12, unit_price: 3.50, uom_name: 'Carton' },
          { product_id: 20, product_name: 'White Sugar 5kg', quantity: 2, unit_price: 8.00, uom_name: 'Bag' },
        ],
      }

      // Replace mode
      const count1 = store.loadOrderToCart(pastOrder, true)
      expect(count1).toBe(2)
      expect(store.cart).toHaveLength(2)
      expect(store.cart[0].product_id).toBe(10)
      expect(store.cart[0].qty).toBe(12)
      expect(store.cart[1].product_id).toBe(20)
      expect(store.cart[1].qty).toBe(2)
      expect(store.cartSubtotal).toBe(12 * 3.50 + 2 * 8.00)

      // Append mode
      const additionalOrder = {
        lines: [
          { product_id: 30, product_name: 'Syrup 750ml', qty: 1, unit_price: 15.00 },
        ],
      }
      const count2 = store.loadOrderToCart(additionalOrder, false)
      expect(count2).toBe(1)
      expect(store.cart).toHaveLength(3)
    })
  })

  // ------------------------------------------------------------------------
  // 2. Minimum Order Requirement & Cutoff Status
  // ------------------------------------------------------------------------
  describe('minimum order validation and cutoff enforcement', () => {
    it('computes minimum order compliance, shortfall, and progress', () => {
      const store = usePortalStore()
      store.accountSummary = {
        customer_id: 1,
        min_order_amount: 200.00,
        allow_reorders: true,
      }

      expect(store.minOrderAmount).toBe(200.00)
      expect(store.meetsMinOrder).toBe(false)
      expect(store.meetsMinimumOrder).toBe(false)
      expect(store.minOrderShortfall).toBe(200.00)
      expect(store.minOrderDifference).toBe(200.00)
      expect(store.minOrderProgress).toBe(0)

      // Add partial items
      store.addToCart({ id: 1, contracted_price: 150 }, 1)
      expect(store.meetsMinOrder).toBe(false)
      expect(store.minOrderShortfall).toBe(50.00)
      expect(store.minOrderProgress).toBe(75)

      // Add item to meet threshold
      store.addToCart({ id: 2, contracted_price: 50 }, 1)
      expect(store.meetsMinOrder).toBe(true)
      expect(store.minOrderShortfall).toBe(0)
      expect(store.minOrderProgress).toBe(100)
    })

    it('computes cutoff status and next delivery dates correctly', () => {
      const store = usePortalStore()
      store.cutoffStatus = {
        is_past_cutoff: false,
        cutoff_time: '22:00:00',
        next_delivery_date: '2026-08-24',
        message: 'Order before 22:00 for next-day delivery',
      }

      expect(store.isPastCutoff).toBe(false)
      expect(store.nextDeliveryDate).toBe('2026-08-24')

      // When past cutoff
      store.cutoffStatus = {
        is_past_cutoff: true,
        cutoff_time: '22:00:00',
        next_delivery_date: '2026-08-25',
        message: 'Daily cutoff passed, delivery scheduled for D+2',
      }

      expect(store.isPastCutoff).toBe(true)
      expect(store.nextDeliveryDate).toBe('2026-08-25')
    })
  })

  // ------------------------------------------------------------------------
  // 3. API Actions: Catalog & Account Summary
  // ------------------------------------------------------------------------
  describe('catalog and account API actions', () => {
    it('fetches catalog with category filters and pagination', async () => {
      const store = usePortalStore()
      const mockItems = [
        { id: 1, product_name: 'Whole Milk', category_id: 1, contracted_price: 3.50 },
        { id: 2, product_name: 'Almond Milk', category_id: 1, contracted_price: 4.20 },
      ]
      const mockCategories = [
        { id: 1, category_name: 'Dairy', item_count: 2 },
      ]

      api.get.mockResolvedValueOnce({
        data: {
          items: mockItems,
          total: 2,
          page: 1,
          limit: 50,
          categories: mockCategories,
        },
      })

      const res = await store.fetchCatalog({ categoryId: 1, search: 'Milk', inStockOnly: true })
      expect(res.items).toHaveLength(2)
      expect(store.catalog).toEqual(mockItems)
      expect(store.catalogCategories).toEqual(mockCategories)
      expect(store.categories).toEqual(mockCategories)
      expect(store.catalogLoading).toBe(false)
      expect(api.get).toHaveBeenCalledWith('/portal/catalog', {
        params: {
          page: 1,
          limit: 50,
          category_id: 1,
          search: 'Milk',
          in_stock_only: true,
        },
      })
    })

    it('handles catalog fetch failure gracefully', async () => {
      const store = usePortalStore()
      api.get.mockRejectedValueOnce({ response: { data: { detail: 'Server unavailable' } } })

      const res = await store.fetchCatalog()
      expect(res).toBeNull()
      expect(store.catalogError).toBe('Server unavailable')
      expect(store.catalogLoading).toBe(false)
    })

    it('fetches account summary and updates store state', async () => {
      const store = usePortalStore()
      const mockSummary = {
        customer_id: 5,
        customer_name: 'The French Bistro',
        outstanding_balance: 1450.00,
        current_balance: 1450.00,
        credit_limit: 5000.00,
        available_credit: 3550.00,
        min_order_amount: 150.00,
        allow_reorders: true,
      }
      api.get.mockResolvedValueOnce({ data: mockSummary })

      const res = await store.fetchAccountSummary()
      expect(res).toEqual(mockSummary)
      expect(store.accountSummary).toEqual(mockSummary)
      expect(store.allowReorders).toBe(true)
      expect(store.minOrderAmount).toBe(150.00)
    })

    it('fetches cutoff status and updates state', async () => {
      const store = usePortalStore()
      const mockCutoff = {
        is_past_cutoff: false,
        cutoff_time: '22:00',
        next_delivery_date: '2026-08-24',
      }
      api.get.mockResolvedValueOnce({ data: mockCutoff })

      const res = await store.fetchCutoffStatus()
      expect(res).toEqual(mockCutoff)
      expect(store.cutoffStatus).toEqual(mockCutoff)
    })

    it('validates cart through backend endpoint', async () => {
      const store = usePortalStore()
      store.addToCart({ id: 1, contracted_price: 50.0 }, 2)

      const mockValRes = {
        is_valid: true,
        subtotal: 100.0,
        min_order_amount: 100.0,
        meets_minimum: true,
      }
      api.post.mockResolvedValueOnce({ data: mockValRes })

      const result = await store.validateCart()
      expect(result).toEqual(mockValRes)
      expect(api.post).toHaveBeenCalledWith('/portal/orders/validate', [
        { product_id: 1, qty: 2, notes: null },
      ])
    })
  })

  // ------------------------------------------------------------------------
  // 4. Order Management & Reordering Actions
  // ------------------------------------------------------------------------
  describe('order placement, retrieval, and reordering', () => {
    it('creates order, clears cart, and refreshes summary on success', async () => {
      const store = usePortalStore()
      store.addToCart({ id: 10, contracted_price: 25.0 }, 4)
      expect(store.cart).toHaveLength(1)

      const mockOrderResponse = {
        id: 88,
        order_number: 'ORD-2026-0088',
        customer_id: 5,
        status: 'Confirmed',
        total_amount: 100.0,
        requested_delivery_date: '2026-08-25',
      }
      api.post.mockResolvedValueOnce({ data: mockOrderResponse })
      api.get.mockResolvedValueOnce({ data: { customer_id: 5, current_balance: 1550.0 } })

      const res = await store.createOrder({
        requested_delivery_date: '2026-08-25',
        notes: 'Deliver to rear kitchen entrance',
        status: 'Confirmed',
      })

      expect(res).toEqual(mockOrderResponse)
      expect(store.cart).toHaveLength(0)
      expect(api.post).toHaveBeenCalledWith('/portal/orders', {
        items: [{ product_id: 10, qty: 4, notes: null }],
        warehouse_id: null,
        requested_delivery_date: '2026-08-25',
        notes: 'Deliver to rear kitchen entrance',
        status: 'Confirmed',
      })
    })

    it('fetches order history with status filters and loads order detail', async () => {
      const store = usePortalStore()
      const mockOrders = [
        { id: 1, order_number: 'ORD-001', status: 'Confirmed', total_amount: 250.0 },
        { id: 2, order_number: 'ORD-002', status: 'Delivered', total_amount: 400.0 },
      ]
      api.get.mockResolvedValueOnce({ data: { items: mockOrders, total: 2, page: 1, limit: 20 } })

      await store.fetchOrders({ status: 'Confirmed' })
      expect(store.orders).toHaveLength(2)
      expect(api.get).toHaveBeenCalledWith('/portal/orders', {
        params: { page: 1, limit: 20, status: 'Confirmed', status_filter: 'Confirmed' },
      })

      // Fetch single order detail
      const mockDetail = { id: 1, order_number: 'ORD-001', lines: [{ product_id: 10, qty: 2 }] }
      api.get.mockResolvedValueOnce({ data: mockDetail })
      const detail = await store.fetchOrderDetail(1)
      expect(detail).toEqual(mockDetail)
      expect(store.currentOrder).toEqual(mockDetail)
    })

    it('submits 1-click reorder and cancels existing unfulfilled order', async () => {
      const store = usePortalStore()
      store.orders = [
        { id: 50, order_number: 'ORD-050', status: 'Confirmed' },
      ]

      // Reorder
      const reorderRes = { id: 51, order_number: 'ORD-051', status: 'Confirmed' }
      api.post.mockResolvedValueOnce({ data: reorderRes })
      api.get.mockResolvedValueOnce({ data: { customer_id: 1 } }) // summary refresh
      const reorder = await store.reorderPastOrder(50, { requested_delivery_date: '2026-08-26' })
      expect(reorder).toEqual(reorderRes)
      expect(api.post).toHaveBeenCalledWith('/portal/orders/50/reorder', {
        order_id: 50,
        requested_delivery_date: '2026-08-26',
        notes: null,
        status: 'Confirmed',
      })

      // Cancel
      const cancelledRes = { id: 50, order_number: 'ORD-050', status: 'Cancelled' }
      api.post.mockResolvedValueOnce({ data: cancelledRes })
      api.get.mockResolvedValueOnce({ data: { customer_id: 1 } }) // summary refresh
      const cancelled = await store.cancelOrder(50, 'Duplicate order placed')
      expect(cancelled).toEqual(cancelledRes)
      expect(store.orders[0].status).toBe('Cancelled')
    })
  })

  // ------------------------------------------------------------------------
  // 5. Invoices & Stripe Settlement Actions
  // ------------------------------------------------------------------------
  describe('invoices, PDF generation, and Stripe settlement', () => {
    it('calculates unpaid invoices, paid invoices, and open balance correctly', async () => {
      const store = usePortalStore()
      const mockInvoices = [
        { id: 1, invoice_number: 'INV-001', status: 'Unpaid', total_amount: 600.0, balance_due: 600.0 },
        { id: 2, invoice_number: 'INV-002', status: 'Partially Paid', total_amount: 1000.0, balance_due: 400.0 },
        { id: 3, invoice_number: 'INV-003', status: 'Paid', total_amount: 350.0, balance_due: 0.0 },
      ]
      api.get.mockResolvedValueOnce({ data: { items: mockInvoices, total: 3, page: 1, limit: 20 } })

      await store.fetchInvoices()
      expect(store.invoices).toHaveLength(3)
      expect(store.unpaidInvoices).toHaveLength(2)
      expect(store.paidInvoices).toHaveLength(1)
      expect(store.totalUnpaidBalance).toBe(1000.0) // 600 + 400
    })

    it('creates invoice checkout session with Stripe Card and ACH methods', async () => {
      const store = usePortalStore()
      const mockSession = {
        session_id: 'cs_test_inv_123',
        checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_inv_123',
      }
      api.post.mockResolvedValueOnce({ data: mockSession })

      const res = await store.createInvoiceCheckoutSession(42)
      expect(res).toEqual(mockSession)
      expect(store.checkoutSession).toEqual(mockSession)
      expect(api.post).toHaveBeenCalledWith(
        '/portal/invoices/42/checkout-session',
        expect.objectContaining({
          invoice_id: 42,
          payment_method_types: ['card', 'us_bank_account'],
        })
      )
    })

    it('creates aggregate balance settlement checkout session', async () => {
      const store = usePortalStore()
      const mockSession = {
        session_id: 'cs_test_bal_456',
        checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_bal_456',
      }
      api.post.mockResolvedValueOnce({ data: mockSession })

      const res = await store.createBalanceCheckoutSession(1000.0, { invoiceIds: [1, 2] })
      expect(res).toEqual(mockSession)
      expect(api.post).toHaveBeenCalledWith(
        '/portal/settlement/checkout-session',
        expect.objectContaining({
          amount: 1000.0,
          invoice_ids: [1, 2],
          payment_method_types: ['card', 'us_bank_account'],
        })
      )
    })

    it('fetches and verifies payment session status and triggers refreshes', async () => {
      const store = usePortalStore()
      const mockStatus = {
        session_id: 'cs_test_xyz',
        status: 'complete',
        payment_status: 'paid',
        amount_total: 60000,
        settlement_type: 'invoice',
        reconciled: true,
      }
      api.get.mockResolvedValueOnce({ data: mockStatus })
      api.get.mockResolvedValueOnce({ data: { current_balance: 400.0 } }) // summary
      api.get.mockResolvedValueOnce({ data: { items: [], total: 0 } }) // invoices

      const res = await store.fetchPaymentSessionStatus('cs_test_xyz', true)
      expect(res).toEqual(mockStatus)
      expect(store.paymentStatus).toEqual(mockStatus)
      expect(api.get).toHaveBeenCalledWith('/portal/settlement/session/cs_test_xyz', {
        params: { verify: true },
      })
    })

    it('downloads invoice PDF using browser blob object URL', async () => {
      const store = usePortalStore()
      const mockBlob = new Blob(['%PDF-1.4 Mock PDF Content'], { type: 'application/pdf' })
      api.get.mockResolvedValueOnce({ data: mockBlob })

      // Mock DOM URL methods
      const createObjectURLMock = vi.fn(() => 'blob:http://test.local/mock-pdf')
      const revokeObjectURLMock = vi.fn()
      window.URL.createObjectURL = createObjectURLMock
      window.URL.revokeObjectURL = revokeObjectURLMock

      const res = await store.downloadInvoicePdf(42)
      expect(res).toBe(true)
      expect(api.get).toHaveBeenCalledWith('/portal/invoices/42/pdf', {
        responseType: 'blob',
      })
      expect(createObjectURLMock).toHaveBeenCalled()
      expect(revokeObjectURLMock).toHaveBeenCalled()
    })
  })
})


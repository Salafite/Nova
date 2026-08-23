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

describe('portal store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  describe('initial state and cart management', () => {
    it('initializes with empty cart and default state', () => {
      const store = usePortalStore()
      expect(store.cart).toEqual([])
      expect(store.cartCount).toBe(0)
      expect(store.cartSubtotal).toBe(0)
      expect(store.cartTaxTotal).toBe(0)
      expect(store.cartGrandTotal).toBe(0)
      expect(store.meetsMinimumOrder).toBe(true)
      expect(store.allowReorders).toBe(true)
    })

    it('adds new product to cart with contracted price', () => {
      const store = usePortalStore()
      const product = {
        id: 101,
        product_code: 'BEV-001',
        product_name: 'Premium Coffee Beans',
        contracted_price: 24.50,
        base_price: 30.00,
        uom_name: 'Bag 1kg',
        tax_rate: 10.0,
      }

      store.addToCart(product, 2)
      expect(store.cart).toHaveLength(1)
      expect(store.cart[0].product_id).toBe(101)
      expect(store.cart[0].quantity).toBe(2)
      expect(store.cart[0].unit_price).toBe(24.50)
      expect(store.cartCount).toBe(2)
      expect(store.cartSubtotal).toBe(49.00)
      expect(store.cartTaxTotal).toBe(4.90)
      expect(store.cartGrandTotal).toBe(53.90)
    })

    it('increments quantity when adding same product again', () => {
      const store = usePortalStore()
      const product = {
        id: 101,
        product_code: 'BEV-001',
        product_name: 'Premium Coffee Beans',
        contracted_price: 25.00,
      }

      store.addToCart(product, 2)
      store.addToCart(product, 3)

      expect(store.cart).toHaveLength(1)
      expect(store.cart[0].quantity).toBe(5)
      expect(store.cartSubtotal).toBe(125.00)
    })

    it('updates quantity and removes item when set to 0', () => {
      const store = usePortalStore()
      const product = { id: 101, contracted_price: 10.0 }
      store.addToCart(product, 3)

      store.updateCartQuantity(101, 5)
      expect(store.cart[0].quantity).toBe(5)
      expect(store.cartSubtotal).toBe(50.00)

      store.updateCartQuantity(101, 0)
      expect(store.cart).toHaveLength(0)
      expect(store.cartCount).toBe(0)
    })

    it('removes item and clears cart', () => {
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

    it('loads past order lines into cart', () => {
      const store = usePortalStore()
      const pastOrder = {
        id: 42,
        lines: [
          { product_id: 10, product_name: 'Oat Milk 1L', quantity: 12, unit_price: 3.50, uom_name: 'Carton' },
          { product_id: 20, product_name: 'Sugar 5kg', quantity: 2, unit_price: 8.00, uom_name: 'Bag' },
        ],
      }

      store.loadOrderToCart(pastOrder, true)
      expect(store.cart).toHaveLength(2)
      expect(store.cart[0].product_id).toBe(10)
      expect(store.cart[0].quantity).toBe(12)
      expect(store.cart[1].product_id).toBe(20)
      expect(store.cart[1].quantity).toBe(2)
      expect(store.cartSubtotal).toBe(12 * 3.50 + 2 * 8.00)
    })
  })

  describe('minimum order validation and cutoff enforcement', () => {
    it('computes minimum order compliance correctly', () => {
      const store = usePortalStore()
      store.accountSummary = {
        customer_id: 1,
        min_order_amount: 150.00,
      }

      expect(store.minOrderAmount).toBe(150.00)
      expect(store.meetsMinimumOrder).toBe(false)
      expect(store.minOrderDifference).toBe(150.00)

      store.addToCart({ id: 1, contracted_price: 100 }, 1)
      expect(store.meetsMinimumOrder).toBe(false)
      expect(store.minOrderDifference).toBe(50.00)

      store.addToCart({ id: 2, contracted_price: 60 }, 1)
      expect(store.meetsMinimumOrder).toBe(true)
      expect(store.minOrderDifference).toBe(0)
    })

    it('computes cutoff status and next delivery date', () => {
      const store = usePortalStore()
      store.cutoffStatus = {
        is_past_cutoff: false,
        cutoff_time: '22:00',
        next_delivery_date: '2026-08-24',
      }

      expect(store.isPastCutoff).toBe(false)
      expect(store.nextDeliveryDate).toBe('2026-08-24')

      store.cutoffStatus.is_past_cutoff = true
      store.cutoffStatus.next_delivery_date = '2026-08-25'
      expect(store.isPastCutoff).toBe(true)
      expect(store.nextDeliveryDate).toBe('2026-08-25')
    })
  })

  describe('API actions and invoice calculations', () => {
    it('fetches account summary successfully', async () => {
      const store = usePortalStore()
      const mockSummary = {
        customer_id: 5,
        customer_name: 'Acme Coffee Co',
        outstanding_balance: 1250.00,
        credit_limit: 5000.00,
        available_credit: 3750.00,
        min_order_amount: 100.00,
        allow_reorders: true,
      }
      api.get.mockResolvedValueOnce({ data: mockSummary })

      const res = await store.fetchAccountSummary()
      expect(res).toEqual(mockSummary)
      expect(store.accountSummary.customer_name).toBe('Acme Coffee Co')
      expect(api.get).toHaveBeenCalledWith('/portal/account/summary')
    })

    it('fetches catalog with categories', async () => {
      const store = usePortalStore()
      const mockCatalog = [
        { id: 1, product_name: 'Beans', category_id: 10, category_name: 'Coffee' },
        { id: 2, product_name: 'Milk', category_id: 20, category_name: 'Dairy' },
      ]
      api.get.mockResolvedValueOnce({ data: { items: mockCatalog, total: 2 } })

      await store.fetchCatalog()
      expect(store.catalog).toHaveLength(2)
      expect(store.catalogCategories).toHaveLength(2)
      expect(store.catalogCategories[0].name).toBe('Coffee')
    })

    it('calculates unpaid invoices and total open balance', async () => {
      const store = usePortalStore()
      const mockInvoices = [
        { id: 1, invoice_number: 'INV-001', status: 'Unpaid', total_amount: 500.00, balance_due: 500.00 },
        { id: 2, invoice_number: 'INV-002', status: 'Partially Paid', total_amount: 800.00, balance_due: 300.00 },
        { id: 3, invoice_number: 'INV-003', status: 'Paid', total_amount: 400.00, balance_due: 0.00 },
      ]
      api.get.mockResolvedValueOnce({ data: { items: mockInvoices, total: 3 } })

      await store.fetchInvoices()
      expect(store.invoices).toHaveLength(3)
      expect(store.unpaidInvoices).toHaveLength(2)
      expect(store.paidInvoices).toHaveLength(1)
      expect(store.totalUnpaidBalance).toBe(800.00)
    })

    it('creates order and clears cart on success', async () => {
      const store = usePortalStore()
      store.addToCart({ id: 1, contracted_price: 50 }, 2)
      expect(store.cart).toHaveLength(1)

      const mockOrderRes = { id: 99, order_number: 'ORD-99', status: 'Confirmed' }
      api.post.mockResolvedValueOnce({ data: mockOrderRes })

      const result = await store.createOrder({ requested_delivery_date: '2026-08-25' })
      expect(result).toEqual(mockOrderRes)
      expect(store.cart).toHaveLength(0)
      expect(api.post).toHaveBeenCalledWith('/portal/orders', expect.objectContaining({
        items: [{ product_id: 1, quantity: 2 }],
        requested_delivery_date: '2026-08-25',
      }))
    })

    it('creates invoice checkout session and balance settlement session', async () => {
      const store = usePortalStore()
      const mockSession = { session_id: 'cs_test_123', checkout_url: 'https://checkout.stripe.com/pay/cs_test_123' }
      api.post.mockResolvedValueOnce({ data: mockSession })

      const res1 = await store.createInvoiceCheckoutSession(42)
      expect(res1).toEqual(mockSession)
      expect(api.post).toHaveBeenCalledWith('/portal/invoices/42/checkout-session', expect.any(Object))

      api.post.mockResolvedValueOnce({ data: mockSession })
      const res2 = await store.createBalanceCheckoutSession(800.00)
      expect(res2).toEqual(mockSession)
      expect(api.post).toHaveBeenCalledWith('/portal/settlement/checkout-session', expect.objectContaining({
        amount: 800.00,
      }))
    })

    it('fetches and verifies payment session status', async () => {
      const store = usePortalStore()
      const mockStatus = {
        session_id: 'cs_test_abc',
        status: 'complete',
        payment_status: 'paid',
        amount_total: 50000,
      }
      api.get.mockResolvedValueOnce({ data: mockStatus })

      const res = await store.fetchPaymentSessionStatus('cs_test_abc', true)
      expect(res).toEqual(mockStatus)
      expect(api.get).toHaveBeenCalledWith('/portal/settlement/session/cs_test_abc', {
        params: { verify: true },
      })
    })
  })
})

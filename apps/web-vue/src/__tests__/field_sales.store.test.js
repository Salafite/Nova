import 'fake-indexeddb/auto'
import { setActivePinia, createPinia } from 'pinia'
import { useFieldSalesStore } from '../stores/fieldSales.js'
import { offlineDb } from '../services/offlineDb.js'
import { catalogSearch } from '../services/catalogSearch.js'
import { syncManager, SYNC_EVENTS } from '../services/syncManager.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

// Mock api client
vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

// Mock auth store
vi.mock('../stores/auth.js', () => ({
  useAuthStore: () => ({
    user: { id: 10, username: 'sales_rep_1', role: 'Sales Rep' },
    isLoggedIn: true
  })
}))

describe('Field Sales Pinia Store', () => {
  let mockProducts = []
  let mockCustomers = []
  let mockPrices = []

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Setup test data
    mockProducts = [
      {
        id: 1,
        sku: 'SKU-001',
        barcode: '1234567890123',
        name: 'Whole Milk 1 Gallon',
        category: 'Dairy',
        base_price: 3.99,
        available_qty: 50,
        warehouse_id: 1,
        tax_rate: 5,
        is_active: true
      },
      {
        id: 2,
        sku: 'SKU-002',
        barcode: '9876543210987',
        name: 'Cheddar Cheese Block 500g',
        category: 'Dairy',
        base_price: 6.5,
        available_qty: 20,
        warehouse_id: 1,
        tax_rate: 5,
        is_active: true
      },
      {
        id: 3,
        sku: 'SKU-003',
        barcode: '1122334455667',
        name: 'Organic Orange Juice 1L',
        category: 'Beverages',
        base_price: 4.25,
        available_qty: 0, // Out of stock
        warehouse_id: 1,
        tax_rate: 8,
        is_active: true
      }
    ]

    mockCustomers = [
      {
        id: 101,
        name: 'Corner Grocery Store',
        group_name: 'Retail',
        phone: '555-0101',
        email: 'corner@store.com',
        credit_limit: 5000,
        balance: 1200,
        available_credit: 3800,
        default_price_list_id: 201,
        tax_rate_pct: 5,
        address: '123 Main St',
        city: 'Metropolis',
        recent_orders: [
          {
            id: 901,
            order_number: 'SO-901',
            grand_total: 50.0,
            lines: [
              { product_id: 1, product_name: 'Whole Milk 1 Gallon', qty: 5, unit_price: 3.5 },
              { product_id: 2, product_name: 'Cheddar Cheese Block 500g', qty: 2, unit_price: 5.5 }
            ]
          }
        ]
      },
      {
        id: 102,
        name: 'Downtown Cafe & Bistro',
        group_name: 'Hospitality',
        phone: '555-0202',
        email: 'orders@downtowncafe.com',
        credit_limit: 2000,
        balance: 1950,
        available_credit: 50,
        default_price_list_id: null,
        tax_rate_pct: 0,
        recent_orders: []
      }
    ]

    mockPrices = [
      { id: 1, price_list_id: 201, product_id: 1, unit_price: 3.5 }, // Discounted contract price
      { id: 2, price_list_id: 201, product_id: 2, unit_price: 5.5 }
    ]

    // Initialize mock database and search indexer
    await offlineDb.deleteDatabase()
    await offlineDb.openDb()
    await offlineDb.saveProducts(mockProducts)
    await offlineDb.saveCustomers(mockCustomers)
    await offlineDb.saveCustomerPrices(mockPrices)
    await offlineDb.setMeta('catalog_last_synced', '2026-08-22T12:00:00Z')
    await offlineDb.setMeta('warehouses', [{ id: 1, name: 'Main Distribution Center' }])
    await offlineDb.setMeta('tax_rates', [{ id: 1, name: 'Standard 5%', rate: 5 }])
  })

  afterEach(async () => {
    syncManager.stop()
    await offlineDb.deleteDatabase()
  })

  describe('Initialization & Catalog Search', () => {
    it('initializes store, loads cached catalog and sets up search indexer', async () => {
      const store = useFieldSalesStore()
      await store.init()

      expect(store.products.length).toBe(3)
      expect(store.totalProductsCount).toBe(3)
      expect(store.categories.length).toBeGreaterThan(0)
      expect(store.catalogLastSynced).toBe('2026-08-22T12:00:00Z')
      expect(store.isDraftLoaded).toBe(true)
    })

    it('filters catalog items via fast search indexer', async () => {
      const store = useFieldSalesStore()
      await store.init()

      store.setSearchQuery('Milk')
      const results = store.searchResults
      expect(results.items.length).toBe(1)
      expect(results.items[0].sku).toBe('SKU-001')

      store.setSearchQuery('')
      store.setSelectedCategory('Beverages')
      const bevResults = store.searchResults
      expect(bevResults.items.length).toBe(1)
      expect(bevResults.items[0].sku).toBe('SKU-003')
    })

    it('performs exact barcode and SKU lookups', async () => {
      const store = useFieldSalesStore()
      await store.init()

      const foundBarcode = store.lookupBarcode('1234567890123')
      expect(foundBarcode).not.toBeNull()
      expect(foundBarcode.name).toBe('Whole Milk 1 Gallon')

      const foundSku = store.lookupSku('SKU-002')
      expect(foundSku).not.toBeNull()
      expect(foundSku.name).toBe('Cheddar Cheese Block 500g')
    })
  })

  describe('Customer Selection & Contracted Pricing', () => {
    it('selects customer and resolves contracted pricing', async () => {
      const store = useFieldSalesStore()
      await store.init()

      await store.selectCustomer(101)
      expect(store.selectedCustomer).not.toBeNull()
      expect(store.selectedCustomer.name).toBe('Corner Grocery Store')
      expect(store.draft.customer_id).toBe(101)
      expect(store.draft.shipping_address).toBe('123 Main St, Metropolis')

      // Resolve contracted price for product 1
      const price1 = await store.resolveProductPrice(mockProducts[0])
      expect(price1.isContracted).toBe(true)
      expect(price1.unitPrice).toBe(3.5) // Contracted price instead of 3.99 base price
    })

    it('uses standard base price when customer has no contract price list', async () => {
      const store = useFieldSalesStore()
      await store.init()

      await store.selectCustomer(102) // Downtown Cafe has default_price_list_id = null
      const price1 = await store.resolveProductPrice(mockProducts[0])
      expect(price1.isContracted).toBe(false)
      expect(price1.unitPrice).toBe(3.99)
    })

    it('filters customer list matching search query', async () => {
      const store = useFieldSalesStore()
      await store.init()

      store.customerSearchQuery = 'Bistro'
      expect(store.filteredCustomers.length).toBe(1)
      expect(store.filteredCustomers[0].name).toBe('Downtown Cafe & Bistro')

      store.customerSearchQuery = '555-0101'
      expect(store.filteredCustomers.length).toBe(1)
      expect(store.filteredCustomers[0].name).toBe('Corner Grocery Store')
    })

    it('calculates available credit and detects limit overflow', async () => {
      const store = useFieldSalesStore()
      await store.init()

      await store.selectCustomer(102) // Available credit is $50
      expect(store.customerAvailableCredit).toBe(50)

      await store.addItemToCart(mockProducts[0], 20) // 20 * 3.99 = 79.80 > 50
      expect(store.isCreditLimitExceeded).toBe(true)
    })
  })

  describe('Active Draft / Cart Management', () => {
    it('adds items, increments quantities, calculates tax & totals, and auto-saves draft', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      // Add product 1 (contracted price $3.50, 5% tax)
      await store.addItemToCart(mockProducts[0], 2)
      expect(store.cartItemCount).toBe(2)
      expect(store.cartLineCount).toBe(1)
      expect(store.cartSubtotal).toBe(7.0)
      expect(store.cartTaxTotal).toBe(0.35)
      expect(store.cartGrandTotal).toBe(7.35)

      // Add product 1 again (should increment quantity to 4)
      await store.addItemToCart(mockProducts[0], 2)
      expect(store.cartItemCount).toBe(4)
      expect(store.cartSubtotal).toBe(14.0)

      // Add product 2 (contracted price $5.50)
      await store.addItemToCart(mockProducts[1], 1)
      expect(store.cartLineCount).toBe(2)
      expect(store.cartSubtotal).toBe(19.5)

      // Verify draft persisted in IndexedDB
      const saved = await offlineDb.getDraftOrder('active_draft')
      expect(saved).not.toBeNull()
      expect(saved.lines.length).toBe(2)
      expect(saved.grand_total).toBe(store.cartGrandTotal)
    })

    it('updates item quantity and removes item if qty <= 0', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      await store.addItemToCart(mockProducts[0], 5)
      await store.updateCartItemQty(1, 3)
      expect(store.cartItemCount).toBe(3)

      await store.updateCartItemQty(1, 0)
      expect(store.cartItemCount).toBe(0)
      expect(store.cartLineCount).toBe(0)
    })

    it('applies line item discount percentage correctly', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      await store.addItemToCart(mockProducts[0], 10) // 10 * 3.50 = 35.00
      await store.updateCartItemDiscount(1, 10) // 10% discount -> subtotal = 31.50

      expect(store.cartSubtotal).toBe(31.5)
      expect(store.cartTaxTotal).toBe(1.58) // 31.50 * 5% = 1.575 -> 1.58
      expect(store.cartGrandTotal).toBe(33.08)
    })

    it('overrides line price and maintains override state', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      await store.addItemToCart(mockProducts[0], 2) // default $3.50
      await store.updateCartItemPrice(1, 3.0) // override to $3.00

      expect(store.cartSubtotal).toBe(6.0)
      const line = store.cartLines[0]
      expect(line.is_price_overridden).toBe(true)
      expect(line.unit_price).toBe(3.0)
    })

    it('clears cart and resets draft in IndexedDB', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      await store.addItemToCart(mockProducts[0], 5)
      expect(store.cartItemCount).toBe(5)

      await store.clearCart()
      expect(store.cartItemCount).toBe(0)
      expect(store.cartLines.length).toBe(0)

      const saved = await offlineDb.getDraftOrder('active_draft')
      expect(saved).toBeNull()
    })

    it('executes 1-click reorder from customer order history', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)

      const pastOrder = mockCustomers[0].recent_orders[0]
      const success = await store.applyReorder(pastOrder)

      expect(success).toBe(true)
      expect(store.cartLineCount).toBe(2)
      expect(store.cartItemCount).toBe(7) // 5 milk + 2 cheese
    })
  })

  describe('Order Submission & Sync Queue', () => {
    it('submits valid cart to offline sync queue, clears cart, and reloads queue', async () => {
      const store = useFieldSalesStore()
      await store.init()
      await store.selectCustomer(101)
      await store.addItemToCart(mockProducts[0], 3)

      expect(store.isCartValid).toBe(true)

      const submitResult = await store.submitOrder()
      expect(submitResult.success).toBe(true)
      expect(submitResult.order.client_order_uuid).toBeDefined()
      expect(submitResult.order.customer_id).toBe(101)

      // Cart should be reset
      expect(store.cartLines.length).toBe(0)

      // Queued orders should contain submitted order
      expect(store.queuedOrders.length).toBe(1)
      expect(store.pendingCount).toBe(1)
    })

    it('throws error when submitting invalid cart without customer', async () => {
      const store = useFieldSalesStore()
      await store.init()
      store.clearCustomer()

      await expect(store.submitOrder()).rejects.toThrow(/Cannot submit order/)
    })

    it('manages conflict modal and deletes queued orders', async () => {
      const store = useFieldSalesStore()
      await store.init()

      // Enqueue a conflict order manually
      const conflictOrder = {
        client_order_uuid: 'uuid-conflict-123',
        customer_id: 101,
        status: 'Conflict',
        conflicts: [
          {
            line_number: 1,
            product_id: 3,
            conflict_type: 'OUT_OF_STOCK',
            message: 'Item is out of stock'
          }
        ],
        lines: []
      }
      await offlineDb.enqueueOrder(conflictOrder)
      await store.loadQueuedOrders()

      expect(store.conflictCount).toBe(1)
      expect(store.conflictOrders.length).toBe(1)

      store.openConflictModal('uuid-conflict-123')
      expect(store.activeConflictOrder).not.toBeNull()
      expect(store.activeConflictOrder.client_order_uuid).toBe('uuid-conflict-123')

      store.closeConflictModal()
      expect(store.activeConflictOrder).toBeNull()

      await store.deleteQueuedOrder('uuid-conflict-123')
      expect(store.queuedOrders.length).toBe(0)
      expect(store.conflictCount).toBe(0)
    })
  })
})

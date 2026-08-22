import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { OfflineDb, STORES, DB_NAME, DB_VERSION } from '../services/offlineDb.js'

describe('OfflineDb Service', () => {
  let testDb

  beforeEach(async () => {
    // Unique DB name for each test
    const testDbName = `test_db_${Date.now()}_${Math.random().toString(36).substring(7)}`
    testDb = new OfflineDb(testDbName, 1)
  })

  afterEach(async () => {
    if (testDb) {
      await testDb.deleteDatabase()
    }
  })

  describe('Initialization and Schema', () => {
    it('creates all required stores with correct keys and indexes', async () => {
      const db = await testDb.openDb()
      expect(db.objectStoreNames.contains(STORES.PRODUCTS)).toBe(true)
      expect(db.objectStoreNames.contains(STORES.CUSTOMERS)).toBe(true)
      expect(db.objectStoreNames.contains(STORES.CUSTOMER_PRICES)).toBe(true)
      expect(db.objectStoreNames.contains(STORES.DRAFT_ORDERS)).toBe(true)
      expect(db.objectStoreNames.contains(STORES.SYNC_QUEUE)).toBe(true)
      expect(db.objectStoreNames.contains(STORES.SYNC_META)).toBe(true)
    })
  })

  describe('Products Store Operations', () => {
    const mockProducts = [
      {
        id: 101,
        sku: 'SKU-APPLES',
        barcode: '123456789012',
        name: 'Organic Honeycrisp Apples',
        category: 'Produce',
        category_id: 1,
        base_price: 2.99,
        available_qty: 150,
        warehouse_id: 1,
        is_active: true
      },
      {
        id: 102,
        sku: 'SKU-BANANAS',
        barcode: '987654321098',
        name: 'Cavendish Bananas',
        category: 'Produce',
        category_id: 1,
        base_price: 0.89,
        available_qty: 300,
        warehouse_id: 1,
        is_active: true
      }
    ]

    it('saves products and retrieves them by ID, SKU, and barcode', async () => {
      await testDb.saveProducts(mockProducts)

      const all = await testDb.getAllProducts()
      expect(all.length).toBe(2)

      const byId = await testDb.getProduct(101)
      expect(byId).not.toBeNull()
      expect(byId.name).toBe('Organic Honeycrisp Apples')

      const bySku = await testDb.getProductBySku('SKU-BANANAS')
      expect(bySku).not.toBeNull()
      expect(bySku.id).toBe(102)

      const byBarcode = await testDb.getProductByBarcode('123456789012')
      expect(byBarcode).not.toBeNull()
      expect(byBarcode.id).toBe(101)
    })
  })

  describe('Customers Store Operations', () => {
    const mockCustomers = [
      {
        id: 201,
        name: 'Whole Foods Downtown',
        group_name: 'Supermarkets',
        phone: '555-1234',
        email: 'buyer@wholefoods.com',
        credit_limit: 10000.0,
        balance: 2500.0,
        available_credit: 7500.0,
        is_active: true
      }
    ]

    it('saves and retrieves customer profiles', async () => {
      await testDb.saveCustomers(mockCustomers)

      const customer = await testDb.getCustomer(201)
      expect(customer).not.toBeNull()
      expect(customer.name).toBe('Whole Foods Downtown')
      expect(customer.available_credit).toBe(7500.0)

      const allCustomers = await testDb.getAllCustomers()
      expect(allCustomers.length).toBe(1)
    })
  })

  describe('Customer Prices Operations', () => {
    const mockPrices = [
      { id: 1, price_list_id: 5, product_id: 101, unit_price: 2.49, min_qty: 10 },
      { id: 2, price_list_id: 5, product_id: 102, unit_price: 0.75, min_qty: 1 }
    ]

    it('saves and queries price list rules', async () => {
      await testDb.saveCustomerPrices(mockPrices)

      const price = await testDb.getCustomerPrice(5, 101)
      expect(price).not.toBeNull()
      expect(price.unit_price).toBe(2.49)

      const allPrices = await testDb.getAllCustomerPrices()
      expect(allPrices.length).toBe(2)
    })
  })

  describe('Draft Orders Operations', () => {
    it('saves, retrieves, and deletes draft orders', async () => {
      const draft = {
        customer_id: 201,
        customer_name: 'Whole Foods Downtown',
        lines: [
          { product_id: 101, qty: 5, unit_price: 2.99, line_total: 14.95 }
        ],
        subtotal: 14.95,
        grand_total: 14.95
      }

      await testDb.saveDraftOrder(draft)

      const saved = await testDb.getDraftOrder('active_draft')
      expect(saved).not.toBeNull()
      expect(saved.customer_id).toBe(201)
      expect(saved.lines.length).toBe(1)
      expect(saved.updated_at).toBeDefined()

      await testDb.deleteDraftOrder('active_draft')
      const deleted = await testDb.getDraftOrder('active_draft')
      expect(deleted).toBeNull()
    })
  })

  describe('Sync Queue Operations', () => {
    it('enqueues orders, filters pending, updates status, and clears synced items', async () => {
      const order1 = {
        client_order_uuid: 'uuid-order-1',
        customer_id: 201,
        grand_total: 100.0,
        lines: [{ product_id: 101, qty: 10, unit_price: 10.0 }]
      }

      const order2 = {
        client_order_uuid: 'uuid-order-2',
        customer_id: 202,
        grand_total: 200.0,
        lines: [{ product_id: 102, qty: 20, unit_price: 10.0 }]
      }

      await testDb.enqueueOrder(order1)
      await testDb.enqueueOrder(order2)

      let pending = await testDb.getPendingOrders()
      expect(pending.length).toBe(2)

      // Update order 1 to Synced
      await testDb.updateQueueOrderStatus('uuid-order-1', 'Synced', {
        server_order_id: 501,
        order_number: 'SO-2026-00501'
      })

      const updated1 = await testDb.getQueuedOrder('uuid-order-1')
      expect(updated1.status).toBe('Synced')
      expect(updated1.server_order_id).toBe(501)

      pending = await testDb.getPendingOrders()
      expect(pending.length).toBe(1)
      expect(pending[0].client_order_uuid).toBe('uuid-order-2')

      // Clear synced orders
      const removedCount = await testDb.clearSyncedOrders()
      expect(removedCount).toBe(1)

      const remainingQueue = await testDb.getAllQueuedOrders()
      expect(remainingQueue.length).toBe(1)
      expect(remainingQueue[0].client_order_uuid).toBe('uuid-order-2')
    })
  })

  describe('Metadata and Full Catalog Bundle Saving', () => {
    it('saves metadata keys and full catalog bundles', async () => {
      await testDb.setMeta('device_id', 'ipad-pro-rep-42')
      const deviceId = await testDb.getMeta('device_id')
      expect(deviceId).toBe('ipad-pro-rep-42')

      const bundle = {
        sync_timestamp: '2026-08-22T20:00:00Z',
        delta_timestamp: '2026-08-22T19:00:00Z',
        products: [
          { id: 301, name: 'Fresh Milk 1L', sku: 'MILK-1L', base_price: 1.5, available_qty: 80 }
        ],
        customers: [
          { id: 401, name: 'Green Grocery', available_credit: 3000 }
        ],
        price_rules: [
          { id: 1, price_list_id: 1, product_id: 301, unit_price: 1.25 }
        ],
        warehouses: [{ id: 1, name: 'Main Distribution Center' }],
        tax_rates: [{ id: 1, rate: 0.0825, name: 'Standard Sales Tax' }],
        payment_terms: [{ id: 1, name: 'Net 30', days: 30 }]
      }

      await testDb.saveCatalogBundle(bundle)

      const lastSync = await testDb.getMeta('catalog_last_synced')
      expect(lastSync).toBe('2026-08-22T20:00:00Z')

      const product = await testDb.getProduct(301)
      expect(product.name).toBe('Fresh Milk 1L')

      const customer = await testDb.getCustomer(401)
      expect(customer.name).toBe('Green Grocery')

      const allMeta = await testDb.getAllMeta()
      expect(allMeta.total_products).toBe(1)
      expect(allMeta.total_customers).toBe(1)
      expect(allMeta.warehouses.length).toBe(1)
    })
  })
})

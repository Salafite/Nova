/**
 * Nova ERP - Field Sales Mobile Offline Storage Layer
 * High-performance Promise-based IndexedDB storage manager.
 */

export const DB_NAME = 'NovaFieldSalesDB'
export const DB_VERSION = 1

export const STORES = {
  PRODUCTS: 'products',
  CUSTOMERS: 'customers',
  CUSTOMER_PRICES: 'customer_prices',
  DRAFT_ORDERS: 'draft_orders',
  SYNC_QUEUE: 'sync_queue',
  SYNC_META: 'sync_meta'
}

export class OfflineDb {
  constructor(dbName = DB_NAME, version = DB_VERSION) {
    this.dbName = dbName
    this.version = version
    this._db = null
    this._initPromise = null
  }

  /**
   * Get safe IndexedDB factory in any environment (browser, worker, node mock)
   */
  _getIndexedDB() {
    if (typeof window !== 'undefined' && window.indexedDB) {
      return window.indexedDB
    }
    if (typeof globalThis !== 'undefined' && globalThis.indexedDB) {
      return globalThis.indexedDB
    }
    return null
  }

  /**
   * Open or retrieve active IndexedDB connection
   */
  async openDb() {
    if (this._db) {
      return this._db
    }

    if (this._initPromise) {
      return this._initPromise
    }

    this._initPromise = new Promise((resolve, reject) => {
      const idb = this._getIndexedDB()
      if (!idb) {
        reject(new Error('IndexedDB is not supported or available in this environment'))
        return
      }

      const request = idb.open(this.dbName, this.version)

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        // 1. Products Store
        if (!db.objectStoreNames.contains(STORES.PRODUCTS)) {
          const productStore = db.createObjectStore(STORES.PRODUCTS, { keyPath: 'id' })
          productStore.createIndex('sku', 'sku', { unique: false })
          productStore.createIndex('barcode', 'barcode', { unique: false })
          productStore.createIndex('name', 'name', { unique: false })
          productStore.createIndex('category', 'category', { unique: false })
          productStore.createIndex('category_id', 'category_id', { unique: false })
          productStore.createIndex('warehouse_id', 'warehouse_id', { unique: false })
          productStore.createIndex('is_active', 'is_active', { unique: false })
        }

        // 2. Customers Store
        if (!db.objectStoreNames.contains(STORES.CUSTOMERS)) {
          const customerStore = db.createObjectStore(STORES.CUSTOMERS, { keyPath: 'id' })
          customerStore.createIndex('name', 'name', { unique: false })
          customerStore.createIndex('group_name', 'group_name', { unique: false })
          customerStore.createIndex('phone', 'phone', { unique: false })
          customerStore.createIndex('email', 'email', { unique: false })
          customerStore.createIndex('is_active', 'is_active', { unique: false })
        }

        // 3. Customer Prices Store
        if (!db.objectStoreNames.contains(STORES.CUSTOMER_PRICES)) {
          const priceStore = db.createObjectStore(STORES.CUSTOMER_PRICES, {
            keyPath: 'id',
            autoIncrement: true
          })
          priceStore.createIndex('price_list_id', 'price_list_id', { unique: false })
          priceStore.createIndex('product_id', 'product_id', { unique: false })
          try {
            priceStore.createIndex('price_product', ['price_list_id', 'product_id'], { unique: false })
          } catch (e) {
            // Compound index fallback for older engines
          }
        }

        // 4. Draft Orders Store
        if (!db.objectStoreNames.contains(STORES.DRAFT_ORDERS)) {
          const draftStore = db.createObjectStore(STORES.DRAFT_ORDERS, { keyPath: 'id' })
          draftStore.createIndex('customer_id', 'customer_id', { unique: false })
          draftStore.createIndex('updated_at', 'updated_at', { unique: false })
        }

        // 5. Sync Queue Store
        if (!db.objectStoreNames.contains(STORES.SYNC_QUEUE)) {
          const queueStore = db.createObjectStore(STORES.SYNC_QUEUE, { keyPath: 'client_order_uuid' })
          queueStore.createIndex('status', 'status', { unique: false })
          queueStore.createIndex('queued_at', 'queued_at', { unique: false })
          queueStore.createIndex('customer_id', 'customer_id', { unique: false })
          queueStore.createIndex('retry_count', 'retry_count', { unique: false })
        }

        // 6. Sync Metadata Store
        if (!db.objectStoreNames.contains(STORES.SYNC_META)) {
          db.createObjectStore(STORES.SYNC_META, { keyPath: 'key' })
        }
      }

      request.onsuccess = (event) => {
        this._db = event.target.result
        this._db.onversionchange = () => {
          this._db.close()
          this._db = null
        }
        resolve(this._db)
      }

      request.onerror = (event) => {
        this._initPromise = null
        reject(event.target.error || new Error('Failed to open IndexedDB'))
      }

      request.onblocked = () => {
        console.warn(`IndexedDB database ${this.dbName} open request is blocked`)
      }
    })

    return this._initPromise
  }

  /**
   * Close the active database connection
   */
  closeDb() {
    if (this._db) {
      this._db.close()
      this._db = null
    }
    this._initPromise = null
  }

  /**
   * Delete entire database
   */
  async deleteDatabase() {
    this.closeDb()
    const idb = this._getIndexedDB()
    if (!idb) return

    return new Promise((resolve, reject) => {
      const request = idb.deleteDatabase(this.dbName)
      request.onsuccess = () => resolve(true)
      request.onerror = (e) => reject(e.target.error)
      request.onblocked = () => resolve(false)
    })
  }

  /**
   * Run a transaction with automatic promise resolution and error handling
   */
  async _runTransaction(storeNames, mode, operation) {
    const db = await this.openDb()
    const stores = Array.isArray(storeNames) ? storeNames : [storeNames]

    return new Promise((resolve, reject) => {
      const tx = db.transaction(stores, mode)
      let opResult = undefined

      tx.oncomplete = () => resolve(opResult)
      tx.onerror = (e) => reject(tx.error || e.target.error)
      tx.onabort = (e) => reject(tx.error || new Error('Transaction was aborted'))

      try {
        if (Array.isArray(storeNames)) {
          const storeMap = {}
          for (const name of storeNames) {
            storeMap[name] = tx.objectStore(name)
          }
          opResult = operation(storeMap, tx)
        } else {
          const store = tx.objectStore(storeNames)
          opResult = operation(store, tx)
        }
      } catch (err) {
        reject(err)
      }
    })
  }

  // -------------------------------------------------------------------------
  // Generic CRUD Helpers
  // -------------------------------------------------------------------------

  async get(storeName, key) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const request = store.get(key)

      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async getAll(storeName, query = null, count = undefined) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const request = store.getAll(query, count)

      request.onsuccess = () => resolve(request.result || [])
      request.onerror = () => reject(request.error)
    })
  }

  async getByIndex(storeName, indexName, query) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const index = store.index(indexName)
      const request = index.get(query)

      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async getAllByIndex(storeName, indexName, query = null, count = undefined) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const index = store.index(indexName)
      const request = index.getAll(query, count)

      request.onsuccess = () => resolve(request.result || [])
      request.onerror = () => reject(request.error)
    })
  }

  async put(storeName, value, key = undefined) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const request = key !== undefined ? store.put(value, key) : store.put(value)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async putBatch(storeName, items) {
    if (!items || !items.length) return []
    const db = await this.openDb()

    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const results = []

      tx.oncomplete = () => resolve(results)
      tx.onerror = () => reject(tx.error)
      tx.onabort = () => reject(tx.error || new Error('Batch transaction aborted'))

      for (const item of items) {
        const req = store.put(item)
        req.onsuccess = () => results.push(req.result)
      }
    })
  }

  async add(storeName, value, key = undefined) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const request = key !== undefined ? store.add(value, key) : store.add(value)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async deleteItem(storeName, key) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const request = store.delete(key)

      request.onsuccess = () => resolve(true)
      request.onerror = () => reject(request.error)
    })
  }

  async clearStore(storeName) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readwrite')
      const store = tx.objectStore(storeName)
      const request = store.clear()

      request.onsuccess = () => resolve(true)
      request.onerror = () => reject(request.error)
    })
  }

  async count(storeName, query = null) {
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, 'readonly')
      const store = tx.objectStore(storeName)
      const request = store.count(query)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  // -------------------------------------------------------------------------
  // Products Domain Methods
  // -------------------------------------------------------------------------

  async saveProducts(products) {
    return this.putBatch(STORES.PRODUCTS, products)
  }

  async getProduct(id) {
    return this.get(STORES.PRODUCTS, id)
  }

  async getProductBySku(sku) {
    if (!sku) return null
    return this.getByIndex(STORES.PRODUCTS, 'sku', sku)
  }

  async getProductByBarcode(barcode) {
    if (!barcode) return null
    return this.getByIndex(STORES.PRODUCTS, 'barcode', barcode)
  }

  async getAllProducts() {
    return this.getAll(STORES.PRODUCTS)
  }

  // -------------------------------------------------------------------------
  // Customers Domain Methods
  // -------------------------------------------------------------------------

  async saveCustomers(customers) {
    return this.putBatch(STORES.CUSTOMERS, customers)
  }

  async getCustomer(id) {
    return this.get(STORES.CUSTOMERS, id)
  }

  async getAllCustomers() {
    return this.getAll(STORES.CUSTOMERS)
  }

  // -------------------------------------------------------------------------
  // Customer Prices Domain Methods
  // -------------------------------------------------------------------------

  async saveCustomerPrices(prices) {
    if (!prices || !prices.length) return []
    const db = await this.openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.CUSTOMER_PRICES, 'readwrite')
      const store = tx.objectStore(STORES.CUSTOMER_PRICES)
      const results = []

      tx.oncomplete = () => resolve(results)
      tx.onerror = () => reject(tx.error)

      for (const price of prices) {
        const req = store.put(price)
        req.onsuccess = () => results.push(req.result)
      }
    })
  }

  async getCustomerPrice(priceListId, productId) {
    if (!priceListId || !productId) return null
    const all = await this.getAllCustomerPrices()
    return all.find(p => p.price_list_id === priceListId && p.product_id === productId) || null
  }

  async getAllCustomerPrices() {
    return this.getAll(STORES.CUSTOMER_PRICES)
  }

  // -------------------------------------------------------------------------
  // Draft Orders Domain Methods
  // -------------------------------------------------------------------------

  async saveDraftOrder(draft) {
    const draftData = {
      id: 'active_draft',
      ...draft,
      updated_at: new Date().toISOString()
    }
    await this.put(STORES.DRAFT_ORDERS, draftData)
    return draftData
  }

  async getDraftOrder(id = 'active_draft') {
    return this.get(STORES.DRAFT_ORDERS, id)
  }

  async deleteDraftOrder(id = 'active_draft') {
    return this.deleteItem(STORES.DRAFT_ORDERS, id)
  }

  async getAllDraftOrders() {
    return this.getAll(STORES.DRAFT_ORDERS)
  }

  // -------------------------------------------------------------------------
  // Sync Queue Domain Methods
  // -------------------------------------------------------------------------

  /**
   * Enqueue an order for synchronization
   */
  async enqueueOrder(order) {
    const uuid = order.client_order_uuid || this._generateUuid()
    const record = {
      ...order,
      client_order_uuid: uuid,
      status: order.status || 'Pending',
      queued_at: order.queued_at || new Date().toISOString(),
      retry_count: order.retry_count || 0,
      last_error: order.last_error || null,
      conflicts: order.conflicts || []
    }
    await this.put(STORES.SYNC_QUEUE, record)
    return record
  }

  async getQueuedOrder(clientOrderUuid) {
    return this.get(STORES.SYNC_QUEUE, clientOrderUuid)
  }

  async getAllQueuedOrders() {
    const orders = await this.getAll(STORES.SYNC_QUEUE)
    return orders.sort((a, b) => new Date(a.queued_at) - new Date(b.queued_at))
  }

  async getPendingOrders() {
    const orders = await this.getAll(STORES.SYNC_QUEUE)
    return orders
      .filter(o => o.status === 'Pending' || o.status === 'Conflict' || o.status === 'Failed')
      .sort((a, b) => new Date(a.queued_at) - new Date(b.queued_at))
  }

  async updateQueueOrderStatus(clientOrderUuid, status, extra = {}) {
    const existing = await this.getQueuedOrder(clientOrderUuid)
    if (!existing) {
      throw new Error(`Queued order with UUID ${clientOrderUuid} not found`)
    }
    const updated = {
      ...existing,
      ...extra,
      status,
      updated_at: new Date().toISOString()
    }
    await this.put(STORES.SYNC_QUEUE, updated)
    return updated
  }

  async removeFromQueue(clientOrderUuid) {
    return this.deleteItem(STORES.SYNC_QUEUE, clientOrderUuid)
  }

  async clearSyncedOrders() {
    const all = await this.getAll(STORES.SYNC_QUEUE)
    const synced = all.filter(o => o.status === 'Synced' || o.status === 'AlreadySynced')
    for (const order of synced) {
      await this.deleteItem(STORES.SYNC_QUEUE, order.client_order_uuid)
    }
    return synced.length
  }

  async clearQueue() {
    return this.clearStore(STORES.SYNC_QUEUE)
  }

  // -------------------------------------------------------------------------
  // Sync Metadata & Catalog Bundle Operations
  // -------------------------------------------------------------------------

  async setMeta(key, value) {
    const metaRecord = {
      key,
      value,
      updated_at: new Date().toISOString()
    }
    await this.put(STORES.SYNC_META, metaRecord)
    return metaRecord
  }

  async getMeta(key, defaultValue = null) {
    const record = await this.get(STORES.SYNC_META, key)
    return record ? record.value : defaultValue
  }

  async getAllMeta() {
    const records = await this.getAll(STORES.SYNC_META)
    const result = {}
    for (const r of records) {
      result[r.key] = r.value
    }
    return result
  }

  /**
   * Save complete mobile catalog bundle into IndexedDB
   */
  async saveCatalogBundle(bundle) {
    if (!bundle) return false

    if (bundle.products && bundle.products.length > 0) {
      await this.saveProducts(bundle.products)
    }

    if (bundle.customers && bundle.customers.length > 0) {
      await this.saveCustomers(bundle.customers)
    }

    if (bundle.price_rules && bundle.price_rules.length > 0) {
      await this.saveCustomerPrices(bundle.price_rules)
    }

    // Save metadata
    if (bundle.sync_timestamp) {
      await this.setMeta('catalog_last_synced', bundle.sync_timestamp)
    }
    if (bundle.delta_timestamp) {
      await this.setMeta('delta_timestamp', bundle.delta_timestamp)
    }
    if (bundle.warehouses) {
      await this.setMeta('warehouses', bundle.warehouses)
    }
    if (bundle.tax_rates) {
      await this.setMeta('tax_rates', bundle.tax_rates)
    }
    if (bundle.payment_terms) {
      await this.setMeta('payment_terms', bundle.payment_terms)
    }
    await this.setMeta('total_products', bundle.total_products || (bundle.products ? bundle.products.length : 0))
    await this.setMeta('total_customers', bundle.total_customers || (bundle.customers ? bundle.customers.length : 0))

    return true
  }

  /**
   * Helper UUID generator
   */
  _generateUuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID()
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
  }
}

// Singleton instance for general application use
export const offlineDb = new OfflineDb()
export default offlineDb

/**
 * Nova ERP - Field Sales Mobile Pinia Store
 * Manages mobile connection status, IndexedDB cached catalog, fast SKU search,
 * customer profiles & contracted pricing, offline draft order editing,
 * 1-click reordering, background sync queue, and stock conflict resolution.
 */

import { defineStore } from 'pinia'
import { api } from '../api/client.js'
import { offlineDb } from '../services/offlineDb.js'
import { catalogSearch } from '../services/catalogSearch.js'
import { syncManager, SYNC_EVENTS } from '../services/syncManager.js'
import { useAuthStore } from './auth.js'

function generateUuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'fs-xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function createBlankDraft(warehouseId = 1) {
  return {
    id: 'active_draft',
    client_order_uuid: generateUuid(),
    customer_id: null,
    warehouse_id: warehouseId,
    order_date: new Date().toISOString().split('T')[0],
    lines: [],
    customer_notes: '',
    shipping_address: '',
    payment_term_id: null,
    requested_delivery_date: null,
    sales_rep_id: null,
    signature: null,
    subtotal: 0,
    tax: 0,
    grand_total: 0,
    updated_at: new Date().toISOString()
  }
}

function calculateLineTotals(line) {
  const qty = Number(line.qty) || 0
  const unitPrice = Number(line.unit_price) || 0
  const discountPct = Math.min(100, Math.max(0, Number(line.discount_pct || line.discount_rate || 0)))
  const taxRate = Math.max(0, Number(line.tax_rate || 0))

  const subtotal = Math.round(qty * unitPrice * (1 - discountPct / 100) * 100) / 100
  const taxAmount = Math.round(subtotal * (taxRate / 100) * 100) / 100
  const total = Math.round((subtotal + taxAmount) * 100) / 100

  return {
    subtotal,
    tax_amount: taxAmount,
    total,
    line_total: total
  }
}

export const useFieldSalesStore = defineStore('fieldSales', {
  state: () => ({
    // Connection & Sync Lifecycle
    isOnline: syncManager.isOnline,
    isSyncing: false,
    lastSyncTime: null,
    lastSyncError: null,
    pendingCount: 0,
    conflictCount: 0,
    syncedCount: 0,
    retryCount: 0,

    // Catalog & Metadata
    products: [],
    categories: [],
    warehouses: [],
    taxRates: [],
    paymentTerms: [],
    selectedWarehouseId: 1,
    catalogLoading: false,
    catalogLastSynced: null,
    totalProductsCount: 0,

    // Catalog Search & Filters
    searchQuery: '',
    selectedCategory: 'all',
    inStockOnlyFilter: false,
    minStockFilter: null,
    sortBy: 'relevance',
    searchExecutionTimeMs: 0,

    // Customers
    customers: [],
    customersLoading: false,
    customerSearchQuery: '',
    selectedCustomer: null,
    customerHistoryLoading: false,
    customerRecentOrders: [],

    // Active Order Draft (Local IndexedDB Cart)
    draft: createBlankDraft(),
    isDraftLoaded: false,

    // Sync Queue & Conflict Resolution
    queuedOrders: [],
    activeConflictOrder: null,
    isSubmittingOrder: false,

    // Internal listeners cleanup
    _unsubscribers: []
  }),

  getters: {
    /**
     * Filtered list of customers matching search query
     */
    filteredCustomers: (state) => {
      const q = (state.customerSearchQuery || '').trim().toLowerCase()
      if (!q) return state.customers

      return state.customers.filter((c) => {
        const name = (c.name || '').toLowerCase()
        const group = (c.group_name || '').toLowerCase()
        const phone = (c.phone || '').toLowerCase()
        const email = (c.email || '').toLowerCase()
        const city = (c.city || '').toLowerCase()
        return name.includes(q) || group.includes(q) || phone.includes(q) || email.includes(q) || city.includes(q)
      })
    },

    /**
     * Fast in-memory catalog search results with metadata
     */
    searchResults: (state) => {
      const result = catalogSearch.searchWithMeta(state.searchQuery, {
        category: state.selectedCategory === 'all' ? '' : state.selectedCategory,
        warehouse_id: state.selectedWarehouseId,
        inStockOnly: state.inStockOnlyFilter,
        minStock: state.minStockFilter,
        sortBy: state.sortBy,
        limit: 100
      })
      return result
    },

    /**
     * Direct list of search result products
     */
    filteredProducts() {
      return this.searchResults.items || []
    },

    // Cart / Draft Computed Getters
    cartLines: (state) => state.draft.lines || [],

    cartItemCount: (state) => {
      return (state.draft.lines || []).reduce((acc, line) => acc + (Number(line.qty) || 0), 0)
    },

    cartLineCount: (state) => {
      return (state.draft.lines || []).length
    },

    cartSubtotal: (state) => {
      return (state.draft.lines || []).reduce((acc, line) => acc + (Number(line.subtotal) || 0), 0)
    },

    cartTaxTotal: (state) => {
      return (state.draft.lines || []).reduce((acc, line) => acc + (Number(line.tax_amount) || 0), 0)
    },

    cartGrandTotal: (state) => {
      const sub = (state.draft.lines || []).reduce((acc, line) => acc + (Number(line.subtotal) || 0), 0)
      const tax = (state.draft.lines || []).reduce((acc, line) => acc + (Number(line.tax_amount) || 0), 0)
      return Math.round((sub + tax) * 100) / 100
    },

    isCartValid: (state) => {
      const hasCustomer = !!state.selectedCustomer || !!state.draft?.customer_id
      const hasLines = (state.draft?.lines || []).length > 0
      const allLinesValid = hasLines && state.draft.lines.every((l) => Number(l.qty) > 0 && Number(l.unit_price) >= 0)
      return hasCustomer && allLinesValid
    },

    customerAvailableCredit: (state) => {
      if (!state.selectedCustomer) return 0
      if (typeof state.selectedCustomer.available_credit === 'number') {
        return state.selectedCustomer.available_credit
      }
      const limit = Number(state.selectedCustomer.credit_limit || 0)
      const balance = Number(state.selectedCustomer.balance || 0)
      return Math.max(0, limit - balance)
    },

    isCreditLimitExceeded() {
      if (!this.selectedCustomer || !this.selectedCustomer.credit_limit) return false
      const avail = this.customerAvailableCredit
      return avail > 0 && this.cartGrandTotal > avail
    },

    // Sync Queue Categorization
    pendingOrders: (state) => {
      return state.queuedOrders.filter((o) => o.status === 'Pending' || o.status === 'Failed')
    },

    conflictOrders: (state) => {
      return state.queuedOrders.filter((o) => o.status === 'Conflict')
    },

    syncedOrders: (state) => {
      return state.queuedOrders.filter((o) => o.status === 'Synced' || o.status === 'AlreadySynced')
    }
  },

  actions: {
    // -----------------------------------------------------------------------
    // Store Initialization & Lifecycle
    // -----------------------------------------------------------------------

    async init() {
      try {
        // Open offline database
        await offlineDb.openDb()

        // Bind sync manager event listeners
        this._bindSyncEvents()

        // Start background network & queue monitoring
        await syncManager.start()

        // Load cached catalog metadata and products into in-memory search indexer
        await this.loadCachedCatalog()

        // Load cached customers
        await this.loadCachedCustomers()

        // Restore draft order from IndexedDB
        await this.loadDraft()

        // Load queued orders and refresh metrics
        await this.loadQueuedOrders()

        // If online and catalog empty, trigger automatic initial sync
        if (this.isOnline && this.products.length === 0) {
          this.fetchCatalog().catch(() => {})
        }
      } catch (err) {
        console.error('Error initializing Field Sales store:', err)
      }
    },

    _bindSyncEvents() {
      this._cleanupSyncEvents()

      const unOnline = syncManager.on(SYNC_EVENTS.ONLINE, () => {
        this.isOnline = true
      })
      const unOffline = syncManager.on(SYNC_EVENTS.OFFLINE, () => {
        this.isOnline = false
      })
      const unStatus = syncManager.on(SYNC_EVENTS.STATUS_CHANGE, (status) => {
        this.isOnline = status.isOnline
        this.isSyncing = status.isSyncing
        this.lastSyncTime = status.lastSyncTime
        this.lastSyncError = status.lastSyncError
        this.pendingCount = status.pendingCount
        this.conflictCount = status.conflictCount
        this.syncedCount = status.syncedCount
        this.retryCount = status.retryCount
      })
      const unStart = syncManager.on(SYNC_EVENTS.SYNC_START, () => {
        this.isSyncing = true
      })
      const unComplete = syncManager.on(SYNC_EVENTS.SYNC_COMPLETE, async () => {
        this.isSyncing = false
        await this.loadQueuedOrders()
      })
      const unError = syncManager.on(SYNC_EVENTS.SYNC_ERROR, (data) => {
        this.isSyncing = false
        this.lastSyncError = data.error?.message || 'Sync failed'
      })
      const unConflict = syncManager.on(SYNC_EVENTS.CONFLICT, async (data) => {
        await this.loadQueuedOrders()
        if (data && data.order) {
          this.activeConflictOrder = data.order
        }
      })
      const unCatUpdated = syncManager.on(SYNC_EVENTS.CATALOG_UPDATED, async () => {
        await this.loadCachedCatalog()
        await this.loadCachedCustomers()
      })

      this._unsubscribers = [unOnline, unOffline, unStatus, unStart, unComplete, unError, unConflict, unCatUpdated]
    },

    _cleanupSyncEvents() {
      for (const unsub of this._unsubscribers) {
        try {
          unsub()
        } catch {}
      }
      this._unsubscribers = []
    },

    cleanup() {
      this._cleanupSyncEvents()
      syncManager.stop()
    },

    // -----------------------------------------------------------------------
    // Catalog & Search Operations
    // -----------------------------------------------------------------------

    async loadCachedCatalog() {
      this.catalogLoading = true
      try {
        const cachedProducts = await offlineDb.getAllProducts()
        this.products = cachedProducts || []
        this.totalProductsCount = this.products.length

        // Index in memory
        catalogSearch.buildIndex(this.products)
        this.categories = catalogSearch.getCategories()

        // Load metadata
        const meta = await offlineDb.getAllMeta()
        this.catalogLastSynced = meta.catalog_last_synced || null
        this.warehouses = meta.warehouses || []
        this.taxRates = meta.tax_rates || []
        this.paymentTerms = meta.payment_terms || []

        if (this.warehouses.length > 0 && !this.selectedWarehouseId) {
          this.selectedWarehouseId = this.warehouses[0].id
        }
      } catch (err) {
        console.error('Failed to load cached catalog:', err)
      } finally {
        this.catalogLoading = false
      }
    },

    async fetchCatalog(options = {}) {
      this.catalogLoading = true
      try {
        const result = await syncManager.syncCatalog({
          ...options,
          warehouse_id: this.selectedWarehouseId
        })
        if (result.success) {
          await this.loadCachedCatalog()
          await this.loadCachedCustomers()
        }
        return result
      } catch (err) {
        console.error('Failed to fetch mobile catalog:', err)
        return { success: false, error: err.message }
      } finally {
        this.catalogLoading = false
      }
    },

    setSearchQuery(query) {
      this.searchQuery = query
    },

    setSelectedCategory(category) {
      this.selectedCategory = category
    },

    setWarehouse(warehouseId) {
      this.selectedWarehouseId = warehouseId
      this.draft.warehouse_id = warehouseId
      this.saveDraft()
    },

    setSortBy(sortBy) {
      this.sortBy = sortBy
    },

    toggleInStockOnly() {
      this.inStockOnlyFilter = !this.inStockOnlyFilter
    },

    lookupBarcode(barcode) {
      return catalogSearch.lookupBarcode(barcode)
    },

    lookupSku(sku) {
      return catalogSearch.lookupSku(sku)
    },

    // -----------------------------------------------------------------------
    // Customer Selection & Contracted Pricing
    // -----------------------------------------------------------------------

    async loadCachedCustomers() {
      this.customersLoading = true
      try {
        const cached = await offlineDb.getAllCustomers()
        this.customers = cached || []
        if (this.selectedCustomer?.id) {
          const refreshed = this.customers.find((c) => c.id === this.selectedCustomer.id) || (await offlineDb.getCustomer(this.selectedCustomer.id))
          if (refreshed) {
            this.selectedCustomer = refreshed
            this.customerRecentOrders = refreshed.recent_orders || []
          }
        }
      } catch (err) {
        console.error('Failed to load cached customers:', err)
      } finally {
        this.customersLoading = false
      }
    },

    async fetchCustomers() {
      this.customersLoading = true
      try {
        if (this.isOnline) {
          const res = await api.get('/sales/mobile/customers')
          const data = res.data?.customers || res.data || []
          if (Array.isArray(data) && data.length > 0) {
            await offlineDb.saveCustomers(data)
            this.customers = data
          }
        } else {
          await this.loadCachedCustomers()
        }
      } catch (err) {
        console.warn('Failed to fetch customers online, using local cache:', err)
        await this.loadCachedCustomers()
      } finally {
        this.customersLoading = false
      }
    },

    async selectCustomer(customerOrId) {
      let customer = null
      if (typeof customerOrId === 'object' && customerOrId !== null) {
        customer = customerOrId
      } else if (typeof customerOrId === 'number' || typeof customerOrId === 'string') {
        const id = Number(customerOrId)
        customer = this.customers.find((c) => c.id === id) || (await offlineDb.getCustomer(id))
      }

      this.selectedCustomer = customer
      this.draft.customer_id = customer ? customer.id : null

      if (customer) {
        this.draft.payment_term_id = customer.payment_term_id || null
        this.draft.shipping_address = customer.address ? `${customer.address}${customer.city ? ', ' + customer.city : ''}` : ''
        this.customerRecentOrders = customer.recent_orders || []

        // Recalculate line prices based on customer contracted pricing
        await this.recalculateCartPrices()

        // Fetch fresh history if online
        if (this.isOnline) {
          this.fetchCustomerHistory(customer.id).catch(() => {})
        }
      } else {
        this.customerRecentOrders = []
      }

      await this.saveDraft()
    },

    clearCustomer() {
      this.selectedCustomer = null
      this.draft.customer_id = null
      this.draft.payment_term_id = null
      this.draft.shipping_address = ''
      this.customerRecentOrders = []
      this.recalculateCartPrices()
      this.saveDraft()
    },

    async fetchCustomerHistory(customerId) {
      if (!customerId) return []
      if (!this.isOnline) {
        const cust = (this.selectedCustomer && this.selectedCustomer.id === customerId)
          ? this.selectedCustomer
          : (await offlineDb.getCustomer(customerId))
        this.customerRecentOrders = cust?.recent_orders || []
        return this.customerRecentOrders
      }
      this.customerHistoryLoading = true
      try {
        const res = await api.get(`/sales/mobile/customers/${customerId}/history`)
        const orders = res.data?.recent_orders || res.data || []
        this.customerRecentOrders = orders

        // Update customer in state and IndexedDB
        if (this.selectedCustomer && this.selectedCustomer.id === customerId) {
          this.selectedCustomer.recent_orders = orders
          await offlineDb.put('customers', JSON.parse(JSON.stringify(this.selectedCustomer)))
        }
        return orders
      } catch (err) {
        console.warn(`Failed to fetch history for customer ${customerId}:`, err)
        const cust = this.selectedCustomer || (await offlineDb.getCustomer(customerId))
        this.customerRecentOrders = cust?.recent_orders || []
        return this.customerRecentOrders
      } finally {
        this.customerHistoryLoading = false
      }
    },

    /**
     * Resolve unit price for a product based on customer price list contracts
     */
    async resolveProductPrice(product, customer = this.selectedCustomer) {
      if (!product) return { unitPrice: 0, isContracted: false, basePrice: 0 }

      const basePrice = Number(product.base_price !== undefined ? product.base_price : product.price || 0)
      if (!customer || !customer.default_price_list_id) {
        return { unitPrice: basePrice, isContracted: false, basePrice }
      }

      try {
        const rule = await offlineDb.getCustomerPrice(customer.default_price_list_id, product.id)
        if (rule && rule.unit_price !== undefined && rule.unit_price !== null) {
          return {
            unitPrice: Number(rule.unit_price),
            isContracted: true,
            basePrice
          }
        }
      } catch (e) {
        console.warn('Error resolving customer price rule:', e)
      }

      return { unitPrice: basePrice, isContracted: false, basePrice }
    },

    /**
     * Recalculate all lines in active cart with current customer pricing rules
     */
    async recalculateCartPrices() {
      if (!this.draft.lines || this.draft.lines.length === 0) return

      const updatedLines = []
      for (const line of this.draft.lines) {
        const product = catalogSearch.getProductById(line.product_id) || (await offlineDb.getProduct(line.product_id))
        const { unitPrice } = await this.resolveProductPrice(product, this.selectedCustomer)
        const taxRate = this.selectedCustomer?.tax_rate_pct !== undefined ? this.selectedCustomer.tax_rate_pct : product?.tax_rate || line.tax_rate || 0

        const updatedLine = {
          ...line,
          unit_price: line.is_price_overridden ? line.unit_price : unitPrice,
          tax_rate: taxRate
        }
        const totals = calculateLineTotals(updatedLine)
        updatedLines.push({ ...updatedLine, ...totals })
      }

      this.draft.lines = updatedLines
      await this.saveDraft()
    },

    // -----------------------------------------------------------------------
    // Active Cart & Draft Order Management
    // -----------------------------------------------------------------------

    async loadDraft() {
      try {
        const savedDraft = await offlineDb.getDraftOrder('active_draft')
        if (savedDraft) {
          this.draft = {
            ...createBlankDraft(this.selectedWarehouseId),
            ...savedDraft
          }
          if (this.draft.customer_id) {
            this.selectedCustomer = this.customers.find((c) => c.id === this.draft.customer_id) || (await offlineDb.getCustomer(this.draft.customer_id))
            if (this.selectedCustomer) {
              this.customerRecentOrders = this.selectedCustomer.recent_orders || []
            }
          }
        } else {
          this.draft = createBlankDraft(this.selectedWarehouseId)
        }
        this.isDraftLoaded = true
      } catch (err) {
        console.error('Failed to load draft order from IndexedDB:', err)
        this.draft = createBlankDraft(this.selectedWarehouseId)
        this.isDraftLoaded = true
      }
    },

    async saveDraft() {
      this._updateDraftTotals()
      try {
        const plainDraft = JSON.parse(JSON.stringify(this.draft))
        await offlineDb.saveDraftOrder(plainDraft)
      } catch (err) {
        console.error('Failed to save draft order to IndexedDB:', err)
      }
    },

    _updateDraftTotals() {
      let sub = 0
      let tax = 0

      for (const line of this.draft.lines) {
        sub += Number(line.subtotal) || 0
        tax += Number(line.tax_amount) || 0
      }

      this.draft.subtotal = Math.round(sub * 100) / 100
      this.draft.tax = Math.round(tax * 100) / 100
      this.draft.grand_total = Math.round((sub + tax) * 100) / 100
      this.draft.updated_at = new Date().toISOString()
    },

    /**
     * Add product item to cart / draft
     */
    async addItemToCart(product, qty = 1, options = {}) {
      if (!product || product.id === undefined) return null

      const existingIndex = this.draft.lines.findIndex((l) => l.product_id === product.id)
      const { unitPrice, isContracted, basePrice } = await this.resolveProductPrice(product, this.selectedCustomer)
      const taxRate = this.selectedCustomer?.tax_rate_pct !== undefined ? this.selectedCustomer.tax_rate_pct : product.tax_rate || 0
      const availableQty = product.available_qty !== undefined ? product.available_qty : product.stock_quantity || 0

      if (existingIndex >= 0) {
        // Increment quantity
        const existing = this.draft.lines[existingIndex]
        const newQty = (Number(existing.qty) || 0) + Number(qty)
        existing.qty = newQty
        const totals = calculateLineTotals(existing)
        Object.assign(existing, totals)
      } else {
        // Create new line
        const newLine = {
          line_number: this.draft.lines.length + 1,
          product_id: product.id,
          sku: product.sku || '',
          name: product.name || '',
          product_name: product.name || '',
          qty: Number(qty) || 1,
          unit_price: options.unit_price !== undefined ? options.unit_price : unitPrice,
          base_price: basePrice,
          is_contracted_price: isContracted,
          is_price_overridden: options.unit_price !== undefined,
          discount_pct: options.discount_pct || 0,
          discount_rate: options.discount_pct || 0,
          tax_rate: taxRate,
          uom_code: product.uom_code || 'UNIT',
          available_qty: availableQty,
          notes: options.notes || '',
          ...calculateLineTotals({
            qty: Number(qty) || 1,
            unit_price: options.unit_price !== undefined ? options.unit_price : unitPrice,
            discount_pct: options.discount_pct || 0,
            tax_rate: taxRate
          })
        }
        this.draft.lines.push(newLine)
      }

      await this.saveDraft()
      return this.draft
    },

    /**
     * Update quantity of a line item
     */
    async updateCartItemQty(productId, qty) {
      const numQty = Number(qty)
      if (numQty <= 0) {
        return this.removeCartItem(productId)
      }

      const line = this.draft.lines.find((l) => l.product_id === productId)
      if (line) {
        line.qty = numQty
        const totals = calculateLineTotals(line)
        Object.assign(line, totals)
        await this.saveDraft()
      }
      return this.draft
    },

    /**
     * Update discount % for a line item
     */
    async updateCartItemDiscount(productId, discountPct) {
      const line = this.draft.lines.find((l) => l.product_id === productId)
      if (line) {
        line.discount_pct = Math.min(100, Math.max(0, Number(discountPct) || 0))
        line.discount_rate = line.discount_pct
        const totals = calculateLineTotals(line)
        Object.assign(line, totals)
        await this.saveDraft()
      }
      return this.draft
    },

    /**
     * Manually override unit price for a line item
     */
    async updateCartItemPrice(productId, newUnitPrice) {
      const line = this.draft.lines.find((l) => l.product_id === productId)
      if (line) {
        line.unit_price = Math.max(0, Number(newUnitPrice) || 0)
        line.is_price_overridden = true
        const totals = calculateLineTotals(line)
        Object.assign(line, totals)
        await this.saveDraft()
      }
      return this.draft
    },

    /**
     * Update customer notes or line notes
     */
    async updateCartItemNotes(productId, notes) {
      const line = this.draft.lines.find((l) => l.product_id === productId)
      if (line) {
        line.notes = notes || ''
        await this.saveDraft()
      }
    },

    /**
     * Remove item from cart
     */
    async removeCartItem(productId) {
      this.draft.lines = this.draft.lines.filter((l) => l.product_id !== productId)
      // Renumber lines
      this.draft.lines.forEach((l, index) => {
        l.line_number = index + 1
      })
      await this.saveDraft()
      return this.draft
    },

    /**
     * Reset and clear draft cart
     */
    async clearCart() {
      const currentWarehouse = this.draft.warehouse_id || this.selectedWarehouseId
      this.draft = createBlankDraft(currentWarehouse)
      if (this.selectedCustomer) {
        this.draft.customer_id = this.selectedCustomer.id
        this.draft.payment_term_id = this.selectedCustomer.payment_term_id || null
        this.draft.shipping_address = this.selectedCustomer.address
          ? `${this.selectedCustomer.address}${this.selectedCustomer.city ? ', ' + this.selectedCustomer.city : ''}`
          : ''
      }
      await offlineDb.deleteDraftOrder('active_draft')
      return this.draft
    },

    /**
     * 1-Click reorder from past customer order history
     */
    async applyReorder(orderHistorySummary) {
      if (!orderHistorySummary || !Array.isArray(orderHistorySummary.lines)) return false

      const addedProducts = []
      for (const histLine of orderHistorySummary.lines) {
        if (!histLine.product_id) continue
        const product = catalogSearch.getProductById(histLine.product_id) || (await offlineDb.getProduct(histLine.product_id))

        if (product) {
          await this.addItemToCart(product, histLine.qty || 1)
          addedProducts.push(product.name)
        }
      }

      await this.saveDraft()
      return addedProducts.length > 0
    },

    // -----------------------------------------------------------------------
    // Order Submission & Sync Queue
    // -----------------------------------------------------------------------

    /**
     * Submit active draft order to offline sync queue and trigger background sync
     */
    async submitOrder(options = {}) {
      if (!this.isCartValid) {
        throw new Error('Cannot submit order: Customer selection and valid line items are required.')
      }

      this.isSubmittingOrder = true
      const authStore = useAuthStore()
      const repId = options.sales_rep_id || authStore.user?.id || null

      try {
        const orderRecord = {
          client_order_uuid: this.draft.client_order_uuid || generateUuid(),
          customer_id: this.selectedCustomer.id,
          customer_name: this.selectedCustomer.name,
          warehouse_id: this.draft.warehouse_id || this.selectedWarehouseId || 1,
          sales_rep_id: repId,
          order_date: this.draft.order_date || new Date().toISOString().split('T')[0],
          offline_created_at: new Date().toISOString(),
          subtotal: this.cartSubtotal,
          tax: this.cartTaxTotal,
          grand_total: this.cartGrandTotal,
          payment_term_id: this.draft.payment_term_id || this.selectedCustomer.payment_term_id || null,
          shipping_address: this.draft.shipping_address || null,
          customer_notes: this.draft.customer_notes || null,
          requested_delivery_date: this.draft.requested_delivery_date || null,
          signature: this.draft.signature || null,
          status: 'Pending',
          lines: this.draft.lines.map((l, index) => ({
            line_number: index + 1,
            product_id: l.product_id,
            sku: l.sku || '',
            name: l.name || l.product_name || '',
            qty: Number(l.qty) || 1,
            unit_price: Number(l.unit_price) || 0,
            base_price: Number(l.base_price) || 0,
            discount_pct: Number(l.discount_pct || l.discount_rate || 0),
            discount_rate: Number(l.discount_pct || l.discount_rate || 0),
            tax_rate: Number(l.tax_rate || 0),
            subtotal: Number(l.subtotal) || 0,
            tax_amount: Number(l.tax_amount) || 0,
            total: Number(l.total || l.line_total) || 0,
            uom_code: l.uom_code || 'UNIT',
            notes: l.notes || null
          }))
        }

        // Enqueue into SyncManager and IndexedDB
        const queued = await syncManager.enqueueOrder(orderRecord)

        // Clear active draft cart
        await this.clearCart()

        // Reload queue
        await this.loadQueuedOrders()

        return {
          success: true,
          order: queued,
          isOnline: this.isOnline
        }
      } catch (err) {
        console.error('Failed to submit field sales order:', err)
        throw err
      } finally {
        this.isSubmittingOrder = false
      }
    },

    async loadQueuedOrders() {
      try {
        const all = await offlineDb.getAllQueuedOrders()
        this.queuedOrders = all || []
        await syncManager.updateQueueMetrics()
        this.pendingCount = syncManager.pendingCount
        this.conflictCount = syncManager.conflictCount
        this.syncedCount = syncManager.syncedCount
      } catch (err) {
        console.error('Failed to load queued orders:', err)
      }
    },

    async triggerSync(options = {}) {
      return syncManager.syncQueue(options)
    },

    // -----------------------------------------------------------------------
    // Stock Conflict Handling
    // -----------------------------------------------------------------------

    openConflictModal(clientOrderUuid) {
      const order = this.queuedOrders.find((o) => o.client_order_uuid === clientOrderUuid)
      this.activeConflictOrder = order || null
    },

    closeConflictModal() {
      this.activeConflictOrder = null
    },

    /**
     * Resolve stock/price conflict for an order and re-sync
     */
    async resolveOrderConflict(clientOrderUuid, resolutions = []) {
      try {
        const result = await syncManager.resolveConflict(clientOrderUuid, resolutions)
        await this.loadQueuedOrders()
        if (this.activeConflictOrder?.client_order_uuid === clientOrderUuid) {
          this.activeConflictOrder = null
        }
        return result
      } catch (err) {
        console.error(`Failed to resolve conflict for order ${clientOrderUuid}:`, err)
        throw err
      }
    },

    /**
     * Delete an order from local queue
     */
    async deleteQueuedOrder(clientOrderUuid) {
      await offlineDb.removeFromQueue(clientOrderUuid)
      await this.loadQueuedOrders()
    },

    /**
     * Clear all synced orders from queue
     */
    async clearSyncedOrders() {
      const count = await offlineDb.clearSyncedOrders()
      await this.loadQueuedOrders()
      return count
    }
  }
})

export default useFieldSalesStore

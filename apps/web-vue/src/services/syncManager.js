/**
 * Nova ERP - Field Sales Mobile Auto-Sync Queue Manager & Network Monitor
 * Monitors online/offline connectivity, manages background sync queue,
 * implements exponential backoff, pre-sync validation, and conflict propagation.
 */

import { api as defaultApi } from '../api/client.js'
import { offlineDb as defaultOfflineDb } from './offlineDb.js'
import { catalogSearch as defaultCatalogSearch } from './catalogSearch.js'

export const SYNC_EVENTS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  STATUS_CHANGE: 'status-change',
  SYNC_START: 'sync-start',
  SYNC_PROGRESS: 'sync-progress',
  SYNC_COMPLETE: 'sync-complete',
  SYNC_ERROR: 'sync-error',
  CONFLICT: 'conflict',
  CATALOG_UPDATED: 'catalog-updated'
}

export class SyncManager {
  constructor(options = {}) {
    this.api = options.api || defaultApi
    this.db = options.db || defaultOfflineDb
    this.catalogSearch = options.catalogSearch || defaultCatalogSearch

    // Configuration
    this.autoSync = options.autoSync !== undefined ? options.autoSync : true
    this.heartbeatIntervalMs = options.heartbeatIntervalMs || 30000 // 30 seconds
    this.heartbeatTimeoutMs = options.heartbeatTimeoutMs || 5000 // 5 seconds
    this.heartbeatUrl = options.heartbeatUrl || '/sales/mobile/catalog?limit=1'
    this.maxRetries = options.maxRetries || 5
    this.initialBackoffMs = options.initialBackoffMs || 2000 // 2 seconds
    this.maxBackoffMs = options.maxBackoffMs || 60000 // 60 seconds
    this.backoffFactor = options.backoffFactor || 2

    // State
    this.isOnline = this._getInitialOnlineStatus()
    this.isSyncing = false
    this.lastSyncTime = null
    this.lastSyncError = null
    this.pendingCount = 0
    this.conflictCount = 0
    this.syncedCount = 0
    this.retryCount = 0
    this.currentBackoffMs = this.initialBackoffMs

    // Internals
    this._listeners = new Map()
    this._heartbeatTimer = null
    this._retryTimer = null
    this._activeSyncPromise = null
    this._isStarted = false
    this._deviceId = options.deviceId || null

    // Bound handlers for DOM events
    this._handleWindowOnline = this._handleWindowOnline.bind(this)
    this._handleWindowOffline = this._handleWindowOffline.bind(this)
  }

  /**
   * Determine initial online state safely across environments
   */
  _getInitialOnlineStatus() {
    if (typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean') {
      return navigator.onLine
    }
    return true
  }

  // -------------------------------------------------------------------------
  // Event Emitter Implementation
  // -------------------------------------------------------------------------

  on(event, callback) {
    if (typeof callback !== 'function') return () => {}
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set())
    }
    this._listeners.get(event).add(callback)
    return () => this.off(event, callback)
  }

  off(event, callback) {
    if (this._listeners.has(event)) {
      this._listeners.get(event).delete(callback)
    }
  }

  emit(event, ...args) {
    if (this._listeners.has(event)) {
      for (const callback of this._listeners.get(event)) {
        try {
          callback(...args)
        } catch (err) {
          console.error(`Error in SyncManager event listener for '${event}':`, err)
        }
      }
    }
  }

  // -------------------------------------------------------------------------
  // Lifecycle Management
  // -------------------------------------------------------------------------

  /**
   * Start listeners, heartbeat verification, and initial queue assessment
   */
  async start() {
    if (this._isStarted) return
    this._isStarted = true

    // Register DOM connectivity listeners
    if (typeof window !== 'undefined' && window.addEventListener) {
      window.addEventListener('online', this._handleWindowOnline)
      window.addEventListener('offline', this._handleWindowOffline)
    }

    // Refresh pending queue metrics from IndexedDB
    await this.updateQueueMetrics()

    // Start background heartbeat
    this._startHeartbeat()

    // If online on start, verify connection and trigger initial sync if enabled
    if (this.isOnline) {
      this.checkHeartbeat().then(isHealthy => {
        if (isHealthy && this.autoSync && this.pendingCount > 0) {
          this.syncQueue({ force: false }).catch(() => {})
        }
      })
    }
  }

  /**
   * Stop all timers and remove listeners
   */
  stop() {
    this._isStarted = false
    this._stopHeartbeat()
    this._cancelRetryTimer()

    if (typeof window !== 'undefined' && window.removeEventListener) {
      window.removeEventListener('online', this._handleWindowOnline)
      window.removeEventListener('offline', this._handleWindowOffline)
    }
  }

  destroy() {
    this.stop()
    this._listeners.clear()
  }

  // -------------------------------------------------------------------------
  // Connectivity & Heartbeat
  // -------------------------------------------------------------------------

  _handleWindowOnline() {
    return this.checkHeartbeat().then(isReachable => {
      if (isReachable) {
        this._setOnlineState(true)
        if (this.autoSync) {
          this.syncQueue({ force: false }).catch(() => {})
        }
      }
    })
  }

  _handleWindowOffline() {
    this._setOnlineState(false)
  }

  _setOnlineState(newStatus) {
    const changed = this.isOnline !== newStatus
    this.isOnline = newStatus

    if (changed) {
      this.emit(newStatus ? SYNC_EVENTS.ONLINE : SYNC_EVENTS.OFFLINE, { isOnline: newStatus })
      this.emit(SYNC_EVENTS.STATUS_CHANGE, this.getStatus())
    }
  }

  /**
   * Ping backend to verify genuine end-to-end network connectivity
   */
  async checkHeartbeat() {
    try {
      const response = await this.api.get(this.heartbeatUrl, {
        timeout: this.heartbeatTimeoutMs,
        headers: { 'Cache-Control': 'no-cache' }
      })
      const isReachable = response && (response.status >= 200 && response.status < 400)
      this._setOnlineState(Boolean(isReachable))
      return Boolean(isReachable)
    } catch (err) {
      // If error is network error or timeout, we are offline
      this._setOnlineState(false)
      return false
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    if (this.heartbeatIntervalMs > 0 && typeof setInterval !== 'undefined') {
      this._heartbeatTimer = setInterval(() => {
        this.checkHeartbeat().catch(() => {})
      }, this.heartbeatIntervalMs)
    }
  }

  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
  }

  // -------------------------------------------------------------------------
  // Queue Metrics and Device Identity
  // -------------------------------------------------------------------------

  async getDeviceId() {
    if (this._deviceId) return this._deviceId
    try {
      const saved = await this.db.getMeta('device_id')
      if (saved) {
        this._deviceId = saved
        return saved
      }
      const newId = `mobile_rep_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
      await this.db.setMeta('device_id', newId)
      this._deviceId = newId
      return newId
    } catch {
      return 'mobile_rep_device'
    }
  }

  /**
   * Recalculate queue item counts from storage
   */
  async updateQueueMetrics() {
    try {
      const allQueued = await this.db.getAllQueuedOrders()
      this.pendingCount = allQueued.filter(o => o.status === 'Pending' || o.status === 'Failed').length
      this.conflictCount = allQueued.filter(o => o.status === 'Conflict').length
      this.syncedCount = allQueued.filter(o => o.status === 'Synced' || o.status === 'AlreadySynced').length
      this.emit(SYNC_EVENTS.STATUS_CHANGE, this.getStatus())
      return {
        pending: this.pendingCount,
        conflict: this.conflictCount,
        synced: this.syncedCount,
        total: allQueued.length
      }
    } catch {
      return { pending: 0, conflict: 0, synced: 0, total: 0 }
    }
  }

  getStatus() {
    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      lastSyncTime: this.lastSyncTime,
      lastSyncError: this.lastSyncError,
      pendingCount: this.pendingCount,
      conflictCount: this.conflictCount,
      syncedCount: this.syncedCount,
      retryCount: this.retryCount
    }
  }

  // -------------------------------------------------------------------------
  // Order Enqueueing & Offline Capture
  // -------------------------------------------------------------------------

  /**
   * Enqueue a newly drafted field sales order
   */
  async enqueueOrder(order) {
    const record = await this.db.enqueueOrder(order)
    await this.updateQueueMetrics()

    // If online and autoSync enabled, trigger background sync
    if (this.isOnline && this.autoSync) {
      this.syncQueue({ force: false }).catch(() => {})
    }

    return record
  }

  // -------------------------------------------------------------------------
  // Queue Synchronization Engine
  // -------------------------------------------------------------------------

  /**
   * Drain pending sync queue with atomic batch submission and stock conflict detection
   */
  async syncQueue(options = {}) {
    const { force = false, includeCatalog = false } = options

    // Prevent concurrent sync execution
    if (this.isSyncing && this._activeSyncPromise) {
      return this._activeSyncPromise
    }

    if (!this.isOnline && !force) {
      return {
        success: false,
        reason: 'offline',
        message: 'Device is currently offline. Orders remain queued locally.'
      }
    }

    this.isSyncing = true
    this.emit(SYNC_EVENTS.SYNC_START)
    this.emit(SYNC_EVENTS.STATUS_CHANGE, this.getStatus())

    this._activeSyncPromise = (async () => {
      try {
        const pendingOrders = await this.db.getPendingOrders()

        // Filter out orders that have unsolved blocking conflicts unless force retrying
        const ordersToSync = pendingOrders.filter(o => o.status === 'Pending' || o.status === 'Failed' || (force && o.status === 'Conflict'))

        if (!ordersToSync.length) {
          this.isSyncing = false
          this.lastSyncError = null
          await this.updateQueueMetrics()

          if (includeCatalog) {
            await this.syncCatalog()
          }

          const result = {
            success: true,
            total_orders: 0,
            synced_count: 0,
            conflict_count: 0,
            failed_count: 0,
            results: []
          }
          this.emit(SYNC_EVENTS.SYNC_COMPLETE, result)
          return result
        }

        const deviceId = await this.getDeviceId()

        // Format batch payload matching FieldSalesBatchSyncRequest
        const payload = {
          device_id: deviceId,
          orders: ordersToSync.map(order => ({
            client_order_uuid: order.client_order_uuid,
            customer_id: order.customer_id,
            warehouse_id: order.warehouse_id || 1,
            offline_created_at: order.offline_created_at || order.queued_at || new Date().toISOString(),
            lines: (order.lines || []).map(line => ({
              product_id: line.product_id,
              sku: line.sku || '',
              name: line.name || '',
              qty: Number(line.qty) || 1,
              unit_price: Number(line.unit_price) || 0,
              discount_rate: Number(line.discount_rate || 0),
              tax_rate: Number(line.tax_rate || 0),
              notes: line.notes || null
            })),
            customer_notes: order.customer_notes || null,
            shipping_address: order.shipping_address || null,
            payment_term_id: order.payment_term_id || null,
            requested_delivery_date: order.requested_delivery_date || null,
            sales_rep_id: order.sales_rep_id || null
          }))
        }

        this.emit(SYNC_EVENTS.SYNC_PROGRESS, {
          phase: 'uploading',
          count: ordersToSync.length
        })

        // POST batch to backend endpoint
        const response = await this.api.post('/sales/mobile/sync', payload)
        const data = response.data || {}
        const results = data.results || []

        // Process individual order results
        for (const item of results) {
          const uuid = item.client_order_uuid
          if (!uuid) continue

          if (item.status === 'Synced' || item.status === 'AlreadySynced') {
            await this.db.updateQueueOrderStatus(uuid, 'Synced', {
              server_order_id: item.order_id,
              order_number: item.order_number,
              synced_at: new Date().toISOString(),
              error_message: null,
              conflicts: []
            })
          } else if (item.status === 'Conflict') {
            await this.db.updateQueueOrderStatus(uuid, 'Conflict', {
              conflicts: item.conflicts || [],
              error_message: item.error_message || 'Stock or price conflict detected'
            })
            const orderRecord = await this.db.getQueuedOrder(uuid)
            this.emit(SYNC_EVENTS.CONFLICT, {
              client_order_uuid: uuid,
              order: orderRecord,
              conflicts: item.conflicts || []
            })
          } else if (item.status === 'Failed') {
            const existing = await this.db.getQueuedOrder(uuid)
            const currentRetries = (existing?.retry_count || 0) + 1
            await this.db.updateQueueOrderStatus(uuid, 'Failed', {
              retry_count: currentRetries,
              last_error: item.error_message || 'Order synchronization failed'
            })
          }
        }

        // Reset backoff upon successful server communication
        this.retryCount = 0
        this.currentBackoffMs = this.initialBackoffMs
        this.lastSyncTime = new Date().toISOString()
        this.lastSyncError = null

        // Sync catalog updates if requested
        if (includeCatalog) {
          await this.syncCatalog()
        }

        await this.updateQueueMetrics()

        const summary = {
          success: true,
          total_orders: data.total_orders || ordersToSync.length,
          synced_count: data.synced_count || 0,
          conflict_count: data.conflict_count || 0,
          failed_count: data.failed_count || 0,
          results
        }

        this.emit(SYNC_EVENTS.SYNC_COMPLETE, summary)
        return summary
      } catch (err) {
        console.error('Field Sales sync error:', err)
        this.lastSyncError = err.message || 'Network or server error during sync'
        this.retryCount++

        // Schedule exponential backoff retry if autoSync is active
        this._scheduleRetry()

        this.emit(SYNC_EVENTS.SYNC_ERROR, {
          error: err,
          retryCount: this.retryCount,
          nextRetryMs: this.currentBackoffMs
        })

        return {
          success: false,
          error: err.message,
          retryCount: this.retryCount
        }
      } finally {
        this.isSyncing = false
        this._activeSyncPromise = null
        await this.updateQueueMetrics()
        this.emit(SYNC_EVENTS.STATUS_CHANGE, this.getStatus())
      }
    })()

    return this._activeSyncPromise
  }

  // -------------------------------------------------------------------------
  // Exponential Backoff Retry Scheduling
  // -------------------------------------------------------------------------

  _scheduleRetry() {
    this._cancelRetryTimer()
    if (!this.autoSync || this.retryCount > this.maxRetries) {
      return
    }

    const delay = Math.min(this.currentBackoffMs, this.maxBackoffMs)
    this.currentBackoffMs = Math.min(this.currentBackoffMs * this.backoffFactor, this.maxBackoffMs)

    if (typeof setTimeout !== 'undefined') {
      this._retryTimer = setTimeout(() => {
        if (this.isOnline && this.autoSync) {
          this.syncQueue({ force: false }).catch(() => {})
        }
      }, delay)
    }
  }

  _cancelRetryTimer() {
    if (this._retryTimer) {
      clearTimeout(this._retryTimer)
      this._retryTimer = null
    }
  }

  // -------------------------------------------------------------------------
  // Pre-Sync Validation (Dry-Run Check)
  // -------------------------------------------------------------------------

  /**
   * Validate queued orders against live server inventory without committing
   */
  async validateQueue(specificOrders = null) {
    if (!this.isOnline) {
      return {
        is_valid: true,
        can_sync_cleanly: true,
        note: 'Offline validation skipped; local check only'
      }
    }

    try {
      const orders = specificOrders || (await this.db.getPendingOrders())
      if (!orders.length) {
        return { is_valid: true, can_sync_cleanly: true, reports: [] }
      }

      const payload = {
        orders: orders.map(o => ({
          client_order_uuid: o.client_order_uuid,
          customer_id: o.customer_id,
          warehouse_id: o.warehouse_id || 1,
          lines: (o.lines || []).map(l => ({
            product_id: l.product_id,
            sku: l.sku || '',
            qty: Number(l.qty) || 1,
            unit_price: Number(l.unit_price) || 0
          }))
        }))
      }

      const response = await this.api.post('/sales/mobile/validate', payload)
      return response.data
    } catch (err) {
      console.warn('Pre-sync validation request failed:', err)
      return {
        is_valid: false,
        error: err.message
      }
    }
  }

  // -------------------------------------------------------------------------
  // Conflict Resolution Engine
  // -------------------------------------------------------------------------

  /**
   * Resolve conflict actions on a specific order and sync immediately
   * resolutionActions: Array of FieldSalesConflictResolutionItem:
   * [{ product_id, action: 'adjust_qty'|'substitute'|'accept_price'|'remove_item'|'backorder', new_qty, substitute_product_id }]
   */
  async resolveConflict(clientOrderUuid, resolutionActions = []) {
    const queuedOrder = await this.db.getQueuedOrder(clientOrderUuid)
    if (!queuedOrder) {
      throw new Error(`Order with UUID ${clientOrderUuid} not found in sync queue`)
    }

    const payload = {
      client_order_uuid: clientOrderUuid,
      order_data: {
        client_order_uuid: clientOrderUuid,
        customer_id: queuedOrder.customer_id,
        warehouse_id: queuedOrder.warehouse_id || 1,
        lines: (queuedOrder.lines || []).map((l, idx) => ({
          line_number: l.line_number || idx + 1,
          product_id: Number(l.product_id),
          product_name: l.product_name || l.name || '',
          sku: l.sku || '',
          qty: Number(l.qty) || 1,
          unit_price: Number(l.unit_price) || 0,
          discount_pct: Number(l.discount_pct || l.discount_rate || 0),
          line_total: Number(l.line_total || l.total || l.subtotal) || 0,
          uom_id: l.uom_id || null,
          notes: l.notes || null
        })),
        customer_notes: queuedOrder.customer_notes || null,
        shipping_address: queuedOrder.shipping_address || null,
        payment_term_id: queuedOrder.payment_term_id || null,
        requested_delivery_date: queuedOrder.requested_delivery_date || null,
        sales_rep_id: queuedOrder.sales_rep_id || null
      },
      resolutions: (resolutionActions || []).map((res) => ({
        line_number: res.line_number || null,
        product_id: Number(res.product_id),
        action: res.action,
        adjusted_qty: res.adjusted_qty !== undefined ? Number(res.adjusted_qty) : (res.new_qty !== undefined ? Number(res.new_qty) : null),
        substitute_product_id: res.substitute_product_id ? Number(res.substitute_product_id) : null,
        substitute_product_name: res.substitute_product_name || null,
        accepted_price: res.accepted_price !== undefined ? Number(res.accepted_price) : (res.new_unit_price !== undefined ? Number(res.new_unit_price) : null)
      }))
    }

    try {
      const response = await this.api.post('/sales/mobile/resolve-conflict', payload)
      const result = response.data

      if (result.status === 'Synced' || result.status === 'AlreadySynced') {
        await this.db.updateQueueOrderStatus(clientOrderUuid, 'Synced', {
          server_order_id: result.server_order_id || result.order_id,
          order_number: result.order_number,
          synced_at: new Date().toISOString(),
          conflicts: [],
          error_message: null
        })
      } else if (result.status === 'Conflict') {
        await this.db.updateQueueOrderStatus(clientOrderUuid, 'Conflict', {
          conflicts: result.conflicts || [],
          error_message: result.message || result.error_message || 'Stock or price conflict detected'
        })
      } else if (result.status === 'Failed') {
        await this.db.updateQueueOrderStatus(clientOrderUuid, 'Failed', {
          error_message: result.message || 'Conflict resolution failed'
        })
      }

      await this.updateQueueMetrics()
      return result
    } catch (err) {
      console.error(`Failed to resolve conflict for order ${clientOrderUuid}:`, err)
      throw err
    }
  }

  // -------------------------------------------------------------------------
  // Catalog Delta Synchronization
  // -------------------------------------------------------------------------

  /**
   * Fetch delta or full mobile catalog bundle and refresh local cache
   */
  async syncCatalog(options = {}) {
    if (!this.isOnline) {
      return { success: false, reason: 'offline' }
    }

    try {
      const deltaTimestamp = options.forceFull
        ? null
        : (options.deltaTimestamp || (await this.db.getMeta('delta_timestamp')))

      const params = {}
      if (deltaTimestamp) {
        params.delta_timestamp = deltaTimestamp
      }
      if (options.warehouse_id) {
        params.warehouse_id = options.warehouse_id
      }
      if (options.sales_rep_id) {
        params.sales_rep_id = options.sales_rep_id
      }

      const response = await this.api.get('/sales/mobile/catalog', { params })
      const bundle = response.data

      if (bundle) {
        // Save to IndexedDB
        await this.db.saveCatalogBundle(bundle)

        // Reload fast in-memory search indexer
        if (this.catalogSearch && typeof this.catalogSearch.loadFromDb === 'function') {
          await this.catalogSearch.loadFromDb(this.db)
        }

        this.emit(SYNC_EVENTS.CATALOG_UPDATED, bundle)
      }

      return { success: true, bundle }
    } catch (err) {
      console.error('Error synchronizing mobile catalog:', err)
      return { success: false, error: err.message }
    }
  }
}

// Default singleton instance
export const syncManager = new SyncManager()
export default syncManager

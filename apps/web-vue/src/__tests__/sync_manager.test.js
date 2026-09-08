import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { SyncManager, SYNC_EVENTS } from '../services/syncManager.js'
import { OfflineDb } from '../services/offlineDb.js'
import { CatalogSearchEngine } from '../services/catalogSearch.js'

describe('SyncManager Service', () => {
  let testDb
  let mockApi
  let mockSearch
  let syncMgr

  beforeEach(async () => {
    const dbName = `test_sync_db_${Date.now()}_${Math.random().toString(36).substring(7)}`
    testDb = new OfflineDb(dbName, 1)
    await testDb.openDb()

    mockApi = {
      get: vi.fn(),
      post: vi.fn()
    }

    mockSearch = new CatalogSearchEngine()
    vi.spyOn(mockSearch, 'loadFromDb').mockResolvedValue(10)

    syncMgr = new SyncManager({
      api: mockApi,
      db: testDb,
      catalogSearch: mockSearch,
      autoSync: true,
      heartbeatIntervalMs: 0, // Disable automatic timer in unit tests
      initialBackoffMs: 50,
      maxBackoffMs: 200,
      backoffFactor: 2
    })
  })

  afterEach(async () => {
    if (syncMgr) {
      syncMgr.destroy()
    }
    if (testDb) {
      await testDb.deleteDatabase()
    }
    vi.clearAllTimers()
    vi.restoreAllMocks()
  })

  describe('Initialization and Event Emitter', () => {
    it('initializes with default online state and empty queue metrics', async () => {
      const status = syncMgr.getStatus()
      expect(status.isOnline).toBe(true)
      expect(status.isSyncing).toBe(false)
      expect(status.pendingCount).toBe(0)
      expect(status.conflictCount).toBe(0)
      expect(status.syncedCount).toBe(0)
    })

    it('registers and triggers event listeners', () => {
      const callback = vi.fn()
      const unsubscribe = syncMgr.on(SYNC_EVENTS.STATUS_CHANGE, callback)

      syncMgr.emit(SYNC_EVENTS.STATUS_CHANGE, { test: 123 })
      expect(callback).toHaveBeenCalledWith({ test: 123 })

      unsubscribe()
      syncMgr.emit(SYNC_EVENTS.STATUS_CHANGE, { test: 456 })
      expect(callback).toHaveBeenCalledTimes(1)
    })
  })

  describe('Heartbeat and Network Status', () => {
    it('detects successful heartbeat and maintains online state', async () => {
      mockApi.get.mockResolvedValueOnce({ status: 200, data: { ok: true } })

      const isReachable = await syncMgr.checkHeartbeat()
      expect(isReachable).toBe(true)
      expect(syncMgr.isOnline).toBe(true)
    })

    it('detects failed heartbeat and sets offline state with event emission', async () => {
      const offlineSpy = vi.fn()
      syncMgr.on(SYNC_EVENTS.OFFLINE, offlineSpy)

      mockApi.get.mockRejectedValueOnce(new Error('Network Error'))

      const isReachable = await syncMgr.checkHeartbeat()
      expect(isReachable).toBe(false)
      expect(syncMgr.isOnline).toBe(false)
      expect(offlineSpy).toHaveBeenCalledWith({ isOnline: false })
    })

    it('automatically triggers background batch sync when internet access is restored', async () => {
      syncMgr.isOnline = false
      const syncSpy = vi.spyOn(syncMgr, 'syncQueue').mockResolvedValue({ success: true })
      mockApi.get.mockResolvedValueOnce({ status: 200, data: { ok: true } })

      await syncMgr._handleWindowOnline()

      expect(syncMgr.isOnline).toBe(true)
      expect(syncSpy).toHaveBeenCalledWith({ force: false })
    })

    it('registers and removes window event listeners on start and stop', async () => {
      const addSpy = vi.spyOn(window, 'addEventListener')
      const removeSpy = vi.spyOn(window, 'removeEventListener')

      await syncMgr.start()
      expect(addSpy).toHaveBeenCalledWith('online', expect.any(Function))
      expect(addSpy).toHaveBeenCalledWith('offline', expect.any(Function))

      syncMgr.stop()
      expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function))
      expect(removeSpy).toHaveBeenCalledWith('offline', expect.any(Function))
    })
  })

  describe('Order Enqueueing and Metrics', () => {
    it('enqueues order in IndexedDB and updates pending count', async () => {
      const order = {
        client_order_uuid: 'test-order-uuid-1',
        customer_id: 101,
        lines: [{ product_id: 1, qty: 5, unit_price: 10.0 }],
        grand_total: 50.0
      }

      // Mock syncQueue to avoid running during enqueue in this test
      vi.spyOn(syncMgr, 'syncQueue').mockResolvedValue({ success: true })

      const enqueued = await syncMgr.enqueueOrder(order)
      expect(enqueued.client_order_uuid).toBe('test-order-uuid-1')

      const metrics = await syncMgr.updateQueueMetrics()
      expect(metrics.pending).toBe(1)
      expect(syncMgr.pendingCount).toBe(1)
    })
  })

  describe('Batch Synchronization', () => {
    it('skips sync when device is offline unless forced', async () => {
      syncMgr.isOnline = false

      const result = await syncMgr.syncQueue({ force: false })
      expect(result.success).toBe(false)
      expect(result.reason).toBe('offline')
      expect(mockApi.post).not.toHaveBeenCalled()
    })

    it('synchronizes pending orders and marks them as Synced on server success', async () => {
      // 1. Seed two pending orders in IndexedDB
      await testDb.enqueueOrder({
        client_order_uuid: 'order-uuid-101',
        customer_id: 201,
        lines: [{ product_id: 10, qty: 2, unit_price: 15.0 }]
      })
      await testDb.enqueueOrder({
        client_order_uuid: 'order-uuid-102',
        customer_id: 202,
        lines: [{ product_id: 11, qty: 1, unit_price: 25.0 }]
      })

      // 2. Mock successful batch response from backend
      mockApi.post.mockResolvedValueOnce({
        data: {
          total_orders: 2,
          synced_count: 2,
          conflict_count: 0,
          failed_count: 0,
          results: [
            {
              client_order_uuid: 'order-uuid-101',
              status: 'Synced',
              order_id: 501,
              order_number: 'SO-2026-00501'
            },
            {
              client_order_uuid: 'order-uuid-102',
              status: 'Synced',
              order_id: 502,
              order_number: 'SO-2026-00502'
            }
          ]
        }
      })

      const completeSpy = vi.fn()
      syncMgr.on(SYNC_EVENTS.SYNC_COMPLETE, completeSpy)

      const result = await syncMgr.syncQueue()

      expect(result.success).toBe(true)
      expect(result.synced_count).toBe(2)
      expect(mockApi.post).toHaveBeenCalledWith('/sales/mobile/sync', expect.objectContaining({
        orders: expect.arrayContaining([
          expect.objectContaining({ client_order_uuid: 'order-uuid-101' }),
          expect.objectContaining({ client_order_uuid: 'order-uuid-102' })
        ])
      }))

      // Verify IndexedDB records were updated
      const order1 = await testDb.getQueuedOrder('order-uuid-101')
      expect(order1.status).toBe('Synced')
      expect(order1.server_order_id).toBe(501)

      const order2 = await testDb.getQueuedOrder('order-uuid-102')
      expect(order2.status).toBe('Synced')
      expect(order2.server_order_id).toBe(502)

      expect(completeSpy).toHaveBeenCalled()
      expect(syncMgr.syncedCount).toBe(2)
      expect(syncMgr.pendingCount).toBe(0)
    })

    it('identifies stock conflicts and emits conflict event', async () => {
      await testDb.enqueueOrder({
        client_order_uuid: 'order-conflict-uuid',
        customer_id: 301,
        lines: [{ product_id: 99, qty: 100, unit_price: 20.0 }]
      })

      mockApi.post.mockResolvedValueOnce({
        data: {
          total_orders: 1,
          synced_count: 0,
          conflict_count: 1,
          failed_count: 0,
          results: [
            {
              client_order_uuid: 'order-conflict-uuid',
              status: 'Conflict',
              error_message: 'Stock depleted while offline',
              conflicts: [
                {
                  product_id: 99,
                  conflict_type: 'OUT_OF_STOCK',
                  requested_qty: 100,
                  available_qty: 0,
                  suggested_substitutes: [{ product_id: 100, name: 'Substitute Item' }]
                }
              ]
            }
          ]
        }
      })

      const conflictSpy = vi.fn()
      syncMgr.on(SYNC_EVENTS.CONFLICT, conflictSpy)

      const result = await syncMgr.syncQueue()

      expect(result.success).toBe(true)
      expect(result.conflict_count).toBe(1)

      const storedOrder = await testDb.getQueuedOrder('order-conflict-uuid')
      expect(storedOrder.status).toBe('Conflict')
      expect(storedOrder.conflicts.length).toBe(1)
      expect(storedOrder.conflicts[0].conflict_type).toBe('OUT_OF_STOCK')

      expect(conflictSpy).toHaveBeenCalledWith(expect.objectContaining({
        client_order_uuid: 'order-conflict-uuid'
      }))
      expect(syncMgr.conflictCount).toBe(1)
    })

    it('handles server network failure, increments retry count, and emits error event', async () => {
      await testDb.enqueueOrder({
        client_order_uuid: 'order-error-uuid',
        customer_id: 401,
        lines: [{ product_id: 1, qty: 1, unit_price: 10 }]
      })

      mockApi.post.mockRejectedValueOnce(new Error('500 Internal Server Error'))

      const errorSpy = vi.fn()
      syncMgr.on(SYNC_EVENTS.SYNC_ERROR, errorSpy)

      const result = await syncMgr.syncQueue()

      expect(result.success).toBe(false)
      expect(result.error).toBe('500 Internal Server Error')
      expect(syncMgr.retryCount).toBe(1)
      expect(errorSpy).toHaveBeenCalled()
    })
  })

  describe('Pre-Sync Validation and Conflict Resolution', () => {
    it('validates queue without committing changes', async () => {
      await testDb.enqueueOrder({
        client_order_uuid: 'val-uuid-1',
        customer_id: 501,
        lines: [{ product_id: 1, qty: 2, unit_price: 10 }]
      })

      mockApi.post.mockResolvedValueOnce({
        data: {
          is_valid: true,
          can_sync_cleanly: true,
          total_orders: 1,
          conflicted_orders_count: 0
        }
      })

      const valResult = await syncMgr.validateQueue()
      expect(valResult.is_valid).toBe(true)
      expect(mockApi.post).toHaveBeenCalledWith('/sales/mobile/validate', expect.any(Object))
    })

    it('resolves conflict and synchronizes order', async () => {
      await testDb.enqueueOrder({
        client_order_uuid: 'order-to-resolve-uuid',
        customer_id: 601,
        status: 'Conflict',
        lines: [{ product_id: 10, qty: 50, unit_price: 5.0 }],
        conflicts: [{ product_id: 10, conflict_type: 'INSUFFICIENT_QTY', available_qty: 20 }]
      })

      mockApi.post.mockResolvedValueOnce({
        data: {
          client_order_uuid: 'order-to-resolve-uuid',
          status: 'Synced',
          order_id: 888,
          order_number: 'SO-2026-00888'
        }
      })

      const resolutionActions = [
        { product_id: 10, action: 'adjust_qty', new_qty: 20 }
      ]

      const resolveRes = await syncMgr.resolveConflict('order-to-resolve-uuid', resolutionActions)
      expect(resolveRes.status).toBe('Synced')
      expect(resolveRes.order_id).toBe(888)

      const updated = await testDb.getQueuedOrder('order-to-resolve-uuid')
      expect(updated.status).toBe('Synced')
      expect(updated.server_order_id).toBe(888)
      expect(updated.conflicts.length).toBe(0)
    })
  })

  describe('Catalog Delta Synchronization', () => {
    it('downloads catalog bundle and triggers catalog search index refresh', async () => {
      mockApi.get.mockResolvedValueOnce({
        data: {
          sync_timestamp: '2026-08-23T10:00:00Z',
          delta_timestamp: '2026-08-23T09:00:00Z',
          products: [{ id: 901, sku: 'TEST-SKU', name: 'Fresh Test Product' }],
          customers: [{ id: 1001, name: 'Test Market' }]
        }
      })

      const updatedSpy = vi.fn()
      syncMgr.on(SYNC_EVENTS.CATALOG_UPDATED, updatedSpy)

      const syncRes = await syncMgr.syncCatalog()
      expect(syncRes.success).toBe(true)
      expect(mockSearch.loadFromDb).toHaveBeenCalledWith(testDb)
      expect(updatedSpy).toHaveBeenCalled()

      const savedProduct = await testDb.getProduct(901)
      expect(savedProduct).not.toBeNull()
      expect(savedProduct.name).toBe('Fresh Test Product')
    })
  })
})

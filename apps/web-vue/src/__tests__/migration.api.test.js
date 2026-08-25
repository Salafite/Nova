import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api } from '../api/client.js'
import {
  listConnectors,
  testConnection,
  discoverSchema,
  previewTable,
  runDryRun,
  commitBatch,
  rollbackBatch,
  listBatches,
  getBatch,
  getBatchReconciliation,
  getBatchItems,
  uploadCsv,
  migrationApi,
} from '../api/migration.js'

vi.mock('../api/client.js', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  CONFIG: { apiBase: 'http://test.local' },
}))

describe('migration API client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listConnectors calls GET /v1/migration/connectors', async () => {
    const mockConnectors = [
      { id: 'sqlserver', name: 'Microsoft SQL Server' },
      { id: 'csv_dump', name: 'CSV & SQL Dumps' },
    ]
    api.get.mockResolvedValue({ data: mockConnectors })

    const result = await listConnectors()
    expect(api.get).toHaveBeenCalledWith('/v1/migration/connectors')
    expect(result).toEqual(mockConnectors)
  })

  it('testConnection calls POST /v1/migration/connectors/test', async () => {
    const payload = {
      source_type: 'sqlserver',
      host: '127.0.0.1',
      port: 1433,
      database: 'LegacyDB',
      user: 'sa',
      password: 'secret',
    }
    const mockResponse = {
      success: true,
      message: 'Connection successful',
      latency_ms: 12.5,
      tables_count: 24,
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await testConnection(payload)
    expect(api.post).toHaveBeenCalledWith('/v1/migration/connectors/test', payload)
    expect(result).toEqual(mockResponse)
  })

  it('discoverSchema calls POST /v1/migration/connectors/discover', async () => {
    const payload = {
      source_type: 'sqlserver',
      host: '127.0.0.1',
      database: 'LegacyDB',
    }
    const mockResponse = {
      success: true,
      tables_count: 2,
      tables: ['tbl_Items', 'tbl_Customers'],
      schemas: {
        tbl_Items: { columns: [{ name: 'ItemCode', type: 'nvarchar' }] },
      },
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await discoverSchema(payload)
    expect(api.post).toHaveBeenCalledWith('/v1/migration/connectors/discover', payload)
    expect(result).toEqual(mockResponse)
  })

  it('previewTable calls POST /v1/migration/connectors/preview', async () => {
    const payload = {
      source_type: 'sqlserver',
      connection: { host: '127.0.0.1', database: 'LegacyDB' },
      table_name: 'tbl_Items',
      limit: 5,
      offset: 0,
    }
    const mockResponse = {
      success: true,
      table_name: 'tbl_Items',
      total_rows_estimate: 1500,
      columns: ['ItemCode', 'ItemName', 'Price'],
      rows: [['ITM001', 'Widget A', 10.5]],
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await previewTable(payload)
    expect(api.post).toHaveBeenCalledWith('/v1/migration/connectors/preview', payload)
    expect(result).toEqual(mockResponse)
  })

  it('runDryRun calls POST /v1/migration/dry-run', async () => {
    const payload = {
      source_type: 'sqlserver',
      connection: { host: '127.0.0.1' },
      table_mappings: { products: 'tbl_Items' },
      cleansing_options: { detect_phantom_products: true },
      batch_name: 'Batch #1',
    }
    const mockResponse = {
      success: true,
      batch_id: 101,
      status: 'DryRunCompleted',
      staged_records: 450,
      phantom_products_flagged: 12,
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await runDryRun(payload)
    expect(api.post).toHaveBeenCalledWith('/v1/migration/dry-run', payload)
    expect(result).toEqual(mockResponse)
  })

  it('commitBatch handles numeric batch ID and force flag', async () => {
    const mockResponse = {
      success: true,
      batch_id: 101,
      status: 'Committed',
      total_records_committed: 450,
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await commitBatch(101, true)
    expect(api.post).toHaveBeenCalledWith('/v1/migration/commit', { batch_id: 101, force: true })
    expect(result).toEqual(mockResponse)
  })

  it('commitBatch handles payload object', async () => {
    const mockResponse = {
      success: true,
      batch_id: 102,
      status: 'Committed',
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await commitBatch({ batch_id: 102, force: false })
    expect(api.post).toHaveBeenCalledWith('/v1/migration/commit', { batch_id: 102, force: false })
    expect(result).toEqual(mockResponse)
  })

  it('rollbackBatch handles numeric batch ID and reason', async () => {
    const mockResponse = {
      success: true,
      batch_id: 101,
      status: 'RolledBack',
      total_records_rolled_back: 450,
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await rollbackBatch(101, 'Testing rollback')
    expect(api.post).toHaveBeenCalledWith('/v1/migration/rollback', {
      batch_id: 101,
      reason: 'Testing rollback',
    })
    expect(result).toEqual(mockResponse)
  })

  it('rollbackBatch handles payload object', async () => {
    const mockResponse = {
      success: true,
      batch_id: 103,
      status: 'RolledBack',
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const result = await rollbackBatch({ batch_id: 103, reason: 'Wrong data' })
    expect(api.post).toHaveBeenCalledWith('/v1/migration/rollback', {
      batch_id: 103,
      reason: 'Wrong data',
    })
    expect(result).toEqual(mockResponse)
  })

  it('listBatches calls GET /v1/migration/batches with params', async () => {
    const mockResponse = {
      items: [{ id: 1, batch_name: 'Batch 1', status: 'Committed' }],
      total: 1,
      limit: 20,
      offset: 0,
    }
    api.get.mockResolvedValue({ data: mockResponse })

    const params = { limit: 20, offset: 0, status: 'Committed' }
    const result = await listBatches(params)
    expect(api.get).toHaveBeenCalledWith('/v1/migration/batches', { params })
    expect(result).toEqual(mockResponse)
  })

  it('getBatch calls GET /v1/migration/batches/:id', async () => {
    const mockResponse = { id: 101, batch_name: 'Test Batch', status: 'DryRunCompleted' }
    api.get.mockResolvedValue({ data: mockResponse })

    const result = await getBatch(101)
    expect(api.get).toHaveBeenCalledWith('/v1/migration/batches/101')
    expect(result).toEqual(mockResponse)
  })

  it('getBatchReconciliation calls GET /v1/migration/batches/:id/reconciliation', async () => {
    const mockReport = {
      batch_id: 101,
      overall_status: 'Passed',
      customer_balances: { total_legacy_receivables: 5000 },
      inventory: { total_legacy_qty: 1200 },
    }
    api.get.mockResolvedValue({ data: mockReport })

    const result = await getBatchReconciliation(101, { tolerance: 0.05 })
    expect(api.get).toHaveBeenCalledWith('/v1/migration/batches/101/reconciliation', {
      params: { tolerance: 0.05 },
    })
    expect(result).toEqual(mockReport)
  })

  it('getBatchItems calls GET /v1/migration/batches/:id/items', async () => {
    const mockItems = [
      { id: 1, entity_type: 'products', target_table: 't0003', target_id: 42, status: 'Inserted' },
    ]
    api.get.mockResolvedValue({ data: mockItems })

    const result = await getBatchItems(101, { entity_type: 'products', limit: 50 })
    expect(api.get).toHaveBeenCalledWith('/v1/migration/batches/101/items', {
      params: { entity_type: 'products', limit: 50 },
    })
    expect(result).toEqual(mockItems)
  })

  it('uploadCsv with File object constructs FormData and posts to /v1/migration/upload', async () => {
    const mockResponse = {
      batch_id: 55,
      total_rows: 10,
      valid_rows: 10,
      sample: [],
    }
    api.post.mockResolvedValue({ data: mockResponse })

    const fakeFile = new Blob(['sku,name\nSKU1,Prod1'], { type: 'text/csv' })
    const result = await uploadCsv(fakeFile, 'products', { sku: 'sku', name: 'name' })

    expect(api.post).toHaveBeenCalledWith(
      '/v1/migration/upload',
      expect.any(FormData),
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    expect(result).toEqual(mockResponse)
  })

  it('uploadCsv with existing FormData passes it directly', async () => {
    const mockResponse = { batch_id: 56, total_rows: 5 }
    api.post.mockResolvedValue({ data: mockResponse })

    const form = new FormData()
    form.append('entity_type', 'suppliers')
    const result = await uploadCsv(form)

    expect(api.post).toHaveBeenCalledWith(
      '/v1/migration/upload',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    expect(result).toEqual(mockResponse)
  })

  it('migrationApi default export contains all functions', () => {
    expect(migrationApi.listConnectors).toBe(listConnectors)
    expect(migrationApi.testConnection).toBe(testConnection)
    expect(migrationApi.discoverSchema).toBe(discoverSchema)
    expect(migrationApi.previewTable).toBe(previewTable)
    expect(migrationApi.runDryRun).toBe(runDryRun)
    expect(migrationApi.commitBatch).toBe(commitBatch)
    expect(migrationApi.rollbackBatch).toBe(rollbackBatch)
    expect(migrationApi.listBatches).toBe(listBatches)
    expect(migrationApi.getBatch).toBe(getBatch)
    expect(migrationApi.getBatchReconciliation).toBe(getBatchReconciliation)
    expect(migrationApi.getBatchItems).toBe(getBatchItems)
    expect(migrationApi.uploadCsv).toBe(uploadCsv)
  })
})

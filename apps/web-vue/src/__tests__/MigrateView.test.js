import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import MigrateView from '../views/migration/MigrateView.vue'
import { migrationApi } from '../api/migration.js'

// Mock the migrationApi methods
vi.mock('../api/migration.js', () => ({
  migrationApi: {
    listConnectors: vi.fn(),
    testConnection: vi.fn(),
    discoverSchema: vi.fn(),
    previewTable: vi.fn(),
    runDryRun: vi.fn(),
    commitBatch: vi.fn(),
    rollbackBatch: vi.fn(),
    listBatches: vi.fn(),
    getBatch: vi.fn(),
    getBatchReconciliation: vi.fn(),
    getBatchItems: vi.fn(),
    uploadCsv: vi.fn(),
  },
}))

// Mock useI18n
vi.mock('../composables/useI18n.js', () => ({
  useI18n: () => ({
    t: (key, fallback) => fallback || key,
    dir: 'ltr',
    isRTL: false,
    locale: { value: 'en-US' },
  }),
}))

describe('MigrateView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders initial Step 1: Connect Source with source selector options', () => {
    const wrapper = mount(MigrateView)
    expect(wrapper.text()).toContain('Automated Legacy ERP Database Migration Bridge')
    expect(wrapper.text()).toContain('Direct SQL Server')
    expect(wrapper.text()).toContain('Multi-Table CSV / SQL Dump')
    expect(wrapper.text()).toContain('Single CSV Upload')
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('allows switching between SQL Server, CSV Dump, and Single CSV source types', async () => {
    const wrapper = mount(MigrateView)
    const cards = wrapper.findAll('.source-card')
    expect(cards.length).toBe(3)

    // Switch to CSV Dump
    await cards[1].trigger('click')
    expect(wrapper.text()).toContain('Dump Directory / Archive Settings')
    expect(wrapper.find('select').exists()).toBe(true)

    // Switch to Single CSV Upload
    await cards[2].trigger('click')
    expect(wrapper.text()).toContain('Upload Legacy CSV File')
    expect(wrapper.find('.upload-zone').exists()).toBe(true)
  })

  it('executes connection test and renders connection metadata badge', async () => {
    migrationApi.testConnection.mockResolvedValueOnce({
      success: true,
      message: 'Connected to SQL Server 2019 successfully',
      latency_ms: 24.5,
      server_version: 'Microsoft SQL Server 2019',
      tables_count: 5,
      tables: ['tbl_Products', 'tbl_Customers', 'tbl_Invoices', 'tbl_Stock', 'tbl_Vendors'],
    })

    const wrapper = mount(MigrateView)
    const testBtn = wrapper.find('.btn-test-conn')
    expect(testBtn.text()).toContain('Test Connection')

    await testBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.testConnection).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Connection Successful')
    expect(wrapper.text()).toContain('24.5 ms')
    expect(wrapper.text()).toContain('Microsoft SQL Server 2019')
  })

  it('executes schema discovery and advances to Step 2: Schema & Cleansing', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({
      success: true,
      tables_count: 3,
      tables: ['tbl_Products', 'tbl_Customers', 'tbl_Inventory'],
      schemas: {
        tbl_Products: {
          table_name: 'tbl_Products',
          row_count_estimate: 1500,
          column_names: ['item_code', 'item_desc', 'sale_price', 'buy_price', 'barcode_no'],
          columns: [
            { name: 'item_code', data_type: 'VARCHAR' },
            { name: 'item_desc', data_type: 'VARCHAR' },
            { name: 'sale_price', data_type: 'DECIMAL' },
          ],
        },
        tbl_Customers: {
          table_name: 'tbl_Customers',
          row_count_estimate: 420,
          column_names: ['cust_code', 'cust_name', 'phone_no', 'balance'],
          columns: [
            { name: 'cust_code', data_type: 'VARCHAR' },
            { name: 'cust_name', data_type: 'VARCHAR' },
          ],
        },
        tbl_Inventory: {
          table_name: 'tbl_Inventory',
          row_count_estimate: 1200,
          column_names: ['sku', 'warehouse', 'qty_on_hand', 'cost'],
          columns: [],
        },
      },
    })

    const wrapper = mount(MigrateView)
    const discoverBtn = wrapper.find('.step-actions .btn-primary')
    expect(discoverBtn.text()).toContain('Discover Schema & Next')

    await discoverBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.discoverSchema).toHaveBeenCalledTimes(1)
    // Should now be on Step 2
    expect(wrapper.text()).toContain('Discovered Legacy Tables')
    expect(wrapper.text()).toContain('tbl_Products')
    expect(wrapper.text()).toContain('1500 rows')
    expect(wrapper.text()).toContain('Phantom Product Detection')
  })

  it('opens table preview modal and displays sampled rows', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({
      success: true,
      schemas: {
        tbl_Products: {
          table_name: 'tbl_Products',
          row_count_estimate: 2,
          column_names: ['sku', 'name', 'price'],
        },
      },
    })
    migrationApi.previewTable.mockResolvedValueOnce({
      table_name: 'tbl_Products',
      columns: ['sku', 'name', 'price'],
      sample_rows: [
        { sku: 'PROD-001', name: 'Espresso Blend', price: 15.5 },
        { sku: 'PROD-002', name: 'Latte Cup', price: 20.0 },
      ],
    })

    const wrapper = mount(MigrateView)
    await wrapper.find('.step-actions .btn-primary').trigger('click') // discover
    await flushPromises()

    const previewBtn = wrapper.find('.btn-chip-preview')
    await previewBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.previewTable).toHaveBeenCalledWith(expect.objectContaining({
      table_name: 'tbl_Products',
      limit: 20,
    }))
    expect(wrapper.text()).toContain('Sample Preview')
    expect(wrapper.text()).toContain('Espresso Blend')
    expect(wrapper.text()).toContain('PROD-002')
  })

  it('executes dry run simulation and transitions to Step 3: Reconciliation Dashboard', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({
      success: true,
      schemas: { tbl_Products: { column_names: ['sku', 'name'] } },
    })

    migrationApi.runDryRun.mockResolvedValueOnce({
      batch_key: 'BATCH-2026-001',
      batch_id: 104,
      success: true,
      total_source_rows: 500,
      valid_rows_count: 495,
      error_rows_count: 5,
      phantom_products_count: 12,
      execution_duration_ms: 120.5,
      validation_errors: [
        { row_index: 42, entity_type: 'products', field_name: 'sku', error_type: 'missing_required', message: 'Missing SKU', severity: 'error' },
      ],
      reconciliation_summary: {
        customer_balance: {
          total_legacy_receivables: 150000,
          total_nova_receivables: 150000,
          total_receivables_delta: 0.0,
          customers_count: 50,
          matched_count: 50,
          top_variances: [],
        },
        inventory: {
          total_legacy_quantity: 8000,
          total_nova_quantity: 8000,
          total_quantity_delta: 0.0,
          total_legacy_valuation: 320000,
          total_nova_valuation: 320000,
          total_valuation_delta: 0.0,
          warehouse_summaries: {
            Main: { warehouse_name: 'Main', legacy_total_quantity: 8000, nova_total_quantity: 8000, quantity_delta: 0, legacy_total_valuation: 320000, nova_total_valuation: 320000, valuation_delta: 0 },
          },
          discrepancies: [],
        },
      },
    })

    migrationApi.getBatchReconciliation.mockResolvedValueOnce({
      batch_key: 'BATCH-2026-001',
      overall_status: 'Passed',
      customer_balance: {
        total_legacy_receivables: 150000,
        total_nova_receivables: 150000,
        total_receivables_delta: 0.0,
        customers_count: 50,
        matched_count: 50,
      },
      inventory: {
        total_legacy_quantity: 8000,
        total_nova_quantity: 8000,
        total_quantity_delta: 0.0,
        total_legacy_valuation: 320000,
        total_nova_valuation: 320000,
        total_valuation_delta: 0.0,
      },
      entity_counts: {
        products: { entity_type: 'products', source_count: 300, staged_count: 295, phantom_count: 12, error_count: 5, match_status: 'Matched' },
        customers: { entity_type: 'customers', source_count: 200, staged_count: 200, phantom_count: 0, error_count: 0, match_status: 'Matched' },
      },
      recommendations: ['All customer balances are verified and ready to commit.'],
    })

    const wrapper = mount(MigrateView)
    await wrapper.find('.step-actions .btn-primary').trigger('click') // discover
    await flushPromises()

    // Click Run Dry-Run Simulation
    const runBtn = wrapper.findAll('.btn-primary').find(b => b.text().includes('Run Dry-Run Simulation'))
    expect(runBtn).toBeDefined()
    await runBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.runDryRun).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Dry-Run Simulation Passed — Ready to Commit')
    expect(wrapper.text()).toContain('BATCH-2026-001')
    expect(wrapper.text()).toContain('Receivables Variance')
    expect(wrapper.text()).toContain('Inventory Valuation Delta')
  })

  it('navigates reconciliation dashboard tabs (Customer Balances, Inventory, Errors, Recommendations)', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({ success: true, schemas: {} })
    migrationApi.runDryRun.mockResolvedValueOnce({
      batch_id: 104,
      batch_key: 'BATCH-104',
      success: true,
      total_source_rows: 100,
      valid_rows_count: 98,
      error_rows_count: 2,
      validation_errors: [
        { row_index: 10, entity_type: 'products', field_name: 'price', error_type: 'invalid_type', message: 'Price must be numeric', severity: 'error' },
      ],
      reconciliation_summary: {
        customer_balance: {
          total_legacy_receivables: 5000,
          total_nova_receivables: 4800,
          total_receivables_delta: -200,
          customers_count: 2,
          discrepancies: [
            { customer_key: 'CUST-001', customer_name: 'Acme Corp', legacy_balance: 5000, nova_balance: 4800, delta: -200, is_matched: false },
          ],
        },
        inventory: {
          total_legacy_quantity: 100,
          total_nova_quantity: 100,
          total_quantity_delta: 0,
          discrepancies: [
            { product_key: 'P1', sku: 'SKU-01', product_name: 'Coffee', warehouse_name: 'Main', legacy_quantity: 10, nova_quantity: 10, valuation_delta: 0, status: 'OK' },
          ],
        },
      },
    })
    migrationApi.getBatchReconciliation.mockResolvedValueOnce({
      batch_key: 'BATCH-104',
      overall_status: 'PassedWithWarnings',
      customer_balance: {
        total_legacy_receivables: 5000,
        total_nova_receivables: 4800,
        total_receivables_delta: -200,
        customers_count: 2,
        discrepancies: [
          { customer_key: 'CUST-001', customer_name: 'Acme Corp', legacy_balance: 5000, nova_balance: 4800, delta: -200, is_matched: false },
        ],
      },
      inventory: {
        total_legacy_quantity: 100,
        total_nova_quantity: 100,
        total_quantity_delta: 0,
        discrepancies: [],
      },
      entity_counts: {
        products: { entity_type: 'products', source_count: 50, staged_count: 48, error_count: 2 },
      },
      recommendations: ['Review customer balance variance for Acme Corp.'],
    })

    const wrapper = mount(MigrateView)
    await wrapper.find('.step-actions .btn-primary').trigger('click') // discover
    await flushPromises()
    const runBtn = wrapper.findAll('.btn-primary').find(b => b.text().includes('Run Dry-Run Simulation'))
    await runBtn.trigger('click')
    await flushPromises()

    // 1. Customer Balances Tab shows Acme Corp discrepancy
    expect(wrapper.text()).toContain('Acme Corp')
    expect(wrapper.text()).toContain('-$200.00')

    // 2. Click Inventory Tab
    const tabs = wrapper.findAll('.tab-btn')
    await tabs[1].trigger('click')
    expect(wrapper.text()).toContain('Inventory Quantities & Valuation')

    // 3. Click Validation Errors Tab
    await tabs[3].trigger('click')
    expect(wrapper.text()).toContain('Price must be numeric')

    // 4. Click Recommendations Tab
    await tabs[4].trigger('click')
    expect(wrapper.text()).toContain('Review customer balance variance for Acme Corp.')
  })

  it('performs one-click commit and displays post-commit success screen with instant rollback option', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({ success: true, schemas: {} })
    migrationApi.runDryRun.mockResolvedValueOnce({
      batch_id: 105,
      batch_key: 'BATCH-105',
      success: true,
      total_source_rows: 300,
      valid_rows_count: 300,
      reconciliation_summary: {},
    })
    migrationApi.getBatchReconciliation.mockResolvedValueOnce({
      batch_key: 'BATCH-105',
      overall_status: 'Passed',
      entity_counts: {},
    })
    migrationApi.commitBatch.mockResolvedValueOnce({
      batch_id: 105,
      status: 'Committed',
      total_inserted: 300,
      execution_time_ms: 184.2,
      inserted_by_entity: {
        products: 150,
        customers: 50,
        inventory_opening: 100,
      },
    })

    const wrapper = mount(MigrateView)
    await wrapper.find('.step-actions .btn-primary').trigger('click') // discover
    await flushPromises()
    const runBtn = wrapper.findAll('.btn-primary').find(b => b.text().includes('Run Dry-Run Simulation'))
    await runBtn.trigger('click')
    await flushPromises()

    // Open Commit Modal
    const commitBtn = wrapper.findAll('.btn-primary').find(b => b.text().includes('Commit'))
    await commitBtn.trigger('click')
    expect(wrapper.text()).toContain('Confirm Migration Commit')

    // Confirm commit
    const modalCommitBtn = wrapper.find('.modal-actions .btn-primary')
    await modalCommitBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.commitBatch).toHaveBeenCalledWith(105, false)
    expect(wrapper.text()).toContain('Migration Committed Successfully!')
    expect(wrapper.text()).toContain('300')
    expect(wrapper.text()).toContain('products: 150')
    expect(wrapper.text()).toContain('Instant Rollback')
  })

  it('executes instant rollback cleanly and shows rollback confirmation banner', async () => {
    migrationApi.discoverSchema.mockResolvedValueOnce({ success: true, schemas: {} })
    migrationApi.runDryRun.mockResolvedValueOnce({
      batch_id: 106,
      batch_key: 'BATCH-106',
      success: true,
      total_source_rows: 100,
      valid_rows_count: 100,
      reconciliation_summary: {},
    })
    migrationApi.getBatchReconciliation.mockResolvedValueOnce({ batch_key: 'BATCH-106', overall_status: 'Passed' })
    migrationApi.commitBatch.mockResolvedValueOnce({ batch_id: 106, total_inserted: 100 })
    migrationApi.rollbackBatch.mockResolvedValueOnce({
      batch_id: 106,
      status: 'RolledBack',
      total_deleted: 100,
    })

    const wrapper = mount(MigrateView)
    await wrapper.find('.step-actions .btn-primary').trigger('click') // discover
    await flushPromises()
    const runBtn = wrapper.findAll('.btn-primary').find(b => b.text().includes('Run Dry-Run Simulation'))
    await runBtn.trigger('click')
    await flushPromises()

    // Commit
    await wrapper.findAll('.btn-primary').find(b => b.text().includes('Commit')).trigger('click')
    await wrapper.find('.modal-actions .btn-primary').trigger('click')
    await flushPromises()

    // Now on committed screen, click Instant Rollback
    const rollbackBtn = wrapper.find('.btn-danger')
    await rollbackBtn.trigger('click')
    expect(wrapper.text()).toContain('Confirm Instant Rollback')

    // Execute rollback in modal
    const confirmRollbackBtn = wrapper.find('.modal-actions .btn-danger')
    await confirmRollbackBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.rollbackBatch).toHaveBeenCalledWith(106, '')
    expect(wrapper.text()).toContain('Migration Batch Rolled Back Successfully')
    expect(wrapper.text()).toContain('100 records safely deleted')
  })

  it('loads and renders Batch History table with tracked items and rollback action', async () => {
    migrationApi.listBatches.mockResolvedValueOnce({
      items: [
        { id: 101, batch_key: 'BATCH-101', source_type: 'sqlserver', entity_type: 'Full Migration', total_rows: 1500, inserted_rows: 1500, status: 'Committed', created_at: '2026-08-25T10:00:00Z' },
        { id: 102, batch_key: 'BATCH-102', source_type: 'csv_dump', entity_type: 'Products', total_rows: 200, inserted_rows: 0, status: 'DryRunCompleted', created_at: '2026-08-25T11:00:00Z' },
      ],
    })
    migrationApi.getBatchItems.mockResolvedValueOnce([
      { id: 1, batch_id: 101, entity_type: 'products', target_table: 't0003', target_id: 42, source_key: 'LEG-100', status: 'Inserted', created_at: '2026-08-25T10:05:00Z' },
    ])

    const wrapper = mount(MigrateView)
    // Click Batch History in header
    const historyBtn = wrapper.find('.header-actions .btn-outline')
    await historyBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.listBatches).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Migration Batches & Audit Trail')
    expect(wrapper.text()).toContain('#101')
    expect(wrapper.text()).toContain('Full Migration')
    expect(wrapper.text()).toContain('Committed')

    // Open tracked items modal for batch #101
    const viewItemsBtn = wrapper.findAll('.action-btn-group .btn-icon')[1]
    await viewItemsBtn.trigger('click')
    await flushPromises()

    expect(migrationApi.getBatchItems).toHaveBeenCalledWith(101, { limit: 100 })
    expect(wrapper.text()).toContain('Tracked Items for Batch #101')
    expect(wrapper.text()).toContain('LEG-100')
    expect(wrapper.text()).toContain('t0003')
  })
})

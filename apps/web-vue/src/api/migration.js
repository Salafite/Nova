/**
 * Migration API Client Module
 *
 * Encapsulates all REST API calls for the Legacy ERP Database Connector & Migration Bridge:
 * - Connector listing, connection testing & schema discovery
 * - Table preview sampling
 * - Dry-run migration simulation & staging
 * - Opening balance & inventory reconciliation reports
 * - Atomic one-click commit & zero-downtime instant rollback
 * - Migration batch history & audit item tracking
 * - Legacy CSV upload & preview
 */

import { api } from './client.js'

/**
 * List all supported legacy database connectors and dump extractors.
 * @returns {Promise<Array<{ id: string, name: string, description: string, [key: string]: any }>>}
 */
export async function listConnectors() {
  const res = await api.get('/v1/migration/connectors')
  return res.data
}

/**
 * Test connectivity and introspect metadata from a legacy database or file dump.
 * @param {Object} payload - Connection parameters
 * @param {string} payload.source_type - Connector type (e.g., 'sqlserver', 'csv_dump')
 * @param {string} [payload.host] - Database host / server address
 * @param {number} [payload.port] - Database port
 * @param {string} [payload.database] - Database name
 * @param {string} [payload.user] - Username
 * @param {string} [payload.password] - Password
 * @param {boolean} [payload.trust_server_certificate] - Trust server SSL certificate
 * @param {string} [payload.dump_path] - Directory or file path for CSV/SQL dumps
 * @param {string} [payload.connection_string] - Direct connection string override
 * @returns {Promise<Object>} Connection test result
 */
export async function testConnection(payload) {
  const res = await api.post('/v1/migration/connectors/test', payload)
  return res.data
}

/**
 * Discover database schema, tables, columns, data types, keys, and row count estimates.
 * @param {Object} payload - Connection parameters
 * @returns {Promise<Object>} Schema discovery output with tables list and metadata
 */
export async function discoverSchema(payload) {
  const res = await api.post('/v1/migration/connectors/discover', payload)
  return res.data
}

/**
 * Fetch a sampled slice of records from a source table or file.
 * @param {Object} payload - Table preview parameters
 * @param {string} payload.source_type - Connector type
 * @param {Object} payload.connection - Connection configuration dictionary
 * @param {string} [payload.table_name] - Target source table name
 * @param {string} [payload.file_path] - Target file path (for CSV dumps)
 * @param {number} [payload.limit] - Max sample rows (default 10)
 * @param {number} [payload.offset] - Row offset
 * @param {Object} [payload.filter_conditions] - Optional filter conditions
 * @param {string} [payload.order_by] - Optional order by clause
 * @returns {Promise<Object>} Sampled rows, total row estimate, and column metadata
 */
export async function previewTable(payload) {
  const res = await api.post('/v1/migration/connectors/preview', payload)
  return res.data
}

/**
 * Execute a dry-run migration pipeline with data cleansing and safe batch staging.
 * @param {Object} payload - Dry run parameters
 * @param {string} payload.source_type - Connector type
 * @param {Object} payload.connection - Connection parameters
 * @param {Object} [payload.table_mappings] - Custom or discovered table & field mappings
 * @param {Object} [payload.cleansing_options] - Phantom product and cleansing settings
 * @param {string} [payload.batch_name] - Human-readable batch name
 * @param {string} [payload.description] - Batch description
 * @returns {Promise<Object>} Dry run simulation results, staging metrics, and reconciliation report
 */
export async function runDryRun(payload) {
  const res = await api.post('/v1/migration/dry-run', payload)
  return res.data
}

/**
 * Commit validated records from staged storage into target Nova ERP business tables.
 * @param {number|Object} batchIdOrPayload - Batch ID or payload object with batch_id and force
 * @param {boolean} [force=false] - Force commit despite warnings
 * @returns {Promise<Object>} Commit summary with inserted record counts per entity
 */
export async function commitBatch(batchIdOrPayload, force = false) {
  const payload = typeof batchIdOrPayload === 'object' && batchIdOrPayload !== null
    ? { batch_id: batchIdOrPayload.batch_id, force: batchIdOrPayload.force ?? false }
    : { batch_id: batchIdOrPayload, force }
  const res = await api.post('/v1/migration/commit', payload)
  return res.data
}

/**
 * Instantly roll back a committed or preview migration batch with zero downtime.
 * @param {number|Object} batchIdOrPayload - Batch ID or payload object with batch_id and reason
 * @param {string} [reason=null] - Reason for rollback
 * @returns {Promise<Object>} Rollback summary with deleted record counts per entity
 */
export async function rollbackBatch(batchIdOrPayload, reason = null) {
  const payload = typeof batchIdOrPayload === 'object' && batchIdOrPayload !== null
    ? { batch_id: batchIdOrPayload.batch_id, reason: batchIdOrPayload.reason ?? null }
    : { batch_id: batchIdOrPayload, reason }
  const res = await api.post('/v1/migration/rollback', payload)
  return res.data
}

/**
 * Retrieve paginated list of migration batches with optional filtering.
 * @param {Object} [params={}] - Query parameters
 * @param {number} [params.limit=50] - Number of batches to return
 * @param {number} [params.offset=0] - Offset for pagination
 * @param {string} [params.status] - Filter by status (e.g. 'Draft', 'DryRunCompleted', 'Committed', 'RolledBack')
 * @param {string} [params.source_type] - Filter by source connector type
 * @returns {Promise<Object>} List of batches and pagination metadata
 */
export async function listBatches(params = {}) {
  const res = await api.get('/v1/migration/batches', { params })
  return res.data
}

/**
 * Fetch detailed information for a single migration batch.
 * @param {number|string} batchId - Batch ID
 * @returns {Promise<Object>} Batch details and metadata
 */
export async function getBatch(batchId) {
  const res = await api.get(`/v1/migration/batches/${batchId}`)
  return res.data
}

/**
 * Retrieve comprehensive opening balance and inventory reconciliation report for a batch.
 * @param {number|string} batchId - Batch ID
 * @param {Object} [params={}] - Query parameters
 * @param {number} [params.tolerance=0.01] - Reconciliation variance tolerance threshold
 * @returns {Promise<Object>} Balance, inventory, and entity reconciliation report
 */
export async function getBatchReconciliation(batchId, params = {}) {
  const res = await api.get(`/v1/migration/batches/${batchId}/reconciliation`, { params })
  return res.data
}

/**
 * Retrieve individual record tracking items for a migration batch.
 * @param {number|string} batchId - Batch ID
 * @param {Object} [params={}] - Query parameters
 * @param {string} [params.entity_type] - Filter by entity type (e.g. 'products', 'customers')
 * @param {number} [params.limit=100] - Record limit
 * @param {number} [params.offset=0] - Record offset
 * @returns {Promise<Array<Object>>} List of migrated/tracked item records
 */
export async function getBatchItems(batchId, params = {}) {
  const res = await api.get(`/v1/migration/batches/${batchId}/items`, { params })
  return res.data
}

/**
 * Upload and stage a legacy single-entity CSV file (backward compatibility).
 * @param {File|FormData} fileOrFormData - CSV file or pre-constructed FormData
 * @param {string} [entityType='products'] - Entity type (e.g. 'products', 'customers', 'suppliers')
 * @param {Object|string} [columnMapping={}] - Column mapping dictionary or JSON string
 * @returns {Promise<Object>} Upload preview and validation summary
 */
export async function uploadCsv(fileOrFormData, entityType = 'products', columnMapping = {}) {
  let form
  if (fileOrFormData instanceof FormData) {
    form = fileOrFormData
  } else {
    form = new FormData()
    form.append('file', fileOrFormData)
    form.append('entity_type', entityType)
    form.append('column_mapping', typeof columnMapping === 'string' ? columnMapping : JSON.stringify(columnMapping))
  }

  const res = await api.post('/v1/migration/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export const migrationApi = {
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
}

export default migrationApi

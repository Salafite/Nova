<template>
  <div :dir="dir" class="edi-gateway-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('edi-gateway-title', 'B2B EDI Gateway') }}</h1>
        <p class="page-subtitle">{{ t('edi-gateway-sub', 'Electronic Data Interchange (ANSI X12 & UN/EDIFACT) Order Automation & Live Feed') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="router.push('/integrations/edi-partners')">
          <span class="material-symbols-outlined">corporate_fare</span>
          {{ t('trading-partners', 'Trading Partners') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-sku-mapping')">
          <span class="material-symbols-outlined">dataset</span>
          {{ t('sku-matrix', 'SKU Matrix') }}
        </button>
        <button class="btn-primary" @click="showIngestModal = true">
          <span class="material-symbols-outlined">file_upload</span>
          {{ t('quick-ingest', 'Ingest Document') }}
        </button>
        <button class="btn-icon" @click="loadData" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="kpi-grid mb-6">
      <div class="kpi-card">
        <div class="kpi-icon icon-purple"><span class="material-symbols-outlined">swap_horiz</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-transactions', 'Total Transacted') }}</span>
          <span class="kpi-value">{{ kpis.total }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-blue"><span class="material-symbols-outlined">shopping_cart</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('inbound-orders', 'Inbound POs (850)') }}</span>
          <span class="kpi-value">{{ kpis.inboundOrders }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-teal"><span class="material-symbols-outlined">local_shipping</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('outbound-asns', 'Outbound ASNs (856)') }}</span>
          <span class="kpi-value">{{ kpis.outboundAsns }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-green"><span class="material-symbols-outlined">receipt_long</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('outbound-invoices', 'Outbound Invoices (810)') }}</span>
          <span class="kpi-value">{{ kpis.outboundInvoices }}</span>
        </div>
      </div>
      <div class="kpi-card" :class="{ 'kpi-alert': kpis.discrepancyHolds > 0 }">
        <div class="kpi-icon icon-amber"><span class="material-symbols-outlined">warning</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('price-holds', 'Price Holds / Discrepancies') }}</span>
          <span class="kpi-value">{{ kpis.discrepancyHolds }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-indigo"><span class="material-symbols-outlined">handshake</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('active-partners', 'Active Partners') }}</span>
          <span class="kpi-value">{{ partners.length }}</span>
        </div>
      </div>
    </div>

    <!-- Quick Ingestion Banner / Action Card -->
    <div class="quick-action-card mb-6">
      <div class="quick-action-header">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">bolt</span>
          <h3 class="quick-title">{{ t('quick-edi-testing', 'Direct EDI Interchange Ingestion & Test Center') }}</h3>
        </div>
        <div class="flex gap-2">
          <button class="btn-sm btn-outline" @click="loadSample('X12_850')">
            <span class="material-symbols-outlined">description</span> Sample ANSI X12 850
          </button>
          <button class="btn-sm btn-outline" @click="loadSample('EDIFACT_ORDERS')">
            <span class="material-symbols-outlined">description</span> Sample EDIFACT ORDERS
          </button>
          <button class="btn-sm btn-outline" @click="loadSample('X12_832')">
            <span class="material-symbols-outlined">category</span> Sample 832 Catalog
          </button>
        </div>
      </div>
      <div class="quick-action-body">
        <div class="quick-controls-grid">
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('trading-partner', 'Trading Partner') }}</label>
            <select v-model="quickForm.partner_id" class="form-control form-control-sm">
              <option :value="null">{{ t('auto-detect-partner', '-- Auto-Detect from EDI Envelope --') }}</option>
              <option v-for="p in partners" :key="p.id" :value="p.id">
                {{ p.partner_code }} ({{ p.partner_name }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('edi-standard', 'Standard') }}</label>
            <select v-model="quickForm.standard" class="form-control form-control-sm">
              <option value="">{{ t('auto-detect', 'Auto-Detect') }}</option>
              <option value="ANSI_X12">ANSI X12</option>
              <option value="EDIFACT">UN/EDIFACT</option>
            </select>
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('doc-type', 'Document Type') }}</label>
            <select v-model="quickForm.document_type" class="form-control form-control-sm">
              <option value="850">850 / ORDERS (Purchase Order)</option>
              <option value="832">832 / PRICAT (Price Catalog)</option>
            </select>
          </div>
          <div class="form-group flex items-end">
            <label class="checkbox-label mb-2">
              <input type="checkbox" v-model="quickForm.auto_confirm" />
              <span>{{ t('auto-confirm', 'Auto-Confirm Sales Order') }}</span>
            </label>
          </div>
        </div>

        <div class="mt-3">
          <textarea
            v-model="quickForm.raw_payload"
            rows="4"
            class="form-control code-editor"
            :placeholder="t('paste-edi-placeholder', 'Paste raw EDI interchange (ISA...IEA or UNB...UNZ) here...')"
          ></textarea>
        </div>

        <div class="flex justify-between items-center mt-3">
          <span class="text-xs text-muted">
            {{ quickForm.raw_payload.length }} {{ t('chars', 'characters') }} |
            {{ detectedStandardLabel }}
          </span>
          <div class="flex gap-2">
            <button
              class="btn-sm btn-outline"
              @click="quickForm.raw_payload = ''"
              :disabled="!quickForm.raw_payload"
            >
              {{ t('clear', 'Clear') }}
            </button>
            <button
              class="btn-sm btn-primary"
              @click="processQuickIngest"
              :disabled="ingesting || !quickForm.raw_payload.trim()"
            >
              <span v-if="ingesting" class="spinner-sm"></span>
              <span v-else class="material-symbols-outlined">play_arrow</span>
              {{ ingesting ? t('processing', 'Processing...') : t('run-ingest', 'Ingest & Process') }}
            </button>
          </div>
        </div>

        <!-- Ingest Result Banner -->
        <div v-if="lastResult" class="ingest-result-banner mt-4" :class="resultBannerClass">
          <div class="flex justify-between items-start">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined">{{ resultBannerIcon }}</span>
              <div>
                <strong>{{ lastResult.transaction_number || t('processed', 'Processed') }}</strong> —
                <span class="badge" :class="statusBadge(lastResult.status)">{{ lastResult.status }}</span>
                <span v-if="lastResult.sales_order_number" class="ml-2 font-medium">
                  → {{ t('sales-order', 'Sales Order') }}: <a class="link-bold" @click="goToSalesOrder(lastResult.sales_order_id)">{{ lastResult.sales_order_number }}</a>
                </span>
              </div>
            </div>
            <button class="btn-icon btn-sm" @click="lastResult = null"><span class="material-symbols-outlined">close</span></button>
          </div>

          <div v-if="lastResult.discrepancies && lastResult.discrepancies.length" class="discrepancies-box mt-3">
            <h5 class="text-xs font-bold text-amber-800">{{ t('discrepancies-detected', 'Price Discrepancies Detected:') }}</h5>
            <ul class="text-xs space-y-1 mt-1">
              <li v-for="(disc, idx) in lastResult.discrepancies" :key="idx">
                Line #{{ disc.line_number }} ({{ disc.partner_sku }}): Ordered ${{ (disc.ordered_price || 0).toFixed(2) }} vs Contract ${{ (disc.expected_price || 0).toFixed(2) }} (Variance: {{ disc.discrepancy_percent?.toFixed(1) }}%)
              </li>
            </ul>
          </div>

          <div v-if="lastResult.errors && lastResult.errors.length" class="errors-box mt-3">
            <h5 class="text-xs font-bold text-red-800">{{ t('errors-noted', 'Processing Errors:') }}</h5>
            <ul class="text-xs space-y-1 mt-1">
              <li v-for="(err, idx) in lastResult.errors" :key="idx">{{ err }}</li>
            </ul>
          </div>

          <div v-if="lastResult.ack_payload" class="ack-preview mt-2">
            <span class="text-xs font-semibold text-muted">{{ t('ack-generated', 'Functional ACK (997/CONTRL):') }}</span>
            <pre class="ack-code">{{ lastResult.ack_payload }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Live Transaction Feed & Filter Section -->
    <div class="data-card">
      <div class="card-filter-bar">
        <div class="search-wrap">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('search-transactions', 'Search by Transaction #, Control #, PO #...')"
          />
        </div>

        <div class="filters-wrap">
          <select v-model="filterDirection" class="filter-select">
            <option value="">{{ t('all-directions', 'All Directions') }}</option>
            <option value="INBOUND">{{ t('inbound', 'Inbound (↓)') }}</option>
            <option value="OUTBOUND">{{ t('outbound', 'Outbound (↑)') }}</option>
          </select>

          <select v-model="filterDocType" class="filter-select">
            <option value="">{{ t('all-doc-types', 'All Document Types') }}</option>
            <option value="850">850 / ORDERS (PO)</option>
            <option value="856">856 / DESADV (ASN)</option>
            <option value="810">810 / INVOIC (Invoice)</option>
            <option value="832">832 / PRICAT (Catalog)</option>
            <option value="997">997 / CONTRL (ACK)</option>
          </select>

          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="PRICE_DISCREPANCY_HOLD">PRICE_DISCREPANCY_HOLD</option>
            <option value="FAILED">FAILED</option>
            <option value="PENDING">PENDING</option>
          </select>

          <select v-model="filterPartner" class="filter-select">
            <option value="">{{ t('all-partners', 'All Partners') }}</option>
            <option v-for="p in partners" :key="p.id" :value="p.id">{{ p.partner_code }}</option>
          </select>
        </div>
      </div>

      <SkeletonTable v-if="loading" />
      <ErrorState v-else-if="error" :message="error" @retry="loadData" />

      <div v-else-if="!filteredTransactions.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">receipt</span>
        <p>{{ t('no-edi-transactions', 'No EDI transactions found.') }}</p>
        <button class="btn-primary" @click="showIngestModal = true">{{ t('ingest-first-doc', 'Ingest Document') }}</button>
      </div>

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('direction', 'Dir') }}</th>
              <th>{{ t('transaction-no', 'Transaction #') }}</th>
              <th>{{ t('doc-type', 'Doc Type') }}</th>
              <th>{{ t('standard', 'Standard') }}</th>
              <th>{{ t('trading-partner', 'Partner') }}</th>
              <th>{{ t('control-no', 'Control #') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th>{{ t('related-record', 'Linked Record') }}</th>
              <th>{{ t('ack', 'ACK') }}</th>
              <th>{{ t('date-time', 'Date / Time') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in filteredTransactions" :key="tx.id">
              <td>
                <span
                  class="direction-pill"
                  :class="tx.direction === 'INBOUND' ? 'dir-in' : 'dir-out'"
                  :title="tx.direction"
                >
                  {{ tx.direction === 'INBOUND' ? '↓ IN' : '↑ OUT' }}
                </span>
              </td>
              <td>
                <strong class="text-primary cursor-pointer" @click="viewTransactionDetails(tx)">
                  {{ tx.transaction_number }}
                </strong>
              </td>
              <td>
                <span class="badge badge-doc">{{ tx.document_type }}</span>
              </td>
              <td>
                <span class="text-xs font-semibold" :class="tx.standard === 'EDIFACT' ? 'text-blue-600' : 'text-purple-600'">
                  {{ tx.standard }}
                </span>
              </td>
              <td>
                <span class="font-medium">{{ getPartnerCode(tx.partner_id) }}</span>
              </td>
              <td class="font-mono text-xs">{{ tx.control_number || '-' }}</td>
              <td class="text-center">
                <span class="badge" :class="statusBadge(tx.status)">
                  {{ tx.status }}
                </span>
              </td>
              <td>
                <div v-if="tx.sales_order_id" class="linked-link">
                  <span class="text-xs text-muted">SO:</span>
                  <a class="link-bold" @click="router.push(`/sales/${tx.sales_order_id}`)">#{{ tx.sales_order_id }}</a>
                </div>
                <div v-else-if="tx.delivery_id" class="linked-link">
                  <span class="text-xs text-muted">Delivery:</span>
                  <a class="link-bold" @click="router.push(`/sales/deliveries`)">#{{ tx.delivery_id }}</a>
                </div>
                <div v-else-if="tx.invoice_id" class="linked-link">
                  <span class="text-xs text-muted">Invoice:</span>
                  <a class="link-bold" @click="router.push(`/finance/${tx.invoice_id}`)">#{{ tx.invoice_id }}</a>
                </div>
                <span v-else class="text-muted text-xs">-</span>
              </td>
              <td>
                <span
                  v-if="tx.ack_status"
                  class="badge-xs"
                  :class="ackBadge(tx.ack_status)"
                >
                  {{ tx.ack_status }}
                </span>
                <span v-else class="text-muted text-xs">-</span>
              </td>
              <td class="text-xs">{{ formatDate(tx.created_at || tx.processed_at) }}</td>
              <td class="text-center">
                <div class="flex justify-center gap-1">
                  <button
                    class="btn-icon btn-sm"
                    @click="viewTransactionDetails(tx)"
                    :title="t('inspect-payload', 'Inspect Raw EDI / ACK')"
                  >
                    <span class="material-symbols-outlined">visibility</span>
                  </button>
                  <button
                    v-if="tx.status === 'PRICE_DISCREPANCY_HOLD' || tx.status === 'FAILED'"
                    class="btn-icon btn-sm btn-icon-warn"
                    @click="openReprocess(tx)"
                    :title="t('reprocess', 'Reprocess Transaction')"
                  >
                    <span class="material-symbols-outlined">restart_alt</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal 1: Quick Ingest / Upload File Modal -->
    <div v-if="showIngestModal" class="modal-overlay" @click.self="showIngestModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">cloud_upload</span>
            <h3>{{ t('ingest-edi-modal-title', 'Ingest EDI Interchange Document') }}</h3>
          </div>
          <button class="btn-icon" @click="showIngestModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="tabs mb-4">
            <button
              class="tab-btn"
              :class="{ active: ingestTab === 'file' }"
              @click="ingestTab = 'file'"
            >
              <span class="material-symbols-outlined">upload_file</span> {{ t('upload-file', 'File Upload (.edi / .x12 / .txt)') }}
            </button>
            <button
              class="tab-btn"
              :class="{ active: ingestTab === 'text' }"
              @click="ingestTab = 'text'"
            >
              <span class="material-symbols-outlined">edit_note</span> {{ t('raw-text', 'Paste EDI Text') }}
            </button>
          </div>

          <div v-if="ingestTab === 'file'" class="file-dropzone mb-4" @dragover.prevent @drop.prevent="handleFileDrop">
            <input type="file" ref="fileInput" @change="handleFileSelect" accept=".edi,.x12,.txt" class="hidden-input" />
            <div class="dropzone-content" @click="$refs.fileInput.click()">
              <span class="material-symbols-outlined drop-icon">upload_file</span>
              <p v-if="!selectedFile" class="font-medium text-sm">{{ t('drag-drop-click', 'Click or drag & drop EDI file here') }}</p>
              <p v-else class="font-bold text-primary text-sm">{{ selectedFile.name }} ({{ (selectedFile.size / 1024).toFixed(1) }} KB)</p>
              <span class="text-xs text-muted">Supports ANSI X12 (.x12, .edi) & UN/EDIFACT (.edi, .txt)</span>
            </div>
          </div>

          <div v-else class="mb-4">
            <label class="form-label">{{ t('edi-payload', 'Raw EDI Payload') }} <span class="required">*</span></label>
            <textarea
              v-model="modalRawPayload"
              rows="7"
              class="form-control code-editor"
              placeholder="ISA*00*          *00*          *01*006945855     *ZZ*NOVADISTRIB   *260908*1200*U*00401*000000101*0*P*>~..."
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">{{ t('trading-partner', 'Trading Partner') }}</label>
              <select v-model="modalPartnerId" class="form-control">
                <option :value="null">{{ t('auto-detect', '-- Auto-Detect from Envelope --') }}</option>
                <option v-for="p in partners" :key="p.id" :value="p.id">
                  {{ p.partner_code }} — {{ p.partner_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('standard', 'EDI Standard') }}</label>
              <select v-model="modalStandard" class="form-control">
                <option value="">{{ t('auto-detect', 'Auto-Detect') }}</option>
                <option value="ANSI_X12">ANSI X12</option>
                <option value="EDIFACT">UN/EDIFACT</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">{{ t('doc-type', 'Document Type') }}</label>
              <select v-model="modalDocType" class="form-control">
                <option value="850">850 / ORDERS (Purchase Order)</option>
                <option value="832">832 / PRICAT (Price Catalog)</option>
              </select>
            </div>
            <div class="form-group flex items-end">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="modalAutoConfirm" />
                <span>{{ t('auto-confirm-order', 'Auto-Confirm Sales Order (Bypass Draft)') }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="showIngestModal = false">{{ t('cancel', 'Cancel') }}</button>
          <button
            class="btn-primary"
            @click="submitModalIngest"
            :disabled="modalIngesting || (ingestTab === 'file' && !selectedFile) || (ingestTab === 'text' && !modalRawPayload.trim())"
          >
            <span v-if="modalIngesting" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">send</span>
            {{ modalIngesting ? t('processing', 'Processing...') : t('ingest-document', 'Ingest & Create Orders') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 2: Payload & Functional ACK Inspector Modal -->
    <div v-if="inspectorTx" class="modal-overlay" @click.self="inspectorTx = null">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <div>
            <div class="flex items-center gap-2">
              <span class="badge" :class="statusBadge(inspectorTx.status)">{{ inspectorTx.status }}</span>
              <h3 class="modal-title">{{ inspectorTx.transaction_number }}</h3>
            </div>
            <p class="text-xs text-muted mt-1">
              {{ inspectorTx.standard }} {{ inspectorTx.document_type }} |
              {{ inspectorTx.direction }} |
              Control #: {{ inspectorTx.control_number || '-' }} |
              Partner: {{ getPartnerCode(inspectorTx.partner_id) }}
            </p>
          </div>
          <button class="btn-icon" @click="inspectorTx = null"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="tabs mb-4">
            <button class="tab-btn" :class="{ active: inspectTab === 'raw' }" @click="inspectTab = 'raw'">
              <span class="material-symbols-outlined">code</span> {{ t('raw-payload', 'Raw EDI Payload') }}
            </button>
            <button class="tab-btn" :class="{ active: inspectTab === 'parsed' }" @click="inspectTab = 'parsed'">
              <span class="material-symbols-outlined">data_object</span> {{ t('parsed-json', 'Parsed JSON Structure') }}
            </button>
            <button class="tab-btn" :class="{ active: inspectTab === 'ack' }" @click="inspectTab = 'ack'">
              <span class="material-symbols-outlined">fact_check</span> {{ t('ack-message', 'Functional ACK (997/CONTRL)') }}
            </button>
            <button v-if="inspectorTx.error_details" class="tab-btn text-amber-600" :class="{ active: inspectTab === 'errors' }" @click="inspectTab = 'errors'">
              <span class="material-symbols-outlined">error</span> {{ t('errors-holds', 'Errors & Holds') }}
            </button>
          </div>

          <!-- Raw EDI tab -->
          <div v-if="inspectTab === 'raw'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-semibold text-muted">{{ t('edi-stream', 'EDI Segment Stream') }}</span>
              <button class="btn-sm btn-outline" @click="copyToClipboard(inspectorTx.raw_payload)">
                <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy') }}
              </button>
            </div>
            <pre class="code-viewer">{{ inspectorTx.raw_payload || 'No raw payload stored' }}</pre>
          </div>

          <!-- Parsed JSON tab -->
          <div v-if="inspectTab === 'parsed'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-semibold text-muted">{{ t('parsed-document-tree', 'Extracted Document Structure') }}</span>
              <button class="btn-sm btn-outline" @click="copyToClipboard(JSON.stringify(inspectorTx.parsed_data, null, 2))">
                <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy JSON') }}
              </button>
            </div>
            <pre class="code-viewer">{{ JSON.stringify(inspectorTx.parsed_data || {}, null, 2) }}</pre>
          </div>

          <!-- ACK tab -->
          <div v-if="inspectTab === 'ack'" class="inspector-tab-content">
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-muted">{{ t('ack-status-label', 'ACK Status:') }}</span>
                <span class="badge" :class="ackBadge(inspectorTx.ack_status)">{{ inspectorTx.ack_status || 'NONE' }}</span>
              </div>
              <button v-if="inspectorTx.ack_payload" class="btn-sm btn-outline" @click="copyToClipboard(inspectorTx.ack_payload)">
                <span class="material-symbols-outlined">content_copy</span> {{ t('copy', 'Copy') }}
              </button>
            </div>
            <pre class="code-viewer">{{ inspectorTx.ack_payload || 'No functional acknowledgment payload recorded.' }}</pre>
          </div>

          <!-- Errors & Holds tab -->
          <div v-if="inspectTab === 'errors'" class="inspector-tab-content">
            <div class="alert-box-warning mb-3">
              <span class="material-symbols-outlined">warning</span>
              <div>
                <strong>{{ t('discrepancy-notice', 'Order held or failed during ingestion') }}</strong>
                <p class="text-xs mt-1">{{ inspectorTx.error_details }}</p>
              </div>
            </div>
            <button class="btn-primary btn-sm" @click="openReprocess(inspectorTx)">
              <span class="material-symbols-outlined">restart_alt</span> {{ t('reprocess-now', 'Reprocess / Force Confirm') }}
            </button>
          </div>
        </div>
        <div class="modal-footer">
          <button
            v-if="inspectorTx.status === 'PRICE_DISCREPANCY_HOLD' || inspectorTx.status === 'FAILED'"
            class="btn-outline text-amber-700"
            @click="openReprocess(inspectorTx)"
          >
            <span class="material-symbols-outlined">restart_alt</span> {{ t('reprocess', 'Reprocess') }}
          </button>
          <button class="btn-primary" @click="inspectorTx = null">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>

    <!-- Modal 3: Reprocess Transaction Modal -->
    <div v-if="reprocessTarget" class="modal-overlay" @click.self="reprocessTarget = null">
      <div class="modal-content">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-amber-600">restart_alt</span>
            <h3>{{ t('reprocess-title', 'Reprocess EDI Transaction') }}</h3>
          </div>
          <button class="btn-icon" @click="reprocessTarget = null"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-muted mb-4">
            {{ t('reprocess-desc', 'Re-evaluate cross-referencing and sales order generation for') }}
            <strong>{{ reprocessTarget.transaction_number }}</strong>.
          </p>

          <div class="form-group mb-4">
            <label class="checkbox-label font-medium">
              <input type="checkbox" v-model="reprocessForm.force_confirm" />
              <span>{{ t('force-confirm-override', 'Force Confirm (Bypass Price Discrepancy Holds)') }}</span>
            </label>
            <span class="text-xs text-muted block mt-1">
              Creates sales order in Confirmed status even if buyer price deviates beyond partner threshold.
            </span>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('override-price-tol', 'Override Price Discrepancy Tolerance (%)') }}</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              v-model.number="reprocessForm.override_price_tolerance"
              class="form-control"
              placeholder="e.g. 5.0"
            />
            <span class="text-xs text-muted block mt-1">
              Leave blank to use trading partner's configured tolerance percentage.
            </span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="reprocessTarget = null">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="executeReprocess" :disabled="reprocessing">
            <span v-if="reprocessing" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">play_arrow</span>
            {{ reprocessing ? t('reprocessing', 'Reprocessing...') : t('execute-reprocess', 'Execute Reprocess') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// State
const loading = ref(true)
const error = ref('')
const transactions = ref([])
const partners = ref([])

// Filters
const searchQuery = ref('')
const filterDirection = ref('')
const filterDocType = ref('')
const filterStatus = ref('')
const filterPartner = ref('')

// Quick Ingest Form
const quickForm = ref({
  partner_id: null,
  standard: '',
  document_type: '850',
  auto_confirm: true,
  raw_payload: '',
})
const ingesting = ref(false)
const lastResult = ref(null)

// Ingest Modal Form
const showIngestModal = ref(false)
const ingestTab = ref('file')
const selectedFile = ref(null)
const modalRawPayload = ref('')
const modalPartnerId = ref(null)
const modalStandard = ref('')
const modalDocType = ref('850')
const modalAutoConfirm = ref(true)
const modalIngesting = ref(false)

// Inspector Modal
const inspectorTx = ref(null)
const inspectTab = ref('raw')

// Reprocess Modal
const reprocessTarget = ref(null)
const reprocessForm = ref({
  force_confirm: true,
  override_price_tolerance: null,
})
const reprocessing = ref(false)

// Computed KPIs
const kpis = computed(() => {
  const total = transactions.value.length
  let inboundOrders = 0
  let outboundAsns = 0
  let outboundInvoices = 0
  let discrepancyHolds = 0

  for (const tx of transactions.value) {
    const doc = (tx.document_type || '').toUpperCase()
    const status = (tx.status || '').toUpperCase()
    if (doc === '850' || doc === 'ORDERS') inboundOrders++
    if (doc === '856' || doc === 'DESADV') outboundAsns++
    if (doc === '810' || doc === 'INVOIC') outboundInvoices++
    if (status === 'PRICE_DISCREPANCY_HOLD') discrepancyHolds++
  }

  return { total, inboundOrders, outboundAsns, outboundInvoices, discrepancyHolds }
})

// Detected Standard Label
const detectedStandardLabel = computed(() => {
  const p = quickForm.value.raw_payload.trim()
  if (!p) return 'No input'
  if (p.startsWith('ISA') || p.includes('GS*')) return 'Detected: ANSI X12'
  if (p.startsWith('UNB') || p.startsWith('UNA') || p.includes('UNH+')) return 'Detected: UN/EDIFACT'
  return 'Standard: Unknown'
})

// Filtered Transactions
const filteredTransactions = computed(() => {
  return transactions.value.filter(tx => {
    if (filterDirection.value && tx.direction !== filterDirection.value) return false
    if (filterDocType.value && tx.document_type !== filterDocType.value) return false
    if (filterStatus.value && tx.status !== filterStatus.value) return false
    if (filterPartner.value && String(tx.partner_id) !== String(filterPartner.value)) return false

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const txn = (tx.transaction_number || '').toLowerCase()
      const ctrl = (tx.control_number || '').toLowerCase()
      const doc = (tx.document_type || '').toLowerCase()
      const std = (tx.standard || '').toLowerCase()
      return txn.includes(q) || ctrl.includes(q) || doc.includes(q) || std.includes(q)
    }
    return true
  })
})

// Result Banner Styling
const resultBannerClass = computed(() => {
  if (!lastResult.value) return ''
  const s = lastResult.value.status
  if (s === 'PROCESSED' || s === 'CONFIRMED' || s === 'SYNCED') return 'banner-success'
  if (s === 'PRICE_DISCREPANCY_HOLD') return 'banner-warning'
  return 'banner-danger'
})

const resultBannerIcon = computed(() => {
  if (!lastResult.value) return 'info'
  const s = lastResult.value.status
  if (s === 'PROCESSED' || s === 'CONFIRMED' || s === 'SYNCED') return 'check_circle'
  if (s === 'PRICE_DISCREPANCY_HOLD') return 'warning'
  return 'error'
})

// Helper Functions
function formatDate(d) {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleString()
  } catch {
    return d
  }
}

function getPartnerCode(partnerId) {
  if (!partnerId) return 'GLOBAL / UNKNOWN'
  const found = partners.value.find(p => p.id === partnerId)
  return found ? found.partner_code : `Partner #${partnerId}`
}

function statusBadge(status) {
  const s = (status || '').toUpperCase()
  if (s === 'PROCESSED' || s === 'CONFIRMED' || s === 'SYNCED' || s === 'DISPATCHED' || s === 'DELIVERED') return 'badge-success'
  if (s === 'PRICE_DISCREPANCY_HOLD' || s === 'PENDING') return 'badge-warning'
  if (s === 'FAILED' || s === 'REJECTED') return 'badge-danger'
  return 'badge-disabled'
}

function ackBadge(ack) {
  const a = (ack || '').toUpperCase()
  if (a === 'ACCEPTED' || a === 'A') return 'badge-success'
  if (a === 'ACCEPTED_WITH_ERRORS' || a === 'E' || a === 'P') return 'badge-warning'
  if (a === 'REJECTED' || a === 'R') return 'badge-danger'
  return 'badge-disabled'
}

function goToSalesOrder(soId) {
  if (soId) router.push(`/sales/${soId}`)
}

async function copyToClipboard(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    toast(t('copied-clipboard', 'Copied to clipboard'), 'success')
  } catch {
    toast('Failed to copy', 'error')
  }
}

// Data Loading
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [txRes, ptRes] = await Promise.all([
      api.get('/T0126I/?limit=100'),
      api.get('/T0124I/?limit=100')
    ])
    transactions.value = Array.isArray(txRes.data) ? txRes.data : (txRes.data?.items || [])
    partners.value = Array.isArray(ptRes.data) ? ptRes.data : (ptRes.data?.items || [])
  } catch (err) {
    console.error('Failed to load EDI data:', err)
    error.value = t('failed-load', 'Failed to load EDI transactions')
  } finally {
    loading.value = false
  }
}

// Quick Ingest Handler
async function processQuickIngest() {
  if (!quickForm.value.raw_payload.trim()) {
    toast(t('payload-required', 'EDI Payload is required'), 'error')
    return
  }

  ingesting.value = true
  try {
    const res = await api.post('/edi/ingest', {
      partner_id: quickForm.value.partner_id || null,
      raw_payload: quickForm.value.raw_payload.trim(),
      standard: quickForm.value.standard || null,
      document_type: quickForm.value.document_type || '850',
      auto_confirm: quickForm.value.auto_confirm,
    })
    lastResult.value = res.data
    toast(t('edi-ingest-success', 'EDI document ingested successfully'), 'success')
    await loadData()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    toast(t('ingest-failed', `Ingestion failed: ${detail}`), 'error')
  } finally {
    ingesting.value = false
  }
}

// File Drop / Select Handlers
function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) selectedFile.value = file
}

function handleFileDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file) selectedFile.value = file
}

async function submitModalIngest() {
  modalIngesting.value = true
  try {
    if (ingestTab.value === 'file' && selectedFile.value) {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      if (modalPartnerId.value) formData.append('partner_id', modalPartnerId.value)
      if (modalStandard.value) formData.append('standard', modalStandard.value)
      if (modalDocType.value) formData.append('document_type', modalDocType.value)
      formData.append('auto_confirm', modalAutoConfirm.value ? 'true' : 'false')

      const res = await api.post('/edi/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      lastResult.value = res.data
      toast(t('upload-success', 'EDI File uploaded and processed'), 'success')
    } else {
      const res = await api.post('/edi/ingest', {
        partner_id: modalPartnerId.value || null,
        raw_payload: modalRawPayload.value.trim(),
        standard: modalStandard.value || null,
        document_type: modalDocType.value || '850',
        auto_confirm: modalAutoConfirm.value,
      })
      lastResult.value = res.data
      toast(t('ingest-success', 'EDI payload processed'), 'success')
    }
    showIngestModal.value = false
    selectedFile.value = null
    modalRawPayload.value = ''
    await loadData()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    toast(t('ingest-failed', `Processing failed: ${detail}`), 'error')
  } finally {
    modalIngesting.value = false
  }
}

// Inspector Action
function viewTransactionDetails(tx) {
  inspectorTx.value = tx
  inspectTab.value = 'raw'
}

// Reprocess Actions
function openReprocess(tx) {
  reprocessTarget.value = tx
  reprocessForm.value = {
    force_confirm: true,
    override_price_tolerance: null,
  }
}

async function executeReprocess() {
  if (!reprocessTarget.value) return
  reprocessing.value = true
  try {
    const res = await api.post(`/edi/transactions/${reprocessTarget.value.id}/reprocess`, {
      transaction_id: reprocessTarget.value.id,
      force_confirm: reprocessForm.value.force_confirm,
      override_price_tolerance: reprocessForm.value.override_price_tolerance || null,
    })
    toast(t('reprocess-success', 'Transaction reprocessed successfully'), 'success')
    lastResult.value = res.data
    reprocessTarget.value = null
    if (inspectorTx.value) inspectorTx.value = null
    await loadData()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    toast(t('reprocess-error', `Reprocess error: ${detail}`), 'error')
  } finally {
    reprocessing.value = false
  }
}

// Sample Payloads Loader
function loadSample(type) {
  if (type === 'X12_850') {
    quickForm.value.partner_id = null
    quickForm.value.standard = 'ANSI_X12'
    quickForm.value.document_type = '850'
    quickForm.value.raw_payload = [
      'ISA*00*          *00*          *01*006945855     *ZZ*NOVADISTRIB   *260908*1200*U*00401*000000101*0*P*>~',
      'GS*PO*006945855*NOVADISTRIB*20260908*1200*101*X*004010~',
      'ST*850*0001~',
      'BEG*00*SA*PO-CRF-98231**20260908~',
      'CUR*BY*USD~',
      'DTM*002*20260912~',
      'N1*BY*CARREFOUR HYPERMARKET*9*0069458550001~',
      'N1*ST*CARREFOUR MALL OF EMIRATES*9*0069458550002~',
      'PO1*1*100*EA*15.50*PE*CB*CRF-ORG-OIL*BP*061414100001*VN*INTERNAL-01~',
      'PID*F****ORGANIC EXTRA VIRGIN OLIVE OIL 1L~',
      'PO1*2*50*CS*45.00*PE*CB*CRF-BASMATI*BP*061414100002*VN*INTERNAL-02~',
      'PID*F****PREMIUM BASMATI RICE 5KG BAG~',
      'CTT*2~',
      'SE*12*0001~',
      'GE*1*101~',
      'IEA*1*000000101~'
    ].join('\n')
  } else if (type === 'EDIFACT_ORDERS') {
    quickForm.value.partner_id = null
    quickForm.value.standard = 'EDIFACT'
    quickForm.value.document_type = '850'
    quickForm.value.raw_payload = [
      "UNA:+.? '",
      "UNB+UNOC:3+5412345000013:14+NOVA:ZZ+260908:1200+10001+++++1'",
      "UNH+0001+ORDERS:D:96A:UN:EAN008'",
      "BGM+220+LULU-PO-77412+9'",
      "DTM+137:20260908:102'",
      "DTM+2:20260915:102'",
      "NAD+BY+6291041000012::9++LULU HYPERMARKET LLC'",
      "NAD+DP+6291041000029::9++LULU REGIONAL DC AL QUOZ'",
      "LIN+1++6291041000101:SRV'",
      "PIA+1+LULU-SKU-101:IN'",
      "IMD+F++:::SUNFLOWER COOKING OIL 1.5L'",
      "QTY+21:200:PCE'",
      "PRI+AAA:12.50:::NTP'",
      "LIN+2++6291041000202:SRV'",
      "PIA+1+LULU-SKU-202:IN'",
      "IMD+F++:::WHITE CRYSTAL SUGAR 2KG'",
      "QTY+21:150:PCE'",
      "PRI+AAA:8.75:::NTP'",
      "UNS+S'",
      "CNT+2:2'",
      "UNT+19+0001'",
      "UNZ+1+10001'"
    ].join('\n')
  } else if (type === 'X12_832') {
    quickForm.value.partner_id = null
    quickForm.value.standard = 'ANSI_X12'
    quickForm.value.document_type = '832'
    quickForm.value.raw_payload = [
      'ISA*00*          *00*          *01*006945855     *ZZ*NOVADISTRIB   *260908*1200*U*00401*000000201*0*P*>~',
      'GS*SC*006945855*NOVADISTRIB*20260908*1200*201*X*004010~',
      'ST*832*0001~',
      'BCT*PR*CAT-2026-Q3**20260908~',
      'CUR*BY*USD~',
      'LIN*1*UP*061414100001*VP*OIL-EV-01~',
      'PID*F****EXTRA VIRGIN OLIVE OIL 1L~',
      'CTP*WS*RES*15.50*1*EA~',
      'PO4*12*1.2*KG*0.015*CR~',
      'LIN*2*UP*061414100002*VP*RICE-BAS-05~',
      'PID*F****PREMIUM BASMATI RICE 5KG~',
      'CTP*WS*RES*45.00*1*CS~',
      'PO4*4*5.0*KG*0.04*CR~',
      'CTT*2~',
      'SE*12*0001~',
      'GE*1*201~',
      'IEA*1*000000201~'
    ].join('\n')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.edi-gateway-view {
  padding-bottom: 32px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}
.page-subtitle {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.kpi-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.kpi-alert {
  border-color: #ffb74d;
  background: #fffdf8;
}
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-purple { background: #ede7f6; color: #5d3fd3; }
.icon-blue { background: #e3f2fd; color: #1976d2; }
.icon-teal { background: #e0f2f1; color: #00796b; }
.icon-green { background: #e8f5e9; color: #2e7d32; }
.icon-amber { background: #fff3e0; color: #f57c00; }
.icon-indigo { background: #e8eaf6; color: #3949ab; }
.kpi-info {
  display: flex;
  flex-direction: column;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #777;
  text-transform: uppercase;
}
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-top: 2px;
}

/* Quick Action Card */
.quick-action-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
.quick-action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.quick-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}
.quick-controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

/* Code Editor / Viewer */
.code-editor {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.4;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px;
  width: 100%;
  resize: vertical;
  color: #0f172a;
}
.code-viewer {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  background: #0f172a;
  color: #f1f5f9;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  max-height: 400px;
}

/* Banners */
.ingest-result-banner {
  padding: 14px;
  border-radius: 8px;
  font-size: 13px;
}
.banner-success { background: #e8f5e9; border: 1px solid #a5d6a7; color: #1b5e20; }
.banner-warning { background: #fff8e1; border: 1px solid #ffe082; color: #f57f17; }
.banner-danger { background: #ffebee; border: 1px solid #ffcdd2; color: #b71c1c; }
.discrepancies-box {
  background: #fffdf5;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #fef08a;
}
.errors-box {
  background: #fff5f5;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #fecaca;
}
.ack-code {
  font-family: monospace;
  font-size: 11px;
  background: rgba(0,0,0,0.05);
  padding: 6px 10px;
  border-radius: 4px;
  margin-top: 4px;
}

/* Data Table Card */
.data-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
}
.card-filter-bar {
  padding: 14px 20px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  min-width: 280px;
  flex: 1;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: #999;
}
.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.filters-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-select {
  padding: 7px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 12px;
  background: #fff;
  color: #444;
}

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  text-align: left;
  white-space: nowrap;
}
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
  color: #333;
}
.data-table tr:hover td { background: #fbfbfe; }

/* Badges & Pills */
.direction-pill {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
}
.dir-in { background: #e0f2fe; color: #0284c7; }
.dir-out { background: #f3e8ff; color: #9333ea; }
.badge { display: inline-block; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; }
.badge-xs { display: inline-block; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 600; }
.badge-doc { background: #f1f5f9; color: #475569; font-family: monospace; font-weight: 700; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #ef6c00; }
.badge-danger { background: #ffebee; color: #c62828; }
.badge-disabled { background: #f1f5f9; color: #94a3b8; }

/* Buttons & Inputs */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #5d3fd3;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #fff;
  color: #4b5563;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.btn-sm { padding: 5px 10px; font-size: 12px; }
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: #666;
}
.btn-icon:hover { background: #f0f0f4; }
.btn-icon-warn { color: #f59e0b; }
.btn-icon-warn:hover { background: #fef3c7; }

/* Dropzone & Modals */
.file-dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  background: #f8fafc;
  transition: border-color 0.2s;
}
.file-dropzone:hover { border-color: #5d3fd3; }
.drop-icon { font-size: 40px; color: #94a3b8; margin-bottom: 8px; }
.hidden-input { display: none; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: #fff;
  border-radius: 14px;
  width: 90%;
  max-width: 580px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}
.modal-lg { max-width: 740px; }
.modal-xl { max-width: 920px; }
.modal-header {
  padding: 16px 22px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-body { padding: 20px 22px; overflow-y: auto; flex: 1; }
.modal-footer {
  padding: 14px 22px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: #fafafa;
}

/* Tabs */
.tabs { display: flex; gap: 4px; border-bottom: 1px solid #e2e8f0; padding-bottom: 2px; }
.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: none;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
}
.tab-btn.active {
  color: #5d3fd3;
  border-bottom: 2px solid #5d3fd3;
  background: #f5f3ff;
}

/* Form Styles */
.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.form-control-sm { padding: 6px 10px; font-size: 12px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.link-bold { color: #5d3fd3; font-weight: 600; cursor: pointer; text-decoration: underline; }
.link-bold:hover { color: #432b9e; }
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }
.alert-box-warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  gap: 10px;
  color: #92400e;
}
</style>

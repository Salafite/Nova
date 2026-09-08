<template>
  <div :dir="dir" class="edi-sku-mapping-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('edi-sku-matrix-title', 'EDI SKU Cross-Reference Matrix') }}</h1>
        <p class="page-subtitle">{{ t('edi-sku-matrix-sub', 'Map Supermarket & B2B Buyer Part Numbers, GTIN/EAN Barcodes, UOM Multipliers & Reference Prices (T0125)') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="router.push('/integrations/edi-gateway')">
          <span class="material-symbols-outlined">hub</span>
          {{ t('edi-gateway', 'EDI Gateway') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-partners')">
          <span class="material-symbols-outlined">corporate_fare</span>
          {{ t('trading-partners', 'Trading Partners') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-pallet-sscc')">
          <span class="material-symbols-outlined">inventory_2</span>
          {{ t('sscc-pallets', 'SSCC Pallets') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-transactions')">
          <span class="material-symbols-outlined">receipt_long</span>
          {{ t('edi-transactions', 'Transactions') }}
        </button>
        <button class="btn-outline" @click="showTester = !showTester">
          <span class="material-symbols-outlined">{{ showTester ? 'visibility_off' : 'troubleshoot' }}</span>
          {{ showTester ? t('hide-tester', 'Hide Tester') : t('live-tester', 'Live SKU Tester') }}
        </button>
        <button class="btn-outline" @click="openBulkImportModal">
          <span class="material-symbols-outlined">upload_file</span>
          {{ t('bulk-import', 'Bulk Import') }}
        </button>
        <button class="btn-primary" @click="openCreateModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-mapping', 'New SKU Mapping') }}
        </button>
        <button class="btn-icon" @click="loadData" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="kpi-grid mb-6">
      <div class="kpi-card">
        <div class="kpi-icon icon-purple"><span class="material-symbols-outlined">dataset</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-mappings', 'Total SKU Mappings') }}</span>
          <span class="kpi-value">{{ kpis.total }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-green"><span class="material-symbols-outlined">check_circle</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('active-mappings', 'Active Mappings') }}</span>
          <span class="kpi-value">{{ kpis.active }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-indigo"><span class="material-symbols-outlined">corporate_fare</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('partners-covered', 'Trading Partners Covered') }}</span>
          <span class="kpi-value">{{ kpis.partnersCount }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-blue"><span class="material-symbols-outlined">qr_code_2</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('gtin-barcodes', 'GTIN / EAN Mapped') }}</span>
          <span class="kpi-value">{{ kpis.gtinCount }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-amber"><span class="material-symbols-outlined">scale</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('uom-conversions', 'UOM Multipliers (>1.0)') }}</span>
          <span class="kpi-value">{{ kpis.uomConversionCount }}</span>
        </div>
      </div>
    </div>

    <!-- Live Cross-Reference Tester Tool Card (collapsible / toggleable) -->
    <div v-if="showTester" class="tester-card mb-6" id="tester-panel">
      <div class="tester-header">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">troubleshoot</span>
          <h3 class="tester-title">{{ t('live-cross-ref-tester', 'Live SKU & Pricing Cross-Reference Resolver') }}</h3>
        </div>
        <button class="btn-icon btn-sm" @click="showTester = false">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="tester-body">
        <p class="text-xs text-muted mb-3">
          {{ t('tester-desc', 'Simulate inbound EDI 850 line item resolution against T0125 SKU matrix, customer contract prices (T0122), and price lists (T0084).') }}
        </p>
        <div class="tester-grid">
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('trading-partner', 'Trading Partner') }} <span class="required">*</span></label>
            <select v-model="testerForm.partner_id" class="form-control form-control-sm">
              <option :value="null">{{ t('select-partner', '-- Select Partner --') }}</option>
              <option v-for="p in partners" :key="p.id" :value="p.id">
                {{ p.partner_code }} ({{ p.partner_name }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('partner-sku', 'Partner SKU / Buyer Part #') }}</label>
            <input
              v-model="testerForm.partner_sku"
              type="text"
              class="form-control form-control-sm"
              placeholder="e.g. CR-MILK-1L"
            />
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('gtin-barcode', 'GTIN / EAN Barcode') }}</label>
            <input
              v-model="testerForm.gtin"
              type="text"
              class="form-control form-control-sm"
              placeholder="e.g. 6291041000012"
            />
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('ordered-uom', 'Ordered UOM') }}</label>
            <input
              v-model="testerForm.partner_uom"
              type="text"
              class="form-control form-control-sm"
              placeholder="e.g. CA, EA, BX"
            />
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('ordered-price', 'Ordered Price ($)') }}</label>
            <input
              v-model.number="testerForm.ordered_price"
              type="number"
              step="0.01"
              min="0"
              class="form-control form-control-sm"
              placeholder="e.g. 24.50"
            />
          </div>
          <div class="form-group">
            <label class="text-xs font-semibold">{{ t('price-tolerance', 'Price Tolerance (%)') }}</label>
            <input
              v-model.number="testerForm.price_tolerance_percent"
              type="number"
              step="0.1"
              min="0"
              class="form-control form-control-sm"
              placeholder="e.g. 2.0"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-3">
          <button class="btn-sm btn-outline" @click="resetTesterForm">
            {{ t('reset', 'Reset') }}
          </button>
          <button
            class="btn-sm btn-primary"
            @click="executeTestResolution"
            :disabled="testingResolution || !testerForm.partner_id || (!testerForm.partner_sku && !testerForm.gtin)"
          >
            <span v-if="testingResolution" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">play_arrow</span>
            {{ testingResolution ? t('resolving', 'Resolving...') : t('test-resolution', 'Test Resolution') }}
          </button>
        </div>

        <!-- Resolution Test Result Banner -->
        <div v-if="testerResult" class="test-result-box mt-3" :class="testerResultClass">
          <div class="flex items-center gap-2 mb-2">
            <span class="material-symbols-outlined">{{ testerResult.is_matched ? 'check_circle' : 'cancel' }}</span>
            <strong class="text-sm">
              {{ testerResult.is_matched ? t('match-found', 'Match Found & Resolved') : t('match-failed', 'Cross-Reference Resolution Failed') }}
            </strong>
          </div>

          <div v-if="testerResult.is_matched" class="test-details-grid">
            <div>
              <span class="detail-label">{{ t('internal-product', 'Internal Product:') }}</span>
              <strong>{{ testerResult.product_name || ('Product #' + testerResult.product_id) }}</strong>
              <span class="text-xs text-muted block font-mono">SKU: {{ testerResult.resolved_sku || '-' }}</span>
            </div>
            <div>
              <span class="detail-label">{{ t('uom-conversion', 'UOM Multiplier:') }}</span>
              <span>1 {{ testerForm.partner_uom || 'Unit' }} = {{ testerResult.uom_conversion_factor }} Base Units (Qty: {{ testerResult.internal_qty }})</span>
            </div>
            <div>
              <span class="detail-label">{{ t('expected-price', 'Contract / List Price:') }}</span>
              <span class="font-bold text-green-700">${{ (testerResult.contract_price || 0).toFixed(2) }}</span>
            </div>
            <div>
              <span class="detail-label">{{ t('tolerance-evaluation', 'Price Tolerance:') }}</span>
              <span v-if="testerResult.has_discrepancy" class="badge badge-warning">
                DISCREPANCY ({{ testerResult.price_discrepancy?.discrepancy_percent?.toFixed(1) }}% variance)
              </span>
              <span v-else class="badge badge-success">WITHIN TOLERANCE</span>
            </div>
          </div>

          <div v-if="testerResult.errors && testerResult.errors.length" class="mt-2 text-xs text-red-700">
            <strong>{{ t('errors', 'Errors:') }}</strong>
            <ul class="list-disc pl-4 mt-1">
              <li v-for="(err, idx) in testerResult.errors" :key="idx">{{ err }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Filter & Table Section -->
    <div class="data-card">
      <div class="card-filter-bar">
        <div class="search-wrap">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('search-mappings', 'Search by Partner SKU, Internal SKU, GTIN, Product Name, Partner...')"
          />
        </div>

        <div class="filters-wrap">
          <select v-model="filterPartner" class="filter-select">
            <option value="">{{ t('all-partners', 'All Trading Partners') }}</option>
            <option v-for="p in partners" :key="p.id" :value="p.id">
              {{ p.partner_code }} ({{ p.partner_name }})
            </option>
          </select>

          <select v-model="filterSkuType" class="filter-select">
            <option value="">{{ t('all-sku-types', 'All SKU Types') }}</option>
            <option value="BUYER_PART_NO">BUYER_PART_NO</option>
            <option value="GTIN">GTIN</option>
            <option value="EAN">EAN</option>
            <option value="UPC">UPC</option>
            <option value="VENDOR_PART_NO">VENDOR_PART_NO</option>
          </select>

          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
            <option value="active">{{ t('active-only', 'Active Only') }}</option>
            <option value="inactive">{{ t('inactive-only', 'Inactive Only') }}</option>
          </select>
        </div>
      </div>

      <SkeletonTable v-if="loading" />
      <ErrorState v-else-if="error" :message="error" @retry="loadData" />

      <div v-else-if="!filteredMappings.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">dataset</span>
        <p>{{ t('no-mappings-found', 'No SKU cross-reference mappings found.') }}</p>
        <button class="btn-primary" @click="openCreateModal">{{ t('create-first-mapping', 'Add First Mapping') }}</button>
      </div>

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('partner', 'Partner') }}</th>
              <th>{{ t('partner-sku', 'Partner SKU') }}</th>
              <th>{{ t('sku-type', 'SKU Type') }}</th>
              <th>{{ t('gtin-barcode', 'GTIN / EAN') }}</th>
              <th>{{ t('internal-product', 'Internal Product (T0001)') }}</th>
              <th>{{ t('uom-conversion', 'UOM Ratio') }}</th>
              <th>{{ t('reference-price', 'Catalog Price') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in filteredMappings" :key="m.id">
              <td>
                <span class="font-bold text-primary">{{ getPartnerCode(m.partner_id) }}</span>
                <span class="text-xs text-muted block">{{ getPartnerName(m.partner_id) }}</span>
              </td>
              <td>
                <strong class="font-mono text-slate-800">{{ m.partner_sku }}</strong>
              </td>
              <td>
                <span class="badge" :class="skuTypeBadge(m.partner_sku_type)">{{ m.partner_sku_type || 'BUYER_PART_NO' }}</span>
              </td>
              <td>
                <div v-if="m.gtin" class="flex items-center gap-1 font-mono text-xs">
                  <span>{{ m.gtin }}</span>
                  <button class="btn-icon btn-xs" :title="t('copy', 'Copy')" @click="copyText(m.gtin)">
                    <span class="material-symbols-outlined text-xs">content_copy</span>
                  </button>
                </div>
                <span v-else class="text-muted text-xs">-</span>
              </td>
              <td>
                <div class="product-info-cell">
                  <span class="font-semibold text-slate-900">{{ getProductName(m.product_id) }}</span>
                  <span class="text-xs text-muted block font-mono">SKU: {{ getProductSku(m.product_id) }} (ID #{{ m.product_id }})</span>
                </div>
              </td>
              <td>
                <div class="uom-ratio-tag">
                  <span class="font-mono font-bold">{{ m.partner_uom || 'EA' }}</span>
                  <span class="text-xs text-muted">→</span>
                  <span class="font-mono font-bold">{{ m.internal_uom || 'EA' }}</span>
                  <span class="multiplier-badge" v-if="m.uom_conversion_factor !== 1">×{{ m.uom_conversion_factor }}</span>
                </div>
              </td>
              <td>
                <span v-if="m.catalog_price !== null && m.catalog_price !== undefined" class="font-bold text-slate-800">
                  ${{ Number(m.catalog_price).toFixed(2) }}
                </span>
                <span v-else class="text-muted text-xs">-</span>
              </td>
              <td class="text-center">
                <span class="badge" :class="m.is_active ? 'badge-success' : 'badge-disabled'">
                  {{ m.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                </span>
              </td>
              <td class="text-center">
                <div class="action-buttons">
                  <button
                    class="btn-icon"
                    :title="t('test-in-resolver', 'Test in Resolver')"
                    @click="quickTestMapping(m)"
                  >
                    <span class="material-symbols-outlined text-blue-600">troubleshoot</span>
                  </button>
                  <button
                    class="btn-icon"
                    :title="t('edit', 'Edit')"
                    @click="openEditModal(m)"
                  >
                    <span class="material-symbols-outlined text-slate-600">edit</span>
                  </button>
                  <button
                    class="btn-icon"
                    :title="t('delete', 'Delete')"
                    @click="confirmDelete(m)"
                  >
                    <span class="material-symbols-outlined text-red-600">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal 1: Create / Edit SKU Mapping Modal -->
    <div v-if="showFormModal" class="modal-overlay" @click.self="showFormModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ isEditing ? t('edit-sku-mapping', 'Edit SKU Cross-Reference Mapping') : t('new-sku-mapping', 'New SKU Cross-Reference Mapping') }}
          </h3>
          <button class="btn-icon" @click="showFormModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>

        <form @submit.prevent="saveMapping">
          <div class="modal-body">
            <div class="form-row mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('trading-partner', 'Trading Partner') }} <span class="required">*</span></label>
                <select v-model="form.partner_id" class="form-control" required>
                  <option :value="null">{{ t('select-partner', '-- Select Partner --') }}</option>
                  <option v-for="p in partners" :key="p.id" :value="p.id">
                    {{ p.partner_code }} - {{ p.partner_name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">{{ t('internal-product', 'Internal Product (T0001)') }} <span class="required">*</span></label>
                <select v-model="form.product_id" class="form-control" required>
                  <option :value="null">{{ t('select-product', '-- Select Product --') }}</option>
                  <option v-for="prod in products" :key="prod.id" :value="prod.id">
                    {{ prod.sku || prod.code || ('#' + prod.id) }} — {{ prod.name || prod.product_name }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-row mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('partner-sku', 'Partner SKU / Buyer Part #') }} <span class="required">*</span></label>
                <input
                  v-model="form.partner_sku"
                  type="text"
                  class="form-control"
                  placeholder="e.g. CR-MILK-1L or LULU-99210"
                  required
                />
              </div>

              <div class="form-group">
                <label class="form-label">{{ t('partner-sku-type', 'Identifier Type') }} <span class="required">*</span></label>
                <select v-model="form.partner_sku_type" class="form-control" required>
                  <option value="BUYER_PART_NO">BUYER_PART_NO (Buyer Internal Code)</option>
                  <option value="GTIN">GTIN (Global Trade Item Number)</option>
                  <option value="EAN">EAN (European Article Number)</option>
                  <option value="UPC">UPC (Universal Product Code)</option>
                  <option value="VENDOR_PART_NO">VENDOR_PART_NO (Supplier Part Code)</option>
                </select>
              </div>
            </div>

            <div class="form-row mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('gtin-barcode', 'GTIN / EAN Barcode') }}</label>
                <input
                  v-model="form.gtin"
                  type="text"
                  class="form-control"
                  placeholder="e.g. 6291041000012"
                />
              </div>

              <div class="form-group">
                <label class="form-label">{{ t('catalog-price', 'Contract / Reference Price ($)') }}</label>
                <input
                  v-model.number="form.catalog_price"
                  type="number"
                  step="0.01"
                  min="0"
                  class="form-control"
                  placeholder="e.g. 18.50"
                />
              </div>
            </div>

            <div class="p-3 bg-slate-50 border rounded-lg mb-3">
              <h5 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                {{ t('uom-conversion-setup', 'Unit of Measure & Packaging Multiplier') }}
              </h5>
              <div class="form-row">
                <div class="form-group mb-0">
                  <label class="form-label">{{ t('partner-uom', 'Partner UOM') }}</label>
                  <input
                    v-model="form.partner_uom"
                    type="text"
                    class="form-control"
                    placeholder="e.g. CA (Case), EA, BX"
                    required
                  />
                </div>
                <div class="form-group mb-0">
                  <label class="form-label">{{ t('internal-uom', 'Internal Base UOM') }}</label>
                  <input
                    v-model="form.internal_uom"
                    type="text"
                    class="form-control"
                    placeholder="e.g. EA, PCS, KG"
                    required
                  />
                </div>
              </div>

              <div class="mt-3">
                <label class="form-label">{{ t('uom-factor', 'UOM Multiplier (Conversion Factor)') }}</label>
                <div class="flex items-center gap-2">
                  <input
                    v-model.number="form.uom_conversion_factor"
                    type="number"
                    step="0.0001"
                    min="0.0001"
                    class="form-control"
                    placeholder="e.g. 12.0 for a case of 12 units"
                    required
                  />
                  <span class="text-xs text-muted whitespace-nowrap">
                    1 {{ form.partner_uom || 'Unit' }} = {{ form.uom_conversion_factor || 1 }} {{ form.internal_uom || 'Base Units' }}
                  </span>
                </div>
              </div>
            </div>

            <div class="form-group mb-0">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" />
                <span class="font-medium">{{ t('is-active', 'Active Cross-Reference Mapping') }}</span>
              </label>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-outline" @click="showFormModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              <span v-if="saving" class="spinner-sm"></span>
              <span v-else class="material-symbols-outlined">save</span>
              {{ saving ? t('saving', 'Saving...') : t('save-mapping', 'Save Mapping') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal 2: Bulk Import SKU Mappings Modal -->
    <div v-if="showBulkModal" class="modal-overlay" @click.self="showBulkModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">upload_file</span>
            <h3 class="modal-title">{{ t('bulk-import-mappings', 'Bulk Import SKU Cross-Reference Matrix') }}</h3>
          </div>
          <button class="btn-icon" @click="showBulkModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('target-partner', 'Trading Partner') }} <span class="required">*</span></label>
              <select v-model="bulkPartnerId" class="form-control" required>
                <option :value="null">{{ t('select-partner', '-- Select Partner --') }}</option>
                <option v-for="p in partners" :key="p.id" :value="p.id">
                  {{ p.partner_code }} - {{ p.partner_name }}
                </option>
              </select>
            </div>
            <div class="form-group flex items-end">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="bulkOverwrite" />
                <span>{{ t('overwrite-existing', 'Overwrite Existing Mappings') }}</span>
              </label>
            </div>
          </div>

          <div class="tabs mb-3">
            <button class="tab-btn" :class="{ active: bulkFormat === 'csv' }" @click="bulkFormat = 'csv'">
              <span class="material-symbols-outlined">grid_on</span> CSV Format
            </button>
            <button class="tab-btn" :class="{ active: bulkFormat === 'json' }" @click="bulkFormat = 'json'">
              <span class="material-symbols-outlined">data_object</span> JSON Format
            </button>
          </div>

          <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-semibold text-muted">
              {{ bulkFormat === 'csv' ? 'Columns: partner_sku, product_id, gtin, partner_uom, uom_conversion_factor, catalog_price' : 'Array of mapping objects' }}
            </span>
            <button class="btn-sm btn-outline" @click="loadBulkSample">
              <span class="material-symbols-outlined">description</span> {{ t('load-sample', 'Load Sample') }}
            </button>
          </div>

          <textarea
            v-model="bulkPayloadText"
            rows="8"
            class="form-control code-editor"
            :placeholder="bulkFormat === 'csv' ? 'partner_sku,product_id,gtin,partner_uom,uom_conversion_factor,catalog_price\nCR-MILK-1L,1,6291041000012,CA,12,24.50' : '[\n  {\n    \"partner_sku\": \"CR-MILK-1L\",\n    \"product_id\": 1,\n    \"gtin\": \"6291041000012\",\n    \"partner_uom\": \"CA\",\n    \"uom_conversion_factor\": 12,\n    \"catalog_price\": 24.50\n  }\n]'"
          ></textarea>

          <!-- Bulk Result Report -->
          <div v-if="bulkResult" class="bulk-result-banner mt-3" :class="bulkResult.errors?.length ? 'banner-warning' : 'banner-success'">
            <div class="flex items-center gap-2 mb-1">
              <span class="material-symbols-outlined">{{ bulkResult.errors?.length ? 'warning' : 'check_circle' }}</span>
              <strong>{{ t('bulk-import-complete', 'Bulk Import Complete') }}</strong>
            </div>
            <p class="text-xs">
              Created: <strong>{{ bulkResult.created || 0 }}</strong> |
              Updated: <strong>{{ bulkResult.updated || 0 }}</strong> |
              Skipped: <strong>{{ bulkResult.skipped || 0 }}</strong>
            </p>
            <div v-if="bulkResult.errors && bulkResult.errors.length" class="mt-2 text-xs text-red-700">
              <strong>{{ t('import-errors', 'Errors:') }}</strong>
              <ul class="list-disc pl-4 mt-1">
                <li v-for="(err, idx) in bulkResult.errors" :key="idx">{{ err }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="showBulkModal = false">{{ t('close', 'Close') }}</button>
          <button
            class="btn-primary"
            @click="executeBulkImport"
            :disabled="bulkImporting || !bulkPartnerId || !bulkPayloadText.trim()"
          >
            <span v-if="bulkImporting" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">upload</span>
            {{ bulkImporting ? t('importing', 'Importing...') : t('run-import', 'Import Mappings') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Dialog -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-content" style="max-width: 440px;">
        <div class="modal-header">
          <h3 class="modal-title">{{ t('confirm-delete', 'Confirm Deletion') }}</h3>
          <button class="btn-icon" @click="deleteTarget = null"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-slate-700">
            {{ t('delete-mapping-prompt', 'Are you sure you want to delete the SKU mapping for') }}
            <strong>{{ deleteTarget.partner_sku }}</strong>
            ({{ getPartnerCode(deleteTarget.partner_id) }})?
          </p>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="deleteTarget = null">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-danger" @click="executeDelete" :disabled="deleting">
            <span v-if="deleting" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">delete</span>
            {{ deleting ? t('deleting', 'Deleting...') : t('delete', 'Delete') }}
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
const mappings = ref([])
const partners = ref([])
const products = ref([])

// Filters
const searchQuery = ref('')
const filterPartner = ref('')
const filterSkuType = ref('')
const filterStatus = ref('')

// Tester Panel State
const showTester = ref(false)
const testingResolution = ref(false)
const testerResult = ref(null)
const testerForm = ref({
  partner_id: null,
  partner_sku: '',
  gtin: '',
  partner_uom: 'EA',
  ordered_price: null,
  price_tolerance_percent: 0.0,
})

// Create / Edit Modal State
const showFormModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = ref({
  partner_id: null,
  product_id: null,
  partner_sku: '',
  partner_sku_type: 'BUYER_PART_NO',
  gtin: '',
  partner_uom: 'EA',
  internal_uom: 'EA',
  uom_conversion_factor: 1.0,
  catalog_price: null,
  is_active: true,
})

// Bulk Import Modal State
const showBulkModal = ref(false)
const bulkPartnerId = ref(null)
const bulkOverwrite = ref(false)
const bulkFormat = ref('csv')
const bulkPayloadText = ref('')
const bulkImporting = ref(false)
const bulkResult = ref(null)

// Delete State
const deleteTarget = ref(null)
const deleting = ref(false)

// Computed KPIs
const kpis = computed(() => {
  const total = mappings.value.length
  let active = 0
  let gtinCount = 0
  let uomConversionCount = 0
  const partnerSet = new Set()

  for (const m of mappings.value) {
    if (m.is_active) active++
    if (m.gtin) gtinCount++
    if (m.uom_conversion_factor && m.uom_conversion_factor !== 1) uomConversionCount++
    if (m.partner_id) partnerSet.add(m.partner_id)
  }

  return {
    total,
    active,
    partnersCount: partnerSet.size,
    gtinCount,
    uomConversionCount,
  }
})

// Filtered Mappings
const filteredMappings = computed(() => {
  return mappings.value.filter(m => {
    if (filterPartner.value && String(m.partner_id) !== String(filterPartner.value)) return false
    if (filterSkuType.value && m.partner_sku_type !== filterSkuType.value) return false
    if (filterStatus.value === 'active' && !m.is_active) return false
    if (filterStatus.value === 'inactive' && m.is_active) return false

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const pSku = (m.partner_sku || '').toLowerCase()
      const gtin = (m.gtin || '').toLowerCase()
      const pCode = getPartnerCode(m.partner_id).toLowerCase()
      const prodName = getProductName(m.product_id).toLowerCase()
      const prodSku = getProductSku(m.product_id).toLowerCase()
      return pSku.includes(q) || gtin.includes(q) || pCode.includes(q) || prodName.includes(q) || prodSku.includes(q)
    }
    return true
  })
})

// Tester Result Class
const testerResultClass = computed(() => {
  if (!testerResult.value) return ''
  if (!testerResult.value.is_matched) return 'banner-danger'
  if (testerResult.value.has_discrepancy) return 'banner-warning'
  return 'banner-success'
})

// Helper Functions
function getPartnerCode(partnerId) {
  if (!partnerId) return 'GLOBAL'
  const found = partners.value.find(p => p.id === partnerId)
  return found ? found.partner_code : `Partner #${partnerId}`
}

function getPartnerName(partnerId) {
  if (!partnerId) return ''
  const found = partners.value.find(p => p.id === partnerId)
  return found ? found.partner_name : ''
}

function getProductName(productId) {
  if (!productId) return 'Unassigned'
  const found = products.value.find(p => p.id === productId)
  return found ? (found.name || found.product_name || `Product #${productId}`) : `Product #${productId}`
}

function getProductSku(productId) {
  if (!productId) return '-'
  const found = products.value.find(p => p.id === productId)
  return found ? (found.sku || found.code || '-') : '-'
}

function skuTypeBadge(type) {
  const t = (type || '').toUpperCase()
  if (t === 'GTIN' || t === 'EAN') return 'badge-blue'
  if (t === 'BUYER_PART_NO') return 'badge-purple'
  if (t === 'UPC') return 'badge-teal'
  return 'badge-doc'
}

function copyText(text) {
  if (!text) return
  navigator.clipboard.writeText(text)
  toast(t('copied-to-clipboard', 'Copied to clipboard'))
}

// Data Loading
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [mRes, pRes, prodRes] = await Promise.allSettled([
      api.get('/T0125I/?limit=300'),
      api.get('/T0124I/?limit=100'),
      api.get('/T0001I/?limit=300'),
    ])

    if (mRes.status === 'fulfilled') {
      mappings.value = Array.isArray(mRes.value.data) ? mRes.value.data : (mRes.value.data?.items || [])
    }
    if (pRes.status === 'fulfilled') {
      partners.value = Array.isArray(pRes.value.data) ? pRes.value.data : (pRes.value.data?.items || [])
    }
    if (prodRes.status === 'fulfilled') {
      products.value = Array.isArray(prodRes.value.data) ? prodRes.value.data : (prodRes.value.data?.items || [])
    }
  } catch (err) {
    console.error('Failed to load EDI SKU mappings:', err)
    error.value = t('failed-load', 'Failed to load SKU cross-reference matrix')
  } finally {
    loading.value = false
  }
}

// Tester Tool Actions
function resetTesterForm() {
  testerForm.value = {
    partner_id: partners.value[0]?.id || null,
    partner_sku: '',
    gtin: '',
    partner_uom: 'EA',
    ordered_price: null,
    price_tolerance_percent: 0.0,
  }
  testerResult.value = null
}

async function executeTestResolution() {
  if (!testerForm.value.partner_id) {
    toast(t('select-partner-required', 'Please select a trading partner'), 'error')
    return
  }

  testingResolution.value = true
  testerResult.value = null
  try {
    const res = await api.post('/edi/cross-reference/resolve', null, {
      params: {
        partner_id: testerForm.value.partner_id,
        partner_sku: testerForm.value.partner_sku || undefined,
        gtin: testerForm.value.gtin || undefined,
        partner_uom: testerForm.value.partner_uom || 'EA',
        ordered_price: testerForm.value.ordered_price || undefined,
        price_tolerance_percent: testerForm.value.price_tolerance_percent || 0.0,
      }
    })
    testerResult.value = res.data
  } catch (err) {
    console.error('Resolution test failed:', err)
    testerResult.value = {
      is_matched: false,
      errors: [err.response?.data?.detail || err.message || 'Resolution failed']
    }
  } finally {
    testingResolution.value = false
  }
}

function quickTestMapping(m) {
  showTester.value = true
  testerForm.value = {
    partner_id: m.partner_id,
    partner_sku: m.partner_sku,
    gtin: m.gtin || '',
    partner_uom: m.partner_uom || 'EA',
    ordered_price: m.catalog_price || null,
    price_tolerance_percent: 0.0,
  }
  executeTestResolution()

  // Scroll to tester
  const el = document.getElementById('tester-panel')
  if (el) el.scrollIntoView({ behavior: 'smooth' })
}

// Modal Actions
function openCreateModal() {
  isEditing.value = false
  editingId.value = null
  form.value = {
    partner_id: partners.value[0]?.id || null,
    product_id: products.value[0]?.id || null,
    partner_sku: '',
    partner_sku_type: 'BUYER_PART_NO',
    gtin: '',
    partner_uom: 'EA',
    internal_uom: 'EA',
    uom_conversion_factor: 1.0,
    catalog_price: null,
    is_active: true,
  }
  showFormModal.value = true
}

function openEditModal(m) {
  isEditing.value = true
  editingId.value = m.id
  form.value = {
    partner_id: m.partner_id,
    product_id: m.product_id,
    partner_sku: m.partner_sku,
    partner_sku_type: m.partner_sku_type || 'BUYER_PART_NO',
    gtin: m.gtin || '',
    partner_uom: m.partner_uom || 'EA',
    internal_uom: m.internal_uom || 'EA',
    uom_conversion_factor: m.uom_conversion_factor || 1.0,
    catalog_price: m.catalog_price,
    is_active: m.is_active !== false,
  }
  showFormModal.value = true
}

async function saveMapping() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (isEditing.value) {
      await api.put(`/T0125I/${editingId.value}`, payload)
      toast(t('mapping-updated', 'SKU cross-reference mapping updated successfully'))
    } else {
      await api.post('/T0125I/', payload)
      toast(t('mapping-created', 'SKU cross-reference mapping created successfully'))
    }
    showFormModal.value = false
    await loadData()
  } catch (err) {
    console.error('Failed to save mapping:', err)
    toast(err.response?.data?.detail || t('save-error', 'Failed to save SKU mapping'), 'error')
  } finally {
    saving.value = false
  }
}

// Bulk Import Actions
function openBulkImportModal() {
  bulkPartnerId.value = partners.value[0]?.id || null
  bulkOverwrite.value = false
  bulkFormat.value = 'csv'
  bulkPayloadText.value = ''
  bulkResult.value = null
  showBulkModal.value = true
}

function loadBulkSample() {
  if (bulkFormat.value === 'csv') {
    bulkPayloadText.value = `partner_sku,product_id,gtin,partner_uom,uom_conversion_factor,catalog_price
CR-MILK-1L,1,6291041000012,CA,12,24.50
CR-CHEE-500G,2,6291041000029,BX,6,35.00
CR-YOG-200G,3,6291041000036,CA,24,18.00`
  } else {
    bulkPayloadText.value = JSON.stringify([
      {
        partner_sku: 'CR-MILK-1L',
        product_id: 1,
        gtin: '6291041000012',
        partner_uom: 'CA',
        uom_conversion_factor: 12,
        catalog_price: 24.50
      },
      {
        partner_sku: 'CR-CHEE-500G',
        product_id: 2,
        gtin: '6291041000029',
        partner_uom: 'BX',
        uom_conversion_factor: 6,
        catalog_price: 35.00
      }
    ], null, 2)
  }
}

async function executeBulkImport() {
  if (!bulkPartnerId.value) {
    toast(t('select-partner-required', 'Please select a trading partner'), 'error')
    return
  }

  let mappingsList = []
  try {
    if (bulkFormat.value === 'json') {
      mappingsList = JSON.parse(bulkPayloadText.value)
    } else {
      // Parse CSV
      const lines = bulkPayloadText.value.trim().split('\n').map(l => l.trim()).filter(Boolean)
      if (lines.length < 2) {
        toast('CSV must contain a header and at least one data line', 'error')
        return
      }
      const header = lines[0].split(',').map(h => h.trim().toLowerCase())
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',').map(p => p.trim())
        const item = {}
        header.forEach((key, idx) => {
          if (parts[idx] !== undefined) {
            if (key === 'product_id' || key === 'uom_conversion_factor' || key === 'catalog_price') {
              item[key] = parseFloat(parts[idx]) || (key === 'uom_conversion_factor' ? 1.0 : parts[idx])
            } else {
              item[key] = parts[idx]
            }
          }
        })
        mappingsList.push(item)
      }
    }
  } catch (err) {
    toast(`Format error: ${err.message}`, 'error')
    return
  }

  bulkImporting.value = true
  bulkResult.value = null
  try {
    const res = await api.post('/edi/sku-mappings/bulk-import', mappingsList, {
      params: {
        partner_id: bulkPartnerId.value,
        overwrite_existing: bulkOverwrite.value,
      }
    })
    bulkResult.value = res.data
    toast(t('bulk-import-success', 'SKU mappings bulk imported successfully'))
    await loadData()
  } catch (err) {
    console.error('Bulk import failed:', err)
    toast(err.response?.data?.detail || 'Bulk import failed', 'error')
  } finally {
    bulkImporting.value = false
  }
}

// Delete Action
function confirmDelete(m) {
  deleteTarget.value = m
}

async function executeDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/T0125I/${deleteTarget.value.id}`)
    toast(t('mapping-deleted', 'SKU mapping deleted successfully'))
    deleteTarget.value = null
    await loadData()
  } catch (err) {
    console.error('Failed to delete mapping:', err)
    toast(err.response?.data?.detail || t('delete-error', 'Failed to delete SKU mapping'), 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.edi-sku-mapping-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 800;
  color: #1e293b;
  margin: 0 0 4px 0;
}
.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* KPI Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.kpi-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #f1f5f9;
}
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.icon-purple { background: #f3e8ff; color: #7e22ce; }
.icon-green { background: #e8f5e9; color: #2e7d32; }
.icon-blue { background: #e0f2fe; color: #0284c7; }
.icon-indigo { background: #e0e7ff; color: #4338ca; }
.icon-amber { background: #fff3e0; color: #d97706; }

.kpi-info {
  display: flex;
  flex-direction: column;
}
.kpi-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}
.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: #1e293b;
  margin-top: 2px;
}

/* Live Tester Card */
.tester-card {
  background: #fff;
  border: 1px solid #e0e7ff;
  border-radius: 14px;
  padding: 18px 22px;
  box-shadow: 0 4px 12px rgba(93, 63, 211, 0.06);
}
.tester-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.tester-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}
.tester-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.test-result-box {
  padding: 14px 18px;
  border-radius: 10px;
  border: 1px solid transparent;
}
.test-details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  font-size: 13px;
  margin-top: 8px;
}
.detail-label {
  display: block;
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

/* Data Card & Tables */
.data-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #f1f5f9;
  overflow: hidden;
}
.card-filter-bar {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 260px;
  max-width: 440px;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 18px;
}
.search-input {
  width: 100%;
  padding: 7px 12px 7px 34px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}
.search-input:focus {
  border-color: #5d3fd3;
  box-shadow: 0 0 0 2px rgba(93, 63, 211, 0.1);
}
.filters-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-select {
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  color: #334155;
  background: #fff;
  outline: none;
}
.table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  background: #f8fafc;
  color: #64748b;
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}
.data-table tbody tr:hover {
  background: #fbfbfe;
}

/* Badges */
.badge { display: inline-block; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; }
.badge-xs { display: inline-block; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 600; }
.badge-purple { background: #f3e8ff; color: #7e22ce; }
.badge-blue { background: #e0f2fe; color: #0369a1; }
.badge-teal { background: #ccfbf1; color: #0f766e; }
.badge-doc { background: #f1f5f9; color: #475569; font-family: monospace; font-weight: 700; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #d97706; }
.badge-disabled { background: #f1f5f9; color: #94a3b8; }

.uom-ratio-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 3px 8px;
  border-radius: 6px;
}
.multiplier-badge {
  background: #ede9fe;
  color: #6d28d9;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  margin-left: 2px;
}

/* Result Banners */
.banner-success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.banner-warning { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.banner-danger { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }

.bulk-result-banner {
  padding: 12px 16px;
  border-radius: 8px;
}

/* Buttons */
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

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-danger:hover:not(:disabled) { background: #b91c1c; }

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
.btn-xs { width: 20px; height: 20px; }

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Modals */
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

/* Forms */
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
.code-editor {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  background: #f8fafc;
}
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.required { color: #e53935; }
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
</style>

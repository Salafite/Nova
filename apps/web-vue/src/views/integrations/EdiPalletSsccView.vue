<template>
  <div :dir="dir" class="edi-pallet-sscc-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('edi-pallet-title', 'EDI SSCC Pallet Logistics') }}</h1>
        <p class="page-subtitle">{{ t('edi-pallet-sub', 'GS1-128 / SSCC-18 Logistics Barcodes, Packaging Hierarchy (Pallet -> Box -> Item) & ASN Inspection (T0137)') }}</p>
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
        <button class="btn-outline" @click="router.push('/integrations/edi-sku-mapping')">
          <span class="material-symbols-outlined">dataset</span>
          {{ t('sku-matrix', 'SKU Matrix') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-transactions')">
          <span class="material-symbols-outlined">receipt_long</span>
          {{ t('edi-transactions', 'Transactions') }}
        </button>
        <button class="btn-secondary" @click="openQuickGeneratorModal">
          <span class="material-symbols-outlined">barcode</span>
          {{ t('generate-sscc', 'Generate SSCC') }}
        </button>
        <button class="btn-primary" @click="openCreateModal">
          <span class="material-symbols-outlined">add_box</span>
          {{ t('new-pallet', 'New Pallet') }}
        </button>
        <button class="btn-icon" @click="loadData" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="kpi-grid mb-6">
      <div class="kpi-card">
        <div class="kpi-icon icon-purple"><span class="material-symbols-outlined">inventory_2</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-pallets', 'Total Pallets & Packs') }}</span>
          <span class="kpi-value">{{ kpis.total }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-blue"><span class="material-symbols-outlined">package_2</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('packed-pallets', 'Packed in Warehouse') }}</span>
          <span class="kpi-value">{{ kpis.packed }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-amber"><span class="material-symbols-outlined">dock</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('staged-pallets', 'Staged for Dispatch') }}</span>
          <span class="kpi-value">{{ kpis.staged }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-teal"><span class="material-symbols-outlined">local_shipping</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('dispatched-asns', 'Dispatched / In-Transit') }}</span>
          <span class="kpi-value">{{ kpis.dispatched }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-green"><span class="material-symbols-outlined">check_circle</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('delivered-pallets', 'Delivered (POD)') }}</span>
          <span class="kpi-value">{{ kpis.delivered }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-indigo"><span class="material-symbols-outlined">scale</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-weight', 'Total Weight (kg)') }}</span>
          <span class="kpi-value">{{ kpis.totalWeight.toLocaleString(undefined, { maximumFractionDigits: 1 }) }}</span>
        </div>
      </div>
    </div>

    <!-- Filter Bar & Search -->
    <div class="data-card">
      <div class="card-filter-bar">
        <div class="search-wrap">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('search-pallets', 'Search SSCC barcode, pallet #, delivery ID, order ID...')"
          />
        </div>

        <div class="filters-wrap">
          <select v-model="filterPackageType" class="filter-select">
            <option value="">{{ t('all-package-types', 'All Container Types') }}</option>
            <option value="PALLET">PALLET</option>
            <option value="BOX">BOX / CARTON</option>
            <option value="CASE">CASE</option>
            <option value="CONTAINER">CONTAINER</option>
          </select>

          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
            <option value="CREATED">CREATED</option>
            <option value="PACKED">PACKED</option>
            <option value="STAGED">STAGED</option>
            <option value="DISPATCHED">DISPATCHED</option>
            <option value="DELIVERED">DELIVERED</option>
          </select>

          <select v-model="filterHierarchy" class="filter-select">
            <option value="">{{ t('all-levels', 'All Hierarchy Levels') }}</option>
            <option value="root">{{ t('root-pallets-only', 'Pallets (Root Level)') }}</option>
            <option value="child">{{ t('nested-boxes-only', 'Nested Cartons/Boxes') }}</option>
          </select>

          <button v-if="hasFilters" class="btn-clear" @click="clearFilters">
            <span class="material-symbols-outlined">close</span>
            {{ t('clear-filters', 'Clear') }}
          </button>
        </div>
      </div>

      <!-- Loading / Error / Empty States -->
      <SkeletonTable v-if="loading" />
      <ErrorState v-else-if="error" :message="error" @retry="loadData" />
      <div v-else-if="!filteredPallets.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">inventory_2</span>
        <p class="empty-text">{{ t('no-pallets-found', 'No SSCC pallet records found.') }}</p>
        <div class="empty-actions">
          <button class="btn-primary" @click="openQuickGeneratorModal">
            <span class="material-symbols-outlined">barcode</span>
            {{ t('generate-first-sscc', 'Generate First SSCC Barcode') }}
          </button>
        </div>
      </div>

      <!-- Pallets Data Table -->
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('sscc-barcode', 'GS1 SSCC-18 Barcode') }}</th>
              <th>{{ t('pallet-num', 'Pallet #') }}</th>
              <th>{{ t('type', 'Type') }}</th>
              <th>{{ t('linked-docs', 'Linked Delivery / Order') }}</th>
              <th>{{ t('weight-kg', 'Gross / Net (kg)') }}</th>
              <th>{{ t('volume-cbm', 'Volume (m³)') }}</th>
              <th>{{ t('units-count', 'Units / Contents') }}</th>
              <th>{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pallet in paginatedPallets" :key="pallet.id">
              <!-- SSCC Barcode & Copy -->
              <td>
                <div class="sscc-cell">
                  <span class="font-mono sscc-code">{{ pallet.sscc_barcode }}</span>
                  <button class="btn-copy-mini" @click="copyText(pallet.sscc_barcode)" :title="t('copy-sscc', 'Copy SSCC-18')">
                    <span class="material-symbols-outlined text-xs">content_copy</span>
                  </button>
                </div>
                <div class="text-2xs text-muted font-mono">
                  (00){{ pallet.sscc_barcode }}
                </div>
              </td>

              <!-- Pallet Number -->
              <td>
                <span class="font-bold text-dark">{{ pallet.pallet_number || `PLT-${pallet.id}` }}</span>
                <span v-if="pallet.parent_sscc_id" class="badge-nested block mt-0.5">
                  <span class="material-symbols-outlined text-3xs">subdirectory_arrow_right</span>
                  Parent #{{ pallet.parent_sscc_id }}
                </span>
              </td>

              <!-- Package Type -->
              <td>
                <span class="badge" :class="getPackageTypeBadgeClass(pallet.package_type)">
                  {{ pallet.package_type || 'PALLET' }}
                </span>
              </td>

              <!-- Linked Documents -->
              <td>
                <div class="linked-docs-cell">
                  <span v-if="pallet.delivery_id" class="doc-badge doc-delivery" :title="`Delivery #${pallet.delivery_id}`">
                    <span class="material-symbols-outlined text-xs">local_shipping</span>
                    DEL-{{ pallet.delivery_id }}
                  </span>
                  <span v-if="pallet.sales_order_id" class="doc-badge doc-order" :title="`Sales Order #${pallet.sales_order_id}`">
                    <span class="material-symbols-outlined text-xs">shopping_bag</span>
                    SO-{{ pallet.sales_order_id }}
                  </span>
                  <span v-if="!pallet.delivery_id && !pallet.sales_order_id" class="text-xs text-muted">
                    -
                  </span>
                </div>
              </td>

              <!-- Weights -->
              <td>
                <div class="weight-cell">
                  <span class="font-medium">{{ formatNumber(pallet.gross_weight_kg) }} kg</span>
                  <span class="text-xs text-muted" v-if="pallet.net_weight_kg">
                    (Net: {{ formatNumber(pallet.net_weight_kg) }} kg)
                  </span>
                </div>
              </td>

              <!-- Volume -->
              <td>
                <span v-if="pallet.volume_cbm" class="text-xs font-mono">{{ pallet.volume_cbm }} m³</span>
                <span v-else class="text-xs text-muted">-</span>
              </td>

              <!-- Items & Contents Summary -->
              <td>
                <div class="contents-cell">
                  <span class="font-bold text-primary">{{ pallet.items_count || 0 }}</span>
                  <span class="text-xs text-muted ml-1">{{ t('units', 'units') }}</span>
                  <button
                    v-if="pallet.contents_summary"
                    class="btn-contents-pill"
                    @click="viewHierarchy(pallet)"
                    :title="t('view-contents-tree', 'View Breakdown')"
                  >
                    <span class="material-symbols-outlined text-xs">account_tree</span>
                    {{ getContentsBadgeText(pallet.contents_summary) }}
                  </button>
                </div>
              </td>

              <!-- Status Badge & Dropdown -->
              <td>
                <div class="status-cell">
                  <span class="badge" :class="getStatusBadgeClass(pallet.status)">
                    {{ pallet.status }}
                  </span>
                </div>
              </td>

              <!-- Action Buttons -->
              <td class="text-center">
                <div class="action-buttons-wrap">
                  <!-- Print GS1 Label -->
                  <button
                    class="btn-icon"
                    @click="viewGs1Label(pallet)"
                    :title="t('print-gs1-label', 'View / Print GS1 Logistics Label')"
                  >
                    <span class="material-symbols-outlined text-primary">print</span>
                  </button>

                  <!-- View Hierarchy Tree -->
                  <button
                    class="btn-icon"
                    @click="viewHierarchy(pallet)"
                    :title="t('view-hierarchy', 'View Packaging Hierarchy (HL)')"
                  >
                    <span class="material-symbols-outlined text-purple">account_tree</span>
                  </button>

                  <!-- Edit Pallet -->
                  <button
                    class="btn-icon"
                    @click="openEditModal(pallet)"
                    :title="t('edit', 'Edit Pallet')"
                  >
                    <span class="material-symbols-outlined text-blue">edit</span>
                  </button>

                  <!-- Change Status Quick Menu -->
                  <button
                    class="btn-icon"
                    @click="openStatusModal(pallet)"
                    :title="t('change-status', 'Update Logistics Status')"
                  >
                    <span class="material-symbols-outlined text-amber">sync_alt</span>
                  </button>

                  <!-- Delete -->
                  <button
                    class="btn-icon text-danger"
                    @click="confirmDelete(pallet)"
                    :title="t('delete', 'Delete')"
                  >
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="filteredPallets.length > pageSize" class="table-pagination">
        <span class="pagination-info">
          {{ t('showing', 'Showing') }} {{ paginationStart }} - {{ paginationEnd }} {{ t('of', 'of') }} {{ filteredPallets.length }}
        </span>
        <div class="pagination-controls">
          <button class="btn-page" :disabled="currentPage === 1" @click="currentPage--">
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
          <button class="btn-page" :disabled="currentPage === totalPages" @click="currentPage++">
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- 1. GS1 Logistics Label Viewer & Printable Modal -->
    <!-- ======================================================================= -->
    <div v-if="showLabelModal" class="modal-backdrop" @click.self="showLabelModal = false">
      <div class="modal-dialog modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">local_shipping</span>
            <h3 class="modal-title">{{ t('gs1-label-title', 'GS1-128 Logistics Pallet Label') }}</h3>
          </div>
          <button class="btn-close" @click="showLabelModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="label-actions-bar mb-4 flex justify-between items-center">
            <div class="flex items-center gap-2">
              <span class="text-xs text-muted">{{ t('format', 'Standard') }}:</span>
              <span class="badge badge-purple">GS1 Logistics Label AI(00)</span>
              <span class="badge badge-blue font-mono">{{ activePallet?.sscc_barcode }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button class="btn-outline btn-sm" @click="copyText(activePallet?.sscc_barcode)">
                <span class="material-symbols-outlined text-xs">content_copy</span>
                {{ t('copy-sscc', 'Copy SSCC-18') }}
              </button>
              <button class="btn-primary btn-sm" @click="printLabel">
                <span class="material-symbols-outlined text-xs">print</span>
                {{ t('print-label', 'Print Label') }}
              </button>
            </div>
          </div>

          <!-- The Physical GS1 Label Preview (Styled for Print & Screen) -->
          <div id="printable-gs1-label" class="gs1-label-sheet">
            <!-- Top Section: Shipper & Consignee -->
            <div class="label-section label-top-grid">
              <div class="label-box shipper-box">
                <div class="box-label">SHIP FROM (SENDER)</div>
                <div class="font-bold">{{ labelData?.header?.shipper?.company_name || 'Nova Distribution Ltd.' }}</div>
                <div>{{ labelData?.header?.shipper?.address || 'Warehouse 4B, Logistics City' }}</div>
                <div>{{ labelData?.header?.shipper?.city || 'Dubai' }}, {{ labelData?.header?.shipper?.country || 'UAE' }}</div>
              </div>
              <div class="label-box ship-to-box">
                <div class="box-label">SHIP TO (CONSIGNEE / DC)</div>
                <div class="font-bold text-lg">{{ labelData?.header?.ship_to?.partner_name || 'Carrefour Supermarket DC' }}</div>
                <div>Store: {{ labelData?.header?.ship_to?.store_number || 'CRF-042' }}</div>
                <div>{{ labelData?.header?.ship_to?.city || 'Dubai Investment Park' }}, {{ labelData?.header?.ship_to?.country || 'UAE' }}</div>
              </div>
            </div>

            <!-- Reference Numbers Bar -->
            <div class="label-section label-ref-grid">
              <div class="label-box">
                <div class="box-label">PURCHASE ORDER #</div>
                <div class="font-bold text-md">{{ activePallet?.sales_order_id ? `PO-SO-${activePallet.sales_order_id}` : 'PO-850-AUTO' }}</div>
              </div>
              <div class="label-box">
                <div class="box-label">DELIVERY SHIPMENT #</div>
                <div class="font-bold text-md">{{ activePallet?.delivery_id ? `DEL-${activePallet.delivery_id}` : 'DISP-001' }}</div>
              </div>
              <div class="label-box">
                <div class="box-label">PALLET # / TARE</div>
                <div class="font-bold text-md">{{ activePallet?.pallet_number || `PLT-${activePallet?.id}` }}</div>
              </div>
            </div>

            <!-- Middle Section: Human Readable Data -->
            <div class="label-section label-middle-grid">
              <div class="label-box span-2">
                <div class="box-label">CONTENT DESCRIPTION</div>
                <div class="font-bold text-md">{{ getPalletContentSummaryText(activePallet) }}</div>
                <div class="text-xs text-muted mt-1">
                  Total Items: {{ activePallet?.items_count || 0 }} Units | Container: {{ activePallet?.package_type || 'PALLET' }}
                </div>
              </div>
              <div class="label-box">
                <div class="box-label">GROSS WEIGHT</div>
                <div class="font-bold text-lg">{{ formatNumber(activePallet?.gross_weight_kg || 0) }} KG</div>
                <div class="text-xs text-muted" v-if="activePallet?.net_weight_kg">Net: {{ formatNumber(activePallet.net_weight_kg) }} KG</div>
              </div>
            </div>

            <!-- Bottom Section: GS1-128 Barcodes -->
            <div class="label-section label-barcode-section">
              <!-- Secondary Barcodes (Batch + Expiry) if available -->
              <div class="secondary-barcode-row" v-if="getBatchOrExpiry(activePallet)">
                <div class="barcode-simulation-sm">
                  <div class="barcode-lines">
                    <span v-for="n in 36" :key="n" :style="{ width: (n % 3 + 1) + 'px' }" class="bar"></span>
                  </div>
                  <div class="barcode-ai-text font-mono">
                    (10) {{ getBatchNumber(activePallet) }} (17) {{ getExpiryDateFormatted(activePallet) }}
                  </div>
                </div>
              </div>

              <!-- Primary SSCC-18 Barcode -->
              <div class="primary-sscc-barcode-wrap">
                <div class="box-label text-center mb-1">SERIAL SHIPPING CONTAINER CODE (SSCC)</div>
                <!-- High-contrast SVG/CSS Barcode Lines -->
                <div class="barcode-lines-wrap">
                  <div class="barcode-bars-dense">
                    <span v-for="b in barcodeBarPattern" :key="b.id" :style="{ width: b.w + 'px', marginRight: b.gap + 'px' }" class="barcode-bar-line"></span>
                  </div>
                </div>
                <!-- Human Readable SSCC formatted (00) 0 0614141 123456789 5 -->
                <div class="human-readable-sscc font-mono">
                  (00) {{ formatHumanReadableSscc(activePallet?.sscc_barcode) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showLabelModal = false">{{ t('close', 'Close') }}</button>
          <button class="btn-primary" @click="printLabel">
            <span class="material-symbols-outlined">print</span>
            {{ t('print-label', 'Print GS1 Label') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- 2. Packaging Hierarchy Tree Modal (Pallet -> Box -> Item) -->
    <!-- ======================================================================= -->
    <div v-if="showHierarchyModal" class="modal-backdrop" @click.self="showHierarchyModal = false">
      <div class="modal-dialog modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-purple">account_tree</span>
            <h3 class="modal-title">{{ t('hierarchy-title', 'Packaging Hierarchy & HL Breakdown') }}</h3>
          </div>
          <button class="btn-close" @click="showHierarchyModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- Summary Header -->
          <div class="hierarchy-summary-card mb-4">
            <div class="flex justify-between items-center">
              <div>
                <span class="text-xs font-bold text-muted uppercase">Tare / Pallet Identifier</span>
                <div class="text-lg font-bold text-dark">{{ activePallet?.pallet_number || `PLT-${activePallet?.id}` }}</div>
                <div class="font-mono text-xs text-primary">(00){{ activePallet?.sscc_barcode }}</div>
              </div>
              <div class="text-right">
                <span class="badge" :class="getStatusBadgeClass(activePallet?.status)">{{ activePallet?.status }}</span>
                <div class="text-xs text-muted mt-1">
                  Gross: <strong>{{ formatNumber(activePallet?.gross_weight_kg) }} kg</strong> |
                  Units: <strong>{{ activePallet?.items_count || 0 }}</strong>
                </div>
              </div>
            </div>
          </div>

          <!-- Interactive Tree Structure -->
          <div class="hierarchy-tree-view">
            <!-- Level 1: Pallet (Tare - Level T) -->
            <div class="tree-node tree-level-pallet">
              <div class="tree-node-header">
                <span class="material-symbols-outlined node-icon icon-pallet">inventory_2</span>
                <div class="node-info">
                  <span class="node-badge badge-tare">HL: Tare / Pallet</span>
                  <span class="font-bold text-dark ml-2">{{ activePallet?.pallet_number || 'Pallet' }}</span>
                  <span class="font-mono text-xs text-muted ml-2">SSCC: {{ activePallet?.sscc_barcode }}</span>
                </div>
                <div class="node-meta">
                  <span class="text-xs font-medium">{{ formatNumber(activePallet?.gross_weight_kg) }} kg</span>
                </div>
              </div>

              <!-- Level 2 & 3: Boxes & Items from contents_summary -->
              <div class="tree-children">
                <div v-if="parsedHierarchyBoxes.length" class="boxes-container">
                  <div v-for="(box, bIdx) in parsedHierarchyBoxes" :key="bIdx" class="tree-node tree-level-box">
                    <div class="tree-node-header">
                      <span class="material-symbols-outlined node-icon icon-box">package_2</span>
                      <div class="node-info">
                        <span class="node-badge badge-box">HL: Pack / Box</span>
                        <span class="font-bold text-dark ml-2">{{ box.box_number || `Box #${bIdx + 1}` }}</span>
                        <span v-if="box.sscc_barcode" class="font-mono text-xs text-muted ml-2">SSCC: {{ box.sscc_barcode }}</span>
                      </div>
                      <div class="node-meta">
                        <span class="text-xs text-muted">{{ box.items?.length || 1 }} SKU(s)</span>
                      </div>
                    </div>

                    <!-- Items within Box -->
                    <div class="tree-children-items">
                      <div v-for="(item, iIdx) in (box.items || [box])" :key="iIdx" class="tree-node-item">
                        <span class="material-symbols-outlined text-teal text-sm">label</span>
                        <div class="item-details">
                          <span class="font-bold text-dark">{{ item.sku || item.product_name || 'Product SKU' }}</span>
                          <span v-if="item.product_name && item.sku" class="text-muted ml-1">- {{ item.product_name }}</span>
                          <div class="item-sub-meta">
                            <span v-if="item.gtin" class="font-mono text-xs">GTIN: {{ item.gtin }} |</span>
                            <span class="font-bold text-primary text-xs"> Qty: {{ item.quantity || item.qty || 1 }} {{ item.uom || 'EA' }}</span>
                            <span v-if="item.batch_number" class="badge-batch ml-2">Lot: {{ item.batch_number }}</span>
                            <span v-if="item.expiry_date" class="text-muted text-xs ml-2">Exp: {{ item.expiry_date }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Fallback when contents_summary is flat list or simple JSON -->
                <div v-else-if="parsedFlatItems.length" class="flat-items-container">
                  <div v-for="(item, iIdx) in parsedFlatItems" :key="iIdx" class="tree-node-item">
                    <span class="material-symbols-outlined text-teal text-sm">label</span>
                    <div class="item-details">
                      <span class="font-bold text-dark">{{ item.sku || item.product_name || `Item #${iIdx + 1}` }}</span>
                      <span v-if="item.product_name && item.sku" class="text-muted ml-1">- {{ item.product_name }}</span>
                      <div class="item-sub-meta">
                        <span v-if="item.gtin" class="font-mono text-xs">GTIN: {{ item.gtin }} |</span>
                        <span class="font-bold text-primary text-xs"> Qty: {{ item.quantity || item.qty || activePallet?.items_count }} {{ item.uom || 'EA' }}</span>
                        <span v-if="item.batch_number" class="badge-batch ml-2">Lot: {{ item.batch_number }}</span>
                        <span v-if="item.expiry_date" class="text-muted text-xs ml-2">Exp: {{ item.expiry_date }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Empty contents -->
                <div v-else class="tree-node-empty">
                  <span class="material-symbols-outlined text-muted text-md">info</span>
                  <span class="text-xs text-muted">
                    No detailed item breakdown recorded for this container. Total units: {{ activePallet?.items_count || 0 }}.
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Raw Contents JSON Accordion -->
          <div class="raw-contents-section mt-4">
            <button class="btn-accordion" @click="showRawJson = !showRawJson">
              <span class="material-symbols-outlined text-xs">{{ showRawJson ? 'expand_less' : 'expand_more' }}</span>
              {{ t('raw-contents-json', 'View Raw Contents Summary JSON') }}
            </button>
            <pre v-if="showRawJson" class="raw-json-viewer">{{ JSON.stringify(activePallet?.contents_summary, null, 2) }}</pre>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showHierarchyModal = false">{{ t('close', 'Close') }}</button>
          <button class="btn-primary" @click="viewGs1Label(activePallet)">
            <span class="material-symbols-outlined">print</span>
            {{ t('view-label', 'View GS1 Label') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- 3. Quick GS1 SSCC-18 Generator Modal -->
    <!-- ======================================================================= -->
    <div v-if="showGeneratorModal" class="modal-backdrop" @click.self="showGeneratorModal = false">
      <div class="modal-dialog">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary">barcode</span>
            <h3 class="modal-title">{{ t('quick-sscc-generator', 'GS1 SSCC-18 Barcode Generator') }}</h3>
          </div>
          <button class="btn-close" @click="showGeneratorModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <p class="text-xs text-muted mb-4">
            {{ t('sscc-gen-desc', 'Generates an official 18-digit Serial Shipping Container Code (SSCC) with GS1 Company Prefix and automated Modulo-10 check digit calculation.') }}
          </p>

          <div class="form-group mb-3">
            <label class="form-label">{{ t('gs1-company-prefix', 'GS1 Company Prefix (7-10 digits)') }}</label>
            <input
              type="text"
              v-model="genForm.company_prefix"
              class="form-control font-mono"
              placeholder="0614141"
              maxlength="12"
            />
            <span class="text-2xs text-muted block mt-1">Standard 7-digit prefix: 0614141 (Nova Distribution default)</span>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('pallet-num-tag', 'Pallet Number / Code') }}</label>
              <input
                type="text"
                v-model="genForm.pallet_number"
                class="form-control"
                placeholder="PLT-2026-001"
              />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('package-type', 'Container Level') }}</label>
              <select v-model="genForm.package_type" class="form-control">
                <option value="PALLET">PALLET</option>
                <option value="BOX">BOX / CARTON</option>
                <option value="CASE">CASE</option>
                <option value="CONTAINER">CONTAINER</option>
              </select>
            </div>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('delivery-id', 'Linked Delivery #') }}</label>
              <input
                type="number"
                v-model.number="genForm.delivery_id"
                class="form-control"
                placeholder="e.g. 101"
              />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('sales-order-id', 'Linked Sales Order #') }}</label>
              <input
                type="number"
                v-model.number="genForm.sales_order_id"
                class="form-control"
                placeholder="e.g. 205"
              />
            </div>
          </div>

          <div class="form-group mb-3">
            <label class="form-label">{{ t('gross-weight-kg', 'Gross Weight (kg)') }}</label>
            <input
              type="number"
              step="0.1"
              v-model.number="genForm.gross_weight_kg"
              class="form-control"
              placeholder="e.g. 450.5"
            />
          </div>

          <!-- Live Generated Barcode Preview -->
          <div v-if="generatedResult" class="generated-preview-card mt-4">
            <div class="preview-header">
              <span class="material-symbols-outlined text-green text-sm">check_circle</span>
              <span class="font-bold text-sm text-green">{{ t('generated-successfully', 'SSCC-18 Barcode Created & Registered!') }}</span>
            </div>
            <div class="preview-body font-mono text-center">
              <div class="text-xl font-bold text-dark">{{ generatedResult.sscc_barcode }}</div>
              <div class="text-xs text-primary font-bold mt-1">{{ generatedResult.gs1_128_formatted }}</div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showGeneratorModal = false">{{ t('close', 'Close') }}</button>
          <button class="btn-primary" @click="handleGenerateSscc" :disabled="generating">
            <span v-if="generating" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">bolt</span>
            {{ generating ? t('generating', 'Generating...') : t('generate-and-register', 'Generate & Save') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- 4. Create / Edit Pallet Modal -->
    <!-- ======================================================================= -->
    <div v-if="showModal" class="modal-backdrop" @click.self="showModal = false">
      <div class="modal-dialog modal-md">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ isEditing ? t('edit-pallet-title', 'Edit Pallet Logistics Record') : t('create-pallet-title', 'Register New SSCC Pallet') }}
          </h3>
          <button class="btn-close" @click="showModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="form-group mb-3">
            <label class="form-label flex justify-between items-center">
              <span>{{ t('sscc-barcode', 'GS1 SSCC-18 Barcode (18 digits)') }} <span class="text-danger">*</span></span>
              <button type="button" class="btn-link-sm" @click="autoFillSscc">
                <span class="material-symbols-outlined text-3xs">auto_fix_high</span> Auto-Generate
              </button>
            </label>
            <input
              type="text"
              v-model="form.sscc_barcode"
              class="form-control font-mono"
              placeholder="006141411234567895"
              maxlength="20"
              @input="validateSsccLive"
            />
            <span v-if="ssccValidationMsg" :class="ssccIsValid ? 'text-green' : 'text-danger'" class="text-2xs block mt-1">
              {{ ssccValidationMsg }}
            </span>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('pallet-num', 'Pallet Number / Tag') }}</label>
              <input type="text" v-model="form.pallet_number" class="form-control" placeholder="PLT-001" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('container-type', 'Container Type') }}</label>
              <select v-model="form.package_type" class="form-control">
                <option value="PALLET">PALLET</option>
                <option value="BOX">BOX</option>
                <option value="CASE">CASE</option>
                <option value="CONTAINER">CONTAINER</option>
              </select>
            </div>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('linked-delivery', 'Linked Delivery #') }}</label>
              <input type="number" v-model.number="form.delivery_id" class="form-control" placeholder="Delivery ID" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('linked-order', 'Linked Sales Order #') }}</label>
              <input type="number" v-model.number="form.sales_order_id" class="form-control" placeholder="Order ID" />
            </div>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('gross-weight', 'Gross Weight (kg)') }}</label>
              <input type="number" step="0.1" v-model.number="form.gross_weight_kg" class="form-control" placeholder="0.0" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('net-weight', 'Net Weight (kg)') }}</label>
              <input type="number" step="0.1" v-model.number="form.net_weight_kg" class="form-control" placeholder="0.0" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('tare-weight', 'Tare (kg)') }}</label>
              <input type="number" step="0.1" v-model.number="form.tare_weight_kg" class="form-control" placeholder="0.0" />
            </div>
          </div>

          <div class="form-row mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('volume-cbm', 'Volume (m³)') }}</label>
              <input type="number" step="0.01" v-model.number="form.volume_cbm" class="form-control" placeholder="0.0" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('items-count', 'Total Units Count') }}</label>
              <input type="number" v-model.number="form.items_count" class="form-control" placeholder="0" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-control">
                <option value="CREATED">CREATED</option>
                <option value="PACKED">PACKED</option>
                <option value="STAGED">STAGED</option>
                <option value="DISPATCHED">DISPATCHED</option>
                <option value="DELIVERED">DELIVERED</option>
              </select>
            </div>
          </div>

          <!-- Contents Summary JSON -->
          <div class="form-group mb-3">
            <label class="form-label">{{ t('contents-summary-json', 'Contents Summary / Hierarchy (JSON format)') }}</label>
            <textarea
              v-model="contentsJsonInput"
              class="form-control font-mono text-xs"
              rows="4"
              placeholder='[{"sku": "BEV-001", "quantity": 120, "batch_number": "LOT-9981", "expiry_date": "2027-12-31"}]'
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showModal = false">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="savePallet" :disabled="saving">
            <span v-if="saving" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">save</span>
            {{ saving ? t('saving', 'Saving...') : t('save-pallet', 'Save Pallet') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- 5. Status Quick Update Modal -->
    <!-- ======================================================================= -->
    <div v-if="showStatusModal" class="modal-backdrop" @click.self="showStatusModal = false">
      <div class="modal-dialog modal-sm">
        <div class="modal-header">
          <h3 class="modal-title">{{ t('update-status', 'Update Pallet Status') }}</h3>
          <button class="btn-close" @click="showStatusModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div class="status-change-info mb-3">
            <div class="font-bold text-dark">{{ activePallet?.pallet_number || `PLT-${activePallet?.id}` }}</div>
            <div class="font-mono text-xs text-muted">{{ activePallet?.sscc_barcode }}</div>
          </div>

          <div class="status-options-grid">
            <button
              v-for="st in ['CREATED', 'PACKED', 'STAGED', 'DISPATCHED', 'DELIVERED']"
              :key="st"
              class="btn-status-option"
              :class="{ active: quickStatus === st }"
              @click="quickStatus = st"
            >
              <span class="badge" :class="getStatusBadgeClass(st)">{{ st }}</span>
            </button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="showStatusModal = false">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="applyStatusChange" :disabled="saving">
            {{ saving ? t('updating', 'Updating...') : t('update', 'Update Status') }}
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

// Data State
const loading = ref(true)
const error = ref('')
const pallets = ref([])

// Filters
const searchQuery = ref('')
const filterPackageType = ref('')
const filterStatus = ref('')
const filterHierarchy = ref('')

// Pagination
const currentPage = ref(1)
const pageSize = 15

// Modals State
const showLabelModal = ref(false)
const showHierarchyModal = ref(false)
const showGeneratorModal = ref(false)
const showModal = ref(false)
const showStatusModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const saving = ref(false)
const generating = ref(false)
const showRawJson = ref(false)

const activePallet = ref(null)
const labelData = ref(null)
const generatedResult = ref(null)
const quickStatus = ref('PACKED')

// Forms
const genForm = ref({
  company_prefix: '0614141',
  pallet_number: '',
  package_type: 'PALLET',
  delivery_id: null,
  sales_order_id: null,
  gross_weight_kg: null,
})

const form = ref({
  sscc_barcode: '',
  pallet_number: '',
  package_type: 'PALLET',
  delivery_id: null,
  sales_order_id: null,
  parent_sscc_id: null,
  gross_weight_kg: null,
  net_weight_kg: null,
  tare_weight_kg: null,
  volume_cbm: null,
  items_count: 0,
  contents_summary: null,
  status: 'PACKED',
})
const contentsJsonInput = ref('')
const ssccValidationMsg = ref('')
const ssccIsValid = ref(true)

// High contrast simulated barcode bar patterns
const barcodeBarPattern = computed(() => {
  const pattern = []
  const seed = activePallet.value?.sscc_barcode || '006141410000000018'
  for (let i = 0; i < 70; i++) {
    const charCode = seed.charCodeAt(i % seed.length) || 50
    const w = ((charCode * (i + 1)) % 3) + 1.5
    const gap = ((charCode + i) % 2) + 1
    pattern.push({ id: i, w, gap })
  }
  return pattern
})

// Modulo-10 Check Digit Calculation
function calculateModulo10(dataStr) {
  const str = String(dataStr).trim()
  if (!str || !/^\d+$/.test(str)) return 0
  let sum = 0
  for (let i = 0; i < str.length; i++) {
    const digit = parseInt(str[i], 10)
    const posFromRight = str.length - i
    const weight = posFromRight % 2 === 1 ? 3 : 1
    sum += digit * weight
  }
  const rem = sum % 10
  return rem === 0 ? 0 : 10 - rem
}

function validateSsccLive() {
  const s = String(form.value.sscc_barcode || '').trim().replace(/[^\d]/g, '')
  if (!s) {
    ssccValidationMsg.value = ''
    ssccIsValid.value = true
    return
  }
  if (s.length !== 18) {
    ssccValidationMsg.value = `SSCC must be exactly 18 digits (current: ${s.length})`
    ssccIsValid.value = false
    return
  }
  const dataPart = s.substring(0, 17)
  const expectedCheck = parseInt(s[17], 10)
  const calculatedCheck = calculateModulo10(dataPart)
  if (expectedCheck !== calculatedCheck) {
    ssccValidationMsg.value = `Invalid Modulo-10 check digit: ${expectedCheck} (calculated: ${calculatedCheck})`
    ssccIsValid.value = false
  } else {
    ssccValidationMsg.value = `✓ Valid GS1 SSCC-18 with Modulo-10 check digit (${expectedCheck})`
    ssccIsValid.value = true
  }
}

function autoFillSscc() {
  const prefix = genForm.value.company_prefix || '0614141'
  const extDigit = '0'
  const serialLength = 16 - prefix.length
  const randomSerial = Math.floor(Math.random() * Math.pow(10, serialLength)).toString().padStart(serialLength, '0')
  const payload17 = `${extDigit}${prefix}${randomSerial}`
  const checkDigit = calculateModulo10(payload17)
  form.value.sscc_barcode = `${payload17}${checkDigit}`
  validateSsccLive()
}

// Copy to Clipboard
async function copyText(txt) {
  if (!txt) return
  try {
    await navigator.clipboard.writeText(txt)
    toast(t('copied-clipboard', 'Copied to clipboard!'), 'success')
  } catch {
    toast('Copy failed', 'error')
  }
}

// Formatting
function formatNumber(num) {
  if (num === null || num === undefined || isNaN(num)) return '0.0'
  return Number(num).toFixed(1)
}

function formatHumanReadableSscc(barcode) {
  if (!barcode) return ''
  const s = String(barcode).trim()
  if (s.length === 18) {
    // 0 0614141 123456789 5
    return `${s[0]} ${s.substring(1, 8)} ${s.substring(8, 17)} ${s[17]}`
  }
  return s
}

function getPackageTypeBadgeClass(type) {
  switch (type?.toUpperCase()) {
    case 'PALLET': return 'badge-purple'
    case 'BOX': return 'badge-teal'
    case 'CASE': return 'badge-blue'
    case 'CONTAINER': return 'badge-amber'
    default: return 'badge-disabled'
  }
}

function getStatusBadgeClass(status) {
  switch (status?.toUpperCase()) {
    case 'DELIVERED': return 'badge-green'
    case 'DISPATCHED': return 'badge-amber'
    case 'STAGED': return 'badge-purple'
    case 'PACKED': return 'badge-blue'
    case 'CREATED': return 'badge-disabled'
    default: return 'badge-disabled'
  }
}

function getContentsBadgeText(contents) {
  if (!contents) return ''
  if (Array.isArray(contents)) return `${contents.length} boxes/items`
  if (typeof contents === 'object') {
    if (contents.boxes) return `${contents.boxes.length} boxes`
    if (contents.items) return `${contents.items.length} items`
    return 'Detailed'
  }
  return 'Summary'
}

function getPalletContentSummaryText(pallet) {
  if (!pallet) return 'Mixed Supermarket Grocery SKU Assortment'
  if (pallet.contents_summary) {
    if (typeof pallet.contents_summary === 'string') return pallet.contents_summary
    if (Array.isArray(pallet.contents_summary) && pallet.contents_summary.length) {
      const first = pallet.contents_summary[0]
      return first.product_name || first.sku || `Mixed Assortment (${pallet.items_count} units)`
    }
  }
  return `Standard Mixed Assortment (${pallet.items_count || 0} Units)`
}

function getBatchOrExpiry(pallet) {
  return getBatchNumber(pallet) || getExpiryDateFormatted(pallet)
}

function getBatchNumber(pallet) {
  if (!pallet?.contents_summary) return 'LOT-260908'
  if (Array.isArray(pallet.contents_summary) && pallet.contents_summary.length) {
    return pallet.contents_summary[0].batch_number || 'LOT-260908'
  }
  return 'LOT-260908'
}

function getExpiryDateFormatted(pallet) {
  if (!pallet?.contents_summary) return '271231'
  if (Array.isArray(pallet.contents_summary) && pallet.contents_summary.length) {
    const exp = pallet.contents_summary[0].expiry_date
    if (exp) return exp.replace(/-/g, '').substring(2)
  }
  return '271231'
}

// Hierarchy Tree Parsing
const parsedHierarchyBoxes = computed(() => {
  if (!activePallet.value?.contents_summary) return []
  const c = activePallet.value.contents_summary
  if (c.boxes && Array.isArray(c.boxes)) return c.boxes
  if (Array.isArray(c) && c.length && c[0].items) return c
  return []
})

const parsedFlatItems = computed(() => {
  if (!activePallet.value?.contents_summary) return []
  const c = activePallet.value.contents_summary
  if (Array.isArray(c) && (!c.length || !c[0].items)) return c
  if (c.items && Array.isArray(c.items)) return c.items
  return []
})

// KPI Calculations
const kpis = computed(() => {
  const all = pallets.value || []
  const total = all.length
  const packed = all.filter(p => p.status === 'PACKED').length
  const staged = all.filter(p => p.status === 'STAGED').length
  const dispatched = all.filter(p => p.status === 'DISPATCHED').length
  const delivered = all.filter(p => p.status === 'DELIVERED').length
  const totalWeight = all.reduce((sum, p) => sum + (Number(p.gross_weight_kg) || 0), 0)
  const totalUnits = all.reduce((sum, p) => sum + (Number(p.items_count) || 0), 0)

  return { total, packed, staged, dispatched, delivered, totalWeight, totalUnits }
})

// Filtering & Search
const hasFilters = computed(() => {
  return !!(searchQuery.value || filterPackageType.value || filterStatus.value || filterHierarchy.value)
})

function clearFilters() {
  searchQuery.value = ''
  filterPackageType.value = ''
  filterStatus.value = ''
  filterHierarchy.value = ''
  currentPage.value = 1
}

const filteredPallets = computed(() => {
  return pallets.value.filter(p => {
    if (filterPackageType.value && (p.package_type || 'PALLET') !== filterPackageType.value) {
      return false
    }
    if (filterStatus.value && p.status !== filterStatus.value) {
      return false
    }
    if (filterHierarchy.value === 'root' && p.parent_sscc_id) {
      return false
    }
    if (filterHierarchy.value === 'child' && !p.parent_sscc_id) {
      return false
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase().trim()
      const matchSscc = (p.sscc_barcode || '').toLowerCase().includes(q)
      const matchPallet = (p.pallet_number || '').toLowerCase().includes(q)
      const matchDel = String(p.delivery_id || '').includes(q)
      const matchOrder = String(p.sales_order_id || '').includes(q)
      if (!matchSscc && !matchPallet && !matchDel && !matchOrder) {
        return false
      }
    }
    return true
  })
})

const totalPages = computed(() => Math.ceil(filteredPallets.value.length / pageSize) || 1)
const paginationStart = computed(() => (currentPage.value - 1) * pageSize + 1)
const paginationEnd = computed(() => Math.min(currentPage.value * pageSize, filteredPallets.value.length))

const paginatedPallets = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredPallets.value.slice(start, start + pageSize)
})

// API Operations
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0137I/')
    pallets.value = res.data || []
  } catch (err) {
    console.error('Failed to load SSCC pallets:', err)
    error.value = t('failed-load', 'Failed to load SSCC pallet records from server.')
  } finally {
    loading.value = false
  }
}

// GS1 Label View & Fetch
async function viewGs1Label(pallet) {
  activePallet.value = pallet
  try {
    const res = await api.get(`/edi/sscc/${pallet.id}/label`)
    labelData.value = res.data?.label || null
  } catch (err) {
    console.warn('Fallback local label data used:', err)
    labelData.value = {
      header: {
        shipper: { company_name: 'Nova Distribution Ltd.', address: 'Warehouse 4B, Logistics City', city: 'Dubai', country: 'UAE' },
        ship_to: { partner_name: 'Carrefour Supermarket DC', store_number: 'CRF-042', city: 'Dubai Investment Park', country: 'UAE' },
      }
    }
  }
  showLabelModal.value = true
}

function printLabel() {
  window.print()
}

// Packaging Hierarchy View
function viewHierarchy(pallet) {
  activePallet.value = pallet
  showRawJson.value = false
  showHierarchyModal.value = true
}

// Quick SSCC Generator
function openQuickGeneratorModal() {
  genForm.value = {
    company_prefix: '0614141',
    pallet_number: `PLT-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
    package_type: 'PALLET',
    delivery_id: null,
    sales_order_id: null,
    gross_weight_kg: null,
  }
  generatedResult.value = null
  showGeneratorModal.value = true
}

async function handleGenerateSscc() {
  generating.value = true
  try {
    const params = new URLSearchParams()
    if (genForm.value.company_prefix) params.append('company_prefix', genForm.value.company_prefix)
    if (genForm.value.pallet_number) params.append('pallet_number', genForm.value.pallet_number)
    if (genForm.value.delivery_id) params.append('delivery_id', genForm.value.delivery_id)
    if (genForm.value.sales_order_id) params.append('sales_order_id', genForm.value.sales_order_id)
    params.append('package_type', genForm.value.package_type || 'PALLET')
    if (genForm.value.gross_weight_kg) params.append('gross_weight_kg', genForm.value.gross_weight_kg)

    const res = await api.post(`/edi/sscc/generate?${params.toString()}`)
    generatedResult.value = res.data
    toast(t('sscc-generated', 'SSCC-18 Barcode generated successfully!'), 'success')
    await loadData()
  } catch (err) {
    console.error('SSCC generation failed:', err)
    toast(t('generation-failed', 'Failed to generate SSCC barcode'), 'error')
  } finally {
    generating.value = false
  }
}

// Create / Edit Modal
function openCreateModal() {
  isEditing.value = false
  editingId.value = null
  form.value = {
    sscc_barcode: '',
    pallet_number: '',
    package_type: 'PALLET',
    delivery_id: null,
    sales_order_id: null,
    parent_sscc_id: null,
    gross_weight_kg: null,
    net_weight_kg: null,
    tare_weight_kg: null,
    volume_cbm: null,
    items_count: 0,
    contents_summary: null,
    status: 'PACKED',
  }
  contentsJsonInput.value = ''
  autoFillSscc()
  showModal.value = true
}

function openEditModal(pallet) {
  isEditing.value = true
  editingId.value = pallet.id
  form.value = {
    sscc_barcode: pallet.sscc_barcode || '',
    pallet_number: pallet.pallet_number || '',
    package_type: pallet.package_type || 'PALLET',
    delivery_id: pallet.delivery_id,
    sales_order_id: pallet.sales_order_id,
    parent_sscc_id: pallet.parent_sscc_id,
    gross_weight_kg: pallet.gross_weight_kg,
    net_weight_kg: pallet.net_weight_kg,
    tare_weight_kg: pallet.tare_weight_kg,
    volume_cbm: pallet.volume_cbm,
    items_count: pallet.items_count || 0,
    status: pallet.status || 'PACKED',
  }
  contentsJsonInput.value = pallet.contents_summary ? JSON.stringify(pallet.contents_summary, null, 2) : ''
  validateSsccLive()
  showModal.value = true
}

async function savePallet() {
  if (!form.value.sscc_barcode) {
    toast(t('sscc-required', 'SSCC barcode is required'), 'error')
    return
  }

  saving.value = true
  try {
    let parsedContents = null
    if (contentsJsonInput.value.trim()) {
      try {
        parsedContents = JSON.parse(contentsJsonInput.value)
      } catch {
        toast(t('invalid-json', 'Contents Summary must be valid JSON'), 'error')
        saving.value = false
        return
      }
    }

    const payload = {
      ...form.value,
      contents_summary: parsedContents,
    }

    if (isEditing.value && editingId.value) {
      await api.put(`/T0137I/${editingId.value}`, payload)
      toast(t('pallet-updated', 'Pallet record updated successfully'), 'success')
    } else {
      await api.post('/T0137I/', payload)
      toast(t('pallet-created', 'Pallet registered successfully'), 'success')
    }
    showModal.value = false
    await loadData()
  } catch (err) {
    console.error('Failed to save pallet:', err)
    toast(t('save-failed', 'Failed to save pallet record'), 'error')
  } finally {
    saving.value = false
  }
}

// Status Modal
function openStatusModal(pallet) {
  activePallet.value = pallet
  quickStatus.value = pallet.status || 'PACKED'
  showStatusModal.value = true
}

async function applyStatusChange() {
  if (!activePallet.value) return
  saving.value = true
  try {
    await api.put(`/T0137I/${activePallet.value.id}`, { status: quickStatus.value })
    toast(t('status-updated', `Status updated to ${quickStatus.value}`), 'success')
    showStatusModal.value = false
    await loadData()
  } catch (err) {
    console.error('Status update failed:', err)
    toast(t('status-failed', 'Failed to update status'), 'error')
  } finally {
    saving.value = false
  }
}

// Delete
async function confirmDelete(pallet) {
  if (!confirm(t('confirm-delete-pallet', `Are you sure you want to delete pallet ${pallet.pallet_number || pallet.sscc_barcode}?`))) {
    return
  }
  try {
    await api.delete(`/T0137I/${pallet.id}`)
    toast(t('pallet-deleted', 'Pallet deleted'), 'success')
    await loadData()
  } catch (err) {
    console.error('Delete failed:', err)
    toast(t('delete-failed', 'Failed to delete pallet'), 'error')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.edi-pallet-sscc-view {
  width: 100%;
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
  flex-wrap: wrap;
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.kpi-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-purple { background: #f3e8ff; color: #7e22ce; }
.icon-blue { background: #dbeafe; color: #1d4ed8; }
.icon-teal { background: #ccfbf1; color: #0f766e; }
.icon-green { background: #dcfce7; color: #15803d; }
.icon-amber { background: #fef3c7; color: #b45309; }
.icon-indigo { background: #e0e7ff; color: #4338ca; }

.kpi-info {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 2px;
}

/* Data Card & Filter Bar */
.data-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.card-filter-bar {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-wrap {
  position: relative;
  flex: 1;
  min-width: 280px;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 18px;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  background: #f8fafc;
  outline: none;
}

.search-input:focus {
  border-color: #5d3fd3;
  background: #fff;
}

.filters-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 12px;
  background: #fff;
  color: #334155;
  outline: none;
}

.btn-clear {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  font-size: 11px;
  color: #64748b;
  cursor: pointer;
}

.btn-clear:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* Table */
.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  color: #1e293b;
  vertical-align: middle;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: #f8fafc;
}

/* SSCC & Cells */
.sscc-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sscc-code {
  font-weight: 700;
  color: #5d3fd3;
  font-size: 13px;
}

.btn-copy-mini {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  padding: 2px;
  display: flex;
  align-items: center;
  border-radius: 4px;
}

.btn-copy-mini:hover {
  color: #5d3fd3;
  background: #f3e8ff;
}

.badge-nested {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  color: #64748b;
  font-family: monospace;
}

.linked-docs-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  font-weight: 600;
}

.doc-delivery {
  background: #ecfeff;
  color: #0891b2;
  border: 1px solid #cffafe;
}

.doc-order {
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #dbeafe;
}

.weight-cell {
  display: flex;
  flex-direction: column;
}

.contents-cell {
  display: flex;
  align-items: center;
}

.btn-contents-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  padding: 2px 8px;
  background: #f3e8ff;
  color: #7e22ce;
  border: 1px solid #e9d5ff;
  border-radius: 12px;
  font-size: 11px;
  cursor: pointer;
  font-weight: 500;
}

.btn-contents-pill:hover {
  background: #e9d5ff;
}

.action-buttons-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-purple { background: #f3e8ff; color: #7e22ce; }
.badge-blue { background: #dbeafe; color: #1d4ed8; }
.badge-teal { background: #ccfbf1; color: #0f766e; }
.badge-green { background: #dcfce7; color: #15803d; }
.badge-amber { background: #fef3c7; color: #b45309; }
.badge-disabled { background: #f1f5f9; color: #64748b; }

.badge-tare { background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }
.badge-box { background: #ecfeff; color: #155e75; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }
.badge-batch { background: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-family: monospace; }

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
}

.btn-primary:hover:not(:disabled) {
  background: #4a32b0;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #0284c7;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  background: #0369a1;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #fff;
  color: #475569;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-outline:hover:not(:disabled) {
  background: #f8fafc;
  color: #0f172a;
}

.btn-sm {
  padding: 5px 10px;
  font-size: 12px;
}

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
  color: #64748b;
}

.btn-icon:hover {
  background: #f1f5f9;
}

.btn-link-sm {
  background: none;
  border: none;
  color: #5d3fd3;
  cursor: pointer;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
}

.btn-link-sm:hover {
  text-decoration: underline;
}

/* Pagination */
.table-pagination {
  padding: 12px 20px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-page {
  width: 28px;
  height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #475569;
}

.btn-page:hover:not(:disabled) {
  background: #f8fafc;
}

.page-indicator {
  font-size: 12px;
  color: #475569;
  padding: 0 4px;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 48px;
  color: #94a3b8;
}

.empty-icon {
  font-size: 48px;
  color: #cbd5e1;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 16px;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 20px;
}

.modal-dialog {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 500px;
}

.modal-sm { max-width: 380px; }
.modal-md { max-width: 580px; }
.modal-lg { max-width: 820px; }

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
}

.btn-close:hover { color: #0f172a; }

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: #f8fafc;
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

/* Form Styles */
.form-group {
  display: flex;
  flex-direction: column;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
}

.form-control {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  color: #0f172a;
  outline: none;
}

.form-control:focus {
  border-color: #5d3fd3;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

/* GS1 Logistics Label Layout */
.gs1-label-sheet {
  border: 2px solid #000;
  background: #fff;
  padding: 16px;
  font-family: 'Arial', sans-serif;
  color: #000;
}

.label-top-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  border-bottom: 2px solid #000;
}

.label-box {
  padding: 8px 10px;
  border-right: 2px solid #000;
  font-size: 12px;
}

.label-box:last-child {
  border-right: none;
}

.box-label {
  font-size: 9px;
  font-weight: 800;
  color: #333;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.label-ref-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  border-bottom: 2px solid #000;
}

.label-middle-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  border-bottom: 2px solid #000;
}

.label-barcode-section {
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.primary-sscc-barcode-wrap {
  width: 100%;
  text-align: center;
}

.barcode-lines-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
}

.barcode-bars-dense {
  display: flex;
  height: 64px;
  align-items: stretch;
}

.barcode-bar-line {
  background: #000;
  display: inline-block;
}

.human-readable-sscc {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #000;
  margin-top: 4px;
}

.secondary-barcode-row {
  margin-bottom: 12px;
  text-align: center;
}

.barcode-simulation-sm {
  display: inline-block;
}

.barcode-lines {
  display: flex;
  height: 32px;
  align-items: stretch;
}

.bar {
  background: #000;
  margin-right: 2px;
}

.barcode-ai-text {
  font-size: 11px;
  font-weight: 700;
  margin-top: 2px;
}

/* Packaging Hierarchy Tree */
.hierarchy-summary-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
}

.hierarchy-tree-view {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tree-node-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.node-icon {
  margin-right: 8px;
}

.icon-pallet { color: #7e22ce; font-size: 22px; }
.icon-box { color: #0284c7; font-size: 18px; }

.node-info {
  flex: 1;
  display: flex;
  align-items: center;
}

.tree-children {
  margin-left: 24px;
  padding-left: 12px;
  border-left: 2px dashed #cbd5e1;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tree-level-box {
  margin-bottom: 6px;
}

.tree-children-items {
  margin-left: 24px;
  padding-left: 12px;
  border-left: 2px dashed #e2e8f0;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tree-node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
}

.item-details {
  display: flex;
  flex-direction: column;
  font-size: 12px;
}

.item-sub-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 2px;
}

.tree-node-empty {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
}

.raw-contents-section {
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}

.btn-accordion {
  background: none;
  border: none;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0;
}

.btn-accordion:hover { color: #0f172a; }

.raw-json-viewer {
  background: #0f172a;
  color: #38bdf8;
  padding: 12px;
  border-radius: 6px;
  font-size: 11px;
  margin-top: 8px;
  max-height: 200px;
  overflow-y: auto;
}

/* Quick Generator Preview Card */
.generated-preview-card {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 12px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

/* Status Modal */
.status-options-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.btn-status-option {
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
}

.btn-status-option:hover {
  background: #f8fafc;
}

.btn-status-option.active {
  border-color: #5d3fd3;
  background: #f3e8ff;
}

/* Print Styles */
@media print {
  body * {
    visibility: hidden;
  }
  #printable-gs1-label, #printable-gs1-label * {
    visibility: visible;
  }
  #printable-gs1-label {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
  }
}

/* Utilities */
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.mb-6 { margin-bottom: 24px; }
.mb-4 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 12px; }
.mb-2 { margin-bottom: 8px; }
.mt-4 { margin-top: 16px; }
.mt-1 { margin-top: 4px; }
.ml-1 { margin-left: 4px; }
.ml-2 { margin-left: 8px; }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }
.text-xs { font-size: 12px; }
.text-2xs { font-size: 11px; }
.text-3xs { font-size: 10px; }
.text-sm { font-size: 13px; }
.text-md { font-size: 14px; }
.text-lg { font-size: 16px; }
.text-xl { font-size: 20px; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-muted { color: #64748b; }
.text-dark { color: #0f172a; }
.text-primary { color: #5d3fd3; }
.text-purple { color: #7e22ce; }
.text-blue { color: #1d4ed8; }
.text-teal { color: #0f766e; }
.text-green { color: #16a34a; }
.text-amber { color: #d97706; }
.text-danger { color: #dc2626; }
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

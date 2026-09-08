<template>
  <div :dir="dir">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('preturn-title', 'Vendor Returns (RMA) & Debit Memos') }}</h1>
        <p class="page-subtitle">{{ t('preturn-sub', 'Manage supplier returns, RMA approval workflows, automated debit memo claims, and inventory quarantine') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-preturn', 'New Return (RMA)') }}
        </button>
      </div>
    </div>

    <!-- Navigation Hub -->
    <div class="nav-cards mb-6">
      <router-link to="/purchasing/requisitions" class="nav-card">
        <span class="material-symbols-outlined nav-icon">receipt_long</span>
        <span class="nav-label">{{ t('pr-title', 'Requisitions') }}</span>
      </router-link>
      <router-link to="/purchasing/rfqs" class="nav-card">
        <span class="material-symbols-outlined nav-icon">request_quote</span>
        <span class="nav-label">{{ t('rfq-title', 'RFQs') }}</span>
      </router-link>
      <router-link to="/purchasing" class="nav-card">
        <span class="material-symbols-outlined nav-icon">receipt</span>
        <span class="nav-label">{{ t('purchase-orders', 'Purchase Orders') }}</span>
      </router-link>
      <router-link to="/purchasing/goods-receipt" class="nav-card">
        <span class="material-symbols-outlined nav-icon">inventory_2</span>
        <span class="nav-label">{{ t('goods-receipt-title', 'Goods Receipt') }}</span>
      </router-link>
      <router-link to="/purchasing/returns" class="nav-card nav-card-active">
        <span class="material-symbols-outlined nav-icon">assignment_return</span>
        <span class="nav-label">{{ t('returns-title', 'Returns (RMA)') }}</span>
      </router-link>
      <router-link to="/purchasing/restock-suggestions" class="nav-card">
        <span class="material-symbols-outlined nav-icon">smart_toy</span>
        <span class="nav-label">{{ t('ai-restock', 'AI Restock') }}</span>
      </router-link>
    </div>

    <!-- Summary KPI Cards -->
    <div class="summary-grid mb-6">
      <div class="summary-card">
        <div class="summary-icon-wrap icon-total">
          <span class="material-symbols-outlined">assignment_return</span>
        </div>
        <div class="summary-content">
          <div class="summary-label">{{ t('rma-total-returns', 'Total RMAs') }}</div>
          <div class="summary-value">{{ stats.total }}</div>
          <div class="summary-hint">{{ t('rma-all-records', 'All logged returns') }}</div>
        </div>
      </div>

      <div class="summary-card" :class="{ 'card-highlight-amber': stats.draft > 0 }">
        <div class="summary-icon-wrap icon-draft">
          <span class="material-symbols-outlined">pending_actions</span>
        </div>
        <div class="summary-content">
          <div class="summary-label">{{ t('rma-pending-approval', 'Pending Approval') }}</div>
          <div class="summary-value">{{ stats.draft }}</div>
          <div class="summary-hint">{{ t('rma-draft-state', 'Draft awaiting sign-off') }}</div>
        </div>
      </div>

      <div class="summary-card" :class="{ 'card-highlight-blue': stats.approved > 0 }">
        <div class="summary-icon-wrap icon-approved">
          <span class="material-symbols-outlined">verified</span>
        </div>
        <div class="summary-content">
          <div class="summary-label">{{ t('rma-approved-quarantine', 'Approved & Quarantined') }}</div>
          <div class="summary-value">{{ stats.approved }}</div>
          <div class="summary-hint">{{ t('rma-awaiting-dispatch', 'Debit memo posted') }}</div>
        </div>
      </div>

      <div class="summary-card">
        <div class="summary-icon-wrap icon-completed">
          <span class="material-symbols-outlined">task_alt</span>
        </div>
        <div class="summary-content">
          <div class="summary-label">{{ t('rma-completed-returns', 'Completed') }}</div>
          <div class="summary-value">{{ stats.returned }}</div>
          <div class="summary-hint">{{ t('rma-returned-to-vendor', 'Dispatched to vendor') }}</div>
        </div>
      </div>

      <div class="summary-card summary-card-accent">
        <div class="summary-icon-wrap icon-money">
          <span class="material-symbols-outlined">account_balance_wallet</span>
        </div>
        <div class="summary-content">
          <div class="summary-label">{{ t('rma-total-claims-val', 'Total Debit Claims') }}</div>
          <div class="summary-value">${{ stats.totalClaimValue.toFixed(2) }}</div>
          <div class="summary-hint">{{ t('rma-recovered-credits', 'Supplier recovery value') }}</div>
        </div>
      </div>
    </div>

    <!-- Filter Toolbar & Search -->
    <div class="toolbar-card mb-4">
      <div class="filter-tabs">
        <button
          type="button"
          class="filter-tab"
          :class="{ active: activeTab === 'all' }"
          @click="activeTab = 'all'"
        >
          {{ t('all', 'All') }} ({{ items.length }})
        </button>
        <button
          type="button"
          class="filter-tab"
          :class="{ active: activeTab === 'Draft' }"
          @click="activeTab = 'Draft'"
        >
          {{ t('draft', 'Draft') }} ({{ stats.draft }})
        </button>
        <button
          type="button"
          class="filter-tab"
          :class="{ active: activeTab === 'Approved' }"
          @click="activeTab = 'Approved'"
        >
          {{ t('approved', 'Approved') }} ({{ stats.approved }})
        </button>
        <button
          type="button"
          class="filter-tab"
          :class="{ active: activeTab === 'Returned' }"
          @click="activeTab = 'Returned'"
        >
          {{ t('returned', 'Returned') }} ({{ stats.returned }})
        </button>
        <button
          type="button"
          class="filter-tab"
          :class="{ active: activeTab === 'Cancelled' }"
          @click="activeTab = 'Cancelled'"
        >
          {{ t('cancelled', 'Cancelled') }} ({{ stats.cancelled }})
        </button>
      </div>

      <div class="search-box">
        <span class="material-symbols-outlined search-icon">search</span>
        <input
          type="text"
          v-model="searchQuery"
          class="search-input"
          :placeholder="t('rma-search-placeholder', 'Search RMA #, supplier, PO, reason...')"
        />
        <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">
          <span class="material-symbols-outlined">cancel</span>
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filteredItems.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">assignment_return</span>
      <p v-if="searchQuery || activeTab !== 'all'">{{ t('no-matching-records', 'No purchase returns match your filter criteria.') }}</p>
      <p v-else>{{ t('no-records', 'No purchase return (RMA) records found.') }}</p>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ t('new-preturn', 'New Return (RMA)') }}
      </button>
    </div>

    <!-- RMA Data Table -->
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('rma-number', 'RMA / Return #') }}</th>
              <th>{{ t('supplier', 'Supplier') }}</th>
              <th>{{ t('reference-docs', 'Source Ref') }}</th>
              <th class="col-num">{{ t('total-amount', 'Claim Amount') }}</th>
              <th>{{ t('debit-memo', 'Debit Memo') }}</th>
              <th>{{ t('reason', 'Reason & Code') }}</th>
              <th>{{ t('return-date', 'Return Date') }}</th>
              <th class="text-center">{{ t('status', 'RMA Status') }}</th>
              <th class="text-center col-actions">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredItems" :key="item.id">
              <!-- RMA Number & Details Link -->
              <td class="cell-order">
                <a class="rma-link" @click="viewDetails(item)" :title="t('view-rma-details', 'View RMA details')">
                  {{ item.return_number }}
                </a>
              </td>

              <!-- Supplier Info -->
              <td>
                <div class="supplier-cell">
                  <span class="supplier-name">{{ supplierName(item.supplier_id) }}</span>
                  <span class="supplier-code">#SUP-{{ item.supplier_id }}</span>
                </div>
              </td>

              <!-- PO & GRN References -->
              <td>
                <div class="ref-badges">
                  <span v-if="item.purchase_order_id" class="ref-badge po-badge" :title="t('purchase-order', 'Purchase Order')">
                    <span class="material-symbols-outlined ref-icon">receipt</span>
                    {{ poNumber(item.purchase_order_id) }}
                  </span>
                  <span v-if="item.goods_receipt_id" class="ref-badge grn-badge" :title="t('goods-receipt', 'Goods Receipt')">
                    <span class="material-symbols-outlined ref-icon">inventory_2</span>
                    GRN #{{ item.goods_receipt_id }}
                  </span>
                  <span v-if="!item.purchase_order_id && !item.goods_receipt_id" class="text-muted text-xs">-</span>
                </div>
              </td>

              <!-- Total Claim Amount -->
              <td class="col-num">
                <strong class="amount-text">${{ (item.total_amount || 0).toFixed(2) }}</strong>
              </td>

              <!-- Debit Memo Link / Badge -->
              <td>
                <div v-if="item.debit_memo_id" class="debit-memo-link-wrap">
                  <router-link
                    :to="'/finance/' + item.debit_memo_id"
                    class="badge badge-debit-memo"
                    :title="t('view-linked-debit-memo', 'View posted supplier debit memo in Finance')"
                  >
                    <span class="material-symbols-outlined debit-icon">account_balance_wallet</span>
                    DM #{{ item.debit_memo_id }}
                  </router-link>
                </div>
                <span v-else-if="item.status === 'Draft'" class="text-muted text-xs italic">
                  {{ t('auto-on-approval', 'Auto on approval') }}
                </span>
                <span v-else class="text-muted text-xs">-</span>
              </td>

              <!-- Reason & Reason Code -->
              <td>
                <div class="reason-cell">
                  <span v-if="item.reason_code" class="reason-pill" :class="reasonCodeClass(item.reason_code)">
                    {{ formatReasonCode(item.reason_code) }}
                  </span>
                  <span class="reason-text" :title="item.reason || ''">
                    {{ item.reason || '-' }}
                  </span>
                </div>
              </td>

              <!-- Dates -->
              <td class="cell-mono">
                <div>{{ item.return_date }}</div>
                <div v-if="item.approved_at" class="text-xs text-muted">
                  {{ t('approved-on', 'Appr:') }} {{ formatDate(item.approved_at) }}
                </div>
              </td>

              <!-- Status Badge -->
              <td class="text-center">
                <span class="badge" :class="statusBadge(item.status)">
                  <span class="material-symbols-outlined status-dot-icon">
                    {{ statusIcon(item.status) }}
                  </span>
                  {{ item.status }}
                </span>
              </td>

              <!-- Actions Column -->
              <td class="text-center col-actions">
                <div class="action-buttons">
                  <!-- View Details -->
                  <button
                    class="btn-icon"
                    @click="viewDetails(item)"
                    :title="t('view-details', 'View RMA Details & Items')"
                    :aria-label="t('view-details', 'View Details')"
                  >
                    <span class="material-symbols-outlined">visibility</span>
                  </button>

                  <!-- Draft State: Quick Approve -->
                  <button
                    v-if="item.status === 'Draft'"
                    class="btn-icon btn-icon-approve"
                    @click="openApproveDialog(item)"
                    :title="t('approve-rma', 'Approve RMA (Auto-post Debit Memo & Quarantine Inventory)')"
                    :aria-label="t('approve-rma', 'Approve')"
                  >
                    <span class="material-symbols-outlined">check_circle</span>
                  </button>

                  <!-- Approved State: Complete Return -->
                  <button
                    v-if="item.status === 'Approved'"
                    class="btn-icon btn-icon-complete"
                    @click="completeReturn(item)"
                    :title="t('complete-return', 'Complete Return (Items Dispatched to Supplier)')"
                    :aria-label="t('complete-return', 'Complete Return')"
                  >
                    <span class="material-symbols-outlined">local_shipping</span>
                  </button>

                  <!-- Edit (Draft only) -->
                  <button
                    v-if="item.status === 'Draft'"
                    class="btn-icon"
                    @click="editItem(item)"
                    :title="t('edit', 'Edit RMA')"
                    :aria-label="t('edit', 'Edit')"
                  >
                    <span class="material-symbols-outlined">edit</span>
                  </button>

                  <!-- Cancel (Draft or Approved) -->
                  <button
                    v-if="item.status === 'Draft' || item.status === 'Approved'"
                    class="btn-icon btn-icon-warning"
                    @click="openCancelDialog(item)"
                    :title="t('cancel-rma', 'Cancel RMA')"
                    :aria-label="t('cancel-rma', 'Cancel RMA')"
                  >
                    <span class="material-symbols-outlined">block</span>
                  </button>

                  <!-- Delete (Draft only) -->
                  <button
                    v-if="item.status === 'Draft'"
                    class="btn-icon btn-icon-danger"
                    @click="deleteItem(item)"
                    :title="t('delete', 'Delete Draft RMA')"
                    :aria-label="t('delete', 'Delete')"
                  >
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- RMA Details Modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-header-icon">assignment_return</span>
            <div>
              <h3>{{ t('rma-details-title', 'Return Merchandise Authorization') }} — {{ selectedDetail?.return_number }}</h3>
              <p class="modal-subtitle">{{ t('rma-details-sub', 'Itemized return lines, debit memo link, and batch quarantine tracking') }}</p>
            </div>
          </div>
          <div class="modal-header-actions">
            <span class="badge" :class="statusBadge(selectedDetail?.status)">
              <span class="material-symbols-outlined status-dot-icon">{{ statusIcon(selectedDetail?.status) }}</span>
              {{ selectedDetail?.status }}
            </span>
            <button class="btn-icon" @click="closeDetailModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
          </div>
        </div>

        <div class="modal-body" v-if="loadingDetail">
          <div class="loading-wrap">
            <span class="material-symbols-outlined spinner">progress_activity</span>
            <span>{{ t('loading-details', 'Loading RMA details and line items...') }}</span>
          </div>
        </div>

        <div class="modal-body" v-else-if="selectedDetail">
          <!-- Overview Cards Grid -->
          <div class="detail-grid mb-6">
            <div class="detail-box">
              <span class="detail-box-label">{{ t('supplier', 'Supplier') }}</span>
              <span class="detail-box-value">{{ supplierName(selectedDetail.supplier_id) }}</span>
              <span class="text-xs text-muted">ID: #{{ selectedDetail.supplier_id }}</span>
            </div>

            <div class="detail-box">
              <span class="detail-box-label">{{ t('reference-docs', 'References') }}</span>
              <div class="detail-box-value-refs">
                <span v-if="selectedDetail.purchase_order_id" class="ref-badge po-badge">
                  PO: {{ selectedDetail.po_number || poNumber(selectedDetail.purchase_order_id) }}
                </span>
                <span v-if="selectedDetail.goods_receipt_id" class="ref-badge grn-badge">
                  GRN: {{ selectedDetail.grn_number || ('#' + selectedDetail.goods_receipt_id) }}
                </span>
                <span v-if="!selectedDetail.purchase_order_id && !selectedDetail.goods_receipt_id" class="text-muted">-</span>
              </div>
            </div>

            <div class="detail-box">
              <span class="detail-box-label">{{ t('debit-memo', 'Supplier Debit Memo') }}</span>
              <div v-if="selectedDetail.debit_memo_id">
                <router-link
                  :to="'/finance/' + selectedDetail.debit_memo_id"
                  class="badge badge-debit-memo"
                >
                  <span class="material-symbols-outlined debit-icon">account_balance_wallet</span>
                  {{ selectedDetail.debit_memo_number || ('DM #' + selectedDetail.debit_memo_id) }}
                </router-link>
              </div>
              <span v-else class="text-xs text-muted">{{ t('not-posted-yet', 'Not generated yet (posts on approval)') }}</span>
            </div>

            <div class="detail-box">
              <span class="detail-box-label">{{ t('total-amount', 'Total Claim Amount') }}</span>
              <span class="detail-box-value highlight-amount">${{ (selectedDetail.total_amount || 0).toFixed(2) }}</span>
              <span class="text-xs text-muted">{{ t('return-date', 'Date:') }} {{ selectedDetail.return_date }}</span>
            </div>
          </div>

          <!-- Approval Audit Info -->
          <div v-if="selectedDetail.approved_at" class="approval-notice mb-4">
            <span class="material-symbols-outlined notice-icon">verified</span>
            <div>
              <strong>{{ t('approved-by-label', 'Approved & Quarantined') }}:</strong>
              {{ selectedDetail.approved_by_name || ('User #' + selectedDetail.approved_by) }}
              on {{ formatDateTime(selectedDetail.approved_at) }}
            </div>
          </div>

          <!-- Reason & Notes -->
          <div class="info-callout mb-6" v-if="selectedDetail.reason || selectedDetail.notes">
            <div v-if="selectedDetail.reason">
              <strong>{{ t('rejection-reason', 'Rejection Reason') }}:</strong> {{ selectedDetail.reason }}
            </div>
            <div v-if="selectedDetail.notes" class="mt-1">
              <strong>{{ t('notes', 'Notes') }}:</strong> {{ selectedDetail.notes }}
            </div>
          </div>

          <!-- Itemized Return Lines Table -->
          <div class="section-header mb-2">
            <h4 class="section-title">
              <span class="material-symbols-outlined">list_alt</span>
              {{ t('itemized-return-lines', 'Itemized Return Lines & Batches') }} ({{ (selectedDetail.lines || []).length }})
            </h4>
          </div>

          <div class="table-wrap mb-6">
            <table class="data-table detail-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{{ t('product-name', 'Product Name') }}</th>
                  <th class="col-num">{{ t('quantity', 'Qty') }}</th>
                  <th class="col-num">{{ t('unit-price', 'Unit Price') }}</th>
                  <th class="col-num">{{ t('line-total', 'Line Total') }}</th>
                  <th>{{ t('batch-lot', 'Batch / Lot #') }}</th>
                  <th>{{ t('reason-code', 'Reason') }}</th>
                  <th>{{ t('quarantine-status', 'Quarantine Status') }}</th>
                  <th>{{ t('disposition', 'Disposition') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in (selectedDetail.lines || [])" :key="line.id || idx">
                  <td class="cell-mono">{{ line.line_number || (idx + 1) }}</td>
                  <td>
                    <strong>{{ line.product_name }}</strong>
                    <div v-if="line.product_id" class="text-xs text-muted">ID: #{{ line.product_id }}</div>
                  </td>
                  <td class="col-num font-mono">{{ line.qty }}</td>
                  <td class="col-num font-mono">${{ (line.unit_price || 0).toFixed(2) }}</td>
                  <td class="col-num font-mono"><strong>${{ (line.line_total || 0).toFixed(2) }}</strong></td>
                  <td>
                    <div v-if="line.batch_number" class="batch-tag">
                      <span class="material-symbols-outlined batch-icon">qr_code</span>
                      {{ line.batch_number }}
                      <span v-if="line.expiry_date" class="expiry-tag">Exp: {{ line.expiry_date }}</span>
                    </div>
                    <span v-else class="text-muted text-xs">-</span>
                  </td>
                  <td>
                    <span class="reason-pill" :class="reasonCodeClass(line.reason_code)">
                      {{ formatReasonCode(line.reason_code) }}
                    </span>
                  </td>
                  <td>
                    <span class="badge" :class="quarantineBadgeClass(line.quarantine_status)">
                      <span class="material-symbols-outlined status-dot-icon">
                        {{ line.quarantine_status === 'Quarantine' ? 'lock' : 'inventory_2' }}
                      </span>
                      {{ line.quarantine_status || 'Quarantine' }}
                    </span>
                  </td>
                  <td class="cell-mono text-xs">
                    {{ line.disposition || 'Return to Vendor' }}
                  </td>
                </tr>
                <tr v-if="!(selectedDetail.lines || []).length">
                  <td colspan="9" class="text-center text-muted py-4">
                    {{ t('no-lines-found', 'No line items attached to this return.') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Attachments / Inspection Photos Gallery Preview -->
          <div class="section-header mb-2" v-if="(selectedDetail.attachments || []).length">
            <h4 class="section-title">
              <span class="material-symbols-outlined">photo_library</span>
              {{ t('inspection-photos', 'Inspection Photos & Attachments') }} ({{ selectedDetail.attachments.length }})
            </h4>
          </div>

          <div class="photos-grid mb-4" v-if="(selectedDetail.attachments || []).length">
            <div v-for="att in selectedDetail.attachments" :key="att.id || att.filename" class="photo-thumb-card">
              <img
                v-if="att.url || att.thumbnail_url || att.data_base64"
                :src="att.url || att.thumbnail_url || (att.data_base64 ? `data:${att.content_type || 'image/jpeg'};base64,${att.data_base64}` : '')"
                :alt="att.filename || 'Inspection photo'"
                class="photo-img"
              />
              <div v-else class="photo-placeholder">
                <span class="material-symbols-outlined">image</span>
              </div>
              <div class="photo-caption">{{ att.filename || att.description || 'Photo' }}</div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <div class="footer-left">
            <!-- Workflow quick actions inside detail modal -->
            <button
              v-if="selectedDetail?.status === 'Draft'"
              class="btn-success"
              @click="closeDetailModal(); openApproveDialog(selectedDetail)"
            >
              <span class="material-symbols-outlined">check_circle</span>
              {{ t('approve-rma', 'Approve & Post Debit Memo') }}
            </button>
            <button
              v-if="selectedDetail?.status === 'Approved'"
              class="btn-primary"
              @click="closeDetailModal(); completeReturn(selectedDetail)"
            >
              <span class="material-symbols-outlined">local_shipping</span>
              {{ t('complete-return', 'Complete Return') }}
            </button>
          </div>
          <button class="btn-outline" @click="closeDetailModal">{{ t('close', 'Close') }}</button>
        </div>
      </div>
    </div>

    <!-- RMA Approval Confirmation Modal -->
    <div v-if="showApproveModal" class="modal-overlay" @click.self="showApproveModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-header-icon text-success">verified</span>
            <div>
              <h3>{{ t('approve-rma-title', 'Approve Purchase Return (RMA)') }}</h3>
              <p class="modal-subtitle">{{ targetRma?.return_number }} — {{ supplierName(targetRma?.supplier_id) }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="showApproveModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <div class="approval-explanation mb-4">
            <p>{{ t('rma-approve-info', 'Approving this RMA initiates the automated supplier debit recovery and inventory write-down workflow:') }}</p>
            <ul class="workflow-checklist">
              <li>
                <span class="material-symbols-outlined check-icon">check</span>
                <span><strong>{{ t('debit-memo-posting', 'Supplier Debit Memo (T0090)') }}:</strong> {{ t('debit-memo-posting-desc', 'Automatically generates a debit memo credited against supplier payables for') }} <strong>${{ (targetRma?.total_amount || 0).toFixed(2) }}</strong>.</span>
              </li>
              <li>
                <span class="material-symbols-outlined check-icon">check</span>
                <span><strong>{{ t('inventory-quarantine', 'Inventory Quarantine (T0088 / T0064)') }}:</strong> {{ t('inventory-quarantine-desc', 'Updates returned batch numbers to Quarantine status and writes down salable inventory.') }}</span>
              </li>
            </ul>
          </div>

          <div class="form-group mb-3">
            <label class="checkbox-label">
              <input type="checkbox" v-model="approveForm.create_debit_memo" />
              <span>{{ t('create-debit-memo-chk', 'Create and post Supplier Debit Memo in Accounting') }}</span>
            </label>
          </div>

          <div class="form-group mb-4">
            <label class="checkbox-label">
              <input type="checkbox" v-model="approveForm.quarantine_inventory" />
              <span>{{ t('quarantine-inventory-chk', 'Quarantine batch inventory & write down salable stock') }}</span>
            </label>
          </div>

          <div class="form-group">
            <label>{{ t('approval-notes', 'Approval Notes / Comments') }}</label>
            <textarea
              v-model="approveForm.notes"
              class="form-input"
              rows="2"
              :placeholder="t('approval-notes-placeholder', 'Optional approval instructions or notes...')"
            ></textarea>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-outline" @click="showApproveModal = false">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-success" :disabled="approving" @click="executeApprove">
            <span class="material-symbols-outlined">check_circle</span>
            {{ approving ? t('approving', 'Approving...') : t('confirm-approve', 'Confirm & Approve RMA') }}
          </button>
        </div>
      </div>
    </div>

    <!-- RMA Cancel Confirmation Modal -->
    <div v-if="showCancelModal" class="modal-overlay" @click.self="showCancelModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-header-icon text-warning">block</span>
            <div>
              <h3>{{ t('cancel-rma-title', 'Cancel Purchase Return (RMA)') }}</h3>
              <p class="modal-subtitle">{{ targetRma?.return_number }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="showCancelModal = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <p class="text-secondary mb-4">
            {{ t('cancel-rma-confirm-msg', 'Are you sure you want to cancel this return authorization? This will halt the return workflow.') }}
          </p>
          <div class="form-group">
            <label>{{ t('cancellation-reason', 'Reason for Cancellation') }} <span class="required">*</span></label>
            <textarea
              v-model="cancelReason"
              class="form-input"
              rows="3"
              required
              :placeholder="t('cancellation-reason-placeholder', 'Explain why this RMA is being cancelled...')"
            ></textarea>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-outline" @click="showCancelModal = false">{{ t('back', 'Back') }}</button>
          <button class="btn-danger" :disabled="cancelling || !cancelReason.trim()" @click="executeCancel">
            {{ cancelling ? t('cancelling', 'Cancelling...') : t('confirm-cancel', 'Cancel RMA') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Comprehensive RMA Creation & Editing Modal (Multi-line, Batch Selector, Unit Price, & Photo Uploader) -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content modal-xl">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-header-icon text-primary">assignment_return</span>
            <div>
              <h3>{{ editing ? t('edit-preturn', 'Edit Purchase Return (RMA)') : t('new-preturn', 'New Purchase Return (RMA)') }}</h3>
              <p class="modal-subtitle">{{ t('rma-form-sub', 'Itemized return authorization, supplier debit claim, batch quarantine & inspection photos') }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <!-- Section 1: Header Information & Reference Documents -->
          <div class="form-section-card mb-6">
            <div class="form-section-title">
              <span class="material-symbols-outlined section-icon">description</span>
              <span>{{ t('rma-header-info', '1. Return Header & References') }}</span>
            </div>

            <div class="form-grid-4">
              <div class="form-group">
                <label>{{ t('return-number', 'RMA / Return #') }}</label>
                <input
                  type="text"
                  v-model="form.return_number"
                  class="form-input font-mono"
                  maxlength="30"
                  :placeholder="t('auto-generated-if-blank', 'Auto-generated if blank')"
                />
              </div>

              <div class="form-group">
                <label>{{ t('supplier', 'Supplier') }} <span class="required">*</span></label>
                <select v-model="form.supplier_id" required class="form-input" @change="onSupplierChange">
                  <option value="">-- {{ t('select-supplier', 'Select Supplier') }} --</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name || s.company_name }} (#{{ s.id }})</option>
                </select>
              </div>

              <div class="form-group">
                <label>{{ t('purchase-order', 'Source Purchase Order') }}</label>
                <select v-model="form.purchase_order_id" class="form-input">
                  <option value="">-- {{ t('none-standalone', 'None / Standalone') }} --</option>
                  <option v-for="o in filteredOrders" :key="o.id" :value="o.id">
                    {{ o.order_number || ('PO #' + o.id) }} ({{ supplierName(o.supplier_id) }})
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>{{ t('goods-receipt', 'Goods Receipt (GRN)') }}</label>
                <div class="grn-select-wrap">
                  <select v-model="form.goods_receipt_id" class="form-input" @change="onGrnChange">
                    <option value="">-- {{ t('none', 'None') }} --</option>
                    <option v-for="g in filteredGoodsReceipts" :key="g.id" :value="g.id">
                      GRN #{{ g.id }} - {{ g.receipt_number || g.receipt_date || '' }}
                    </option>
                  </select>
                  <button
                    v-if="form.goods_receipt_id"
                    type="button"
                    class="btn-sm btn-outline btn-import-grn"
                    @click="importLinesFromGRN(form.goods_receipt_id)"
                    :title="t('import-grn-items', 'Import all items from this Goods Receipt')"
                  >
                    <span class="material-symbols-outlined icon-xs">download</span> {{ t('import-grn', 'Import GRN') }}
                  </button>
                </div>
              </div>
            </div>

            <div class="form-grid-3 mt-3">
              <div class="form-group">
                <label>{{ t('return-date', 'Return Date') }} <span class="required">*</span></label>
                <input type="date" v-model="form.return_date" required class="form-input font-mono" />
              </div>

              <div class="form-group">
                <label>{{ t('rejection-reason', 'Overall Reason / Summary') }}</label>
                <input
                  type="text"
                  v-model="form.reason"
                  class="form-input"
                  :placeholder="t('reason-placeholder', 'e.g. Temperature excursion during transit, damaged pallets')"
                />
              </div>

              <div class="form-group">
                <label>{{ t('claim-amount-preview', 'Calculated Claim Total ($)') }}</label>
                <div class="calculated-total-box font-mono">
                  <span class="total-currency">$</span>
                  <span class="total-val">{{ totalLinesAmount.toFixed(2) }}</span>
                  <span class="total-badge">{{ form.lines.length }} {{ t('lines-unit', 'lines') }}</span>
                </div>
              </div>
            </div>

            <div class="form-group mt-3">
              <label>{{ t('notes', 'Inspection Notes & Driver / Dock Observations') }}</label>
              <textarea
                v-model="form.notes"
                class="form-input"
                rows="2"
                :placeholder="t('notes-placeholder', 'Additional notes regarding dock inspection, supplier notification, carrier bill of lading, or disposal...')"
              ></textarea>
            </div>
          </div>

          <!-- Section 2: Multi-line Item Entry & Batch Selector -->
          <div class="form-section-card mb-6">
            <div class="lines-section-header">
              <div class="form-section-title">
                <span class="material-symbols-outlined section-icon">list_alt</span>
                <span>{{ t('itemized-return-lines', '2. Itemized Return Lines & Batches') }}</span>
                <span class="badge badge-subtle">{{ form.lines.length }} {{ t('items', 'items') }}</span>
              </div>
              <div class="lines-actions">
                <button
                  type="button"
                  class="btn-outline btn-sm"
                  @click="generateAllBatches"
                  :title="t('gen-all-batches-title', 'Auto-generate batch/lot numbers for lines missing one')"
                >
                  <span class="material-symbols-outlined icon-xs">qr_code_2</span> {{ t('auto-batches', 'Auto Batch') }}
                </button>
                <button
                  type="button"
                  class="btn-primary btn-sm"
                  @click="addLine"
                >
                  <span class="material-symbols-outlined icon-xs">add</span> {{ t('add-return-item', 'Add Return Item') }}
                </button>
              </div>
            </div>

            <!-- Empty lines state -->
            <div v-if="!form.lines.length" class="empty-lines-box">
              <span class="material-symbols-outlined empty-lines-icon">playlist_add</span>
              <p>{{ t('no-lines-in-rma', 'No items added to this return authorization yet.') }}</p>
              <div class="flex gap-2 justify-center mt-2">
                <button type="button" class="btn-primary btn-sm" @click="addLine">
                  <span class="material-symbols-outlined icon-xs">add</span> {{ t('add-line', 'Add Item') }}
                </button>
                <button
                  v-if="form.goods_receipt_id"
                  type="button"
                  class="btn-outline btn-sm"
                  @click="importLinesFromGRN(form.goods_receipt_id)"
                >
                  <span class="material-symbols-outlined icon-xs">download</span> {{ t('import-from-grn', 'Import from Selected GRN') }}
                </button>
              </div>
            </div>

            <!-- Lines Table Editor -->
            <div v-else class="lines-editor-wrap">
              <table class="lines-editor-table">
                <thead>
                  <tr>
                    <th class="w-8">#</th>
                    <th style="width: 22%">{{ t('product', 'Product') }} <span class="required">*</span></th>
                    <th style="width: 18%">{{ t('batch-lot', 'Batch / Lot #') }}</th>
                    <th style="width: 11%">{{ t('exp-date', 'Expiry Date') }}</th>
                    <th style="width: 9%" class="col-num">{{ t('qty', 'Qty') }} <span class="required">*</span></th>
                    <th style="width: 10%" class="col-num">{{ t('unit-price', 'Unit Price ($)') }}</th>
                    <th style="width: 10%" class="col-num">{{ t('line-total', 'Total ($)') }}</th>
                    <th style="width: 14%">{{ t('reason-code', 'Reason Code') }}</th>
                    <th style="width: 12%">{{ t('disposition', 'Disposition') }}</th>
                    <th class="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, idx) in form.lines" :key="line.id || idx" class="line-row">
                    <td class="cell-mono text-center">{{ idx + 1 }}</td>

                    <!-- Product Selector -->
                    <td>
                      <div class="product-input-cell">
                        <select
                          v-model="line.product_id"
                          class="form-input form-input-sm"
                          @change="onProductSelect(line)"
                        >
                          <option value="">-- {{ t('select-product', 'Select Product') }} --</option>
                          <option v-for="p in products" :key="p.id" :value="p.id">
                            {{ p.name || p.sku }} ({{ p.sku ? p.sku + ' - ' : '' }}#{{ p.id }})
                          </option>
                        </select>
                        <input
                          v-if="!line.product_id"
                          type="text"
                          v-model="line.product_name"
                          class="form-input form-input-xs mt-1"
                          :placeholder="t('or-custom-product-name', 'Or type custom item name...')"
                        />
                      </div>
                    </td>

                    <!-- Batch / Lot Selector -->
                    <td>
                      <div class="batch-input-cell">
                        <div class="batch-flex-row">
                          <input
                            type="text"
                            v-model="line.batch_number"
                            class="form-input form-input-sm font-mono batch-text-input"
                            :placeholder="t('lot-batch-placeholder', 'e.g. LOT-2026-001')"
                            @change="onManualBatchInput(line)"
                          />
                          <button
                            type="button"
                            class="btn-gen-batch"
                            @click="generateBatchForLine(line, idx)"
                            :title="t('auto-gen-batch', 'Auto-generate lot number')"
                          >
                            <span class="material-symbols-outlined icon-xs">autorenew</span>
                          </button>
                        </div>
                        <!-- Quick batch suggestion dropdown if product has registered batches -->
                        <div v-if="getBatchesForProduct(line.product_id).length" class="batch-suggestions">
                          <select
                            class="form-input form-input-xs batch-quick-select"
                            @change="e => onBatchOptionSelect(line, e.target.value)"
                          >
                            <option value="">-- {{ t('pick-registered-batch', 'Pick from inventory batches') }} --</option>
                            <option
                              v-for="b in getBatchesForProduct(line.product_id)"
                              :key="b.id"
                              :value="b.id"
                            >
                              {{ b.batch_number }} (Qty: {{ b.quantity || 0 }}, Exp: {{ b.expiry_date || 'N/A' }})
                            </option>
                          </select>
                        </div>
                      </div>
                    </td>

                    <!-- Expiration Date -->
                    <td>
                      <input
                        type="date"
                        v-model="line.expiry_date"
                        class="form-input form-input-sm font-mono"
                        :title="t('expiry-date', 'Expiration Date')"
                      />
                    </td>

                    <!-- Quantity -->
                    <td>
                      <input
                        type="number"
                        step="any"
                        min="0.01"
                        v-model.number="line.qty"
                        class="form-input form-input-sm col-num font-mono font-bold"
                        placeholder="1"
                        required
                      />
                    </td>

                    <!-- Unit Price ($) -->
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        v-model.number="line.unit_price"
                        class="form-input form-input-sm col-num font-mono"
                        placeholder="0.00"
                      />
                    </td>

                    <!-- Line Total ($) -->
                    <td class="col-num font-mono font-bold line-total-cell">
                      ${{ ((Number(line.qty) || 0) * (Number(line.unit_price) || 0)).toFixed(2) }}
                    </td>

                    <!-- Reason Code -->
                    <td>
                      <select v-model="line.reason_code" class="form-input form-input-sm reason-select">
                        <option v-for="rc in REASON_CODES" :key="rc.value" :value="rc.value">
                          {{ rc.label }}
                        </option>
                      </select>
                    </td>

                    <!-- Disposition -->
                    <td>
                      <select v-model="line.disposition" class="form-input form-input-sm disposition-select">
                        <option v-for="disp in DISPOSITIONS" :key="disp.value" :value="disp.value">
                          {{ disp.label }}
                        </option>
                      </select>
                    </td>

                    <!-- Remove Button -->
                    <td class="text-center">
                      <button
                        type="button"
                        class="btn-icon btn-icon-danger"
                        @click="removeLine(idx)"
                        :title="t('remove-line', 'Remove line item')"
                      >
                        <span class="material-symbols-outlined">delete</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr class="editor-summary-row">
                    <td colspan="4" class="text-right font-bold text-secondary">
                      {{ t('total-items-qty', 'Total Items & Claim:') }}
                    </td>
                    <td class="col-num font-mono font-bold">
                      {{ totalLinesQty }}
                    </td>
                    <td></td>
                    <td class="col-num font-mono font-bold text-primary highlight-claim">
                      ${{ totalLinesAmount.toFixed(2) }}
                    </td>
                    <td colspan="3"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <!-- Section 3: Inspection Photos & Attachment Uploader -->
          <div class="form-section-card">
            <div class="photos-section-header">
              <div class="form-section-title">
                <span class="material-symbols-outlined section-icon">photo_camera</span>
                <span>{{ t('inspection-photos-title', '3. Inspection Photos & Evidence') }}</span>
                <span class="badge badge-subtle">{{ (form.attachments || []).length }} {{ t('photos', 'photos') }}</span>
              </div>
              <div class="flex gap-2">
                <label class="btn-outline btn-sm file-upload-btn">
                  <span class="material-symbols-outlined icon-xs">upload_file</span>
                  {{ t('upload-photos', 'Upload Image Files') }}
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    class="hidden-file-input"
                    @change="handleFileUpload"
                  />
                </label>
              </div>
            </div>

            <p class="section-desc mb-3">
              {{ t('photos-instructions', 'Upload clear inspection photos of damaged cartons, broken seals, expired date stamps, or temperature logs for supplier recovery proof.') }}
            </p>

            <!-- URL direct entry bar -->
            <div class="url-input-bar mb-4">
              <input
                type="text"
                v-model="newPhotoUrl"
                class="form-input form-input-sm flex-1"
                :placeholder="t('paste-photo-url', 'Or paste image URL (https://...)...')"
                @keydown.enter.prevent="addPhotoByUrl"
              />
              <input
                type="text"
                v-model="newPhotoDesc"
                class="form-input form-input-sm photo-desc-input"
                :placeholder="t('caption-placeholder', 'Caption (e.g. Broken pallet dock 4)')"
                @keydown.enter.prevent="addPhotoByUrl"
              />
              <button
                type="button"
                class="btn-outline btn-sm"
                :disabled="!newPhotoUrl.trim()"
                @click="addPhotoByUrl"
              >
                <span class="material-symbols-outlined icon-xs">add_link</span> {{ t('add-url', 'Add URL') }}
              </button>
            </div>

            <!-- Uploaded Photos Grid Preview -->
            <div v-if="(form.attachments || []).length" class="photos-upload-grid">
              <div
                v-for="(att, pIdx) in form.attachments"
                :key="att.id || pIdx"
                class="photo-edit-card"
              >
                <div class="photo-preview-wrap">
                  <img
                    v-if="att.url || att.thumbnail_url || att.data_base64"
                    :src="att.url || att.thumbnail_url || (att.data_base64 ? `data:${att.content_type || 'image/jpeg'};base64,${att.data_base64}` : '')"
                    :alt="att.filename || 'Evidence Photo'"
                    class="photo-thumb-img"
                  />
                  <div v-else class="photo-no-preview">
                    <span class="material-symbols-outlined">broken_image</span>
                  </div>
                  <button
                    type="button"
                    class="photo-remove-btn"
                    @click="removeAttachment(pIdx)"
                    :title="t('remove-photo', 'Remove photo')"
                  >
                    <span class="material-symbols-outlined icon-xs">close</span>
                  </button>
                </div>
                <div class="photo-info-wrap">
                  <span class="photo-filename" :title="att.filename">{{ att.filename || ('Photo #' + (pIdx + 1)) }}</span>
                  <input
                    type="text"
                    v-model="att.description"
                    class="form-input form-input-xs photo-caption-input"
                    :placeholder="t('photo-notes', 'Notes / observation...')"
                  />
                </div>
              </div>
            </div>

            <div v-else class="no-photos-box">
              <span class="material-symbols-outlined icon-muted">add_photo_alternate</span>
              <p class="text-xs text-muted">{{ t('no-photos-yet', 'No inspection photos attached yet.') }}</p>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="modal-footer">
          <div class="modal-footer-summary">
            <div class="claim-summary-pill">
              <span class="summary-pill-label">{{ t('total-claim-summary', 'Total Claim Recovery:') }}</span>
              <strong class="summary-pill-val font-mono">${{ totalLinesAmount.toFixed(2) }}</strong>
              <span class="summary-pill-sub">({{ form.lines.length }} {{ t('items', 'items') }})</span>
            </div>
          </div>

          <div class="modal-footer-btns">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button
              class="btn-primary"
              :disabled="saving || !form.supplier_id || !form.lines.length"
              @click="saveItem"
            >
              <span v-if="saving" class="material-symbols-outlined spinner">progress_activity</span>
              <span v-else class="material-symbols-outlined">save</span>
              {{ saving ? t('saving', 'Saving...') : (editing ? t('update-rma', 'Update RMA') : t('create-rma', 'Save & Create RMA')) }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Dialog for Deletion -->
    <ConfirmDialog
      v-if="confirmTarget"
      :title="t('confirm-delete-rma', 'Delete Draft RMA?')"
      :message="t('confirm-delete-msg', 'Are you sure you want to delete RMA') + ' ' + confirmTarget.return_number + '?'"
      @confirm="executeDelete"
      @cancel="confirmTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

// Predefined RMA Reason Codes with friendly labels
const REASON_CODES = [
  { value: 'damaged', label: 'Damaged in Transit / Unloading', color: 'pill-danger' },
  { value: 'expired', label: 'Expired / Short-Dated Stock', color: 'pill-warning' },
  { value: 'rejected', label: 'Receiving Dock Rejection', color: 'pill-danger' },
  { value: 'wrong_item', label: 'Wrong Item / Specification', color: 'pill-info' },
  { value: 'qc_failed', label: 'QC Inspection Failed', color: 'pill-danger' },
  { value: 'defective', label: 'Defective / Spoiled Quality', color: 'pill-warning' },
  { value: 'over_delivery', label: 'Over Delivery / Excess', color: 'pill-neutral' },
  { value: 'other', label: 'Other Rejection Reason', color: 'pill-neutral' },
]

const DISPOSITIONS = [
  { value: 'Return to Vendor', label: 'Return to Vendor' },
  { value: 'Scrap', label: 'Scrap & Write-Off' },
  { value: 'Supplier Credit', label: 'Supplier Credit Only' },
  { value: 'Replacement', label: 'Request Replacement' },
]

const loading = ref(true)
const error = ref('')
const items = ref([])
const suppliers = ref([])
const orders = ref([])
const goodsReceipts = ref([])
const goodsReceiptLines = ref([])
const products = ref([])
const batches = ref([])

// Filters & Tabs
const activeTab = ref('all')
const searchQuery = ref('')

// Modals state
const showModal = ref(false)
const editing = ref(false)
const editId = ref(null)
const saving = ref(false)
const deletedLineIds = ref([])

const showDetailModal = ref(false)
const loadingDetail = ref(false)
const selectedDetail = ref(null)

const showApproveModal = ref(false)
const approving = ref(false)
const targetRma = ref(null)
const approveForm = ref({
  create_debit_memo: true,
  quarantine_inventory: true,
  notes: '',
})

const showCancelModal = ref(false)
const cancelling = ref(false)
const cancelReason = ref('')

const confirmTarget = ref(null)

// Direct photo URL input
const newPhotoUrl = ref('')
const newPhotoDesc = ref('')

// Form data for comprehensive RMA header & lines
const form = ref({
  return_number: '',
  supplier_id: '',
  purchase_order_id: '',
  goods_receipt_id: '',
  return_date: '',
  status: 'Draft',
  total_amount: 0,
  reason: '',
  notes: '',
  lines: [],
  attachments: [],
})

// KPI Computations
const stats = computed(() => {
  const all = items.value || []
  const total = all.length
  const draft = all.filter(i => i.status === 'Draft').length
  const approved = all.filter(i => i.status === 'Approved').length
  const returned = all.filter(i => i.status === 'Returned' || i.status === 'Received').length
  const cancelled = all.filter(i => i.status === 'Cancelled').length
  const totalClaimValue = all
    .filter(i => i.status !== 'Cancelled')
    .reduce((sum, i) => sum + (Number(i.total_amount) || 0), 0)

  return { total, draft, approved, returned, cancelled, totalClaimValue }
})

// Filtered items list for main table
const filteredItems = computed(() => {
  let list = items.value || []

  if (activeTab.value !== 'all') {
    if (activeTab.value === 'Returned') {
      list = list.filter(i => i.status === 'Returned' || i.status === 'Received')
    } else {
      list = list.filter(i => i.status === activeTab.value)
    }
  }

  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(i => {
      const num = (i.return_number || '').toLowerCase()
      const sName = supplierName(i.supplier_id).toLowerCase()
      const poNum = poNumber(i.purchase_order_id).toLowerCase()
      const reason = (i.reason || '').toLowerCase()
      const reasonCode = (i.reason_code || '').toLowerCase()
      const dmId = String(i.debit_memo_id || '')
      return num.includes(q) || sName.includes(q) || poNum.includes(q) || reason.includes(q) || reasonCode.includes(q) || dmId.includes(q)
    })
  }

  return list
})

// Filter POs by selected supplier in modal
const filteredOrders = computed(() => {
  if (!form.value.supplier_id) return orders.value || []
  return (orders.value || []).filter(o => o.supplier_id === Number(form.value.supplier_id))
})

// Filter Goods Receipts by selected supplier or selected PO
const filteredGoodsReceipts = computed(() => {
  let list = goodsReceipts.value || []
  if (form.value.supplier_id) {
    list = list.filter(g => !g.supplier_id || g.supplier_id === Number(form.value.supplier_id))
  }
  if (form.value.purchase_order_id) {
    list = list.filter(g => !g.purchase_order_id || g.purchase_order_id === Number(form.value.purchase_order_id))
  }
  return list
})

// Dynamic total claim amount calculated from lines sum
const totalLinesAmount = computed(() => {
  if (!form.value.lines || !form.value.lines.length) return 0
  return form.value.lines.reduce((sum, line) => {
    const qty = Number(line.qty) || 0
    const price = Number(line.unit_price) || 0
    return sum + (qty * price)
  }, 0)
})

// Total quantity summed across lines
const totalLinesQty = computed(() => {
  if (!form.value.lines || !form.value.lines.length) return 0
  return form.value.lines.reduce((sum, line) => sum + (Number(line.qty) || 0), 0)
})

function statusBadge(status) {
  const map = {
    Draft: 'badge-warning',
    Approved: 'badge-info',
    Returned: 'badge-active',
    Received: 'badge-active',
    Cancelled: 'badge-inactive',
  }
  return map[status] || 'badge-inactive'
}

function statusIcon(status) {
  const map = {
    Draft: 'pending',
    Approved: 'verified',
    Returned: 'task_alt',
    Received: 'task_alt',
    Cancelled: 'cancel',
  }
  return map[status] || 'help'
}

function reasonCodeClass(code) {
  const map = {
    damaged: 'pill-danger',
    expired: 'pill-warning',
    rejected: 'pill-danger',
    wrong_item: 'pill-info',
    qc_failed: 'pill-danger',
    defective: 'pill-warning',
    over_delivery: 'pill-neutral',
    other: 'pill-neutral',
  }
  return map[code] || 'pill-neutral'
}

function quarantineBadgeClass(status) {
  const map = {
    Quarantine: 'badge-warning',
    Released: 'badge-active',
    Scrapped: 'badge-danger',
  }
  return map[status] || 'badge-warning'
}

function formatReasonCode(code) {
  if (!code) return ''
  return code.replace(/_/g, ' ').toUpperCase()
}

function supplierName(id) {
  if (!id) return '-'
  const s = suppliers.value.find(x => x.id === id)
  return s ? (s.name || s.company_name) : `Supplier #${id}`
}

function poNumber(id) {
  if (!id) return '-'
  const o = orders.value.find(x => x.id === id)
  return o ? (o.order_number || `PO #${id}`) : `PO #${id}`
}

function today() {
  return new Date().toISOString().split('T')[0]
}

function formatDate(val) {
  if (!val) return ''
  try {
    return new Date(val).toLocaleDateString()
  } catch {
    return String(val)
  }
}

function formatDateTime(val) {
  if (!val) return ''
  try {
    return new Date(val).toLocaleString()
  } catch {
    return String(val)
  }
}

function getBatchesForProduct(productId) {
  if (!productId) return []
  return (batches.value || []).filter(b => b.product_id === Number(productId))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [retRes, supRes, ordRes, grnRes, grnLineRes, prodRes, batchRes] = await Promise.all([
      api.get('/T0081I/'),
      api.get('/T0011I/').catch(() => api.get('/T0103I/').catch(() => ({ data: [] }))),
      api.get('/T0014I/').catch(() => ({ data: [] })),
      api.get('/T0075I/').catch(() => ({ data: [] })),
      api.get('/T0076I/').catch(() => ({ data: [] })),
      api.get('/T0003I/').catch(() => ({ data: [] })),
      api.get('/T0088I/').catch(() => ({ data: [] })),
    ])
    items.value = retRes.data || []
    suppliers.value = supRes.data || []
    orders.value = ordRes.data || []
    goodsReceipts.value = grnRes.data || []
    goodsReceiptLines.value = grnLineRes.data || []
    products.value = prodRes.data || []
    batches.value = batchRes.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load purchase returns data')
  } finally {
    loading.value = false
  }
}

async function viewDetails(item) {
  selectedDetail.value = item
  showDetailModal.value = true
  loadingDetail.value = true
  try {
    const res = await api.get(`/T0081I/${item.id}/details`)
    selectedDetail.value = res.data || item
  } catch {
    selectedDetail.value = item
  } finally {
    loadingDetail.value = false
  }
}

function closeDetailModal() {
  showDetailModal.value = false
  selectedDetail.value = null
}

function onSupplierChange() {
  // If selected PO does not belong to new supplier, reset it
  if (form.value.purchase_order_id) {
    const po = orders.value.find(o => o.id === Number(form.value.purchase_order_id))
    if (po && form.value.supplier_id && po.supplier_id !== Number(form.value.supplier_id)) {
      form.value.purchase_order_id = ''
    }
  }
  // Reset GRN if supplier does not match
  if (form.value.goods_receipt_id) {
    const grn = goodsReceipts.value.find(g => g.id === Number(form.value.goods_receipt_id))
    if (grn && form.value.supplier_id && grn.supplier_id && grn.supplier_id !== Number(form.value.supplier_id)) {
      form.value.goods_receipt_id = ''
    }
  }
}

function onGrnChange() {
  const grnId = form.value.goods_receipt_id
  if (!grnId) return
  const grn = goodsReceipts.value.find(g => g.id === Number(grnId))
  if (grn) {
    if (grn.supplier_id && !form.value.supplier_id) {
      form.value.supplier_id = grn.supplier_id
    }
    if (grn.purchase_order_id && !form.value.purchase_order_id) {
      form.value.purchase_order_id = grn.purchase_order_id
    }
  }
}

// 1-Click Import Line Items from Goods Receipt
function importLinesFromGRN(grnId) {
  if (!grnId) return
  const grn = goodsReceipts.value.find(g => g.id === Number(grnId))
  if (grn && grn.supplier_id) {
    form.value.supplier_id = grn.supplier_id
  }
  if (grn && grn.purchase_order_id) {
    form.value.purchase_order_id = grn.purchase_order_id
  }

  const matchingLines = (goodsReceiptLines.value || []).filter(l => l.receipt_id === Number(grnId))
  if (!matchingLines.length) {
    toast(t('no-grn-lines-found', 'No line items found for Goods Receipt #' + grnId), 'info')
    return
  }

  const newLines = matchingLines.map(gl => {
    const prod = products.value.find(p => p.id === gl.product_id)
    const unitPrice = prod ? (prod.cost_price || prod.price || 0) : 0
    return {
      product_id: gl.product_id || '',
      product_name: gl.product_name || (prod ? (prod.name || prod.sku) : `Product #${gl.product_id}`),
      batch_number: gl.batch_number || '',
      batch_id: null,
      expiry_date: gl.expiry_date ? gl.expiry_date.slice(0, 10) : '',
      qty: Number(gl.qty_received) || Number(gl.qty_ordered) || 1,
      unit_price: Number(unitPrice) || 0,
      reason_code: 'rejected',
      disposition: 'Return to Vendor',
      quarantine_status: 'Quarantine',
    }
  })

  // Append or replace if only 1 empty line
  if (form.value.lines.length === 1 && !form.value.lines[0].product_id && !form.value.lines[0].product_name) {
    form.value.lines = newLines
  } else {
    form.value.lines = [...form.value.lines, ...newLines]
  }

  toast(t('imported-grn-lines-success', `Imported ${newLines.length} item(s) from GRN #${grnId}`), 'success')
}

function addLine() {
  form.value.lines.push({
    product_id: '',
    product_name: '',
    batch_number: '',
    batch_id: null,
    expiry_date: '',
    qty: 1,
    unit_price: 0,
    reason_code: 'damaged',
    disposition: 'Return to Vendor',
    quarantine_status: 'Quarantine',
  })
}

function removeLine(idx) {
  const line = form.value.lines[idx]
  if (line && line.id) {
    deletedLineIds.value.push(line.id)
  }
  form.value.lines.splice(idx, 1)
}

function onProductSelect(line) {
  if (!line.product_id) return
  const p = products.value.find(x => x.id === Number(line.product_id))
  if (p) {
    line.product_name = p.name || p.sku || `Product #${p.id}`
    if (!line.unit_price || line.unit_price === 0) {
      line.unit_price = Number(p.cost_price || p.price || 0)
    }
  }

  // Check if batches exist for this product and pre-fill if none set
  const prodBatches = getBatchesForProduct(line.product_id)
  if (prodBatches.length && !line.batch_number) {
    const firstBatch = prodBatches[0]
    line.batch_number = firstBatch.batch_number
    line.batch_id = firstBatch.id
    if (firstBatch.expiry_date) {
      line.expiry_date = firstBatch.expiry_date.slice(0, 10)
    }
  }
}

function onBatchOptionSelect(line, batchId) {
  if (!batchId) return
  const b = batches.value.find(x => x.id === Number(batchId))
  if (b) {
    line.batch_id = b.id
    line.batch_number = b.batch_number
    if (b.expiry_date) {
      line.expiry_date = b.expiry_date.slice(0, 10)
    }
    if (b.product_id && !line.product_id) {
      line.product_id = b.product_id
      onProductSelect(line)
    }
  }
}

function onManualBatchInput(line) {
  if (!line.batch_number) {
    line.batch_id = null
    return
  }
  // Try to find matching registered batch
  const matched = (batches.value || []).find(b => b.batch_number && b.batch_number.trim().toLowerCase() === line.batch_number.trim().toLowerCase())
  if (matched) {
    line.batch_id = matched.id
    if (!line.expiry_date && matched.expiry_date) {
      line.expiry_date = matched.expiry_date.slice(0, 10)
    }
  }
}

function generateBatchForLine(line, idx) {
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const seq = String((idx !== undefined ? idx : form.value.lines.indexOf(line)) + 1).padStart(3, '0')
  line.batch_number = `LOT-${d}-${seq}`
  line.batch_id = null
}

function generateAllBatches() {
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  form.value.lines.forEach((line, idx) => {
    if (!line.batch_number || !line.batch_number.trim()) {
      const seq = String(idx + 1).padStart(3, '0')
      line.batch_number = `LOT-${d}-${seq}`
      line.batch_id = null
    }
  })
}

// Inspection Photo Upload via File input (FileReader Base64)
function handleFileUpload(e) {
  const files = e.target?.files
  if (!files || !files.length) return

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const reader = new FileReader()
    reader.onload = (event) => {
      const result = event.target?.result
      if (!result) return
      const base64Data = result.split(',')[1] || result
      form.value.attachments.push({
        id: `att_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        filename: file.name,
        content_type: file.type || 'image/jpeg',
        size_bytes: file.size,
        data_base64: base64Data,
        description: '',
      })
    }
    reader.readAsDataURL(file)
  }

  // Reset file input
  e.target.value = ''
}

function addPhotoByUrl() {
  if (!newPhotoUrl.value.trim()) return
  form.value.attachments.push({
    id: `att_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    filename: newPhotoUrl.value.split('/').pop() || 'web_photo.jpg',
    url: newPhotoUrl.value.trim(),
    content_type: 'image/jpeg',
    description: newPhotoDesc.value.trim() || '',
  })
  newPhotoUrl.value = ''
  newPhotoDesc.value = ''
}

function removeAttachment(idx) {
  form.value.attachments.splice(idx, 1)
}

function openAdd() {
  editing.value = false
  editId.value = null
  deletedLineIds.value = []
  newPhotoUrl.value = ''
  newPhotoDesc.value = ''

  const dateCode = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const randSeq = Math.floor(100 + Math.random() * 900)

  form.value = {
    return_number: `RMA-${dateCode}-${randSeq}`,
    supplier_id: '',
    purchase_order_id: '',
    goods_receipt_id: '',
    return_date: today(),
    status: 'Draft',
    total_amount: 0,
    reason: '',
    notes: '',
    lines: [
      {
        product_id: '',
        product_name: '',
        batch_number: '',
        batch_id: null,
        expiry_date: '',
        qty: 1,
        unit_price: 0,
        reason_code: 'damaged',
        disposition: 'Return to Vendor',
        quarantine_status: 'Quarantine',
      }
    ],
    attachments: [],
  }
  showModal.value = true
}

async function editItem(item) {
  editing.value = true
  editId.value = item.id
  deletedLineIds.value = []
  newPhotoUrl.value = ''
  newPhotoDesc.value = ''

  try {
    // Load full details including existing line items and attachments
    const res = await api.get(`/T0081I/${item.id}/details`)
    const full = res.data || item

    const loadedLines = (full.lines || []).map((l, idx) => ({
      id: l.id,
      product_id: l.product_id || '',
      product_name: l.product_name || '',
      batch_number: l.batch_number || '',
      batch_id: l.batch_id || null,
      expiry_date: l.expiry_date ? l.expiry_date.slice(0, 10) : '',
      qty: Number(l.qty) || 1,
      unit_price: Number(l.unit_price) || 0,
      reason_code: l.reason_code || 'damaged',
      disposition: l.disposition || 'Return to Vendor',
      quarantine_status: l.quarantine_status || 'Quarantine',
      line_number: l.line_number || idx + 1,
    }))

    form.value = {
      return_number: full.return_number || item.return_number,
      supplier_id: full.supplier_id || item.supplier_id,
      purchase_order_id: full.purchase_order_id || item.purchase_order_id || '',
      goods_receipt_id: full.goods_receipt_id || item.goods_receipt_id || '',
      return_date: full.return_date || item.return_date || today(),
      status: full.status || item.status || 'Draft',
      total_amount: Number(full.total_amount) || Number(item.total_amount) || 0,
      reason: full.reason || item.reason || '',
      notes: full.notes || item.notes || '',
      lines: loadedLines.length ? loadedLines : [
        {
          product_id: '',
          product_name: '',
          batch_number: '',
          batch_id: null,
          expiry_date: '',
          qty: 1,
          unit_price: 0,
          reason_code: 'damaged',
          disposition: 'Return to Vendor',
          quarantine_status: 'Quarantine',
        }
      ],
      attachments: Array.isArray(full.attachments) ? [...full.attachments] : [],
    }
  } catch {
    // Fallback if details endpoint fails
    form.value = {
      return_number: item.return_number,
      supplier_id: item.supplier_id,
      purchase_order_id: item.purchase_order_id || '',
      goods_receipt_id: item.goods_receipt_id || '',
      return_date: item.return_date || today(),
      status: item.status || 'Draft',
      total_amount: item.total_amount || 0,
      reason: item.reason || '',
      notes: item.notes || '',
      lines: [
        {
          product_id: '',
          product_name: '',
          batch_number: '',
          batch_id: null,
          expiry_date: '',
          qty: 1,
          unit_price: 0,
          reason_code: 'damaged',
          disposition: 'Return to Vendor',
          quarantine_status: 'Quarantine',
        }
      ],
      attachments: Array.isArray(item.attachments) ? [...item.attachments] : [],
    }
  }

  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  if (!form.value.supplier_id) {
    toast(t('supplier-required', 'Supplier is required'), 'error')
    return
  }

  // Filter valid lines (must have product selected or product_name typed)
  const validLines = (form.value.lines || []).filter(l => l.product_id || (l.product_name && l.product_name.trim()))
  if (!validLines.length) {
    toast(t('at-least-one-line-item', 'At least one line item is required for RMA authorization'), 'error')
    return
  }

  saving.value = true
  try {
    const finalTotal = totalLinesAmount.value

    const headerPayload = {
      return_number: form.value.return_number ? form.value.return_number.trim() : null,
      supplier_id: Number(form.value.supplier_id),
      purchase_order_id: form.value.purchase_order_id ? Number(form.value.purchase_order_id) : null,
      goods_receipt_id: form.value.goods_receipt_id ? Number(form.value.goods_receipt_id) : null,
      return_date: form.value.return_date || today(),
      status: form.value.status || 'Draft',
      total_amount: finalTotal,
      reason: form.value.reason || null,
      notes: form.value.notes || null,
      attachments: form.value.attachments || [],
    }

    if (editing.value) {
      // 1. Update RMA Header
      await api.put(`/T0081I/${editId.value}`, headerPayload)

      // 2. Delete removed line items
      for (const lineId of deletedLineIds.value) {
        await api.delete(`/T0082I/${lineId}`).catch(() => {})
      }

      // 3. Update or create line items
      for (let i = 0; i < validLines.length; i++) {
        const l = validLines[i]
        const linePayload = {
          return_id: editId.value,
          product_id: l.product_id ? Number(l.product_id) : null,
          product_name: l.product_name || (products.value.find(p => p.id === Number(l.product_id))?.name || `Product #${l.product_id}`),
          qty: Number(l.qty) || 1,
          unit_price: Number(l.unit_price) || 0,
          batch_number: l.batch_number ? l.batch_number.trim() : null,
          batch_id: l.batch_id ? Number(l.batch_id) : null,
          expiry_date: l.expiry_date || null,
          reason_code: l.reason_code || 'damaged',
          disposition: l.disposition || 'Return to Vendor',
          quarantine_status: l.quarantine_status || 'Quarantine',
          line_number: i + 1,
        }

        if (l.id) {
          await api.put(`/T0082I/${l.id}`, linePayload)
        } else {
          await api.post('/T0082I/', linePayload)
        }
      }

      toast(t('rma-updated', 'RMA updated successfully with all lines and attachments'), 'success')
    } else {
      // Create new RMA
      const res = await api.post('/T0081I/', headerPayload)
      const newRmaId = res.data?.id

      if (newRmaId && validLines.length) {
        const linesPayload = validLines.map((l, i) => ({
          return_id: newRmaId,
          product_id: l.product_id ? Number(l.product_id) : null,
          product_name: l.product_name || (products.value.find(p => p.id === Number(l.product_id))?.name || `Product #${l.product_id}`),
          qty: Number(l.qty) || 1,
          unit_price: Number(l.unit_price) || 0,
          batch_number: l.batch_number ? l.batch_number.trim() : null,
          batch_id: l.batch_id ? Number(l.batch_id) : null,
          expiry_date: l.expiry_date || null,
          reason_code: l.reason_code || 'damaged',
          disposition: l.disposition || 'Return to Vendor',
          quarantine_status: l.quarantine_status || 'Quarantine',
          line_number: i + 1,
        }))

        await api.post('/T0082I/bulk', {
          return_id: newRmaId,
          lines: linesPayload,
        })
      }

      toast(t('rma-created', 'Purchase Return (RMA) created successfully'), 'success')
    }

    closeModal()
    await load()
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-save', 'Failed to save RMA')
    toast(msg, 'error')
  } finally {
    saving.value = false
  }
}

function openApproveDialog(item) {
  targetRma.value = item
  approveForm.value = {
    create_debit_memo: true,
    quarantine_inventory: true,
    notes: '',
  }
  showApproveModal.value = true
}

async function executeApprove() {
  if (!targetRma.value) return
  approving.value = true
  try {
    const payload = {
      create_debit_memo: approveForm.value.create_debit_memo,
      quarantine_inventory: approveForm.value.quarantine_inventory,
      notes: approveForm.value.notes || null,
    }
    await api.post(`/T0081I/${targetRma.value.id}/approve`, payload)
    toast(t('rma-approved-success', 'RMA approved. Debit memo posted & inventory quarantined.'), 'success')
    showApproveModal.value = false
    targetRma.value = null
    await load()
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-approve', 'Failed to approve RMA')
    toast(msg, 'error')
  } finally {
    approving.value = false
  }
}

async function completeReturn(item) {
  try {
    await api.post(`/T0081I/${item.id}/complete-return`)
    toast(t('rma-completed-success', 'Return completed. Stock movements finalized.'), 'success')
    await load()
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-action', 'Failed to complete return')
    toast(msg, 'error')
  }
}

function openCancelDialog(item) {
  targetRma.value = item
  cancelReason.value = ''
  showCancelModal.value = true
}

async function executeCancel() {
  if (!targetRma.value) return
  cancelling.value = true
  try {
    await api.post(`/T0081I/${targetRma.value.id}/cancel`, {
      reason: cancelReason.value,
    })
    toast(t('rma-cancelled-success', 'RMA has been cancelled'), 'success')
    showCancelModal.value = false
    targetRma.value = null
    await load()
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-cancel', 'Failed to cancel RMA')
    toast(msg, 'error')
  } finally {
    cancelling.value = false
  }
}

function deleteItem(item) {
  confirmTarget.value = item
}

async function executeDelete() {
  const item = confirmTarget.value
  confirmTarget.value = null
  if (!item) return
  try {
    await api.delete(`/T0081I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast(t('deleted', 'RMA deleted successfully'), 'success')
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-delete', 'Failed to delete RMA')
    toast(msg, 'error')
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
/* Page Layout */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-actions { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

/* Navigation Hub Cards */
.nav-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.nav-card { display: flex; flex-direction: column; align-items: center; gap: 6px; text-decoration: none; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 16px 10px; transition: all 0.15s; color: var(--text-secondary); }
.nav-card:hover { border-color: var(--color-primary); background: var(--bg-surface-hover); color: var(--color-primary); }
.nav-card-active { border-color: var(--color-primary); background: #f0eeff; color: var(--color-primary); }
.nav-card-active .nav-label { font-weight: 700; }
.nav-icon { font-size: 26px; }
.nav-label { font-size: 12px; font-weight: 600; text-align: center; }

/* Summary KPI Cards */
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.summary-card { display: flex; align-items: center; gap: 14px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 16px; transition: transform 0.15s, box-shadow 0.15s; }
.summary-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-1px); }
.summary-card-accent { border-color: #c7d2fe; background: linear-gradient(135deg, var(--bg-surface) 0%, #f5f3ff 100%); }
.card-highlight-amber { border-color: #fde68a; }
.card-highlight-blue { border-color: #bae6fd; }

.summary-icon-wrap { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.summary-icon-wrap .material-symbols-outlined { font-size: 24px; }
.icon-total { background: #f3f4f6; color: #4b5563; }
.icon-draft { background: #fef3c7; color: #d97706; }
.icon-approved { background: #e0f2fe; color: #0284c7; }
.icon-completed { background: #dcfce7; color: #16a34a; }
.icon-money { background: #ede9fe; color: #7c3aed; }

.summary-content { display: flex; flex-direction: column; overflow: hidden; }
.summary-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.summary-value { font-size: 22px; font-weight: 700; color: var(--text-primary); margin-top: 2px; }
.summary-hint { font-size: 11px; color: var(--text-subtle); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Filter Toolbar */
.toolbar-card { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 10px 14px; }
.filter-tabs { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.filter-tab { background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; transition: all 0.15s; }
.filter-tab:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.filter-tab.active { background: var(--color-primary); color: #fff; }

.search-box { display: flex; align-items: center; gap: 6px; background: var(--bg-surface-low); border: 1px solid var(--border-input); border-radius: 8px; padding: 4px 10px; min-width: 260px; }
.search-icon { font-size: 18px; color: var(--text-muted); }
.search-input { border: none; background: transparent; font-size: 12px; color: var(--text-primary); outline: none; width: 100%; }
.clear-btn { background: none; border: none; padding: 0; cursor: pointer; color: var(--text-subtle); display: flex; }
.clear-btn:hover { color: var(--text-primary); }
.clear-btn .material-symbols-outlined { font-size: 16px; }

/* Table and Cards */
.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); vertical-align: middle; }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }

.cell-order { font-family: monospace; font-weight: 700; white-space: nowrap; }
.cell-mono { font-family: monospace; font-size: 12px; }
.col-num { text-align: right; }
.col-actions { width: 140px; text-align: center; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-xs { font-size: 11px; }
.text-muted { color: var(--text-muted); }
.text-secondary { color: var(--text-secondary); }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.italic { font-style: italic; }

.rma-link { color: var(--color-primary); cursor: pointer; text-decoration: none; font-weight: 700; }
.rma-link:hover { text-decoration: underline; }

.supplier-cell { display: flex; flex-direction: column; gap: 2px; }
.supplier-name { font-weight: 600; color: var(--text-primary); }
.supplier-code { font-size: 11px; font-family: monospace; color: var(--text-muted); }

.ref-badges { display: flex; flex-direction: column; gap: 4px; }
.ref-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-family: monospace; padding: 2px 6px; border-radius: 4px; font-weight: 600; width: fit-content; }
.po-badge { background: #f3f4f6; color: #374151; }
.grn-badge { background: #eef2ff; color: #4338ca; }
.ref-icon { font-size: 14px; }

.amount-text { font-size: 13px; color: var(--text-primary); }

.debit-memo-link-wrap { display: inline-flex; }
.badge-debit-memo { display: inline-flex; align-items: center; gap: 4px; background: #ede9fe; color: #6d28d9; padding: 3px 8px; border-radius: 6px; font-family: monospace; font-weight: 600; font-size: 11px; text-decoration: none; transition: background 0.15s; }
.badge-debit-memo:hover { background: #ddd6fe; }
.debit-icon { font-size: 14px; }

.reason-cell { display: flex; flex-direction: column; gap: 4px; max-width: 180px; }
.reason-text { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.reason-pill { display: inline-block; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px; width: fit-content; text-transform: uppercase; letter-spacing: 0.3px; }
.pill-danger { background: #fee2e2; color: #b91c1c; }
.pill-warning { background: #fef3c7; color: #b45309; }
.pill-info { background: #e0f2fe; color: #0369a1; }
.pill-neutral { background: #f3f4f6; color: #4b5563; }

.batch-tag { display: inline-flex; align-items: center; gap: 4px; font-family: monospace; font-size: 11px; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
.batch-icon { font-size: 14px; color: var(--text-muted); }
.expiry-tag { font-size: 10px; color: #b45309; margin-left: 4px; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }
.badge-subtle { background: #f3f4f6; color: #4b5563; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
.status-dot-icon { font-size: 14px; }

/* Action Buttons */
.action-buttons { display: inline-flex; align-items: center; gap: 2px; }
.btn-icon { background: none; border: none; padding: 5px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); display: inline-flex; align-items: center; justify-content: center; transition: all 0.15s; }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.btn-icon-approve:hover { background: #dcfce7; color: #16a34a; }
.btn-icon-complete:hover { background: #e0f2fe; color: #0284c7; }
.btn-icon-warning:hover { background: #fef3c7; color: #d97706; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: var(--color-primary); color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-success { display: inline-flex; align-items: center; gap: 6px; background: #16a34a; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-success:hover { background: #15803d; }
.btn-success:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: #dc2626; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--text-primary); padding: 8px 18px; border: 1px solid var(--border-default); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover); }
.btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-sm { padding: 5px 12px; font-size: 12px; border-radius: 6px; }
.icon-xs { font-size: 16px; }

/* Empty state */
.empty-state { text-align: center; padding: 48px; color: var(--text-faint); font-size: 14px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 16px; display: block; }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 620px; max-width: 95vw; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: flex; flex-direction: column; }
.modal-lg { width: 900px; }
.modal-xl { width: 1100px; max-width: 96vw; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); }
.modal-title-wrap { display: flex; align-items: center; gap: 10px; }
.modal-header-icon { font-size: 26px; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-subtitle { font-size: 12px; color: var(--text-muted); margin: 2px 0 0 0; }
.modal-header-actions { display: flex; align-items: center; gap: 10px; }
.modal-body { padding: 24px; flex: 1; overflow-y: auto; }
.modal-footer { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-top: 1px solid var(--border-default); background: var(--bg-surface-low); }
.modal-footer-btns { display: flex; align-items: center; gap: 10px; }
.footer-left { display: flex; align-items: center; gap: 8px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

/* Form Sections */
.form-section-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 18px; }
.form-section-title { font-size: 14px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.section-icon { font-size: 20px; color: var(--color-primary); }
.section-desc { font-size: 12px; color: var(--text-muted); margin: 4px 0 0 0; }

.form-grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 14px; }
.form-grid-3 { display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 0; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
.form-input-sm { padding: 5px 8px; font-size: 12px; }
.form-input-xs { padding: 3px 6px; font-size: 11px; }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }
.text-primary { color: var(--color-primary); }
.text-success { color: #16a34a; }
.text-warning { color: #d97706; }

.grn-select-wrap { display: flex; gap: 6px; align-items: center; }
.btn-import-grn { white-space: nowrap; }

.calculated-total-box { display: flex; align-items: center; gap: 4px; background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe; border-radius: 6px; padding: 7px 12px; font-weight: 700; height: 36px; box-sizing: border-box; }
.total-currency { font-size: 13px; opacity: 0.8; }
.total-val { font-size: 16px; }
.total-badge { margin-left: auto; font-size: 11px; background: rgba(109, 40, 217, 0.12); padding: 2px 6px; border-radius: 4px; font-family: sans-serif; font-weight: 600; }

.checkbox-label { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; cursor: pointer; user-select: none; }
.checkbox-label input[type="checkbox"] { width: 16px; height: 16px; cursor: pointer; accent-color: var(--color-primary); }

/* Lines Editor Specifics */
.lines-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.lines-actions { display: flex; align-items: center; gap: 8px; }
.empty-lines-box { text-align: center; padding: 32px 16px; background: var(--bg-surface-low); border: 1px dashed var(--border-default); border-radius: 8px; color: var(--text-muted); font-size: 13px; }
.empty-lines-icon { font-size: 36px; color: var(--border-default); margin-bottom: 8px; display: block; }

.lines-editor-wrap { overflow-x: auto; border: 1px solid var(--border-default); border-radius: 8px; background: var(--bg-surface); }
.lines-editor-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.lines-editor-table th { background: var(--bg-surface-low); padding: 8px 10px; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; border-bottom: 1px solid var(--border-default); text-align: left; white-space: nowrap; }
.lines-editor-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-light); vertical-align: top; }
.line-row:hover { background: var(--bg-surface-hover); }

.batch-input-cell { display: flex; flex-direction: column; gap: 4px; }
.batch-flex-row { display: flex; align-items: center; gap: 4px; }
.batch-text-input { font-size: 11px; }
.btn-gen-batch { background: var(--bg-surface-low); border: 1px solid var(--border-input); border-radius: 4px; padding: 4px 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-muted); transition: all 0.15s; }
.btn-gen-batch:hover { color: var(--color-primary); border-color: var(--color-primary); background: var(--bg-surface-hover); }
.batch-quick-select { font-size: 10px; color: var(--text-secondary); }

.line-total-cell { padding-top: 10px !important; font-size: 13px; color: var(--text-primary); }
.editor-summary-row td { background: var(--bg-surface-low); padding: 10px 10px; border-top: 2px solid var(--border-default); border-bottom: none; font-size: 13px; }
.highlight-claim { font-size: 15px; }

/* Photos Uploader Specifics */
.photos-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.hidden-file-input { display: none; }
.file-upload-btn { cursor: pointer; user-select: none; }

.url-input-bar { display: flex; gap: 8px; align-items: center; }
.photo-desc-input { max-width: 280px; }

.photos-upload-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-top: 10px; }
.photo-edit-card { border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; background: var(--bg-surface); display: flex; flex-direction: column; }
.photo-preview-wrap { position: relative; height: 110px; background: var(--bg-surface-low); overflow: hidden; }
.photo-thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.photo-no-preview { height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-muted); }
.photo-remove-btn { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,0.65); color: #fff; border: none; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.15s; }
.photo-remove-btn:hover { background: #dc2626; }
.photo-info-wrap { padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.photo-filename { font-size: 11px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.no-photos-box { text-align: center; padding: 20px; background: var(--bg-surface-low); border: 1px dashed var(--border-light); border-radius: 8px; }
.icon-muted { font-size: 28px; color: var(--border-default); margin-bottom: 4px; display: block; }

.claim-summary-pill { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-surface); border: 1px solid var(--border-default); padding: 6px 14px; border-radius: 8px; font-size: 13px; }
.summary-pill-label { color: var(--text-muted); font-size: 12px; }
.summary-pill-val { font-size: 16px; color: var(--color-primary); }
.summary-pill-sub { font-size: 11px; color: var(--text-muted); }

/* Detail Modal Specifics */
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.detail-box { background: var(--bg-surface-low); border: 1px solid var(--border-light); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 3px; }
.detail-box-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
.detail-box-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.highlight-amount { font-size: 18px; color: var(--color-primary); font-family: monospace; }
.detail-box-value-refs { display: flex; flex-direction: column; gap: 4px; }

.approval-notice { display: flex; align-items: center; gap: 10px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #166534; }
.notice-icon { font-size: 20px; color: #16a34a; flex-shrink: 0; }

.info-callout { background: var(--bg-surface-low); border-left: 3px solid var(--color-primary); border-radius: 4px; padding: 10px 14px; font-size: 13px; color: var(--text-secondary); }

.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-title { font-size: 13px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 6px; margin: 0; }
.section-title .material-symbols-outlined { font-size: 18px; color: var(--color-primary); }

.detail-table th { font-size: 10px; padding: 8px 10px; }
.detail-table td { padding: 8px 10px; font-size: 12px; }

.workflow-checklist { list-style: none; padding: 0; margin: 10px 0 0 0; display: flex; flex-direction: column; gap: 8px; }
.workflow-checklist li { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
.check-icon { font-size: 16px; color: #16a34a; margin-top: 1px; flex-shrink: 0; }

.approval-explanation { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; font-size: 13px; }

.photos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
.photo-thumb-card { border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; background: var(--bg-surface); }
.photo-img { width: 100%; height: 80px; object-fit: cover; display: block; }
.photo-placeholder { height: 80px; display: flex; align-items: center; justify-content: center; background: var(--bg-surface-low); color: var(--text-muted); }
.photo-caption { font-size: 11px; padding: 4px 6px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.loading-wrap { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 40px; color: var(--text-muted); font-size: 13px; }
.spinner { animation: spin 1s linear infinite; font-size: 20px; color: var(--color-primary); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.py-4 { padding-top: 16px; padding-bottom: 16px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.gap-2 { gap: 8px; }
.justify-between { justify-content: space-between; }
.justify-center { justify-content: center; }
.items-center { align-items: center; }

[dir="rtl"] .data-table th,
[dir="rtl"] .lines-editor-table th { text-align: right; }
[dir="rtl"] .data-table td,
[dir="rtl"] .lines-editor-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .info-callout { border-left: none; border-right: 3px solid var(--color-primary); }
[dir="rtl"] .total-badge { margin-left: 0; margin-right: auto; }
</style>

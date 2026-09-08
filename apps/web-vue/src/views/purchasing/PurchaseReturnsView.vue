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

    <!-- Create / Edit RMA Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <span class="material-symbols-outlined modal-header-icon">edit_document</span>
            <div>
              <h3>{{ editing ? t('edit-preturn', 'Edit Purchase Return (RMA)') : t('new-preturn', 'New Purchase Return (RMA)') }}</h3>
              <p class="modal-subtitle">{{ t('rma-form-sub', 'Log supplier return details for dock-side or warehouse inspection') }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <div class="form-row">
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
              <select v-model="form.supplier_id" required class="form-input">
                <option value="">-- {{ t('select-supplier', 'Select Supplier') }} --</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }} (#{{ s.id }})</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('purchase-order', 'Purchase Order') }}</label>
              <select v-model="form.purchase_order_id" class="form-input">
                <option value="">-- {{ t('none-standalone', 'None / Standalone') }} --</option>
                <option v-for="o in orders" :key="o.id" :value="o.id">{{ o.order_number }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('goods-receipt', 'Goods Receipt (GRN)') }}</label>
              <select v-model="form.goods_receipt_id" class="form-input">
                <option value="">-- {{ t('none', 'None') }} --</option>
                <option v-for="g in goodsReceipts" :key="g.id" :value="g.id">GRN #{{ g.id }} - {{ g.receipt_number || g.date || '' }}</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('return-date', 'Return Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.return_date" required class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('total-amount', 'Claim Amount ($)') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.total_amount" class="form-input font-mono" />
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('reason', 'Rejection / Return Reason') }}</label>
            <input
              type="text"
              v-model="form.reason"
              class="form-input"
              :placeholder="t('reason-placeholder', 'e.g. Damaged crates during unloading, temperature excursion')"
            />
          </div>

          <div class="form-group">
            <label>{{ t('notes', 'Inspection Notes & Observations') }}</label>
            <textarea
              v-model="form.notes"
              class="form-input"
              rows="3"
              :placeholder="t('notes-placeholder', 'Additional notes regarding driver departure, credit agreement, or lot disposition...')"
            ></textarea>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving || !form.supplier_id" @click="saveItem">
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save Return') }}
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

const loading = ref(true)
const error = ref('')
const items = ref([])
const suppliers = ref([])
const orders = ref([])
const goodsReceipts = ref([])

// Filters & Tabs
const activeTab = ref('all')
const searchQuery = ref('')

// Modals state
const showModal = ref(false)
const editing = ref(false)
const editId = ref(null)
const saving = ref(false)

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

// Form data for RMA header
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

// Filtered items list
const filteredItems = computed(() => {
  let list = items.value || []

  // Tab filter
  if (activeTab.value !== 'all') {
    if (activeTab.value === 'Returned') {
      list = list.filter(i => i.status === 'Returned' || i.status === 'Received')
    } else {
      list = list.filter(i => i.status === activeTab.value)
    }
  }

  // Search filter
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
  return s ? s.name : `Supplier #${id}`
}

function poNumber(id) {
  if (!id) return '-'
  const o = orders.value.find(x => x.id === id)
  return o ? o.order_number : `PO #${id}`
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

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [retRes, supRes, ordRes, grnRes] = await Promise.all([
      api.get('/T0081I/'),
      api.get('/T0011I/'),
      api.get('/T0014I/'),
      api.get('/T0075I/').catch(() => ({ data: [] })),
    ])
    items.value = retRes.data || []
    suppliers.value = supRes.data || []
    orders.value = ordRes.data || []
    goodsReceipts.value = grnRes.data || []
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
    // fallback to item
    selectedDetail.value = item
  } finally {
    loadingDetail.value = false
  }
}

function closeDetailModal() {
  showDetailModal.value = false
  selectedDetail.value = null
}

function openAdd() {
  editing.value = false
  editId.value = null
  form.value = {
    return_number: '',
    supplier_id: '',
    purchase_order_id: '',
    goods_receipt_id: '',
    return_date: today(),
    status: 'Draft',
    total_amount: 0,
    reason: '',
    notes: '',
  }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
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
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      supplier_id: Number(form.value.supplier_id),
      purchase_order_id: form.value.purchase_order_id ? Number(form.value.purchase_order_id) : null,
      goods_receipt_id: form.value.goods_receipt_id ? Number(form.value.goods_receipt_id) : null,
      total_amount: Number(form.value.total_amount) || 0,
      notes: form.value.notes || null,
      reason: form.value.reason || null,
      return_number: form.value.return_number ? form.value.return_number.trim() : null,
    }

    if (editing.value) {
      await api.put(`/T0081I/${editId.value}`, payload)
      toast(t('rma-updated', 'RMA updated successfully'), 'success')
    } else {
      await api.post('/T0081I/', payload)
      toast(t('rma-created', 'RMA created successfully'), 'success')
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
.text-xs { font-size: 11px; }
.text-muted { color: var(--text-muted); }
.text-secondary { color: var(--text-secondary); }
.font-mono { font-family: monospace; }
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

/* Empty state */
.empty-state { text-align: center; padding: 48px; color: var(--text-faint); font-size: 14px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 16px; display: block; }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 92vw; max-height: 88vh; overflow-y: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: flex; flex-direction: column; }
.modal-lg { width: 880px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); }
.modal-title-wrap { display: flex; align-items: center; gap: 10px; }
.modal-header-icon { font-size: 26px; color: var(--color-primary); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-subtitle { font-size: 12px; color: var(--text-muted); margin: 2px 0 0 0; }
.modal-header-actions { display: flex; align-items: center; gap: 10px; }
.modal-body { padding: 24px; flex: 1; }
.modal-footer { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-top: 1px solid var(--border-default); background: var(--bg-surface-low); }
.footer-left { display: flex; align-items: center; gap: 8px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

/* Forms */
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }
.text-success { color: #16a34a; }
.text-warning { color: #d97706; }

.checkbox-label { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; cursor: pointer; user-select: none; }
.checkbox-label input[type="checkbox"] { width: 16px; height: 16px; cursor: pointer; accent-color: var(--color-primary); }

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

.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-1 { margin-top: 4px; }
.py-4 { padding-top: 16px; padding-bottom: 16px; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .info-callout { border-left: none; border-right: 3px solid var(--color-primary); }
</style>


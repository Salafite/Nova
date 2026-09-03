<template>
  <div :dir="dir" class="stock-transfer-detail-view">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="loadData(true)" />

    <template v-else-if="transfer">
      <!-- Top Navigation & Action Header -->
      <div class="top-nav-row">
        <button class="btn-link" @click="router.push('/warehouse/transfers')">
          <span class="material-symbols-outlined icon-xs">arrow_back</span>
          {{ t('back-to-transfers', 'Back to Transfers') }}
        </button>
      </div>

      <div class="page-header">
        <div class="header-left">
          <div class="title-status-wrap">
            <h1 class="page-title font-mono">{{ transfer.transfer_number || `#TRF-${transfer.id}` }}</h1>
            <span class="badge" :class="statusBadgeClass(transfer.status)">
              <span class="material-symbols-outlined icon-xs">{{ statusIcon(transfer.status) }}</span>
              {{ transfer.status }}
            </span>
          </div>

          <div class="route-subtitle">
            <span class="wh-pill origin-pill" :title="transfer.source_warehouse_name">
              <span class="material-symbols-outlined icon-xs">warehouse</span>
              {{ transfer.source_warehouse_name || getWarehouseName(transfer.source_warehouse_id) }}
            </span>
            <span class="material-symbols-outlined route-arrow">arrow_forward</span>
            <span class="wh-pill dest-pill" :title="transfer.destination_warehouse_name">
              <span class="material-symbols-outlined icon-xs">domain</span>
              {{ transfer.destination_warehouse_name || getWarehouseName(transfer.destination_warehouse_id) }}
            </span>
          </div>
        </div>

        <!-- Header Actions Toolbar -->
        <div class="header-actions">
          <!-- Draft / Pending Actions -->
          <template v-if="transfer.status === 'Draft' || transfer.status === 'Pending'">
            <button class="btn-outline" @click="openAddLineModal">
              <span class="material-symbols-outlined icon-xs">add</span>
              {{ t('add-line', 'Add Item') }}
            </button>
            <button class="btn-primary" @click="openDispatchModal">
              <span class="material-symbols-outlined icon-xs">flight_takeoff</span>
              {{ t('dispatch-transfer', 'Dispatch Transfer') }}
            </button>
            <button class="btn-danger-outline" @click="openCancelModal">
              <span class="material-symbols-outlined icon-xs">cancel</span>
              {{ t('cancel-transfer', 'Cancel') }}
            </button>
          </template>

          <!-- In Transit Actions -->
          <template v-else-if="transfer.status === 'In Transit'">
            <button class="btn-primary btn-receive" @click="openReceiveModal">
              <span class="material-symbols-outlined icon-xs">fact_check</span>
              {{ t('receive-transfer', 'Receive Transfer') }}
            </button>
            <button class="btn-danger-outline" @click="openCancelModal">
              <span class="material-symbols-outlined icon-xs">cancel</span>
              {{ t('cancel-transfer', 'Cancel') }}
            </button>
          </template>

          <!-- Common Print & Refresh Buttons -->
          <button class="btn-outline btn-icon-only" @click="printWaybill" :title="t('print-waybill', 'Print Waybill')">
            <span class="material-symbols-outlined">print</span>
          </button>
          <button class="btn-outline btn-icon-only" @click="loadData(false)" :title="t('refresh', 'Refresh')">
            <span class="material-symbols-outlined">refresh</span>
          </button>
        </div>
      </div>

      <!-- Cancelled Status Banner -->
      <div v-if="transfer.status === 'Cancelled'" class="cancelled-banner">
        <span class="material-symbols-outlined icon-md text-danger">cancel</span>
        <div class="cancelled-content">
          <h4 class="cancelled-title">{{ t('transfer-cancelled-title', 'Stock Transfer Cancelled') }}</h4>
          <p class="cancelled-desc">
            {{ transfer.notes || t('transfer-cancelled-desc', 'This stock transfer was cancelled. Any in-transit or reserved inventory has been released.') }}
          </p>
        </div>
      </div>

      <!-- Discrepancy / Transit Loss Alert Banner -->
      <div v-if="transfer.total_lost_qty > 0" class="discrepancy-banner">
        <span class="material-symbols-outlined discrepancy-icon">warning</span>
        <div class="discrepancy-content">
          <h4 class="discrepancy-title">
            {{ t('discrepancy-loss-detected', 'Transit Discrepancies / Losses Detected') }}
            <span class="discrepancy-qty-tag">({{ transfer.total_lost_qty }} {{ t('lost-units', 'units lost/damaged') }})</span>
          </h4>
          <p class="discrepancy-desc">
            {{ t('discrepancy-loss-desc', 'Discrepancies or damaged goods were recorded during receipt. Stock adjustments have been logged under Transfer Loss.') }}
          </p>
        </div>
      </div>

      <!-- Workflow Timeline Stepper -->
      <div class="data-card timeline-card">
        <div class="card-header-simple">
          <h3 class="card-title">
            <span class="material-symbols-outlined icon-sm">timeline</span>
            {{ t('transfer-workflow', 'Transfer Workflow & Status Timeline') }}
          </h3>
        </div>

        <div class="stepper-wrap">
          <!-- Step 1: Draft / Created -->
          <div class="step-item" :class="getStepClass(1)">
            <div class="step-icon-wrap">
              <span class="material-symbols-outlined step-icon">
                {{ isStepCompleted(1) ? 'check' : 'edit_document' }}
              </span>
            </div>
            <div class="step-content">
              <div class="step-title">{{ t('step-created', 'Order Created') }}</div>
              <div class="step-meta">
                <span v-if="transfer.transfer_date">{{ formatDate(transfer.transfer_date) }}</span>
                <span v-else>{{ t('draft', 'Draft') }}</span>
              </div>
            </div>
          </div>

          <div class="step-line" :class="{ 'step-line-active': isStepActiveOrDone(2) }"></div>

          <!-- Step 2: Dispatched / In Transit -->
          <div class="step-item" :class="getStepClass(2)">
            <div class="step-icon-wrap">
              <span class="material-symbols-outlined step-icon">
                {{ isStepCompleted(2) ? 'check' : 'local_shipping' }}
              </span>
            </div>
            <div class="step-content">
              <div class="step-title">{{ t('step-dispatched', 'Dispatched (In Transit)') }}</div>
              <div class="step-meta">
                <span v-if="transfer.dispatched_at">{{ formatDateTime(transfer.dispatched_at) }}</span>
                <span v-else-if="transfer.status === 'Draft'">{{ t('pending-dispatch', 'Awaiting dispatch') }}</span>
                <span v-if="transfer.dispatched_by_name" class="step-sub-user">({{ transfer.dispatched_by_name }})</span>
                <span v-if="transfer.carrier" class="step-sub-carrier">• {{ transfer.carrier }}</span>
              </div>
            </div>
          </div>

          <div class="step-line" :class="{ 'step-line-active': isStepActiveOrDone(3) }"></div>

          <!-- Step 3: Received / Completed -->
          <div class="step-item" :class="getStepClass(3)">
            <div class="step-icon-wrap">
              <span class="material-symbols-outlined step-icon">
                {{ isStepCompleted(3) ? 'task_alt' : 'fact_check' }}
              </span>
            </div>
            <div class="step-content">
              <div class="step-title">{{ t('step-received', 'Received & Verified') }}</div>
              <div class="step-meta">
                <span v-if="transfer.received_at">{{ formatDateTime(transfer.received_at) }}</span>
                <span v-else>{{ t('pending-receipt', 'Awaiting destination receipt') }}</span>
                <span v-if="transfer.received_by_name" class="step-sub-user">({{ transfer.received_by_name }})</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Route & Logistics Overview Cards Grid -->
      <div class="grid-overview">
        <!-- Origin Warehouse Card -->
        <div class="info-card">
          <div class="info-card-header">
            <span class="material-symbols-outlined icon-sm text-primary">warehouse</span>
            <h4 class="info-card-title">{{ t('origin-wh', 'Origin Warehouse (Source)') }}</h4>
          </div>
          <div class="info-card-body">
            <div class="wh-main-name">{{ transfer.source_warehouse_name || getWarehouseName(transfer.source_warehouse_id) }}</div>
            <div class="wh-id-code text-muted text-xs font-mono">ID: #{{ transfer.source_warehouse_id }}</div>
            <div class="info-row mt-2">
              <span class="info-lbl">{{ t('transfer-date', 'Transfer Date') }}:</span>
              <span class="info-val">{{ formatDate(transfer.transfer_date) }}</span>
            </div>
          </div>
        </div>

        <!-- Destination Warehouse Card -->
        <div class="info-card">
          <div class="info-card-header">
            <span class="material-symbols-outlined icon-sm text-primary">domain</span>
            <h4 class="info-card-title">{{ t('destination-wh', 'Destination Warehouse') }}</h4>
          </div>
          <div class="info-card-body">
            <div class="wh-main-name">{{ transfer.destination_warehouse_name || getWarehouseName(transfer.destination_warehouse_id) }}</div>
            <div class="wh-id-code text-muted text-xs font-mono">ID: #{{ transfer.destination_warehouse_id }}</div>
            <div class="info-row mt-2">
              <span class="info-lbl">{{ t('expected-delivery-date', 'Exp. Delivery') }}:</span>
              <span class="info-val">{{ formatDate(transfer.expected_delivery_date) || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Logistics & Shipping Details Card -->
        <div class="info-card">
          <div class="info-card-header">
            <span class="material-symbols-outlined icon-sm text-primary">local_shipping</span>
            <h4 class="info-card-title">{{ t('shipping-carrier', 'Logistics & Shipping') }}</h4>
          </div>
          <div class="info-card-body">
            <div class="info-row">
              <span class="info-lbl">{{ t('carrier-name', 'Carrier') }}:</span>
              <span class="info-val font-medium">{{ transfer.carrier || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">{{ t('tracking-no', 'Tracking #') }}:</span>
              <span class="info-val font-mono text-xs">{{ transfer.tracking_number || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">{{ t('dispatched-by-lbl', 'Dispatched By') }}:</span>
              <span class="info-val">{{ transfer.dispatched_by_name || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">{{ t('received-by-lbl', 'Received By') }}:</span>
              <span class="info-val">{{ transfer.received_by_name || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Summary KPI Quantities Card -->
        <div class="info-card">
          <div class="info-card-header">
            <span class="material-symbols-outlined icon-sm text-primary">inventory_2</span>
            <h4 class="info-card-title">{{ t('lines-summary', 'Transfer Items Summary') }}</h4>
          </div>
          <div class="info-card-body summary-body">
            <div class="summary-stat">
              <span class="summary-stat-num">{{ transfer.lines?.length || transfer.lines_count || 0 }}</span>
              <span class="summary-stat-lbl">{{ t('lines', 'Lines') }}</span>
            </div>
            <div class="summary-stat">
              <span class="summary-stat-num">{{ transfer.total_requested_qty || 0 }}</span>
              <span class="summary-stat-lbl">{{ t('qty-requested-total', 'Requested') }}</span>
            </div>
            <div class="summary-stat">
              <span class="summary-stat-num in-transit">{{ transfer.total_dispatched_qty || 0 }}</span>
              <span class="summary-stat-lbl">{{ t('qty-dispatched-total', 'Dispatched') }}</span>
            </div>
            <div class="summary-stat">
              <span class="summary-stat-num received">{{ transfer.total_received_qty || 0 }}</span>
              <span class="summary-stat-lbl">{{ t('qty-received-total', 'Received') }}</span>
            </div>
            <div class="summary-stat">
              <span class="summary-stat-num" :class="{ 'discrepancies': transfer.total_lost_qty > 0 }">
                {{ transfer.total_lost_qty || 0 }}
              </span>
              <span class="summary-stat-lbl">{{ t('qty-lost-total', 'Loss') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Notes Box (if present) -->
      <div v-if="transfer.notes" class="notes-box data-card">
        <span class="material-symbols-outlined icon-xs text-muted">description</span>
        <div class="notes-body">
          <span class="notes-title">{{ t('notes-instructions', 'Notes & Instructions') }}:</span>
          <span class="notes-text">{{ transfer.notes }}</span>
        </div>
      </div>

      <!-- Line Items Table Card -->
      <div class="data-card line-items-card">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3 class="card-title">{{ t('transfer-lines', 'Transfer Line Items') }}</h3>
            <p class="card-subtitle">{{ t('transfer-lines-sub', 'Itemized products, batch allocations, dispatch and receipt quantities') }}</p>
          </div>
          <div v-if="transfer.status === 'Draft' || transfer.status === 'Pending'" class="header-actions-sub">
            <button class="btn-outline btn-sm" @click="openAddLineModal">
              <span class="material-symbols-outlined icon-xs">add</span>
              {{ t('add-line', 'Add Item') }}
            </button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-8">#</th>
                <th>{{ t('product', 'Product (SKU & Name)') }}</th>
                <th>{{ t('batch-lot', 'Batch / Lot #') }}</th>
                <th class="col-num">{{ t('qty-requested', 'Requested') }}</th>
                <th class="col-num">{{ t('qty-dispatched', 'Dispatched') }}</th>
                <th class="col-num">{{ t('qty-received', 'Received') }}</th>
                <th class="col-num">{{ t('qty-lost', 'Lost / Damaged') }}</th>
                <th>{{ t('loss-reason', 'Loss Reason & Notes') }}</th>
                <th class="text-center">{{ t('status', 'Status') }}</th>
                <th v-if="transfer.status === 'Draft' || transfer.status === 'Pending'" class="col-actions text-center">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(line, idx) in (transfer.lines || [])"
                :key="line.id || idx"
                :class="{ 'row-lost': line.qty_lost > 0, 'row-received': line.qty_received >= line.qty_requested && line.qty_received > 0 }"
              >
                <!-- Line Number -->
                <td class="cell-mono font-bold">{{ line.line_number || idx + 1 }}</td>

                <!-- Product -->
                <td>
                  <div class="prod-cell">
                    <span v-if="line.product_code" class="font-mono text-xs text-muted">[{{ line.product_code }}]</span>
                    <strong class="prod-name">{{ line.product_name || getProductName(line.product_id) }}</strong>
                    <span v-if="line.uom_name" class="uom-tag text-xs">{{ line.uom_name }}</span>
                  </div>
                  <div v-if="line.notes" class="line-notes-sub text-xs text-muted">
                    <span class="material-symbols-outlined icon-xxs">notes</span>
                    {{ line.notes }}
                  </div>
                </td>

                <!-- Batch / Lot -->
                <td>
                  <span v-if="line.batch_number" class="badge badge-batch">
                    <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                    {{ line.batch_number }}
                  </span>
                  <span v-else class="text-muted text-xs">—</span>
                </td>

                <!-- Requested Qty -->
                <td class="col-num font-mono font-medium">{{ line.qty_requested }}</td>

                <!-- Dispatched Qty -->
                <td class="col-num font-mono">
                  <span v-if="line.qty_dispatched > 0" class="text-primary font-medium">{{ line.qty_dispatched }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- Received Qty -->
                <td class="col-num font-mono">
                  <span v-if="line.qty_received > 0" class="text-success font-bold">{{ line.qty_received }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- Lost / Damaged Qty -->
                <td class="col-num font-mono">
                  <span v-if="line.qty_lost > 0" class="badge badge-loss font-bold">
                    {{ line.qty_lost }}
                  </span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- Loss Reason & Notes -->
                <td>
                  <div v-if="line.qty_lost > 0 || line.loss_reason">
                    <div v-if="line.loss_reason" class="loss-reason-text font-semibold text-danger">
                      <span class="material-symbols-outlined icon-xs">warning</span>
                      {{ formatLossReason(line.loss_reason) }}
                    </div>
                    <div v-if="line.loss_notes" class="loss-notes-text text-xs text-muted">
                      {{ line.loss_notes }}
                    </div>
                  </div>
                  <span v-else class="text-muted text-xs">—</span>
                </td>

                <!-- Line Status Badge -->
                <td class="text-center">
                  <span v-if="line.qty_lost > 0" class="badge badge-loss">
                    {{ t('discrepant', 'Discrepancy') }}
                  </span>
                  <span v-else-if="transfer.status === 'Received' || (line.qty_received >= line.qty_requested && line.qty_received > 0)" class="badge badge-received">
                    <span class="material-symbols-outlined icon-xs">check</span>
                    {{ t('matched', 'Matched') }}
                  </span>
                  <span v-else-if="transfer.status === 'In Transit'" class="badge badge-transit">
                    {{ t('in-transit', 'In Transit') }}
                  </span>
                  <span v-else class="badge badge-draft">
                    {{ t('pending', 'Pending') }}
                  </span>
                </td>

                <!-- Actions for Draft -->
                <td v-if="transfer.status === 'Draft' || transfer.status === 'Pending'" class="text-center">
                  <div class="actions-group-cell">
                    <button class="btn-icon btn-xs" @click="openEditLineModal(line)" :title="t('edit', 'Edit')">
                      <span class="material-symbols-outlined icon-xs">edit</span>
                    </button>
                    <button class="btn-icon btn-icon-danger btn-xs" @click="openDeleteLineModal(line)" :title="t('delete', 'Delete')">
                      <span class="material-symbols-outlined icon-xs">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Table Totals Summary Bar -->
        <div class="transfer-table-footer">
          <div class="footer-summary-group">
            <span class="footer-lbl">{{ t('total-lines', 'Total Lines') }}:</span>
            <span class="footer-val font-mono">{{ transfer.lines?.length || 0 }}</span>
          </div>
          <div class="footer-summary-group">
            <span class="footer-lbl">{{ t('total-requested', 'Total Requested') }}:</span>
            <span class="footer-val font-mono">{{ transfer.total_requested_qty || 0 }}</span>
          </div>
          <div class="footer-summary-group">
            <span class="footer-lbl">{{ t('total-dispatched', 'Total Dispatched') }}:</span>
            <span class="footer-val font-mono text-primary">{{ transfer.total_dispatched_qty || 0 }}</span>
          </div>
          <div class="footer-summary-group">
            <span class="footer-lbl">{{ t('total-received', 'Total Received') }}:</span>
            <span class="footer-val font-mono text-success">{{ transfer.total_received_qty || 0 }}</span>
          </div>
          <div v-if="transfer.total_lost_qty > 0" class="footer-summary-group">
            <span class="footer-lbl">{{ t('total-lost', 'Total Loss') }}:</span>
            <span class="footer-val font-mono text-danger font-bold">{{ transfer.total_lost_qty }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- =================================================================== -->
    <!-- Dispatch Modal Dialog                                               -->
    <!-- =================================================================== -->
    <Teleport to="body">
      <div v-if="showDispatchModal" class="modal-overlay" @click.self="showDispatchModal = false">
        <div class="modal-dialog modal-lg" :dir="dir">
          <div class="modal-header">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">flight_takeoff</span>
              <h3 class="modal-title">{{ t('dispatch-transfer-title', 'Dispatch Stock Transfer') }}</h3>
            </div>
            <button class="modal-close" @click="showDispatchModal = false">&times;</button>
          </div>

          <form @submit.prevent="submitDispatch" class="modal-body">
            <div class="dispatch-alert">
              <span class="material-symbols-outlined icon-md">info</span>
              <div>
                <p class="alert-title">{{ t('dispatch-info-title', 'Stock Deduction & In-Transit Movement') }}</p>
                <p class="alert-desc">
                  {{ t('dispatch-info-desc', 'Dispatching will deduct stock from the source warehouse and allocate it to In-Transit inventory until acknowledged by destination warehouse.') }}
                </p>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ t('carrier', 'Carrier / Transport Provider') }}</label>
                <input
                  type="text"
                  v-model="dispatchForm.carrier"
                  class="form-input"
                  placeholder="e.g. DHL Express, Internal Fleet Truck #4, Aramex"
                />
              </div>

              <div class="form-group">
                <label>{{ t('tracking-number', 'Tracking / Waybill Number') }}</label>
                <input
                  type="text"
                  v-model="dispatchForm.tracking_number"
                  class="form-input"
                  placeholder="e.g. TRK-9902341"
                />
              </div>
            </div>

            <div class="form-group">
              <label>{{ t('dispatch-notes', 'Dispatch Notes & Remarks') }}</label>
              <textarea
                v-model="dispatchForm.notes"
                rows="2"
                class="form-input form-textarea"
                placeholder="Optional carrier notes or dispatch remarks..."
              ></textarea>
            </div>

            <!-- Dispatched Lines Verification Preview -->
            <div class="dispatch-lines-preview">
              <h5 class="preview-title">{{ t('verify-dispatch-qty', 'Items to Dispatch') }}</h5>
              <table class="preview-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>{{ t('product', 'Product') }}</th>
                    <th>{{ t('batch-lot', 'Batch #') }}</th>
                    <th class="col-num">{{ t('qty-requested', 'Req. Qty') }}</th>
                    <th class="col-num">{{ t('qty-dispatched', 'Dispatch Qty') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, idx) in dispatchForm.lines" :key="'disp-line-' + idx">
                    <td class="cell-mono">{{ idx + 1 }}</td>
                    <td>{{ line.product_name || getProductName(line.product_id) }}</td>
                    <td>{{ line.batch_number || '—' }}</td>
                    <td class="col-num">{{ line.qty_requested }}</td>
                    <td class="col-num">
                      <input
                        type="number"
                        step="any"
                        min="0.001"
                        v-model.number="line.qty_dispatched"
                        class="form-input form-input-sm preview-qty-input"
                        required
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-outline" @click="showDispatchModal = false" :disabled="submitting">
                {{ t('cancel', 'Cancel') }}
              </button>
              <button type="submit" class="btn-primary" :disabled="submitting">
                <span v-if="submitting" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                <span v-else class="material-symbols-outlined icon-xs">flight_takeoff</span>
                {{ submitting ? t('dispatching', 'Dispatching...') : t('confirm-dispatch', 'Confirm Dispatch') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- =================================================================== -->
    <!-- Receive Modal Dialog (with Itemized Loss & Reason Code Capture)     -->
    <!-- =================================================================== -->
    <Teleport to="body">
      <div v-if="showReceiveModal" class="modal-overlay" @click.self="showReceiveModal = false">
        <div class="modal-dialog modal-xl" :dir="dir">
          <div class="modal-header">
            <div>
              <h3 class="modal-title flex items-center gap-2">
                <span class="material-symbols-outlined text-success">fact_check</span>
                {{ t('receive-modal-title', 'Receive Stock Transfer') }}
              </h3>
              <p class="modal-subtitle">
                {{ t('receive-modal-sub', 'Verify received quantities at destination warehouse and log any transit damage or discrepancies') }}
              </p>
            </div>
            <button class="modal-close" @click="showReceiveModal = false">&times;</button>
          </div>

          <form @submit.prevent="submitReceive" class="modal-body">
            <!-- Header quick action bar -->
            <div class="receive-actions-bar">
              <div class="font-medium text-sm">
                {{ t('route', 'Route') }}:
                <strong>{{ transfer.source_warehouse_name }}</strong> &rarr; <strong>{{ transfer.destination_warehouse_name }}</strong>
              </div>
              <div class="flex items-center gap-2">
                <button type="button" class="btn-outline btn-sm" @click="resetForScanToCount">
                  <span class="material-symbols-outlined icon-xs">restart_alt</span>
                  {{ t('reset-scan-count', 'Reset for Scan-to-Count') }}
                </button>
                <button type="button" class="btn-outline btn-sm" @click="receiveAllInFull">
                  <span class="material-symbols-outlined icon-xs">done_all</span>
                  {{ t('receive-all-full', 'Receive All in Full') }}
                </button>
              </div>
            </div>

            <!-- Rapid Barcode Scanner Box -->
            <div class="barcode-scanner-box">
              <div class="barcode-input-wrap">
                <span class="material-symbols-outlined barcode-icon">qr_code_scanner</span>
                <input
                  ref="barcodeInputRef"
                  type="text"
                  v-model="barcodeQuery"
                  class="barcode-input form-input"
                  :placeholder="t('scan-barcode-ph', 'Scan barcode, SKU, or Lot # (e.g. SKU-DAIRY-01, LOT-MILK-202608)...')"
                  @keydown.enter.prevent="handleBarcodeScan"
                />
                <button type="button" class="btn-primary btn-sm" @click="handleBarcodeScan">
                  <span class="material-symbols-outlined icon-xs">search</span>
                  {{ t('scan', 'Scan Barcode') }}
                </button>
              </div>
              <div v-if="scanFeedback" class="scan-feedback" :class="scanFeedback.type">
                <span class="material-symbols-outlined icon-xs">
                  {{ scanFeedback.type === 'success' ? 'check_circle' : 'error' }}
                </span>
                <span>{{ scanFeedback.message }}</span>
              </div>
            </div>

            <!-- Itemized Receiving Lines Table -->
            <div class="receive-table-wrap">
              <table class="receive-table">
                <thead>
                  <tr>
                    <th style="width: 3%;">#</th>
                    <th style="width: 20%;">{{ t('product', 'Product') }}</th>
                    <th style="width: 14%;">{{ t('batch-expiry', 'Batch & Expiry') }}</th>
                    <th style="width: 9%;" class="col-num">{{ t('dispatched', 'Dispatched') }}</th>
                    <th style="width: 11%;" class="col-num">{{ t('qty-received', 'Received') }} <span class="required">*</span></th>
                    <th style="width: 9%;" class="col-num">{{ t('qty-lost', 'Lost / Short') }}</th>
                    <th style="width: 17%;">{{ t('loss-reason', 'Loss Reason (if lost > 0)') }}</th>
                    <th style="width: 17%;">{{ t('loss-notes', 'Loss Notes / Remarks') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(rLine, index) in receiveForm.lines"
                    :key="'rec-line-' + index"
                    :class="{
                      'row-loss-highlight': (rLine.qty_lost > 0),
                      'row-scanned-highlight': (lastScannedLineId === rLine.line_id),
                      'row-verified': rLine.verified
                    }"
                  >
                    <!-- Line # & Verification Checkmark -->
                    <td class="cell-mono">
                      <span v-if="rLine.verified" class="material-symbols-outlined icon-xs text-success" title="Verified">check_circle</span>
                      <span v-else>{{ index + 1 }}</span>
                    </td>

                    <!-- Product & SKU Code -->
                    <td>
                      <div class="font-medium text-sm">{{ rLine.product_name || getProductName(rLine.product_id) }}</div>
                      <div v-if="rLine.product_code" class="text-xs text-muted font-mono">
                        {{ rLine.product_code }}
                      </div>
                    </td>

                    <!-- Batch & Expiration Verification -->
                    <td>
                      <div v-if="rLine.batch_number" class="badge badge-batch badge-xs mb-1">
                        <span class="material-symbols-outlined icon-xxs">qr_code_2</span>
                        {{ rLine.batch_number }}
                      </div>
                      <input
                        type="date"
                        v-model="rLine.expiration_date"
                        class="form-input form-input-sm date-input-sm"
                        :title="t('expiration-date', 'Expiration Date')"
                      />
                    </td>

                    <!-- Dispatched Qty (Read-only reference) -->
                    <td class="col-num font-mono font-medium text-muted">
                      {{ rLine.qty_dispatched }}
                    </td>

                    <!-- Received Qty (Input) -->
                    <td class="col-num">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        :max="rLine.qty_dispatched"
                        v-model.number="rLine.qty_received"
                        class="form-input form-input-sm rec-qty-input"
                        @input="onReceivedQtyChange(rLine)"
                        required
                      />
                    </td>

                    <!-- Lost / Damaged Qty (Auto calculated or adjusted) -->
                    <td class="col-num">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        v-model.number="rLine.qty_lost"
                        class="form-input form-input-sm lost-qty-input"
                        :class="{ 'input-lost-alert': rLine.qty_lost > 0 }"
                        @input="onLostQtyChange(rLine)"
                      />
                    </td>

                    <!-- Loss Reason Code (Dropdown) -->
                    <td>
                      <select
                        v-model="rLine.loss_reason"
                        class="form-input form-input-sm"
                        :disabled="rLine.qty_lost <= 0"
                        :required="rLine.qty_lost > 0"
                      >
                        <option value="">{{ rLine.qty_lost > 0 ? t('select-reason', '-- Select Loss Reason --') : '—' }}</option>
                        <option value="Transit Damage">{{ t('loss-reason-damage', 'Transit Damage') }}</option>
                        <option value="Spillage / Leakage">{{ t('loss-reason-spillage', 'Spillage / Leakage') }}</option>
                        <option value="Theft / Pilferage">{{ t('loss-reason-theft', 'Theft / Pilferage') }}</option>
                        <option value="Expired / Spoiled">{{ t('loss-reason-expired', 'Expired / Spoiled') }}</option>
                        <option value="Shortage / Missing">{{ t('loss-reason-shortage', 'Shortage / Missing') }}</option>
                        <option value="Packaging Failure">{{ t('loss-reason-packaging', 'Packaging Failure') }}</option>
                        <option value="Temperature Deviation">{{ t('loss-reason-temp', 'Temperature Deviation') }}</option>
                        <option value="Other">{{ t('loss-reason-other', 'Other Discrepancy') }}</option>
                      </select>
                    </td>

                    <!-- Loss Notes / Remarks -->
                    <td>
                      <input
                        type="text"
                        v-model="rLine.loss_notes"
                        class="form-input form-input-sm"
                        :placeholder="rLine.qty_lost > 0 ? t('loss-notes-ph', 'Damage details, box condition...') : '—'"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- General Receiving Notes -->
            <div class="form-group mt-3">
              <label>{{ t('receive-notes', 'Receiving Remarks / Inspector Notes') }}</label>
              <textarea
                v-model="receiveForm.notes"
                rows="2"
                class="form-input form-textarea"
                :placeholder="t('receive-notes-ph', 'Inspection condition on arrival, seal verification, warehouse receiving notes...')"
              ></textarea>
            </div>

            <!-- Total Quantities Summary Footer -->
            <div class="receive-totals-bar">
              <div class="rec-total-item">
                <span class="rec-lbl">{{ t('total-dispatched', 'Total Dispatched') }}:</span>
                <span class="rec-val font-mono">{{ totalReceiveDispatchedQty }}</span>
              </div>
              <div class="rec-total-item">
                <span class="rec-lbl">{{ t('total-received', 'Total Received') }}:</span>
                <span class="rec-val font-mono text-success">{{ totalReceiveReceivedQty }}</span>
              </div>
              <div class="rec-total-item">
                <span class="rec-lbl">{{ t('total-lost', 'Total Discrepancy / Loss') }}:</span>
                <span class="rec-val font-mono" :class="totalReceiveLostQty > 0 ? 'text-danger font-bold' : ''">
                  {{ totalReceiveLostQty }}
                </span>
              </div>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-outline" @click="showReceiveModal = false" :disabled="submitting">
                {{ t('cancel', 'Cancel') }}
              </button>
              <button type="submit" class="btn-primary btn-receive" :disabled="submitting">
                <span v-if="submitting" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                <span v-else class="material-symbols-outlined icon-xs">check_circle</span>
                {{ submitting ? t('receiving', 'Receiving...') : t('confirm-receipt', 'Confirm Receipt') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- =================================================================== -->
    <!-- Add / Edit Line Modal Dialog (for Draft/Pending Orders)              -->
    <!-- =================================================================== -->
    <Teleport to="body">
      <div v-if="showLineModal" class="modal-overlay" @click.self="showLineModal = false">
        <div class="modal-dialog modal-md" :dir="dir">
          <div class="modal-header">
            <h3 class="modal-title">
              {{ editingLine ? t('edit-line', 'Edit Line Item') : t('add-line', 'Add Transfer Line Item') }}
            </h3>
            <button class="modal-close" @click="showLineModal = false">&times;</button>
          </div>

          <form @submit.prevent="submitLineForm" class="modal-body">
            <div class="form-group">
              <label>{{ t('product', 'Product') }} <span class="required">*</span></label>
              <select v-model.number="lineForm.product_id" class="form-input" required>
                <option :value="null">{{ t('select-product', '-- Select Product --') }}</option>
                <option v-for="prod in products" :key="'modal-line-prod-' + prod.id" :value="prod.id">
                  {{ prod.sku ? `[${prod.sku}] ` : '' }}{{ prod.name }}
                </option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>{{ t('qty-requested', 'Quantity Requested') }} <span class="required">*</span></label>
                <input
                  type="number"
                  step="any"
                  min="0.001"
                  v-model.number="lineForm.qty_requested"
                  class="form-input"
                  required
                />
              </div>

              <div class="form-group">
                <label>{{ t('batch-lot', 'Batch / Lot #') }}</label>
                <input
                  type="text"
                  v-model="lineForm.batch_number"
                  class="form-input"
                  placeholder="Optional Lot#"
                />
              </div>
            </div>

            <div class="form-group">
              <label>{{ t('line-notes', 'Item Notes') }}</label>
              <input
                type="text"
                v-model="lineForm.notes"
                class="form-input"
                placeholder="Optional remarks..."
              />
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-outline" @click="showLineModal = false" :disabled="submitting">
                {{ t('cancel', 'Cancel') }}
              </button>
              <button type="submit" class="btn-primary" :disabled="submitting">
                <span v-if="submitting" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                {{ submitting ? t('saving', 'Saving...') : t('save', 'Save Item') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- =================================================================== -->
    <!-- Cancel Confirmation Modal                                           -->
    <!-- =================================================================== -->
    <Teleport to="body">
      <div v-if="showCancelModal" class="modal-overlay" @click.self="showCancelModal = false">
        <div class="modal-dialog modal-sm" :dir="dir">
          <div class="modal-header">
            <h3 class="modal-title">{{ t('confirm-cancel-transfer', 'Cancel Stock Transfer') }}</h3>
            <button class="modal-close" @click="showCancelModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <p class="mb-3">
              {{ t('cancel-transfer-confirm-msg', 'Are you sure you want to cancel stock transfer') }}
              <strong class="font-mono">{{ transfer.transfer_number }}</strong>?
            </p>
            <p v-if="transfer.status === 'In Transit'" class="text-sm text-warning mb-3">
              <span class="material-symbols-outlined icon-xs">warning</span>
              {{ t('cancel-in-transit-warn', 'This transfer is currently In Transit. Cancelling will reverse the dispatch and restore stock to the source warehouse.') }}
            </p>
            <div class="form-group">
              <label>{{ t('cancellation-reason', 'Cancellation Reason') }}</label>
              <input
                type="text"
                v-model="cancelReason"
                class="form-input"
                placeholder="e.g. Duplicate order, order cancelled by manager"
              />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-outline" @click="showCancelModal = false" :disabled="submitting">{{ t('back', 'Back') }}</button>
            <button class="btn-danger" :disabled="submitting" @click="submitCancel">
              {{ submitting ? t('cancelling', 'Cancelling...') : t('cancel-transfer-btn', 'Cancel Transfer') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- =================================================================== -->
    <!-- Delete Line Confirmation Modal                                      -->
    <!-- =================================================================== -->
    <Teleport to="body">
      <div v-if="showDeleteLineModal" class="modal-overlay" @click.self="showDeleteLineModal = false">
        <div class="modal-dialog modal-sm" :dir="dir">
          <div class="modal-header">
            <h3 class="modal-title">{{ t('delete-line', 'Remove Item') }}</h3>
            <button class="modal-close" @click="showDeleteLineModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <p>{{ t('delete-line-confirm', 'Remove this item from transfer order?') }}</p>
            <p v-if="targetLine" class="font-medium mt-1">
              {{ targetLine.product_name || getProductName(targetLine.product_id) }} ({{ targetLine.qty_requested }} units)
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-outline" @click="showDeleteLineModal = false" :disabled="submitting">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-danger" :disabled="submitting" @click="submitDeleteLine">
              {{ submitting ? t('deleting', 'Removing...') : t('delete', 'Remove') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import { useWebSocket } from '../../composables/useWebSocket.js'
import { useAuthStore } from '../../stores/auth.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// Data State
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const transfer = ref(null)
const warehouses = ref([])
const products = ref([])

// Modal Visibility States
const showDispatchModal = ref(false)
const showReceiveModal = ref(false)
const showCancelModal = ref(false)
const showLineModal = ref(false)
const showDeleteLineModal = ref(false)

// Active Editing Line / Target Line
const editingLine = ref(null)
const targetLine = ref(null)
const cancelReason = ref('')

// Form States
const dispatchForm = reactive({
  carrier: '',
  tracking_number: '',
  notes: '',
  lines: []
})

const receiveForm = reactive({
  notes: '',
  lines: []
})

const lineForm = reactive({
  product_id: null,
  qty_requested: 1,
  batch_number: '',
  notes: ''
})

// Multi-tenant & Real-time WebSocket updates
const auth = useAuthStore()
const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
wsInventory.on('stock_transfers_updated', () => {
  loadData(false)
})
wsInventory.on('stock_updated', () => {
  loadData(false)
})

// ---------------------------------------------------------------------------
// Computed Helpers & Summaries
// ---------------------------------------------------------------------------

const totalReceiveDispatchedQty = computed(() => {
  return receiveForm.lines.reduce((sum, l) => sum + (Number(l.qty_dispatched) || 0), 0).toFixed(2)
})

const totalReceiveReceivedQty = computed(() => {
  return receiveForm.lines.reduce((sum, l) => sum + (Number(l.qty_received) || 0), 0).toFixed(2)
})

const totalReceiveLostQty = computed(() => {
  return receiveForm.lines.reduce((sum, l) => sum + (Number(l.qty_lost) || 0), 0).toFixed(2)
})

// ---------------------------------------------------------------------------
// Timeline / Stepper Helpers
// ---------------------------------------------------------------------------

function getStepClass(stepNum) {
  if (!transfer.value) return ''
  const status = transfer.value.status

  if (status === 'Cancelled') {
    return 'step-cancelled'
  }

  if (stepNum === 1) {
    if (status === 'Draft' || status === 'Pending') return 'step-active'
    return 'step-done'
  }

  if (stepNum === 2) {
    if (status === 'In Transit') return 'step-active'
    if (status === 'Received' || status === 'Partially Received') return 'step-done'
    return 'step-pending'
  }

  if (stepNum === 3) {
    if (status === 'Received' || status === 'Partially Received') return 'step-done'
    return 'step-pending'
  }

  return ''
}

function isStepCompleted(stepNum) {
  if (!transfer.value) return false
  const status = transfer.value.status
  if (status === 'Cancelled') return false

  if (stepNum === 1) return status !== 'Draft' && status !== 'Pending'
  if (stepNum === 2) return status === 'Received' || status === 'Partially Received'
  if (stepNum === 3) return status === 'Received' || status === 'Partially Received'
  return false
}

function isStepActiveOrDone(stepNum) {
  if (!transfer.value) return false
  const status = transfer.value.status
  if (status === 'Cancelled') return false

  if (stepNum === 2) return status === 'In Transit' || status === 'Received' || status === 'Partially Received'
  if (stepNum === 3) return status === 'Received' || status === 'Partially Received'
  return false
}

// ---------------------------------------------------------------------------
// Badge and Formatting Helpers
// ---------------------------------------------------------------------------

function statusBadgeClass(status) {
  switch (status) {
    case 'Draft':
    case 'Pending':
      return 'badge-draft'
    case 'In Transit':
      return 'badge-transit'
    case 'Received':
      return 'badge-received'
    case 'Partially Received':
      return 'badge-partial'
    case 'Cancelled':
      return 'badge-cancelled'
    default:
      return 'badge-default'
  }
}

function statusIcon(status) {
  switch (status) {
    case 'Draft':
    case 'Pending':
      return 'edit_note'
    case 'In Transit':
      return 'local_shipping'
    case 'Received':
      return 'task_alt'
    case 'Partially Received':
      return 'hourglass_top'
    case 'Cancelled':
      return 'cancel'
    default:
      return 'info'
  }
}

function getWarehouseName(id) {
  if (!id) return '—'
  const wh = warehouses.value.find(w => w.id === id)
  return wh ? wh.name : `#${id}`
}

function getProductName(id) {
  if (!id) return '—'
  const prod = products.value.find(p => p.id === id)
  return prod ? prod.name : `#${id}`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

function formatDateTime(dtStr) {
  if (!dtStr) return '—'
  try {
    const d = new Date(dtStr)
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dtStr
  }
}

function formatLossReason(reason) {
  switch (reason) {
    case 'Transit Damage':
      return t('loss-reason-damage', 'Transit Damage')
    case 'Spillage / Leakage':
      return t('loss-reason-spillage', 'Spillage / Leakage')
    case 'Theft / Pilferage':
      return t('loss-reason-theft', 'Theft / Pilferage')
    case 'Expired / Spoiled':
      return t('loss-reason-expired', 'Expired / Spoiled')
    case 'Shortage / Missing':
      return t('loss-reason-shortage', 'Shortage / Missing')
    case 'Packaging Failure':
      return t('loss-reason-packaging', 'Packaging Failure')
    case 'Temperature Deviation':
      return t('loss-reason-temp', 'Temperature Deviation')
    default:
      return reason
  }
}

// ---------------------------------------------------------------------------
// Data Loaders
// ---------------------------------------------------------------------------

async function loadData(showSpinner = true) {
  if (showSpinner) loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [detailRes, whRes, prodRes] = await Promise.all([
      api.get(`/T0108I/${id}/detail`),
      api.get('/T0008I/').catch(() => ({ data: [] })),
      api.get('/T0003I/').catch(() => ({ data: [] }))
    ])
    transfer.value = detailRes.data
    warehouses.value = whRes.data || []
    products.value = prodRes.data || []
  } catch (err) {
    console.error('Error loading stock transfer details:', err)
    error.value = t('failed-load-transfer', 'Failed to load stock transfer order details.')
  } finally {
    if (showSpinner) loading.value = false
  }
}

// ---------------------------------------------------------------------------
// Dispatch Workflow
// ---------------------------------------------------------------------------

function openDispatchModal() {
  if (!transfer.value) return
  dispatchForm.carrier = transfer.value.carrier || ''
  dispatchForm.tracking_number = transfer.value.tracking_number || ''
  dispatchForm.notes = ''
  dispatchForm.lines = (transfer.value.lines || []).map(l => ({
    line_id: l.id,
    product_id: l.product_id,
    product_name: l.product_name,
    batch_number: l.batch_number,
    batch_id: l.batch_id,
    qty_requested: l.qty_requested,
    qty_dispatched: l.qty_dispatched > 0 ? l.qty_dispatched : l.qty_requested,
  }))
  showDispatchModal.value = true
}

async function submitDispatch() {
  if (!transfer.value) return
  submitting.value = true
  try {
    const payload = {
      carrier: dispatchForm.carrier || null,
      tracking_number: dispatchForm.tracking_number || null,
      notes: dispatchForm.notes || null,
      lines: dispatchForm.lines.map(l => ({
        line_id: l.line_id,
        product_id: l.product_id,
        qty_dispatched: Number(l.qty_dispatched),
        batch_id: l.batch_id || null,
        batch_number: l.batch_number || null,
      }))
    }
    const res = await api.post(`/T0108I/${transfer.value.id}/dispatch`, payload)
    transfer.value = res.data
    toast(t('transfer-dispatched-success', 'Stock transfer dispatched and moved to In-Transit'), 'success')
    showDispatchModal.value = false
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-dispatch-transfer', 'Failed to dispatch stock transfer')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// Receive Workflow (with itemized loss & discrepancy handling)
// ---------------------------------------------------------------------------

function openReceiveModal() {
  if (!transfer.value) return
  receiveForm.notes = ''
  receiveForm.lines = (transfer.value.lines || []).map(l => {
    const dispQty = l.qty_dispatched > 0 ? l.qty_dispatched : l.qty_requested
    return {
      line_id: l.id,
      product_id: l.product_id,
      product_name: l.product_name,
      batch_id: l.batch_id,
      batch_number: l.batch_number,
      qty_dispatched: dispQty,
      qty_received: dispQty,
      qty_lost: 0,
      loss_reason: '',
      loss_notes: ''
    }
  })
  showReceiveModal.value = true
}

function receiveAllInFull() {
  receiveForm.lines.forEach(l => {
    l.qty_received = l.qty_dispatched
    l.qty_lost = 0
    l.loss_reason = ''
    l.loss_notes = ''
  })
}

function onReceivedQtyChange(rLine) {
  const disp = Number(rLine.qty_dispatched) || 0
  const rec = Number(rLine.qty_received) || 0
  if (rec <= disp) {
    rLine.qty_lost = Number((disp - rec).toFixed(3))
  } else {
    rLine.qty_lost = 0
  }
  if (rLine.qty_lost <= 0) {
    rLine.loss_reason = ''
  }
}

function onLostQtyChange(rLine) {
  const disp = Number(rLine.qty_dispatched) || 0
  const lost = Number(rLine.qty_lost) || 0
  if (lost <= disp) {
    rLine.qty_received = Number((disp - lost).toFixed(3))
  }
  if (lost <= 0) {
    rLine.loss_reason = ''
  }
}

async function submitReceive() {
  if (!transfer.value) return
  submitting.value = true
  try {
    const payloadLines = receiveForm.lines.map(l => ({
      line_id: l.line_id,
      product_id: l.product_id,
      qty_received: Number(l.qty_received),
      qty_lost: Number(l.qty_lost) || 0,
      loss_reason: l.qty_lost > 0 ? (l.loss_reason || 'Transit Damage') : null,
      loss_notes: l.loss_notes || null,
      batch_id: l.batch_id || null,
      batch_number: l.batch_number || null,
    }))

    const payloadLosses = receiveForm.lines
      .filter(l => Number(l.qty_lost) > 0)
      .map(l => ({
        line_id: l.line_id,
        product_id: l.product_id,
        qty_lost: Number(l.qty_lost),
        loss_reason: l.loss_reason || 'Transit Damage',
        loss_notes: l.loss_notes || null,
      }))

    const payload = {
      notes: receiveForm.notes || null,
      lines: payloadLines,
      losses: payloadLosses.length > 0 ? payloadLosses : null
    }

    const res = await api.post(`/T0108I/${transfer.value.id}/receive`, payload)
    transfer.value = res.data
    toast(t('receipt-completed-success', 'Stock transfer received successfully and inventory moved to destination warehouse'), 'success')
    showReceiveModal.value = false
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-receive-transfer', 'Failed to receive stock transfer')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// Cancel Workflow
// ---------------------------------------------------------------------------

function openCancelModal() {
  cancelReason.value = ''
  showCancelModal.value = true
}

async function submitCancel() {
  if (!transfer.value) return
  submitting.value = true
  try {
    const res = await api.post(`/T0108I/${transfer.value.id}/cancel`, {
      reason: cancelReason.value || 'Cancelled by user'
    })
    transfer.value = res.data
    toast(t('transfer-cancelled-success', 'Stock transfer cancelled successfully'), 'success')
    showCancelModal.value = false
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-cancel-transfer', 'Failed to cancel stock transfer')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// Line Management (Add, Edit, Delete for Draft orders)
// ---------------------------------------------------------------------------

function openAddLineModal() {
  editingLine.value = null
  lineForm.product_id = products.value.length > 0 ? products.value[0].id : null
  lineForm.qty_requested = 10
  lineForm.batch_number = ''
  lineForm.notes = ''
  showLineModal.value = true
}

function openEditLineModal(line) {
  editingLine.value = line
  lineForm.product_id = line.product_id
  lineForm.qty_requested = line.qty_requested
  lineForm.batch_number = line.batch_number || ''
  lineForm.notes = line.notes || ''
  showLineModal.value = true
}

async function submitLineForm() {
  if (!transfer.value) return
  submitting.value = true
  try {
    if (editingLine.value) {
      await api.put(`/T0108I/${transfer.value.id}/lines/${editingLine.value.id}`, {
        product_id: Number(lineForm.product_id),
        qty_requested: Number(lineForm.qty_requested),
        batch_number: lineForm.batch_number || null,
        notes: lineForm.notes || null,
      })
      toast(t('item-updated', 'Transfer line updated'), 'success')
    } else {
      await api.post(`/T0108I/${transfer.value.id}/lines`, {
        transfer_id: transfer.value.id,
        product_id: Number(lineForm.product_id),
        qty_requested: Number(lineForm.qty_requested),
        batch_number: lineForm.batch_number || null,
        notes: lineForm.notes || null,
        line_number: (transfer.value.lines?.length || 0) + 1
      })
      toast(t('item-added', 'Item added to transfer'), 'success')
    }
    showLineModal.value = false
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-save-line', 'Failed to save transfer line item')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

function openDeleteLineModal(line) {
  targetLine.value = line
  showDeleteLineModal.value = true
}

async function submitDeleteLine() {
  if (!transfer.value || !targetLine.value) return
  submitting.value = true
  try {
    await api.delete(`/T0108I/${transfer.value.id}/lines/${targetLine.value.id}`)
    toast(t('item-deleted', 'Transfer line removed'), 'success')
    showDeleteLineModal.value = false
    await loadData(false)
  } catch (err) {
    const msg = err.response?.data?.detail || t('failed-delete-line', 'Failed to remove transfer line item')
    toast(msg, 'error')
  } finally {
    submitting.value = false
  }
}

function printWaybill() {
  window.print()
}

onMounted(() => {
  loadData(true)
})
</script>

<style scoped>
.stock-transfer-detail-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.top-nav-row {
  display: flex;
  align-items: center;
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
}

.btn-link:hover {
  text-decoration: underline;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 14px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-status-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.route-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wh-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.route-arrow {
  font-size: 16px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Timeline Stepper */
.timeline-card {
  padding: 20px 24px;
}

.card-header-simple {
  margin-bottom: 18px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.stepper-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  position: relative;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.step-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-surface-hover);
  border: 2px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.step-icon {
  font-size: 20px;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.step-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.step-sub-carrier {
  color: var(--color-primary);
  font-weight: 500;
}

.step-line {
  height: 3px;
  flex: 0.8;
  background: var(--border-default);
  margin: 0 8px;
  border-radius: 2px;
  transition: background 0.2s ease;
}

.step-line-active {
  background: var(--color-primary);
}

/* Stepper state modifiers */
.step-done .step-icon-wrap {
  background: #dcfce7;
  border-color: #16a34a;
  color: #15803d;
}

.step-done .step-title {
  color: #15803d;
}

.step-active .step-icon-wrap {
  background: #e0f2fe;
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.15);
}

.step-active .step-title {
  color: var(--color-primary);
}

/* Discrepancy & Cancel Banners */
.discrepancy-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #b91c1c;
}

.discrepancy-icon {
  font-size: 28px;
  color: #dc2626;
  flex-shrink: 0;
}

.discrepancy-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 2px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.discrepancy-qty-tag {
  font-size: 12px;
  background: #fee2e2;
  padding: 1px 6px;
  border-radius: 4px;
}

.discrepancy-desc {
  font-size: 12px;
  margin: 0;
  color: #991b1b;
}

.cancelled-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #f3f4f6;
  border: 1px solid var(--border-default);
  border-radius: 10px;
}

.cancelled-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.cancelled-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* Overview Cards Grid */
.grid-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.info-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 8px;
}

.info-card-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  margin: 0;
}

.wh-main-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-top: 4px;
}

.info-lbl {
  color: var(--text-muted);
}

.info-val {
  color: var(--text-primary);
}

.summary-body {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  text-align: center;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-stat-num.in-transit { color: #0284c7; }
.summary-stat-num.received { color: #16a34a; }
.summary-stat-num.discrepancies { color: #dc2626; }

.summary-stat-lbl {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* Notes Box */
.notes-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
}

.notes-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-right: 6px;
}

.notes-text {
  color: var(--text-secondary);
}

/* Line Items Table */
.data-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}

.card-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 3px 0 0 0;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.data-table th {
  background: var(--bg-surface-hover);
  padding: 12px 14px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.data-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.prod-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.uom-tag {
  background: var(--bg-surface-hover);
  padding: 1px 5px;
  border-radius: 4px;
  border: 1px solid var(--border-light);
}

.line-notes-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.actions-group-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

/* Table Footer Summary */
.transfer-table-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 24px;
  padding: 12px 20px;
  background: var(--bg-surface-hover);
  border-top: 1px solid var(--border-default);
  font-size: 12px;
  flex-wrap: wrap;
}

.footer-summary-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.footer-lbl {
  color: var(--text-muted);
}

.footer-val {
  font-weight: 700;
}

/* Modal Dialogs */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-dialog {
  background: var(--bg-surface);
  border-radius: 12px;
  width: 92%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-sm { max-width: 440px; }
.modal-md { max-width: 580px; }
.modal-lg { max-width: 760px; }
.modal-xl { max-width: 960px; }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-muted);
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}

/* Receiving Modal Table */
.receive-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-surface-hover);
  border-radius: 8px;
}

.receive-table-wrap {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.receive-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.receive-table th {
  background: var(--bg-surface-hover);
  padding: 10px 12px;
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.receive-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.row-loss-highlight {
  background-color: #fef2f2;
}

.rec-qty-input {
  max-width: 100px;
  font-weight: 700;
  color: #15803d;
}

.lost-qty-input {
  max-width: 100px;
}

.input-lost-alert {
  border-color: #dc2626 !important;
  color: #dc2626 !important;
  font-weight: 700;
  background: #fee2e2;
}

.receive-totals-bar {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
  padding: 10px 16px;
  background: var(--bg-surface-hover);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 12px;
}

.rec-total-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rec-lbl {
  color: var(--text-muted);
}

.rec-val {
  font-weight: 700;
}

/* Dispatch Preview Table */
.dispatch-lines-preview {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.preview-title {
  font-size: 12px;
  font-weight: 700;
  padding: 8px 12px;
  background: var(--bg-surface-hover);
  margin: 0;
  border-bottom: 1px solid var(--border-default);
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.preview-table th {
  padding: 8px 12px;
  font-size: 11px;
  background: var(--bg-surface-hover);
  border-bottom: 1px solid var(--border-light);
  text-align: left;
}

.preview-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
}

.preview-qty-input {
  max-width: 110px;
}

.dispatch-alert {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  color: #0369a1;
}

.alert-title {
  font-weight: 600;
  font-size: 13px;
  margin: 0 0 2px 0;
}

.alert-desc {
  font-size: 12px;
  margin: 0;
}

/* Common Form & Button Utilities */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-input-sm {
  padding: 5px 8px;
  font-size: 12px;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.required {
  color: var(--color-error);
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}

.badge-draft { background: #fef3c7; color: #b45309; }
.badge-transit { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
.badge-received { background: #dcfce7; color: #15803d; }
.badge-partial { background: #ffedd5; color: #c2410c; }
.badge-cancelled { background: #f3f4f6; color: #6b7280; }
.badge-loss { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-batch { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
.badge-xs { font-size: 10px; padding: 1px 5px; }

/* Button Styles */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-primary);
  color: #fff;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-receive {
  background: #16a34a;
}

.btn-receive:hover:not(:disabled) {
  background: #15803d;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-outline:hover {
  background: var(--bg-surface-hover);
}

.btn-danger-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--color-error);
  border: 1px solid #fecaca;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-danger-outline:hover {
  background: #fef2f2;
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-error);
  color: #fff;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 5px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.btn-icon-danger:hover {
  background: #fee2e2;
  color: var(--color-error);
}

.btn-icon-only {
  padding: 8px;
}

.btn-sm {
  padding: 5px 10px;
  font-size: 12px;
}

.btn-xs {
  padding: 2px 4px;
}

/* Typography & Layout Utilities */
.font-mono { font-family: 'JetBrains Mono', monospace; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.col-num { text-align: right; }
.text-center { text-align: center; }
.text-xs { font-size: 11px; }
.text-sm { font-size: 12px; }
.text-muted { color: var(--text-muted); }
.text-primary { color: var(--color-primary); }
.text-success { color: #16a34a; }
.text-danger { color: #dc2626; }
.text-warning { color: #d97706; }
.icon-xxs { font-size: 12px; }
.icon-xs { font-size: 14px; }
.icon-sm { font-size: 18px; }
.icon-md { font-size: 24px; }
.w-8 { width: 32px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mb-3 { margin-bottom: 12px; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spin {
  animation: spin 1s linear infinite;
}

/* RTL Layout Adaptations */
[dir="rtl"] .data-table th,
[dir="rtl"] .data-table td,
[dir="rtl"] .receive-table th,
[dir="rtl"] .receive-table td,
[dir="rtl"] .preview-table th,
[dir="rtl"] .preview-table td {
  text-align: right;
}

[dir="rtl"] .col-num {
  text-align: left;
}

[dir="rtl"] .text-center {
  text-align: center;
}

[dir="rtl"] .route-arrow {
  transform: rotate(180deg);
}

[dir="rtl"] .header-actions,
[dir="rtl"] .modal-footer,
[dir="rtl"] .transfer-table-footer,
[dir="rtl"] .receive-totals-bar {
  flex-direction: row-reverse;
}

@media (max-width: 1024px) {
  .grid-overview {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .grid-overview {
    grid-template-columns: 1fr;
  }
  .stepper-wrap {
    flex-direction: column;
    align-items: flex-start;
  }
  .step-line {
    display: none;
  }
}
</style>

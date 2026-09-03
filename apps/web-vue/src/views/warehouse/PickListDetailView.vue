<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load(true)" />
    <template v-else-if="pickList">
      <!-- Top navigation & header -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/warehouse/pick-lists')">&larr; {{ t('back-to-pick-lists', 'Back to Pick Lists') }}</button>
          <div class="flex items-center gap-3">
            <h1 class="page-title">{{ t('pick-list', 'Pick List') }} {{ pickList.pick_list_number }}</h1>
            <span class="badge badge-fefo">
              <span class="material-symbols-outlined icon-xs">bolt</span>
              {{ t('fefo-picking-badge', 'FEFO Picking') }}
            </span>
            <span v-if="hasCatchWeightItems" class="badge badge-cw">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ t('dual-uom-catch-weight', 'Dual UOM / Catch-Weight') }}
            </span>
          </div>
        </div>
        <div class="flex gap-2 items-center">
          <button
            v-if="pickList.status === 'In Progress'"
            class="btn-secondary flex items-center gap-1"
            @click="showCameraScanner = true"
            :title="t('open-camera-scanner', 'Open Camera Barcode Scanner')"
          >
            <span class="material-symbols-outlined icon-xs">photo_camera</span>
            {{ t('camera-scan', 'Camera Scan') }}
          </button>
          <button v-if="hasUnapprovedDiscrepancies" class="btn-warning" @click="openSupervisorApprovalModal(null)" :title="t('approve-all-discrepancies-hint', 'Approve out-of-tolerance weight discrepancies')">
            <span class="material-symbols-outlined icon-xs">verified_user</span>
            {{ t('approve-discrepancies', 'Approve Discrepancies') }} ({{ discrepantItems.length }})
          </button>
          <button v-if="pickList.status === 'Pending'" class="btn-primary" @click="startPicking">
            <span class="material-symbols-outlined">play_arrow</span> {{ t('start-picking', 'Start Picking') }}
          </button>
          <button
            v-if="pickList.status === 'In Progress'"
            class="btn-primary"
            @click="completePicking"
            :disabled="!allPicked || hasUnapprovedDiscrepancies || completing"
            :title="hasUnapprovedDiscrepancies ? t('cannot-complete-discrepancy', 'Cannot complete: Unapproved catch-weight tolerance discrepancies exist') : ''"
          >
            <span v-if="completing" class="material-symbols-outlined spin">progress_activity</span>
            <span v-else class="material-symbols-outlined">check_circle</span>
            {{ completing ? t('completing', 'Completing...') : t('complete-picking', 'Complete Picking') }}
          </button>
        </div>
      </div>

      <!-- Out-of-Tolerance Discrepancy Alert Banner -->
      <div v-if="hasUnapprovedDiscrepancies" class="discrepancy-banner mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined discrepancy-icon">warning</span>
          <div class="flex-1">
            <h4 class="discrepancy-title">
              {{ t('tolerance-discrepancy-title', 'Catch-Weight Tolerance Discrepancy Detected') }}
              <span class="discrepancy-count">({{ discrepantItems.length }} {{ discrepantItems.length === 1 ? 'item' : 'items' }})</span>
            </h4>
            <p class="discrepancy-desc">
              {{ t('tolerance-discrepancy-desc', 'One or more weighed items deviate beyond the allowed tolerance percentage (+/- tolerance limit). Supervisor approval is required before completing this pick list and generating invoices.') }}
            </p>
          </div>
          <button class="btn-warning btn-sm" @click="openSupervisorApprovalModal(null)">
            <span class="material-symbols-outlined icon-xs">verified_user</span>
            {{ t('approve-all', 'Approve Discrepancies') }}
          </button>
        </div>
      </div>

      <!-- Pick List Summary Card -->
      <div class="detail-card mb-4">
        <div class="grid-stats">
          <div class="info-row">
            <span class="info-label">{{ t('status', 'Status') }}:</span>
            <span class="badge" :class="statusBadge">{{ pickList.status }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('order', 'Order') }}:</span>
            <a class="order-link" @click="$router.push(`/sales/${pickList.sales_order_id}`)">#{{ pickList.sales_order_id }}</a>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('warehouse', 'Warehouse') }}:</span>
            <span>{{ warehouseName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('progress', 'Progress') }}:</span>
            <span class="font-bold">{{ pickList.progress_pct || 0 }}%</span>
          </div>
          <div v-if="hasCatchWeightItems" class="info-row">
            <span class="info-label">{{ t('weighed-total', 'Actual Weight') }}:</span>
            <span class="font-bold text-cw">
              {{ formatNumber(totalCatchWeight) }} / {{ formatNumber(totalNominalWeight) }} {{ catchWeightUnit }}
            </span>
          </div>
          <div v-if="hasCatchWeightItems" class="info-row">
            <span class="info-label">{{ t('tolerance-status', 'Tolerance') }}:</span>
            <span v-if="hasUnapprovedDiscrepancies" class="badge badge-tolerance-out">
              <span class="material-symbols-outlined icon-xs">warning</span>
              {{ discrepantItems.length }} {{ t('discrepancy', 'Discrepancy') }}
            </span>
            <span v-else-if="hasApprovedDiscrepancies" class="badge badge-tolerance-approved">
              <span class="material-symbols-outlined icon-xs">verified</span>
              {{ t('approved', 'Approved') }}
            </span>
            <span v-else class="badge badge-tolerance-within">
              <span class="material-symbols-outlined icon-xs">check_circle</span>
              {{ t('normal', 'Normal') }}
            </span>
          </div>
        </div>

        <div class="progress-bar-wrap mt-3">
          <div class="progress-bar" :style="{ width: (pickList.progress_pct || 0) + '%' }"></div>
        </div>
        <div class="flex justify-between text-xs text-muted mt-1">
          <span>{{ pickedLinesCount }} / {{ items.length }} {{ t('items-picked', 'lines completed') }}</span>
          <span>{{ totalPickedQty }} / {{ totalOrderedQty }} {{ t('units-picked', 'units picked') }}</span>
        </div>
      </div>

      <!-- Quick Barcode / Lot Scanner Bar for In Progress Picking -->
      <div v-if="pickList.status === 'In Progress'" class="scanner-card mb-4" :class="{ 'flash-success': flashState === 'success', 'flash-error': flashState === 'error' }">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined scanner-icon">qr_code_scanner</span>
          <div class="flex-1">
            <div class="flex justify-between items-center mb-1">
              <label class="scanner-label">{{ t('quick-scan', 'USB / Bluetooth & Camera Barcode Scanner') }}</label>
              <div class="flex items-center gap-2 text-xs">
                <span class="badge badge-scanner-active" :title="t('scanner-listener-active', 'Hardware scanner listener active')">
                  <span class="status-pulse"></span>
                  {{ t('scanner-ready', 'Scanner Active') }}
                </span>
                <button
                  type="button"
                  class="btn-icon btn-xs"
                  @click="soundEnabled = !soundEnabled"
                  :title="soundEnabled ? t('mute-audio', 'Mute scan audio') : t('unmute-audio', 'Unmute scan audio')"
                >
                  <span class="material-symbols-outlined icon-xs">{{ soundEnabled ? 'volume_up' : 'volume_off' }}</span>
                </button>
              </div>
            </div>
            <div class="flex gap-2">
              <input
                type="text"
                v-model="globalScan"
                class="form-input scanner-input"
                :placeholder="t('scan-placeholder', 'Scan barcode or type lot number then press Enter to pick...')"
                @keyup.enter="onGlobalScan"
              />
              <button class="btn-secondary" @click="onGlobalScan" :disabled="!globalScan.trim()">
                <span class="material-symbols-outlined">search</span> {{ t('match-lot', 'Match & Pick') }}
              </button>
              <button class="btn-primary btn-camera-trigger" @click="showCameraScanner = true" :title="t('open-camera', 'Scan via Camera')">
                <span class="material-symbols-outlined icon-xs">photo_camera</span> {{ t('camera', 'Camera') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Items to Pick Table -->
      <div class="data-card">
        <div class="card-header flex justify-between items-center">
          <div>
            <h3 class="card-title">{{ t('items-to-pick', 'Items to Pick') }}</h3>
            <p class="card-subtitle">{{ t('items-fefo-desc', 'FEFO-suggested lots based on earliest expiration dates. Record scale weight for catch-weight items.') }}</p>
          </div>
          <div v-if="pickList.status === 'In Progress'" class="flex gap-2">
            <button class="btn-outline btn-sm" @click="pickAllRemaining">
              <span class="material-symbols-outlined icon-xs">done_all</span> {{ t('pick-all-suggested', 'Pick All Suggested') }}
            </button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-8">#</th>
                <th>{{ t('product', 'Product') }}</th>
                <th>{{ t('suggested-fefo-lot', 'Suggested Lot (FEFO)') }}</th>
                <th>{{ t('expiry-date', 'Expiry Date') }}</th>
                <th>{{ t('picked-lot-override', 'Picked Lot Selection') }}</th>
                <th class="col-num">{{ t('qty-ordered', 'Ordered') }}</th>
                <th class="col-num">{{ t('qty-picked', 'Picked') }}</th>
                <th>{{ t('scale-weight', 'Scale Weight (Dual UOM)') }}</th>
                <th class="text-center" v-if="pickList.status === 'In Progress'">{{ t('pick-action', 'Action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id" :class="{ 'row-picked': isItemFullyPicked(item), 'row-discrepancy': isItemOut(item) }">
                <td class="cell-mono">{{ item.line_number }}</td>
                <td>
                  <div class="flex items-center gap-2 flex-wrap">
                    <strong>{{ item.product_name || `#${item.product_id}` }}</strong>
                    <span v-if="isCatchWeightItem(item)" class="badge badge-cw" :title="t('dual-uom-item', 'Catch-weight item with actual scale weight pricing')">
                      <span class="material-symbols-outlined icon-xs">scale</span>
                      {{ t('catch-weight-item', 'Catch Weight') }}
                    </span>
                  </div>
                  <div class="text-muted text-xs flex items-center gap-2 mt-1">
                    <span v-if="item.product_id">ID: #{{ item.product_id }}</span>
                    <span v-if="isCatchWeightItem(item) && item.tolerance_pct != null" class="badge-tol">
                      {{ t('tol-limit', 'Tol') }}: ±{{ item.tolerance_pct }}%
                    </span>
                  </div>
                </td>

                <!-- Suggested FEFO Lot -->
                <td>
                  <div v-if="item.batch_number" class="flex items-center gap-1">
                    <span class="badge badge-batch">
                      <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                      {{ item.batch_number }}
                    </span>
                  </div>
                  <span v-else class="text-muted text-xs">{{ t('none', 'Standard Stock') }}</span>
                </td>

                <!-- Suggested Expiry Date -->
                <td>
                  <div v-if="item.expiry_date" :class="getExpiryClass(item.expiry_date)">
                    <span>{{ formatDate(item.expiry_date) }}</span>
                    <span v-if="isExpired(item.expiry_date)" class="badge-tag-danger">{{ t('expired', 'EXPIRED') }}</span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Picked Lot / Alternative Lot Selector -->
                <td>
                  <!-- While picking is In Progress: dropdown + scan override -->
                  <div v-if="pickList.status === 'In Progress'" class="lot-picker-cell">
                    <div class="lot-controls">
                      <!-- Dropdown of available lots -->
                      <select
                        class="form-input form-input-sm lot-select"
                        :value="lineState[item.id]?.selectedBatchId || ''"
                        @change="onBatchSelect(item, $event.target.value)"
                      >
                        <option value="">
                          {{ item.batch_number ? `Suggested (${item.batch_number})` : '-- Select Alternative Lot --' }}
                        </option>
                        <option
                          v-for="b in (availableBatches[item.id] || [])"
                          :key="b.id"
                          :value="b.id"
                        >
                          Lot: {{ b.batch_number }} (Exp: {{ formatDate(b.expiry_date) }}, Stock: {{ b.quantity }})
                        </option>
                      </select>

                      <!-- Inline Scan or manual entry toggle/input -->
                      <div class="flex items-center gap-1 mt-1">
                        <input
                          type="text"
                          class="form-input form-input-xs batch-input"
                          :placeholder="t('scan-lot-or-manual', 'Scan / Manual Lot #')"
                          v-model="lineState[item.id].scanInput"
                          @keyup.enter="onScanLot(item)"
                        />
                        <button
                          type="button"
                          class="btn-icon btn-xs"
                          :title="t('apply-lot', 'Apply Scanned Lot')"
                          @click="onScanLot(item)"
                          :disabled="!lineState[item.id]?.scanInput?.trim()"
                        >
                          <span class="material-symbols-outlined icon-xs">check</span>
                        </button>
                      </div>

                      <!-- Current active selection indicator -->
                      <div v-if="lineState[item.id]?.selectedBatchNumber" class="selected-batch-indicator mt-1">
                        <span class="badge badge-picked-lot" :class="{ 'badge-override': lineState[item.id]?.selectedBatchNumber !== item.batch_number }">
                          <span class="material-symbols-outlined icon-xs">
                            {{ lineState[item.id]?.selectedBatchNumber === item.batch_number ? 'check_circle' : 'swap_horiz' }}
                          </span>
                          Picked Lot: {{ lineState[item.id]?.selectedBatchNumber }}
                          <span v-if="lineState[item.id]?.selectedBatchNumber !== item.batch_number" class="override-tag">{{ t('lot-override', 'OVERRIDE') }}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- Completed or Pending: Display picked lot -->
                  <div v-else>
                    <span v-if="item.picked_batch_number" class="badge badge-batch badge-batch-completed">
                      <span class="material-symbols-outlined icon-xs">verified</span>
                      {{ item.picked_batch_number }}
                    </span>
                    <span v-else-if="item.batch_number" class="badge badge-batch">
                      <span class="material-symbols-outlined icon-xs">qr_code_2</span>
                      {{ item.batch_number }}
                    </span>
                    <span v-else class="text-muted text-xs">-</span>
                  </div>
                </td>

                <td class="col-num font-bold">{{ item.qty_ordered }}</td>
                <td class="col-num" :class="{ 'text-green': item.qty_picked >= item.qty_ordered }">
                  {{ item.qty_picked }}
                </td>

                <!-- Scale Weight / Dual UOM Column -->
                <td>
                  <!-- Catch-Weight item display / inputs -->
                  <div v-if="isCatchWeightItem(item)" class="scale-weight-cell">
                    <!-- In Progress: Scale Weight Input & Live Variance -->
                    <template v-if="pickList.status === 'In Progress'">
                      <div class="scale-input-row">
                        <div class="scale-input-wrap">
                          <span class="scale-icon material-symbols-outlined">scale</span>
                          <input
                            type="number"
                            class="form-input form-input-sm scale-input"
                            step="any"
                            min="0"
                            :placeholder="t('scale-weight', 'Actual scale weight')"
                            v-model.number="lineState[item.id].catchWeightActual"
                            @keyup.enter="savePick(item)"
                          />
                          <span class="scale-uom-badge">{{ item.catch_weight_uom || 'kg' }}</span>
                        </div>
                      </div>

                      <div class="scale-info-row text-xs mt-1">
                        <span class="text-muted">
                          {{ t('nominal', 'Nominal') }}: <strong>{{ formatNumber(item.nominal_weight) }}</strong> {{ item.catch_weight_uom || 'kg' }}
                        </span>
                      </div>

                      <!-- Live Tolerance Variance Feedback -->
                      <div class="mt-1 flex items-center gap-1 flex-wrap">
                        <!-- Within Tolerance -->
                        <span
                          v-if="getLiveToleranceStatus(item) === 'Within Tolerance'"
                          class="badge badge-tolerance-within"
                          :title="`Variance: ${formatVariance(getLiveVariance(item))}% (Limit: ±${item.tolerance_pct || 0}%)`"
                        >
                          <span class="material-symbols-outlined icon-xs">check_circle</span>
                          {{ formatVariance(getLiveVariance(item)) }}% {{ t('within-tol', 'Within Tol.') }}
                        </span>

                        <!-- Out of Tolerance -->
                        <span
                          v-else-if="getLiveToleranceStatus(item) === 'Out of Tolerance'"
                          class="badge badge-tolerance-out"
                          :title="`Variance: ${formatVariance(getLiveVariance(item))}% exceeds limit ±${item.tolerance_pct || 0}%)`"
                        >
                          <span class="material-symbols-outlined icon-xs">warning</span>
                          {{ formatVariance(getLiveVariance(item)) }}% {{ t('out-of-tol', 'Out of Tol.') }}
                        </span>

                        <!-- Supervisor Approved -->
                        <span
                          v-else-if="getLiveToleranceStatus(item) === 'Approved' || item.supervisor_approved"
                          class="badge badge-tolerance-approved"
                          :title="item.supervisor_notes ? `Approved: ${item.supervisor_notes}` : 'Supervisor Approved'"
                        >
                          <span class="material-symbols-outlined icon-xs">verified</span>
                          {{ t('approved', 'Approved') }} ({{ formatVariance(getLiveVariance(item) ?? item.tolerance_variance_pct) }}%)
                        </span>

                        <!-- Awaiting Weight -->
                        <span
                          v-else
                          class="text-xs text-muted"
                        >
                          {{ t('pending-scale-weight', 'Pending scale weight') }}
                        </span>
                      </div>
                    </template>

                    <!-- Completed / Pending View Mode -->
                    <template v-else>
                      <div class="font-bold flex items-center gap-1">
                        <span v-if="item.catch_weight_actual !== null && item.catch_weight_actual !== undefined">
                          {{ formatNumber(item.catch_weight_actual) }} {{ item.catch_weight_uom || 'kg' }}
                        </span>
                        <span v-else class="text-muted text-xs">{{ t('not-weighed', 'Not weighed') }}</span>
                      </div>

                      <div class="text-xs text-muted mt-1">
                        <span>{{ t('nominal', 'Nominal') }}: {{ formatNumber(item.nominal_weight) }} {{ item.catch_weight_uom || 'kg' }}</span>
                      </div>

                      <div v-if="item.tolerance_status && item.tolerance_status !== 'Not Applicable'" class="mt-1">
                        <span v-if="item.tolerance_status === 'Within Tolerance'" class="badge badge-tolerance-within">
                          <span class="material-symbols-outlined icon-xs">check_circle</span>
                          {{ formatVariance(item.tolerance_variance_pct) }}% Within Tol.
                        </span>
                        <span v-else-if="item.tolerance_status === 'Approved' || item.supervisor_approved" class="badge badge-tolerance-approved" :title="item.supervisor_notes || 'Approved'">
                          <span class="material-symbols-outlined icon-xs">verified</span>
                          {{ formatVariance(item.tolerance_variance_pct) }}% Approved
                        </span>
                        <span v-else-if="item.tolerance_status === 'Out of Tolerance'" class="badge badge-tolerance-out">
                          <span class="material-symbols-outlined icon-xs">warning</span>
                          {{ formatVariance(item.tolerance_variance_pct) }}% Out of Tol.
                        </span>
                      </div>
                    </template>
                  </div>

                  <!-- Standard non-catch-weight item -->
                  <div v-else class="text-muted text-xs">
                    {{ t('standard-unit', 'Standard (Fixed)') }}
                  </div>
                </td>

                <!-- In Progress Pick Actions -->
                <td class="text-center" v-if="pickList.status === 'In Progress'">
                  <div class="pick-actions-wrap">
                    <input
                      type="number"
                      class="pick-input"
                      step="any"
                      min="0"
                      :max="item.qty_ordered"
                      v-model.number="lineState[item.id].pickQty"
                      @keyup.enter="savePick(item)"
                    />
                    <button
                      class="btn-primary btn-sm btn-pick"
                      :disabled="lineState[item.id]?.saving"
                      @click="savePick(item)"
                      :title="t('save-pick', 'Update Pick Quantity and Weighed Amount')"
                    >
                      <span v-if="lineState[item.id]?.saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                      <span v-else class="material-symbols-outlined icon-xs">check</span>
                      {{ t('pick', 'Pick') }}
                    </button>
                    <button
                      v-if="item.qty_picked < item.qty_ordered"
                      class="btn-outline btn-xs"
                      :title="t('pick-full', 'Pick Full Qty')"
                      @click="pickFullQty(item)"
                    >
                      All
                    </button>
                    <button
                      v-if="isItemOut(item)"
                      class="btn-warning btn-xs"
                      :title="t('approve-item-discrepancy', 'Approve tolerance discrepancy for this line')"
                      @click="openSupervisorApprovalModal(item)"
                    >
                      <span class="material-symbols-outlined icon-xs">verified_user</span>
                      {{ t('approve', 'Approve') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Supervisor Approval Modal Dialog -->
      <Teleport to="body">
        <div v-if="showApprovalModal" class="modal-overlay" @click.self="closeApprovalModal">
          <div class="modal-dialog" :dir="dir">
            <div class="modal-header">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-warning">verified_user</span>
                <h3 class="modal-title">{{ t('supervisor-approval-title', 'Supervisor Tolerance Approval') }}</h3>
              </div>
              <button class="modal-close" @click="closeApprovalModal">&times;</button>
            </div>
            <div class="modal-body">
              <p class="modal-intro">
                {{ approvalTargetItem
                  ? t('approve-item-desc', `Approving weight discrepancy for Line #${approvalTargetItem.line_number} (${approvalTargetItem.product_name || 'Item'}):`)
                  : t('approve-all-desc', `Approving ${discrepantItems.length} out-of-tolerance item(s) in pick list ${pickList.pick_list_number}:`)
                }}
              </p>

              <div class="discrepancy-summary-box mb-3">
                <table class="summary-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>{{ t('product', 'Product') }}</th>
                      <th>{{ t('nominal', 'Nominal') }}</th>
                      <th>{{ t('actual', 'Actual') }}</th>
                      <th>{{ t('variance', 'Variance') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="it in (approvalTargetItem ? [approvalTargetItem] : discrepantItems)" :key="it.id">
                      <td class="cell-mono">{{ it.line_number }}</td>
                      <td><strong>{{ it.product_name || `#${it.product_id}` }}</strong></td>
                      <td>{{ formatNumber(it.nominal_weight) }} {{ it.catch_weight_uom || 'kg' }}</td>
                      <td>{{ formatNumber(it.catch_weight_actual !== null && it.catch_weight_actual !== undefined ? it.catch_weight_actual : lineState[it.id]?.catchWeightActual) }} {{ it.catch_weight_uom || 'kg' }}</td>
                      <td>
                        <span class="text-red font-bold">
                          {{ formatVariance(getLiveVariance(it) ?? it.tolerance_variance_pct) }}%
                        </span>
                        <span class="text-xs text-muted"> (±{{ it.tolerance_pct || 0 }}%)</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="form-group mb-3">
                <label class="form-label">{{ t('supervisor-id', 'Supervisor ID / Username') }} <span class="text-red">*</span></label>
                <input
                  type="text"
                  class="form-input w-full"
                  v-model="approvalForm.supervisorId"
                  :placeholder="t('supervisor-id-placeholder', 'Enter supervisor username or employee ID')"
                  required
                />
              </div>

              <div class="form-group mb-3">
                <label class="form-label">{{ t('supervisor-notes', 'Approval Justification Notes') }}</label>
                <textarea
                  class="form-input form-textarea w-full"
                  rows="3"
                  v-model="approvalForm.supervisorNotes"
                  :placeholder="t('supervisor-notes-placeholder', 'Reason for approving weight discrepancy (e.g. customer approved pack variation)...')"
                ></textarea>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-outline" @click="closeApprovalModal" :disabled="approving">
                {{ t('cancel', 'Cancel') }}
              </button>
              <button class="btn-warning" @click="submitApproval" :disabled="approving || !approvalForm.supervisorId.trim()">
                <span v-if="approving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
                <span v-else class="material-symbols-outlined icon-xs">check_circle</span>
                {{ approving ? t('approving', 'Approving...') : t('confirm-approval', 'Approve Discrepancy') }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Camera Barcode Scanner Modal -->
      <CameraBarcodeScannerModal
        v-model="showCameraScanner"
        @scan="(parsed, raw) => handleBarcodeScan(parsed, raw)"
      />

      <!-- Barcode Scan Mismatch Warning Modal -->
      <Teleport to="body">
        <div v-if="showMismatchModal" class="modal-overlay" @click.self="showMismatchModal = false">
          <div class="modal-dialog modal-dialog-warning" :dir="dir">
            <div class="modal-header header-danger">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-red">warning</span>
                <h3 class="modal-title text-red">{{ t('barcode-mismatch-title', 'Barcode Scan Mismatch Warning') }}</h3>
              </div>
              <button class="modal-close" @click="showMismatchModal = false">&times;</button>
            </div>
            <div class="modal-body text-center py-6">
              <div class="mismatch-icon-wrap mb-3">
                <span class="material-symbols-outlined icon-mismatch">qr_code_scanner</span>
              </div>
              <h4 class="font-bold text-lg text-slate-800 mb-2">
                {{ t('unrecognized-barcode', 'Unrecognized or Mismatched Item') }}
              </h4>
              <p class="text-sm text-slate-600 mb-4">
                {{ t('mismatch-desc', 'Scanned barcode does not match any allocated line item or lot in this pick list:') }}
              </p>
              <div class="scanned-code-box mb-4">
                <code>{{ lastMismatchedCode }}</code>
              </div>
              <div class="alert-warning-box">
                <span class="material-symbols-outlined icon-xs">block</span>
                <span>{{ t('staging-prevented', 'Item staging prevented to avoid wrong item shipment.') }}</span>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-primary btn-danger-action" @click="showMismatchModal = false">
                {{ t('acknowledge-dismiss', 'Acknowledge & Dismiss') }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'
import { useBarcodeScanner } from '../../composables/useBarcodeScanner.js'
import { useScanFeedback } from '../../composables/useScanFeedback.js'
import CameraBarcodeScannerModal from '../../components/CameraBarcodeScannerModal.vue'
import { parseBarcode } from '../../utils/barcodeParser.js'

const route = useRoute()
const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// Scan feedback & hardware scanner listeners
const feedback = useScanFeedback()
const { flashState, notifySuccess, notifyError, notifyWarning, soundEnabled } = feedback

const showCameraScanner = ref(false)
const showMismatchModal = ref(false)
const lastMismatchedCode = ref('')

const scanner = useBarcodeScanner({
  onScan: (parsedBarcode, rawString) => {
    handleBarcodeScan(parsedBarcode, rawString)
  },
  ignoreInputs: false,
  endKeys: ['Enter']
})

const loading = ref(true)
const completing = ref(false)
const approving = ref(false)
const error = ref('')
const pickList = ref(null)
const items = ref([])
const warehouses = ref([])
const availableBatches = ref({})
const lineState = reactive({})
const globalScan = ref('')

// Supervisor approval modal state
const showApprovalModal = ref(false)
const approvalTargetItem = ref(null)
const approvalForm = reactive({
  supervisorId: '1',
  supervisorNotes: ''
})

const statusBadge = computed(() => {
  const map = {
    Pending: 'badge-warning',
    'In Progress': 'badge-info',
    Completed: 'badge-active',
    Cancelled: 'badge-inactive'
  }
  return map[pickList.value?.status] || 'badge-inactive'
})

const warehouseName = computed(() => {
  if (!pickList.value?.warehouse_id) return '-'
  const w = warehouses.value.find(x => x.id === pickList.value.warehouse_id)
  return w ? w.name : `#${pickList.value.warehouse_id}`
})

const allPicked = computed(() => {
  return items.value.length > 0 && items.value.every(i => (i.qty_picked || 0) >= (i.qty_ordered || 0))
})

const pickedLinesCount = computed(() => {
  return items.value.filter(i => (i.qty_picked || 0) >= (i.qty_ordered || 0)).length
})

const totalOrderedQty = computed(() => {
  return items.value.reduce((acc, i) => acc + (Number(i.qty_ordered) || 0), 0)
})

const totalPickedQty = computed(() => {
  return items.value.reduce((acc, i) => acc + (Number(i.qty_picked) || 0), 0)
})

const hasCatchWeightItems = computed(() => {
  return items.value.some(isCatchWeightItem)
})

const catchWeightUnit = computed(() => {
  const cw = items.value.find(i => i.catch_weight_uom)
  return cw?.catch_weight_uom || 'kg'
})

const totalCatchWeight = computed(() => {
  return items.value
    .filter(isCatchWeightItem)
    .reduce((acc, i) => {
      const act = lineState[i.id]?.catchWeightActual !== undefined && lineState[i.id]?.catchWeightActual !== '' && lineState[i.id]?.catchWeightActual !== null
        ? Number(lineState[i.id].catchWeightActual)
        : (i.catch_weight_actual !== null && i.catch_weight_actual !== undefined ? Number(i.catch_weight_actual) : 0)
      return acc + (act || 0)
    }, 0)
})

const totalNominalWeight = computed(() => {
  return items.value
    .filter(isCatchWeightItem)
    .reduce((acc, i) => acc + (Number(i.nominal_weight) || 0), 0)
})

const discrepantItems = computed(() => {
  return items.value.filter(isItemOut)
})

const hasUnapprovedDiscrepancies = computed(() => {
  return discrepantItems.value.length > 0
})

const hasApprovedDiscrepancies = computed(() => {
  return items.value.some(i => i.supervisor_approved)
})

function isCatchWeightItem(item) {
  if (!item) return false
  return Boolean(
    item.catch_weight_uom ||
    (item.nominal_weight !== null && item.nominal_weight !== undefined) ||
    (item.tolerance_pct !== null && item.tolerance_pct !== undefined) ||
    item.is_catch_weight
  )
}

function formatNumber(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val) || val === '') return '-'
  return Number(val).toFixed(decimals)
}

function formatVariance(val) {
  if (val === null || val === undefined || isNaN(val)) return '0.00'
  const num = Number(val)
  return num > 0 ? `+${num.toFixed(2)}` : num.toFixed(2)
}

function getLiveVariance(item) {
  if (!item) return null
  const state = lineState[item.id]
  let actual = null
  if (state && state.catchWeightActual !== '' && state.catchWeightActual !== null && state.catchWeightActual !== undefined) {
    actual = Number(state.catchWeightActual)
  } else if (item.catch_weight_actual !== null && item.catch_weight_actual !== undefined) {
    actual = Number(item.catch_weight_actual)
  }

  if (actual === null || isNaN(actual)) return null
  const nominal = item.nominal_weight !== null && item.nominal_weight !== undefined ? Number(item.nominal_weight) : null
  if (nominal === null || nominal <= 0) return null
  return Number((((actual - nominal) / nominal) * 100).toFixed(2))
}

function getLiveToleranceStatus(item) {
  if (!item) return 'Not Applicable'
  if (item.supervisor_approved) return 'Approved'

  const variance = getLiveVariance(item)
  if (variance === null) {
    return item.tolerance_status || 'Not Applicable'
  }

  const tol = item.tolerance_pct !== null && item.tolerance_pct !== undefined ? Number(item.tolerance_pct) : 0
  if (Math.abs(variance) <= (tol + 1e-6)) {
    return 'Within Tolerance'
  }
  return 'Out of Tolerance'
}

function isItemOut(item) {
  if (!item || !isCatchWeightItem(item) || item.supervisor_approved) return false
  const status = getLiveToleranceStatus(item)
  return status === 'Out of Tolerance'
}

function isItemFullyPicked(item) {
  return (item.qty_picked || 0) >= (item.qty_ordered || 0) && item.qty_ordered > 0
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function isExpired(d) {
  if (!d) return false
  return new Date(d) < new Date()
}

function getExpiryClass(d) {
  if (!d) return ''
  if (isExpired(d)) return 'text-red font-semibold'
  const exp = new Date(d)
  const daysUntil = (exp - new Date()) / (1000 * 60 * 60 * 24)
  if (daysUntil <= 30) return 'text-amber font-semibold'
  return 'text-green'
}

async function load(showSkeleton = true) {
  if (showSkeleton) loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [detailRes, whRes] = await Promise.all([
      api.get(`/T0101I/${id}/detail`),
      api.get('/T0008I/').catch(() => ({ data: [] })),
    ])
    const data = detailRes.data
    pickList.value = { ...data }
    items.value = data.items || []
    warehouses.value = whRes.data || []

    // Initialize lineState
    for (const item of items.value) {
      const existing = lineState[item.id]
      lineState[item.id] = {
        pickQty: existing ? existing.pickQty : (item.qty_picked !== undefined && item.qty_picked !== null ? item.qty_picked : item.qty_ordered),
        catchWeightActual: existing && existing.catchWeightActual !== undefined && existing.catchWeightActual !== ''
          ? existing.catchWeightActual
          : (item.catch_weight_actual !== undefined && item.catch_weight_actual !== null ? item.catch_weight_actual : ''),
        selectedBatchId: item.picked_batch_id || item.batch_id || null,
        selectedBatchNumber: item.picked_batch_number || item.batch_number || '',
        scanInput: '',
        saving: false
      }
    }

    // Fetch available batches for all items if In Progress
    if (pickList.value.status === 'In Progress') {
      await Promise.all(
        items.value.map(item => fetchAvailableBatches(item.id))
      )
    }
  } catch (err) {
    console.error('Error loading pick list:', err)
    error.value = t('failed-load', 'Failed to load pick list')
  } finally {
    loading.value = false
  }
}

async function fetchAvailableBatches(itemId) {
  try {
    const res = await api.get(`/T0101I/${pickList.value.id}/items/${itemId}/available-batches`)
    availableBatches.value[itemId] = res.data || []
  } catch {
    availableBatches.value[itemId] = []
  }
}

function onBatchSelect(item, batchId) {
  const state = lineState[item.id]
  if (!state) return

  if (!batchId) {
    // Reset to suggested batch
    state.selectedBatchId = item.batch_id || null
    state.selectedBatchNumber = item.batch_number || ''
    return
  }

  const numId = Number(batchId)
  const batches = availableBatches.value[item.id] || []
  const found = batches.find(b => b.id === numId)
  if (found) {
    state.selectedBatchId = found.id
    state.selectedBatchNumber = found.batch_number
    toast(`Selected lot ${found.batch_number}`, 'info')
  }
}

function onScanLot(item) {
  const state = lineState[item.id]
  if (!state) return
  const scanned = (state.scanInput || '').trim()
  if (!scanned) return

  const batches = availableBatches.value[item.id] || []
  const matched = batches.find(b => (b.batch_number || '').toLowerCase() === scanned.toLowerCase())

  if (matched) {
    state.selectedBatchId = matched.id
    state.selectedBatchNumber = matched.batch_number
    toast(`Matched available lot ${matched.batch_number}`, 'success')
  } else {
    // Custom/external lot barcode
    state.selectedBatchId = null
    state.selectedBatchNumber = scanned
    toast(`Lot override set to "${scanned}"`, 'info')
  }
  state.scanInput = ''
}

function handleBarcodeScan(parsed, rawString) {
  if (pickList.value?.status !== 'In Progress') {
    toast(t('picking-not-in-progress', 'Picking is not in progress'), 'warning')
    return
  }

  const rawCode = (rawString || (typeof parsed === 'string' ? parsed : parsed?.raw) || '').trim()
  if (!rawCode) return

  const parsedObj = (typeof parsed === 'object' && parsed !== null) ? parsed : parseBarcode(rawCode)

  const gtin = parsedObj.gtin || parsedObj.code || rawCode
  const aiBatch = parsedObj.aiData?.['10'] || parsedObj.batchNumber || null
  const aiExpiry = parsedObj.aiData?.['17'] || parsedObj.expiryDate || null

  let matchedItem = null
  let matchedBatch = null

  const normRaw = rawCode.toLowerCase().replace(/^0+/, '')
  const normGtin = (gtin || '').toLowerCase().replace(/^0+/, '')

  // 1. Check direct match by product barcode, GTIN, product_id, sku
  matchedItem = items.value.find(i => {
    const pCode = (i.barcode || i.product_barcode || i.gtin || i.sku || '').toLowerCase()
    const normPCode = pCode.replace(/^0+/, '')
    const rCode = rawCode.toLowerCase()
    const gCode = (gtin || '').toLowerCase()
    return (
      (pCode && (pCode === rCode || pCode === gCode || (normPCode && (normPCode === normRaw || normPCode === normGtin)))) ||
      String(i.product_id) === rawCode ||
      String(i.product_id) === gtin ||
      (normRaw && String(i.product_id) === normRaw)
    )
  })

  // 2. If not found by product identifier, check lot / batch number (GS1 AI 10 or rawCode)
  const targetBatch = (aiBatch || rawCode).toLowerCase()
  if (!matchedItem) {
    for (const item of items.value) {
      const batches = availableBatches.value[item.id] || []
      const b = batches.find(x => (x.batch_number || '').toLowerCase() === targetBatch)
      if (b) {
        matchedItem = item
        matchedBatch = b
        break
      }
      if ((item.batch_number || '').toLowerCase() === targetBatch) {
        matchedItem = item
        break
      }
    }
  }

  // 3. Fallback fuzzy search by product name
  if (!matchedItem) {
    const lowerRaw = rawCode.toLowerCase()
    matchedItem = items.value.find(i =>
      i.product_name && i.product_name.toLowerCase().includes(lowerRaw)
    )
  }

  // Evaluate match result
  if (matchedItem) {
    const state = lineState[matchedItem.id]
    if (state) {
      // 1. GS1 Expiry Date Validation (AI 17 / AI 15)
      if (aiExpiry && isExpired(aiExpiry)) {
        lastMismatchedCode.value = `${rawCode} (Expired: ${aiExpiry})`
        showMismatchModal.value = true
        notifyError(t('scanned-batch-expired', `Scanned batch is EXPIRED (${aiExpiry})! Cannot pick expired items.`))
        globalScan.value = ''
        return
      }

      // 2. GS1 Batch / Lot FEFO Validation
      const batches = availableBatches.value[matchedItem.id] || []

      if (matchedBatch) {
        if (matchedBatch.expiry_date && isExpired(matchedBatch.expiry_date)) {
          lastMismatchedCode.value = `${rawCode} (Expired Lot: ${matchedBatch.batch_number})`
          showMismatchModal.value = true
          notifyError(t('scanned-batch-expired', `Lot "${matchedBatch.batch_number}" is EXPIRED (${formatDate(matchedBatch.expiry_date)})! Cannot pick expired items.`))
          globalScan.value = ''
          return
        }

        state.selectedBatchId = matchedBatch.id
        state.selectedBatchNumber = matchedBatch.batch_number

        if (matchedItem.batch_number && (matchedBatch.batch_number || '').toLowerCase() !== matchedItem.batch_number.toLowerCase()) {
          notifyWarning(t('fefo-lot-override-notice', `FEFO Warning: Scanned lot "${matchedBatch.batch_number}" overrides allocated lot "${matchedItem.batch_number}".`))
        }
      } else if (aiBatch) {
        const normAiBatch = aiBatch.toLowerCase()
        const isAllocatedMatch = matchedItem.batch_number && matchedItem.batch_number.toLowerCase() === normAiBatch
        const foundAi = batches.find(b => (b.batch_number || '').toLowerCase() === normAiBatch)

        if (isAllocatedMatch) {
          state.selectedBatchId = matchedItem.batch_id || null
          state.selectedBatchNumber = matchedItem.batch_number
        } else if (foundAi) {
          if (foundAi.expiry_date && isExpired(foundAi.expiry_date)) {
            lastMismatchedCode.value = `${rawCode} (Expired Lot: ${foundAi.batch_number})`
            showMismatchModal.value = true
            notifyError(t('scanned-batch-expired', `Lot "${foundAi.batch_number}" is EXPIRED (${formatDate(foundAi.expiry_date)})! Cannot pick expired items.`))
            globalScan.value = ''
            return
          }

          state.selectedBatchId = foundAi.id
          state.selectedBatchNumber = foundAi.batch_number
          notifyWarning(t('fefo-lot-override-notice', `FEFO Warning: Scanned lot "${foundAi.batch_number}" overrides allocated lot "${matchedItem.batch_number}".`))
        } else if (batches.length > 0 || matchedItem.batch_number) {
          // Scanned GS1 batch number does not exist in allocated or available warehouse stock for this item
          lastMismatchedCode.value = `${rawCode} (Unallocated Lot: ${aiBatch})`
          showMismatchModal.value = true
          notifyError(t('unallocated-gs1-batch', `Scanned lot "${aiBatch}" is not allocated or available in warehouse stock for ${matchedItem.product_name || 'this item'}!`))
          globalScan.value = ''
          return
        } else {
          // Custom/external lot barcode
          state.selectedBatchId = null
          state.selectedBatchNumber = aiBatch
        }
      }

      // Check if item is already fully picked
      if ((matchedItem.qty_picked >= matchedItem.qty_ordered || state.pickQty >= matchedItem.qty_ordered) && matchedItem.qty_ordered > 0) {
        notifyWarning(t('item-already-picked', `Item "${matchedItem.product_name || 'item'}" is already fully picked`))
        globalScan.value = ''
        return
      }

      // Increment pick quantity by 1 unit (up to qty_ordered)
      const currentPicked = Math.max(matchedItem.qty_picked || 0, state.pickQty || 0)
      state.pickQty = Math.min(matchedItem.qty_ordered, currentPicked + 1)

      // Handle catch-weight default weight if not set
      if (isCatchWeightItem(matchedItem) && (state.catchWeightActual === '' || state.catchWeightActual === null || state.catchWeightActual === undefined)) {
        if (matchedItem.nominal_weight !== null && matchedItem.nominal_weight !== undefined) {
          state.catchWeightActual = matchedItem.nominal_weight
        }
      }

      // Save pick and trigger audio/visual confirmation
      savePick(matchedItem)
      notifySuccess(t('scan-pick-success', `Scanned ${rawCode} - picked line #${matchedItem.line_number} (${matchedItem.product_name || 'item'})`))
      globalScan.value = ''
      return
    }
  }

  // No match found -> Trigger Error Buzzer & Mismatch Warning Modal
  lastMismatchedCode.value = rawCode
  showMismatchModal.value = true
  notifyError(t('scan-mismatch-error', `Barcode scan mismatch: "${rawCode}" is not in this pick list!`))
  globalScan.value = ''
}

function onGlobalScan() {
  const code = globalScan.value.trim()
  if (!code) return
  handleBarcodeScan(null, code)
}

async function savePick(item) {
  const state = lineState[item.id]
  if (!state) return

  const qty = parseFloat(state.pickQty)
  if (isNaN(qty) || qty < 0) {
    toast(t('invalid-qty', 'Please enter a valid pick quantity'), 'error')
    return
  }
  if (qty > item.qty_ordered) {
    toast(`Picked quantity (${qty}) cannot exceed ordered quantity (${item.qty_ordered})`, 'error')
    return
  }

  state.saving = true
  try {
    const payload = {
      qty_picked: qty,
      picked_batch_id: state.selectedBatchId !== null && state.selectedBatchId !== undefined ? Number(state.selectedBatchId) : null,
      picked_batch_number: state.selectedBatchNumber ? String(state.selectedBatchNumber).trim() : null
    }

    // Include catch-weight scale weight parameters if applicable
    if (isCatchWeightItem(item)) {
      if (state.catchWeightActual !== '' && state.catchWeightActual !== null && state.catchWeightActual !== undefined) {
        payload.catch_weight_actual = parseFloat(state.catchWeightActual)
      }
      if (item.catch_weight_uom) {
        payload.catch_weight_uom = item.catch_weight_uom
      }
      if (item.nominal_weight !== null && item.nominal_weight !== undefined) {
        payload.nominal_weight = item.nominal_weight
      }
      if (item.tolerance_pct !== null && item.tolerance_pct !== undefined) {
        payload.tolerance_pct = item.tolerance_pct
      }
    }

    const res = await api.post(`/T0101I/${pickList.value.id}/pick-item/${item.id}`, payload)
    item.qty_picked = res.data.qty_picked
    item.picked_batch_id = res.data.picked_batch_id
    item.picked_batch_number = res.data.picked_batch_number
    item.catch_weight_actual = res.data.catch_weight_actual
    item.catch_weight_uom = res.data.catch_weight_uom
    item.nominal_weight = res.data.nominal_weight
    item.tolerance_pct = res.data.tolerance_pct
    item.tolerance_variance_pct = res.data.tolerance_variance_pct
    item.tolerance_status = res.data.tolerance_status
    item.supervisor_approved = res.data.supervisor_approved
    item.supervisor_approved_by = res.data.supervisor_approved_by
    item.supervisor_approved_at = res.data.supervisor_approved_at
    item.supervisor_notes = res.data.supervisor_notes

    toast(t('pick-updated', `Line #${item.line_number} pick recorded`, item.line_number), 'success')
    await load(false)
  } catch (e) {
    console.error('Pick error:', e)
    toast(e.response?.data?.detail || t('failed-pick', 'Failed to update pick'), 'error')
  } finally {
    state.saving = false
  }
}

function pickFullQty(item) {
  const state = lineState[item.id]
  if (!state) return
  state.pickQty = item.qty_ordered
  if (!state.selectedBatchId && item.batch_id) {
    state.selectedBatchId = item.batch_id
    state.selectedBatchNumber = item.batch_number
  }
  if (isCatchWeightItem(item) && (state.catchWeightActual === '' || state.catchWeightActual === null || state.catchWeightActual === undefined)) {
    if (item.nominal_weight !== null && item.nominal_weight !== undefined) {
      state.catchWeightActual = item.nominal_weight
    }
  }
  savePick(item)
}

async function pickAllRemaining() {
  const pendingItems = items.value.filter(i => (i.qty_picked || 0) < (i.qty_ordered || 0))
  if (!pendingItems.length) {
    toast(t('all-already-picked', 'All items are already fully picked'), 'info')
    return
  }

  for (const item of pendingItems) {
    const state = lineState[item.id]
    if (state) {
      state.pickQty = item.qty_ordered
      if (!state.selectedBatchId && item.batch_id) {
        state.selectedBatchId = item.batch_id
        state.selectedBatchNumber = item.batch_number
      }
      const payload = {
        qty_picked: item.qty_ordered,
        picked_batch_id: state.selectedBatchId,
        picked_batch_number: state.selectedBatchNumber
      }
      if (isCatchWeightItem(item)) {
        const wt = (state.catchWeightActual !== '' && state.catchWeightActual !== null && state.catchWeightActual !== undefined)
          ? parseFloat(state.catchWeightActual)
          : item.nominal_weight
        if (wt !== null && wt !== undefined) {
          payload.catch_weight_actual = wt
        }
        if (item.catch_weight_uom) payload.catch_weight_uom = item.catch_weight_uom
        if (item.nominal_weight !== null) payload.nominal_weight = item.nominal_weight
        if (item.tolerance_pct !== null) payload.tolerance_pct = item.tolerance_pct
      }
      try {
        await api.post(`/T0101I/${pickList.value.id}/pick-item/${item.id}`, payload)
      } catch (err) {
        console.error('Error picking item:', err)
      }
    }
  }
  toast(t('all-picked-success', 'All suggested lots picked successfully'), 'success')
  await load(false)
}

function openSupervisorApprovalModal(item = null) {
  approvalTargetItem.value = item
  approvalForm.supervisorId = '1'
  approvalForm.supervisorNotes = ''
  showApprovalModal.value = true
}

function closeApprovalModal() {
  showApprovalModal.value = false
  approvalTargetItem.value = null
}

async function submitApproval() {
  if (!approvalForm.supervisorId.trim()) {
    toast(t('supervisor-id-required', 'Supervisor ID is required'), 'error')
    return
  }
  approving.value = true
  try {
    const payload = {
      supervisor_id: approvalForm.supervisorId.trim(),
      supervisor_notes: approvalForm.supervisorNotes.trim() || undefined
    }

    if (approvalTargetItem.value) {
      payload.item_id = approvalTargetItem.value.id
      await api.post(`/T0101I/${pickList.value.id}/approve-tolerance`, payload)
      toast(t('item-approved-success', `Line #${approvalTargetItem.value.line_number} tolerance discrepancy approved`), 'success')
    } else {
      await api.post(`/T0101I/${pickList.value.id}/approve-tolerance`, payload)
      toast(t('all-approved-success', 'All tolerance discrepancies approved successfully'), 'success')
    }
    closeApprovalModal()
    await load(false)
  } catch (err) {
    console.error('Approval error:', err)
    toast(err.response?.data?.detail || t('approval-failed', 'Failed to approve tolerance discrepancy'), 'error')
  } finally {
    approving.value = false
  }
}

async function startPicking() {
  try {
    await api.post(`/T0101I/${pickList.value.id}/start`)
    toast(t('picking-started', 'Picking started'), 'success')
    await load(false)
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-start', 'Failed to start picking'), 'error')
  }
}

async function completePicking() {
  if (hasUnapprovedDiscrepancies.value) {
    toast(t('cannot-complete-discrepancy', 'Cannot complete picking: Unapproved catch-weight tolerance discrepancies exist'), 'error')
    return
  }
  completing.value = true
  try {
    await api.post(`/T0101I/${pickList.value.id}/complete`)
    toast(t('picking-completed', 'Pick list completed — sales order marked as shipped and lot inventory deducted'), 'success')
    await load(false)
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-complete', 'Failed to complete picking'), 'error')
  } finally {
    completing.value = false
  }
}

onMounted(() => {
  load(true)
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mb-4 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 12px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-wrap { flex-wrap: wrap; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.block { display: block; }
.w-8 { width: 32px; }
.w-full { width: 100%; }

.text-muted { color: #888; }
.text-xs { font-size: 11px; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.text-green { color: #16a34a; }
.text-amber { color: #d97706; }
.text-red { color: #dc2626; }
.text-warning { color: #d97706; }
.text-cw { color: #5d3fd3; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.order-link { color: #5d3fd3; cursor: pointer; font-weight: 600; }
.order-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-warning { display: inline-flex; align-items: center; gap: 6px; background: #d97706; color: #fff; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-warning:hover:not(:disabled) { background: #b45309; }
.btn-warning:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { display: inline-flex; align-items: center; gap: 6px; background: #f0f0f4; color: #333; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover:not(:disabled) { background: #e2e2ea; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-outline { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; background: transparent; color: #5d3fd3; border: 1px solid #ddd6fe; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f3ff; }

.btn-sm { padding: 5px 12px; font-size: 12px; }
.btn-xs { padding: 3px 8px; font-size: 11px; }

.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; cursor: pointer; color: #555; }
.btn-icon:hover:not(:disabled) { background: #f1f5f9; color: #5d3fd3; border-color: #5d3fd3; }
.btn-icon:disabled { opacity: 0.4; cursor: not-allowed; }

/* Discrepancy Banner */
.discrepancy-banner { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #d97706; border-radius: 8px; padding: 14px 18px; }
.discrepancy-icon { font-size: 28px; color: #d97706; }
.discrepancy-title { font-size: 14px; font-weight: 700; color: #92400e; margin: 0; display: flex; align-items: center; gap: 6px; }
.discrepancy-count { font-weight: 600; font-size: 12px; color: #b45309; }
.discrepancy-desc { font-size: 12px; color: #78350f; margin: 4px 0 0; }

.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.info-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 75px; }

.progress-bar-wrap { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.progress-bar { height: 100%; background: #5d3fd3; border-radius: 4px; transition: width 0.3s; }

/* Quick Scanner Card */
.scanner-card { background: #fdfaff; border: 1px dashed #c4b5fd; border-radius: 12px; padding: 14px 18px; }
.scanner-icon { font-size: 32px; color: #5d3fd3; }
.scanner-label { display: block; font-size: 11px; font-weight: 700; color: #5d3fd3; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.scanner-input { background: #fff; border-color: #c4b5fd; font-family: monospace; font-size: 13px; }

/* Data Card & Table */
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0; }
.card-subtitle { font-size: 12px; color: #64748b; margin: 2px 0 0; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
.data-table tbody tr:hover { background: #fafaff; }
.row-picked { background: #f8fdf9 !important; }
.row-discrepancy { background: #fffdf5 !important; }

.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }

/* Lot selector & picking inputs */
.lot-picker-cell { min-width: 200px; }
.lot-controls { display: flex; flex-direction: column; }
.lot-select { width: 100%; font-size: 11px; padding: 4px 6px; }
.batch-input { width: 100%; font-family: monospace; font-size: 11px; color: #5d3fd3; }

/* Scale Weight Cell */
.scale-weight-cell { min-width: 170px; }
.scale-input-wrap { display: inline-flex; align-items: center; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; overflow: hidden; }
.scale-input-wrap:focus-within { border-color: #5d3fd3; box-shadow: 0 0 0 1px #5d3fd3; }
.scale-icon { font-size: 16px; color: #5d3fd3; padding: 0 4px; }
.scale-input { border: none !important; width: 80px; padding: 4px 6px; font-size: 12px; font-weight: 700; font-family: monospace; text-align: right; outline: none; }
.scale-uom-badge { background: #f1f5f9; color: #475569; font-size: 10px; font-weight: 700; padding: 4px 6px; border-left: 1px solid #e2e8f0; text-transform: uppercase; }

.pick-actions-wrap { display: flex; align-items: center; justify-content: center; gap: 6px; }
.pick-input { width: 64px; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; text-align: center; font-weight: 600; font-family: monospace; }
.pick-input:focus { border-color: #5d3fd3; outline: none; }
.btn-pick { padding: 4px 10px; }

/* Badges */
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-fefo { background: #ede9fe; color: #5d3fd3; font-size: 11px; padding: 3px 10px; border-radius: 6px; border: 1px solid #ddd6fe; }

.badge-cw { background: #ede9fe; color: #5d3fd3; border: 1px solid #c4b5fd; font-size: 10px; padding: 2px 8px; border-radius: 12px; font-weight: 700; }
.badge-tol { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; padding: 1px 5px; border-radius: 4px; font-size: 10px; font-weight: 600; }

.badge-tolerance-within { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-family: monospace; }
.badge-tolerance-out { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-family: monospace; }
.badge-tolerance-approved { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-family: monospace; }

.badge-batch { background: #f3f0ff; color: #5d3fd3; border: 1px solid #ddd6fe; padding: 2px 8px; border-radius: 6px; font-family: monospace; font-size: 11px; font-weight: 600; }
.badge-batch-completed { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.badge-picked-lot { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 10px; font-weight: 600; }
.badge-picked-lot.badge-override { background: #fffbeb; color: #b45309; border-color: #fde68a; }
.override-tag { margin-left: 4px; padding: 1px 3px; font-size: 8px; background: #fbbf24; color: #78350f; border-radius: 3px; font-weight: 800; }
.badge-tag-danger { display: inline-block; margin-left: 6px; padding: 1px 4px; font-size: 9px; background: #fee2e2; color: #b91c1c; border-radius: 4px; font-weight: 700; }

.form-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
.form-input-sm { padding: 4px 8px; font-size: 12px; border-radius: 6px; }
.form-input-xs { padding: 3px 6px; font-size: 11px; border-radius: 4px; }
.form-textarea { resize: vertical; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }
select.form-input { appearance: auto; }

/* Modal Dialog */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 10000; }
.modal-dialog { background: #fff; border-radius: 12px; width: 90%; max-width: 580px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); overflow: hidden; }
.modal-header { padding: 16px 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-close { background: none; border: none; font-size: 24px; color: #94a3b8; cursor: pointer; line-height: 1; }
.modal-close:hover { color: #1e293b; }
.modal-body { padding: 20px; max-height: 75vh; overflow-y: auto; }
.modal-intro { font-size: 13px; color: #475569; margin: 0 0 14px; }
.modal-footer { padding: 14px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 8px; }

.discrepancy-summary-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.summary-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.summary-table th { background: #f1f5f9; padding: 8px 10px; text-align: left; font-size: 11px; font-weight: 600; color: #64748b; }
.summary-table td { padding: 8px 10px; border-top: 1px solid #e2e8f0; }

.icon-xs { font-size: 14px !important; vertical-align: middle; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .summary-table th { text-align: right; }
[dir="rtl"] .scale-uom-badge { border-left: none; border-right: 1px solid #e2e8f0; }

/* Scanner status badge & pulse */
.badge-scanner-active { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
.status-pulse { width: 7px; height: 7px; border-radius: 50%; background: #16a34a; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }

/* Camera trigger button */
.btn-camera-trigger { background: #0284c7; color: #fff; }
.btn-camera-trigger:hover { background: #0369a1; }

/* Visual Flash States */
.scanner-card.flash-success { border-color: #22c55e !important; box-shadow: 0 0 12px rgba(34, 197, 94, 0.4); background: #f0fdf4 !important; transition: all 0.2s ease; }
.scanner-card.flash-error { border-color: #ef4444 !important; box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); background: #fef2f2 !important; transition: all 0.2s ease; }

/* Mismatch Warning Modal */
.modal-dialog-warning { max-width: 480px; }
.header-danger { background: #fef2f2; border-bottom: 1px solid #fee2e2; }
.mismatch-icon-wrap { width: 56px; height: 56px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; margin: 0 auto; }
.icon-mismatch { font-size: 32px; }
.scanned-code-box { background: #f1f5f9; padding: 8px 14px; border-radius: 8px; border: 1px solid #e2e8f0; display: inline-block; font-family: monospace; font-size: 15px; color: #0f172a; }
.alert-warning-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; color: #92400e; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; }
.btn-danger-action { background: #dc2626; color: #fff; border: none; }
.btn-danger-action:hover { background: #b91c1c; }
</style>


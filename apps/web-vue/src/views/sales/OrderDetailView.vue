<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="order">
      <!-- Top header & actions -->
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/sales')">&larr; {{ t('back-to-orders', 'Back to Orders') }}</button>
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="page-title">{{ t('sales-order', 'Sales Order') }} #{{ order.order_number }}</h1>
            <span class="badge" :class="statusBadge">{{ order.status }}</span>
            <span v-if="order.status === 'Credit Hold'" class="badge badge-credit-hold">
              <span class="material-symbols-outlined icon-xs">gpp_bad</span>
              Credit Hold
            </span>
            <span v-if="hasCatchWeightLines" class="badge badge-cw" :title="t('dual-uom-order-hint', 'Order contains dual UOM catch-weight items with scale weight pricing')">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ t('dual-uom-order', 'Dual UOM / Catch-Weight') }}
            </span>
            <span v-if="orderPaymentTerm && orderPaymentTerm.discount_percentage > 0" class="badge badge-discount-rate" :title="t('early-discount-available', 'Early Payment Discount Available')">
              <span class="material-symbols-outlined icon-xs">savings</span>
              {{ orderPaymentTerm.discount_percentage }}% {{ t('early-discount', 'Early Discount') }}
            </span>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap items-center">
          <button
            v-if="hasCatchWeightLines && (order.status === 'Confirmed' || order.status === 'Shipped' || order.status === 'Delivered')"
            class="btn-outline btn-cw"
            @click="recalculateCatchWeight"
            :disabled="recalculating"
            :title="t('recalculate-cw-hint', 'Sync and recalculate line totals with recorded warehouse scale weights')"
          >
            <span v-if="recalculating" class="material-symbols-outlined spin icon-xs">progress_activity</span>
            <span v-else class="material-symbols-outlined icon-xs">refresh</span>
            {{ recalculating ? t('recalculating', 'Recalculating...') : t('recalculate-cw', 'Recalculate Pricing') }}
          </button>
          <button v-if="order.status === 'Pending'" class="btn-primary" @click="confirmOrder">
            <span class="material-symbols-outlined icon-xs">check_circle</span>
            {{ t('confirm', 'Confirm') }}
          </button>
          <button
            v-if="order.status === 'Shipped'"
            class="btn-primary"
            @click="deliverOrder"
            :disabled="delivering"
            :title="t('deliver-hint', 'Mark order as delivered and generate final catch-weight invoice')"
          >
            <span v-if="delivering" class="material-symbols-outlined spin icon-xs">progress_activity</span>
            <span v-else class="material-symbols-outlined icon-xs">local_shipping</span>
            {{ delivering ? t('delivering', 'Delivering...') : t('deliver', 'Mark Delivered') }}
          </button>
          <button v-if="order.status === 'Credit Hold'" class="btn-override" @click="showOverrideModal = true">
            <span class="material-symbols-outlined icon-xs">lock_open</span>
            Override Credit Hold
          </button>
          <button v-if="canCancel" class="btn-outline btn-outline-danger" @click="cancelOrder">
            <span class="material-symbols-outlined icon-xs">cancel</span>
            {{ t('cancel-order', 'Cancel Order') }}
          </button>
        </div>
      </div>

      <!-- Catch-Weight Billing Adjustment Notice Banner -->
      <div v-if="hasCatchWeightLines && weightAdjustmentAmount !== 0" class="cw-notice-banner mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined cw-banner-icon">scale</span>
          <div class="flex-1">
            <h4 class="cw-banner-title">
              {{ t('cw-pricing-applied', 'Catch-Weight Scale Pricing Applied') }}
              <span class="badge" :class="weightAdjustmentAmount >= 0 ? 'badge-adjustment-pos' : 'badge-adjustment-neg'">
                {{ weightAdjustmentAmount >= 0 ? '+' : '' }}${{ weightAdjustmentAmount.toFixed(2) }}
              </span>
            </h4>
            <p class="cw-banner-desc">
              {{ t('cw-pricing-desc', 'Final billing reflects actual warehouse scale weights recorded during picking instead of nominal estimated weights.') }}
              <span class="font-medium">
                {{ t('nominal-total', 'Nominal') }}: {{ formatNumber(totalNominalWeight) }} {{ primaryWeightUnit }} &rarr;
                {{ t('actual-total', 'Actual Weighed') }}: {{ formatNumber(totalActualWeight) }} {{ primaryWeightUnit }}
                ({{ formatVariance(totalWeightVariance) }}%)
              </span>
            </p>
          </div>
        </div>
      </div>

      <!-- Credit Hold Banner -->
      <div v-if="order.status === 'Credit Hold'" class="credit-hold-banner mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined credit-hold-icon">gpp_bad</span>
          <div class="flex-1">
            <h4 class="credit-hold-title">Order Placed on Financial Credit Hold</h4>
            <p class="credit-hold-reason">{{ order.hold_reason }}</p>
            <div v-if="creditStatus" class="credit-status-info">
              <span class="credit-status-label">Available Credit</span>
              <span class="mono">${{ formatNumber(creditStatus.available_credit || 0) }}</span>
            </div>
          </div>
          <button class="btn-outline btn-outline-danger" @click="showRejectModal = true">
            <span class="material-symbols-outlined icon-xs">block</span>
            Reject Order
          </button>
        </div>
      </div>

      <!-- Credit Hold Release Banner -->
      <div v-if="order.hold_released_by" class="credit-hold-release-banner mb-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined credit-hold-release-icon">verified</span>
          <div class="flex-1">
            <h4 class="credit-hold-release-title">Credit Hold Overridden & Authorized</h4>
            <p class="credit-hold-release-reason">{{ order.hold_release_reason }}</p>
            <div class="credit-status-info">
              <span class="credit-status-label">Released by</span>
              <span class="mono">{{ order.hold_released_by }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Grid: Order Info & Totals -->
      <div class="detail-grid">
        <div class="detail-card">
          <h3 class="card-title">{{ t('order-info', 'Order Information') }}</h3>
          <div class="info-row"><span class="info-label">{{ t('status', 'Status') }}:</span><span class="badge" :class="statusBadge">{{ order.status }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('sales-customer', 'Customer') }}:</span><span>{{ customerName }}</span></div>
          <div class="info-row">
            <span class="info-label">{{ t('payment-terms', 'Payment Terms') }}:</span>
            <span class="font-medium text-primary">{{ paymentTermDisplay }}</span>
          </div>
          <div v-if="orderPaymentTerm && orderPaymentTerm.discount_percentage > 0" class="info-row">
            <span class="info-label">{{ t('early-discount', 'Early Discount') }}:</span>
            <span class="badge badge-discount-rate">
              <span class="material-symbols-outlined icon-xs">savings</span>
              {{ orderPaymentTerm.discount_percentage }}% {{ t('within', 'within') }} {{ orderPaymentTerm.discount_days }} {{ t('days', 'days') }}
            </span>
          </div>
          <div class="info-row"><span class="info-label">{{ t('sales-order-date', 'Order Date') }}:</span><span>{{ order.order_date }}</span></div>
          <div class="info-row"><span class="info-label">{{ t('warehouse', 'Warehouse') }}:</span><span>{{ warehouseName }}</span></div>
          <div v-if="hasCatchWeightLines" class="info-row">
            <span class="info-label">{{ t('pricing-model', 'Pricing Model') }}:</span>
            <span class="badge badge-cw">
              <span class="material-symbols-outlined icon-xs">balance</span>
              {{ t('dual-uom-model', 'Dual UOM (Scale Weight)') }}
            </span>
          </div>
          <div class="info-row" v-if="order.notes"><span class="info-label">{{ t('sales-notes', 'Notes') }}:</span><span>{{ order.notes }}</span></div>
        </div>

        <div class="detail-card">
          <h3 class="card-title">{{ t('totals', 'Totals & Catch-Weight Summary') }}</h3>
          
          <!-- Original Subtotal -->
          <div class="info-row">
            <span class="info-label">{{ t('sales-subtotal', 'Original Subtotal') }}:</span>
            <span class="col-num">${{ (originalSubtotal || order.subtotal || 0).toFixed(2) }}</span>
          </div>

          <!-- Dual UOM Catch-Weight Rows -->
          <template v-if="hasCatchWeightLines">
            <div class="info-row">
              <span class="info-label">{{ t('nominal-total-weight', 'Nominal Total Weight') }}:</span>
              <span class="col-num text-muted">{{ formatNumber(totalNominalWeight) }} {{ primaryWeightUnit }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('actual-total-weight', 'Actual Weighed Weight') }}:</span>
              <span class="col-num font-bold text-cw">
                {{ totalActualWeight !== null ? `${formatNumber(totalActualWeight)} ${primaryWeightUnit}` : t('pending-weighing', 'Pending Weighing') }}
              </span>
            </div>
            <div v-if="totalWeightVariance !== null" class="info-row">
              <span class="info-label">{{ t('net-weight-variance', 'Net Weight Variance') }}:</span>
              <span class="col-num font-bold" :class="totalWeightVariance >= 0 ? 'text-green' : 'text-amber'">
                {{ formatVariance(totalWeightVariance) }}%
              </span>
            </div>
            <div v-if="weightAdjustmentAmount !== 0" class="info-row cw-adj-row">
              <span class="info-label text-cw font-medium">{{ t('weight-adjustment', 'Catch-Weight Adjustment') }}:</span>
              <span class="col-num font-bold" :class="weightAdjustmentAmount >= 0 ? 'text-green' : 'text-danger'">
                {{ weightAdjustmentAmount >= 0 ? '+' : '' }}${{ weightAdjustmentAmount.toFixed(2) }}
              </span>
            </div>
            <div v-if="recalculatedSubtotal !== null && recalculatedSubtotal !== originalSubtotal" class="info-row">
              <span class="info-label font-bold">{{ t('recalculated-subtotal', 'Weighed Subtotal') }}:</span>
              <span class="col-num font-bold text-primary">${{ recalculatedSubtotal.toFixed(2) }}</span>
            </div>
          </template>

          <div class="info-row"><span class="info-label">{{ t('sales-tax', 'Tax') }}:</span><span class="col-num">${{ (order.tax || 0).toFixed(2) }}</span></div>
          <div v-if="order.freight_amount" class="info-row"><span class="info-label">{{ t('freight', 'Freight') }}:</span><span class="col-num">${{ (order.freight_amount || 0).toFixed(2) }}</span></div>
          <div v-if="order.discount_amount" class="info-row"><span class="info-label">{{ t('discount', 'Discount') }}:</span><span class="col-num text-danger">-${{ (order.discount_amount || 0).toFixed(2) }}</span></div>
          
          <div class="info-row total-row">
            <span class="info-label">{{ t('sales-grand-total', 'Grand Total') }}:</span>
            <span class="col-num grand-total-amount">${{ (order.grand_total || 0).toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- Order Lines Table with Dual UOM Breakdown -->
      <div class="data-card mt-4">
        <div class="card-header flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 class="card-title">{{ t('order-lines', 'Order Lines') }}</h3>
            <p class="card-subtitle text-xs text-muted" v-if="hasCatchWeightLines">
              {{ t('cw-lines-subtitle', 'Dual UOM items display Stocking Unit (Cases) vs Pricing Unit (Scale kg/lbs) with live weight recalculations.') }}
            </p>
          </div>
          <div v-if="hasCatchWeightLines" class="flex items-center gap-2">
            <span class="badge badge-cw">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ catchWeightLinesCount }} / {{ lines.length }} Catch-Weight Items
            </span>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-8">#</th>
                <th>{{ t('product', 'Product') }}</th>
                <th class="col-num">{{ t('ordered-qty', 'Stocking Qty') }}</th>
                <th>{{ t('pricing-basis-rate', 'Pricing UOM & Rate') }}</th>
                <th class="col-num">{{ t('nominal-weight', 'Nominal Weight') }}</th>
                <th class="col-num">{{ t('scale-weight', 'Actual Scale Weight') }}</th>
                <th class="text-center">{{ t('weight-variance', 'Weight Var.') }}</th>
                <th class="col-num">{{ t('unit-price', 'Unit Price') }}</th>
                <th class="col-num">{{ t('line-total', 'Line Total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in lines" :key="line.id" :class="{ 'row-cw': isCatchWeightLine(line) }">
                <td class="cell-mono">{{ line.line_number }}</td>
                <td>
                  <div class="flex items-center gap-2 flex-wrap">
                    <strong>{{ line.product_name || `#${line.product_id}` }}</strong>
                    <span v-if="isCatchWeightLine(line)" class="badge badge-cw" :title="t('cw-item', 'Catch-Weight item billed by physical scale weight')">
                      <span class="material-symbols-outlined icon-xs">scale</span>
                      {{ t('catch-weight-item', 'Catch Weight') }}
                    </span>
                  </div>
                  <div class="text-muted text-xs flex items-center gap-2 mt-1">
                    <span v-if="line.product_id">ID: #{{ line.product_id }}</span>
                    <span v-if="getLineUomName(line)" class="text-secondary font-medium">UOM: {{ getLineUomName(line) }}</span>
                  </div>
                </td>
                <td class="col-num font-bold">
                  {{ line.qty }} <span class="text-xs text-muted">{{ getLineUomCode(line) }}</span>
                </td>

                <!-- Pricing UOM & Unit Rate -->
                <td>
                  <div v-if="isCatchWeightLine(line) && line.unit_price_pricing_uom">
                    <span class="font-bold text-primary">${{ Number(line.unit_price_pricing_uom).toFixed(2) }}</span>
                    <span class="text-xs text-muted"> / {{ getPricingUomCode(line) }}</span>
                  </div>
                  <div v-else-if="isCatchWeightLine(line)">
                    <span class="font-bold text-primary">${{ Number(line.unit_price || 0).toFixed(2) }}</span>
                    <span class="text-xs text-muted"> / {{ getPricingUomCode(line) }}</span>
                  </div>
                  <div v-else class="text-muted text-xs">
                    ${{ (line.unit_price || 0).toFixed(2) }} / {{ getLineUomCode(line) }}
                  </div>
                </td>

                <!-- Nominal Weight -->
                <td class="col-num">
                  <span v-if="line.nominal_weight !== null && line.nominal_weight !== undefined">
                    {{ formatNumber(line.nominal_weight) }} <span class="text-xs text-muted">{{ getPricingUomCode(line) }}</span>
                  </span>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Actual Weighed Weight -->
                <td class="col-num">
                  <div v-if="line.catch_weight_actual !== null && line.catch_weight_actual !== undefined">
                    <span class="font-bold text-cw">{{ formatNumber(line.catch_weight_actual) }}</span>
                    <span class="text-xs text-muted"> {{ getPricingUomCode(line) }}</span>
                  </div>
                  <div v-else-if="isCatchWeightLine(line)">
                    <span class="badge badge-pending-weigh text-xs">{{ t('pending-weigh', 'Pending') }}</span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Weight Variance -->
                <td class="text-center">
                  <div v-if="isCatchWeightLine(line) && getLineVariance(line) !== null">
                    <span class="badge" :class="getLineVarianceClass(line)">
                      {{ formatVariance(getLineVariance(line)) }}%
                    </span>
                  </div>
                  <span v-else class="text-muted text-xs">-</span>
                </td>

                <!-- Stocking Unit Price -->
                <td class="col-num">${{ (line.unit_price || 0).toFixed(2) }}</td>

                <!-- Final Line Total (with recalculated comparison) -->
                <td class="col-num">
                  <div v-if="isCatchWeightLine(line) && line.recalculated_total !== null && line.recalculated_total !== undefined">
                    <div class="font-bold text-primary">${{ Number(line.recalculated_total).toFixed(2) }}</div>
                    <div v-if="Number(line.recalculated_total) !== Number(line.line_total)" class="text-xs text-muted strike-original">
                      ${{ Number(line.line_total || 0).toFixed(2) }}
                      <span :class="Number(line.recalculated_total) >= Number(line.line_total) ? 'text-green' : 'text-danger'">
                        ({{ Number(line.recalculated_total) >= Number(line.line_total) ? '+' : '' }}${{ (Number(line.recalculated_total) - Number(line.line_total)).toFixed(2) }})
                      </span>
                    </div>
                  </div>
                  <div v-else class="font-bold">
                    ${{ (line.line_total || 0).toFixed(2) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Dedicated Catch-Weight Audit & Dual UOM Breakdown Card -->
      <div v-if="hasCatchWeightLines" class="data-card mt-4">
        <div class="card-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-cw">balance</span>
            <h3 class="card-title">{{ t('cw-audit-title', 'Dual UOM Catch-Weight Audit & Reconciliation') }}</h3>
          </div>
        </div>
        <div class="card-body">
          <div class="grid-stats mb-3">
            <div class="stat-box">
              <span class="stat-label">{{ t('total-nominal-weight', 'Total Nominal Weight') }}</span>
              <span class="stat-value">{{ formatNumber(totalNominalWeight) }} {{ primaryWeightUnit }}</span>
            </div>
            <div class="stat-box">
              <span class="stat-label">{{ t('total-actual-weight', 'Total Actual Scale Weight') }}</span>
              <span class="stat-value text-cw">
                {{ totalActualWeight !== null ? `${formatNumber(totalActualWeight)} ${primaryWeightUnit}` : t('pending-weighing', 'Pending') }}
              </span>
            </div>
            <div class="stat-box">
              <span class="stat-label">{{ t('weight-variance', 'Weight Variance') }}</span>
              <span class="stat-value" :class="totalWeightVariance >= 0 ? 'text-green' : 'text-amber'">
                {{ totalWeightVariance !== null ? `${formatVariance(totalWeightVariance)}%` : '-' }}
              </span>
            </div>
            <div class="stat-box">
              <span class="stat-label">{{ t('billing-adjustment', 'Net Catch-Weight Adjustment') }}</span>
              <span class="stat-value" :class="weightAdjustmentAmount >= 0 ? 'text-green' : 'text-danger'">
                {{ weightAdjustmentAmount >= 0 ? '+' : '' }}${{ weightAdjustmentAmount.toFixed(2) }}
              </span>
            </div>
          </div>
          <p class="text-xs text-muted">
            {{ t('cw-audit-explanation', 'Nova ERP Dual UOM Engine tracks warehouse stock movements by Stocking UOM (Cases/Boxes) while generating certified commercial invoices based on physical scale weight (kg/lbs). Tolerances and pricing adjustments ensure operating margin accuracy.') }}
          </p>
        </div>
      </div>

      <!-- Status History -->
      <div class="data-card mt-4">
        <div class="card-header"><h3 class="card-title">{{ t('status-history', 'Status History') }}</h3></div>
        <div class="timeline" v-if="statusHistory.length">
          <div v-for="(entry, i) in statusHistory" :key="i" class="timeline-item">
            <div class="timeline-dot" :class="entry.class"></div>
            <div class="timeline-content">
              <span class="badge" :class="entry.class">{{ entry.status }}</span>
              <span class="timeline-date">{{ entry.date }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-sm">{{ t('no-records', 'No records found') }}</div>
      </div>
    </template>

    <!-- Override Credit Hold Modal -->
    <Teleport to="body">
      <div v-if="showOverrideModal" class="modal-overlay" @click.self="showOverrideModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Override Credit Hold</h3>
            <button class="btn-icon" @click="showOverrideModal = false"><span class="material-symbols-outlined">close</span></button>
          </div>
          <div class="modal-body">
            <label>Reason for override</label>
            <textarea class="form-textarea" v-model="overrideReason" rows="3" placeholder="Enter reason for overriding credit hold..."></textarea>
            <label class="mt-3">Target Status</label>
            <select class="form-select" v-model="overrideTargetStatus">
              <option value="Confirmed">Confirmed</option>
              <option value="Pending">Pending</option>
            </select>
          </div>
          <div class="modal-footer">
            <button class="btn-outline" @click="showOverrideModal = false">Cancel</button>
            <button class="btn-override" @click="executeOverride" :disabled="!overrideReason">Confirm Override</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Reject Credit Hold Modal -->
    <Teleport to="body">
      <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Reject Credit Hold</h3>
            <button class="btn-icon" @click="showRejectModal = false"><span class="material-symbols-outlined">close</span></button>
          </div>
          <div class="modal-body">
            <label>Reason for rejection</label>
            <textarea class="form-textarea" v-model="rejectReason" rows="3" placeholder="Enter reason for rejecting this order..."></textarea>
          </div>
          <div class="modal-footer">
            <button class="btn-outline" @click="showRejectModal = false">Cancel</button>
            <button class="btn-outline btn-outline-danger btn-danger" @click="executeReject" :disabled="!rejectReason">Confirm Rejection</button>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      v-if="showConfirmCancel"
      :title="t('cancel-order', 'Cancel Order')"
      :message="t('cancel-order-msg', 'Are you sure you want to cancel this order? This will release any reserved stock.')"
      @confirm="executeCancel"
      @cancel="showConfirmCancel = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const recalculating = ref(false)
const delivering = ref(false)
const error = ref('')
const order = ref(null)
const lines = ref([])
const customers = ref([])
const warehouses = ref([])
const uoms = ref([])
const paymentTerms = ref([])
const showConfirmCancel = ref(false)
const creditStatus = ref(null)
const showOverrideModal = ref(false)
const overrideReason = ref('')
const overrideTargetStatus = ref('Confirmed')
const showRejectModal = ref(false)
const rejectReason = ref('')

const customerName = computed(() => {
  if (!order.value) return ''
  const c = customers.value.find(x => x.id === order.value.customer_id)
  return c ? c.name : `#${order.value.customer_id}`
})

const orderPaymentTerm = computed(() => {
  if (!order.value?.payment_term_id) {
    const cust = customers.value.find(x => x.id === order.value?.customer_id)
    if (cust?.payment_term_id) {
      return paymentTerms.value.find(p => p.id === cust.payment_term_id) || null
    }
    return null
  }
  return paymentTerms.value.find(p => p.id === order.value.payment_term_id) || null
})

const paymentTermDisplay = computed(() => {
  if (!order.value?.payment_term_id) {
    const cust = customers.value.find(x => x.id === order.value?.customer_id)
    if (cust?.payment_term_id) {
      const term = paymentTerms.value.find(p => p.id === cust.payment_term_id)
      if (term) {
        if (term.discount_percentage > 0 && term.discount_days > 0) {
          return `${term.name} (${term.discount_percentage}% / ${term.discount_days}d, Net ${term.due_days}d)`
        }
        return `${term.name} (Net ${term.due_days}d)`
      }
    }
    return '-'
  }
  const term = paymentTerms.value.find(p => p.id === order.value.payment_term_id)
  if (!term) return `Term #${order.value.payment_term_id}`
  if (term.discount_percentage > 0 && term.discount_days > 0) {
    return `${term.name} (${term.discount_percentage}% / ${term.discount_days}d, Net ${term.due_days}d)`
  }
  return `${term.name} (Net ${term.due_days}d)`
})

const warehouseName = computed(() => {
  if (!order.value || !order.value.warehouse_id) return '-'
  const w = warehouses.value.find(x => x.id === order.value.warehouse_id)
  return w ? (w.name || `#${order.value.warehouse_id}`) : `#${order.value.warehouse_id}`
})

const statusBadge = computed(() => {
  const map = {
    Pending: 'badge-warning',
    Confirmed: 'badge-info',
    Shipped: 'badge-info',
    Delivered: 'badge-active',
    Cancelled: 'badge-inactive',
    Paid: 'badge-active',
    Invoiced: 'badge-active',
  }
  return map[order.value?.status] || 'badge-inactive'
})

const canCancel = computed(() => {
  return order.value && ['Pending', 'Confirmed'].includes(order.value.status)
})

const hasCatchWeightLines = computed(() => {
  return lines.value.some(isCatchWeightLine)
})

const catchWeightLinesCount = computed(() => {
  return lines.value.filter(isCatchWeightLine).length
})

const primaryWeightUnit = computed(() => {
  const cwLine = lines.value.find(isCatchWeightLine)
  if (!cwLine) return 'kg'
  return getPricingUomCode(cwLine) || 'kg'
})

const totalNominalWeight = computed(() => {
  const cw = lines.value.filter(isCatchWeightLine)
  if (!cw.length) return null
  return cw.reduce((sum, l) => sum + (Number(l.nominal_weight) || 0), 0)
})

const totalActualWeight = computed(() => {
  const cw = lines.value.filter(isCatchWeightLine)
  const hasWeighed = cw.some(l => l.catch_weight_actual !== null && l.catch_weight_actual !== undefined)
  if (!hasWeighed) return null
  return cw.reduce((sum, l) => sum + (Number(l.catch_weight_actual) || 0), 0)
})

const totalWeightVariance = computed(() => {
  if (totalNominalWeight.value === null || totalActualWeight.value === null || totalNominalWeight.value <= 0) {
    return null
  }
  return Number((((totalActualWeight.value - totalNominalWeight.value) / totalNominalWeight.value) * 100).toFixed(2))
})

const originalSubtotal = computed(() => {
  return lines.value.reduce((sum, l) => sum + (Number(l.line_total) || 0), 0)
})

const recalculatedSubtotal = computed(() => {
  if (!hasCatchWeightLines.value) return null
  return lines.value.reduce((sum, l) => {
    if (isCatchWeightLine(l) && l.recalculated_total !== null && l.recalculated_total !== undefined) {
      return sum + Number(l.recalculated_total)
    }
    return sum + (Number(l.line_total) || 0)
  }, 0)
})

const weightAdjustmentAmount = computed(() => {
  if (recalculatedSubtotal.value === null) return 0
  return Number((recalculatedSubtotal.value - originalSubtotal.value).toFixed(2))
})

const statusHistory = computed(() => {
  if (!order.value) return []
  const allStatuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Invoiced', 'Paid', 'Cancelled']
  const current = order.value.status
  const idx = allStatuses.indexOf(current)
  if (idx === -1) return [{ status: current, date: order.value.updated_at || order.value.created_at, class: 'badge-info' }]
  const classMap = {
    Pending: 'badge-warning',
    Confirmed: 'badge-info',
    Shipped: 'badge-info',
    Delivered: 'badge-active',
    Invoiced: 'badge-active',
    Paid: 'badge-active',
    Cancelled: 'badge-inactive',
  }
  return allStatuses.slice(0, idx + 1).map((s, i) => ({
    status: s,
    date: i === idx ? (order.value.updated_at || order.value.created_at) : order.value.created_at,
    class: classMap[s] || 'badge-info',
  }))
})

function isCatchWeightLine(line) {
  if (!line) return false
  return Boolean(
    line.is_catch_weight ||
    line.pricing_uom_id !== null && line.pricing_uom_id !== undefined ||
    line.unit_price_pricing_uom !== null && line.unit_price_pricing_uom !== undefined ||
    line.nominal_weight !== null && line.nominal_weight !== undefined ||
    line.catch_weight_actual !== null && line.catch_weight_actual !== undefined
  )
}

function getLineUomCode(line) {
  if (!line || !line.uom_id) return 'units'
  const u = uoms.value.find(x => x.id === line.uom_id)
  return u ? (u.uom_code || u.uom_name) : 'units'
}

function getLineUomName(line) {
  if (!line || !line.uom_id) return ''
  const u = uoms.value.find(x => x.id === line.uom_id)
  return u ? u.uom_name : ''
}

function getPricingUomCode(line) {
  if (!line) return 'kg'
  if (line.pricing_uom_id) {
    const u = uoms.value.find(x => x.id === line.pricing_uom_id)
    if (u) return u.uom_code || u.uom_name
  }
  return 'kg'
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

function getLineVariance(line) {
  if (!line || line.nominal_weight === null || line.nominal_weight === undefined || line.catch_weight_actual === null || line.catch_weight_actual === undefined) {
    return null
  }
  const nom = Number(line.nominal_weight)
  const act = Number(line.catch_weight_actual)
  if (nom <= 0) return null
  return Number((((act - nom) / nom) * 100).toFixed(2))
}

function getLineVarianceClass(line) {
  const varPct = getLineVariance(line)
  if (varPct === null) return 'badge-inactive'
  if (Math.abs(varPct) <= 10) return 'badge-tolerance-within'
  return 'badge-tolerance-out'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [orderRes, lineRes, custRes, whRes, uomRes, ptRes] = await Promise.all([
      api.get(`/T0012I/${id}`),
      api.get('/T0013I/', { params: { sales_order_id: id } }),
      api.get('/T0010I/'),
      api.get('/T0008I/'),
      api.get('/T0001I/').catch(() => ({ data: [] })),
      api.get('/T0096I/').catch(() => ({ data: [] })),
    ])
    order.value = orderRes.data
    lines.value = lineRes.data || []
    customers.value = custRes.data || []
    warehouses.value = whRes.data || []
    uoms.value = uomRes.data || []
    paymentTerms.value = ptRes.data || []

    if (order.value?.status === 'Credit Hold' && order.value?.customer_id) {
      try {
        const creditRes = await api.get(`/T0010I/${order.value.customer_id}/credit-status`)
        creditStatus.value = creditRes.data
      } catch { creditStatus.value = null }
    }
  } catch {
    error.value = t('failed-load', 'Failed to load sales order')
  } finally {
    loading.value = false
  }
}

async function confirmOrder() {
  try {
    await api.post(`/T0012I/${order.value.id}/confirm`)
    toast(t('order-confirmed-stock-reserved', 'Order confirmed — stock reserved and pick list created'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Confirmation failed', 'error')
  }
}

async function deliverOrder() {
  delivering.value = true
  try {
    await api.post(`/T0012I/${order.value.id}/deliver`)
    toast(t('order-delivered-invoiced', 'Order delivered — final catch-weight invoice created and customer balance updated'), 'success')
    await load()
  } catch (e) {
    const msg = e.response?.data?.detail || 'Delivery failed'
    toast(msg, 'error')
  } finally {
    delivering.value = false
  }
}

async function recalculateCatchWeight() {
  recalculating.value = true
  try {
    const res = await api.post(`/T0012I/${order.value.id}/recalculate-catch-weight`)
    toast(t('cw-recalculated-success', 'Catch-weight pricing recalculated from warehouse picking weights'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Recalculation failed', 'error')
  } finally {
    recalculating.value = false
  }
}

function cancelOrder() {
  showConfirmCancel.value = true
}

async function executeCancel() {
  showConfirmCancel.value = false
  try {
    await api.post(`/T0012I/${order.value.id}/cancel`)
    toast(t('order-cancelled-stock-released', 'Order cancelled — stock released'), 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Cancellation failed', 'error')
  }
}

async function executeOverride() {
  try {
    await api.post(`/T0012I/${order.value.id}/override-credit-hold`, {
      reason: overrideReason.value,
      target_status: overrideTargetStatus.value,
    })
    toast('Credit hold overridden — order released', 'success')
    showOverrideModal.value = false
    overrideReason.value = ''
    overrideTargetStatus.value = 'Confirmed'
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Override failed', 'error')
  }
}

async function executeReject() {
  try {
    await api.post(`/T0012I/${order.value.id}/reject-credit-hold`, {
      reason: rejectReason.value,
    })
    toast('Credit hold rejected — order cancelled', 'success')
    showRejectModal.value = false
    rejectReason.value = ''
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Rejection failed', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-state-sm { text-align: center; padding: 24px; color: #999; font-size: 13px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-wrap { flex-wrap: wrap; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-outline:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-cw { color: #0284c7; border-color: #bae6fd; background: #f0f9ff; }
.btn-cw:hover { background: #e0f2fe; }

.btn-outline-danger { color: #dc2626; border-color: #fca5a5; }
.btn-outline-danger:hover { background: #fee2e2; }

/* Catch-Weight Banner */
.cw-notice-banner { background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px 18px; }
.cw-banner-icon { font-size: 28px; color: #16a34a; }
.cw-banner-title { font-size: 14px; font-weight: 700; color: #14532d; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
.cw-banner-desc { font-size: 12px; color: #166534; margin: 0; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-body { padding: 16px 18px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 130px; }
.total-row { border-top: 1px solid #eee; margin-top: 8px; padding-top: 8px; font-weight: 700; }
.grand-total-amount { font-size: 16px; color: #5d3fd3; }
.cw-adj-row { background: #f8fafc; padding: 6px 8px; border-radius: 6px; }
.col-num { font-family: monospace; font-weight: 600; text-align: right; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.row-cw { background: #fcfdfe; }
.row-cw:hover { background: #f0f7ff !important; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.strike-original { text-decoration: line-through; color: #94a3b8; font-weight: normal; }

/* Grid stats for Audit card */
.grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.stat-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; display: flex; flex-direction: column; }
.stat-label { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
.stat-value { font-size: 16px; font-weight: 700; color: #1e293b; font-family: monospace; }

/* Badges */
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-cw { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-tolerance-within { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.badge-tolerance-out { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
.badge-adjustment-pos { background: #dcfce7; color: #16a34a; font-family: monospace; }
.badge-adjustment-neg { background: #fee2e2; color: #dc2626; font-family: monospace; }
.badge-pending-weigh { background: #fef3c7; color: #b45309; }
.badge-discount-rate { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }

.icon-xs { font-size: 14px !important; }
.text-cw { color: #0284c7; }
.text-green { color: #16a34a; }
.text-success { color: #16a34a; }
.text-amber { color: #d97706; }
.text-danger { color: #dc2626; }
.text-primary { color: #5d3fd3; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.timeline { padding: 16px; }
.timeline-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-left: 2px solid #e0e0e0; margin-left: 8px; padding-left: 20px; position: relative; }
.timeline-item:last-child { border-left-color: transparent; }
.timeline-dot { width: 10px; height: 10px; border-radius: 50%; position: absolute; left: -6px; }
.timeline-dot.badge-active { background: #16a34a; }
.timeline-dot.badge-warning { background: #d97706; }
.timeline-dot.badge-info { background: #0284c7; }
.timeline-dot.badge-inactive { background: #888; }
.timeline-content { display: flex; align-items: center; gap: 10px; }
.timeline-date { font-size: 11px; color: #999; }

.badge-credit-hold { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.credit-hold-banner { background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 20px; }
.credit-hold-icon { color: #dc2626; font-size: 28px; }
.credit-hold-title { font-size: 15px; font-weight: 700; color: #991b1b; margin: 0 0 6px; }
.credit-hold-reason { font-size: 13px; color: #7f1d1d; margin: 0 0 10px; }
.credit-status-info { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding-top: 8px; border-top: 1px solid #fecaca; }
.credit-status-label { color: #991b1b; font-weight: 600; }

.credit-hold-release-banner { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 20px; }
.credit-hold-release-icon { color: #16a34a; font-size: 28px; }
.credit-hold-release-title { font-size: 15px; font-weight: 700; color: #166534; margin: 0 0 6px; }
.credit-hold-release-reason { font-size: 13px; color: #14532d; margin: 0 0 10px; }

.btn-override { display: inline-flex; align-items: center; gap: 6px; background: #16a34a; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-override:hover { background: #15803d; }
.btn-override:disabled { opacity: 0.6; cursor: not-allowed; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 12px; width: 480px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #e0e0e0; }
.modal-header h3 { font-size: 16px; font-weight: 700; margin: 0; }
.modal-body { padding: 24px; }
.modal-body label { display: block; font-size: 12px; font-weight: 600; color: #666; margin-bottom: 4px; }
.form-textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; resize: vertical; font-family: inherit; }
.form-textarea:focus { outline: none; border-color: #5d3fd3; }
.form-select { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; margin-top: 4px; }
.mt-3 { margin-top: 12px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid #e0e0e0; }
.font-medium { font-weight: 600; }
.icon-xs { font-size: 16px; }

[dir="rtl"] .timeline-item { border-left: none; border-right: 2px solid #e0e0e0; margin-left: 0; margin-right: 8px; padding-left: 0; padding-right: 20px; }
[dir="rtl"] .timeline-dot { left: auto; right: -6px; }
[dir="rtl"] .data-table th { text-align: right; }
</style>


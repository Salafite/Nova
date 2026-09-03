<template>
  <div v-if="order" class="modal-backdrop" @click="handleClose">
    <div class="conflict-modal" @click.stop>
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-icon-danger">
          <span class="material-symbols-outlined">warning</span>
        </div>
        <div class="header-text">
          <h3 class="modal-title">Stock Conflict Resolution</h3>
          <p class="modal-subtitle">
            Order for <strong>{{ order.customer_name }}</strong> encountered inventory or pricing changes while offline.
          </p>
        </div>
        <button class="btn-close" @click="handleClose" aria-label="Close dialog">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <div class="order-summary-strip">
          <div class="strip-item">
            <span class="strip-label">Order UUID</span>
            <span class="strip-val font-mono">{{ truncateUuid(order.client_order_uuid) }}</span>
          </div>
          <div class="strip-item">
            <span class="strip-label">Created Offline</span>
            <span class="strip-val">{{ formatDate(order.offline_created_at || order.order_date) }}</span>
          </div>
          <div class="strip-item">
            <span class="strip-label">Order Total</span>
            <span class="strip-val font-bold">{{ formatMoney(order.grand_total) }}</span>
          </div>
        </div>

        <!-- Conflict Lines List -->
        <div class="conflicts-list">
          <div
            v-for="(item, idx) in conflictItems"
            :key="item.product_id || idx"
            class="conflict-card"
          >
            <div class="conflict-card-header">
              <div class="item-identity">
                <span class="item-name">{{ item.product_name || item.name || `Item #${item.product_id}` }}</span>
                <span class="item-sku">SKU: {{ item.sku }}</span>
              </div>
              <span class="conflict-badge" :class="getConflictReasonClass(item.reason || item.conflict_type)">
                {{ formatReasonText(item.reason || item.conflict_type) }}
              </span>
            </div>

            <div class="conflict-details-box">
              <div class="detail-line">
                <span class="detail-label">Requested Quantity:</span>
                <span class="detail-val font-bold">{{ item.requested_qty || item.qty }}</span>
              </div>
              <div v-if="item.available_qty !== undefined" class="detail-line">
                <span class="detail-label">Current Available Stock:</span>
                <span class="detail-val" :class="{ 'text-danger': item.available_qty <= 0, 'text-warning': item.available_qty > 0 }">
                  {{ item.available_qty }} units
                </span>
              </div>
              <div v-if="item.current_price !== undefined" class="detail-line">
                <span class="detail-label">Current Price:</span>
                <span class="detail-val font-mono">{{ formatMoney(item.current_price) }}</span>
              </div>
              <div v-if="item.requested_price !== undefined && item.requested_price !== item.current_price" class="detail-line">
                <span class="detail-label">Requested Price:</span>
                <span class="detail-val font-mono line-through">{{ formatMoney(item.requested_price) }}</span>
              </div>
            </div>

            <!-- Resolution Action Choice -->
            <div class="resolution-options">
              <div class="option-label">Choose Action:</div>
              <div class="options-grid">
                <!-- If Insufficient Qty: Adjust Qty option -->
                <button
                  v-if="(item.available_qty || 0) > 0"
                  class="btn-choice"
                  :class="{ selected: getResolutionAction(item) === 'adjust_qty' }"
                  @click="setResolution(item, 'adjust_qty', { adjusted_qty: item.available_qty })"
                >
                  <span class="material-symbols-outlined">tune</span>
                  Adjust to {{ item.available_qty }} Units
                </button>

                <!-- Backorder option -->
                <button
                  class="btn-choice"
                  :class="{ selected: getResolutionAction(item) === 'backorder' }"
                  @click="setResolution(item, 'backorder')"
                >
                  <span class="material-symbols-outlined">hourglass_top</span>
                  Keep as Backorder
                </button>

                <!-- Substitute option -->
                <button
                  v-if="hasSubstituteOptions(item)"
                  class="btn-choice"
                  :class="{ selected: getResolutionAction(item) === 'substitute' }"
                  @click="selectSubstituteAction(item)"
                >
                  <span class="material-symbols-outlined">swap_calls</span>
                  Substitute
                </button>

                <!-- Accept Price (if price mismatch) -->
                <button
                  v-if="item.reason === 'PRICE_MISMATCH' || item.conflict_type === 'PRICE_MISMATCH' || (item.current_price !== undefined && item.requested_price !== undefined && item.current_price !== item.requested_price)"
                  class="btn-choice"
                  :class="{ selected: getResolutionAction(item) === 'accept_price' }"
                  @click="setResolution(item, 'accept_price', { new_unit_price: item.current_price, accepted_price: item.current_price })"
                >
                  <span class="material-symbols-outlined">check</span>
                  Accept New Price
                </button>

                <!-- Remove item option -->
                <button
                  class="btn-choice danger"
                  :class="{ selected: getResolutionAction(item) === 'remove_item' }"
                  @click="setResolution(item, 'remove_item')"
                >
                  <span class="material-symbols-outlined">delete</span>
                  Remove from Order
                </button>
              </div>
            </div>

            <!-- Extra Controls when Adjust Qty or Substitute is selected -->
            <div v-if="getResolutionAction(item) === 'adjust_qty'" class="extra-control-box">
              <label class="control-label">Adjusted Quantity:</label>
              <div class="qty-adjust-group">
                <button class="btn-step" @click="changeAdjustedQty(item, -1)">-</button>
                <input
                  type="number"
                  class="qty-input"
                  :value="getResolutionData(item).adjusted_qty"
                  @input="onAdjustedQtyInput(item, $event)"
                  min="1"
                  :max="item.available_qty || 9999"
                />
                <button class="btn-step" @click="changeAdjustedQty(item, 1)">+</button>
              </div>
            </div>

            <div v-if="getResolutionAction(item) === 'substitute'" class="extra-control-box">
              <label class="control-label">Select Substitute Item:</label>
              <select
                class="substitute-select"
                :value="getResolutionData(item).substitute_product_id || ''"
                @change="onSubstituteSelect(item, $event)"
              >
                <option value="" disabled>-- Choose Substitute Product --</option>
                <option
                  v-for="sub in getAvailableSubstitutes(item)"
                  :key="sub.id || sub.product_id"
                  :value="sub.id || sub.product_id"
                >
                  {{ sub.name || sub.product_name }} (SKU: {{ sub.sku }}) - {{ formatMoney(sub.base_price || sub.price || sub.unit_price) }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <button class="btn-delete-order" @click="handleDeleteOrder">
          <span class="material-symbols-outlined">delete_forever</span>
          Discard Order
        </button>

        <div class="footer-primary-actions">
          <button class="btn-secondary" @click="handleClose">
            Cancel
          </button>
          <button
            class="btn-primary"
            :disabled="resolving"
            @click="handleApplyResolutions"
          >
            <span v-if="resolving" class="material-symbols-outlined spin-icon">sync</span>
            <span v-else class="material-symbols-outlined">check_circle</span>
            Apply & Resync
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'

const props = defineProps({
  order: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'resolved'])

const store = useFieldSalesStore()
const { show: toast } = useToast()

const resolving = ref(false)
const resolutionsMap = ref({})

// Extract conflict items from order metadata
const conflictItems = computed(() => {
  if (!props.order) return []
  if (Array.isArray(props.order.conflicts) && props.order.conflicts.length > 0) {
    return props.order.conflicts
  }
  if (props.order.sync_error_details && Array.isArray(props.order.sync_error_details.conflicts)) {
    return props.order.sync_error_details.conflicts
  }
  // Fallback to lines that have stock mismatch
  return (props.order.lines || []).map((line) => ({
    line_number: line.line_number || 1,
    product_id: line.product_id,
    sku: line.sku,
    product_name: line.name || line.product_name,
    requested_qty: line.qty,
    available_qty: line.available_qty !== undefined ? line.available_qty : 0,
    reason: line.available_qty !== undefined && line.available_qty <= 0 ? 'OUT_OF_STOCK' : 'INSUFFICIENT_QTY'
  }))
})

// Initialize default resolutions when order changes
watch(
  () => props.order,
  () => {
    resolutionsMap.value = {}
    if (props.order) {
      for (const item of conflictItems.value) {
        const id = item.product_id
        if ((item.available_qty || 0) > 0) {
          resolutionsMap.value[id] = { action: 'adjust_qty', adjusted_qty: item.available_qty }
        } else if (item.reason === 'PRICE_MISMATCH' || item.conflict_type === 'PRICE_MISMATCH') {
          resolutionsMap.value[id] = { action: 'accept_price', new_unit_price: item.current_price, accepted_price: item.current_price }
        } else {
          resolutionsMap.value[id] = { action: 'backorder' }
        }
      }
    }
  },
  { immediate: true }
)

function getResolutionAction(item) {
  return resolutionsMap.value[item.product_id]?.action || 'backorder'
}

function getResolutionData(item) {
  return resolutionsMap.value[item.product_id] || {}
}

function setResolution(item, action, extras = {}) {
  resolutionsMap.value[item.product_id] = {
    action,
    product_id: item.product_id,
    line_number: item.line_number || 1,
    ...extras
  }
}

function hasSubstituteOptions(item) {
  if (item.suggested_substitute || item.substitute_product_id) return true
  if (Array.isArray(item.suggested_substitutes) && item.suggested_substitutes.length > 0) return true
  return store.products && store.products.length > 0
}

function getAvailableSubstitutes(item) {
  const subs = []
  if (item.suggested_substitutes && Array.isArray(item.suggested_substitutes)) {
    subs.push(...item.suggested_substitutes)
  }
  if (item.suggested_substitute) {
    if (!subs.some(s => (s.id || s.product_id) === (item.suggested_substitute.id || item.suggested_substitute.product_id))) {
      subs.push(item.suggested_substitute)
    }
  }
  // Add matching catalog products excluding current product
  if (store.products && store.products.length > 0) {
    const catalogFiltered = store.products.filter(p => p.id !== item.product_id && !subs.some(s => (s.id || s.product_id) === p.id))
    subs.push(...catalogFiltered)
  }
  return subs
}

function getSubstituteProductId(item) {
  const subs = getAvailableSubstitutes(item)
  if (subs.length > 0) {
    return subs[0].id || subs[0].product_id
  }
  return item.substitute_product_id || null
}

function selectSubstituteAction(item) {
  const subId = getSubstituteProductId(item)
  const subs = getAvailableSubstitutes(item)
  const subItem = subs.find(s => (s.id || s.product_id) === subId)
  setResolution(item, 'substitute', {
    substitute_product_id: subId,
    substitute_product_name: subItem?.name || subItem?.product_name || ''
  })
}

function changeAdjustedQty(item, delta) {
  const current = Number(getResolutionData(item).adjusted_qty) || 1
  const max = item.available_qty || 9999
  const next = Math.max(1, Math.min(max, current + delta))
  setResolution(item, 'adjust_qty', { adjusted_qty: next })
}

function onAdjustedQtyInput(item, event) {
  const val = Math.max(1, Number(event.target.value) || 1)
  setResolution(item, 'adjust_qty', { adjusted_qty: val })
}

function onSubstituteSelect(item, event) {
  const subId = Number(event.target.value)
  const subs = getAvailableSubstitutes(item)
  const subItem = subs.find(s => (s.id || s.product_id) === subId)
  setResolution(item, 'substitute', {
    substitute_product_id: subId,
    substitute_product_name: subItem?.name || subItem?.product_name || ''
  })
}

function truncateUuid(uuid) {
  if (!uuid) return ''
  return uuid.length > 18 ? `${uuid.slice(0, 8)}...${uuid.slice(-6)}` : uuid
}

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return d
  }
}

function formatMoney(amount) {
  const num = Number(amount) || 0
  return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function getConflictReasonClass(reason) {
  if (reason === 'OUT_OF_STOCK') return 'badge-danger'
  if (reason === 'INSUFFICIENT_QTY') return 'badge-warning'
  if (reason === 'PRICE_MISMATCH') return 'badge-info'
  return 'badge-secondary'
}

function formatReasonText(reason) {
  if (reason === 'OUT_OF_STOCK') return 'Out of Stock'
  if (reason === 'INSUFFICIENT_QTY') return 'Insufficient Quantity'
  if (reason === 'PRICE_MISMATCH') return 'Price Mismatch'
  if (reason === 'CREDIT_LIMIT_EXCEEDED') return 'Credit Limit Exceeded'
  return reason || 'Conflict'
}

function handleClose() {
  emit('close')
}

async function handleDeleteOrder() {
  if (!props.order) return
  if (window.confirm('Are you sure you want to discard and delete this offline order?')) {
    try {
      await store.deleteQueuedOrder(props.order.client_order_uuid)
      toast('Order removed from sync queue', 'info')
      emit('close')
    } catch (err) {
      toast(`Failed to delete order: ${err.message}`, 'error')
    }
  }
}

async function handleApplyResolutions() {
  if (!props.order) return
  resolving.value = true

  const resolutionsList = Object.entries(resolutionsMap.value).map(([productId, config]) => {
    const item = conflictItems.value.find(i => String(i.product_id) === String(productId))
    return {
      line_number: item?.line_number || 1,
      product_id: Number(productId),
      action: config.action,
      adjusted_qty: config.adjusted_qty !== undefined ? Number(config.adjusted_qty) : null,
      substitute_product_id: config.substitute_product_id ? Number(config.substitute_product_id) : null,
      substitute_product_name: config.substitute_product_name || null,
      accepted_price: config.new_unit_price || config.accepted_price || null,
      new_unit_price: config.new_unit_price || config.accepted_price || null
    }
  })

  try {
    const result = await store.resolveOrderConflict(props.order.client_order_uuid, resolutionsList)
    if (result && (result.status === 'Synced' || result.status === 'AlreadySynced' || result.success)) {
      toast('Conflict resolved and order synced successfully!', 'success')
      emit('resolved', result)
      emit('close')
    } else {
      toast(`Conflict resolution completed with status: ${result?.status || 'Pending'}`, 'info')
      emit('close')
    }
  } catch (err) {
    toast(`Failed to resolve conflict: ${err.message}`, 'error')
  } finally {
    resolving.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.conflict-modal {
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-surface);
}

.header-icon-danger {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #fee2e2;
  color: #dc2626;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-text {
  flex: 1;
  min-width: 0;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
}

.btn-close:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

/* Body */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.order-summary-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 8px 12px;
}

.strip-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.strip-label {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
}

.strip-val {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.font-mono {
  font-family: monospace;
}

.font-bold {
  font-weight: 700;
}

.line-through {
  text-decoration: line-through;
}

/* Conflict items */
.conflicts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conflict-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.conflict-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.item-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.item-sku {
  font-size: 11px;
  color: var(--text-subtle);
}

.conflict-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

.badge-warning {
  background: #fef3c7;
  color: #92400e;
}

.badge-info {
  background: #dbeafe;
  color: #1e40af;
}

.badge-secondary {
  background: var(--bg-surface-low);
  color: var(--text-muted);
}

.conflict-details-box {
  background: var(--bg-surface-low, #f9fafb);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-line {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.detail-label {
  color: var(--text-muted);
}

.detail-val {
  font-weight: 600;
  color: var(--text-primary);
}

.text-danger {
  color: var(--color-error, #dc2626);
}

.text-warning {
  color: #d97706;
}

/* Resolution Options Grid */
.resolution-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

@media (max-width: 460px) {
  .options-grid {
    grid-template-columns: 1fr;
  }
}

.btn-choice {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-input);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.btn-choice:hover {
  background: var(--bg-surface-hover);
  border-color: var(--color-primary);
}

.btn-choice.selected {
  background: var(--bg-primary-faded, #e6deff);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 700;
}

.btn-choice.danger.selected {
  background: #fee2e2;
  border-color: #ef4444;
  color: #991b1b;
}

.btn-choice .material-symbols-outlined {
  font-size: 16px;
}

/* Extra controls */
.extra-control-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background: var(--bg-surface-low, #f9fafb);
  border-radius: 8px;
  border: 1px dashed var(--border-default);
}

.control-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.qty-adjust-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-step {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border-input);
  background: var(--bg-surface);
  font-weight: 700;
  cursor: pointer;
}

.qty-input {
  width: 60px;
  height: 28px;
  text-align: center;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-weight: 700;
}

.substitute-select {
  width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-input);
  background: var(--bg-surface);
  font-size: 12px;
  color: var(--text-primary);
}

/* Modal Footer */
.modal-footer {
  padding: 14px 16px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-surface);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.btn-delete-order {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 8px;
  background: none;
  border: 1px solid var(--border-input);
  color: var(--color-error, #dc2626);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-delete-order:hover {
  background: #fef2f2;
}

.footer-primary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  padding: 8px 14px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--bg-surface-hover);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1s infinite linear;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

<template>
  <div class="portal-order-detail-page" :dir="dir">
    <div class="portal-container">
      <!-- Loading Skeleton -->
      <div v-if="portal.ordersLoading && !order" class="detail-loading-box">
        <div class="skeleton-shimmer skeleton-header"></div>
        <div class="skeleton-cards-grid">
          <div class="skeleton-shimmer skeleton-card"></div>
          <div class="skeleton-shimmer skeleton-card"></div>
        </div>
        <div class="skeleton-shimmer skeleton-table"></div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.ordersError && !order" class="detail-error-card">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('order-load-error', 'Unable to Load Order Details') }}</h3>
        <p>{{ portal.ordersError }}</p>
        <div class="error-actions">
          <router-link to="/portal/orders" class="btn-outline">
            <span class="material-symbols-outlined">arrow_back</span>
            <span>{{ t('back-to-orders', 'Back to Order History') }}</span>
          </router-link>
          <button class="btn-primary" @click="loadOrderDetail">
            <span class="material-symbols-outlined">refresh</span>
            <span>{{ t('retry', 'Retry') }}</span>
          </button>
        </div>
      </div>

      <!-- Order Detail View -->
      <div v-else-if="order" class="order-detail-content">
        <!-- Top Navigation & Breadcrumbs -->
        <div class="detail-top-nav">
          <router-link to="/portal/orders" class="back-link">
            <span class="material-symbols-outlined">arrow_back</span>
            <span>{{ t('back-to-orders', 'Back to Order History') }}</span>
          </router-link>
        </div>

        <!-- Header Section -->
        <div class="order-header-card">
          <div class="header-left-col">
            <div class="order-title-row">
              <h1 class="order-title">{{ t('sales-order', 'Replenishment Order') }} #{{ order.order_number }}</h1>
              <span class="status-badge" :class="getStatusBadgeClass(order.status)">
                <span class="status-dot"></span>
                <span>{{ order.status }}</span>
              </span>
            </div>
            <p class="order-meta-desc">
              {{ t('placed-on', 'Placed on') }} <strong>{{ formatDate(order.order_date) }}</strong>
              <span v-if="order.requested_delivery_date"> &bull; {{ t('requested-delivery', 'Requested Delivery') }}: <strong>{{ formatDate(order.requested_delivery_date) }}</strong></span>
            </p>
          </div>

          <!-- Top Action Buttons -->
          <div class="header-right-actions">
            <!-- 1-Click Reorder Button -->
            <button class="btn-action-primary" @click="openReorderModal" :title="t('reorder-these-supplies', '1-Click Reorder Standard Supplies')">
              <span class="material-symbols-outlined">repeat</span>
              <span>{{ t('reorder-supplies', 'Reorder Supplies') }}</span>
            </button>

            <!-- Load into Cart Button -->
            <button class="btn-action-secondary" @click="loadToCart" :title="t('load-to-cart-desc', 'Load these items into active cart')">
              <span class="material-symbols-outlined">add_shopping_cart</span>
              <span>{{ t('load-to-cart', 'Load to Cart') }}</span>
            </button>

            <!-- Cancel Order Button (if allowed) -->
            <button v-if="canCancelOrder" class="btn-action-danger" @click="openCancelModal">
              <span class="material-symbols-outlined">close</span>
              <span>{{ t('cancel-order', 'Cancel Order') }}</span>
            </button>
          </div>
        </div>

        <!-- Visual Fulfillment Step Tracker -->
        <div class="fulfillment-tracker-card">
          <div class="tracker-header">
            <span class="material-symbols-outlined tracker-icon">local_shipping</span>
            <span class="tracker-heading">{{ t('fulfillment-progress', 'Fulfillment & Delivery Progress') }}</span>
          </div>

          <div class="tracker-steps" :class="{ 'is-cancelled-order': order.status === 'Cancelled' }">
            <div
              v-for="(step, idx) in fulfillmentSteps"
              :key="step.key"
              class="tracker-step"
              :class="{
                'step-completed': isStepCompleted(step.key),
                'step-current': isStepCurrent(step.key),
                'step-upcoming': isStepUpcoming(step.key),
              }"
            >
              <div class="step-marker-row">
                <div class="step-circle">
                  <span class="material-symbols-outlined" v-if="isStepCompleted(step.key)">check</span>
                  <span class="material-symbols-outlined" v-else-if="isStepCurrent(step.key)">{{ step.icon }}</span>
                  <span class="step-num" v-else>{{ idx + 1 }}</span>
                </div>
                <div class="step-line" v-if="idx < fulfillmentSteps.length - 1"></div>
              </div>
              <div class="step-label-area">
                <span class="step-title">{{ step.label }}</span>
                <span class="step-sub">{{ step.description }}</span>
              </div>
            </div>
          </div>

          <!-- Cancelled Banner if Order was Cancelled -->
          <div v-if="order.status === 'Cancelled'" class="cancelled-alert-banner">
            <span class="material-symbols-outlined">cancel</span>
            <span>{{ t('order-is-cancelled-desc', 'This replenishment order has been cancelled and will not be fulfilled.') }}</span>
          </div>
        </div>

        <!-- 2-Column Summary Cards -->
        <div class="summary-cards-grid">
          <!-- Order & Fulfillment Information Card -->
          <div class="info-card">
            <div class="card-header">
              <span class="material-symbols-outlined card-header-icon">info</span>
              <h3>{{ t('order-info', 'Fulfillment & Delivery Details') }}</h3>
            </div>
            <div class="card-body">
              <div class="info-data-row">
                <span class="info-label">{{ t('order-number', 'Order Number') }}:</span>
                <span class="info-val font-mono">{{ order.order_number }}</span>
              </div>
              <div class="info-data-row">
                <span class="info-label">{{ t('order-date', 'Order Date') }}:</span>
                <span class="info-val">{{ formatDate(order.order_date) }}</span>
              </div>
              <div class="info-data-row">
                <span class="info-label">{{ t('requested-delivery-date', 'Requested Delivery') }}:</span>
                <span class="info-val font-semibold text-accent">{{ formatDate(order.requested_delivery_date) }}</span>
              </div>
              <div class="info-data-row">
                <span class="info-label">{{ t('customer-name', 'Account Name') }}:</span>
                <span class="info-val">{{ order.customer_name || portal.accountSummary?.company_name || 'Customer' }}</span>
              </div>
              <div class="info-data-row" v-if="order.notes">
                <span class="info-label">{{ t('delivery-instructions', 'Special Notes') }}:</span>
                <span class="info-val notes-val">{{ order.notes }}</span>
              </div>
            </div>
          </div>

          <!-- Financial Summary Card -->
          <div class="info-card">
            <div class="card-header">
              <span class="material-symbols-outlined card-header-icon">receipt</span>
              <h3>{{ t('financial-summary', 'Payment & Invoice Summary') }}</h3>
            </div>
            <div class="card-body">
              <div class="info-data-row">
                <span class="info-label">{{ t('subtotal', 'Subtotal') }}:</span>
                <span class="info-val font-mono">${{ (order.subtotal || 0).toFixed(2) }}</span>
              </div>
              <div class="info-data-row">
                <span class="info-label">{{ t('tax', 'Tax') }}:</span>
                <span class="info-val font-mono">${{ (order.tax || 0).toFixed(2) }}</span>
              </div>
              <div class="info-data-row total-highlight-row">
                <span class="info-label font-bold">{{ t('grand-total', 'Grand Total') }}:</span>
                <span class="info-val total-grand font-mono font-bold">${{ (order.grand_total || order.subtotal || 0).toFixed(2) }}</span>
              </div>

              <!-- Quick Link to Invoices -->
              <div class="invoice-link-prompt">
                <router-link to="/portal/invoices" class="btn-invoice-link">
                  <span class="material-symbols-outlined">payments</span>
                  <span>{{ t('view-open-invoices', 'View & Settle Invoices') }}</span>
                  <span class="material-symbols-outlined">arrow_forward</span>
                </router-link>
              </div>
            </div>
          </div>
        </div>

        <!-- Itemized Line Items Card -->
        <div class="line-items-card">
          <div class="card-header">
            <div class="card-header-left">
              <span class="material-symbols-outlined card-header-icon">format_list_bulleted</span>
              <h3>{{ t('itemized-order-lines', 'Itemized Order Line Items') }} ({{ order.lines ? order.lines.length : 0 }})</h3>
            </div>
          </div>

          <div class="table-wrap">
            <table class="lines-table">
              <thead>
                <tr>
                  <th class="col-num-index">#</th>
                  <th>{{ t('product-details', 'Product Details') }}</th>
                  <th>{{ t('uom', 'UOM') }}</th>
                  <th class="text-right">{{ t('contracted-price', 'Unit Price') }}</th>
                  <th class="text-center">{{ t('qty-ordered', 'Qty') }}</th>
                  <th class="text-right">{{ t('line-total', 'Line Total') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in order.lines" :key="line.id || idx" class="line-row">
                  <td class="col-num-index font-mono">{{ idx + 1 }}</td>
                  <td class="cell-product-info">
                    <div class="product-info-cluster">
                      <span class="product-name-title">{{ line.product_name }}</span>
                      <div class="product-code-row" v-if="line.product_code">
                        <span class="sku-pill font-mono">{{ line.product_code }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="cell-uom">
                    <span class="uom-pill">{{ line.uom_name || 'Ea' }}</span>
                  </td>
                  <td class="cell-unit-price text-right font-mono">
                    ${{ (line.unit_price || 0).toFixed(2) }}
                  </td>
                  <td class="cell-qty text-center font-bold font-mono">
                    {{ line.qty }}
                  </td>
                  <td class="cell-line-total text-right font-mono font-bold">
                    ${{ (line.line_total || ((line.unit_price || 0) * line.qty)).toFixed(2) }}
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="tfoot-row">
                  <td colspan="4" class="text-right font-bold">{{ t('subtotal', 'Subtotal') }}:</td>
                  <td colspan="2" class="text-right font-mono font-bold">${{ (order.subtotal || 0).toFixed(2) }}</td>
                </tr>
                <tr class="tfoot-row">
                  <td colspan="4" class="text-right">{{ t('tax', 'Estimated Wholesale Tax') }}:</td>
                  <td colspan="2" class="text-right font-mono">${{ (order.tax || 0).toFixed(2) }}</td>
                </tr>
                <tr class="tfoot-row grand-total-tfoot">
                  <td colspan="4" class="text-right font-bold">{{ t('grand-total', 'Grand Total') }}:</td>
                  <td colspan="2" class="text-right font-mono font-bold total-grand">${{ (order.grand_total || order.subtotal || 0).toFixed(2) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 1-Click Reorder Modal -->
    <div v-if="showReorderModal" class="modal-overlay" @click.self="showReorderModal = false">
      <div class="reorder-modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-icon-badge">
              <span class="material-symbols-outlined">repeat</span>
            </div>
            <div>
              <h3>{{ t('reorder-title', 'Reorder Supplies') }}</h3>
              <p class="modal-subtitle">{{ t('reorder-from-order', 'Replenish items from order') }} <strong>#{{ order?.order_number }}</strong></p>
            </div>
          </div>
          <button class="btn-close-modal" @click="showReorderModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="reorder-options-box">
            <div class="option-mode-toggle">
              <label class="mode-radio-label" :class="{ selected: reorderMode === 'direct' }">
                <input type="radio" v-model="reorderMode" value="direct" />
                <div class="mode-text-wrap">
                  <span class="mode-title">{{ t('instant-1click-reorder', 'Instant 1-Click Order Submission') }}</span>
                  <span class="mode-desc">{{ t('instant-reorder-desc', 'Creates a new order immediately using your contracted pricing.') }}</span>
                </div>
              </label>

              <label class="mode-radio-label" :class="{ selected: reorderMode === 'cart' }">
                <input type="radio" v-model="reorderMode" value="cart" />
                <div class="mode-text-wrap">
                  <span class="mode-title">{{ t('load-to-cart', 'Load Items into Cart to Modify') }}</span>
                  <span class="mode-desc">{{ t('load-cart-desc', 'Loads these items into your replenishment cart so you can adjust quantities.') }}</span>
                </div>
              </label>
            </div>

            <!-- Direct Reorder Settings -->
            <div v-if="reorderMode === 'direct'" class="direct-reorder-fields">
              <div class="form-group">
                <label class="field-label">
                  <span class="material-symbols-outlined mini-icon">event</span>
                  {{ t('requested-delivery-date', 'Requested Delivery Date') }}
                </label>
                <input
                  type="date"
                  v-model="reorderDeliveryDate"
                  :min="minDeliveryDate"
                  class="portal-input"
                />
                <span class="input-hint" v-if="portal.nextDeliveryDate">
                  Earliest available: {{ portal.nextDeliveryDate }}
                </span>
              </div>

              <div class="form-group">
                <label class="field-label">
                  <span class="material-symbols-outlined mini-icon">edit_note</span>
                  {{ t('reorder-notes', 'Delivery Notes / Special Instructions') }}
                </label>
                <textarea
                  v-model="reorderNotes"
                  rows="2"
                  class="portal-textarea"
                  :placeholder="t('delivery-notes-placeholder', 'e.g., Deliver to kitchen back dock before 10 AM...')"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showReorderModal = false" :disabled="isReordering">
            {{ t('cancel', 'Cancel') }}
          </button>
          <button class="btn-primary" @click="executeReorder" :disabled="isReordering">
            <span class="material-symbols-outlined" v-if="!isReordering">repeat</span>
            <span class="material-symbols-outlined spin-icon" v-else>sync</span>
            <span>{{ isReordering ? t('reordering', 'Placing Reorder...') : (reorderMode === 'cart' ? t('load-items-cart', 'Load to Cart & Proceed') : t('confirm-reorder', 'Submit Replenishment Order')) }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Cancel Order Confirmation Modal -->
    <div v-if="showCancelModal" class="modal-overlay" @click.self="showCancelModal = false">
      <div class="cancel-modal-card">
        <div class="cancel-header">
          <div class="warning-icon-badge">
            <span class="material-symbols-outlined">warning</span>
          </div>
          <h3>{{ t('cancel-order-title', 'Cancel Replenishment Order') }}</h3>
          <p class="modal-subtitle">
            {{ t('cancel-order-prompt', 'Are you sure you want to cancel order') }} <strong>#{{ order?.order_number }}</strong>?
          </p>
        </div>

        <div class="cancel-body">
          <p class="cancel-warning-text">
            {{ t('cancel-warning', 'Cancelling this order will release any allocated stock and mark the order as Cancelled.') }}
          </p>
          <div class="form-group">
            <label class="field-label">{{ t('cancellation-reason', 'Cancellation Reason (Optional)') }}</label>
            <input
              type="text"
              v-model="cancelReason"
              class="portal-input"
              :placeholder="t('reason-placeholder', 'e.g., Ordered duplicate items by mistake')"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showCancelModal = false" :disabled="isCancelling">
            {{ t('keep-order', 'Keep Order') }}
          </button>
          <button class="btn-danger" @click="executeCancel" :disabled="isCancelling">
            <span class="material-symbols-outlined" v-if="!isCancelling">delete_forever</span>
            <span class="material-symbols-outlined spin-icon" v-else>sync</span>
            <span>{{ isCancelling ? t('cancelling', 'Cancelling...') : t('confirm-cancel-order', 'Yes, Cancel Order') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

const showReorderModal = ref(false)
const reorderMode = ref('direct')
const reorderDeliveryDate = ref('')
const reorderNotes = ref('')
const isReordering = ref(false)

const showCancelModal = ref(false)
const cancelReason = ref('')
const isCancelling = ref(false)

const order = computed(() => portal.currentOrder)

const canCancelOrder = computed(() => {
  return order.value && ['Pending', 'Confirmed', 'Draft'].includes(order.value.status)
})

const fulfillmentSteps = [
  { key: 'Draft', label: 'Draft / Placed', description: 'Order submitted', icon: 'edit_document' },
  { key: 'Confirmed', label: 'Confirmed', description: 'Stock reserved', icon: 'check_circle' },
  { key: 'Shipped', label: 'Shipped', description: 'On delivery route', icon: 'local_shipping' },
  { key: 'Delivered', label: 'Delivered', description: 'Fulfillment completed', icon: 'task_alt' },
]

const statusOrderMap = {
  Draft: 0,
  Pending: 1,
  Confirmed: 1,
  Processing: 1,
  Shipped: 2,
  Delivered: 3,
}

function isStepCompleted(stepKey) {
  if (!order.value || order.value.status === 'Cancelled') return false
  const currentIdx = statusOrderMap[order.value.status] ?? 0
  const stepIdx = statusOrderMap[stepKey] ?? 0
  return currentIdx > stepIdx
}

function isStepCurrent(stepKey) {
  if (!order.value || order.value.status === 'Cancelled') return false
  const currentIdx = statusOrderMap[order.value.status] ?? 0
  const stepIdx = statusOrderMap[stepKey] ?? 0
  return currentIdx === stepIdx
}

function isStepUpcoming(stepKey) {
  if (!order.value || order.value.status === 'Cancelled') return true
  const currentIdx = statusOrderMap[order.value.status] ?? 0
  const stepIdx = statusOrderMap[stepKey] ?? 0
  return currentIdx < stepIdx
}

const minDeliveryDate = computed(() => {
  if (portal.cutoffStatus?.next_delivery_date) {
    return portal.cutoffStatus.next_delivery_date
  }
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  return tomorrow.toISOString().split('T')[0]
})

function formatDate(val) {
  if (!val) return '-'
  try {
    const d = new Date(val)
    if (isNaN(d.getTime())) return val
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return val
  }
}

function getStatusBadgeClass(status) {
  const map = {
    Confirmed: 'badge-blue',
    Shipped: 'badge-purple',
    Delivered: 'badge-green',
    Processing: 'badge-indigo',
    Pending: 'badge-amber',
    Draft: 'badge-neutral',
    Cancelled: 'badge-red',
  }
  return map[status] || 'badge-neutral'
}

async function loadOrderDetail() {
  const orderId = route.params.id
  if (orderId) {
    await portal.fetchOrderDetail(orderId)
  }
}

function openReorderModal() {
  if (!order.value) return
  showReorderModal.value = true
  reorderMode.value = 'direct'
  reorderDeliveryDate.value = portal.cutoffStatus?.next_delivery_date || ''
  reorderNotes.value = order.value.notes || ''
}

function loadToCart() {
  if (!order.value) return
  const count = portal.loadOrderToCart(order.value, false)
  showToast(t('reorder-loaded-toast', `Loaded ${count} items into your replenishment cart!`), 'success', 3000)
  router.push('/portal/cart')
}

async function executeReorder() {
  if (!order.value) return

  if (reorderMode.value === 'cart') {
    loadToCart()
    showReorderModal.value = false
    return
  }

  isReordering.value = true
  try {
    const payload = {
      requested_delivery_date: reorderDeliveryDate.value || null,
      notes: reorderNotes.value || null,
      status: 'Confirmed',
    }
    const newOrder = await portal.reorderPastOrder(order.value.id, payload)
    if (newOrder) {
      showToast(t('reorder-success-toast', `Reorder placed successfully! Order #${newOrder.order_number}`), 'success', 4000)
      showReorderModal.value = false
      router.push(`/portal/orders/${newOrder.id}`)
    }
  } catch (err) {
    showToast(err.message || t('reorder-failed-toast', 'Failed to place reorder'), 'error', 4000)
  } finally {
    isReordering.value = false
  }
}

function openCancelModal() {
  showCancelModal.value = true
  cancelReason.value = ''
}

async function executeCancel() {
  if (!order.value) return
  isCancelling.value = true
  try {
    await portal.cancelOrder(order.value.id, cancelReason.value)
    showToast(t('order-cancelled-toast', `Order #${order.value.order_number} cancelled`), 'info', 3000)
    showCancelModal.value = false
    await loadOrderDetail()
  } catch (err) {
    showToast(err.message || t('cancel-failed-toast', 'Failed to cancel order'), 'error', 4000)
  } finally {
    isCancelling.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    loadOrderDetail(),
    portal.fetchCutoffStatus(),
    portal.fetchAccountSummary(),
  ])
})
</script>

<style scoped>
.portal-order-detail-page {
  width: 100%;
}

.portal-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Loading & Error */
.detail-loading-box {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.skeleton-shimmer {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.03) 25%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.03) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 12px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-header { height: 100px; }
.skeleton-cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.skeleton-card { height: 200px; }
.skeleton-table { height: 300px; }

.detail-error-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 60px 24px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
  color: #f87171;
  margin-bottom: 12px;
}

.detail-error-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 8px;
}

.detail-error-card p {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 24px;
}

.error-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

/* Top Nav */
.detail-top-nav {
  margin-bottom: 16px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #a5b4fc;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.15s;
}

.back-link:hover {
  color: #fff;
}

.back-link .material-symbols-outlined {
  font-size: 18px;
}

/* Header Card */
.order-header-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.order-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}

.order-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  letter-spacing: -0.3px;
  margin: 0;
}

.order-meta-desc {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-action-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border: none;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  transition: all 0.15s;
}

.btn-action-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.5);
}

.btn-action-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-action-secondary:hover {
  background: var(--bg-surface-hover, #2a2a4a);
  border-color: #6366f1;
}

.btn-action-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-action-danger:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* Fulfillment Tracker Card */
.fulfillment-tracker-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.tracker-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.tracker-icon {
  font-size: 22px;
  color: #818cf8;
}

.tracker-heading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.tracker-steps {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

@media (max-width: 768px) {
  .tracker-steps {
    flex-direction: column;
    gap: 20px;
  }
}

.tracker-step {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.step-marker-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-body, #0f0f1a);
  border: 2px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted, #94a3b8);
  flex-shrink: 0;
  transition: all 0.2s;
}

.step-line {
  flex: 1;
  height: 2px;
  background: var(--border-default, #2a2a4a);
  margin: 0 8px;
}

.step-completed .step-circle {
  background: #22c55e;
  border-color: #22c55e;
  color: #fff;
}

.step-completed .step-line {
  background: #22c55e;
}

.step-current .step-circle {
  background: rgba(99, 102, 241, 0.2);
  border-color: #6366f1;
  color: #a5b4fc;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);
}

.step-label-area {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 2px;
}

.step-upcoming .step-title {
  color: var(--text-muted, #94a3b8);
}

.step-sub {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.cancelled-alert-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
  font-size: 13px;
  font-weight: 600;
}

/* 2-Column Summary Cards */
.summary-cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

@media (max-width: 860px) {
  .summary-cards-grid {
    grid-template-columns: 1fr;
  }
}

.info-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
}

.card-header-icon {
  font-size: 20px;
  color: #a5b4fc;
}

.card-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.card-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-data-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.info-label {
  color: var(--text-secondary, #94a3b8);
}

.info-val {
  color: var(--text-primary, #fff);
  font-weight: 500;
}

.notes-val {
  max-width: 60%;
  text-align: right;
  font-style: italic;
}

.total-highlight-row {
  border-top: 1px solid var(--border-default, #2a2a4a);
  padding-top: 12px;
  margin-top: 4px;
}

.total-grand {
  font-size: 18px;
  color: #a5b4fc;
}

.text-accent {
  color: #4ade80 !important;
}

.invoice-link-prompt {
  margin-top: 8px;
}

.btn-invoice-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #a5b4fc;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}

.btn-invoice-link:hover {
  background: rgba(99, 102, 241, 0.18);
  color: #fff;
  border-color: #6366f1;
}

.btn-invoice-link .material-symbols-outlined {
  font-size: 18px;
}

/* Itemized Line Items Card */
.line-items-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 24px;
}

.table-wrap {
  overflow-x: auto;
}

.lines-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.lines-table th {
  background: rgba(0, 0, 0, 0.2);
  padding: 12px 18px;
  text-align: left;
  font-weight: 700;
  color: var(--text-muted, #94a3b8);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  white-space: nowrap;
}

.lines-table td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  vertical-align: middle;
}

.col-num-index {
  width: 40px;
  color: var(--text-muted, #94a3b8);
}

.cell-product-info {
  min-width: 220px;
}

.product-info-cluster {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.product-name-title {
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.product-code-row {
  margin-top: 2px;
}

.sku-pill {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  background: rgba(255, 255, 255, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
}

.cell-uom {
  width: 80px;
}

.uom-pill {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  color: var(--text-secondary, #94a3b8);
}

.tfoot-row td {
  background: rgba(0, 0, 0, 0.15);
  padding: 10px 18px;
}

.grand-total-tfoot td {
  border-top: 1px solid var(--border-default, #2a2a4a);
  font-size: 15px;
}

/* Badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 11px;
  font-weight: 700;
  text-transform: capitalize;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.badge-green {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}
.badge-green .status-dot { background: #4ade80; }

.badge-blue {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}
.badge-blue .status-dot { background: #818cf8; }

.badge-purple {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}
.badge-purple .status-dot { background: #c084fc; }

.badge-amber {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.badge-amber .status-dot { background: #fbbf24; }

.badge-neutral {
  background: rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.badge-neutral .status-dot { background: #94a3b8; }

.badge-red {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.badge-red .status-dot { background: #f87171; }

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.reorder-modal-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  width: 580px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  background: rgba(0, 0, 0, 0.15);
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-icon-badge {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a5b4fc;
}

.modal-icon-badge .material-symbols-outlined {
  font-size: 22px;
}

.modal-title-wrap h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  margin: 2px 0 0;
}

.btn-close-modal {
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
}

.btn-close-modal:hover {
  color: #fff;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.option-mode-toggle {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
}

.mode-radio-label {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-default, #2a2a4a);
  background: var(--bg-body, #0f0f1a);
  cursor: pointer;
  transition: all 0.15s;
}

.mode-radio-label.selected {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.mode-radio-label input[type="radio"] {
  margin-top: 3px;
  accent-color: #6366f1;
}

.mode-text-wrap {
  display: flex;
  flex-direction: column;
}

.mode-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 2px;
}

.mode-desc {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}

.direct-reorder-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 6px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
  display: flex;
  align-items: center;
  gap: 4px;
}

.portal-input, .portal-textarea {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
}

.portal-input:focus, .portal-textarea:focus {
  border-color: #6366f1;
}

.input-hint {
  font-size: 11px;
  color: #4ade80;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-default, #2a2a4a);
  background: rgba(0, 0, 0, 0.15);
}

/* Cancel Modal */
.cancel-modal-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  width: 480px;
  max-width: 95vw;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}

.cancel-header {
  padding: 24px 24px 12px;
  text-align: center;
}

.warning-icon-badge {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.15);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #f87171;
  margin-bottom: 12px;
}

.warning-icon-badge .material-symbols-outlined {
  font-size: 28px;
}

.cancel-header h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 4px;
}

.cancel-body {
  padding: 0 24px 20px;
}

.cancel-warning-text {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.5;
  margin-bottom: 16px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: 10px 14px;
  border-radius: 8px;
}

/* Generic Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  padding: 9px 18px;
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-outline:hover:not(:disabled) {
  background: var(--bg-surface-hover, #2a2a4a);
  color: #fff;
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #dc2626;
  color: #fff;
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.text-center { text-align: center; }
.text-right { text-align: right; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-mono { font-family: monospace; }

[dir="rtl"] .lines-table th { text-align: right; }
[dir="rtl"] .lines-table td { text-align: right; }
[dir="rtl"] .text-right { text-align: left; }
</style>

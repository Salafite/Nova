<template>
  <div class="portal-order-detail-page" :dir="dir">
    <div class="portal-container">
      <!-- Breadcrumbs & Header -->
      <div class="detail-header-section">
        <div class="header-left">
          <router-link to="/portal/orders" class="back-link">
            <span class="material-symbols-outlined">arrow_back</span>
            <span>{{ t('back-to-orders', 'Back to Order History') }}</span>
          </router-link>
          <div class="title-status-row" v-if="order">
            <h1 class="page-title">{{ t('order-num-prefix', 'Order') }} #{{ order.order_number }}</h1>
            <span class="status-badge" :class="getStatusBadgeClass(order.status)">
              <span class="material-symbols-outlined status-icon">{{ getStatusIcon(order.status) }}</span>
              <span>{{ order.status }}</span>
            </span>
          </div>
          <p class="order-meta-text" v-if="order">
            {{ t('placed-on', 'Placed on') }} {{ formatDate(order.order_date) }}
            <span v-if="order.created_at">at {{ formatTime(order.created_at) }}</span>
          </p>
        </div>

        <!-- Top Action Buttons -->
        <div class="header-actions" v-if="order">
          <button
            v-if="portal.allowReorders && order.status !== 'Cancelled'"
            class="btn-primary-reorder"
            @click="openReorderModal"
          >
            <span class="material-symbols-outlined">repeat</span>
            <span>{{ t('1-click-reorder', '1-Click Reorder Supplies') }}</span>
          </button>

          <button
            class="btn-secondary-cart"
            @click="handleLoadToCart"
          >
            <span class="material-symbols-outlined">add_shopping_cart</span>
            <span>{{ t('add-items-to-cart', 'Add Items to Cart') }}</span>
          </button>

          <button
            v-if="isCancellable(order.status)"
            class="btn-outline-danger"
            @click="openCancelModal"
          >
            <span class="material-symbols-outlined">cancel</span>
            <span>{{ t('cancel-order', 'Cancel Order') }}</span>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portal.ordersLoading" class="detail-loading-state">
        <div class="skeleton-stepper-card">
          <div class="skeleton-shimmer skeleton-stepper"></div>
        </div>
        <div class="skeleton-grid">
          <div class="skeleton-shimmer skeleton-card-box"></div>
          <div class="skeleton-shimmer skeleton-card-box"></div>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.ordersError" class="detail-error-card">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('order-not-found', 'Order Not Found') }}</h3>
        <p>{{ portal.ordersError }}</p>
        <router-link to="/portal/orders" class="btn-primary">
          <span class="material-symbols-outlined">arrow_back</span>
          <span>{{ t('return-to-orders', 'Return to Order History') }}</span>
        </router-link>
      </div>

      <!-- Order Detail Content -->
      <div v-else-if="order" class="order-content-wrapper">
        <!-- Fulfillment Stepper Timeline -->
        <div class="stepper-card">
          <h3 class="stepper-title">
            <span class="material-symbols-outlined">timeline</span>
            <span>{{ t('fulfillment-progress', 'Fulfillment Progress') }}</span>
          </h3>

          <div class="fulfillment-stepper" v-if="order.status !== 'Cancelled'">
            <div
              v-for="(step, idx) in fulfillmentSteps"
              :key="step.key"
              class="stepper-step"
              :class="{
                'step-completed': isStepCompleted(step.key),
                'step-current': isStepCurrent(step.key),
                'step-pending': isStepPending(step.key)
              }"
            >
              <div class="step-connector-line" v-if="idx > 0"></div>
              <div class="step-circle">
                <span class="material-symbols-outlined" v-if="isStepCompleted(step.key)">check</span>
                <span class="material-symbols-outlined" v-else>{{ step.icon }}</span>
              </div>
              <div class="step-info">
                <span class="step-name">{{ step.label }}</span>
                <span class="step-detail" v-if="isStepCurrent(step.key)">{{ t('in-progress', 'Current Stage') }}</span>
                <span class="step-detail" v-else-if="isStepCompleted(step.key)">{{ t('completed', 'Completed') }}</span>
              </div>
            </div>
          </div>

          <!-- Cancelled Order Banner -->
          <div v-else class="cancelled-banner">
            <span class="material-symbols-outlined banner-icon">cancel</span>
            <div class="banner-text">
              <strong>{{ t('order-cancelled-title', 'Order Cancelled') }}</strong>
              <p>{{ t('order-cancelled-msg', 'This order has been cancelled and will not be processed for fulfillment.') }}</p>
            </div>
          </div>
        </div>

        <!-- Information Cards Grid -->
        <div class="detail-info-grid">
          <!-- Card 1: Fulfillment & Delivery Info -->
          <div class="info-card">
            <div class="card-header">
              <span class="material-symbols-outlined card-icon text-indigo">local_shipping</span>
              <h4>{{ t('delivery-details', 'Delivery & Schedule') }}</h4>
            </div>
            <div class="info-rows">
              <div class="info-row">
                <span class="info-label">{{ t('requested-delivery-date', 'Requested Delivery') }}</span>
                <span class="info-value font-semibold text-indigo">
                  {{ formatDate(order.requested_delivery_date) || t('standard-schedule', 'Standard Delivery') }}
                </span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('order-date', 'Date Placed') }}</span>
                <span class="info-value">{{ formatDate(order.order_date) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('order-number', 'Sales Order #') }}</span>
                <span class="info-value font-mono">{{ order.order_number }}</span>
              </div>
              <div class="info-row" v-if="order.notes">
                <span class="info-label">{{ t('delivery-notes', 'Delivery Notes') }}</span>
                <span class="info-value notes-text">{{ order.notes }}</span>
              </div>
            </div>
          </div>

          <!-- Card 2: Account & Customer Info -->
          <div class="info-card">
            <div class="card-header">
              <span class="material-symbols-outlined card-icon text-green">business</span>
              <h4>{{ t('customer-account', 'Wholesale Account') }}</h4>
            </div>
            <div class="info-rows">
              <div class="info-row">
                <span class="info-label">{{ t('account-name', 'Company Name') }}</span>
                <span class="info-value font-semibold">{{ order.customer_name || portal.accountSummary?.company_name || 'Customer' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('customer-id', 'Customer ID') }}</span>
                <span class="info-value font-mono">#{{ order.customer_id }}</span>
              </div>
              <div class="info-row" v-if="portal.accountSummary?.default_price_list_name">
                <span class="info-label">{{ t('contract-price-list', 'Contracted Price List') }}</span>
                <span class="info-value">{{ portal.accountSummary.default_price_list_name }}</span>
              </div>
              <div class="info-row" v-if="portal.accountSummary?.order_cutoff_time">
                <span class="info-label">{{ t('account-cutoff', 'Daily Cutoff Time') }}</span>
                <span class="info-value font-mono">{{ portal.accountSummary.order_cutoff_time.slice(0, 5) }}</span>
              </div>
            </div>
          </div>

          <!-- Card 3: Financial Summary -->
          <div class="info-card">
            <div class="card-header">
              <span class="material-symbols-outlined card-icon text-amber">payments</span>
              <h4>{{ t('financial-summary', 'Payment & Financials') }}</h4>
            </div>
            <div class="info-rows">
              <div class="info-row">
                <span class="info-label">{{ t('subtotal', 'Items Subtotal') }}</span>
                <span class="info-value">${{ (Number(order.subtotal) || 0).toFixed(2) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('tax', 'Wholesale Tax') }}</span>
                <span class="info-value">${{ (Number(order.tax) || 0).toFixed(2) }}</span>
              </div>
              <div class="info-row total-highlight-row">
                <span class="info-label font-bold">{{ t('order-total', 'Grand Total') }}</span>
                <span class="info-value total-amount font-bold">${{ (Number(order.grand_total || order.subtotal) || 0).toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Itemized Order Lines Table Card -->
        <div class="order-lines-card">
          <div class="card-top-title">
            <div class="title-with-count">
              <span class="material-symbols-outlined">inventory_2</span>
              <h3>{{ t('itemized-order-lines', 'Itemized Line Items') }}</h3>
              <span class="lines-count-pill">{{ order.lines?.length || 0 }} {{ order.lines?.length === 1 ? 'item' : 'items' }}</span>
            </div>
            <button class="btn-sm-cart" @click="handleLoadToCart">
              <span class="material-symbols-outlined">add_shopping_cart</span>
              <span>{{ t('reorder-all-items', 'Reorder All Lines') }}</span>
            </button>
          </div>

          <div class="lines-table-wrapper">
            <table class="lines-table">
              <thead>
                <tr>
                  <th class="col-num-header">#</th>
                  <th>{{ t('sku-code', 'SKU / Code') }}</th>
                  <th>{{ t('product-name', 'Product Name') }}</th>
                  <th>{{ t('uom', 'UOM') }}</th>
                  <th class="text-center">{{ t('quantity', 'Quantity') }}</th>
                  <th class="text-right">{{ t('unit-price', 'Contracted Price') }}</th>
                  <th class="text-right">{{ t('line-total', 'Line Total') }}</th>
                  <th class="text-center">{{ t('buy-again', 'Action') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in order.lines" :key="line.id || idx" class="line-row">
                  <td class="col-num font-mono">{{ line.line_number || (idx + 1) }}</td>
                  <td class="cell-sku font-mono">{{ line.product_code || '-' }}</td>
                  <td class="cell-product-name">
                    <div class="product-name-cluster">
                      <span class="name-text">{{ line.product_name }}</span>
                      <span class="contract-badge-mini">
                        <span class="material-symbols-outlined">verified</span> Contracted
                      </span>
                    </div>
                  </td>
                  <td class="cell-uom">
                    <span class="uom-pill">{{ line.uom_name || 'Ea' }}</span>
                  </td>
                  <td class="text-center font-bold cell-qty">
                    {{ line.qty }}
                  </td>
                  <td class="text-right cell-price">
                    ${{ (Number(line.unit_price) || 0).toFixed(2) }}
                  </td>
                  <td class="text-right cell-line-total font-bold">
                    ${{ (Number(line.line_total) || (Number(line.unit_price || 0) * Number(line.qty || 1))).toFixed(2) }}
                  </td>
                  <td class="text-center cell-action">
                    <button
                      class="btn-buy-line"
                      @click="quickAddLineToCart(line)"
                      :title="t('add-item-to-cart', 'Add this item to cart')"
                    >
                      <span class="material-symbols-outlined">add_shopping_cart</span>
                      <span>{{ t('add', 'Add') }}</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 1-Click Replenishment Reorder Modal -->
    <div v-if="showReorderModal && order" class="modal-overlay" @click.self="closeReorderModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-indigo">
              <span class="material-symbols-outlined">repeat</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('reorder-supplies-title', '1-Click Reorder Standard Supplies') }}</h3>
              <p class="modal-subtitle">{{ t('reorder-based-on', 'Reordering standard items from Order') }} #{{ order.order_number }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeReorderModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- Cutoff Time Alert -->
          <div class="cutoff-notice-box" :class="{ 'past-cutoff': portal.isPastCutoff }">
            <span class="material-symbols-outlined notice-icon">
              {{ portal.isPastCutoff ? 'schedule' : 'bolt' }}
            </span>
            <div class="notice-text">
              <strong>{{ portal.isPastCutoff ? 'Post-Cutoff Reorder' : 'Next-Day Delivery Eligible' }}</strong>
              <p>{{ portal.isPastCutoff ? `Cutoff deadline passed. Reorder will be scheduled for ${portal.nextDeliveryDate}.` : `Order now for estimated next-day fulfillment on ${portal.nextDeliveryDate}.` }}</p>
            </div>
          </div>

          <!-- Items to Reorder List -->
          <div class="reorder-items-preview">
            <h4 class="section-title">
              <span class="material-symbols-outlined">inventory_2</span>
              {{ t('reorder-items', 'Items in this Reorder') }} ({{ order.lines?.length || 0 }})
            </h4>
            <div class="reorder-lines-list">
              <div v-for="line in order.lines" :key="line.id" class="reorder-line-item">
                <div class="reorder-line-info">
                  <span class="line-product-name">{{ line.product_name }}</span>
                  <span class="line-sku" v-if="line.product_code">({{ line.product_code }})</span>
                </div>
                <div class="reorder-line-qty">
                  <span class="qty-pill">Qty: {{ line.qty }} {{ line.uom_name || '' }}</span>
                  <span class="line-price">${{ (Number(line.unit_price || 0) * Number(line.qty || 1)).toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Delivery Date & Notes Form -->
          <div class="reorder-form-grid">
            <div class="form-group">
              <label class="form-label">
                <span class="material-symbols-outlined">calendar_today</span>
                {{ t('requested-delivery-date', 'Requested Delivery Date') }}
              </label>
              <input
                type="date"
                v-model="reorderDeliveryDate"
                :min="portal.nextDeliveryDate || todayDate"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label class="form-label">
                <span class="material-symbols-outlined">notes</span>
                {{ t('special-delivery-instructions', 'Special Delivery Instructions') }}
              </label>
              <textarea
                v-model="reorderNotes"
                rows="2"
                :placeholder="t('reorder-notes-placeholder', 'e.g., Deliver to kitchen back entrance before 9 AM...')"
                class="form-input"
              ></textarea>
            </div>
          </div>

          <!-- Estimated Total -->
          <div class="reorder-total-banner">
            <span>{{ t('estimated-reorder-total', 'Estimated Reorder Subtotal') }}:</span>
            <span class="total-val">${{ Number(order.grand_total || order.subtotal || 0).toFixed(2) }}</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeReorderModal">
            {{ t('cancel', 'Cancel') }}
          </button>
          <button class="btn-secondary" @click="handleLoadAndCustomize">
            <span class="material-symbols-outlined">edit_note</span>
            {{ t('load-to-cart-to-edit', 'Load into Cart to Customize') }}
          </button>
          <button class="btn-primary" :disabled="reorderSubmitting" @click="executeInstantReorder">
            <span class="material-symbols-outlined" v-if="!reorderSubmitting">repeat</span>
            <span class="spinner" v-else></span>
            <span>{{ reorderSubmitting ? t('placing-reorder', 'Submitting Reorder...') : t('confirm-1-click-reorder', 'Confirm 1-Click Reorder') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Cancel Order Confirmation Modal -->
    <div v-if="showCancelModal && order" class="modal-overlay" @click.self="closeCancelModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-red">
              <span class="material-symbols-outlined">cancel</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('cancel-order-title', 'Cancel Replenishment Order') }}</h3>
              <p class="modal-subtitle">{{ t('order-num-prefix', 'Order') }} #{{ order.order_number }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeCancelModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <p class="cancel-warning-text">
            {{ t('cancel-order-prompt', 'Are you sure you want to cancel this replenishment order? Any reserved inventory will be immediately released.') }}
          </p>

          <div class="form-group mt-4">
            <label class="form-label">{{ t('cancellation-reason', 'Reason for Cancellation (optional)') }}</label>
            <textarea
              v-model="cancelReason"
              rows="2"
              :placeholder="t('cancel-reason-placeholder', 'e.g., Placed by mistake, changed delivery requirements...')"
              class="form-input"
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeCancelModal">
            {{ t('keep-order', 'Keep Order') }}
          </button>
          <button class="btn-danger" :disabled="cancelSubmitting" @click="executeCancelOrder">
            <span class="material-symbols-outlined" v-if="!cancelSubmitting">delete</span>
            <span class="spinner" v-else></span>
            <span>{{ cancelSubmitting ? t('cancelling', 'Cancelling...') : t('confirm-cancel', 'Yes, Cancel Order') }}</span>
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

// 1-Click Reorder Modal state
const showReorderModal = ref(false)
const reorderDeliveryDate = ref('')
const reorderNotes = ref('')
const reorderSubmitting = ref(false)

// Cancel Modal state
const showCancelModal = ref(false)
const cancelReason = ref('')
const cancelSubmitting = ref(false)

const order = computed(() => portal.currentOrder)

const todayDate = computed(() => {
  return new Date().toISOString().split('T')[0]
})

// Stepper Step Definitions
const fulfillmentSteps = [
  { key: 'Draft', label: 'Order Drafted', icon: 'edit_document' },
  { key: 'Confirmed', label: 'Confirmed', icon: 'check_circle' },
  { key: 'Shipped', label: 'Shipped / In Transit', icon: 'local_shipping' },
  { key: 'Delivered', label: 'Delivered', icon: 'verified' },
]

const stepOrder = ['Draft', 'Pending', 'Confirmed', 'Processing', 'Shipped', 'Delivered']

function getStatusRank(status) {
  if (status === 'Draft') return 0
  if (status === 'Pending') return 1
  if (status === 'Confirmed' || status === 'Processing') return 2
  if (status === 'Shipped') return 3
  if (status === 'Delivered' || status === 'Paid' || status === 'Invoiced') return 4
  return -1
}

function isStepCompleted(stepKey) {
  if (!order.value) return false
  const currentRank = getStatusRank(order.value.status)
  const targetRank = getStatusRank(stepKey)
  return currentRank > targetRank
}

function isStepCurrent(stepKey) {
  if (!order.value) return false
  const currentRank = getStatusRank(order.value.status)
  const targetRank = getStatusRank(stepKey)
  return currentRank === targetRank
}

function isStepPending(stepKey) {
  if (!order.value) return true
  const currentRank = getStatusRank(order.value.status)
  const targetRank = getStatusRank(stepKey)
  return currentRank < targetRank
}

function isCancellable(status) {
  return ['Draft', 'Pending', 'Confirmed'].includes(status)
}

// 1-Click Reorder Handlers
function openReorderModal() {
  if (!order.value) return
  reorderDeliveryDate.value = portal.nextDeliveryDate || todayDate.value
  reorderNotes.value = `Standard replenishment reorder based on #${order.value.order_number}`
  showReorderModal.value = true
}

function closeReorderModal() {
  showReorderModal.value = false
  reorderSubmitting.value = false
}

async function executeInstantReorder() {
  if (!order.value) return
  reorderSubmitting.value = true
  try {
    const result = await portal.reorderPastOrder(order.value.id, {
      requested_delivery_date: reorderDeliveryDate.value || null,
      notes: reorderNotes.value || null,
      status: 'Confirmed',
    })
    if (result) {
      showToast(`Reorder #${result.order_number} submitted successfully!`, 'success', 4000)
      closeReorderModal()
      router.push(`/portal/orders/${result.id}`)
    }
  } catch (err) {
    showToast(err.message || 'Failed to submit 1-click reorder', 'error', 4000)
  } finally {
    reorderSubmitting.value = false
  }
}

function handleLoadToCart() {
  if (!order.value) return
  const count = portal.loadOrderToCart(order.value, false)
  showToast(`Added ${count} items from order #${order.value.order_number} to cart!`, 'success', 3000)
}

function handleLoadAndCustomize() {
  if (!order.value) return
  portal.loadOrderToCart(order.value, false)
  closeReorderModal()
  showToast(`Loaded ${order.value.lines?.length || 0} items to cart for customization`, 'info', 3000)
  router.push('/portal/cart')
}

function quickAddLineToCart(line) {
  if (!line.product_id) return
  portal.addToCart({
    id: line.product_id,
    product_id: line.product_id,
    product_code: line.product_code || '',
    product_name: line.product_name || '',
    uom_name: line.uom_name || '',
    unit_price: Number(line.unit_price || 0),
    contracted_price: Number(line.unit_price || 0),
    base_price: Number(line.unit_price || 0),
    is_contracted: true,
  }, Number(line.qty || 1))
  showToast(`Added ${line.product_name} to cart!`, 'success', 2000)
}

// Cancel Handlers
function openCancelModal() {
  cancelReason.value = ''
  showCancelModal.value = true
}

function closeCancelModal() {
  showCancelModal.value = false
  cancelSubmitting.value = false
}

async function executeCancelOrder() {
  if (!order.value) return
  cancelSubmitting.value = true
  try {
    await portal.cancelOrder(order.value.id, cancelReason.value)
    showToast(`Order #${order.value.order_number} cancelled successfully`, 'info', 3000)
    closeCancelModal()
    portal.fetchOrderDetail(route.params.id)
  } catch (err) {
    showToast(err.message || 'Failed to cancel order', 'error', 4000)
  } finally {
    cancelSubmitting.value = false
  }
}

// Helpers
function getStatusBadgeClass(status) {
  const map = {
    Draft: 'status-draft',
    Pending: 'status-pending',
    Confirmed: 'status-confirmed',
    Processing: 'status-processing',
    Shipped: 'status-shipped',
    Delivered: 'status-delivered',
    Cancelled: 'status-cancelled',
    Paid: 'status-paid',
  }
  return map[status] || 'status-default'
}

function getStatusIcon(status) {
  const map = {
    Draft: 'edit_document',
    Pending: 'hourglass_empty',
    Confirmed: 'check_circle',
    Processing: 'autorenew',
    Shipped: 'local_shipping',
    Delivered: 'verified',
    Cancelled: 'cancel',
    Paid: 'payments',
  }
  return map[status] || 'receipt'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

function formatTime(dateTimeStr) {
  if (!dateTimeStr) return ''
  try {
    const d = new Date(dateTimeStr)
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

onMounted(() => {
  if (route.params.id) {
    portal.fetchOrderDetail(route.params.id)
  }
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
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

/* Header Section */
.detail-header-section {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #818cf8;
  text-decoration: none;
  margin-bottom: 8px;
  transition: color 0.15s ease;
}

.back-link:hover {
  color: #a5b4fc;
}

.back-link .material-symbols-outlined {
  font-size: 16px;
}

.title-status-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  letter-spacing: -0.4px;
  margin: 0;
}

.order-meta-text {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-primary-reorder {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.2s ease;
}

.btn-primary-reorder:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

.btn-secondary-cart {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary-cart:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: #6366f1;
}

.btn-outline-danger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-outline-danger:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}

/* Stepper Card */
.stepper-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 24px;
}

.stepper-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 20px;
}

.stepper-title .material-symbols-outlined {
  color: #818cf8;
  font-size: 18px;
}

.fulfillment-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  padding: 0 10px;
}

.stepper-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
  z-index: 1;
}

.step-connector-line {
  position: absolute;
  top: 18px;
  right: 50%;
  left: -50%;
  height: 3px;
  background: var(--border-default, #2a2a4a);
  z-index: -1;
}

.step-completed .step-connector-line,
.step-current .step-connector-line {
  background: #6366f1;
}

.step-circle {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--bg-surface-low, #0f0f1a);
  border: 2px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #64748b);
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.step-circle .material-symbols-outlined {
  font-size: 18px;
}

.step-completed .step-circle {
  background: #22c55e;
  border-color: #22c55e;
  color: #fff;
}

.step-current .step-circle {
  background: #6366f1;
  border-color: #818cf8;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.25);
}

.step-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.step-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.step-detail {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}

.cancelled-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #f87171;
}

.cancelled-banner .banner-icon {
  font-size: 28px;
}

.banner-text p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}

/* Info Cards Grid */
.detail-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1024px) {
  .detail-info-grid {
    grid-template-columns: 1fr;
  }
}

.info-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 18px 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
}

.card-header h4 {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.card-icon {
  font-size: 20px;
}

.text-indigo { color: #818cf8; }
.text-green { color: #4ade80; }
.text-amber { color: #fbbf24; }

.info-rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.info-label {
  color: var(--text-secondary, #94a3b8);
}

.info-value {
  color: var(--text-primary, #fff);
}

.total-highlight-row {
  border-top: 1px solid var(--border-default, #2a2a4a);
  padding-top: 10px;
  margin-top: 4px;
}

.total-amount {
  font-size: 16px;
  color: #a5b4fc;
}

.notes-text {
  max-width: 200px;
  text-align: right;
  font-style: italic;
  color: var(--text-secondary, #94a3b8);
}

/* Order Lines Card */
.order-lines-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
}

.card-top-title {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-with-count {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-with-count h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.title-with-count .material-symbols-outlined {
  color: #818cf8;
  font-size: 20px;
}

.lines-count-pill {
  background: rgba(255, 255, 255, 0.08);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--text-secondary, #94a3b8);
  font-weight: 600;
}

.btn-sm-cart {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-sm-cart:hover {
  background: #6366f1;
  color: #fff;
}

.lines-table-wrapper {
  overflow-x: auto;
}

.lines-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.lines-table th {
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  padding: 12px 18px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  font-weight: 700;
}

.lines-table td {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 13px;
  color: var(--text-primary, #e2e8f0);
}

.line-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.col-num-header, .col-num {
  width: 40px;
  color: var(--text-muted, #64748b);
}

.cell-sku {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}

.product-name-cluster {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-text {
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.contract-badge-mini {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: rgba(99, 102, 241, 0.12);
  color: #a5b4fc;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.contract-badge-mini .material-symbols-outlined {
  font-size: 12px;
}

.uom-pill {
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.cell-qty {
  font-size: 14px;
  color: var(--text-primary, #fff);
}

.btn-buy-line {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-buy-line:hover {
  background: rgba(99, 102, 241, 0.15);
  border-color: #6366f1;
  color: #a5b4fc;
}

.btn-buy-line .material-symbols-outlined {
  font-size: 14px;
}

/* Status Badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
}

.status-icon {
  font-size: 14px;
}

.status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-confirmed, .status-processing { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); }
.status-shipped { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
.status-delivered, .status-paid { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
.status-cancelled { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.status-draft { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
.status-default { background: rgba(255, 255, 255, 0.08); color: #e2e8f0; }

/* Loading & Error */
.detail-loading-state {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-stepper-card {
  height: 120px;
  border-radius: 12px;
  background: var(--bg-surface, #1a1a2e);
  padding: 20px;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.skeleton-card-box {
  height: 160px;
}

.skeleton-shimmer {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.04) 25%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
  width: 100%;
  height: 100%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.detail-error-card {
  text-align: center;
  padding: 48px 24px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
}

.error-icon {
  font-size: 40px;
  color: #f87171;
  margin-bottom: 12px;
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 600px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
}

.modal-card-sm {
  max-width: 480px;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-badge-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bg-indigo { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.bg-red { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0 0 2px;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
}

.modal-close-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 70vh;
  overflow-y: auto;
}

.cutoff-notice-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.25);
  color: #4ade80;
  font-size: 12px;
}

.cutoff-notice-box.past-cutoff {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.25);
  color: #fbbf24;
}

.cutoff-notice-box .notice-icon {
  font-size: 20px;
  margin-top: 1px;
}

.notice-text p {
  margin: 2px 0 0;
  color: var(--text-secondary, #94a3b8);
}

.reorder-items-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.section-title .material-symbols-outlined {
  font-size: 16px;
  color: #818cf8;
}

.reorder-lines-list {
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 8px;
  max-height: 160px;
  overflow-y: auto;
}

.reorder-line-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 12px;
}

.reorder-line-item:last-child {
  border-bottom: none;
}

.line-product-name {
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.line-sku {
  color: var(--text-muted, #64748b);
  margin-left: 4px;
}

.reorder-line-qty {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qty-pill {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 11px;
}

.line-price {
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.reorder-form-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-label .material-symbols-outlined {
  font-size: 15px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
}

.form-input:focus {
  border-color: #6366f1;
}

.reorder-total-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.total-val {
  font-size: 18px;
  font-weight: 700;
  color: #a5b4fc;
}

.cancel-warning-text {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.5;
  margin: 0;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary, .btn-secondary, .btn-outline, .btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.btn-primary {
  background: #6366f1;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #4f46e5;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary, #fff);
  border: 1px solid var(--border-default, #2a2a4a);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
}

.btn-outline:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

.btn-danger {
  background: #ef4444;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .detail-header-section {
    flex-direction: column;
    align-items: flex-start;
  }
  .fulfillment-stepper {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  .step-connector-line {
    display: none;
  }
  .stepper-step {
    flex-direction: row;
    gap: 12px;
  }
  .step-info {
    align-items: flex-start;
    text-align: left;
  }
  .lines-table th:nth-child(2),
  .lines-table td:nth-child(2) {
    display: none;
  }
}
</style>

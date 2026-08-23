<template>
  <div class="portal-orders-page" :dir="dir">
    <div class="portal-container">
      <!-- Page Header -->
      <div class="page-header-row">
        <div>
          <h1 class="page-title">{{ t('portal-orders-title', 'Order History & Replenishment') }}</h1>
          <p class="page-subtitle">{{ t('portal-orders-subtitle', 'Track fulfillment progress, view past shipments, and 1-click reorder standard supplies.') }}</p>
        </div>
        <div class="header-actions">
          <router-link to="/portal/catalog" class="btn-primary-action">
            <span class="material-symbols-outlined">add_shopping_cart</span>
            <span>{{ t('order-new-supplies', 'New Supply Order') }}</span>
          </router-link>
        </div>
      </div>

      <!-- Quick Metrics Cards -->
      <div class="orders-metrics-grid" v-if="!portal.ordersLoading && portal.orders">
        <div class="metric-card">
          <div class="metric-icon bg-indigo">
            <span class="material-symbols-outlined">receipt_long</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('total-orders', 'Total Orders') }}</span>
            <span class="metric-value">{{ portal.ordersTotal || portal.orders.length }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon bg-amber">
            <span class="material-symbols-outlined">local_shipping</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('in-progress-orders', 'In Fulfillment') }}</span>
            <span class="metric-value">{{ activeOrdersCount }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon bg-green">
            <span class="material-symbols-outlined">verified</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('delivered-orders', 'Delivered Orders') }}</span>
            <span class="metric-value">{{ deliveredOrdersCount }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon bg-purple">
            <span class="material-symbols-outlined">payments</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('total-replenishment-spend', 'Total Spend') }}</span>
            <span class="metric-value">${{ totalSpend.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- Filters, Status Tabs & Search Bar -->
      <div class="orders-filter-card">
        <!-- Status Tabs Bar -->
        <div class="status-tabs-row">
          <button
            class="status-tab-btn"
            :class="{ active: selectedStatus === null }"
            @click="setStatusFilter(null)"
          >
            <span>{{ t('all-orders', 'All Orders') }}</span>
            <span class="tab-count-badge">{{ portal.ordersTotal || portal.orders.length }}</span>
          </button>
          <button
            class="status-tab-btn"
            :class="{ active: selectedStatus === 'active' }"
            @click="setStatusFilter('active')"
          >
            <span class="status-indicator-dot dot-amber"></span>
            <span>{{ t('active-fulfillment', 'Active / Processing') }}</span>
            <span class="tab-count-badge" v-if="activeOrdersCount > 0">{{ activeOrdersCount }}</span>
          </button>
          <button
            class="status-tab-btn"
            :class="{ active: selectedStatus === 'Delivered' }"
            @click="setStatusFilter('Delivered')"
          >
            <span class="status-indicator-dot dot-green"></span>
            <span>{{ t('delivered', 'Delivered') }}</span>
          </button>
          <button
            class="status-tab-btn"
            :class="{ active: selectedStatus === 'Cancelled' }"
            @click="setStatusFilter('Cancelled')"
          >
            <span class="status-indicator-dot dot-gray"></span>
            <span>{{ t('cancelled', 'Cancelled') }}</span>
          </button>
        </div>

        <!-- Search and Refresh Row -->
        <div class="filter-controls-row">
          <div class="search-input-wrap">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              type="text"
              v-model="searchQuery"
              :placeholder="t('search-orders-placeholder', 'Search by order number or item name...')"
              class="filter-search-input"
            />
            <button v-if="searchQuery" class="clear-search-btn" @click="searchQuery = ''" title="Clear">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <div class="controls-actions">
            <button class="btn-refresh" @click="reloadOrders" :title="t('refresh-orders', 'Refresh')">
              <span class="material-symbols-outlined">refresh</span>
              <span>{{ t('refresh', 'Refresh') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portal.ordersLoading" class="orders-loading-state">
        <div v-for="i in 4" :key="i" class="order-skeleton-row">
          <div class="skeleton-shimmer skeleton-circle"></div>
          <div class="skeleton-shimmer skeleton-text-lg"></div>
          <div class="skeleton-shimmer skeleton-text-md"></div>
          <div class="skeleton-shimmer skeleton-btn"></div>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.ordersError" class="orders-error-card">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('orders-error-title', 'Unable to Load Orders') }}</h3>
        <p>{{ portal.ordersError }}</p>
        <button class="btn-primary" @click="reloadOrders">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('retry', 'Retry') }}
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredOrders.length === 0" class="orders-empty-card">
        <div class="empty-icon-wrap">
          <span class="material-symbols-outlined">receipt_long</span>
        </div>
        <h3>{{ t('no-orders-found', 'No Orders Found') }}</h3>
        <p>{{ t('no-orders-desc', 'You have not placed any replenishment orders yet or no orders match your search.') }}</p>
        <router-link to="/portal/catalog" class="btn-primary">
          <span class="material-symbols-outlined">inventory_2</span>
          <span>{{ t('browse-and-order', 'Order Supplies Now') }}</span>
        </router-link>
      </div>

      <!-- Orders List / Table -->
      <div v-else class="orders-table-wrapper">
        <table class="orders-table">
          <thead>
            <tr>
              <th>{{ t('order-number', 'Order #') }}</th>
              <th>{{ t('order-date', 'Date Placed') }}</th>
              <th>{{ t('delivery-date', 'Requested Delivery') }}</th>
              <th>{{ t('items-summary', 'Items & Breakdown') }}</th>
              <th class="text-right">{{ t('order-total', 'Total') }}</th>
              <th class="text-center">{{ t('fulfillment-status', 'Fulfillment Status') }}</th>
              <th class="text-right">{{ t('quick-actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in filteredOrders" :key="order.id" class="order-table-row">
              <!-- Order Number -->
              <td class="cell-order-num">
                <router-link :to="`/portal/orders/${order.id}`" class="order-num-link">
                  <span class="material-symbols-outlined link-icon">receipt</span>
                  <span class="order-num-text">{{ order.order_number }}</span>
                </router-link>
              </td>

              <!-- Order Date -->
              <td class="cell-date">
                <div class="date-stacked">
                  <span class="date-main">{{ formatDate(order.order_date) }}</span>
                  <span class="date-sub" v-if="order.created_at">{{ formatTime(order.created_at) }}</span>
                </div>
              </td>

              <!-- Requested Delivery Date -->
              <td class="cell-delivery-date">
                <div class="delivery-badge" v-if="order.requested_delivery_date">
                  <span class="material-symbols-outlined badge-icon">calendar_today</span>
                  <span>{{ formatDate(order.requested_delivery_date) }}</span>
                </div>
                <span v-else class="text-muted">{{ t('standard-schedule', 'Standard') }}</span>
              </td>

              <!-- Items Summary -->
              <td class="cell-items-preview">
                <div class="items-preview-box">
                  <div class="items-count-tag">
                    {{ order.lines?.length || 0 }} {{ (order.lines?.length === 1) ? 'item' : 'items' }}
                  </div>
                  <div class="items-names-list" v-if="order.lines && order.lines.length > 0">
                    <span class="item-name-chip" v-for="(line, idx) in order.lines.slice(0, 2)" :key="idx">
                      {{ line.product_name }} <span class="chip-qty">×{{ line.qty }}</span>
                    </span>
                    <span v-if="order.lines.length > 2" class="more-items-chip">
                      +{{ order.lines.length - 2 }} more
                    </span>
                  </div>
                </div>
              </td>

              <!-- Total Amount -->
              <td class="cell-total text-right">
                <div class="total-stack">
                  <span class="total-amount">${{ Number(order.grand_total || order.subtotal || 0).toFixed(2) }}</span>
                  <span class="tax-info" v-if="order.tax > 0">incl. ${{ Number(order.tax).toFixed(2) }} tax</span>
                </div>
              </td>

              <!-- Status Badge -->
              <td class="cell-status text-center">
                <span class="status-badge" :class="getStatusBadgeClass(order.status)">
                  <span class="material-symbols-outlined status-icon">
                    {{ getStatusIcon(order.status) }}
                  </span>
                  <span>{{ order.status }}</span>
                </span>
              </td>

              <!-- Actions Cluster -->
              <td class="cell-actions text-right">
                <div class="actions-cluster">
                  <!-- 1-Click Reorder Button -->
                  <button
                    v-if="portal.allowReorders && order.status !== 'Cancelled'"
                    class="btn-action-reorder"
                    @click="openReorderModal(order)"
                    :title="t('1-click-reorder-tooltip', '1-Click Reorder standard supplies from this order')"
                  >
                    <span class="material-symbols-outlined">repeat</span>
                    <span class="action-btn-text">{{ t('reorder', 'Reorder') }}</span>
                  </button>

                  <!-- Load into Cart Button -->
                  <button
                    class="btn-action-cart"
                    @click="handleLoadToCart(order)"
                    :title="t('load-to-cart-tooltip', 'Add these items to your active cart')"
                  >
                    <span class="material-symbols-outlined">add_shopping_cart</span>
                  </button>

                  <!-- View Details Button -->
                  <router-link
                    :to="`/portal/orders/${order.id}`"
                    class="btn-action-view"
                    :title="t('view-details', 'View Order Details')"
                  >
                    <span class="material-symbols-outlined">visibility</span>
                  </router-link>

                  <!-- Cancel Button (if cancellable) -->
                  <button
                    v-if="isCancellable(order.status)"
                    class="btn-action-cancel"
                    @click="openCancelModal(order)"
                    :title="t('cancel-order', 'Cancel Order')"
                  >
                    <span class="material-symbols-outlined">cancel</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Bar -->
      <div class="orders-pagination" v-if="portal.ordersTotal > portal.ordersLimit">
        <div class="pagination-info">
          {{ t('showing-orders', 'Showing') }} {{ ((portal.ordersPage - 1) * portal.ordersLimit) + 1 }} -
          {{ Math.min(portal.ordersPage * portal.ordersLimit, portal.ordersTotal) }} {{ t('of', 'of') }} {{ portal.ordersTotal }}
        </div>
        <div class="pagination-buttons">
          <button
            class="page-nav-btn"
            :disabled="portal.ordersPage <= 1"
            @click="changePage(portal.ordersPage - 1)"
          >
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <span class="current-page-pill">{{ portal.ordersPage }}</span>
          <button
            class="page-nav-btn"
            :disabled="portal.ordersPage * portal.ordersLimit >= portal.ordersTotal"
            @click="changePage(portal.ordersPage + 1)"
          >
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 1-Click Replenishment Reorder Modal -->
    <div v-if="showReorderModal && selectedOrderForReorder" class="modal-overlay" @click.self="closeReorderModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-indigo">
              <span class="material-symbols-outlined">repeat</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('reorder-supplies-title', '1-Click Reorder Standard Supplies') }}</h3>
              <p class="modal-subtitle">{{ t('reorder-based-on', 'Reordering standard items from Order') }} #{{ selectedOrderForReorder.order_number }}</p>
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
              {{ t('reorder-items', 'Items in this Reorder') }} ({{ selectedOrderForReorder.lines?.length || 0 }})
            </h4>
            <div class="reorder-lines-list">
              <div v-for="line in selectedOrderForReorder.lines" :key="line.id" class="reorder-line-item">
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
            <span class="total-val">${{ Number(selectedOrderForReorder.grand_total || selectedOrderForReorder.subtotal || 0).toFixed(2) }}</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeReorderModal">
            {{ t('cancel', 'Cancel') }}
          </button>
          <button class="btn-secondary" @click="handleLoadAndCustomize(selectedOrderForReorder)">
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
    <div v-if="showCancelModal && selectedOrderForCancel" class="modal-overlay" @click.self="closeCancelModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-red">
              <span class="material-symbols-outlined">cancel</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('cancel-order-title', 'Cancel Replenishment Order') }}</h3>
              <p class="modal-subtitle">{{ t('order-num-prefix', 'Order') }} #{{ selectedOrderForCancel.order_number }}</p>
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
import { useRouter } from 'vue-router'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const router = useRouter()
const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

// Filters state
const selectedStatus = ref(null)
const searchQuery = ref('')

// 1-Click Reorder Modal state
const showReorderModal = ref(false)
const selectedOrderForReorder = ref(null)
const reorderDeliveryDate = ref('')
const reorderNotes = ref('')
const reorderSubmitting = ref(false)

// Cancel Modal state
const showCancelModal = ref(false)
const selectedOrderForCancel = ref(null)
const cancelReason = ref('')
const cancelSubmitting = ref(false)

const todayDate = computed(() => {
  return new Date().toISOString().split('T')[0]
})

// Metrics Computations
const activeOrdersCount = computed(() => {
  if (!portal.orders) return 0
  return portal.orders.filter(o => ['Draft', 'Pending', 'Confirmed', 'Processing', 'Shipped'].includes(o.status)).length
})

const deliveredOrdersCount = computed(() => {
  if (!portal.orders) return 0
  return portal.orders.filter(o => o.status === 'Delivered').length
})

const totalSpend = computed(() => {
  if (!portal.orders) return 0
  return portal.orders
    .filter(o => o.status !== 'Cancelled')
    .reduce((sum, o) => sum + Number(o.grand_total || o.subtotal || 0), 0)
})

// Filtered Orders List
const filteredOrders = computed(() => {
  let list = portal.orders || []

  // Status Filter
  if (selectedStatus.value === 'active') {
    list = list.filter(o => ['Draft', 'Pending', 'Confirmed', 'Processing', 'Shipped'].includes(o.status))
  } else if (selectedStatus.value) {
    list = list.filter(o => o.status?.toLowerCase() === selectedStatus.value.toLowerCase())
  }

  // Text Search
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(o => {
      const numMatch = o.order_number?.toLowerCase().includes(q)
      const dateMatch = o.order_date?.toLowerCase().includes(q)
      const lineMatch = o.lines?.some(l => l.product_name?.toLowerCase().includes(q) || l.product_code?.toLowerCase().includes(q))
      return numMatch || dateMatch || lineMatch
    })
  }

  return list
})

function setStatusFilter(status) {
  selectedStatus.value = status
  if (status === 'active') {
    portal.fetchOrders({ page: 1 })
  } else if (status) {
    portal.fetchOrders({ status, page: 1 })
  } else {
    portal.fetchOrders({ page: 1 })
  }
}

function reloadOrders() {
  portal.fetchOrders({
    status: selectedStatus.value === 'active' ? null : selectedStatus.value,
    page: portal.ordersPage,
  })
}

function changePage(page) {
  portal.fetchOrders({
    page,
    status: selectedStatus.value === 'active' ? null : selectedStatus.value,
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 1-Click Reorder Handlers
function openReorderModal(order) {
  selectedOrderForReorder.value = order
  reorderDeliveryDate.value = portal.nextDeliveryDate || todayDate.value
  reorderNotes.value = `Standard replenishment reorder based on #${order.order_number}`
  showReorderModal.value = true
}

function closeReorderModal() {
  showReorderModal.value = false
  selectedOrderForReorder.value = null
  reorderSubmitting.value = false
}

async function executeInstantReorder() {
  if (!selectedOrderForReorder.value) return
  reorderSubmitting.value = true
  try {
    const result = await portal.reorderPastOrder(selectedOrderForReorder.value.id, {
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

function handleLoadToCart(order) {
  const count = portal.loadOrderToCart(order, false)
  showToast(`Added ${count} items from order #${order.order_number} to cart!`, 'success', 3000)
}

function handleLoadAndCustomize(order) {
  portal.loadOrderToCart(order, false)
  closeReorderModal()
  showToast(`Loaded ${order.lines?.length || 0} items to cart for customization`, 'info', 3000)
  router.push('/portal/cart')
}

// Cancel Handlers
function isCancellable(status) {
  return ['Draft', 'Pending', 'Confirmed'].includes(status)
}

function openCancelModal(order) {
  selectedOrderForCancel.value = order
  cancelReason.value = ''
  showCancelModal.value = true
}

function closeCancelModal() {
  showCancelModal.value = false
  selectedOrderForCancel.value = null
  cancelSubmitting.value = false
}

async function executeCancelOrder() {
  if (!selectedOrderForCancel.value) return
  cancelSubmitting.value = true
  try {
    await portal.cancelOrder(selectedOrderForCancel.value.id, cancelReason.value)
    showToast(`Order #${selectedOrderForCancel.value.order_number} cancelled successfully`, 'info', 3000)
    closeCancelModal()
    reloadOrders()
  } catch (err) {
    showToast(err.message || 'Failed to cancel order', 'error', 4000)
  } finally {
    cancelSubmitting.value = false
  }
}

// Status Badges & Icons
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
  portal.fetchOrders()
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
})
</script>

<style scoped>
.portal-orders-page {
  width: 100%;
}

.portal-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Page Header */
.page-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  letter-spacing: -0.4px;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
}

.btn-primary-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.2s ease;
}

.btn-primary-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

/* Metrics Grid */
.orders-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1024px) {
  .orders-metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .orders-metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon .material-symbols-outlined {
  font-size: 22px;
}

.bg-indigo { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.bg-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.bg-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.bg-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.bg-red { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  margin-bottom: 2px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

/* Filter Card */
.orders-filter-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-tabs-row {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  padding-bottom: 14px;
  overflow-x: auto;
}

.status-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary, #94a3b8);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.status-tab-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

.status-tab-btn.active {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-color: rgba(99, 102, 241, 0.3);
}

.status-indicator-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot-amber { background: #fbbf24; }
.dot-green { background: #4ade80; }
.dot-gray { background: #94a3b8; }

.tab-count-badge {
  background: rgba(255, 255, 255, 0.08);
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
}

.filter-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.search-input-wrap {
  flex: 1;
  max-width: 480px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 18px;
  color: var(--text-muted, #64748b);
  pointer-events: none;
}

.filter-search-input {
  width: 100%;
  padding: 8px 36px 8px 36px;
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease;
}

.filter-search-input:focus {
  border-color: #6366f1;
}

.clear-search-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 8px;
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-refresh:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
  border-color: #6366f1;
}

/* Orders Table */
.orders-table-wrapper {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow: hidden;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.orders-table th {
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  padding: 14px 18px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  font-weight: 700;
}

.orders-table td {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 13px;
  color: var(--text-primary, #e2e8f0);
}

.order-table-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.cell-order-num {
  font-weight: 600;
}

.order-num-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #818cf8;
  text-decoration: none;
  font-weight: 700;
  font-family: monospace;
}

.order-num-link:hover {
  text-decoration: underline;
  color: #a5b4fc;
}

.link-icon {
  font-size: 16px;
}

.date-stacked {
  display: flex;
  flex-direction: column;
}

.date-main {
  font-weight: 600;
}

.date-sub {
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.delivery-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.1);
  color: #a5b4fc;
  font-size: 12px;
  font-weight: 600;
}

.delivery-badge .badge-icon {
  font-size: 14px;
}

.items-preview-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.items-count-tag {
  font-weight: 600;
  font-size: 12px;
  color: var(--text-primary, #fff);
}

.items-names-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.item-name-chip {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}

.chip-qty {
  font-weight: 700;
  color: #a5b4fc;
}

.more-items-chip {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  align-self: center;
}

.total-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.total-amount {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.tax-info {
  font-size: 10px;
  color: var(--text-muted, #64748b);
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

/* Actions Cluster */
.actions-cluster {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-action-reorder {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-reorder:hover {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.btn-action-reorder .material-symbols-outlined {
  font-size: 16px;
}

.btn-action-cart, .btn-action-view, .btn-action-cancel {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-cart:hover, .btn-action-view:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary, #fff);
  border-color: #6366f1;
}

.btn-action-cancel:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.4);
}

.btn-action-cart .material-symbols-outlined,
.btn-action-view .material-symbols-outlined,
.btn-action-cancel .material-symbols-outlined {
  font-size: 16px;
}

/* Pagination */
.orders-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
}

.pagination-info {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-nav-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.current-page-pill {
  font-size: 13px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  background: #6366f1;
  color: #fff;
}

/* Loading & Empty States */
.orders-loading-state {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-skeleton-row {
  height: 72px;
  border-radius: 12px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.skeleton-shimmer {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.04) 25%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-circle { width: 36px; height: 36px; border-radius: 50%; }
.skeleton-text-lg { flex: 2; height: 16px; }
.skeleton-text-md { flex: 1; height: 16px; }
.skeleton-btn { width: 90px; height: 32px; border-radius: 8px; }

.orders-empty-card, .orders-error-card {
  text-align: center;
  padding: 48px 24px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
}

.empty-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.1);
  color: #a5b4fc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.empty-icon-wrap .material-symbols-outlined {
  font-size: 32px;
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
  .page-header-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .filter-controls-row {
    flex-direction: column;
    align-items: stretch;
  }
  .search-input-wrap {
    max-width: 100%;
  }
  .action-btn-text {
    display: none;
  }
  .orders-table th:nth-child(3),
  .orders-table td:nth-child(3) {
    display: none;
  }
}
</style>

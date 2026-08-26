<template>
  <div class="portal-orders-page" :dir="dir">
    <div class="portal-container">
      <!-- Page Header -->
      <div class="orders-header-row">
        <div>
          <h1 class="page-title">{{ t('portal-orders-title', 'Order History & Replenishment') }}</h1>
          <p class="page-subtitle">{{ t('portal-orders-subtitle', 'Track past wholesale orders, fulfillment status, and 1-click reorder standard supplies.') }}</p>
        </div>
        <div class="header-actions">
          <router-link to="/portal/catalog" class="btn-primary-action">
            <span class="material-symbols-outlined">add_shopping_cart</span>
            <span>{{ t('order-supplies', 'Order Supplies') }}</span>
          </router-link>
        </div>
      </div>

      <!-- Quick Metrics Summary Cards -->
      <div class="orders-metrics-grid" v-if="portal.orders && portal.orders.length > 0">
        <div class="metric-card">
          <div class="metric-icon-wrap icon-blue">
            <span class="material-symbols-outlined">receipt_long</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('total-orders', 'Total Orders') }}</span>
            <span class="metric-value">{{ portal.ordersTotal || portal.orders.length }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap icon-amber">
            <span class="material-symbols-outlined">local_shipping</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('active-in-transit', 'In Progress / Shipped') }}</span>
            <span class="metric-value">{{ activeOrdersCount }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap icon-green">
            <span class="material-symbols-outlined">check_circle</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('delivered-orders', 'Delivered Orders') }}</span>
            <span class="metric-value">{{ deliveredOrdersCount }}</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrap icon-purple">
            <span class="material-symbols-outlined">payments</span>
          </div>
          <div class="metric-info">
            <span class="metric-label">{{ t('total-order-value', 'Total Spend') }}</span>
            <span class="metric-value">${{ totalOrdersSpend.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- Search and Status Filter Navigation -->
      <div class="orders-controls-card">
        <div class="controls-top-row">
          <!-- Search Box -->
          <div class="search-field-wrap">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              v-model="searchQuery"
              @input="handleSearchInput"
              type="text"
              class="search-input"
              :placeholder="t('search-orders-placeholder', 'Search by order # or notes...')"
            />
            <button v-if="searchQuery" class="clear-search-btn" @click="clearSearch" title="Clear search">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Quick Refresh Button -->
          <div class="controls-right-actions">
            <button class="btn-refresh" @click="loadOrders" :disabled="portal.ordersLoading" :title="t('refresh', 'Refresh')">
              <span class="material-symbols-outlined" :class="{ 'spin-icon': portal.ordersLoading }">refresh</span>
              <span>{{ t('refresh', 'Refresh') }}</span>
            </button>
          </div>
        </div>

        <!-- Status Filter Pills Bar -->
        <div class="status-pills-bar">
          <button
            v-for="tab in statusTabs"
            :key="tab.id"
            class="status-pill"
            :class="{ active: currentStatusFilter === tab.id }"
            @click="setStatusFilter(tab.id)"
          >
            <span class="pill-name">{{ tab.label }}</span>
            <span class="pill-count" v-if="tab.count !== undefined">{{ tab.count }}</span>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portal.ordersLoading && !portal.orders.length" class="orders-loading-state">
        <div class="skeleton-row" v-for="i in 5" :key="i">
          <div class="skeleton-shimmer skeleton-line w-20"></div>
          <div class="skeleton-shimmer skeleton-line w-40"></div>
          <div class="skeleton-shimmer skeleton-line w-20"></div>
          <div class="skeleton-shimmer skeleton-line w-20"></div>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.ordersError" class="orders-error-card">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('orders-error-title', 'Unable to Load Orders') }}</h3>
        <p>{{ portal.ordersError }}</p>
        <button class="btn-primary" @click="loadOrders">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('retry', 'Retry') }}
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="!filteredOrders || filteredOrders.length === 0" class="orders-empty-card">
        <div class="empty-icon-wrap">
          <span class="material-symbols-outlined">receipt_long</span>
        </div>
        <h3>{{ t('no-orders-found', 'No Orders Found') }}</h3>
        <p v-if="searchQuery || currentStatusFilter">
          {{ t('no-matching-orders-desc', 'No orders matched your active search or status filter.') }}
        </p>
        <p v-else>
          {{ t('no-orders-yet-desc', 'You have not placed any replenishment orders yet. Explore your contracted catalog to order supplies.') }}
        </p>
        <div class="empty-actions">
          <button v-if="searchQuery || currentStatusFilter" class="btn-outline" @click="resetFilters">
            <span class="material-symbols-outlined">restart_alt</span>
            {{ t('reset-filters', 'Reset Filters') }}
          </button>
          <router-link to="/portal/catalog" class="btn-primary">
            <span class="material-symbols-outlined">inventory_2</span>
            {{ t('browse-catalog', 'Browse Order Supplies') }}
          </router-link>
        </div>
      </div>

      <!-- Orders Data Table -->
      <div v-else class="orders-table-card">
        <div class="table-wrap">
          <table class="orders-table">
            <thead>
              <tr>
                <th>{{ t('order-number', 'Order #') }}</th>
                <th>{{ t('order-date', 'Order Date') }}</th>
                <th>{{ t('delivery-date', 'Delivery Date') }}</th>
                <th>{{ t('items', 'Items') }}</th>
                <th class="col-status text-center">{{ t('fulfillment-status', 'Fulfillment Status') }}</th>
                <th class="col-num text-right">{{ t('total-amount', 'Grand Total') }}</th>
                <th class="col-actions text-center">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in filteredOrders" :key="order.id" class="order-row">
                <!-- Order Number -->
                <td class="cell-order-number">
                  <router-link :to="`/portal/orders/${order.id}`" class="order-link">
                    <span class="material-symbols-outlined order-link-icon">receipt</span>
                    <span class="order-link-text">{{ order.order_number }}</span>
                  </router-link>
                </td>

                <!-- Order Date -->
                <td class="cell-date">
                  <span class="date-text">{{ formatDate(order.order_date) }}</span>
                </td>

                <!-- Requested Delivery Date -->
                <td class="cell-date">
                  <span class="delivery-date-text" v-if="order.requested_delivery_date">
                    <span class="material-symbols-outlined mini-icon">local_shipping</span>
                    <span>{{ formatDate(order.requested_delivery_date) }}</span>
                  </span>
                  <span v-else class="text-muted">-</span>
                </td>

                <!-- Items Preview -->
                <td class="cell-items">
                  <div class="items-preview-stack">
                    <span class="items-count-badge">
                      {{ (order.lines && order.lines.length) ? `${order.lines.length} ${order.lines.length === 1 ? 'item' : 'items'}` : t('supplies', 'Supplies') }}
                    </span>
                    <span class="lines-snippet" v-if="order.lines && order.lines.length">
                      {{ order.lines.map(l => l.product_name).slice(0, 2).join(', ') }}{{ order.lines.length > 2 ? '...' : '' }}
                    </span>
                  </div>
                </td>

                <!-- Fulfillment Status Badge -->
                <td class="cell-status text-center">
                  <span class="status-badge" :class="getStatusBadgeClass(order.status)">
                    <span class="status-dot"></span>
                    <span>{{ order.status }}</span>
                  </span>
                </td>

                <!-- Grand Total -->
                <td class="cell-amount text-right">
                  <span class="grand-total-val">${{ (order.grand_total || order.subtotal || 0).toFixed(2) }}</span>
                </td>

                <!-- Actions Cluster -->
                <td class="cell-actions text-center">
                  <div class="action-buttons-cluster">
                    <!-- 1-Click Reorder Button -->
                    <button
                      class="btn-action btn-reorder"
                      @click="openReorderModal(order)"
                      :title="t('reorder-supplies-btn', '1-Click Reorder Standard Supplies')"
                    >
                      <span class="material-symbols-outlined">repeat</span>
                      <span class="btn-text">{{ t('reorder', 'Reorder') }}</span>
                    </button>

                    <!-- View Details Link -->
                    <router-link
                      :to="`/portal/orders/${order.id}`"
                      class="btn-action btn-view"
                      :title="t('view-details', 'View Order Details')"
                    >
                      <span class="material-symbols-outlined">visibility</span>
                    </router-link>

                    <!-- Cancel Order Button (if allowed) -->
                    <button
                      v-if="canCancelOrder(order)"
                      class="btn-action btn-cancel"
                      @click="openCancelModal(order)"
                      :title="t('cancel-order', 'Cancel Order')"
                    >
                      <span class="material-symbols-outlined">close</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Controls -->
        <div class="pagination-footer" v-if="portal.ordersTotal > portal.ordersLimit">
          <span class="pagination-info">
            {{ t('showing', 'Showing') }} {{ ((portal.ordersPage - 1) * portal.ordersLimit) + 1 }} -
            {{ Math.min(portal.ordersPage * portal.ordersLimit, portal.ordersTotal) }} {{ t('of', 'of') }} {{ portal.ordersTotal }}
          </span>
          <div class="pagination-buttons">
            <button
              class="page-nav-btn"
              :disabled="portal.ordersPage <= 1"
              @click="changePage(portal.ordersPage - 1)"
            >
              <span class="material-symbols-outlined">chevron_left</span>
            </button>
            <span class="current-page-num">{{ portal.ordersPage }}</span>
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
    </div>

    <!-- 1-Click Reorder Modal -->
    <div v-if="selectedReorderOrder" class="modal-overlay" @click.self="closeReorderModal">
      <div class="reorder-modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-icon-badge">
              <span class="material-symbols-outlined">repeat</span>
            </div>
            <div>
              <h3>{{ t('reorder-title', 'Reorder Supplies') }}</h3>
              <p class="modal-subtitle">
                {{ t('reorder-subtitle', 'Based on past order') }} <strong>#{{ selectedReorderOrder.order_number }}</strong>
              </p>
            </div>
          </div>
          <button class="btn-close-modal" @click="closeReorderModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- Items Summary List -->
          <div class="reorder-items-summary" v-if="selectedReorderOrder.lines && selectedReorderOrder.lines.length">
            <div class="summary-section-label">{{ t('items-included', 'Items in this Reorder') }}:</div>
            <div class="reorder-lines-list">
              <div v-for="line in selectedReorderOrder.lines" :key="line.id || line.product_id" class="reorder-line-item">
                <div class="line-name-col">
                  <span class="line-product-name">{{ line.product_name }}</span>
                  <span class="line-sku" v-if="line.product_code">({{ line.product_code }})</span>
                </div>
                <div class="line-qty-price-col">
                  <span class="line-qty">{{ line.qty }} {{ line.uom_name || 'ea' }}</span>
                  <span class="line-price">${{ (line.unit_price || 0).toFixed(2) }}</span>
                  <span class="line-total">${{ (line.line_total || ((line.unit_price || 0) * line.qty)).toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Reorder Action Mode Choice -->
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
          <button class="btn-outline" @click="closeReorderModal" :disabled="isReordering">
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
    <div v-if="selectedCancelOrder" class="modal-overlay" @click.self="closeCancelModal">
      <div class="cancel-modal-card">
        <div class="cancel-header">
          <div class="warning-icon-badge">
            <span class="material-symbols-outlined">warning</span>
          </div>
          <h3>{{ t('cancel-order-title', 'Cancel Replenishment Order') }}</h3>
          <p class="modal-subtitle">
            {{ t('cancel-order-prompt', 'Are you sure you want to cancel order') }} <strong>#{{ selectedCancelOrder.order_number }}</strong>?
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
          <button class="btn-outline" @click="closeCancelModal" :disabled="isCancelling">
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
import { useRouter } from 'vue-router'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const router = useRouter()
const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

const searchQuery = ref('')
const currentStatusFilter = ref(null)
const selectedReorderOrder = ref(null)
const reorderMode = ref('direct') // 'direct' or 'cart'
const reorderDeliveryDate = ref('')
const reorderNotes = ref('')
const isReordering = ref(false)

const selectedCancelOrder = ref(null)
const cancelReason = ref('')
const isCancelling = ref(false)

// Status Filter Tabs
const statusTabs = computed(() => {
  const allOrders = portal.orders || []
  return [
    { id: null, label: t('all-orders', 'All Orders'), count: allOrders.length },
    { id: 'Confirmed', label: t('confirmed', 'Confirmed'), count: allOrders.filter(o => o.status === 'Confirmed').length },
    { id: 'Shipped', label: t('shipped', 'Shipped'), count: allOrders.filter(o => o.status === 'Shipped').length },
    { id: 'Delivered', label: t('delivered', 'Delivered'), count: allOrders.filter(o => o.status === 'Delivered').length },
    { id: 'Pending', label: t('pending', 'Pending'), count: allOrders.filter(o => o.status === 'Pending').length },
    { id: 'Draft', label: t('drafts', 'Drafts'), count: allOrders.filter(o => o.status === 'Draft').length },
    { id: 'Cancelled', label: t('cancelled', 'Cancelled'), count: allOrders.filter(o => o.status === 'Cancelled').length },
  ]
})

// Metrics calculations
const activeOrdersCount = computed(() => {
  return (portal.orders || []).filter(o => ['Pending', 'Confirmed', 'Processing', 'Shipped'].includes(o.status)).length
})

const deliveredOrdersCount = computed(() => {
  return (portal.orders || []).filter(o => o.status === 'Delivered').length
})

const totalOrdersSpend = computed(() => {
  return (portal.orders || [])
    .filter(o => o.status !== 'Cancelled')
    .reduce((sum, o) => sum + (Number(o.grand_total ?? o.subtotal) || 0), 0)
})

// Filtered orders computed based on search query and status pill
const filteredOrders = computed(() => {
  let list = portal.orders || []

  if (currentStatusFilter.value) {
    list = list.filter(o => o.status === currentStatusFilter.value)
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(o => {
      const numMatch = (o.order_number || '').toLowerCase().includes(q)
      const notesMatch = (o.notes || '').toLowerCase().includes(q)
      const linesMatch = (o.lines || []).some(l => (l.product_name || '').toLowerCase().includes(q) || (l.product_code || '').toLowerCase().includes(q))
      return numMatch || notesMatch || linesMatch
    })
  }

  return list
})

const minDeliveryDate = computed(() => {
  if (portal.cutoffStatus?.next_delivery_date) {
    return portal.cutoffStatus.next_delivery_date
  }
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  return tomorrow.toISOString().split('T')[0]
})

// Helpers
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

function canCancelOrder(order) {
  return order && ['Pending', 'Confirmed', 'Draft'].includes(order.status)
}

function setStatusFilter(statusId) {
  currentStatusFilter.value = statusId
  portal.fetchOrders({ status: statusId, page: 1 })
}

function handleSearchInput() {
  // Local filter is reactive
}

function clearSearch() {
  searchQuery.value = ''
}

function resetFilters() {
  searchQuery.value = ''
  currentStatusFilter.value = null
  portal.fetchOrders({ page: 1, status: null })
}

function changePage(page) {
  portal.fetchOrders({ page, status: currentStatusFilter.value })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function loadOrders() {
  await portal.fetchOrders({ status: currentStatusFilter.value })
}

// 1-Click Reorder modal handling
function openReorderModal(order) {
  selectedReorderOrder.value = order
  reorderMode.value = 'direct'
  reorderDeliveryDate.value = portal.cutoffStatus?.next_delivery_date || ''
  reorderNotes.value = order.notes || ''
}

function closeReorderModal() {
  selectedReorderOrder.value = null
  isReordering.value = false
}

async function executeReorder() {
  if (!selectedReorderOrder.value) return

  if (reorderMode.value === 'cart') {
    const count = portal.loadOrderToCart(selectedReorderOrder.value, false)
    showToast(t('reorder-loaded-toast', `Loaded ${count} items into your replenishment cart!`), 'success', 3000)
    closeReorderModal()
    router.push('/portal/cart')
    return
  }

  isReordering.value = true
  try {
    const payload = {
      requested_delivery_date: reorderDeliveryDate.value || null,
      notes: reorderNotes.value || null,
      status: 'Confirmed',
    }
    const newOrder = await portal.reorderPastOrder(selectedReorderOrder.value.id, payload)
    if (newOrder) {
      showToast(t('reorder-success-toast', `Reorder placed successfully! Order #${newOrder.order_number}`), 'success', 4000)
      closeReorderModal()
      await loadOrders()
    }
  } catch (err) {
    showToast(err.message || t('reorder-failed-toast', 'Failed to submit reorder'), 'error', 4000)
  } finally {
    isReordering.value = false
  }
}

// Cancel order handling
function openCancelModal(order) {
  selectedCancelOrder.value = order
  cancelReason.value = ''
}

function closeCancelModal() {
  selectedCancelOrder.value = null
  isCancelling.value = false
}

async function executeCancel() {
  if (!selectedCancelOrder.value) return
  isCancelling.value = true
  try {
    await portal.cancelOrder(selectedCancelOrder.value.id, cancelReason.value)
    showToast(t('order-cancelled-toast', `Order #${selectedCancelOrder.value.order_number} cancelled`), 'info', 3000)
    closeCancelModal()
    await loadOrders()
  } catch (err) {
    showToast(err.message || t('cancel-failed-toast', 'Failed to cancel order'), 'error', 4000)
  } finally {
    isCancelling.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    portal.fetchOrders(),
    portal.fetchCutoffStatus(),
    portal.fetchAccountSummary(),
  ])
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

.orders-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
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
  border: 1px solid #6366f1;
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: all 0.2s ease;
}

.btn-primary-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.5);
}

.btn-primary-action .material-symbols-outlined {
  font-size: 20px;
}

/* Metrics Summary Grid */
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
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px 20px;
}

.metric-icon-wrap {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon-wrap .material-symbols-outlined {
  font-size: 24px;
}

.icon-blue {
  background: rgba(99, 102, 241, 0.12);
  color: #818cf8;
}

.icon-amber {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
}

.icon-green {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
}

.icon-purple {
  background: rgba(168, 85, 247, 0.12);
  color: #c084fc;
}

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted, #94a3b8);
  letter-spacing: 0.5px;
  font-weight: 600;
  margin-bottom: 2px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  font-family: monospace;
}

/* Controls & Filter Bar */
.orders-controls-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.controls-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.search-field-wrap {
  position: relative;
  flex: 1;
  max-width: 440px;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted, #94a3b8);
  font-size: 20px;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 9px 36px 9px 40px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: #6366f1;
}

.clear-search-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}

.clear-search-btn:hover {
  color: #fff;
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-refresh:hover {
  background: var(--bg-surface-hover, #2a2a4a);
  color: #fff;
  border-color: #6366f1;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

/* Status Filter Pills Bar */
.status-pills-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.status-pill:hover {
  border-color: #6366f1;
  color: #fff;
}

.status-pill.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: #6366f1;
  color: #a5b4fc;
}

.pill-count {
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
}

.status-pill.active .pill-count {
  background: rgba(99, 102, 241, 0.3);
  color: #fff;
}

/* Loading, Error, Empty states */
.orders-loading-state {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 24px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
}

.skeleton-row:last-child {
  border-bottom: none;
}

.skeleton-shimmer {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.03) 25%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.03) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-line {
  height: 16px;
}

.w-20 { width: 20%; }
.w-40 { width: 40%; }

.orders-error-card, .orders-empty-card {
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

.empty-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--bg-surface-low, #222240);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #a5b4fc;
  margin-bottom: 16px;
}

.empty-icon-wrap .material-symbols-outlined {
  font-size: 32px;
}

.orders-empty-card h3, .orders-error-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 8px;
}

.orders-empty-card p, .orders-error-card p {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  max-width: 480px;
  margin: 0 auto 20px;
  line-height: 1.5;
}

.empty-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

/* Orders Data Table */
.orders-table-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow: hidden;
}

.table-wrap {
  overflow-x: auto;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.orders-table th {
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

.orders-table td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  vertical-align: middle;
}

.order-row:hover {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.02));
}

.cell-order-number {
  font-weight: 700;
}

.order-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #a5b4fc;
  text-decoration: none;
  font-family: monospace;
  font-size: 13px;
  transition: color 0.15s;
}

.order-link:hover {
  color: #fff;
  text-decoration: underline;
}

.order-link-icon {
  font-size: 18px;
}

.cell-date {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
}

.delivery-date-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-primary, #fff);
}

.mini-icon {
  font-size: 15px;
  color: #818cf8;
}

.cell-items {
  max-width: 240px;
}

.items-preview-stack {
  display: flex;
  flex-direction: column;
}

.items-count-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.lines-snippet {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.col-status {
  width: 140px;
}

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

.col-num {
  font-family: monospace;
  font-weight: 700;
  white-space: nowrap;
}

.grand-total-val {
  font-size: 14px;
  color: var(--text-primary, #fff);
}

.col-actions {
  width: 170px;
}

.action-buttons-cluster {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border-default, #2a2a4a);
  background: var(--bg-body, #0f0f1a);
  color: var(--text-secondary, #94a3b8);
  text-decoration: none;
  transition: all 0.15s;
}

.btn-action:hover {
  background: var(--bg-surface-hover, #2a2a4a);
  color: #fff;
  border-color: #6366f1;
}

.btn-action .material-symbols-outlined {
  font-size: 16px;
}

.btn-reorder {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.35);
  color: #a5b4fc;
}

.btn-reorder:hover {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

.btn-cancel:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.4);
  color: #f87171;
}

/* Pagination */
.pagination-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(0, 0, 0, 0.15);
  border-top: 1px solid var(--border-default, #2a2a4a);
}

.pagination-info {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-nav-btn {
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 6px;
  color: var(--text-primary, #fff);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.current-page-num {
  font-size: 12px;
  font-weight: 700;
  padding: 0 8px;
  color: #a5b4fc;
}

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
  width: 620px;
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

.reorder-items-summary {
  margin-bottom: 20px;
}

.summary-section-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #94a3b8);
  margin-bottom: 8px;
}

.reorder-lines-list {
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 10px;
  max-height: 160px;
  overflow-y: auto;
}

.reorder-line-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
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
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  margin-left: 4px;
}

.line-qty-price-col {
  display: flex;
  align-items: center;
  gap: 12px;
}

.line-qty {
  color: var(--text-secondary, #94a3b8);
}

.line-price {
  color: var(--text-muted, #94a3b8);
}

.line-total {
  font-family: monospace;
  font-weight: 700;
  color: #a5b4fc;
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
.text-muted { color: var(--text-muted, #94a3b8); }

[dir="rtl"] .orders-table th { text-align: right; }
[dir="rtl"] .orders-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .search-icon { left: auto; right: 12px; }
[dir="rtl"] .search-input { padding: 9px 40px 9px 36px; }
[dir="rtl"] .clear-search-btn { right: auto; left: 10px; }
</style>

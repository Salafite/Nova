<template>
  <div class="field-sales-mobile-shell">
    <!-- Top Mobile Navigation & Status Bar -->
    <header class="mobile-top-bar">
      <div class="top-bar-left">
        <div class="app-branding">
          <span class="material-symbols-outlined branding-icon">local_shipping</span>
          <span class="branding-title">Field Sales</span>
        </div>

        <!-- Warehouse Selector -->
        <div class="warehouse-picker-box">
          <span class="material-symbols-outlined picker-icon">warehouse</span>
          <select
            :value="store.selectedWarehouseId"
            class="warehouse-select"
            aria-label="Select Warehouse"
            @change="handleWarehouseChange(Number($event.target.value))"
          >
            <option v-for="wh in store.warehouses" :key="wh.id" :value="wh.id">
              {{ wh.name || `Warehouse ${wh.id}` }}
            </option>
          </select>
        </div>
      </div>

      <div class="top-bar-right">
        <!-- Live Connection & Sync Status Badge -->
        <SyncStatusBadge />

        <!-- Refresh Catalog Button -->
        <button
          class="btn-refresh"
          :disabled="store.catalogLoading || !store.isOnline"
          @click="handleRefreshCatalog"
          title="Download latest catalog updates"
        >
          <span class="material-symbols-outlined" :class="{ 'spin-icon': store.catalogLoading }">
            refresh
          </span>
        </button>

        <!-- Cart Quick Trigger Button (Header) -->
        <button
          class="btn-cart-header"
          @click="isCartDrawerOpen = true"
          aria-label="View shopping cart"
        >
          <span class="material-symbols-outlined">shopping_cart</span>
          <span v-if="store.cartItemCount > 0" class="cart-pill-badge">
            {{ store.cartItemCount }}
          </span>
        </button>
      </div>
    </header>

    <!-- Main Navigation Tabs: Order Capture vs Sync Queue -->
    <nav class="main-tab-nav">
      <button
        class="tab-item"
        :class="{ active: activeTab === 'capture' }"
        @click="activeTab = 'capture'"
      >
        <span class="material-symbols-outlined tab-icon">edit_note</span>
        <span class="tab-label">Order Capture</span>
        <span v-if="store.cartLines.length > 0" class="tab-counter">{{ store.cartLines.length }}</span>
      </button>

      <button
        class="tab-item"
        :class="{ active: activeTab === 'queue' }"
        @click="activeTab = 'queue'"
      >
        <span class="material-symbols-outlined tab-icon">cloud_sync</span>
        <span class="tab-label">Sync Queue</span>
        <span v-if="store.pendingCount + store.conflictCount > 0" class="tab-counter-warn">
          {{ store.pendingCount + store.conflictCount }}
        </span>
      </button>
    </nav>

    <!-- Main Content Area -->
    <main class="mobile-content-area">
      <!-- TAB 1: ORDER CAPTURE -->
      <section v-show="activeTab === 'capture'" class="tab-panel order-capture-panel">
        <!-- Customer Selection & History Card -->
        <CustomerSelectCard />

        <!-- Fast Catalog Search & SKU Engine -->
        <FastCatalogSearch />
      </section>

      <!-- TAB 2: SYNC QUEUE & LOCAL HISTORY -->
      <section v-show="activeTab === 'queue'" class="tab-panel sync-queue-panel">
        <div class="queue-header-row">
          <div class="queue-title-group">
            <h3 class="queue-heading">Offline Sync Queue</h3>
            <p class="queue-subheading">
              Orders created offline are saved in IndexedDB and automatically synchronized when online.
            </p>
          </div>

          <div class="queue-actions-group">
            <button
              class="btn-trigger-sync"
              :disabled="!store.isOnline || store.isSyncing || store.pendingCount === 0"
              @click="handleTriggerSync"
            >
              <span class="material-symbols-outlined" :class="{ 'spin-icon': store.isSyncing }">
                sync
              </span>
              Sync Now
            </button>

            <button
              v-if="store.syncedCount > 0"
              class="btn-clear-synced"
              @click="store.clearSyncedOrders"
            >
              Clear Synced
            </button>
          </div>
        </div>

        <!-- Filter Sub-tabs for Queue -->
        <div class="queue-filter-tabs">
          <button
            class="filter-pill"
            :class="{ active: queueFilter === 'all' }"
            @click="queueFilter = 'all'"
          >
            All ({{ store.queuedOrders.length }})
          </button>
          <button
            class="filter-pill"
            :class="{ active: queueFilter === 'pending' }"
            @click="queueFilter = 'pending'"
          >
            Pending ({{ store.pendingOrders.length }})
          </button>
          <button
            class="filter-pill"
            :class="{ active: queueFilter === 'conflict' }"
            @click="queueFilter = 'conflict'"
          >
            Conflicts ({{ store.conflictOrders.length }})
          </button>
          <button
            class="filter-pill"
            :class="{ active: queueFilter === 'synced' }"
            @click="queueFilter = 'synced'"
          >
            Synced ({{ store.syncedOrders.length }})
          </button>
        </div>

        <!-- Orders Queue List -->
        <div class="queue-list">
          <div
            v-for="order in filteredQueueOrders"
            :key="order.client_order_uuid"
            class="queued-order-card"
            :class="getOrderCardStatusClass(order.status)"
          >
            <div class="order-header-line">
              <div class="customer-info-box">
                <span class="customer-order-name">{{ order.customer_name }}</span>
                <span class="order-uuid-tag font-mono">{{ truncateUuid(order.client_order_uuid) }}</span>
              </div>

              <div class="order-status-badge" :class="getOrderStatusBadgeClass(order.status)">
                <span class="material-symbols-outlined badge-status-icon">{{ getOrderStatusIcon(order.status) }}</span>
                <span>{{ order.status }}</span>
              </div>
            </div>

            <!-- Items & Financial Summary -->
            <div class="order-summary-row">
              <div class="summary-col">
                <span class="summary-label">Created At</span>
                <span class="summary-value">{{ formatDate(order.offline_created_at || order.order_date) }}</span>
              </div>
              <div class="summary-col">
                <span class="summary-label">Items</span>
                <span class="summary-value">{{ (order.lines || []).length }} lines</span>
              </div>
              <div class="summary-col">
                <span class="summary-label">Grand Total</span>
                <span class="summary-value font-bold text-primary">{{ formatMoney(order.grand_total) }}</span>
              </div>
            </div>

            <!-- Conflict or Error Notice Banner -->
            <div v-if="order.status === 'Conflict' || order.error_message" class="order-error-banner">
              <span class="material-symbols-outlined error-banner-icon">report_problem</span>
              <span class="error-banner-text">
                {{ order.error_message || 'Inventory conflict: stock changed while offline' }}
              </span>
            </div>

            <!-- Action Buttons Row -->
            <div class="order-actions-bar">
              <button
                v-if="order.status === 'Conflict'"
                class="btn-resolve-conflict"
                @click="openConflictModalFor(order)"
              >
                <span class="material-symbols-outlined">rule</span>
                Resolve Conflict
              </button>

              <button
                v-if="order.status === 'Pending' || order.status === 'Failed'"
                class="btn-retry-sync"
                :disabled="!store.isOnline || store.isSyncing"
                @click="store.triggerSync({ force: true })"
              >
                <span class="material-symbols-outlined">refresh</span>
                Retry Sync
              </button>

              <button
                class="btn-delete-queued"
                @click="handleDeleteOrder(order.client_order_uuid)"
                title="Discard order from local device"
              >
                <span class="material-symbols-outlined">delete_outline</span>
              </button>
            </div>
          </div>

          <!-- Empty Queue State -->
          <div v-if="filteredQueueOrders.length === 0" class="empty-queue-state">
            <span class="material-symbols-outlined empty-icon">inbox</span>
            <p class="empty-title">No orders in this queue</p>
            <p class="empty-desc">Orders you take in the Field Sales app will appear here until synced.</p>
          </div>
        </div>
      </section>
    </main>

    <!-- Sticky Bottom Bar for Mobile Cart Summary -->
    <footer v-if="store.cartLines.length > 0" class="sticky-cart-bottom-bar">
      <div class="bottom-bar-content">
        <div class="bottom-summary" @click="isCartDrawerOpen = true">
          <div class="bottom-cart-icon-box">
            <span class="material-symbols-outlined">shopping_basket</span>
            <span class="bottom-badge">{{ store.cartItemCount }}</span>
          </div>
          <div class="bottom-totals">
            <span class="bottom-customer-name">
              {{ store.selectedCustomer ? store.selectedCustomer.name : 'Select Customer' }}
            </span>
            <span class="bottom-grand-total">{{ formatMoney(store.cartGrandTotal) }}</span>
          </div>
        </div>

        <button class="btn-review-order" @click="isCartDrawerOpen = true">
          <span>Review Order</span>
          <span class="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </footer>

    <!-- Modals & Drawers -->
    <MobileCartDrawer
      :is-open="isCartDrawerOpen"
      @close="isCartDrawerOpen = false"
      @order-submitted="handleOrderSubmitted"
    />

    <ConflictResolutionModal
      :order="store.activeConflictOrder"
      @close="store.closeConflictModal"
      @resolved="handleConflictResolved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'
import SyncStatusBadge from '../../components/mobile/SyncStatusBadge.vue'
import CustomerSelectCard from '../../components/mobile/CustomerSelectCard.vue'
import FastCatalogSearch from '../../components/mobile/FastCatalogSearch.vue'
import MobileCartDrawer from '../../components/mobile/MobileCartDrawer.vue'
import ConflictResolutionModal from '../../components/mobile/ConflictResolutionModal.vue'

const store = useFieldSalesStore()
const { show: toast } = useToast()

const activeTab = ref('capture')
const queueFilter = ref('all')
const isCartDrawerOpen = ref(false)

const filteredQueueOrders = computed(() => {
  if (queueFilter.value === 'pending') return store.pendingOrders
  if (queueFilter.value === 'conflict') return store.conflictOrders
  if (queueFilter.value === 'synced') return store.syncedOrders
  return store.queuedOrders
})

function formatMoney(amount) {
  const num = Number(amount) || 0
  return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return isoStr
  }
}

function truncateUuid(uuid) {
  if (!uuid) return ''
  return uuid.length > 16 ? `${uuid.slice(0, 8)}...${uuid.slice(-4)}` : uuid
}

function getOrderCardStatusClass(status) {
  if (status === 'Synced' || status === 'AlreadySynced') return 'card-synced'
  if (status === 'Conflict') return 'card-conflict'
  if (status === 'Failed') return 'card-failed'
  return 'card-pending'
}

function getOrderStatusBadgeClass(status) {
  if (status === 'Synced' || status === 'AlreadySynced') return 'badge-success'
  if (status === 'Conflict') return 'badge-danger'
  if (status === 'Failed') return 'badge-danger'
  return 'badge-warning'
}

function getOrderStatusIcon(status) {
  if (status === 'Synced' || status === 'AlreadySynced') return 'check_circle'
  if (status === 'Conflict') return 'warning'
  if (status === 'Failed') return 'error_outline'
  return 'schedule'
}

function handleWarehouseChange(warehouseId) {
  store.setWarehouse(warehouseId)
  toast('Warehouse switched', 'info')
}

async function handleRefreshCatalog() {
  try {
    const res = await store.fetchCatalog({ force: true })
    if (res && res.success) {
      toast('Catalog updated successfully', 'success')
    }
  } catch (err) {
    toast(`Failed to refresh catalog: ${err.message}`, 'error')
  }
}

async function handleTriggerSync() {
  try {
    const res = await store.triggerSync({ force: true })
    if (res && res.success) {
      toast('All pending orders synchronized!', 'success')
    }
  } catch (err) {
    toast(`Sync error: ${err.message}`, 'error')
  }
}

function openConflictModalFor(order) {
  store.openConflictModal(order.client_order_uuid)
}

async function handleDeleteOrder(uuid) {
  if (window.confirm('Delete this order from local queue?')) {
    await store.deleteQueuedOrder(uuid)
    toast('Order removed from queue', 'info')
  }
}

function handleOrderSubmitted() {
  activeTab.value = 'queue'
}

function handleConflictResolved() {
  toast('Order conflict resolved successfully', 'success')
}

onMounted(async () => {
  await store.init()
})

onUnmounted(() => {
  store.cleanup()
})
</script>

<style scoped>
.field-sales-mobile-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-body);
  color: var(--text-primary);
  padding-bottom: 70px;
}

/* Top Navigation Bar */
.mobile-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-branding {
  display: flex;
  align-items: center;
  gap: 6px;
}

.branding-icon {
  color: var(--color-primary);
  font-size: 24px;
}

.branding-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}

.warehouse-picker-box {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-input);
  border-radius: 6px;
  padding: 2px 6px;
}

.picker-icon {
  font-size: 16px;
  color: var(--text-subtle);
}

.warehouse-select {
  background: transparent;
  border: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: var(--bg-surface-hover);
  color: var(--color-primary);
}

.btn-refresh:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-refresh .material-symbols-outlined {
  font-size: 18px;
}

.btn-cart-header {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cart-header:hover {
  background: var(--color-primary);
  color: #fff;
}

.btn-cart-header .material-symbols-outlined {
  font-size: 20px;
}

.cart-pill-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
  border: 2px solid var(--bg-surface);
}

/* Tab Navigation */
.main-tab-nav {
  display: flex;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 0 16px;
}

.tab-item {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-item:hover {
  color: var(--text-primary);
}

.tab-item.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 700;
}

.tab-icon {
  font-size: 18px;
}

.tab-counter {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
}

.tab-counter-warn {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
  background: #f59e0b;
  color: #fff;
}

/* Content Area */
.mobile-content-area {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 16px;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Queue Tab Styles */
.queue-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
}

.queue-heading {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.queue-subheading {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.queue-actions-group {
  display: flex;
  gap: 8px;
}

.btn-trigger-sync {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-trigger-sync:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-clear-synced {
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.queue-filter-tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.filter-pill {
  padding: 4px 12px;
  border-radius: 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.filter-pill.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queued-order-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.card-conflict {
  border-color: #fca5a5;
  background: #fffcfc;
}

.order-header-line {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.customer-info-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.customer-order-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.order-uuid-tag {
  font-size: 11px;
  color: var(--text-subtle);
}

.order-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 12px;
}

.badge-status-icon {
  font-size: 13px;
}

.badge-success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.badge-warning {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.order-summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: var(--bg-surface-low, #f9fafb);
  border-radius: 8px;
  padding: 8px 12px;
  gap: 8px;
}

.summary-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: 10px;
  color: var(--text-subtle);
  text-transform: uppercase;
}

.summary-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.order-error-banner {
  padding: 8px 10px;
  background: #fee2e2;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #991b1b;
}

.error-banner-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.order-actions-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 6px;
  border-top: 1px solid var(--border-light);
}

.btn-resolve-conflict {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  background: #dc2626;
  color: #fff;
  border: none;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.btn-resolve-conflict .material-symbols-outlined {
  font-size: 16px;
}

.btn-retry-sync {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-retry-sync .material-symbols-outlined {
  font-size: 16px;
}

.btn-delete-queued {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 4px;
}

.btn-delete-queued:hover {
  color: var(--color-error, #dc2626);
}

.btn-delete-queued .material-symbols-outlined {
  font-size: 18px;
}

.empty-queue-state {
  padding: 50px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--text-subtle);
}

.empty-icon {
  font-size: 44px;
  margin-bottom: 8px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 12px;
  margin: 4px 0 0 0;
}

/* Sticky Bottom Bar */
.sticky-cart-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-default);
  box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.08);
  padding: 10px 16px;
  z-index: 90;
}

.bottom-bar-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.bottom-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  min-width: 0;
}

.bottom-cart-icon-box {
  position: relative;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bottom-cart-icon-box .material-symbols-outlined {
  font-size: 22px;
}

.bottom-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
  border: 2px solid var(--bg-surface);
}

.bottom-totals {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.bottom-customer-name {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bottom-grand-total {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.btn-review-order {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-review-order:hover {
  background: var(--color-primary-hover);
}

.btn-review-order .material-symbols-outlined {
  font-size: 18px;
}

.spin-icon {
  animation: spin 1s infinite linear;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

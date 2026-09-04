<template>
  <div class="customer-card-container">
    <!-- Unselected State: Search & Selection Modal / Drawer / Accordion -->
    <div v-if="!store.selectedCustomer" class="customer-selection-box">
      <div class="selection-header">
        <div class="header-title">
          <span class="material-symbols-outlined icon-primary">person_search</span>
          <span class="title-text">Select Customer</span>
        </div>
        <span class="customer-count-badge">{{ store.filteredCustomers.length }} available</span>
      </div>

      <!-- Customer Search Input -->
      <div class="search-input-wrapper">
        <span class="material-symbols-outlined search-icon">search</span>
        <input
          v-model="store.customerSearchQuery"
          type="text"
          class="customer-search-input"
          placeholder="Search by name, phone, city, group..."
          aria-label="Search customer"
        />
        <button
          v-if="store.customerSearchQuery"
          class="clear-query-btn"
          @click="store.customerSearchQuery = ''"
          aria-label="Clear customer search"
        >
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>

      <!-- Customer Candidates List -->
      <div class="customer-list">
        <div
          v-for="cust in visibleCustomers"
          :key="cust.id"
          class="customer-list-item"
          @click="handleSelectCustomer(cust)"
        >
          <div class="cust-avatar">
            <span class="material-symbols-outlined">storefront</span>
          </div>
          <div class="cust-info">
            <div class="cust-top-line">
              <span class="cust-name">{{ cust.name }}</span>
              <span v-if="cust.group_name" class="cust-group-pill">{{ cust.group_name }}</span>
            </div>
            <div class="cust-meta-line">
              <span v-if="cust.phone" class="meta-item">
                <span class="material-symbols-outlined mini-icon">phone</span>
                {{ cust.phone }}
              </span>
              <span v-if="cust.city" class="meta-item">
                <span class="material-symbols-outlined mini-icon">location_on</span>
                {{ cust.city }}
              </span>
              <span class="meta-item credit-highlight">
                Credit: {{ formatMoney(cust.available_credit !== undefined && cust.available_credit !== null ? cust.available_credit : ((Number(cust.credit_limit) || 0) - (Number(cust.balance) || 0))) }}
              </span>
            </div>
          </div>
          <button class="btn-select-customer" @click.stop="handleSelectCustomer(cust)">
            Select
          </button>
        </div>

        <!-- Empty state -->
        <div v-if="visibleCustomers.length === 0" class="empty-customer-list">
          <span class="material-symbols-outlined empty-icon">sentiment_dissatisfied</span>
          <p class="empty-text">No customers found matching "{{ store.customerSearchQuery }}"</p>
        </div>
      </div>
    </div>

    <!-- Selected State: Customer Profile Card & Quick History -->
    <div v-else class="customer-profile-card">
      <div class="profile-top">
        <div class="customer-identity">
          <div class="avatar-circle">
            <span class="material-symbols-outlined">storefront</span>
          </div>
          <div class="identity-details">
            <div class="name-badge-row">
              <h3 class="customer-name-heading">{{ store.selectedCustomer.name }}</h3>
              <span v-if="store.selectedCustomer.group_name" class="group-tag">
                {{ store.selectedCustomer.group_name }}
              </span>
            </div>
            <div class="contact-subline">
              <span v-if="store.selectedCustomer.phone" class="subline-item">
                <span class="material-symbols-outlined mini-icon">call</span>
                {{ store.selectedCustomer.phone }}
              </span>
              <span v-if="store.selectedCustomer.city" class="subline-item">
                <span class="material-symbols-outlined mini-icon">place</span>
                {{ store.selectedCustomer.city }}
              </span>
            </div>
          </div>
        </div>

        <button class="btn-change-customer" @click="handleChangeCustomer" title="Change selected customer">
          <span class="material-symbols-outlined">swap_horiz</span>
          Change
        </button>
      </div>

      <!-- Financial Status Bar -->
      <div class="financial-summary-grid">
        <div class="fin-stat-box">
          <span class="fin-label">Credit Limit</span>
          <span class="fin-val">{{ formatMoney(store.selectedCustomer.credit_limit || 0) }}</span>
        </div>

        <div class="fin-stat-box">
          <span class="fin-label">Balance</span>
          <span class="fin-val font-mono">{{ formatMoney(store.selectedCustomer.balance || 0) }}</span>
        </div>

        <div class="fin-stat-box" :class="{ 'credit-warning': store.isCreditLimitExceeded }">
          <span class="fin-label">Available Credit</span>
          <span class="fin-val font-bold" :class="availableCreditClass">
            {{ formatMoney(store.customerAvailableCredit) }}
          </span>
        </div>

        <div class="fin-stat-box">
          <span class="fin-label">Payment Terms</span>
          <span class="fin-val terms-pill">{{ paymentTermText }}</span>
        </div>
      </div>

      <!-- Credit Limit Exceeded Warning Alert -->
      <div v-if="store.isCreditLimitExceeded" class="credit-alert-banner">
        <span class="material-symbols-outlined">error</span>
        <span>Order total ({{ formatMoney(store.cartGrandTotal) }}) exceeds available credit limit ({{ formatMoney(store.customerAvailableCredit) }}).</span>
      </div>

      <!-- Customer Order History Accordion / Carousel -->
      <div v-if="store.customerRecentOrders && store.customerRecentOrders.length > 0" class="history-section">
        <div class="history-toggle" @click="historyExpanded = !historyExpanded">
          <div class="history-title">
            <span class="material-symbols-outlined history-icon">history</span>
            <span>Recent Orders ({{ store.customerRecentOrders.length }})</span>
            <span class="reorder-tip">1-Click Quick Reorder</span>
          </div>
          <span class="material-symbols-outlined chevron-icon" :class="{ open: historyExpanded }">
            expand_more
          </span>
        </div>

        <!-- History Content -->
        <div v-if="historyExpanded" class="history-carousel">
          <div
            v-for="order in store.customerRecentOrders"
            :key="order.order_id || order.id || order.order_number"
            class="history-order-card"
          >
            <div class="order-card-header">
              <div class="order-meta">
                <span class="order-number">{{ order.order_number || `#${order.order_id || order.id}` }}</span>
                <span class="order-date">{{ formatDate(order.order_date || order.created_at) }}</span>
              </div>
              <span class="order-total-amount">{{ formatMoney(order.total_amount || order.grand_total || 0) }}</span>
            </div>

            <!-- Order Lines Mini Preview -->
            <div v-if="order.lines && order.lines.length" class="order-items-preview">
              <div v-for="line in order.lines.slice(0, 3)" :key="line.product_id || line.sku" class="mini-item-row">
                <span class="mini-item-name">{{ line.product_name || line.name || line.sku }}</span>
                <span class="mini-item-qty">x{{ line.qty || line.quantity }}</span>
              </div>
              <div v-if="order.lines.length > 3" class="more-items-tag">
                +{{ order.lines.length - 3 }} more items
              </div>
            </div>

            <!-- 1-Click Reorder Button -->
            <button class="btn-reorder-all" @click="handleApplyReorder(order)" :disabled="reordering">
              <span class="material-symbols-outlined">shopping_cart_checkout</span>
              <span>Reorder Items</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'

const store = useFieldSalesStore()
const { show: toast } = useToast()

const historyExpanded = ref(false)
const reordering = ref(false)

const visibleCustomers = computed(() => {
  return store.filteredCustomers.slice(0, 30)
})

const paymentTermText = computed(() => {
  if (!store.selectedCustomer) return 'Standard'
  if (store.selectedCustomer.payment_term_name) return store.selectedCustomer.payment_term_name
  if (store.paymentTerms && store.selectedCustomer.payment_term_id) {
    const term = store.paymentTerms.find((t) => t.id === store.selectedCustomer.payment_term_id)
    if (term) return term.name || term.term_name || `Term #${term.id}`
  }
  return 'Standard'
})

const availableCreditClass = computed(() => {
  const avail = store.customerAvailableCredit
  if (avail <= 0) return 'text-danger'
  if (avail < 500) return 'text-warning'
  return 'text-success'
})

function formatMoney(amount) {
  const num = Number(amount) || 0
  return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return dateStr
  }
}

async function handleSelectCustomer(customer) {
  try {
    await store.selectCustomer(customer)
    toast(`Customer selected: ${customer.name}`, 'info')
  } catch (err) {
    toast(`Failed to select customer: ${err.message}`, 'error')
  }
}

function handleChangeCustomer() {
  store.clearCustomer()
}

async function handleApplyReorder(order) {
  reordering.value = true
  try {
    const applied = await store.applyReorder(order)
    if (applied) {
      toast(`Added items from order ${order.order_number || ''} to cart`, 'success')
    } else {
      toast('No items could be added from this order history', 'warning')
    }
  } catch (err) {
    toast(`Failed to reorder: ${err.message}`, 'error')
  } finally {
    reordering.value = false
  }
}
</script>

<style scoped>
.customer-card-container {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* Unselected Box */
.customer-selection-box {
  padding: 14px;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.icon-primary {
  color: var(--color-primary);
  font-size: 20px;
}

.customer-count-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--bg-surface-low, #f9fafb);
  color: var(--text-muted);
  border: 1px solid var(--border-light);
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-subtle);
  font-size: 18px;
  pointer-events: none;
}

.customer-search-input {
  width: 100%;
  height: 40px;
  padding: 8px 36px 8px 36px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s;
}

.customer-search-input:focus {
  border-color: var(--color-primary);
}

.clear-query-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 4px;
}

.clear-query-btn .material-symbols-outlined {
  font-size: 16px;
}

.customer-list {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.customer-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all 0.15s ease;
}

.customer-list-item:hover {
  background: var(--bg-surface-hover);
  border-color: var(--color-primary);
}

.cust-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cust-avatar .material-symbols-outlined {
  font-size: 18px;
}

.cust-info {
  flex: 1;
  min-width: 0;
}

.cust-top-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cust-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cust-group-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--bg-surface-low);
  color: var(--text-muted);
  border: 1px solid var(--border-light);
}

.cust-meta-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-subtle);
  margin-top: 2px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.mini-icon {
  font-size: 12px;
}

.credit-highlight {
  color: var(--color-success, #16a34a);
  font-weight: 600;
}

.btn-select-customer {
  padding: 5px 12px;
  border-radius: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-select-customer:hover {
  background: var(--color-primary);
  color: #fff;
}

.empty-customer-list {
  padding: 24px;
  text-align: center;
  color: var(--text-subtle);
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 6px;
}

.empty-text {
  font-size: 12px;
}

/* Selected Customer Profile Card */
.customer-profile-card {
  padding: 14px;
}

.profile-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.customer-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.avatar-circle {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-circle .material-symbols-outlined {
  font-size: 22px;
}

.identity-details {
  min-width: 0;
}

.name-badge-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.customer-name-heading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
}

.contact-subline {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.subline-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.btn-change-customer {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-change-customer:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-change-customer .material-symbols-outlined {
  font-size: 16px;
}

/* Financial summary grid */
.financial-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 10px;
}

@media (max-width: 600px) {
  .financial-summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.fin-stat-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fin-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-subtle);
  letter-spacing: 0.3px;
}

.fin-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.font-mono {
  font-family: monospace;
}

.font-bold {
  font-weight: 700;
}

.terms-pill {
  font-size: 11px;
  color: var(--color-primary);
}

.text-success {
  color: var(--color-success, #16a34a);
}

.text-warning {
  color: #d97706;
}

.text-danger {
  color: var(--color-error, #dc2626);
}

.credit-alert-banner {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #991b1b;
}

.credit-alert-banner .material-symbols-outlined {
  font-size: 18px;
  flex-shrink: 0;
}

/* History Section */
.history-section {
  margin-top: 12px;
  border-top: 1px solid var(--border-light);
  padding-top: 10px;
}

.history-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 4px 0;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-icon {
  font-size: 18px;
  color: var(--color-primary);
}

.reorder-tip {
  font-size: 10px;
  background: #dbeafe;
  color: #1e40af;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.chevron-icon {
  font-size: 18px;
  color: var(--text-subtle);
  transition: transform 0.2s ease;
}

.chevron-icon.open {
  transform: rotate(180deg);
}

.history-carousel {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 10px 0 4px 0;
  scrollbar-width: thin;
}

.history-order-card {
  min-width: 220px;
  max-width: 240px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}

.order-meta {
  display: flex;
  flex-direction: column;
}

.order-number {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.order-date {
  font-size: 10px;
  color: var(--text-subtle);
}

.order-total-amount {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-primary);
}

.order-items-preview {
  margin: 6px 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
}

.mini-item-row {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
}

.mini-item-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.mini-item-qty {
  font-weight: 600;
  color: var(--text-secondary);
}

.more-items-tag {
  font-size: 10px;
  color: var(--text-subtle);
  font-style: italic;
}

.btn-reorder-all {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
  border: none;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-reorder-all:hover:not(:disabled) {
  background: var(--color-primary);
  color: #fff;
}

.btn-reorder-all:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reorder-all .material-symbols-outlined {
  font-size: 14px;
}
</style>

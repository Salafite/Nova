<template>
  <div class="portal-cart-page" :dir="dir">
    <div class="portal-container">
      <!-- Breadcrumb & Page Header -->
      <div class="cart-header-section">
        <div class="cart-header-left">
          <router-link to="/portal/catalog" class="back-link">
            <span class="material-symbols-outlined">arrow_back</span>
            <span>{{ t('back-to-catalog', 'Back to Order Supplies') }}</span>
          </router-link>
          <h1 class="page-title">{{ t('cart-title', 'Replenishment Cart & Checkout') }}</h1>
          <p class="page-subtitle">{{ t('cart-subtitle', 'Review contracted items, select delivery schedule, and confirm your replenishment order.') }}</p>
        </div>
        <div class="cart-header-right" v-if="portal.cart.length > 0">
          <button class="btn-clear-cart" @click="handleClearCart">
            <span class="material-symbols-outlined">delete_sweep</span>
            <span>{{ t('clear-cart', 'Clear Cart') }}</span>
          </button>
        </div>
      </div>

      <!-- Empty Cart State -->
      <div v-if="!portal.cart || portal.cart.length === 0" class="empty-cart-card">
        <div class="empty-cart-icon">
          <span class="material-symbols-outlined">shopping_cart</span>
        </div>
        <h2>{{ t('cart-empty-title', 'Your Replenishment Cart is Empty') }}</h2>
        <p>{{ t('cart-empty-desc', 'Browse our wholesale catalog to add contracted products for your restaurant or grocery business.') }}</p>
        <router-link to="/portal/catalog" class="btn-browse-catalog">
          <span class="material-symbols-outlined">inventory_2</span>
          <span>{{ t('browse-supplies', 'Browse Order Supplies') }}</span>
        </router-link>
      </div>

      <!-- Active Cart Layout (Two Columns: Items Review + Checkout Summary) -->
      <div v-else class="cart-grid-layout">
        <!-- Left Column: Line Items Review -->
        <div class="cart-items-column">
          <!-- Cutoff Schedule Alert -->
          <div class="schedule-alert-box" :class="{ 'past-cutoff': portal.isPastCutoff }">
            <div class="schedule-icon-area">
              <span class="material-symbols-outlined">{{ portal.isPastCutoff ? 'schedule' : 'local_shipping' }}</span>
            </div>
            <div class="schedule-text-area">
              <div class="schedule-title">
                {{ portal.isPastCutoff ? t('cutoff-schedule-past', 'Post-Cutoff Fulfillment') : t('cutoff-schedule-ontime', 'Next-Day Delivery Scheduled') }}
              </div>
              <div class="schedule-desc">
                {{ portal.isPastCutoff 
                  ? t('cutoff-past-cart-msg', 'Order placed after daily cutoff. Delivery is scheduled for ') + portal.nextDeliveryDate
                  : t('cutoff-ontime-cart-msg', 'Order placed before daily cutoff. Estimated delivery on ') + portal.nextDeliveryDate
                }}
              </div>
            </div>
          </div>

          <!-- Items Table Card -->
          <div class="cart-table-card">
            <div class="table-header-title">
              <span class="material-symbols-outlined">format_list_bulleted</span>
              <h3>{{ t('order-items', 'Order Line Items') }} ({{ portal.cartUniqueItemCount }} {{ portal.cartUniqueItemCount === 1 ? 'item' : 'items' }})</h3>
            </div>

            <div class="items-list">
              <div
                v-for="item in portal.cart"
                :key="item.product_id"
                class="cart-item-row"
                :class="{ 'contracted-item': item.is_contracted }"
              >
                <!-- Item Visual & Info -->
                <div class="item-main-info">
                  <div class="item-avatar">
                    <span class="material-symbols-outlined">inventory_2</span>
                  </div>
                  <div class="item-meta">
                    <div class="item-tags">
                      <span class="sku-badge">{{ item.product_code }}</span>
                      <span v-if="item.category_name" class="category-badge">{{ item.category_name }}</span>
                      <span v-if="item.is_contracted" class="contract-badge">
                        <span class="material-symbols-outlined">verified</span> Contracted
                      </span>
                    </div>
                    <div class="item-name">{{ item.product_name }}</div>
                    <div class="item-uom" v-if="item.uom_name">{{ t('unit', 'Unit') }}: {{ item.uom_name }}</div>

                    <!-- Line Item Special Instructions -->
                    <div class="item-note-input-wrap">
                      <input
                        type="text"
                        v-model="item.notes"
                        @change="portal.saveCart()"
                        :placeholder="t('item-note-placeholder', 'Add item note / special instruction (optional)...')"
                        class="item-note-input"
                      />
                    </div>
                  </div>
                </div>

                <!-- Item Price, Stepper & Line Total -->
                <div class="item-actions-cluster">
                  <!-- Unit Price -->
                  <div class="item-unit-price-box">
                    <span class="unit-price-val">${{ (item.unit_price || 0).toFixed(2) }}</span>
                    <span class="unit-price-lbl">/ {{ item.uom_name || 'ea' }}</span>
                  </div>

                  <!-- Stepper -->
                  <div class="item-stepper">
                    <button class="step-action-btn" @click="decrementQty(item)">−</button>
                    <input
                      type="number"
                      min="1"
                      class="step-qty-val"
                      :value="item.qty"
                      @change="handleQtyInput(item, $event.target.value)"
                    />
                    <button class="step-action-btn" @click="incrementQty(item)">+</button>
                  </div>

                  <!-- Line Total -->
                  <div class="item-line-total-box">
                    <span class="line-total-val">${{ ((item.unit_price || 0) * (item.qty || 1)).toFixed(2) }}</span>
                  </div>

                  <!-- Remove Button -->
                  <button
                    class="btn-remove-item"
                    @click="portal.removeFromCart(item.product_id)"
                    title="Remove item"
                  >
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Order Checkout Summary Card -->
        <div class="cart-summary-column">
          <div class="summary-sticky-card">
            <h3 class="summary-card-title">{{ t('order-summary', 'Order Summary') }}</h3>

            <!-- Minimum Order Requirement Gauge -->
            <div class="min-order-gauge-box" v-if="portal.minOrderAmount > 0">
              <div class="gauge-header">
                <span class="gauge-label">{{ t('min-order-threshold', 'Min Order Threshold') }}</span>
                <span class="gauge-status" :class="portal.meetsMinOrder ? 'text-success' : 'text-warning'">
                  {{ portal.meetsMinOrder ? t('met', 'Met') : t('shortfall', 'Shortfall') }}
                </span>
              </div>
              <div class="gauge-bar-track">
                <div
                  class="gauge-bar-fill"
                  :class="{ 'fill-success': portal.meetsMinOrder }"
                  :style="{ width: `${portal.minOrderProgress}%` }"
                ></div>
              </div>
              <div class="gauge-details">
                <span>${{ portal.cartSubtotal.toFixed(2) }} of ${{ portal.minOrderAmount.toFixed(2) }}</span>
                <span v-if="!portal.meetsMinOrder" class="text-warning font-semibold">
                  +${{ portal.minOrderShortfall.toFixed(2) }} needed
                </span>
              </div>
            </div>

            <!-- Price Breakdown -->
            <div class="summary-breakdown">
              <div class="breakdown-row">
                <span class="label">{{ t('items-count', 'Total Items') }}</span>
                <span class="value">{{ portal.cartItemCount }}</span>
              </div>
              <div class="breakdown-row">
                <span class="label">{{ t('cart-subtotal', 'Cart Subtotal') }}</span>
                <span class="value">${{ portal.cartSubtotal.toFixed(2) }}</span>
              </div>
              <div class="breakdown-row">
                <span class="label">{{ t('estimated-tax', 'Estimated Tax (Wholesale)') }}</span>
                <span class="value">$0.00</span>
              </div>
              <div class="breakdown-row total-row">
                <span class="label">{{ t('order-total', 'Estimated Total') }}</span>
                <span class="value total-price">${{ portal.cartSubtotal.toFixed(2) }}</span>
              </div>
            </div>

            <!-- Delivery & Fulfillment Settings -->
            <div class="fulfillment-settings-box">
              <div class="form-group">
                <label class="form-label">
                  <span class="material-symbols-outlined label-icon">event</span>
                  {{ t('requested-delivery-date', 'Requested Delivery Date') }}
                </label>
                <input
                  type="date"
                  v-model="deliveryDate"
                  :min="minDeliveryDate"
                  class="portal-input"
                />
                <span class="input-hint" v-if="portal.nextDeliveryDate">
                  Earliest available: {{ portal.nextDeliveryDate }}
                </span>
              </div>

              <div class="form-group">
                <label class="form-label">
                  <span class="material-symbols-outlined label-icon">notes</span>
                  {{ t('delivery-instructions', 'Delivery & Receiving Notes') }}
                </label>
                <textarea
                  v-model="orderNotes"
                  rows="2"
                  class="portal-textarea"
                  :placeholder="t('delivery-notes-placeholder', 'e.g., Gate code #1234, deliver to kitchen back dock before 10 AM...')"
                ></textarea>
              </div>
            </div>

            <!-- Submission Warnings & Buttons -->
            <div v-if="!portal.meetsMinOrder" class="min-order-alert-callout">
              <span class="material-symbols-outlined">error</span>
              <span>
                {{ t('min-order-block-msg', 'Minimum order amount of') }} ${{ portal.minOrderAmount.toFixed(2) }} {{ t('is-required-for-confirmed', 'is required to submit a confirmed order.') }}
              </span>
            </div>

            <div class="checkout-actions-stack">
              <!-- Primary: Confirm & Place Order -->
              <button
                class="btn-submit-order"
                :disabled="isSubmitting || !portal.meetsMinOrder || portal.cart.length === 0"
                @click="handleSubmitOrder('Confirmed')"
              >
                <span class="material-symbols-outlined" v-if="!isSubmitting">check_circle</span>
                <span class="material-symbols-outlined spin-icon" v-else>sync</span>
                <span>{{ isSubmitting ? t('submitting-order', 'Placing Order...') : t('confirm-and-place-order', 'Confirm & Place Order') }}</span>
              </button>

              <!-- Secondary: Save as Draft Order -->
              <button
                class="btn-save-draft"
                :disabled="isSubmitting || portal.cart.length === 0"
                @click="handleSubmitOrder('Draft')"
              >
                <span class="material-symbols-outlined">draft</span>
                <span>{{ t('save-as-draft', 'Save as Draft Order') }}</span>
              </button>
            </div>

            <!-- Customer Account Credit Overview -->
            <div class="account-credit-footer" v-if="portal.accountSummary">
              <div class="credit-row">
                <span class="credit-lbl">{{ t('available-credit', 'Available Credit') }}:</span>
                <span class="credit-val">${{ (portal.accountSummary.available_credit || 0).toFixed(2) }}</span>
              </div>
              <div class="credit-row">
                <span class="credit-lbl">{{ t('payment-terms', 'Payment Terms') }}:</span>
                <span class="credit-val">{{ portal.accountSummary.price_list_name || 'Net 30' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Success Confirmation Dialog -->
    <div v-if="submittedOrder" class="modal-overlay">
      <div class="order-success-modal">
        <div class="success-icon-badge">
          <span class="material-symbols-outlined">check</span>
        </div>
        <h2>{{ t('order-placed-title', 'Replenishment Order Submitted!') }}</h2>
        <p class="order-number-text">
          {{ t('order-number', 'Order Number') }}: <strong>{{ submittedOrder.order_number }}</strong>
        </p>
        <div class="order-summary-pill-box">
          <div class="summary-pill">
            <span class="pill-title">{{ t('status', 'Status') }}</span>
            <span class="badge" :class="submittedOrder.status === 'Confirmed' ? 'badge-green' : 'badge-amber'">
              {{ submittedOrder.status }}
            </span>
          </div>
          <div class="summary-pill">
            <span class="pill-title">{{ t('delivery-date', 'Delivery Date') }}</span>
            <span class="pill-val">{{ submittedOrder.requested_delivery_date || 'Scheduled' }}</span>
          </div>
          <div class="summary-pill">
            <span class="pill-title">{{ t('total-amount', 'Total') }}</span>
            <span class="pill-val">${{ (submittedOrder.total_amount || 0).toFixed(2) }}</span>
          </div>
        </div>
        <div class="modal-actions-row">
          <button class="btn-outline" @click="goToCatalog">
            <span class="material-symbols-outlined">shopping_bag</span>
            <span>{{ t('order-more-supplies', 'Order More Supplies') }}</span>
          </button>
          <button class="btn-primary" @click="goToOrders">
            <span class="material-symbols-outlined">receipt_long</span>
            <span>{{ t('view-order-history', 'View Orders') }}</span>
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

const deliveryDate = ref('')
const orderNotes = ref('')
const isSubmitting = ref(false)
const submittedOrder = ref(null)

const minDeliveryDate = computed(() => {
  if (portal.cutoffStatus?.next_delivery_date) {
    return portal.cutoffStatus.next_delivery_date
  }
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  return tomorrow.toISOString().split('T')[0]
})

function incrementQty(item) {
  portal.addToCart({ id: item.product_id }, 1)
}

function decrementQty(item) {
  if (item.qty <= 1) {
    portal.removeFromCart(item.product_id)
  } else {
    portal.updateCartQty(item.product_id, item.qty - 1)
  }
}

function handleQtyInput(item, val) {
  const parsed = parseInt(val, 10)
  if (isNaN(parsed) || parsed <= 0) {
    portal.removeFromCart(item.product_id)
  } else {
    portal.updateCartQty(item.product_id, parsed)
  }
}

function handleClearCart() {
  if (confirm(t('confirm-clear-cart', 'Are you sure you want to clear all items from your cart?'))) {
    portal.clearCart()
    showToast(t('cart-cleared', 'Cart cleared successfully'), 'info', 2000)
  }
}

async function handleSubmitOrder(orderStatus = 'Confirmed') {
  if (portal.cart.length === 0) return
  if (orderStatus === 'Confirmed' && !portal.meetsMinOrder) {
    showToast(t('min-order-unmet-error', 'Minimum order amount is not met'), 'error', 3000)
    return
  }

  isSubmitting.value = true
  try {
    const payload = {
      items: portal.cart.map(i => ({
        product_id: i.product_id,
        qty: Number(i.qty),
        notes: i.notes || null,
      })),
      requested_delivery_date: deliveryDate.value || portal.nextDeliveryDate || null,
      notes: orderNotes.value || null,
      status: orderStatus,
    }

    const orderRes = await portal.submitOrder(payload)
    if (orderRes) {
      submittedOrder.value = orderRes
      showToast(t('order-submitted-toast', `Order #${orderRes.order_number} submitted successfully!`), 'success', 4000)
    }
  } catch (err) {
    showToast(err.message || t('order-failed-toast', 'Failed to place order. Please try again.'), 'error', 5000)
  } finally {
    isSubmitting.value = false
  }
}

function goToCatalog() {
  submittedOrder.value = null
  router.push('/portal/catalog')
}

function goToOrders() {
  submittedOrder.value = null
  router.push('/portal/orders')
}

onMounted(async () => {
  await Promise.all([
    portal.fetchAccountSummary(),
    portal.fetchCutoffStatus(),
  ])
  if (portal.cutoffStatus?.next_delivery_date) {
    deliveryDate.value = portal.cutoffStatus.next_delivery_date
  }
})
</script>

<style scoped>
.portal-cart-page {
  width: 100%;
}

.portal-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

.cart-header-section {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #a5b4fc;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  margin-bottom: 8px;
  transition: color 0.15s;
}

.back-link:hover {
  color: #fff;
}

.back-link .material-symbols-outlined {
  font-size: 18px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
}

.btn-clear-cart {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-muted, #94a3b8);
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-clear-cart:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}

.btn-clear-cart .material-symbols-outlined {
  font-size: 18px;
}

/* Empty Cart */
.empty-cart-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px dashed var(--border-default, #2a2a4a);
  border-radius: 16px;
  padding: 80px 24px;
  text-align: center;
  max-width: 600px;
  margin: 40px auto;
}

.empty-cart-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--bg-surface-low, #222240);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #a5b4fc;
  margin-bottom: 20px;
}

.empty-cart-icon .material-symbols-outlined {
  font-size: 36px;
}

.empty-cart-card h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 8px;
}

.empty-cart-card p {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 24px;
  line-height: 1.5;
}

.btn-browse-catalog {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  padding: 12px 24px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
}

/* Active Cart Grid */
.cart-grid-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;
  align-items: flex-start;
}

@media (max-width: 1080px) {
  .cart-grid-layout {
    grid-template-columns: 1fr;
  }
}

/* Left Column */
.schedule-alert-box {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.25);
  margin-bottom: 20px;
}

.schedule-alert-box.past-cutoff {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.25);
}

.schedule-icon-area .material-symbols-outlined {
  font-size: 24px;
  color: #4ade80;
}

.past-cutoff .schedule-icon-area .material-symbols-outlined {
  color: #fbbf24;
}

.schedule-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 2px;
}

.schedule-desc {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}

.cart-table-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow: hidden;
}

.table-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
}

.table-header-title h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.table-header-title .material-symbols-outlined {
  font-size: 20px;
  color: #a5b4fc;
}

.items-list {
  display: flex;
  flex-direction: column;
}

.cart-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  gap: 16px;
  flex-wrap: wrap;
  transition: background 0.15s;
}

.cart-item-row:last-child {
  border-bottom: none;
}

.cart-item-row:hover {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.02));
}

.item-main-info {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
  min-width: 280px;
}

.item-avatar {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--bg-surface-low, #222240);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a5b4fc;
}

.item-avatar .material-symbols-outlined {
  font-size: 24px;
}

.item-meta {
  flex: 1;
}

.item-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.sku-badge {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  background: rgba(255, 255, 255, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
}

.category-badge {
  font-size: 11px;
  color: #a5b4fc;
}

.contract-badge {
  font-size: 10px;
  font-weight: 700;
  color: #4ade80;
  background: rgba(34, 197, 94, 0.15);
  padding: 1px 6px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.contract-badge .material-symbols-outlined {
  font-size: 11px;
}

.item-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin-bottom: 2px;
}

.item-uom {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  margin-bottom: 8px;
}

.item-note-input-wrap {
  margin-top: 4px;
}

.item-note-input {
  width: 100%;
  max-width: 380px;
  padding: 6px 10px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 6px;
  color: var(--text-primary, #fff);
  font-size: 11px;
  outline: none;
}

.item-note-input:focus {
  border-color: #6366f1;
}

.item-actions-cluster {
  display: flex;
  align-items: center;
  gap: 18px;
}

.item-unit-price-box {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 70px;
}

.unit-price-val {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.unit-price-lbl {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
}

.item-stepper {
  display: inline-flex;
  align-items: center;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid #6366f1;
  border-radius: 8px;
  overflow: hidden;
}

.step-action-btn {
  background: none;
  border: none;
  color: #a5b4fc;
  width: 32px;
  height: 32px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
}

.step-action-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  color: #fff;
}

.step-qty-val {
  width: 44px;
  text-align: center;
  background: none;
  border: none;
  color: var(--text-primary, #fff);
  font-weight: 700;
  font-size: 13px;
  outline: none;
}

.item-line-total-box {
  min-width: 80px;
  text-align: right;
}

.line-total-val {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.btn-remove-item {
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-remove-item:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.btn-remove-item .material-symbols-outlined {
  font-size: 20px;
}

/* Right Column: Checkout Sticky Card */
.summary-sticky-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 24px;
  position: sticky;
  top: 90px;
}

.summary-card-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin-bottom: 16px;
}

/* Min Order Gauge */
.min-order-gauge-box {
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 18px;
}

.gauge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 6px;
}

.gauge-label {
  color: var(--text-muted, #94a3b8);
  font-weight: 600;
}

.gauge-bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.gauge-bar-fill {
  height: 100%;
  background: #f59e0b;
  transition: width 0.3s ease;
}

.gauge-bar-fill.fill-success {
  background: #22c55e;
}

.gauge-details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}

.text-success {
  color: #4ade80 !important;
}

.text-warning {
  color: #fbbf24 !important;
}

.font-semibold {
  font-weight: 600;
}

/* Breakdown */
.summary-breakdown {
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  padding-bottom: 16px;
  margin-bottom: 16px;
}

.breakdown-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 10px;
}

.breakdown-row .label {
  color: var(--text-secondary, #94a3b8);
}

.breakdown-row .value {
  color: var(--text-primary, #fff);
  font-weight: 600;
}

.breakdown-row.total-row {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-default, #2a2a4a);
  margin-bottom: 0;
}

.breakdown-row.total-row .label {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.total-price {
  font-size: 20px !important;
  font-weight: 800 !important;
  color: #a5b4fc !important;
}

/* Fulfillment Inputs */
.fulfillment-settings-box {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
}

.label-icon {
  font-size: 16px;
  color: #a5b4fc;
}

.portal-input, .portal-textarea {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.portal-input:focus, .portal-textarea:focus {
  border-color: #6366f1;
}

.input-hint {
  font-size: 10px;
  color: var(--text-muted, #64748b);
}

.min-order-alert-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 16px;
  font-size: 11px;
  color: #f87171;
  line-height: 1.4;
}

.min-order-alert-callout .material-symbols-outlined {
  font-size: 18px;
  color: #ef4444;
  flex-shrink: 0;
}

/* Actions Stack */
.checkout-actions-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.btn-submit-order {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  border: none;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  transition: all 0.2s ease;
}

.btn-submit-order:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.6);
}

.btn-submit-order:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-save-draft {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-save-draft:hover:not(:disabled) {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.05));
  color: var(--text-primary, #fff);
}

.account-credit-footer {
  padding-top: 14px;
  border-top: 1px solid var(--border-default, #2a2a4a);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.credit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.credit-lbl {
  color: var(--text-muted, #64748b);
}

.credit-val {
  color: var(--text-secondary, #94a3b8);
  font-weight: 600;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Success Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}

.order-success-modal {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 16px;
  padding: 32px;
  max-width: 480px;
  width: 100%;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}

.success-icon-badge {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.15);
  border: 2px solid #22c55e;
  color: #22c55e;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.success-icon-badge .material-symbols-outlined {
  font-size: 36px;
}

.order-success-modal h2 {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}

.order-number-text {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 20px;
}

.order-summary-pill-box {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 24px;
}

.summary-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pill-title {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.5px;
}

.pill-val {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}

.modal-actions-row {
  display: flex;
  gap: 12px;
}

.modal-actions-row button {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.badge-green {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-amber {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}
</style>

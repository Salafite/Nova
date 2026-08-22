<template>
  <div v-if="isOpen" class="drawer-backdrop" @click="handleClose">
    <div class="drawer-panel" :class="{ open: isOpen }" @click.stop>
      <!-- Drawer Header -->
      <div class="drawer-header">
        <div class="header-main">
          <div class="header-icon-box">
            <span class="material-symbols-outlined">shopping_cart</span>
          </div>
          <div class="header-title-box">
            <div class="title-row">
              <h3 class="drawer-title">Active Order</h3>
              <span class="item-count-badge">{{ store.cartItemCount }} items</span>
            </div>
            <p class="customer-subtext">
              {{ store.selectedCustomer ? store.selectedCustomer.name : 'No customer selected' }}
            </p>
          </div>
        </div>

        <div class="header-actions">
          <button
            v-if="store.cartLines.length > 0"
            class="btn-clear-cart"
            @click="handleClearCart"
            title="Clear active order draft"
          >
            <span class="material-symbols-outlined">delete_sweep</span>
            Clear
          </button>
          <button class="btn-close-drawer" @click="handleClose" aria-label="Close cart drawer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
      </div>

      <!-- Drawer Body: Scrollable -->
      <div class="drawer-body">
        <!-- Empty Cart Notice -->
        <div v-if="store.cartLines.length === 0" class="empty-cart-state">
          <span class="material-symbols-outlined empty-cart-icon">remove_shopping_cart</span>
          <h4 class="empty-cart-title">Your draft order is empty</h4>
          <p class="empty-cart-desc">
            Browse the product catalog or use customer purchase history to add items to this order.
          </p>
        </div>

        <template v-else>
          <!-- Cart Items List -->
          <div class="cart-items-section">
            <div class="section-label">Order Items ({{ store.cartLines.length }} lines)</div>

            <div
              v-for="line in store.cartLines"
              :key="line.product_id"
              class="cart-line-card"
            >
              <div class="line-header">
                <div class="line-product-info">
                  <span class="line-title">{{ line.name || line.product_name }}</span>
                  <div class="line-meta">
                    <span class="line-sku">SKU: {{ line.sku }}</span>
                    <span v-if="line.is_contracted_price" class="contract-badge">Contracted</span>
                  </div>
                </div>
                <button
                  class="btn-remove-line"
                  @click="store.removeCartItem(line.product_id)"
                  aria-label="Remove item"
                >
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </div>

              <!-- Price & Quantity Controls Row -->
              <div class="line-controls-row">
                <!-- Quantity Steppers -->
                <div class="qty-stepper-box">
                  <button
                    class="step-btn minus"
                    @click="store.updateCartItemQty(line.product_id, line.qty - 1)"
                    aria-label="Decrease quantity"
                  >
                    <span class="material-symbols-outlined">remove</span>
                  </button>
                  <input
                    type="number"
                    min="1"
                    :value="line.qty"
                    class="qty-input"
                    @change="store.updateCartItemQty(line.product_id, Number($event.target.value) || 1)"
                  />
                  <button
                    class="step-btn plus"
                    @click="store.updateCartItemQty(line.product_id, line.qty + 1)"
                    aria-label="Increase quantity"
                  >
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>

                <!-- Unit Price & Discount Controls -->
                <div class="unit-price-display">
                  <div class="price-edit-toggle">
                    <span class="unit-rate-label">Unit Price:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      :value="line.unit_price"
                      class="price-override-input"
                      @change="store.updateCartItemPrice(line.product_id, Number($event.target.value) || 0)"
                    />
                  </div>
                  <div class="discount-input-row">
                    <span class="discount-label">Disc %:</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      :value="line.discount_pct || line.discount_rate || 0"
                      class="discount-input"
                      @change="store.updateCartItemDiscount(line.product_id, Number($event.target.value) || 0)"
                    />
                  </div>
                </div>

                <!-- Line Total -->
                <div class="line-total-box">
                  <span class="line-total-val">{{ formatMoney(line.total || line.line_total) }}</span>
                </div>
              </div>

              <!-- Optional Notes Input -->
              <div class="line-notes-row">
                <input
                  type="text"
                  :value="line.notes || ''"
                  placeholder="Add item instructions / notes..."
                  class="line-notes-input"
                  @change="store.updateCartItemNotes(line.product_id, $event.target.value)"
                />
              </div>
            </div>
          </div>

          <!-- Order Metadata Fields -->
          <div class="order-details-form">
            <div class="section-label">Order Logistics & Terms</div>

            <div class="form-grid">
              <div class="form-field">
                <label class="field-label">Requested Delivery Date</label>
                <input
                  v-model="store.draft.requested_delivery_date"
                  type="date"
                  class="field-input"
                  @change="store.saveDraft"
                />
              </div>

              <div class="form-field">
                <label class="field-label">Payment Terms</label>
                <select
                  v-model="store.draft.payment_term_id"
                  class="field-select"
                  @change="store.saveDraft"
                >
                  <option :value="null">Default (Customer Terms)</option>
                  <option v-for="term in store.paymentTerms" :key="term.id" :value="term.id">
                    {{ term.name || term.term_name || `Term #${term.id}` }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-field">
              <label class="field-label">Shipping / Delivery Address</label>
              <input
                v-model="store.draft.shipping_address"
                type="text"
                class="field-input"
                placeholder="Client delivery address..."
                @change="store.saveDraft"
              />
            </div>

            <div class="form-field">
              <label class="field-label">Customer Order Notes</label>
              <textarea
                v-model="store.draft.customer_notes"
                rows="2"
                class="field-textarea"
                placeholder="Special delivery instructions, contact person, PO number..."
                @change="store.saveDraft"
              ></textarea>
            </div>
          </div>
        </template>
      </div>

      <!-- Drawer Footer: Totals & Submit -->
      <div class="drawer-footer">
        <div class="totals-breakdown">
          <div class="totals-line">
            <span class="totals-label">Subtotal</span>
            <span class="totals-amount font-mono">{{ formatMoney(store.cartSubtotal) }}</span>
          </div>

          <div class="totals-line">
            <span class="totals-label">Estimated Tax</span>
            <span class="totals-amount font-mono">{{ formatMoney(store.cartTaxTotal) }}</span>
          </div>

          <div class="totals-line grand">
            <span class="grand-label">Grand Total</span>
            <span class="grand-amount">{{ formatMoney(store.cartGrandTotal) }}</span>
          </div>
        </div>

        <!-- Exceeded credit limit alert -->
        <div v-if="store.isCreditLimitExceeded" class="credit-limit-alert">
          <span class="material-symbols-outlined">warning</span>
          <span>Order total exceeds available credit limit!</span>
        </div>

        <!-- Submit Button -->
        <div class="footer-actions">
          <button class="btn-cancel" @click="handleClose">
            Continue Browsing
          </button>

          <button
            class="btn-submit-order"
            :disabled="!store.isCartValid || store.isSubmittingOrder"
            @click="handleSubmitOrder"
          >
            <span v-if="store.isSubmittingOrder" class="material-symbols-outlined spin-icon">
              sync
            </span>
            <span v-else class="material-symbols-outlined">
              {{ store.isOnline ? 'cloud_upload' : 'save' }}
            </span>
            <span>
              {{ submitButtonLabel }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'order-submitted'])

const store = useFieldSalesStore()
const { show: toast } = useToast()

const submitButtonLabel = computed(() => {
  if (store.isSubmittingOrder) return 'Submitting...'
  if (store.isOnline) return `Submit & Sync Order (${formatMoney(store.cartGrandTotal)})`
  return `Save to Offline Queue (${formatMoney(store.cartGrandTotal)})`
})

function formatMoney(amount) {
  const num = Number(amount) || 0
  return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function handleClose() {
  emit('close')
}

async function handleClearCart() {
  if (window.confirm('Are you sure you want to clear all items from this order draft?')) {
    await store.clearCart()
    toast('Cart draft cleared', 'info')
  }
}

async function handleSubmitOrder() {
  if (!store.isCartValid) {
    toast('Please select a customer and add valid line items', 'error')
    return
  }

  try {
    const result = await store.submitOrder()
    if (result && result.success) {
      if (result.isOnline) {
        toast('Order submitted and queued for cloud sync!', 'success')
      } else {
        toast('Order saved locally! Will sync automatically when connection is restored.', 'info')
      }
      emit('order-submitted', result.order)
      emit('close')
    }
  } catch (err) {
    toast(`Failed to submit order: ${err.message}`, 'error')
  }
}
</script>

<style scoped>
.drawer-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.drawer-panel {
  width: 100%;
  max-width: 520px;
  height: 100%;
  background: var(--bg-surface);
  box-shadow: -4px 0 25px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  animation: slideInRight 0.25s ease;
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

/* Header */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-box {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--bg-primary-faded, #e6deff);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon-box .material-symbols-outlined {
  font-size: 22px;
}

.header-title-box {
  display: flex;
  flex-direction: column;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.item-count-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
}

.customer-subtext {
  font-size: 12px;
  color: var(--text-muted);
  margin: 2px 0 0 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-clear-cart {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 6px;
  background: none;
  border: 1px solid var(--border-input);
  color: var(--color-error, #dc2626);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.btn-clear-cart .material-symbols-outlined {
  font-size: 15px;
}

.btn-close-drawer {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 6px;
  border-radius: 6px;
}

.btn-close-drawer:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

/* Body */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-cart-state {
  padding: 60px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--text-subtle);
}

.empty-cart-icon {
  font-size: 48px;
  margin-bottom: 10px;
  color: var(--text-muted);
}

.empty-cart-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px 0;
}

.empty-cart-desc {
  font-size: 13px;
  max-width: 300px;
  margin: 0;
}

.section-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-subtle);
  margin-bottom: 8px;
}

/* Cart Line Card */
.cart-line-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.line-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.line-product-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.line-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.line-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.line-sku {
  font-size: 11px;
  color: var(--text-subtle);
}

.contract-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  background: #dbeafe;
  color: #1e40af;
}

.btn-remove-line {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  padding: 4px;
}

.btn-remove-line:hover {
  color: var(--color-error, #dc2626);
}

.btn-remove-line .material-symbols-outlined {
  font-size: 18px;
}

.line-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.qty-stepper-box {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  overflow: hidden;
}

.step-btn {
  width: 32px;
  height: 32px;
  background: var(--bg-surface-low, #f9fafb);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-primary);
}

.step-btn:hover {
  background: var(--bg-surface-hover);
}

.step-btn .material-symbols-outlined {
  font-size: 16px;
}

.qty-input {
  width: 44px;
  height: 32px;
  border: none;
  border-left: 1px solid var(--border-input);
  border-right: 1px solid var(--border-input);
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
}

.unit-price-display {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-edit-toggle, .discount-input-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.unit-rate-label, .discount-label {
  font-size: 10px;
  color: var(--text-muted);
}

.price-override-input, .discount-input {
  width: 60px;
  height: 24px;
  border: 1px solid var(--border-input);
  border-radius: 4px;
  padding: 0 4px;
  font-size: 11px;
  color: var(--text-primary);
  background: var(--bg-surface);
}

.line-total-box {
  text-align: right;
}

.line-total-val {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.line-notes-input {
  width: 100%;
  height: 28px;
  border: 1px dashed var(--border-input);
  border-radius: 6px;
  padding: 0 8px;
  font-size: 11px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
}

.line-notes-input:focus {
  border-color: var(--color-primary);
  border-style: solid;
}

/* Order logistics */
.order-details-form {
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

@media (max-width: 480px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.field-input, .field-select, .field-textarea {
  width: 100%;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 12px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
}

.field-input:focus, .field-select:focus, .field-textarea:focus {
  border-color: var(--color-primary);
}

/* Footer */
.drawer-footer {
  padding: 16px;
  border-top: 1px solid var(--border-default);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.totals-breakdown {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.totals-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-muted);
}

.totals-line.grand {
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px solid var(--border-light);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.grand-amount {
  color: var(--color-primary);
}

.credit-limit-alert {
  padding: 8px 10px;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #991b1b;
}

.credit-limit-alert .material-symbols-outlined {
  font-size: 16px;
  flex-shrink: 0;
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.btn-cancel {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  background: var(--bg-surface-hover);
}

.btn-submit-order {
  flex: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-submit-order:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-submit-order:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-submit-order .material-symbols-outlined {
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

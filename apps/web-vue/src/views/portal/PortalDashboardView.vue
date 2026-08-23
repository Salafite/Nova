<template>
  <div class="portal-dashboard-page" :dir="dir">
    <div class="portal-container">
      <!-- Welcome & Account Header Banner -->
      <div class="dashboard-hero-card">
        <div class="hero-content">
          <div class="hero-badge">
            <span class="material-symbols-outlined">verified</span>
            <span>{{ t('wholesale-portal-badge', 'B2B Wholesale Portal') }}</span>
          </div>
          <h1 class="hero-title">
            {{ t('welcome-back', 'Welcome back') }}, <span class="highlight-company">{{ customerCompanyName }}</span>
          </h1>
          <p class="hero-subtitle">
            {{ t('hero-subtext', 'Manage 24/7 replenishment orders, review contracted pricing, and settle open invoices online.') }}
          </p>

          <!-- Account Meta Tags -->
          <div class="hero-tags-row">
            <div class="hero-tag" v-if="portal.accountSummary?.default_price_list_name">
              <span class="material-symbols-outlined tag-icon">local_offer</span>
              <span>{{ portal.accountSummary.default_price_list_name }}</span>
            </div>
            <div class="hero-tag" v-if="portal.accountSummary?.order_cutoff_time">
              <span class="material-symbols-outlined tag-icon">schedule</span>
              <span>{{ t('daily-cutoff', 'Daily Cutoff') }}: {{ portal.accountSummary.order_cutoff_time.slice(0, 5) }}</span>
            </div>
            <div class="hero-tag" v-if="portal.accountSummary?.min_order_amount > 0">
              <span class="material-symbols-outlined tag-icon">shopping_bag</span>
              <span>{{ t('min-order', 'Min Order') }}: ${{ portal.accountSummary.min_order_amount.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <div class="hero-actions">
          <router-link to="/portal/catalog" class="btn-hero-primary">
            <span class="material-symbols-outlined">add_shopping_cart</span>
            <span>{{ t('order-supplies-now', 'Order Supplies') }}</span>
          </router-link>
          <router-link to="/portal/invoices" class="btn-hero-secondary">
            <span class="material-symbols-outlined">payments</span>
            <span>{{ t('view-all-invoices', 'View Invoices') }}</span>
          </router-link>
        </div>
      </div>

      <!-- KPI Summary Cards Grid (4 Columns) -->
      <div class="dashboard-kpis-grid">
        <!-- KPI 1: Outstanding Balance -->
        <div class="kpi-card kpi-balance" :class="{ 'has-balance': outstandingBalance > 0 }">
          <div class="kpi-top">
            <div class="kpi-icon-box bg-purple">
              <span class="material-symbols-outlined">account_balance_wallet</span>
            </div>
            <button
              v-if="outstandingBalance > 0"
              class="btn-kpi-pay"
              @click="openBalancePaymentModal"
            >
              <span class="material-symbols-outlined">bolt</span>
              <span>{{ t('pay-now', 'Pay Balance') }}</span>
            </button>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">{{ t('outstanding-balance', 'Outstanding Balance') }}</span>
            <div class="kpi-value-row">
              <span class="kpi-value">${{ outstandingBalance.toFixed(2) }}</span>
              <span class="kpi-sub-badge" :class="outstandingBalance > 0 ? 'badge-amber' : 'badge-green'">
                {{ openInvoicesCount }} {{ openInvoicesCount === 1 ? 'invoice due' : 'invoices due' }}
              </span>
            </div>
          </div>
        </div>

        <!-- KPI 2: Credit Limit & Available Credit Gauge -->
        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon-box bg-indigo">
              <span class="material-symbols-outlined">credit_score</span>
            </div>
            <span class="gauge-percent-text" v-if="creditLimit > 0">
              {{ creditUtilizationPercent }}% {{ t('used', 'used') }}
            </span>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">{{ t('available-credit', 'Available Credit') }}</span>
            <div class="kpi-value-row">
              <span class="kpi-value">${{ availableCredit.toFixed(2) }}</span>
              <span class="kpi-limit-lbl" v-if="creditLimit > 0">of ${{ creditLimit.toFixed(2) }} limit</span>
            </div>
            <!-- Credit Utilization Progress Bar -->
            <div class="credit-gauge-track" v-if="creditLimit > 0">
              <div
                class="credit-gauge-fill"
                :class="{ 'fill-warning': creditUtilizationPercent > 80, 'fill-danger': creditUtilizationPercent >= 100 }"
                :style="{ width: `${Math.min(100, creditUtilizationPercent)}%` }"
              ></div>
            </div>
          </div>
        </div>

        <!-- KPI 3: Cutoff & Next Delivery Window -->
        <div class="kpi-card" :class="{ 'kpi-cutoff-passed': portal.isPastCutoff }">
          <div class="kpi-top">
            <div class="kpi-icon-box" :class="portal.isPastCutoff ? 'bg-amber' : 'bg-green'">
              <span class="material-symbols-outlined">{{ portal.isPastCutoff ? 'schedule' : 'local_shipping' }}</span>
            </div>
            <span class="kpi-sub-badge" :class="portal.isPastCutoff ? 'badge-amber' : 'badge-green'">
              {{ portal.isPastCutoff ? 'Cutoff Passed' : 'Next-Day Ready' }}
            </span>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">{{ t('next-delivery-date', 'Next Scheduled Delivery') }}</span>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ portal.nextDeliveryDate || t('tomorrow', 'Next Day') }}</span>
            </div>
            <span class="kpi-caption">
              {{ portal.isPastCutoff ? 'D+2 fulfillment applied' : `Order by ${portal.cutoffStatus?.cutoff_time || '22:00'} for D+1` }}
            </span>
          </div>
        </div>

        <!-- KPI 4: Active Replenishment Orders -->
        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon-box bg-blue">
              <span class="material-symbols-outlined">receipt_long</span>
            </div>
            <router-link to="/portal/orders" class="kpi-link">
              <span>{{ t('view-all', 'View All') }}</span>
              <span class="material-symbols-outlined">arrow_forward</span>
            </router-link>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">{{ t('active-orders', 'Orders in Fulfillment') }}</span>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ activeOrdersCount }}</span>
              <span class="kpi-sub-badge badge-blue">{{ totalOrdersCount }} {{ t('total', 'total') }}</span>
            </div>
            <span class="kpi-caption">{{ deliveredOrdersCount }} completed shipments</span>
          </div>
        </div>
      </div>

      <!-- Dashboard Main Two-Column Layout -->
      <div class="dashboard-main-grid">
        <!-- Left Column: Recent Orders & Quick Reorder -->
        <div class="dashboard-card">
          <div class="card-header-row">
            <div class="card-title-wrap">
              <span class="material-symbols-outlined card-header-icon text-indigo">repeat</span>
              <h3>{{ t('recent-orders-reorder', 'Recent Orders & 1-Click Reorder') }}</h3>
            </div>
            <router-link to="/portal/orders" class="card-action-link">
              <span>{{ t('all-orders', 'All Orders') }}</span>
              <span class="material-symbols-outlined">arrow_forward</span>
            </router-link>
          </div>

          <div v-if="portal.ordersLoading" class="mini-loading-list">
            <div v-for="i in 3" :key="i" class="skeleton-mini-row"></div>
          </div>

          <div v-else-if="!recentOrders || recentOrders.length === 0" class="mini-empty-state">
            <span class="material-symbols-outlined empty-icon">receipt_long</span>
            <p>{{ t('no-orders-yet', 'No previous replenishment orders.') }}</p>
            <router-link to="/portal/catalog" class="btn-sm-primary">
              <span class="material-symbols-outlined">add_shopping_cart</span>
              <span>{{ t('place-first-order', 'Place First Order') }}</span>
            </router-link>
          </div>

          <div v-else class="recent-orders-list">
            <div v-for="order in recentOrders" :key="order.id" class="recent-order-item">
              <div class="order-item-left">
                <div class="order-main-row">
                  <router-link :to="`/portal/orders/${order.id}`" class="order-link-code">
                    #{{ order.order_number }}
                  </router-link>
                  <span class="status-badge" :class="getStatusBadgeClass(order.status)">
                    {{ order.status }}
                  </span>
                </div>
                <div class="order-sub-row">
                  <span class="order-date-text">{{ formatDate(order.order_date) }}</span>
                  <span class="dot-separator">•</span>
                  <span class="order-lines-count">{{ order.lines?.length || 0 }} {{ (order.lines?.length === 1) ? 'item' : 'items' }}</span>
                  <span class="dot-separator">•</span>
                  <span class="order-amount-text">${{ Number(order.grand_total || order.subtotal || 0).toFixed(2) }}</span>
                </div>
              </div>

              <div class="order-item-actions">
                <button
                  v-if="portal.allowReorders && order.status !== 'Cancelled'"
                  class="btn-mini-reorder"
                  @click="openReorderModal(order)"
                  :title="t('1-click-reorder', '1-Click Reorder')"
                >
                  <span class="material-symbols-outlined">repeat</span>
                  <span>{{ t('reorder', 'Reorder') }}</span>
                </button>
                <router-link :to="`/portal/orders/${order.id}`" class="btn-mini-icon" title="View details">
                  <span class="material-symbols-outlined">chevron_right</span>
                </router-link>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Open Invoices & Online Settlement -->
        <div class="dashboard-card">
          <div class="card-header-row">
            <div class="card-title-wrap">
              <span class="material-symbols-outlined card-header-icon text-amber">receipt</span>
              <h3>{{ t('open-invoices-settlement', 'Open Invoices & Settlement') }}</h3>
            </div>
            <router-link to="/portal/invoices" class="card-action-link">
              <span>{{ t('all-invoices', 'All Invoices') }}</span>
              <span class="material-symbols-outlined">arrow_forward</span>
            </router-link>
          </div>

          <div v-if="portal.invoicesLoading" class="mini-loading-list">
            <div v-for="i in 3" :key="i" class="skeleton-mini-row"></div>
          </div>

          <div v-else-if="!unpaidInvoices || unpaidInvoices.length === 0" class="mini-empty-state">
            <span class="material-symbols-outlined empty-icon text-green">check_circle</span>
            <p class="font-semibold text-white">{{ t('all-caught-up', 'All Caught Up!') }}</p>
            <span class="text-secondary text-xs">{{ t('no-open-invoices-desc', 'You have no outstanding invoice balances due.') }}</span>
          </div>

          <div v-else class="recent-invoices-list">
            <!-- Full Settlement Banner -->
            <div class="settle-all-banner" v-if="outstandingBalance > 0">
              <div class="banner-left">
                <span class="banner-lbl">{{ t('total-open-balance', 'Total Balance Due') }}</span>
                <span class="banner-amt">${{ outstandingBalance.toFixed(2) }}</span>
              </div>
              <button class="btn-settle-banner" @click="openBalancePaymentModal">
                <span class="material-symbols-outlined">bolt</span>
                <span>{{ t('settle-all-online', 'Settle All via Stripe') }}</span>
              </button>
            </div>

            <div v-for="inv in unpaidInvoices.slice(0, 4)" :key="inv.id" class="recent-invoice-item">
              <div class="invoice-item-left">
                <div class="invoice-main-row">
                  <span class="invoice-code font-mono">#{{ inv.invoice_number }}</span>
                  <span class="status-badge" :class="getInvoiceBadgeClass(inv.status)">
                    {{ inv.status }}
                  </span>
                </div>
                <div class="invoice-sub-row">
                  <span class="invoice-date-text">{{ t('due', 'Due') }}: {{ formatDate(inv.due_date) }}</span>
                  <span class="dot-separator">•</span>
                  <span class="invoice-balance-text">${{ Number(inv.balance_due ?? inv.total_amount).toFixed(2) }} due</span>
                </div>
              </div>

              <div class="invoice-item-actions">
                <button
                  class="btn-mini-pdf"
                  @click="portal.downloadInvoicePdf(inv.id)"
                  :title="t('download-pdf', 'Download PDF')"
                >
                  <span class="material-symbols-outlined">picture_as_pdf</span>
                </button>
                <button
                  class="btn-mini-pay"
                  @click="openInvoicePaymentModal(inv)"
                  :title="t('pay-with-card-ach', 'Pay with Card or ACH')"
                >
                  <span class="material-symbols-outlined">credit_card</span>
                  <span>{{ t('pay', 'Pay') }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Supply Catalog Highlight Carousel / Grid -->
      <div class="dashboard-card mt-6" v-if="portal.catalog && portal.catalog.length > 0">
        <div class="card-header-row">
          <div class="card-title-wrap">
            <span class="material-symbols-outlined card-header-icon text-indigo">inventory_2</span>
            <h3>{{ t('contracted-supplies-highlight', 'Your Contracted Replenishment Supplies') }}</h3>
          </div>
          <router-link to="/portal/catalog" class="card-action-link">
            <span>{{ t('browse-full-catalog', 'Browse Full Catalog') }}</span>
            <span class="material-symbols-outlined">arrow_forward</span>
          </router-link>
        </div>

        <div class="supplies-carousel-grid">
          <div
            v-for="product in portal.catalog.slice(0, 4)"
            :key="product.id"
            class="mini-product-card"
          >
            <div class="product-top-row">
              <span class="product-code-tag">{{ product.product_code }}</span>
              <span class="contract-badge-pill" v-if="product.is_contracted">
                <span class="material-symbols-outlined">verified</span> Contracted
              </span>
            </div>
            <h4 class="product-name-heading" :title="product.product_name">{{ product.product_name }}</h4>
            <div class="product-price-row">
              <div class="price-box">
                <span class="price-val">${{ Number(product.contracted_price || product.base_price).toFixed(2) }}</span>
                <span class="price-uom" v-if="product.uom_name">/ {{ product.uom_name }}</span>
              </div>
              <button
                class="btn-quick-add"
                @click="quickAddToCart(product)"
                :disabled="!product.is_in_stock"
              >
                <span class="material-symbols-outlined">add_shopping_cart</span>
                <span>{{ t('add', 'Add') }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Settle Single Invoice Modal -->
    <div v-if="showInvoicePayModal && selectedInvoiceForPay" class="modal-overlay" @click.self="closeInvoicePayModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-indigo">
              <span class="material-symbols-outlined">payments</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('pay-invoice-title', 'Settle Invoice Online') }}</h3>
              <p class="modal-subtitle">Invoice #{{ selectedInvoiceForPay.invoice_number }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeInvoicePayModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="payment-amount-card">
            <span class="amount-label">{{ t('amount-to-pay', 'Total Amount Due') }}</span>
            <span class="amount-value">${{ Number(selectedInvoiceForPay.balance_due ?? selectedInvoiceForPay.total_amount).toFixed(2) }}</span>
          </div>

          <div class="payment-methods-selector">
            <label class="form-label">{{ t('select-payment-method', 'Payment Method Supported') }}</label>
            <div class="methods-badges">
              <div class="method-badge">
                <span class="material-symbols-outlined">credit_card</span>
                <span>Credit / Debit Card (Instant)</span>
              </div>
              <div class="method-badge">
                <span class="material-symbols-outlined">account_balance</span>
                <span>ACH Bank Transfer (Direct Debit)</span>
              </div>
            </div>
          </div>

          <div class="stripe-trust-notice">
            <span class="material-symbols-outlined">lock</span>
            <span>Secured by Stripe 256-bit encrypted checkout. Automatic AR reconciliation upon payment.</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeInvoicePayModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="paymentRedirecting" @click="proceedInvoiceStripeCheckout">
            <span class="material-symbols-outlined" v-if="!paymentRedirecting">open_in_new</span>
            <span class="spinner" v-else></span>
            <span>{{ paymentRedirecting ? t('redirecting-to-stripe', 'Redirecting to Stripe...') : t('proceed-to-stripe', 'Proceed to Stripe Checkout') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Settle Full Balance Modal -->
    <div v-if="showBalancePayModal" class="modal-overlay" @click.self="closeBalancePayModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-purple">
              <span class="material-symbols-outlined">bolt</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('settle-full-balance', 'Settle Account Balance') }}</h3>
              <p class="modal-subtitle">{{ customerCompanyName }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeBalancePayModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="payment-amount-card">
            <span class="amount-label">{{ t('total-outstanding-balance', 'Total Outstanding Balance') }}</span>
            <span class="amount-value">${{ outstandingBalance.toFixed(2) }}</span>
          </div>

          <p class="text-secondary text-xs">
            This will create a Stripe checkout session for your full outstanding balance across {{ openInvoicesCount }} open invoice(s). Upon completion, payment records and general ledger reconciliations will be automatically generated.
          </p>

          <div class="stripe-trust-notice">
            <span class="material-symbols-outlined">lock</span>
            <span>Supports Credit Card & ACH Bank Transfer via Stripe.</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeBalancePayModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="paymentRedirecting" @click="proceedBalanceStripeCheckout">
            <span class="material-symbols-outlined" v-if="!paymentRedirecting">open_in_new</span>
            <span class="spinner" v-else></span>
            <span>{{ paymentRedirecting ? t('redirecting-to-stripe', 'Redirecting to Stripe...') : t('pay-balance-now', 'Pay Balance with Stripe') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 1-Click Reorder Modal -->
    <div v-if="showReorderModal && selectedOrderForReorder" class="modal-overlay" @click.self="closeReorderModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-indigo">
              <span class="material-symbols-outlined">repeat</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('reorder-supplies-title', '1-Click Reorder Standard Supplies') }}</h3>
              <p class="modal-subtitle">Order #{{ selectedOrderForReorder.order_number }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeReorderModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="reorder-total-banner">
            <span>{{ t('estimated-subtotal', 'Estimated Subtotal') }}:</span>
            <span class="total-val">${{ Number(selectedOrderForReorder.grand_total || selectedOrderForReorder.subtotal || 0).toFixed(2) }}</span>
          </div>

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
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeReorderModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="reorderSubmitting" @click="executeReorder">
            <span class="material-symbols-outlined" v-if="!reorderSubmitting">repeat</span>
            <span class="spinner" v-else></span>
            <span>{{ reorderSubmitting ? t('submitting', 'Submitting...') : t('confirm-reorder', 'Confirm Reorder') }}</span>
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
import { useAuthStore } from '../../stores/auth.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const router = useRouter()
const portal = usePortalStore()
const auth = useAuthStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

// Modals State
const showInvoicePayModal = ref(false)
const selectedInvoiceForPay = ref(null)
const showBalancePayModal = ref(false)
const showReorderModal = ref(false)
const selectedOrderForReorder = ref(null)
const reorderDeliveryDate = ref('')
const reorderSubmitting = ref(false)
const paymentRedirecting = ref(false)

const todayDate = computed(() => new Date().toISOString().split('T')[0])

// Customer Info
const customerCompanyName = computed(() => {
  if (portal.accountSummary?.company_name) return portal.accountSummary.company_name
  if (portal.accountSummary?.customer_name) return portal.accountSummary.customer_name
  if (auth.user?.full_name) return auth.user.full_name
  return 'Valued Wholesale Customer'
})

// Financial Metrics
const outstandingBalance = computed(() => {
  return portal.totalUnpaidBalance
})

const creditLimit = computed(() => {
  return Number(portal.accountSummary?.credit_limit || 0)
})

const availableCredit = computed(() => {
  if (portal.accountSummary?.available_credit !== undefined) {
    return Number(portal.accountSummary.available_credit) || 0
  }
  return Math.max(0, creditLimit.value - outstandingBalance.value)
})

const creditUtilizationPercent = computed(() => {
  if (creditLimit.value <= 0) return 0
  return Math.min(100, Math.round((outstandingBalance.value / creditLimit.value) * 100))
})

// Orders & Invoices Lists
const recentOrders = computed(() => {
  return (portal.orders || []).slice(0, 5)
})

const activeOrdersCount = computed(() => {
  return (portal.orders || []).filter(o => ['Draft', 'Pending', 'Confirmed', 'Processing', 'Shipped'].includes(o.status)).length
})

const totalOrdersCount = computed(() => {
  return portal.ordersTotal || portal.orders?.length || 0
})

const deliveredOrdersCount = computed(() => {
  return (portal.orders || []).filter(o => o.status === 'Delivered').length
})

const unpaidInvoices = computed(() => {
  return portal.unpaidInvoices || []
})

const openInvoicesCount = computed(() => {
  return unpaidInvoices.value.length
})

// Modals & Handlers
function openInvoicePaymentModal(inv) {
  selectedInvoiceForPay.value = inv
  showInvoicePayModal.value = true
}

function closeInvoicePayModal() {
  showInvoicePayModal.value = false
  selectedInvoiceForPay.value = null
  paymentRedirecting.value = false
}

async function proceedInvoiceStripeCheckout() {
  if (!selectedInvoiceForPay.value) return
  paymentRedirecting.value = true
  try {
    const session = await portal.createInvoiceCheckoutSession(selectedInvoiceForPay.value.id, {
      paymentMethodTypes: ['card', 'us_bank_account'],
    })
    if (session && session.checkout_url) {
      window.location.href = session.checkout_url
    }
  } catch (err) {
    showToast(err.message || 'Failed to initialize Stripe checkout', 'error', 4000)
    paymentRedirecting.value = false
  }
}

function openBalancePaymentModal() {
  showBalancePayModal.value = true
}

function closeBalancePayModal() {
  showBalancePayModal.value = false
  paymentRedirecting.value = false
}

async function proceedBalanceStripeCheckout() {
  if (outstandingBalance.value <= 0) return
  paymentRedirecting.value = true
  try {
    const session = await portal.createBalanceCheckoutSession(outstandingBalance.value, {
      paymentMethodTypes: ['card', 'us_bank_account'],
    })
    if (session && session.checkout_url) {
      window.location.href = session.checkout_url
    }
  } catch (err) {
    showToast(err.message || 'Failed to initialize Stripe settlement', 'error', 4000)
    paymentRedirecting.value = false
  }
}

function openReorderModal(order) {
  selectedOrderForReorder.value = order
  reorderDeliveryDate.value = portal.nextDeliveryDate || todayDate.value
  showReorderModal.value = true
}

function closeReorderModal() {
  showReorderModal.value = false
  selectedOrderForReorder.value = null
  reorderSubmitting.value = false
}

async function executeReorder() {
  if (!selectedOrderForReorder.value) return
  reorderSubmitting.value = true
  try {
    const result = await portal.reorderPastOrder(selectedOrderForReorder.value.id, {
      requested_delivery_date: reorderDeliveryDate.value || null,
      status: 'Confirmed',
    })
    if (result) {
      showToast(`Reorder #${result.order_number} placed successfully!`, 'success', 4000)
      closeReorderModal()
      router.push(`/portal/orders/${result.id}`)
    }
  } catch (err) {
    showToast(err.message || 'Failed to place reorder', 'error', 4000)
  } finally {
    reorderSubmitting.value = false
  }
}

function quickAddToCart(product) {
  portal.addToCart(product, 1)
  showToast(`Added ${product.product_name} to replenishment cart`, 'success', 2000)
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

function getInvoiceBadgeClass(status) {
  const map = {
    Paid: 'status-paid',
    Unpaid: 'status-pending',
    'Partially Paid': 'status-confirmed',
    Overdue: 'status-cancelled',
    Cancelled: 'status-draft',
  }
  return map[status] || 'status-default'
}

onMounted(() => {
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
  portal.fetchOrders({ page: 1, limit: 5 })
  portal.fetchInvoices({ page: 1, limit: 10 })
  portal.fetchCatalog({ page: 1, limit: 8 })
})
</script>

<style scoped>
.portal-dashboard-page {
  width: 100%;
}

.portal-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Hero Welcome Card */
.dashboard-hero-card {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.08) 50%, var(--bg-surface, #1a1a2e) 100%);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  padding: 28px 32px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

@media (max-width: 900px) {
  .dashboard-hero-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 10px;
}

.hero-badge .material-symbols-outlined {
  font-size: 14px;
}

.hero-title {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary, #fff);
  letter-spacing: -0.5px;
  margin: 0 0 6px;
}

.highlight-company {
  color: #818cf8;
}

.hero-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  margin: 0 0 16px;
  max-width: 680px;
}

.hero-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
}

.tag-icon {
  font-size: 15px;
  color: #818cf8;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 200px;
}

.btn-hero-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: all 0.2s ease;
}

.btn-hero-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
}

.btn-hero-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.btn-hero-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: #6366f1;
}

/* KPIs Grid */
.dashboard-kpis-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1024px) {
  .dashboard-kpis-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .dashboard-kpis-grid {
    grid-template-columns: 1fr;
  }
}

.kpi-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
}

.kpi-balance.has-balance {
  border-left: 4px solid #f59e0b;
}

.kpi-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-icon-box {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon-box .material-symbols-outlined {
  font-size: 22px;
}

.bg-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.bg-indigo { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.bg-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.bg-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.bg-blue { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }

.btn-kpi-pay {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  border: none;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
}

.btn-kpi-pay .material-symbols-outlined {
  font-size: 14px;
}

.gauge-percent-text {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary, #94a3b8);
}

.kpi-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #818cf8;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.kpi-link .material-symbols-outlined {
  font-size: 14px;
}

.kpi-body {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  margin-bottom: 4px;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary, #fff);
  letter-spacing: -0.5px;
}

.kpi-sub-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.kpi-limit-lbl {
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.kpi-caption {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  margin-top: 4px;
}

.credit-gauge-track {
  width: 100%;
  height: 5px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
}

.credit-gauge-fill {
  height: 100%;
  background: #6366f1;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.credit-gauge-fill.fill-warning { background: #f59e0b; }
.credit-gauge-fill.fill-danger { background: #ef4444; }

.badge-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.badge-blue { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }

/* Dashboard Main Two Column Grid */
.dashboard-main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .dashboard-main-grid {
    grid-template-columns: 1fr;
  }
}

.dashboard-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  margin-bottom: 14px;
}

.card-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-title-wrap h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
}

.card-header-icon {
  font-size: 20px;
}

.card-action-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #818cf8;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.card-action-link .material-symbols-outlined {
  font-size: 14px;
}

/* Recent Orders List */
.recent-orders-list, .recent-invoices-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-order-item, .recent-invoice-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.15s ease;
}

.recent-order-item:hover, .recent-invoice-item:hover {
  border-color: rgba(99, 102, 241, 0.25);
  background: rgba(255, 255, 255, 0.02);
}

.order-main-row, .invoice-main-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.order-link-code {
  color: #818cf8;
  text-decoration: none;
  font-weight: 700;
  font-family: monospace;
  font-size: 13px;
}

.order-link-code:hover {
  text-decoration: underline;
}

.invoice-code {
  color: var(--text-primary, #fff);
  font-weight: 700;
  font-size: 13px;
}

.order-sub-row, .invoice-sub-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
}

.dot-separator {
  color: var(--text-muted, #64748b);
}

.order-amount-text, .invoice-balance-text {
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.order-item-actions, .invoice-item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-mini-reorder {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.btn-mini-reorder:hover {
  background: #6366f1;
  color: #fff;
}

.btn-mini-reorder .material-symbols-outlined {
  font-size: 14px;
}

.btn-mini-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #64748b);
  text-decoration: none;
  padding: 4px;
  border-radius: 4px;
}

.btn-mini-icon:hover {
  color: var(--text-primary, #fff);
}

.btn-mini-pdf {
  background: none;
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  padding: 5px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.btn-mini-pdf:hover {
  color: #f87171;
  border-color: #f87171;
}

.btn-mini-pdf .material-symbols-outlined {
  font-size: 16px;
}

.btn-mini-pay {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 6px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  border: none;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.btn-mini-pay:hover {
  background: #16a34a;
}

.btn-mini-pay .material-symbols-outlined {
  font-size: 14px;
}

/* Settle All Banner */
.settle-all-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(217, 119, 6, 0.05) 100%);
  border: 1px solid rgba(245, 158, 11, 0.25);
  margin-bottom: 6px;
}

.banner-left {
  display: flex;
  flex-direction: column;
}

.banner-lbl {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.5px;
}

.banner-amt {
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
}

.btn-settle-banner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  background: #f59e0b;
  color: #000;
  border: none;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-settle-banner:hover {
  background: #fbbf24;
}

.btn-settle-banner .material-symbols-outlined {
  font-size: 16px;
}

/* Supplies Carousel Grid */
.supplies-carousel-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 900px) {
  .supplies-carousel-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .supplies-carousel-grid {
    grid-template-columns: 1fr;
  }
}

.mini-product-card {
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
}

.product-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.product-code-tag {
  font-size: 10px;
  font-family: monospace;
  color: var(--text-muted, #64748b);
}

.contract-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  font-weight: 700;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  padding: 1px 6px;
  border-radius: 10px;
}

.contract-badge-pill .material-symbols-outlined {
  font-size: 11px;
}

.product-name-heading {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-price-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.price-val {
  font-size: 14px;
  font-weight: 800;
  color: #a5b4fc;
}

.price-uom {
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.btn-quick-add {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.btn-quick-add:hover {
  background: #6366f1;
  border-color: #6366f1;
}

.btn-quick-add .material-symbols-outlined {
  font-size: 14px;
}

/* Status Badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
}

.status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.status-confirmed, .status-processing { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.status-shipped { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
.status-delivered, .status-paid { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-cancelled { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.status-draft { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.status-default { background: rgba(255, 255, 255, 0.08); color: #e2e8f0; }

/* Empty & Loading */
.mini-empty-state {
  text-align: center;
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.mini-empty-state .empty-icon {
  font-size: 32px;
  color: var(--text-muted, #64748b);
}

.mini-empty-state p {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  margin: 0;
}

.btn-sm-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  background: #6366f1;
  color: #fff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  margin-top: 6px;
}

.skeleton-mini-row {
  height: 52px;
  border-radius: 8px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.02) 25%, rgba(255, 255, 255, 0.06) 50%, rgba(255, 255, 255, 0.02) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin-bottom: 8px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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
  max-width: 540px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}

.modal-card-sm {
  max-width: 440px;
}

.modal-header {
  padding: 18px 24px;
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
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 16px;
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
  display: flex;
  align-items: center;
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.payment-amount-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px;
  border-radius: 12px;
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
}

.amount-label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.amount-value {
  font-size: 30px;
  font-weight: 800;
  color: #4ade80;
  letter-spacing: -0.5px;
}

.payment-methods-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.methods-badges {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.method-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-default, #2a2a4a);
  font-size: 12px;
  color: var(--text-primary, #fff);
}

.method-badge .material-symbols-outlined {
  color: #818cf8;
  font-size: 18px;
}

.stripe-trust-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
}

.stripe-trust-notice .material-symbols-outlined {
  font-size: 16px;
  color: #818cf8;
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
}

.total-val {
  font-size: 18px;
  font-weight: 700;
  color: #a5b4fc;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-default, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary, .btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-primary { background: #6366f1; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #4f46e5; }
.btn-outline { background: transparent; border: 1px solid var(--border-default, #2a2a4a); color: var(--text-secondary, #94a3b8); }
.btn-outline:hover { background: rgba(255, 255, 255, 0.05); }

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
</style>

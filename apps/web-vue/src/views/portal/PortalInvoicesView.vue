<template>
  <div class="portal-invoices-page" :dir="dir">
    <div class="portal-container">
      <!-- Page Header -->
      <div class="page-header-row">
        <div>
          <h1 class="page-title">{{ t('portal-invoices-title', 'Invoices & Online Settlement') }}</h1>
          <p class="page-subtitle">{{ t('portal-invoices-subtitle', 'Download official PDF invoices and settle open balances online via Stripe Credit Card or ACH.') }}</p>
        </div>
        <div class="header-actions" v-if="portal.totalUnpaidBalance > 0">
          <button class="btn-pay-balance-hero" @click="openBalancePayModal">
            <span class="material-symbols-outlined">bolt</span>
            <span>{{ t('settle-full-balance', 'Settle Full Balance') }} (${{ portal.totalUnpaidBalance.toFixed(2) }})</span>
          </button>
        </div>
      </div>

      <!-- Financial Metrics Summary Grid -->
      <div class="invoices-metrics-grid">
        <!-- Metric 1: Total Outstanding Balance -->
        <div class="metric-card" :class="{ 'has-open-balance': portal.totalUnpaidBalance > 0 }">
          <div class="metric-icon-box bg-purple">
            <span class="material-symbols-outlined">account_balance_wallet</span>
          </div>
          <div class="metric-details">
            <span class="metric-label">{{ t('total-balance-due', 'Total Balance Due') }}</span>
            <div class="metric-value-row">
              <span class="metric-value font-bold">${{ portal.totalUnpaidBalance.toFixed(2) }}</span>
              <span class="badge" :class="portal.totalUnpaidBalance > 0 ? 'badge-amber' : 'badge-green'">
                {{ openInvoicesCount }} {{ openInvoicesCount === 1 ? 'open invoice' : 'open invoices' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Metric 2: Paid Invoices Total -->
        <div class="metric-card">
          <div class="metric-icon-box bg-green">
            <span class="material-symbols-outlined">check_circle</span>
          </div>
          <div class="metric-details">
            <span class="metric-label">{{ t('settled-invoices', 'Settled Invoices') }}</span>
            <div class="metric-value-row">
              <span class="metric-value font-bold">{{ paidInvoicesCount }}</span>
              <span class="badge badge-green">{{ t('reconciled', 'Auto-Reconciled') }}</span>
            </div>
          </div>
        </div>

        <!-- Metric 3: Supported Stripe Payment Rails -->
        <div class="metric-card">
          <div class="metric-icon-box bg-indigo">
            <span class="material-symbols-outlined">credit_card</span>
          </div>
          <div class="metric-details">
            <span class="metric-label">{{ t('accepted-payment-rails', 'Payment Methods') }}</span>
            <div class="payment-rails-list">
              <span class="rail-chip">Visa / Mastercard / Amex</span>
              <span class="rail-chip font-bold">ACH Direct Debit</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Filter Tabs & Search Bar -->
      <div class="invoices-filter-card">
        <div class="status-tabs-row">
          <button
            class="status-tab-btn"
            :class="{ active: selectedFilter === 'all' }"
            @click="setFilter('all')"
          >
            <span>{{ t('all-invoices', 'All Invoices') }}</span>
            <span class="tab-count-badge">{{ portal.invoicesTotal || portal.invoices.length }}</span>
          </button>
          <button
            class="status-tab-btn"
            :class="{ active: selectedFilter === 'unpaid' }"
            @click="setFilter('unpaid')"
          >
            <span class="status-dot dot-amber"></span>
            <span>{{ t('unpaid-due', 'Unpaid / Due') }}</span>
            <span class="tab-count-badge" v-if="openInvoicesCount > 0">{{ openInvoicesCount }}</span>
          </button>
          <button
            class="status-tab-btn"
            :class="{ active: selectedFilter === 'paid' }"
            @click="setFilter('paid')"
          >
            <span class="status-dot dot-green"></span>
            <span>{{ t('paid-settled', 'Paid / Settled') }}</span>
            <span class="tab-count-badge" v-if="paidInvoicesCount > 0">{{ paidInvoicesCount }}</span>
          </button>
        </div>

        <div class="filter-controls-row">
          <div class="search-input-wrap">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              type="text"
              v-model="searchQuery"
              :placeholder="t('search-invoices-placeholder', 'Search by invoice #, order #, or date...')"
              class="filter-search-input"
            />
            <button v-if="searchQuery" class="clear-search-btn" @click="searchQuery = ''">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <button class="btn-refresh" @click="reloadInvoices">
            <span class="material-symbols-outlined">refresh</span>
            <span>{{ t('refresh', 'Refresh') }}</span>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portal.invoicesLoading" class="invoices-loading-state">
        <div v-for="i in 4" :key="i" class="invoice-skeleton-row"></div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.invoicesError" class="invoices-error-card">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('invoices-error-title', 'Unable to Load Invoices') }}</h3>
        <p>{{ portal.invoicesError }}</p>
        <button class="btn-primary" @click="reloadInvoices">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('retry', 'Retry') }}
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredInvoices.length === 0" class="invoices-empty-card">
        <div class="empty-icon-wrap">
          <span class="material-symbols-outlined">receipt</span>
        </div>
        <h3>{{ t('no-invoices-found', 'No Invoices Found') }}</h3>
        <p>{{ t('no-invoices-desc', 'There are no invoices matching your current filter.') }}</p>
      </div>

      <!-- Invoices Table -->
      <div v-else class="invoices-table-wrapper">
        <table class="invoices-table">
          <thead>
            <tr>
              <th>{{ t('invoice-number', 'Invoice #') }}</th>
              <th>{{ t('issue-date', 'Issue Date') }}</th>
              <th>{{ t('due-date', 'Due Date') }}</th>
              <th>{{ t('sales-order', 'Sales Order') }}</th>
              <th class="text-right">{{ t('invoice-amount', 'Total Amount') }}</th>
              <th class="text-right">{{ t('balance-due', 'Balance Due') }}</th>
              <th class="text-center">{{ t('payment-status', 'Payment Status') }}</th>
              <th class="text-right">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in filteredInvoices" :key="inv.id" class="invoice-row">
              <!-- Invoice Number & PDF Link -->
              <td class="cell-inv-num">
                <div class="inv-num-cluster">
                  <span class="inv-code font-mono">{{ inv.invoice_number }}</span>
                </div>
              </td>

              <!-- Issue Date -->
              <td class="cell-date">
                {{ formatDate(inv.issue_date || inv.created_at) }}
              </td>

              <!-- Due Date with Overdue Indicator -->
              <td class="cell-due-date">
                <div class="due-date-box" :class="{ 'text-danger': isOverdue(inv) }">
                  <span>{{ formatDate(inv.due_date) }}</span>
                  <span v-if="isOverdue(inv)" class="overdue-tag">{{ t('overdue', 'Overdue') }}</span>
                </div>
              </td>

              <!-- Linked Sales Order -->
              <td class="cell-order">
                <router-link
                  v-if="inv.sales_order_id"
                  :to="`/portal/orders/${inv.sales_order_id}`"
                  class="order-link font-mono"
                >
                  #{{ inv.sales_order_number || inv.sales_order_id }}
                </router-link>
                <span v-else class="text-muted">-</span>
              </td>

              <!-- Total Amount -->
              <td class="cell-amount text-right font-semibold">
                ${{ (Number(inv.total_amount) || 0).toFixed(2) }}
              </td>

              <!-- Balance Due -->
              <td class="cell-balance text-right">
                <span
                  class="balance-val font-bold"
                  :class="Number(inv.balance_due ?? inv.total_amount) > 0 ? 'text-amber' : 'text-green'"
                >
                  ${{ (Number(inv.balance_due ?? (inv.status === 'Paid' ? 0 : inv.total_amount))).toFixed(2) }}
                </span>
              </td>

              <!-- Payment Status Badge -->
              <td class="cell-status text-center">
                <span class="status-badge" :class="getStatusBadgeClass(inv.status)">
                  <span class="material-symbols-outlined status-icon">{{ getStatusIcon(inv.status) }}</span>
                  <span>{{ inv.status }}</span>
                </span>
              </td>

              <!-- Actions Cluster -->
              <td class="cell-actions text-right">
                <div class="actions-cluster">
                  <!-- Download PDF Button -->
                  <button
                    class="btn-action-pdf"
                    @click="handleDownloadPdf(inv)"
                    :title="t('download-pdf-invoice', 'Download Printable PDF Invoice')"
                  >
                    <span class="material-symbols-outlined">picture_as_pdf</span>
                    <span class="action-text">PDF</span>
                  </button>

                  <!-- Pay Now with Stripe Button (if unpaid) -->
                  <button
                    v-if="inv.status !== 'Paid' && inv.status !== 'Cancelled'"
                    class="btn-action-pay"
                    @click="openInvoicePayModal(inv)"
                    :title="t('pay-invoice-stripe', 'Pay online via Credit Card or ACH')"
                  >
                    <span class="material-symbols-outlined">credit_card</span>
                    <span>{{ t('pay-now', 'Pay Now') }}</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Bar -->
      <div class="invoices-pagination" v-if="portal.invoicesTotal > portal.invoicesLimit">
        <span class="pagination-info">
          {{ t('showing-invoices', 'Showing') }} {{ ((portal.invoicesPage - 1) * portal.invoicesLimit) + 1 }} -
          {{ Math.min(portal.invoicesPage * portal.invoicesLimit, portal.invoicesTotal) }} {{ t('of', 'of') }} {{ portal.invoicesTotal }}
        </span>
        <div class="pagination-buttons">
          <button
            class="page-nav-btn"
            :disabled="portal.invoicesPage <= 1"
            @click="changePage(portal.invoicesPage - 1)"
          >
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <span class="current-page-pill">{{ portal.invoicesPage }}</span>
          <button
            class="page-nav-btn"
            :disabled="portal.invoicesPage * portal.invoicesLimit >= portal.invoicesTotal"
            @click="changePage(portal.invoicesPage + 1)"
          >
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Pay Individual Invoice Modal -->
    <div v-if="showInvoicePayModal && selectedInvoiceForPay" class="modal-overlay" @click.self="closeInvoicePayModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-indigo">
              <span class="material-symbols-outlined">payments</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('pay-invoice-online', 'Settle Invoice Online') }}</h3>
              <p class="modal-subtitle">Invoice #{{ selectedInvoiceForPay.invoice_number }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeInvoicePayModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="payment-amount-card">
            <span class="amount-label">{{ t('amount-due', 'Balance Due') }}</span>
            <span class="amount-val">${{ (Number(selectedInvoiceForPay.balance_due ?? selectedInvoiceForPay.total_amount)).toFixed(2) }}</span>
            <span class="amount-meta">Invoice Total: ${{ Number(selectedInvoiceForPay.total_amount).toFixed(2) }}</span>
          </div>

          <div class="payment-rails-options">
            <label class="section-label">{{ t('accepted-payment-options', 'Supported Payment Methods') }}</label>
            <div class="rail-option-card">
              <span class="material-symbols-outlined rail-icon text-indigo">credit_card</span>
              <div class="rail-info">
                <strong>Credit or Debit Card</strong>
                <p>Instant online settlement (Visa, Mastercard, American Express).</p>
              </div>
            </div>
            <div class="rail-option-card">
              <span class="material-symbols-outlined rail-icon text-green">account_balance</span>
              <div class="rail-info">
                <strong>ACH Direct Debit (US Bank Account)</strong>
                <p>Zero processing fees for wholesale bank transfers.</p>
              </div>
            </div>
          </div>

          <div class="stripe-trust-banner">
            <span class="material-symbols-outlined">lock</span>
            <span>Payments are securely processed via Stripe. General ledger and AR payment receipts are automatically reconciled in Nova ERP upon completion.</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeInvoicePayModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="paymentSubmitting" @click="executeInvoiceCheckout">
            <span class="material-symbols-outlined" v-if="!paymentSubmitting">open_in_new</span>
            <span class="spinner" v-else></span>
            <span>{{ paymentSubmitting ? t('launching-checkout', 'Redirecting to Stripe...') : t('proceed-to-stripe-checkout', 'Proceed to Stripe Checkout') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Pay Full Account Balance Modal -->
    <div v-if="showBalancePayModal" class="modal-overlay" @click.self="closeBalancePayModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <div class="modal-badge-icon bg-purple">
              <span class="material-symbols-outlined">bolt</span>
            </div>
            <div>
              <h3 class="modal-title">{{ t('settle-full-balance-title', 'Settle Full Account Balance') }}</h3>
              <p class="modal-subtitle">{{ t('balance-settlement-desc', 'Settle all outstanding wholesale invoices in one transaction') }}</p>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeBalancePayModal">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="modal-body">
          <div class="payment-amount-card">
            <span class="amount-label">{{ t('total-outstanding-balance', 'Total Outstanding Balance') }}</span>
            <span class="amount-val">${{ portal.totalUnpaidBalance.toFixed(2) }}</span>
            <span class="amount-meta">Across {{ openInvoicesCount }} open invoice(s)</span>
          </div>

          <div class="payment-rails-options">
            <label class="section-label">{{ t('accepted-payment-options', 'Supported Payment Methods') }}</label>
            <div class="rail-option-card">
              <span class="material-symbols-outlined rail-icon text-indigo">credit_card</span>
              <div class="rail-info">
                <strong>Credit or Debit Card</strong>
                <p>Instant account balance settlement.</p>
              </div>
            </div>
            <div class="rail-option-card">
              <span class="material-symbols-outlined rail-icon text-green">account_balance</span>
              <div class="rail-info">
                <strong>ACH Direct Debit (US Bank Account)</strong>
                <p>Ideal for wholesale settlement amounts.</p>
              </div>
            </div>
          </div>

          <div class="stripe-trust-banner">
            <span class="material-symbols-outlined">lock</span>
            <span>Secured by Stripe 256-bit encrypted checkout. Automatic AR reconciliation upon payment.</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="closeBalancePayModal">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" :disabled="paymentSubmitting" @click="executeBalanceCheckout">
            <span class="material-symbols-outlined" v-if="!paymentSubmitting">open_in_new</span>
            <span class="spinner" v-else></span>
            <span>{{ paymentSubmitting ? t('launching-checkout', 'Redirecting to Stripe...') : t('pay-balance-now', 'Pay Balance with Stripe') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

// Filters state
const selectedFilter = ref('all')
const searchQuery = ref('')

// Modals state
const showInvoicePayModal = ref(false)
const selectedInvoiceForPay = ref(null)
const showBalancePayModal = ref(false)
const paymentSubmitting = ref(false)

// Metric counts
const openInvoicesCount = computed(() => {
  return portal.unpaidInvoices.length
})

const paidInvoicesCount = computed(() => {
  return portal.paidInvoices.length
})

// Filtered Invoices
const filteredInvoices = computed(() => {
  let list = portal.invoices || []

  if (selectedFilter.value === 'unpaid') {
    list = list.filter(inv => inv.status !== 'Paid' && inv.status !== 'Cancelled')
  } else if (selectedFilter.value === 'paid') {
    list = list.filter(inv => inv.status === 'Paid')
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(inv => {
      const invNum = inv.invoice_number?.toLowerCase().includes(q)
      const orderNum = inv.sales_order_number?.toLowerCase().includes(q)
      const dateStr = inv.issue_date?.toLowerCase().includes(q) || inv.due_date?.toLowerCase().includes(q)
      return invNum || orderNum || dateStr
    })
  }

  return list
})

function setFilter(filter) {
  selectedFilter.value = filter
  if (filter === 'unpaid') {
    portal.fetchInvoices({ status: 'Unpaid', page: 1 })
  } else if (filter === 'paid') {
    portal.fetchInvoices({ status: 'Paid', page: 1 })
  } else {
    portal.fetchInvoices({ page: 1 })
  }
}

function reloadInvoices() {
  portal.fetchInvoices({ page: portal.invoicesPage })
  portal.fetchAccountSummary()
}

function changePage(page) {
  portal.fetchInvoices({ page })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// PDF Download
async function handleDownloadPdf(inv) {
  try {
    showToast(`Generating PDF for invoice #${inv.invoice_number}...`, 'info', 2000)
    await portal.downloadInvoicePdf(inv.id)
    showToast(`Invoice #${inv.invoice_number} PDF downloaded!`, 'success', 3000)
  } catch (err) {
    showToast(err.message || 'Failed to download PDF invoice', 'error', 4000)
  }
}

// Payment Checkout Handlers
function openInvoicePayModal(inv) {
  selectedInvoiceForPay.value = inv
  showInvoicePayModal.value = true
}

function closeInvoicePayModal() {
  showInvoicePayModal.value = false
  selectedInvoiceForPay.value = null
  paymentSubmitting.value = false
}

async function executeInvoiceCheckout() {
  if (!selectedInvoiceForPay.value) return
  paymentSubmitting.value = true
  try {
    const session = await portal.createInvoiceCheckoutSession(selectedInvoiceForPay.value.id, {
      paymentMethodTypes: ['card', 'us_bank_account'],
    })
    if (session && session.checkout_url) {
      window.location.href = session.checkout_url
    }
  } catch (err) {
    showToast(err.message || 'Failed to launch Stripe checkout', 'error', 4000)
    paymentSubmitting.value = false
  }
}

function openBalancePayModal() {
  showBalancePayModal.value = true
}

function closeBalancePayModal() {
  showBalancePayModal.value = false
  paymentSubmitting.value = false
}

async function executeBalanceCheckout() {
  paymentSubmitting.value = true
  try {
    const session = await portal.createBalanceCheckoutSession(portal.totalUnpaidBalance, {
      paymentMethodTypes: ['card', 'us_bank_account'],
    })
    if (session && session.checkout_url) {
      window.location.href = session.checkout_url
    }
  } catch (err) {
    showToast(err.message || 'Failed to launch Stripe balance settlement', 'error', 4000)
    paymentSubmitting.value = false
  }
}

// Formatters & Badges
function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

function isOverdue(inv) {
  if (inv.status === 'Paid' || inv.status === 'Cancelled' || !inv.due_date) return false
  const due = new Date(inv.due_date)
  const now = new Date()
  return due.getTime() < now.getTime()
}

function getStatusBadgeClass(status) {
  const map = {
    Paid: 'status-paid',
    Unpaid: 'status-pending',
    'Partially Paid': 'status-confirmed',
    Overdue: 'status-cancelled',
    Cancelled: 'status-draft',
  }
  return map[status] || 'status-default'
}

function getStatusIcon(status) {
  const map = {
    Paid: 'verified',
    Unpaid: 'hourglass_empty',
    'Partially Paid': 'pending',
    Overdue: 'warning',
    Cancelled: 'cancel',
  }
  return map[status] || 'receipt'
}

onMounted(() => {
  portal.fetchInvoices()
  portal.fetchAccountSummary()
})
</script>

<style scoped>
.portal-invoices-page {
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

.btn-pay-balance-hero {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35);
  transition: all 0.2s ease;
}

.btn-pay-balance-hero:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(245, 158, 11, 0.45);
}

/* Metrics Grid */
.invoices-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 900px) {
  .invoices-metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-card.has-open-balance {
  border-left: 4px solid #f59e0b;
}

.metric-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon-box .material-symbols-outlined {
  font-size: 24px;
}

.bg-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }
.bg-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.bg-indigo { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }

.metric-details {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  margin-bottom: 4px;
}

.metric-value-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.metric-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary, #fff);
  letter-spacing: -0.5px;
}

.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }

.payment-rails-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rail-chip {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  color: var(--text-primary, #fff);
}

/* Filter Card */
.invoices-filter-card {
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

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot-amber { background: #fbbf24; }
.dot-green { background: #4ade80; }

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
}

.btn-refresh:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

/* Invoices Table */
.invoices-table-wrapper {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow: hidden;
}

.invoices-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.invoices-table th {
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  padding: 14px 18px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #64748b);
  font-weight: 700;
}

.invoices-table td {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 13px;
  color: var(--text-primary, #e2e8f0);
}

.invoice-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.cell-inv-num {
  font-weight: 700;
}

.inv-code {
  color: #818cf8;
}

.due-date-box {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.overdue-tag {
  font-size: 10px;
  font-weight: 700;
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  padding: 1px 6px;
  border-radius: 8px;
}

.order-link {
  color: #a5b4fc;
  text-decoration: none;
}

.order-link:hover {
  text-decoration: underline;
}

.text-danger { color: #f87171 !important; }
.text-amber { color: #fbbf24; }
.text-green { color: #4ade80; }

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

.status-paid { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
.status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-confirmed { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); }
.status-cancelled { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.status-draft { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
.status-default { background: rgba(255, 255, 255, 0.08); color: #e2e8f0; }

/* Actions Cluster */
.actions-cluster {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-action-pdf {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-pdf:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}

.btn-action-pdf .material-symbols-outlined {
  font-size: 16px;
}

.btn-action-pay {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  border: none;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-pay:hover {
  background: #16a34a;
  transform: translateY(-1px);
}

.btn-action-pay .material-symbols-outlined {
  font-size: 15px;
}

/* Pagination */
.invoices-pagination {
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

/* Skeletons & Empty State */
.invoices-loading-state {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.invoice-skeleton-row {
  height: 64px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.02) 25%, rgba(255, 255, 255, 0.06) 50%, rgba(255, 255, 255, 0.02) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.invoices-empty-card, .invoices-error-card {
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
  max-width: 520px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
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

.amount-val {
  font-size: 32px;
  font-weight: 800;
  color: #4ade80;
  letter-spacing: -0.5px;
}

.amount-meta {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  margin-top: 4px;
}

.payment-rails-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.rail-option-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-default, #2a2a4a);
}

.rail-icon {
  font-size: 22px;
}

.rail-info strong {
  font-size: 13px;
  color: var(--text-primary, #fff);
  display: block;
}

.rail-info p {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  margin: 2px 0 0;
}

.stripe-trust-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
}

.stripe-trust-banner .material-symbols-outlined {
  font-size: 16px;
  color: #818cf8;
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

@media (max-width: 768px) {
  .page-header-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .invoices-table th:nth-child(2),
  .invoices-table td:nth-child(2),
  .invoices-table th:nth-child(4),
  .invoices-table td:nth-child(4) {
    display: none;
  }
}
</style>

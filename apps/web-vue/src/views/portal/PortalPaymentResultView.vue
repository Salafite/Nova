<template>
  <div class="portal-payment-result-page" :dir="dir">
    <div class="portal-container">
      <div class="result-card-container">
        <!-- State 1: Verifying / Loading -->
        <div v-if="verifying" class="result-card state-loading">
          <div class="spinner-large"></div>
          <h2 class="result-title">{{ t('verifying-payment', 'Verifying Payment...') }}</h2>
          <p class="result-subtitle">{{ t('verifying-subtext', 'Communicating with Stripe and automatically reconciling your account receivables...') }}</p>
        </div>

        <!-- State 2: Success / Settled -->
        <div v-else-if="paymentState === 'complete' || paymentState === 'paid'" class="result-card state-success">
          <div class="result-icon-circle bg-green-glow">
            <span class="material-symbols-outlined">check_circle</span>
          </div>

          <h2 class="result-title">{{ t('payment-successful', 'Payment Successful & Reconciled!') }}</h2>
          <p class="result-subtitle">{{ t('payment-success-desc', 'Your settlement has been processed and your general ledger account balance has been updated.') }}</p>

          <!-- Payment Breakdown Card -->
          <div class="breakdown-card">
            <div class="breakdown-row">
              <span class="breakdown-lbl">{{ t('amount-paid', 'Amount Paid') }}</span>
              <span class="breakdown-val highlight-green">${{ formattedAmount }}</span>
            </div>

            <div class="breakdown-row" v-if="paymentStatus?.payment_status">
              <span class="breakdown-lbl">{{ t('status', 'Status') }}</span>
              <span class="status-pill status-paid">
                <span class="material-symbols-outlined">verified</span>
                <span>{{ paymentStatus.payment_status }}</span>
              </span>
            </div>

            <div class="breakdown-row" v-if="paymentStatus?.customer_email">
              <span class="breakdown-lbl">{{ t('receipt-email', 'Receipt Sent To') }}</span>
              <span class="breakdown-val font-mono">{{ paymentStatus.customer_email }}</span>
            </div>

            <div class="breakdown-row" v-if="sessionId">
              <span class="breakdown-lbl">{{ t('stripe-session-id', 'Stripe Reference') }}</span>
              <span class="breakdown-val font-mono truncate-text" :title="sessionId">{{ sessionId }}</span>
            </div>

            <div class="breakdown-row" v-if="invoiceId">
              <span class="breakdown-lbl">{{ t('settled-invoice', 'Settled Invoice') }}</span>
              <span class="breakdown-val font-mono font-bold">#{{ invoiceId }}</span>
            </div>
          </div>

          <div class="reconciliation-badge">
            <span class="material-symbols-outlined">account_balance</span>
            <span>{{ t('ar-reconciled-notice', 'Nova ERP accounts receivable records and balancing journal entries have been registered.') }}</span>
          </div>

          <!-- Action Buttons -->
          <div class="result-actions-row">
            <button
              v-if="invoiceId"
              class="btn-result-download"
              @click="downloadReceiptPdf"
            >
              <span class="material-symbols-outlined">picture_as_pdf</span>
              <span>{{ t('download-paid-invoice', 'Download Paid Invoice PDF') }}</span>
            </button>

            <router-link to="/portal/invoices" class="btn-result-primary">
              <span class="material-symbols-outlined">receipt_long</span>
              <span>{{ t('view-all-invoices', 'View Invoices') }}</span>
            </router-link>

            <router-link to="/portal/dashboard" class="btn-result-secondary">
              <span class="material-symbols-outlined">dashboard</span>
              <span>{{ t('return-to-dashboard', 'Return to Dashboard') }}</span>
            </router-link>
          </div>
        </div>

        <!-- State 3: ACH Processing / Pending -->
        <div v-else-if="paymentState === 'processing'" class="result-card state-processing">
          <div class="result-icon-circle bg-amber-glow">
            <span class="material-symbols-outlined">hourglass_top</span>
          </div>

          <h2 class="result-title">{{ t('ach-processing-title', 'ACH Bank Transfer Initiated') }}</h2>
          <p class="result-subtitle">
            {{ t('ach-processing-desc', 'Your ACH Direct Debit transfer has been submitted to Stripe and will typically clear within 2-4 business days. Your account balance will update automatically upon settlement.') }}
          </p>

          <div class="breakdown-card">
            <div class="breakdown-row">
              <span class="breakdown-lbl">{{ t('settlement-amount', 'Settlement Amount') }}</span>
              <span class="breakdown-val highlight-amber">${{ formattedAmount }}</span>
            </div>
            <div class="breakdown-row" v-if="sessionId">
              <span class="breakdown-lbl">{{ t('stripe-reference', 'Reference') }}</span>
              <span class="breakdown-val font-mono truncate-text">{{ sessionId }}</span>
            </div>
          </div>

          <div class="result-actions-row">
            <router-link to="/portal/invoices" class="btn-result-primary">
              <span class="material-symbols-outlined">receipt_long</span>
              <span>{{ t('view-invoices', 'View Invoices') }}</span>
            </router-link>
            <router-link to="/portal/dashboard" class="btn-result-secondary">
              <span class="material-symbols-outlined">dashboard</span>
              <span>{{ t('return-to-dashboard', 'Return to Dashboard') }}</span>
            </router-link>
          </div>
        </div>

        <!-- State 4: Cancelled / Failed / Error -->
        <div v-else class="result-card state-error">
          <div class="result-icon-circle bg-red-glow">
            <span class="material-symbols-outlined">cancel</span>
          </div>

          <h2 class="result-title">{{ t('payment-not-completed', 'Payment Not Completed') }}</h2>
          <p class="result-subtitle">
            {{ errorMessage || t('payment-cancelled-desc', 'The Stripe checkout session was cancelled or could not be verified. No charges were made to your account.') }}
          </p>

          <div class="result-actions-row">
            <router-link to="/portal/invoices" class="btn-result-primary">
              <span class="material-symbols-outlined">replay</span>
              <span>{{ t('retry-settlement', 'Try Payment Again') }}</span>
            </router-link>
            <router-link to="/portal/dashboard" class="btn-result-secondary">
              <span class="material-symbols-outlined">dashboard</span>
              <span>{{ t('return-to-dashboard', 'Return to Dashboard') }}</span>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const route = useRoute()
const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

const verifying = ref(true)
const paymentStatus = ref(null)
const errorMessage = ref('')

const sessionId = computed(() => route.query.session_id || '')
const invoiceId = computed(() => route.query.invoice_id || paymentStatus.value?.metadata?.invoice_id || '')
const isCancelled = computed(() => route.query.status === 'cancelled' || route.query.cancel === 'true')

const paymentState = computed(() => {
  if (isCancelled.value) return 'cancelled'
  if (!paymentStatus.value) return 'error'
  if (paymentStatus.value.status === 'complete' || paymentStatus.value.payment_status === 'paid') return 'complete'
  if (paymentStatus.value.status === 'processing' || paymentStatus.value.payment_status === 'unpaid') return 'processing'
  return paymentStatus.value.status || 'error'
})

const formattedAmount = computed(() => {
  if (paymentStatus.value?.amount_total) {
    return (paymentStatus.value.amount_total / 100).toFixed(2)
  }
  return '0.00'
})

async function verifyPayment() {
  if (isCancelled.value) {
    verifying.value = false
    return
  }

  if (!sessionId.value) {
    verifying.value = false
    errorMessage.value = 'No checkout session ID provided in payment callback URL.'
    return
  }

  try {
    const status = await portal.fetchPaymentSessionStatus(sessionId.value, true)
    paymentStatus.value = status
    // Refresh customer financial balances in the background
    portal.fetchAccountSummary()
    portal.fetchInvoices()
  } catch (err) {
    errorMessage.value = err.message || 'Failed to verify checkout settlement status'
  } finally {
    verifying.value = false
  }
}

async function downloadReceiptPdf() {
  if (!invoiceId.value) return
  try {
    showToast(`Downloading invoice #${invoiceId.value} PDF...`, 'info', 2000)
    await portal.downloadInvoicePdf(invoiceId.value)
    showToast(`Invoice #${invoiceId.value} PDF downloaded!`, 'success', 3000)
  } catch (err) {
    showToast(err.message || 'Failed to download invoice PDF', 'error', 4000)
  }
}

onMounted(() => {
  verifyPayment()
})
</script>

<style scoped>
.portal-payment-result-page {
  width: 100%;
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.portal-container {
  max-width: 680px;
  width: 100%;
  margin: 0 auto;
  padding: 40px 24px;
}

.result-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 20px;
  padding: 40px 36px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-icon-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.result-icon-circle .material-symbols-outlined {
  font-size: 40px;
}

.bg-green-glow {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 2px solid rgba(34, 197, 94, 0.3);
  box-shadow: 0 0 24px rgba(34, 197, 94, 0.25);
}

.bg-amber-glow {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 2px solid rgba(245, 158, 11, 0.3);
  box-shadow: 0 0 24px rgba(245, 158, 11, 0.25);
}

.bg-red-glow {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 2px solid rgba(239, 68, 68, 0.3);
  box-shadow: 0 0 24px rgba(239, 68, 68, 0.25);
}

.result-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary, #fff);
  letter-spacing: -0.4px;
  margin: 0 0 10px;
}

.result-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  max-width: 520px;
  margin: 0 0 24px;
}

/* Breakdown Card */
.breakdown-card {
  width: 100%;
  background: var(--bg-surface-low, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.breakdown-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.breakdown-lbl {
  color: var(--text-muted, #64748b);
  font-weight: 500;
}

.breakdown-val {
  color: var(--text-primary, #fff);
  font-weight: 600;
}

.highlight-green {
  font-size: 18px;
  font-weight: 800;
  color: #4ade80;
}

.highlight-amber {
  font-size: 18px;
  font-weight: 800;
  color: #fbbf24;
}

.truncate-text {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.status-paid {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-pill .material-symbols-outlined {
  font-size: 13px;
}

.reconciliation-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  font-size: 12px;
  text-align: left;
  margin-bottom: 28px;
}

.reconciliation-badge .material-symbols-outlined {
  font-size: 20px;
  flex-shrink: 0;
}

/* Actions Row */
.result-actions-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
}

.btn-result-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  transition: all 0.2s ease;
}

.btn-result-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
}

.btn-result-download {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-result-download:hover {
  background: #ef4444;
  color: #fff;
}

.btn-result-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 20px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.btn-result-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

.spinner-large {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 24px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

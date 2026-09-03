<template>
  <div class="driver-handover-container" :dir="dir">
    <div class="header-card flex items-center justify-between mb-4">
      <div>
        <h1 class="page-title">{{ t('driver-handover-title', 'Driver EOD Handover Reconciliation') }}</h1>
        <p class="page-subtitle">{{ t('driver-handover-sub', 'Reconcile daily COD cash and check collections from delivery drivers at depot return') }}</p>
      </div>
      <button class="btn-outline" @click="$router.push('/sales/deliveries')">
        <span class="material-symbols-outlined icon-xs">arrow_back</span>
        {{ t('back-deliveries', 'Deliveries') }}
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-4">
      <div class="form-grid-3">
        <div class="form-group">
          <label class="form-label">{{ t('driver-id', 'Driver ID') }}</label>
          <input type="number" min="1" v-model.number="driverId" class="form-input" placeholder="e.g. 1" />
        </div>
        <div class="form-group">
          <label class="form-label">{{ t('handover-date', 'Handover Date') }}</label>
          <input type="date" v-model="handoverDate" class="form-input" />
        </div>
        <div class="form-group flex items-end">
          <button class="btn-primary w-full" :disabled="loading" @click="fetchReport">
            <span v-if="loading" class="material-symbols-outlined spin icon-xs">progress_activity</span>
            <span v-else class="material-symbols-outlined icon-xs">search</span>
            {{ t('load-report', 'Load Handover Report') }}
          </button>
        </div>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="fetchReport" />

    <div v-else-if="report" class="handover-content">
      <!-- Aggregated Summary Cards -->
      <div class="summary-grid mb-4">
        <div class="summary-card">
          <span class="summary-label">{{ t('total-deliveries', 'Total Deliveries') }}</span>
          <span class="summary-value">{{ report.total_deliveries || 0 }}</span>
          <span class="summary-sub text-muted">Completed: {{ report.completed_deliveries || 0 }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">{{ t('expected-cash', 'Expected Cash Collection') }}</span>
          <span class="summary-value font-mono">${{ formatAmount(report.expected_cash || report.total_cash_expected || 0) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">{{ t('expected-check', 'Expected Check Collection') }}</span>
          <span class="summary-value font-mono">${{ formatAmount(report.expected_check || report.total_check_expected || 0) }}</span>
        </div>
        <div class="summary-card highlight-card">
          <span class="summary-label">{{ t('total-expected', 'Total Expected Collections') }}</span>
          <span class="summary-value text-purple font-mono">${{ formatAmount((report.expected_cash || 0) + (report.expected_check || 0)) }}</span>
        </div>
      </div>

      <!-- Reconciliation Form Card -->
      <div class="card mb-4">
        <h3 class="section-title mb-3">{{ t('cash-reconciliation', 'Physical Cash/Check Handover') }}</h3>
        
        <div class="form-grid-2">
          <div class="form-group">
            <label class="form-label">{{ t('cash-submitted', 'Physical Cash Submitted ($)') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="cashSubmitted" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('check-submitted', 'Physical Checks Submitted ($)') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="checkSubmitted" class="form-input" />
          </div>
          <div class="form-group col-span-full">
            <label class="form-label">{{ t('handover-notes', 'Reconciliation Notes / Discrepancy Reason') }}</label>
            <textarea v-model="reconciliationNotes" class="form-input" rows="2" placeholder="e.g. Exact cash collected and counted by cashier"></textarea>
          </div>
        </div>

        <!-- Discrepancy Alert -->
        <div v-if="discrepancyAmount !== 0" class="discrepancy-box mt-3" :class="discrepancyAmount > 0 ? 'box-over' : 'box-short'">
          <span class="material-symbols-outlined icon-sm">warning</span>
          <div>
            <strong>{{ discrepancyAmount > 0 ? t('cash-over', 'Cash Surplus (+)') : t('cash-shortage', 'Cash Shortage (-)') }}:</strong>
            <span> ${{ formatAmount(Math.abs(discrepancyAmount)) }}</span>
          </div>
        </div>

        <div class="flex justify-end mt-4">
          <button class="btn-primary btn-reconcile" :disabled="reconciling" @click="submitReconciliation">
            <span v-if="reconciling" class="material-symbols-outlined spin icon-xs">progress_activity</span>
            <span v-else class="material-symbols-outlined icon-xs">fact_check</span>
            {{ reconciling ? t('reconciling', 'Reconciling...') : t('reconcile-handover', 'Complete & Reconcile Handover') }}
          </button>
        </div>
      </div>

      <!-- Deliveries Detail Table -->
      <div v-if="report.deliveries && report.deliveries.length" class="data-card">
        <div class="table-header p-3 font-semibold border-b">
          {{ t('driver-deliveries-list', 'Assigned Delivery Drops & COD Log') }}
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('delivery-number', 'Delivery #') }}</th>
                <th>{{ t('status', 'Status') }}</th>
                <th>{{ t('payment-status', 'Payment Status') }}</th>
                <th>{{ t('cash-collected', 'Cash Coll.') }}</th>
                <th>{{ t('check-collected', 'Check Coll.') }}</th>
                <th>{{ t('check-details', 'Check Details') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="del in report.deliveries" :key="del.id">
                <td class="cell-mono font-bold">{{ del.delivery_number }}</td>
                <td><span class="badge badge-info">{{ del.status }}</span></td>
                <td><span class="badge badge-active">{{ del.payment_status || 'Pending' }}</span></td>
                <td class="cell-mono">${{ formatAmount(del.cod_cash_amount || 0) }}</td>
                <td class="cell-mono">${{ formatAmount(del.cod_check_amount || 0) }}</td>
                <td class="cell-mono text-muted">{{ del.cod_check_number ? `${del.cod_check_number} (${del.cod_check_bank || 'Bank'})` : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const driverId = ref(1)
const handoverDate = ref(new Date().toISOString().split('T')[0])
const loading = ref(false)
const reconciling = ref(false)
const error = ref('')
const report = ref(null)

const cashSubmitted = ref(0)
const checkSubmitted = ref(0)
const reconciliationNotes = ref('')

const totalExpectedCash = computed(() => {
  if (!report.value) return 0
  return Number(report.value.expected_cash || report.value.total_cash_expected || 0)
})

const totalExpectedCheck = computed(() => {
  if (!report.value) return 0
  return Number(report.value.expected_check || report.value.total_check_expected || 0)
})

const discrepancyAmount = computed(() => {
  const expectedTotal = totalExpectedCash.value + totalExpectedCheck.value
  const submittedTotal = Number(cashSubmitted.value || 0) + Number(checkSubmitted.value || 0)
  return Number((submittedTotal - expectedTotal).toFixed(2))
})

onMounted(async () => {
  await fetchReport()
})

async function fetchReport() {
  if (!driverId.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/sales/driver-handover/${driverId.value}`, {
      params: { delivery_date: handoverDate.value }
    })
    report.value = res.data
    cashSubmitted.value = totalExpectedCash.value
    checkSubmitted.value = totalExpectedCheck.value
  } catch (err) {
    error.value = t('failed-handover', 'Failed to load driver handover report')
  } finally {
    loading.value = false
  }
}

function formatAmount(val) {
  if (val === null || val === undefined || isNaN(val)) return '0.00'
  return Number(val).toFixed(2)
}

async function submitReconciliation() {
  if (!driverId.value) return
  reconciling.value = true
  try {
    await api.post('/sales/driver-handover/reconcile', {
      driver_id: driverId.value,
      cash_submitted: Number(cashSubmitted.value || 0),
      check_submitted: Number(checkSubmitted.value || 0),
      delivery_date: handoverDate.value,
      notes: reconciliationNotes.value || null
    })
    toast(t('reconciliation-success', 'Handover reconciled successfully!'), 'success')
    await fetchReport()
  } catch (err) {
    toast(err.response?.data?.detail || t('reconcile-failed', 'Failed to reconcile handover'), 'error')
  } finally {
    reconciling.value = false
  }
}
</script>

<style scoped>
.driver-handover-container { padding: 16px; max-width: 1000px; margin: 0 auto; }
.page-title { font-size: 20px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }

.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; }
.form-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.form-group { margin-bottom: 8px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }

.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.summary-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; }
.highlight-card { border-color: #c084fc; background: #faf5ff; }
.summary-label { font-size: 12px; color: #64748b; font-weight: 600; }
.summary-value { font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 4px; }
.summary-sub { font-size: 11px; margin-top: 2px; }
.text-purple { color: #6b21a8; }

.discrepancy-box { padding: 10px 14px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
.box-over { background: #fef9c3; border: 1px solid #fde047; color: #854d0e; }
.box-short { background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f8fafc; padding: 10px 14px; text-align: left; font-weight: 600; color: #475569; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; }

.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-info { background: #e0f2fe; color: #0284c7; }

.btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 18px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: #fff; color: #334155; padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; cursor: pointer; }

.col-span-full { grid-column: 1 / -1; }
.w-full { width: 100%; }
.font-mono { font-family: monospace; }
.icon-xs { font-size: 14px !important; }
.icon-sm { font-size: 18px !important; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .form-grid-3, .form-grid-2 { grid-template-columns: 1fr; }
}
</style>

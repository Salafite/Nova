<template>
  <div :dir="dir" class="spoilage-prevention-view">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ isAr ? 'منع تلف وجبات المخزون القابلة للتلف' : 'Perishable Batch Spoilage Prevention' }}</h1>
        <p class="page-subtitle">
          {{ isAr ? 'تنبيهات الانتهاء الوشيك مع توصيات الخصومات الترويجية لمنع التلف' : 'Proactive batch expiry alerts & AI-recommended promotional markdown suggestions' }}
        </p>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-card mb-6 flex flex-wrap gap-4 items-center">
      <div class="filter-group">
        <label class="filter-label">{{ isAr ? 'الحد الأدنى لدرجة الخطورة' : 'Minimum Risk Severity' }}</label>
        <select v-model="minSeverity" class="filter-select" @change="loadSpoilageRisks">
          <option value="">{{ isAr ? 'جميع المستويات' : 'All Severities' }}</option>
          <option value="CRITICAL">{{ isAr ? 'حرج فقط' : 'Critical Only' }}</option>
          <option value="HIGH">{{ isAr ? 'مرتفع وفوق' : 'High & Above' }}</option>
          <option value="MEDIUM">{{ isAr ? 'متوسط وفوق' : 'Medium & Above' }}</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">{{ isAr ? 'حد أيام انتهاء الصلاحية' : 'Expiry Horizon (Days)' }}</label>
        <select v-model.number="expiryThreshold" class="filter-select" @change="loadSpoilageRisks">
          <option :value="15">15 {{ isAr ? 'يوم' : 'Days' }}</option>
          <option :value="30">30 {{ isAr ? 'يوم' : 'Days' }}</option>
          <option :value="60">60 {{ isAr ? 'يوم' : 'Days' }} ({{ isAr ? 'افتراضي' : 'Default' }})</option>
          <option :value="90">90 {{ isAr ? 'يوم' : 'Days' }}</option>
        </select>
      </div>

      <button class="btn-primary flex items-center gap-2" :disabled="loading" @click="loadSpoilageRisks">
        <span class="material-symbols-outlined">refresh</span>
        {{ isAr ? 'تحديث المخاطر' : 'Re-evaluate Risks' }}
      </button>
    </div>

    <!-- Summary KPIs -->
    <div v-if="!loading && !error && report" class="kpi-grid mb-6">
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'الوجبات في خطر التلف' : 'Batches At Risk' }}</span>
        <span class="kpi-value text-red">{{ atRiskCount }}</span>
        <span class="kpi-sub">{{ isAr ? 'من إجمالي' : 'out of' }} {{ totalBatchesAnalyzed }} {{ isAr ? 'وجبة تم تحليلها' : 'batches analyzed' }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'إجمالي الكمية المتوقع تلفها' : 'Total Est. Spoilage Qty' }}</span>
        <span class="kpi-value text-orange">{{ totalSpoilageQty.toFixed(1) }}</span>
        <span class="kpi-sub">{{ isAr ? 'وحدات معاطاة قبل البيع' : 'units expected to expire' }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'القيمة الإجمالية المعرضة للخطر' : 'Total Value At Risk' }}</span>
        <span class="kpi-value text-purple">${{ totalValueAtRisk.toFixed(2) }}</span>
        <span class="kpi-sub">{{ isAr ? 'خسارة مالية محتملة' : 'potential gross margin loss' }}</span>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadSpoilageRisks" />

    <div v-else-if="!alerts.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon font-green">verified_user</span>
      <p>{{ isAr ? 'لا توجد وجبات مخزون معرضة لخطر التلف حاليًا' : 'No perishable inventory batches are currently at risk of spoilage.' }}</p>
    </div>

    <!-- Spoilage Alerts Table -->
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ isAr ? 'رقم الوجبة' : 'Batch #' }}</th>
              <th>{{ isAr ? 'المنتج' : 'Product' }}</th>
              <th>{{ isAr ? 'تاريخ الانتهاء' : 'Expiry Date' }}</th>
              <th class="text-center">{{ isAr ? 'الأيام المتبقية' : 'Days Left' }}</th>
              <th class="text-center">{{ isAr ? 'الكمية الحالية' : 'Current Qty' }}</th>
              <th class="text-center">{{ isAr ? 'الكمية المتوقع تلفها' : 'Est Spoilage' }}</th>
              <th class="text-center">{{ isAr ? 'درجة الخطورة' : 'Severity' }}</th>
              <th class="text-center">{{ isAr ? 'التوصية' : 'Recommended Action' }}</th>
              <th class="text-center">{{ isAr ? 'الإجراء' : 'Action' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in alerts" :key="item.batch_id" :class="{ 'row-critical': isCritical(item) }">
              <td class="cell-sku">{{ item.batch_number }}</td>
              <td class="font-semibold">{{ item.product_name || ('#' + item.product_id) }}</td>
              <td>{{ item.expiry_date }}</td>
              <td class="text-center font-bold" :class="daysLeftClass(item.days_to_expiry)">
                {{ item.days_to_expiry }} {{ isAr ? 'يوم' : 'd' }}
              </td>
              <td class="text-center mono">{{ item.current_quantity }}</td>
              <td class="text-center mono text-red font-bold">
                {{ formatNum(item.estimated_spoilage_quantity) }}
              </td>
              <td class="text-center">
                <span :class="severityBadgeClass(item.risk_severity)">
                  {{ item.risk_severity }}
                </span>
              </td>
              <td class="text-center text-sm font-medium">
                {{ item.recommended_action || (item.recommended_discount_percentage + '% Markdown') }}
              </td>
              <td class="text-center">
                <button
                  class="btn-sm btn-outline-purple"
                  @click="openPromotionModal(item)"
                >
                  {{ isAr ? 'اقتراح خصم' : 'Propose Markdown' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Promotion Modal -->
    <div v-if="selectedBatch" class="modal-backdrop" @click.self="selectedBatch = null">
      <div class="modal-card">
        <h3 class="modal-title">{{ isAr ? 'تفاصيل الخصم الترويجي للوجبة' : 'Batch Promotional Discount Proposal' }}</h3>
        <p class="modal-subtitle">
          {{ isAr ? 'الوجبة:' : 'Batch:' }} {{ selectedBatch.batch_number }} — {{ selectedBatch.product_name }}
        </p>

        <div class="modal-body space-y-4">
          <div class="info-row">
            <span>{{ isAr ? 'الأيام المتبقية للانقضاء:' : 'Days to Expiry:' }}</span>
            <strong class="text-red">{{ selectedBatch.days_to_expiry }} {{ isAr ? 'يوم' : 'days' }}</strong>
          </div>
          <div class="info-row">
            <span>{{ isAr ? 'الكمية المتوقع تلفها:' : 'Estimated Spoilage Qty:' }}</span>
            <strong>{{ formatNum(selectedBatch.estimated_spoilage_quantity) }} units</strong>
          </div>
          <div class="form-group mt-4">
            <label class="filter-label">{{ isAr ? 'نسبة الخصم المقترحة (%):' : 'Proposed Discount %:' }}</label>
            <input
              v-model.number="proposedDiscountPct"
              type="number"
              min="5"
              max="90"
              class="filter-select w-full"
            />
          </div>
          <div v-if="proposalResult" class="proposal-result p-3 bg-purple-50 rounded border border-purple-200 mt-3">
            <p class="text-xs font-semibold text-purple-900">{{ isAr ? 'الملخص الترويجي:' : 'Promotion Summary:' }}</p>

            <p class="text-sm font-bold text-purple-700">
              {{ proposalResult.recommended_discount_pct || proposedDiscountPct }}% {{ isAr ? 'خصم مقتطع' : 'Markdown Applied' }}
            </p>

          </div>
        </div>

        <div class="modal-footer flex justify-end gap-3 mt-6">
          <button class="btn-secondary" @click="selectedBatch = null">
            {{ isAr ? 'إلغاء' : 'Close' }}
          </button>
          <button class="btn-primary" :disabled="applying" @click="confirmPromotion">
            {{ isAr ? 'تطبيق الخصم الترويجي' : 'Apply Promotional Discount' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir, locale } = useI18n()
const isAr = computed(() => locale.value === 'ar-EG')

const loading = ref(true)
const error = ref('')
const report = ref(null)

const minSeverity = ref('')
const expiryThreshold = ref(60)

const selectedBatch = ref(null)
const proposedDiscountPct = ref(30)
const proposalResult = ref(null)
const applying = ref(false)

const alerts = computed(() => {
  if (!report.value) return []
  return report.value.alerts || report.value.items || report.value.batches || []
})

const totalBatchesAnalyzed = computed(() => report.value?.total_batches_analyzed || report.value?.total_batches_evaluated || 0)
const atRiskCount = computed(() => report.value?.at_risk_batches_count || report.value?.batches_at_risk_count || alerts.value.length)
const totalSpoilageQty = computed(() => report.value?.total_estimated_spoilage_quantity || report.value?.total_estimated_spoilage_qty || 0)
const totalValueAtRisk = computed(() => report.value?.total_value_at_risk || 0)

function formatNum(val) {
  return typeof val === 'number' ? val.toFixed(1) : '0.0'
}

function isCritical(item) {
  const sev = (item.risk_severity || '').toUpperCase()
  return sev === 'CRITICAL' || item.days_to_expiry <= 14
}

function daysLeftClass(days) {
  if (days <= 14) return 'text-red'
  if (days <= 30) return 'text-orange'
  return 'text-green'
}

function severityBadgeClass(sev) {
  const s = (sev || '').toUpperCase()
  if (s === 'CRITICAL') return 'badge badge-critical'
  if (s === 'HIGH') return 'badge badge-high'
  if (s === 'MEDIUM') return 'badge badge-medium'
  return 'badge badge-low'
}

async function loadSpoilageRisks() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/api/inventory/spoilage-risk', {
      params: {
        min_severity: minSeverity.value || undefined,
        days_to_expiry_threshold: expiryThreshold.value,
      },
    })
    report.value = res.data
  } catch (err) {
    error.value = isAr.value ? 'فشل تحميل تنبيهات مخاطر التلف' : 'Failed to load spoilage risk alerts'
  } finally {
    loading.value = false
  }
}

function openPromotionModal(item) {
  selectedBatch.value = item
  proposedDiscountPct.value = item.recommended_discount_percentage || 30
  proposalResult.value = null
}

async function confirmPromotion() {
  if (!selectedBatch.value) return
  applying.value = true
  try {
    const res = await api.post('/api/inventory/spoilage-risk/propose-discount', null, {
      params: {
        batch_id: selectedBatch.value.batch_id,
        discount_percentage: proposedDiscountPct.value,
      },
    })
    proposalResult.value = res.data
    alert(isAr.value ? 'تم إنشاء الخصم الترويجي بنجاح' : 'Promotional markdown proposal generated successfully!')
    selectedBatch.value = null
    loadSpoilageRisks()
  } catch (err) {
    alert(isAr.value ? 'فشل تطبيق الخصم الترويجي' : 'Failed to apply promotional discount.')
  } finally {
    applying.value = false
  }
}

onMounted(() => {
  loadSpoilageRisks()
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }

.filter-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; }
.filter-group { display: flex; flex-direction: column; gap: 4px; }
.filter-label { font-size: 11px; font-weight: 600; color: #666; text-transform: uppercase; }
.filter-select { padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; background: #fff; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.kpi-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; display: flex; flex-direction: column; }
.kpi-label { font-size: 12px; color: #777; font-weight: 500; }
.kpi-value { font-size: 24px; font-weight: 700; margin: 4px 0; }
.kpi-sub { font-size: 11px; color: #999; }

.text-red { color: #dc2626; }
.text-orange { color: #ea580c; }
.text-purple { color: #5d3fd3; }
.font-green { color: #16a34a; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:hover td { background: #fafafe; }
.row-critical td { background: #fef2f2; }

.cell-sku { font-family: monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.text-center { text-align: center; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }

.badge { display: inline-block; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
.badge-critical { background: #fee2e2; color: #dc2626; }
.badge-high { background: #ffedd5; color: #c2410c; }
.badge-medium { background: #fef9c3; color: #a16207; }
.badge-low { background: #f3f4f6; color: #4b5563; }

.btn-primary { padding: 8px 16px; background: #5d3fd3; color: #fff; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }

.btn-secondary { padding: 8px 16px; background: #e5e7eb; color: #374151; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover { background: #d1d5db; }

.btn-sm { padding: 4px 10px; font-size: 11px; border-radius: 6px; font-weight: 600; cursor: pointer; }
.btn-outline-purple { border: 1px solid #5d3fd3; color: #5d3fd3; background: transparent; }
.btn-outline-purple:hover { background: #f5f3ff; }

.empty-state { text-align: center; padding: 48px; color: #999; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: #fff; border-radius: 12px; padding: 24px; max-width: 500px; width: 90%; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
.modal-title { font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-subtitle { font-size: 13px; color: #666; margin-top: 4px; margin-bottom: 16px; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f3f4f6; font-size: 13px; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .text-center { text-align: center; }
</style>

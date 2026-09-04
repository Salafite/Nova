<template>
  <div :dir="dir" class="predictive-demand-view">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ isAr ? 'التنبؤ بالطلب على المخزون' : 'Predictive Demand Forecasting' }}</h1>
        <p class="page-subtitle">
          {{ isAr ? 'توقعات الطلب الأسبوعية باستخدام الذكاء الاصطناعي مع فترات الثقة 80% و 95%' : 'AI-driven weekly SKU demand projections with 80% & 95% confidence intervals' }}
        </p>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-card mb-6 flex flex-wrap gap-4 items-center">
      <div class="filter-group">
        <label class="filter-label">{{ isAr ? 'نافذة السجل (أيام)' : 'Lookback Days' }}</label>
        <select v-model.number="lookbackDays" class="filter-select" @change="loadForecasts">
          <option :value="30">30 {{ isAr ? 'يوم' : 'Days' }}</option>
          <option :value="60">60 {{ isAr ? 'يوم' : 'Days' }}</option>
          <option :value="90">90 {{ isAr ? 'يوم' : 'Days' }} ({{ isAr ? 'الموصى به' : 'Recommended' }})</option>
          <option :value="180">180 {{ isAr ? 'يوم' : 'Days' }}</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">{{ isAr ? 'أفق التوقع (أسابيع)' : 'Forecast Horizon' }}</label>
        <select v-model.number="forecastWeeks" class="filter-select" @change="loadForecasts">
          <option :value="2">2 {{ isAr ? 'أسابيع' : 'Weeks' }}</option>
          <option :value="4">4 {{ isAr ? 'أسابيع' : 'Weeks' }}</option>
          <option :value="8">8 {{ isAr ? 'أسابيع' : 'Weeks' }}</option>
          <option :value="12">12 {{ isAr ? 'أسبوعًا' : 'Weeks' }}</option>
        </select>
      </div>

      <button class="btn-primary flex items-center gap-2" :disabled="loading" @click="loadForecasts">
        <span class="material-symbols-outlined">sync</span>
        {{ isAr ? 'تحديث التوقعات' : 'Refresh Forecasts' }}
      </button>
    </div>

    <!-- Summary KPIs -->
    <div v-if="!loading && !error && forecasts.length" class="kpi-grid mb-6">
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'إجمالي الأفراد المتوقعة' : 'Total Projected Demand' }}</span>
        <span class="kpi-value text-purple">{{ totalProjectedDemand.toFixed(0) }}</span>
        <span class="kpi-sub">{{ forecastWeeks }} {{ isAr ? 'أسابيع قادمة' : 'weeks horizon' }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'متوسط سرعة المبيعات' : 'Avg Weekly Velocity' }}</span>
        <span class="kpi-value text-blue">{{ avgWeeklyVelocity.toFixed(1) }} / wk</span>
        <span class="kpi-sub">{{ isAr ? 'مستندة على مبيعات 90+ يوم' : 'based on sales history' }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">{{ isAr ? 'المنتجات التي تم تحليلها' : 'SKUs Forecasted' }}</span>
        <span class="kpi-value text-green">{{ forecasts.length }}</span>
        <span class="kpi-sub">{{ isAr ? 'مستويات ثقة إحصائية' : 'statistical confidence bounds' }}</span>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadForecasts" />

    <div v-else-if="!forecasts.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">trending_up</span>
      <p>{{ isAr ? 'لا توجد بيانات توقعات متاحة' : 'No demand forecast data available.' }}</p>
    </div>

    <!-- Forecast Data Table -->
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ isAr ? 'معرف المنتج' : 'SKU ID' }}</th>
              <th class="text-center">{{ isAr ? 'السرعة الأساسية' : 'Base Velocity' }}</th>
              <th class="text-center">{{ isAr ? 'معامل الاتجاه' : 'Trend Factor' }}</th>
              <th class="text-center">{{ isAr ? 'الطلب المتوقع (أسبوع 1)' : 'W1 Forecast' }}</th>
              <th class="text-center">{{ isAr ? 'نطاق الثقة 80%' : '80% Confidence Bound' }}</th>
              <th class="text-center">{{ isAr ? 'نطاق الثقة 95%' : '95% Confidence Bound' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fc in forecasts" :key="fc.product_id">
              <td class="cell-sku">#{{ fc.product_id }}</td>
              <td class="text-center mono">{{ formatNum(fc.base_velocity) }} / wk</td>
              <td class="text-center">
                <span :class="trendBadgeClass(fc.trend_factor)">
                  {{ (fc.trend_factor * 100).toFixed(0) }}%
                </span>
              </td>
              <td class="text-center mono font-bold">
                {{ formatNum(getFirstWeekDemand(fc)) }}
              </td>
              <td class="text-center">
                <span class="badge badge-ci-80">
                  {{ getCI80Text(fc) }}
                </span>
              </td>
              <td class="text-center">
                <span class="badge badge-ci-95">
                  {{ getCI95Text(fc) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
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
const forecasts = ref([])

const lookbackDays = ref(90)
const forecastWeeks = ref(4)

const totalProjectedDemand = computed(() => {
  return forecasts.value.reduce((acc, fc) => {
    const weeklySum = (fc.weekly_projections || []).reduce((wAcc, wp) => wAcc + (wp.predicted_demand || wp.forecast_qty || 0), 0)
    return acc + (weeklySum || fc.base_velocity * forecastWeeks.value)
  }, 0)
})

const avgWeeklyVelocity = computed(() => {
  if (!forecasts.value.length) return 0
  const total = forecasts.value.reduce((acc, fc) => acc + (fc.base_velocity || 0), 0)
  return total / forecasts.value.length
})

function formatNum(val) {
  return typeof val === 'number' ? val.toFixed(1) : '0.0'
}

function getFirstWeekDemand(fc) {
  if (fc.weekly_projections && fc.weekly_projections.length > 0) {
    return fc.weekly_projections[0].predicted_demand || fc.weekly_projections[0].forecast_qty || fc.base_velocity
  }
  return fc.base_velocity || 0
}

function getCI80Text(fc) {
  if (fc.weekly_projections && fc.weekly_projections.length > 0) {
    const w1 = fc.weekly_projections[0]
    if (w1.confidence_80) {
      return `${formatNum(w1.confidence_80.lower_bound)} - ${formatNum(w1.confidence_80.upper_bound)}`
    }
    if (w1.ci_80) {
      return `${formatNum(w1.ci_80[0])} - ${formatNum(w1.ci_80[1])}`
    }
  }
  const low = (fc.base_velocity || 0) * 0.85
  const high = (fc.base_velocity || 0) * 1.15
  return `${formatNum(low)} - ${formatNum(high)}`
}

function getCI95Text(fc) {
  if (fc.weekly_projections && fc.weekly_projections.length > 0) {
    const w1 = fc.weekly_projections[0]
    if (w1.confidence_95) {
      return `${formatNum(w1.confidence_95.lower_bound)} - ${formatNum(w1.confidence_95.upper_bound)}`
    }
    if (w1.ci_95) {
      return `${formatNum(w1.ci_95[0])} - ${formatNum(w1.ci_95[1])}`
    }
  }
  const low = (fc.base_velocity || 0) * 0.75
  const high = (fc.base_velocity || 0) * 1.25
  return `${formatNum(low)} - ${formatNum(high)}`
}

function trendBadgeClass(factor) {
  if (!factor || factor === 1.0) return 'badge badge-neutral'
  if (factor > 1.0) return 'badge badge-success'
  return 'badge badge-warning'
}

async function loadForecasts() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/api/inventory/predictive-demand', {
      params: {
        lookback_days: lookbackDays.value,
        forecast_weeks: forecastWeeks.value,
      },
    })
    forecasts.value = res.data || []
  } catch (err) {
    error.value = isAr.value ? 'فشل تحميل بيانات التوقعات' : 'Failed to load predictive demand forecasts'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadForecasts()
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

.text-purple { color: #5d3fd3; }
.text-blue { color: #2563eb; }
.text-green { color: #16a34a; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:hover td { background: #fafafe; }

.cell-sku { font-family: monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #333; }
.font-bold { font-weight: 700; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-neutral { background: #f3f4f6; color: #4b5563; }
.badge-success { background: #dcfce7; color: #15803d; }
.badge-warning { background: #fef3c7; color: #b45309; }
.badge-ci-80 { background: #eff6ff; color: #1d4ed8; }
.badge-ci-95 { background: #f3e8ff; color: #6b21a8; }

.btn-primary { padding: 8px 16px; background: #5d3fd3; color: #fff; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }

.empty-state { text-align: center; padding: 48px; color: #999; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .text-center { text-align: center; }
</style>

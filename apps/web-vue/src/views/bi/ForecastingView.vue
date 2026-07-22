<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div><h1 class="page-title">{{ t('forecast-title', 'Forecasting') }}</h1><p class="page-subtitle">{{ t('forecast-sub', 'Sales and demand forecasting with predictive analytics') }}</p></div>
    </div>
    <SkeletonTable v-if="loading" /><ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">trending_up</span><p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>{{ t('metric') }}</th><th>{{ t('period') }}</th><th class="text-center">{{ t('forecasted', 'Forecasted') }}</th><th class="text-center">{{ t('actual') }}</th><th class="text-center">{{ t('variance') }}</th><th>{{ t('confidence', 'Confidence') }}</th></tr></thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><strong>{{ item.metric || item.name || item.kpi_name }}</strong></td>
              <td>{{ item.period || item.month || item.quarter || '-' }}</td>
              <td class="text-center">{{ formatCurrency(item.forecasted_value || item.predicted) }}</td>
              <td class="text-center">{{ formatCurrency(item.actual_value || item.actual) }}</td>
              <td class="text-center" :class="varianceClass(item)">{{ item.variance || (item.actual && item.forecasted_value ? ((item.actual - item.forecasted_value) / item.forecasted_value * 100).toFixed(1) + '%' : '-') }}</td>
              <td>{{ item.confidence_score ? (item.confidence_score * 100).toFixed(0) + '%' : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
const { t, dir } = useI18n()
const loading = ref(true); const error = ref(''); const items = ref([])
function formatCurrency(v) { return v != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v) : '-' }
function varianceClass(item) { const v = item.variance_percent || item.variance; if (!v) return ''; const n = parseFloat(v); return n >= 0 ? 'text-green' : 'text-red' }
async function load() { loading.value = true; error.value = ''; try { const res = await api.get('/T0053I/'); items.value = res.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
onMounted(() => { load() })
</script>
<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; }
.text-green { color: #16a34a; font-weight: 600; }
.text-red { color: #dc2626; font-weight: 600; }
.mb-6 { margin-bottom: 24px; }
</style>
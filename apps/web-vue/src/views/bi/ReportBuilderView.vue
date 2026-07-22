<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('report-title', 'Report Builder') }}</h1>
        <p class="page-subtitle">{{ t('report-subtitle', 'Query entity data and build custom reports') }}</p>
      </div>
    </div>

    <div class="report-layout">
      <div class="report-sidebar">
        <div class="section-block">
          <h4>{{ t('report-entity', 'Data Source') }}</h4>
          <select v-model="selectedEntity" class="form-input" @change="onEntityChange">
            <option value="">{{ t('report-select-entity', '-- Select Entity --') }}</option>
            <option v-for="e in entities" :key="e.value" :value="e.value">{{ e.label }}</option>
          </select>
        </div>

        <div v-if="selectedEntity" class="section-block">
          <h4>{{ t('report-columns', 'Columns') }}</h4>
          <div class="column-list">
            <label v-for="col in availableColumns" :key="col" class="column-check">
              <input type="checkbox" :value="col" v-model="selectedColumns" />
              <span>{{ col }}</span>
            </label>
          </div>
        </div>

        <div v-if="selectedEntity" class="section-block">
          <h4>{{ t('report-limit', 'Max Rows') }}</h4>
          <input type="number" v-model.number="limit" class="form-input" min="1" max="1000" />
        </div>

        <button v-if="selectedEntity" class="btn-primary btn-run" @click="runReport" :disabled="running">
          <span class="material-symbols-outlined">play_arrow</span>
          {{ running ? t('report-running', 'Running...') : t('report-run', 'Run Report') }}
        </button>
      </div>

      <div class="report-main">
        <div v-if="!selectedEntity" class="placeholder">
          <span class="material-symbols-outlined placeholder-icon">description</span>
          <p>{{ t('report-select-prompt', 'Select a data source and columns to build your report') }}</p>
        </div>

        <div v-else-if="error" class="error-state">
          <span class="material-symbols-outlined">error</span>
          <p>{{ error }}</p>
        </div>

        <div v-else-if="!result.length && !running" class="placeholder">
          <span class="material-symbols-outlined">table_chart</span>
          <p>{{ t('report-run-prompt', 'Click "Run Report" to fetch data') }}</p>
        </div>

        <template v-else-if="result.length">
          <div class="result-toolbar">
            <span class="result-count">{{ t('report-rows', '{n} rows', { n: result.length }) }}</span>
            <div class="result-actions">
              <button class="btn-outline btn-xs" @click="toggleChart">
                <span class="material-symbols-outlined">bar_chart</span>
                {{ showChart ? t('report-show-table', 'Table') : t('report-show-chart', 'Chart') }}
              </button>
              <button class="btn-outline btn-xs" @click="exportCsv">
                <span class="material-symbols-outlined">download</span>
                {{ t('report-export', 'Export CSV') }}
              </button>
            </div>
          </div>

          <div v-if="showChart" class="chart-section">
            <div class="chart-controls">
              <select v-model="chartLabelCol" class="form-input form-input-sm">
                <option value="">{{ t('report-chart-label', '-- Label Column --') }}</option>
                <option v-for="col in displayColumns" :key="col" :value="col">{{ col }}</option>
              </select>
              <select v-model="chartValueCol" class="form-input form-input-sm">
                <option value="">{{ t('report-chart-value', '-- Value Column --') }}</option>
                <option v-for="col in displayColumns" :key="col" :value="col">{{ col }}</option>
              </select>
              <select v-model="chartType" class="form-input form-input-sm">
                <option value="bar">Bar</option>
                <option value="line">Line</option>
                <option value="pie">Pie</option>
                <option value="donut">Donut</option>
              </select>
            </div>
            <ChartRenderer v-if="chartLabelCol && chartValueCol" :type="chartType" :labels="chartLabels" :values="chartValues" :height="300" color="#5d3fd3" />
          </div>

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in displayColumns" :key="col" class="cell-th">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in result" :key="i">
                  <td v-for="col in displayColumns" :key="col">{{ formatValue(row[col]) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { api } from '../../api/client.js'
import ChartRenderer from '../../components/charts/ChartRenderer.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()

const entities = [
  { value: 'T0003I', label: 'Products' },
  { value: 'T0010I', label: 'Customers' },
  { value: 'T0011I', label: 'Suppliers' },
  { value: 'T0012I', label: 'Sales Orders' },
  { value: 'T0014I', label: 'Purchase Orders' },
  { value: 'T0090I', label: 'Invoices' },
  { value: 'T0091I', label: 'Payments' },
  { value: 'T0030I', label: 'Employees' },
  { value: 'T0021I', label: 'Users' },
  { value: 'T0052I', label: 'KPI Definitions' },
  { value: 'T0054I', label: 'BI Dashboards' }
]

const selectedEntity = ref('')
const availableColumns = ref([])
const selectedColumns = ref([])
const limit = ref(100)
const running = ref(false)
const error = ref('')
const result = ref([])
const showChart = ref(false)
const chartType = ref('bar')
const chartLabelCol = ref('')
const chartValueCol = ref('')

const columnCache = {}

const displayColumns = computed(() => {
  if (selectedColumns.value.length) return selectedColumns.value
  if (result.value.length) return Object.keys(result.value[0]).slice(0, 8)
  return []
})

const chartLabels = computed(() => {
  if (!chartLabelCol.value) return []
  return result.value.map(r => r[chartLabelCol.value])
})

const chartValues = computed(() => {
  if (!chartValueCol.value) return []
  return result.value.map(r => {
    const v = parseFloat(r[chartValueCol.value])
    return isNaN(v) ? 0 : v
  })
})

async function onEntityChange() {
  selectedColumns.value = []
  result.value = []
  error.value = ''
  showChart.value = false
  if (!selectedEntity.value) return

  if (columnCache[selectedEntity.value]) {
    availableColumns.value = columnCache[selectedEntity.value]
    return
  }

  try {
    const res = await api.get('/' + selectedEntity.value + '/', { params: { limit: 1 } })
    const data = res.data || []
    const cols = data.length ? Object.keys(data[0]) : ['id']
    availableColumns.value = cols
    columnCache[selectedEntity.value] = cols
    selectedColumns.value = cols.slice(0, 6)
  } catch {
    availableColumns.value = ['id', 'name', 'code', 'is_active']
    selectedColumns.value = ['id', 'name']
  }
}

async function runReport() {
  if (!selectedEntity.value) return
  running.value = true
  error.value = ''
  result.value = []
  showChart.value = false
  try {
    const res = await api.get('/' + selectedEntity.value + '/', { params: { limit: limit.value || 100 } })
    result.value = res.data || []
    if (!result.value.length) {
      toast(t('report-empty', 'No data found'), 'info')
    }
  } catch (e) {
    error.value = t('report-error', 'Failed to fetch data')
  } finally {
    running.value = false
  }
}

function formatValue(val) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function toggleChart() { showChart.value = !showChart.value }

function exportCsv() {
  if (!result.value.length) return
  const cols = displayColumns.value
  const header = cols.join(',')
  const rows = result.value.map(r => cols.map(c => {
    const v = r[c]
    if (v === null || v === undefined) return ''
    const s = String(v).replace(/"/g, '""')
    return `"${s}"`
  }).join(','))
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = selectedEntity.value + '_report.csv'
  a.click(); URL.revokeObjectURL(url)
  toast(t('report-exported', 'Report exported'), 'success')
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-subtitle { font-size: 13px; color: var(--text-subtle); margin-top: 2px; }

.report-layout { display: grid; grid-template-columns: 260px 1fr; gap: 20px; min-height: 500px; }

.report-sidebar { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 20px; }
.section-block { margin-bottom: 20px; }
.section-block h4 { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }

.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
.form-input-sm { padding: 6px 8px; font-size: 12px; }

.column-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.column-check { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer; padding: 3px 0; }
.column-check input { width: 14px; height: 14px; }

.btn-run { width: 100%; justify-content: center; margin-top: 8px; }
.btn-xs { padding: 4px 12px !important; font-size: 12px !important; }

.report-main { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 20px; overflow: hidden; }

.placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 100px 0; color: var(--text-faint); }
.placeholder-icon { font-size: 64px; color: var(--border-default); margin-bottom: 12px; }
.error-state { display: flex; flex-direction: column; align-items: center; padding: 60px 0; color: #dc2626; }
.error-state .material-symbols-outlined { font-size: 48px; margin-bottom: 12px; }

.result-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.result-count { font-size: 13px; color: var(--text-subtle); }
.result-actions { display: flex; gap: 8px; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { background: var(--bg-surface-low); padding: 8px 12px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid var(--border-light); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }

.chart-section { margin-bottom: 20px; }
.chart-controls { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }

@media (max-width: 767px) {
  .report-layout { grid-template-columns: 1fr; }
}
[dir="rtl"] .result-toolbar { flex-direction: row-reverse; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .section-block h4 { text-align: right; }
</style>

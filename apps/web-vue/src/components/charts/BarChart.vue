<template>
  <div class="chart-box">
    <Bar v-if="data" :data="data" :options="options" />
    <div v-else class="chart-empty">{{ t('no-data', 'No data') }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { useI18n } from '../../composables/useI18n.js'
import { useChartTheme } from '../../composables/useChartTheme.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const { t } = useI18n()
const { chartOptions } = useChartTheme()

const props = defineProps({
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  color: { type: String, default: '#5d3fd3' },
  height: { type: Number, default: 250 }
})

const options = computed(() => chartOptions({ legend: { display: false } }))

const data = computed(() => {
  if (!props.labels.length || !props.values.length) return null
  return {
    labels: props.labels,
    datasets: [{
      label: props.label,
      data: props.values,
      backgroundColor: props.color + '33',
      borderColor: props.color,
      borderWidth: 2,
      borderRadius: 4
    }]
  }
})
</script>

<style scoped>
.chart-box { position: relative; width: 100%; height: v-bind(height + 'px'); }
.chart-empty { display: flex; align-items: center; justify-content: center; height: v-bind(height + 'px'); color: var(--text-faint); font-size: 13px; }
</style>

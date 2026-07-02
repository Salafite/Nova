<template>
  <div class="chart-box">
    <Line v-if="data" :data="data" :options="options" />
    <div v-else class="chart-empty">{{ t('no-data', 'No data') }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { useI18n } from '../../composables/useI18n.js'
import { useChartTheme } from '../../composables/useChartTheme.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const { t } = useI18n()
const { chartOptions, colors, dark } = useChartTheme()

const props = defineProps({
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  color: { type: String, default: '#5d3fd3' },
  fill: { type: Boolean, default: true },
  height: { type: Number, default: 250 },
  datasets: { type: Array, default: null }
})

const options = computed(() => chartOptions({
  legend: { display: !!props.datasets },
  extra: { elements: { point: { radius: 3, hoverRadius: 6 } } }
}))

const data = computed(() => {
  if (props.datasets) {
    if (!props.labels.length) return null
    return { labels: props.labels, datasets: props.datasets }
  }
  if (!props.labels.length || !props.values.length) return null
  return {
    labels: props.labels,
    datasets: [{
      label: props.label,
      data: props.values,
      borderColor: props.color,
      backgroundColor: props.fill ? props.color + '1a' : 'transparent',
      fill: props.fill,
      tension: 0.4,
      pointBackgroundColor: props.color,
      pointBorderColor: colors(dark.value).pointBorderColor,
      pointBorderWidth: 2,
      borderWidth: 2
    }]
  }
})
</script>

<style scoped>
.chart-box { position: relative; width: 100%; height: v-bind(height + 'px'); }
.chart-empty { display: flex; align-items: center; justify-content: center; height: v-bind(height + 'px'); color: var(--text-faint); font-size: 13px; }
</style>

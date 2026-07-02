<template>
  <div class="chart-box">
    <Doughnut v-if="data" :data="data" :options="options" />
    <div v-else class="chart-empty">{{ t('no-data', 'No data') }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { useI18n } from '../../composables/useI18n.js'
import { useChartTheme } from '../../composables/useChartTheme.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const { t } = useI18n()
const { chartOptions, colors, dark } = useChartTheme()

const props = defineProps({
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  colors: { type: Array, default: () => ['#5d3fd3', '#90efef', '#555c69', '#cabeff', '#76d6d5', '#ffdad6'] },
  centerText: { type: String, default: '' },
  height: { type: Number, default: 250 }
})

const options = computed(() => chartOptions({
  legend: { position: 'bottom' },
  scales: undefined,
  extra: { cutout: '70%' }
}))

const data = computed(() => {
  if (!props.labels.length || !props.values.length) return null
  return {
    labels: props.labels,
    datasets: [{
      data: props.values,
      backgroundColor: props.colors,
      borderColor: colors(dark.value).segmentBorder,
      borderWidth: 2
    }]
  }
})
</script>

<style scoped>
.chart-box { position: relative; width: 100%; height: v-bind(height + 'px'); }
.chart-empty { display: flex; align-items: center; justify-content: center; height: v-bind(height + 'px'); color: var(--text-faint); font-size: 13px; }
</style>

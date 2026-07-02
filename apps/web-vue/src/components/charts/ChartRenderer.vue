<template>
  <BarChart v-if="type === 'bar'" v-bind="chartProps" />
  <LineChart v-else-if="type === 'line'" v-bind="chartProps" />
  <PieChart v-else-if="type === 'pie'" v-bind="chartProps" />
  <DonutChart v-else-if="type === 'donut' || type === 'doughnut'" v-bind="chartProps" />
  <StatWidget v-else-if="type === 'stat'" v-bind="statProps" @click="$emit('widget-click')" />
  <ProgressWidget v-else-if="type === 'progress'" v-bind="progressProps" @click="$emit('widget-click')" />
  <div v-else class="unknown-widget">
    <span class="material-symbols-outlined">help</span>
    <span>{{ t('unknown-widget', 'Unknown widget type') }}: {{ type }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import BarChart from './BarChart.vue'
import LineChart from './LineChart.vue'
import PieChart from './PieChart.vue'
import DonutChart from './DonutChart.vue'
import StatWidget from './StatWidget.vue'
import ProgressWidget from './ProgressWidget.vue'

const { t } = useI18n()

const props = defineProps({
  type: { type: String, default: 'stat' },
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  color: { type: String, default: '#5d3fd3' },
  colors: { type: Array, default: () => [] },
  height: { type: Number, default: 250 },
  statLabel: { type: String, default: '' },
  statValue: { type: [String, Number], default: 0 },
  statPrefix: { type: String, default: '' },
  statSuffix: { type: String, default: '' },
  statIcon: { type: String, default: '' },
  statIconColor: { type: String, default: '#5d3fd3' },
  statValueColor: { type: String, default: '#1a1a2e' },
  trend: { type: String, default: '' },
  trendDir: { type: String, default: 'up' },
  progressLabel: { type: String, default: '' },
  progressValue: { type: Number, default: 0 },
  progressSubtext: { type: String, default: '' },
  fill: { type: Boolean, default: true },
  decimals: { type: Number, default: 0 },
  centerText: { type: String, default: '' }
})

defineEmits(['widget-click'])

const chartProps = computed(() => ({
  labels: props.labels,
  values: props.values,
  label: props.label,
  color: props.color,
  colors: props.colors.length ? props.colors : undefined,
  height: props.height,
  fill: props.fill,
  centerText: props.centerText
}))

const statProps = computed(() => ({
  label: props.statLabel,
  value: props.statValue,
  prefix: props.statPrefix,
  suffix: props.statSuffix,
  icon: props.statIcon,
  iconColor: props.statIconColor,
  valueColor: props.statValueColor,
  trend: props.trend,
  trendDir: props.trendDir,
  decimals: props.decimals
}))

const progressProps = computed(() => ({
  label: props.progressLabel,
  value: props.progressValue,
  subtext: props.progressSubtext,
  color: props.color
}))
</script>

<style scoped>
.unknown-widget { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: var(--text-faint); font-size: 13px; }
.unknown-widget .material-symbols-outlined { font-size: 24px; }
</style>

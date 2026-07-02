<template>
  <div class="stat-widget" :class="{ clickable: !!to }" @click="$emit('click')">
    <div class="stat-head">
      <span class="stat-label">{{ label }}</span>
      <span v-if="icon" class="material-symbols-outlined stat-icon" :style="{ color: iconColor }">{{ icon }}</span>
    </div>
    <div class="stat-value" :style="{ color: valueColor }">{{ prefix }}{{ displayValue }}{{ suffix }}</div>
    <div v-if="trend" class="stat-trend" :class="trendDir">
      <span class="material-symbols-outlined trend-arrow">{{ trendDir === 'up' ? 'trending_up' : 'trending_down' }}</span>
      {{ trend }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: [String, Number], default: 0 },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' },
  icon: { type: String, default: '' },
  iconColor: { type: String, default: '#5d3fd3' },
  valueColor: { type: String, default: '#1a1a2e' },
  trend: { type: String, default: '' },
  trendDir: { type: String, default: 'up' },
  decimals: { type: Number, default: 0 },
  to: { type: String, default: '' }
})

defineEmits(['click'])

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString(undefined, { minimumFractionDigits: props.decimals, maximumFractionDigits: props.decimals })
  }
  return props.value
})
</script>

<style scoped>
.stat-widget { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 20px; }
.stat-widget.clickable { cursor: pointer; }
.stat-widget.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.stat-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.stat-label { font-size: 11px; font-weight: 600; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.5px; }
.stat-icon { font-size: 20px; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-trend { display: flex; align-items: center; gap: 4px; margin-top: 8px; font-size: 12px; font-weight: 600; }
.stat-trend.up { color: #16a34a; }
.stat-trend.down { color: #dc2626; }
.trend-arrow { font-size: 16px; }
</style>

<template>
  <div class="progress-widget" :class="{ clickable: !!to }" @click="$emit('click')">
    <div class="progress-head">
      <span class="progress-label">{{ label }}</span>
      <span class="progress-pct">{{ value }}%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" :style="{ width: clamped + '%', background: barColor }"></div>
    </div>
    <div v-if="subtext" class="progress-sub">{{ subtext }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: Number, default: 0 },
  color: { type: String, default: '#5d3fd3' },
  subtext: { type: String, default: '' },
  to: { type: String, default: '' }
})

defineEmits(['click'])

const clamped = computed(() => Math.min(100, Math.max(0, props.value)))
const barColor = computed(() => {
  if (props.value >= 100) return '#16a34a'
  if (props.value < 25) return '#dc2626'
  return props.color
})
</script>

<style scoped>
.progress-widget { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; }
.progress-widget.clickable { cursor: pointer; }
.progress-widget.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.progress-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.progress-label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.progress-pct { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.progress-track { height: 8px; background: var(--border-light); border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.progress-sub { margin-top: 6px; font-size: 11px; color: var(--text-subtle); }
</style>

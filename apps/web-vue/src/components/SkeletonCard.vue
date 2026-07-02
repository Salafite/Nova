<template>
  <div class="skeleton-card" :class="[`skeleton-${variant}`]">
    <div class="skeleton-bar" v-for="i in bars" :key="i" :style="{ width: widths[(i - 1) % widths.length], height: heights[(i - 1) % heights.length] }"></div>
  </div>
</template>

<script setup>
const props = defineProps({
  variant: { type: String, default: 'card', validator: v => ['card', 'detail', 'form'].includes(v) },
})
const bars = props.variant === 'form' ? 6 : props.variant === 'detail' ? 4 : 3
const widths = props.variant === 'form' ? ['40%', '100%', '100%', '100%', '60%', '100%'] : ['55%', '90%', '75%', '45%']
const heights = ['16px', '14px', '14px', '14px', '14px', '14px']
</script>

<style scoped>
.skeleton-card { padding: 24px; border: 1px solid var(--border-default); border-radius: 8px; display: flex; flex-direction: column; gap: 14px; }
.skeleton-bar { height: 14px; background: linear-gradient(90deg, var(--skeleton-from, #e5e7eb) 25%, var(--skeleton-to, #f3f4f6) 50%, var(--skeleton-from, #e5e7eb) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; border-radius: 4px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>

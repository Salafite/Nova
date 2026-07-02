<template>
  <div class="stat-card">
    <div class="stat-value" :style="{ color: color }">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: String, value: [String, Number], color: { type: String, default: '#5d3fd3' }
})
</script>

<style scoped>
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #666; margin-top: 4px; }
</style>

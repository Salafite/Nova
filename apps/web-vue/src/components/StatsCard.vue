<template>
  <div class="stat-card" :class="{ clickable: !!to }" @click="navigate">
    <div class="stat-value" :style="{ color: color }">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  label: String, value: [String, Number], color: { type: String, default: '#5d3fd3' }, to: { type: String, default: '' }
})

const router = useRouter()
function navigate() { if (props.to) router.push({ name: props.to }) }
</script>

<style scoped>
.stat-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px; text-align: center; transition: box-shadow 0.15s, transform 0.15s; }
.stat-card.clickable { cursor: pointer; }
.stat-card.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
</style>

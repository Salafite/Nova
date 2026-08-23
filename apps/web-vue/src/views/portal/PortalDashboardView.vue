<template>
  <div class="portal-view portal-dashboard-view">
    <div class="portal-header">
      <div>
        <h1 class="portal-title">Customer Dashboard</h1>
        <p class="portal-subtitle">Welcome back! Manage your replenishment orders and account balance.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { usePortalStore } from '../../stores/portal.js'

const portal = usePortalStore()

onMounted(() => {
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
})
</script>

<style scoped>
.portal-view { padding: 24px; max-width: 1400px; margin: 0 auto; }
.portal-title { font-size: 24px; font-weight: 700; color: var(--color-text-primary, #fff); margin: 0 0 4px; }
.portal-subtitle { font-size: 14px; color: var(--color-text-muted, #94a3b8); margin: 0; }
</style>

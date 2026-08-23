<template>
  <div class="portal-view portal-payment-result-view">
    <div class="portal-header">
      <div>
        <h1 class="portal-title">Payment Confirmation</h1>
        <p class="portal-subtitle">Stripe settlement and payment status verification.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePortalStore } from '../../stores/portal.js'

const route = useRoute()
const portal = usePortalStore()

onMounted(() => {
  const sessionId = route.query.session_id
  if (sessionId) {
    portal.fetchPaymentSessionStatus(sessionId)
  }
})
</script>

<style scoped>
.portal-view { padding: 24px; max-width: 1400px; margin: 0 auto; }
.portal-title { font-size: 24px; font-weight: 700; color: var(--color-text-primary, #fff); margin: 0 0 4px; }
.portal-subtitle { font-size: 14px; color: var(--color-text-muted, #94a3b8); margin: 0; }
</style>

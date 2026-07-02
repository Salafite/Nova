<template>
  <div class="error-state-card">
    <span class="material-symbols-outlined error-icon">error_outline</span>
    <p class="error-message">{{ message }}</p>
    <button v-if="showRetry" class="btn-outline btn-sm" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'Something went wrong. Please try again.' },
  retryLabel: { type: String, default: 'Retry' },
  showRetry: { type: Boolean, default: true },
})
defineEmits(['retry'])
</script>

<style scoped>
.error-state-card { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; text-align: center; }
.error-icon { font-size: 48px; color: #dc2626; margin-bottom: 12px; }
.error-message { color: #6b7280; font-size: 14px; margin: 0 0 16px; }
.btn-sm { padding: 6px 16px; font-size: 13px; }
</style>

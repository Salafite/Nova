<template>
  <p v-if="message" class="field-error">{{ message }}</p>
</template>

<script setup>
defineProps({ message: { type: String, default: '' } })
</script>

<style scoped>
.field-error { font-size: 11px; color: #dc2626; margin: 3px 0 0; }
</style>

<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from './composables/useI18n.js'

const { apply } = useI18n()
onMounted(apply)
</script>

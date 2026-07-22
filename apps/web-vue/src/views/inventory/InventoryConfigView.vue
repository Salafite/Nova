<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ locale === 'ar-EG' ? 'إعدادات المخزون' : 'Inventory Configurations' }}</h1>
        <p class="page-subtitle">{{ locale === 'ar-EG' ? 'إدارة إعدادات المخزون والمستودعات' : 'Manage inventory and warehouse settings' }}</p>
      </div>
    </div>
    <div class="empty-state">
      <span class="material-symbols-outlined empty-icon">settings</span>
      <p>{{ locale === 'ar-EG' ? 'شاشة الإعدادات قيد الإنشاء' : 'Configuration screen coming soon' }}</p>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '../../composables/useI18n.js'
const { locale, dir } = useI18n()
</script>

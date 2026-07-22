<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ locale === 'ar-EG' ? 'نظرة عامة على المخزون' : 'Inventory Overview' }}</h1>
        <p class="page-subtitle">{{ locale === 'ar-EG' ? 'ملخص سريع لحالة المخزون والمستودعات' : 'Quick summary of inventory and warehouse status' }}</p>
      </div>
    </div>
    <div class="empty-state">
      <span class="material-symbols-outlined empty-icon">grid_view</span>
      <p>{{ locale === 'ar-EG' ? 'لوحة نظرة عامة قيد الإنشاء' : 'Overview dashboard coming soon' }}</p>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '../../composables/useI18n.js'
const { locale, dir } = useI18n()
</script>

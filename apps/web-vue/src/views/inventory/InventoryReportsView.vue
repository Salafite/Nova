<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ locale === 'ar-EG' ? 'تقارير المخزون' : 'Inventory Reports' }}</h1>
        <p class="page-subtitle">{{ locale === 'ar-EG' ? 'تقارير وتحليلات المخزون' : 'Inventory reports and analytics' }}</p>
      </div>
    </div>
    <div class="empty-state">
      <span class="material-symbols-outlined empty-icon">bar_chart</span>
      <p>{{ locale === 'ar-EG' ? 'وحدة التقارير قيد الإنشاء' : 'Reports module coming soon' }}</p>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '../../composables/useI18n.js'
const { locale, dir } = useI18n()
</script>

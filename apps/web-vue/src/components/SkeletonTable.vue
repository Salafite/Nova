<template>
  <div class="skeleton-table">
    <div class="skeleton-header">
      <div class="skeleton-cell" v-for="i in columns" :key="i" :style="{ width: headerWidths[i - 1] || '100px' }"></div>
    </div>
    <div class="skeleton-row" v-for="r in rows" :key="r">
      <div class="skeleton-cell" v-for="i in columns" :key="i" :style="{ width: columnWidths[(r + i) % columnWidths.length] }"></div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  rows: { type: Number, default: 6 },
  columns: { type: Number, default: 5 },
  headerWidths: { type: Array, default: () => ['120px', '160px', '100px', '90px', '80px'] },
})
const columnWidths = ['140px', '100px', '180px', '80px', '120px', '90px', '150px', '70px']
</script>

<style scoped>
.skeleton-table { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.skeleton-header, .skeleton-row { display: flex; gap: 16px; padding: 14px 20px; }
.skeleton-header { background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
.skeleton-row { border-bottom: 1px solid #f3f4f6; }
.skeleton-row:last-child { border-bottom: none; }
.skeleton-cell { height: 14px; background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; border-radius: 4px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>

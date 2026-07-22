<template>
  <div class="inv-subnav" :dir="dir">
    <nav class="inv-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['inv-tab', { active: activeTab === tab.id }]"
        @click="navigate(tab)"
      >
        <span class="material-symbols-outlined inv-tab-icon">{{ tab.icon }}</span>
        <span class="inv-tab-label">{{ isRTL && tab.label_ar ? tab.label_ar : tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n.js'

const route = useRoute()
const router = useRouter()
const { isRTL } = useI18n()
const { dir } = useI18n()

const INVENTORY_ROUTES = {
  'inventory-overview': 'overview',
  products: 'products',
  'product-detail': 'products',
  categories: 'products',
  barcodes: 'products',
  attributes: 'products',
  uom: 'products',
  'uom-conversions': 'products',
  inventory: 'stock',
  'inventory-counts': 'stock',
  'stock-movements': 'stock',
  'stock-adjustments': 'stock',
  'batch-numbers': 'stock',
  'serial-numbers': 'stock',
  warehouses: 'warehouse',
  'pick-lists': 'warehouse',
  'pick-list-detail': 'warehouse',
  'goods-receipt': 'warehouse',
  'inventory-reports': 'reports',
  'inventory-config': 'configurations',
}

const tabs = [
  { id: 'overview', icon: 'grid_view', label: 'Overview', label_ar: 'نظرة عامة', route: 'inventory-overview' },
  { id: 'products', icon: 'inventory_2', label: 'Products', label_ar: 'المنتجات', route: 'products' },
  { id: 'stock', icon: 'warehouse', label: 'Stock', label_ar: 'المخزون', route: 'inventory' },
  { id: 'warehouse', icon: 'factory', label: 'Warehouse', label_ar: 'المستودعات', route: 'warehouses' },
  { id: 'reports', icon: 'bar_chart', label: 'Reports', label_ar: 'التقارير', route: 'inventory-reports' },
  { id: 'configurations', icon: 'settings', label: 'Configurations', label_ar: 'الإعدادات', route: 'inventory-config' },
]

const activeTab = computed(() => INVENTORY_ROUTES[route.name] || null)

function navigate(tab) {
  router.push({ name: tab.route })
}
</script>

<style scoped>
.inv-subnav {
  display: flex;
  align-items: center;
  height: 44px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 0 24px;
  flex-shrink: 0;
  overflow: hidden;
}
.inv-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  width: 100%;
}
.inv-tabs::-webkit-scrollbar { display: none; }
.inv-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  background: none;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  font-family: inherit;
}
.inv-tab:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.inv-tab.active {
  background: var(--bg-primary-faded);
  color: var(--color-primary);
  font-weight: 600;
}
.inv-tab-icon { font-size: 18px; }

@media (max-width: 767px) {
  .inv-subnav { padding: 0 12px; }
  .inv-tab { padding: 6px 10px; font-size: 12px; }
  .inv-tab-icon { font-size: 16px; }
}
</style>

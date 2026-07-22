<template>
  <div class="inv-subnav" :dir="dir" @mouseleave="openTab = null">
    <nav class="inv-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="inv-tab-wrap"
        @mouseenter="openTab = tab.id"
      >
        <button
          :class="['inv-tab', { active: activeTab === tab.id, open: openTab === tab.id }]"
        >
          <span class="material-symbols-outlined inv-tab-icon">{{ tab.icon }}</span>
          <span class="inv-tab-label">{{ isRTL && tab.label_ar ? tab.label_ar : tab.label }}</span>
          <span class="material-symbols-outlined inv-tab-arrow" v-if="tab.items.length">expand_more</span>
        </button>
        <Transition name="subnav-dropdown">
          <div v-if="openTab === tab.id && tab.items.length" class="inv-dropdown">
            <button
              v-for="item in tab.items"
              :key="item.route"
              :class="['inv-dropdown-item', { active: route.name === item.route }]"
              @click="go(item)"
            >
              <span class="material-symbols-outlined">{{ item.icon }}</span>
              <span>{{ isRTL && item.label_ar ? item.label_ar : item.label }}</span>
            </button>
          </div>
        </Transition>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n.js'

const route = useRoute()
const router = useRouter()
const { isRTL } = useI18n()
const { dir } = useI18n()

const openTab = ref(null)

const INVENTORY_ROUTES = {
  'inventory-overview': 'overview',
  products: 'products',
  'product-detail': 'products',
  categories: 'products',
  barcodes: 'products',
  attributes: 'products',
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
  uom: 'configurations',
  'uom-conversions': 'configurations',
}

const tabs = [
  {
    id: 'overview', icon: 'grid_view',
    label: 'Overview', label_ar: 'نظرة عامة',
    items: [
      { label: 'Inventory Overview', label_ar: 'نظرة عامة على المخزون', icon: 'grid_view', route: 'inventory-overview' },
    ],
  },
  {
    id: 'products', icon: 'inventory_2',
    label: 'Products', label_ar: 'المنتجات',
    items: [
      { label: 'Products', label_ar: 'المنتجات', icon: 'inventory_2', route: 'products' },
      { label: 'Barcodes', label_ar: 'الباركود', icon: 'qr_code_scanner', route: 'barcodes' },
      { label: 'Attributes', label_ar: 'الخصائص', icon: 'list_alt', route: 'attributes' },
      { label: 'Categories', label_ar: 'التصنيفات', icon: 'category', route: 'categories' },
    ],
  },
  {
    id: 'stock', icon: 'warehouse',
    label: 'Stock', label_ar: 'المخزون',
    items: [
      { label: 'Stock Levels', label_ar: 'مستويات المخزون', icon: 'warehouse', route: 'inventory' },
      { label: 'Stock Movements', label_ar: 'حركات المخزون', icon: 'swap_vert', route: 'stock-movements' },
      { label: 'Stock Adjustments', label_ar: 'تسوية المخزون', icon: 'swipe_up_alt', route: 'stock-adjustments' },
      { label: 'Inventory Counts', label_ar: 'جرد المخزون', icon: 'fact_check', route: 'inventory-counts' },
      { label: 'Batch Numbers', label_ar: 'أرقام الدفعات', icon: 'inventory_2', route: 'batch-numbers' },
      { label: 'Serial Numbers', label_ar: 'الأرقام التسلسلية', icon: 'qr_code', route: 'serial-numbers' },
    ],
  },
  {
    id: 'warehouse', icon: 'factory',
    label: 'Warehouse', label_ar: 'المستودعات',
    items: [
      { label: 'Warehouses', label_ar: 'المستودعات', icon: 'factory', route: 'warehouses' },
      { label: 'Pick Lists', label_ar: 'قوائم التجهيز', icon: 'assignment', route: 'pick-lists' },
    ],
  },
  {
    id: 'reports', icon: 'bar_chart',
    label: 'Reports', label_ar: 'التقارير',
    items: [
      { label: 'Inventory Reports', label_ar: 'تقارير المخزون', icon: 'bar_chart', route: 'inventory-reports' },
    ],
  },
  {
    id: 'configurations', icon: 'settings',
    label: 'Configurations', label_ar: 'الإعدادات',
    items: [
      { label: 'Inventory Config', label_ar: 'إعدادات المخزون', icon: 'settings', route: 'inventory-config' },
      { label: 'UOM', label_ar: 'وحدات القياس', icon: 'straighten', route: 'uom' },
      { label: 'UOM Conversions', label_ar: 'تحويلات الوحدات', icon: 'swap_horiz', route: 'uom-conversions' },
    ],
  },
]

const activeTab = computed(() => INVENTORY_ROUTES[route.name] || null)

function go(item) {
  openTab.value = null
  router.push({ name: item.route })
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
  position: relative;
  z-index: 200;
}
.inv-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow: visible;
  width: 100%;
}
.inv-tab-wrap {
  position: relative;
  flex-shrink: 0;
}
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
.inv-tab.open {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}
.inv-tab-icon { font-size: 18px; }
.inv-tab-arrow { font-size: 16px; transition: transform 0.2s; }
.inv-tab.open .inv-tab-arrow { transform: rotate(180deg); }

.inv-dropdown {
  position: absolute;
  top: 100%;
  inset-inline-start: 0;
  min-width: 200px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 300;
  margin-top: 4px;
}
.inv-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: none;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  font-family: inherit;
  text-align: left;
}
.inv-dropdown-item:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.inv-dropdown-item.active { background: var(--bg-primary-faded); color: var(--color-primary); font-weight: 600; }
.inv-dropdown-item .material-symbols-outlined { font-size: 18px; }
[dir="rtl"] .inv-dropdown-item { text-align: right; }

.subnav-dropdown-enter-active, .subnav-dropdown-leave-active { transition: opacity 0.12s, transform 0.12s; }
.subnav-dropdown-enter-from, .subnav-dropdown-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 767px) {
  .inv-subnav { padding: 0 12px; }
  .inv-tab { padding: 6px 10px; font-size: 12px; }
  .inv-tab-icon { font-size: 16px; }
}
</style>

<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ locale === 'ar-EG' ? 'المخزون' : 'Inventory' }}</h1>
        <p class="page-subtitle">{{ locale === 'ar-EG' ? 'عرض مستويات المخزون لكل منتج ومستودع' : 'View stock levels by product and warehouse' }}</p>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">warehouse</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('sku') }}</th>
              <th>{{ t('name') }}</th>
              <th>Warehouse</th>
              <th class="text-center">{{ locale === 'ar-EG' ? 'الكمية' : 'Qty' }}</th>
              <th class="text-center">{{ locale === 'ar-EG' ? 'حد إعادة الطلب' : 'Reorder' }}</th>
              <th class="text-center">{{ locale === 'ar-EG' ? 'الحالة' : 'Status' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" :class="{ 'row-warning': isLowStock(item) }">
              <td class="cell-sku">{{ productSku(item.product_id) }}</td>
              <td class="cell-name">{{ productName(item.product_id) }}</td>
              <td>{{ warehouseName(item.warehouse_id) }}</td>
              <td class="text-center mono">{{ item.qty }}</td>
              <td class="text-center mono">{{ item.reorder_level }}</td>
              <td class="text-center">
                <span :class="stockBadge(item)">{{ stockLabel(item) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useWebSocket } from '../../composables/useWebSocket.js'
import { useAuthStore } from '../../stores/auth.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir, locale } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])
const products = ref([])
const warehouses = ref([])

const auth = useAuthStore()
const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
wsInventory.on('stock_updated', () => {
  console.log('[WS] stock_updated received, refreshing inventory')
  loadLookups()
  load()
})

function productSku(id) {
  const p = products.value.find(x => x.id === id)
  return p ? p.sku : `#${id}`
}

function productName(id) {
  const p = products.value.find(x => x.id === id)
  return p ? p.name : `#${id}`
}

function warehouseName(id) {
  const w = warehouses.value.find(x => x.id === id)
  return w ? w.name : `#${id}`
}

function isLowStock(item) {
  return item.qty <= item.reorder_level && item.qty > 0
}

function stockBadge(item) {
  if (item.qty <= 0) return 'badge badge-danger'
  if (isLowStock(item)) return 'badge badge-warning'
  return 'badge badge-active'
}

function stockLabel(item) {
  const zero = locale.value === 'ar-EG' ? 'نفد' : 'Out'
  const low = locale.value === 'ar-EG' ? 'منخفض' : 'Low'
  const ok = locale.value === 'ar-EG' ? 'جيد' : 'OK'
  if (item.qty <= 0) return zero
  if (isLowStock(item)) return low
  return ok
}

async function loadLookups() {
  try {
    const [pRes, wRes] = await Promise.all([
      api.get('/T0003I/'),
      api.get('/T0008I/').catch(() => ({ data: [] })),
    ])
    products.value = pRes.data || []
    warehouses.value = wRes.data || []
  } catch {}
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0009I/')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadLookups(); load() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.row-warning td { background: #fffbeb; }
.text-center { text-align: center; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.cell-sku { font-family: monospace; font-size: 12px; color: #888; }
.cell-name { font-weight: 600; color: #1a1a2e; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-danger { background: #fee2e2; color: #dc2626; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .text-center { text-align: center; }
</style>

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ product.name || t('loading') }}</h1>
        <p class="page-subtitle">{{ t('product-detail-sub') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="$router.push('/products')">{{ t('back') }}</button>
        <button class="btn-primary" @click="showEdit = true">{{ t('edit') }}</button>
      </div>
    </div>

    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="product">
      <div class="detail-grid">
        <div class="data-card">
          <div class="card-header"><h3>{{ t('basic-info') }}</h3></div>
          <div class="card-body">
            <div class="info-row"><span class="info-label">{{ t('sku') }}</span><span class="info-value cell-mono">{{ product.sku }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('category') }}</span><span class="info-value">{{ product.category || '-' }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('brand') }}</span><span class="info-value">{{ product.brand || '-' }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('price') }}</span><span class="info-value">${{ (product.price || 0).toFixed(2) }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('cost') }}</span><span class="info-value">${{ (product.cost_price || 0).toFixed(2) }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('tax') }}</span><span class="info-value">{{ ((product.tax_rate || 0) * 100).toFixed(1) }}%</span></div>
            <div class="info-row"><span class="info-label">{{ t('status') }}</span><span class="info-value"><span :class="product.is_active ? 'badge badge-active' : 'badge badge-inactive'">{{ product.is_active ? t('active') : t('inactive') }}</span></span></div>
            <div class="info-row" v-if="product.is_phantom"><span class="info-label">{{ t('phantom') }}</span><span class="info-value"><span class="badge badge-warning">{{ t('yes') }}</span></span></div>
          </div>
        </div>

        <div class="data-card">
          <div class="card-header"><h3>{{ t('stock-levels') }}</h3></div>
          <div class="card-body">
            <SkeletonTable v-if="stockLoading" :rows="3" :columns="3" />
            <div v-else-if="!stockLevels.length" class="empty-section">{{ t('no-stock') }}</div>
            <div v-else>
              <div class="stock-row" v-for="sl in stockLevels" :key="sl.id">
                <span class="warehouse-name">{{ sl.warehouse_name || sl.warehouse_id }}</span>
                <span class="stock-qty" :class="stockClass(sl)">{{ sl.qty }}</span>
                <span v-if="sl.reserved_qty" class="stock-reserved">({{ sl.reserved_qty }} {{ t('reserved') }})</span>
              </div>
            </div>
          </div>
        </div>

        <div class="data-card">
          <div class="card-header"><h3>{{ t('suppliers') }}</h3></div>
          <div class="card-body">
            <div v-if="supplierLinks.length">
              <div class="supplier-row" v-for="link in supplierLinks" :key="link.id">
                <span>{{ supplierName(link.supplier_id) }}</span>
                <span class="cell-mono">${{ (link.unit_cost || 0).toFixed(2) }}</span>
                <span class="cell-mono">{{ link.lead_time_days || '-' }}d</span>
                <span class="badge badge-sm" :class="link.is_preferred ? 'badge-active' : 'badge-inactive'">{{ link.is_preferred ? t('preferred') : '-' }}</span>
              </div>
            </div>
            <div v-else class="empty-section">{{ t('no-suppliers') }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const product = ref(null)
const stockLevels = ref([])
const stockLoading = ref(true)
const supplierLinks = ref([])
const suppliers = ref([])
const showEdit = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [prodRes, stockRes, suppRes, linksRes] = await Promise.all([
      api.get(`/T0003I/${route.params.id}`),
      api.get('/T0009I/', { params: { product_id: route.params.id } }),
      api.get('/T0011I/'),
      api.get(`/T0103I/by-product/${route.params.id}`),
    ])
    product.value = prodRes.data
    stockLevels.value = stockRes.data || []
    suppliers.value = suppRes.data || []
    supplierLinks.value = linksRes.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load product'
  } finally {
    loading.value = false
    stockLoading.value = false
  }
}

function supplierName(id) {
  const s = suppliers.value.find(x => x.id === id)
  return s ? s.name : `#${id}`
}

function stockClass(sl) {
  const avail = sl.qty - (sl.reserved_qty || 0)
  if (avail <= 0) return 'stock-out'
  if (avail <= (sl.reorder_level || 5)) return 'stock-low'
  return ''
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.header-actions { display: flex; gap: 10px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
.card-header { padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.card-header h3 { font-size: 14px; font-weight: 700; margin: 0; color: #1a1a2e; }
.card-body { padding: 16px 20px; }
.info-row { display: flex; padding: 8px 0; border-bottom: 1px solid #f8f8f8; font-size: 13px; }
.info-row:last-child { border-bottom: none; }
.info-label { color: #888; min-width: 100px; flex-shrink: 0; }
.info-value { color: #1a1a2e; font-weight: 500; }
.cell-mono { font-family: monospace; }
.stock-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f8f8f8; font-size: 13px; }
.stock-row:last-child { border-bottom: none; }
.warehouse-name { flex: 1; color: #555; }
.stock-qty { font-weight: 700; min-width: 40px; text-align: right; }
.stock-reserved { color: #d97706; font-size: 11px; }
.stock-out { color: #dc2626; }
.stock-low { color: #d97706; }
.supplier-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.supplier-row span { min-width: 60px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-sm { font-size: 10px !important; padding: 1px 6px !important; }
.empty-section { font-size: 12px; color: #999; padding: 12px 0; text-align: center; }
</style>

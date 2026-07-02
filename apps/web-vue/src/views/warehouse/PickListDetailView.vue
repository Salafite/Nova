<template>
  <div :dir="dir">
    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="pickList">
      <div class="flex justify-between items-center mb-6">
        <div>
          <button class="btn-link" @click="$router.push('/warehouse/pick-lists')">&larr; {{ t('back-to-pick-lists') }}</button>
          <h2 class="page-title">{{ t('pick-list') }} {{ pickList.pick_list_number }}</h2>
        </div>
        <div class="flex gap-2">
          <button v-if="pickList.status === 'Pending'" class="btn-primary" @click="startPicking">{{ t('start-picking') }}</button>
          <button v-if="pickList.status === 'In Progress'" class="btn-primary" @click="completePicking" :disabled="!allPicked">{{ t('complete-picking') }}</button>
        </div>
      </div>

      <div class="detail-card mb-4">
        <div class="info-row"><span class="info-label">{{ t('status') }}:</span><span class="badge" :class="statusBadge">{{ pickList.status }}</span></div>
        <div class="info-row"><span class="info-label">{{ t('order') }}:</span><a class="order-link" @click="$router.push(`/sales/${pickList.sales_order_id}`)">#{{ pickList.sales_order_id }}</a></div>
        <div class="info-row"><span class="info-label">{{ t('warehouse') }}:</span><span>{{ warehouseName }}</span></div>
        <div class="info-row"><span class="info-label">{{ t('progress') }}:</span><span>{{ pickList.progress_pct || 0 }}%</span></div>
        <div class="progress-bar-wrap mt-2">
          <div class="progress-bar" :style="{ width: (pickList.progress_pct || 0) + '%' }"></div>
        </div>
      </div>

      <div class="data-card">
        <div class="card-header"><h3 class="card-title">{{ t('items-to-pick') }}</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('product') }}</th>
                <th class="col-num">{{ t('qty-ordered') }}</th>
                <th class="col-num">{{ t('qty-picked') }}</th>
                <th class="text-center" v-if="pickList.status === 'In Progress'">{{ t('pick') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td class="cell-mono">{{ item.line_number }}</td>
                <td>{{ item.product_name || `#${item.product_id}` }}</td>
                <td class="col-num">{{ item.qty_ordered }}</td>
                <td class="col-num">{{ item.qty_picked }}</td>
                <td class="text-center" v-if="pickList.status === 'In Progress'">
                  <input type="number" class="pick-input" :value="item.qty_picked" :min="0" :max="item.qty_ordered" @change="updatePick(item, $event.target.value)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import ErrorState from '../../components/ErrorState.vue'

const route = useRoute()
const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const pickList = ref(null)
const items = ref([])
const warehouses = ref([])

const statusBadge = computed(() => {
  const map = { Pending: 'badge-warning', 'In Progress': 'badge-info', Completed: 'badge-active', Cancelled: 'badge-inactive' }
  return map[pickList.value?.status] || 'badge-inactive'
})

const warehouseName = computed(() => {
  if (!pickList.value?.warehouse_id) return '-'
  const w = warehouses.value.find(x => x.id === pickList.value.warehouse_id)
  return w ? w.name : `#${pickList.value.warehouse_id}`
})

const allPicked = computed(() => {
  return items.value.length > 0 && items.value.every(i => i.qty_picked >= i.qty_ordered)
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const [detailRes, whRes] = await Promise.all([
      api.get(`/T0101I/${id}/detail`),
      api.get('/T0008I/'),
    ])
    const data = detailRes.data
    pickList.value = { ...data }
    items.value = data.items || []
    warehouses.value = whRes.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

async function startPicking() {
  try {
    await api.post(`/T0101I/${pickList.value.id}/start`)
    toast('Picking started', 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Failed to start picking', 'error')
  }
}

async function updatePick(item, val) {
  const qty = parseFloat(val) || 0
  if (qty < 0 || qty > item.qty_ordered) return
  try {
    const res = await api.post(`/T0101I/${pickList.value.id}/pick-item/${item.id}`, { qty_picked: qty })
    item.qty_picked = res.data.qty_picked
    pickList.value.progress_pct = undefined
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Failed to update pick', 'error')
  }
}

async function completePicking() {
  try {
    await api.post(`/T0101I/${pickList.value.id}/complete`)
    toast('Pick list completed — order marked as shipped', 'success')
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Failed to complete picking', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.loading-state, .error-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mb-4 { margin-bottom: 16px; }
.mt-2 { margin-top: 8px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }

.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 8px; }
.btn-link:hover { text-decoration: underline; }
.order-link { color: #5d3fd3; cursor: pointer; }
.order-link:hover { text-decoration: underline; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.detail-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; }
.info-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; font-size: 13px; }
.info-label { color: #888; font-weight: 500; min-width: 80px; }

.progress-bar-wrap { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.progress-bar { height: 100%; background: #5d3fd3; border-radius: 4px; transition: width 0.3s; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
.card-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin: 0; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; }
.text-center { text-align: center; }

.pick-input { width: 70px; padding: 4px 6px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; text-align: center; }
.pick-input:focus { border-color: #5d3fd3; outline: none; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }

[dir="rtl"] .data-table th { text-align: right; }
</style>

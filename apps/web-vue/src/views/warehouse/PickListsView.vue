<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('pick-lists') }}</h2>
        <p class="page-subtitle">{{ t('pick-lists-sub') }}</p>
      </div>
    </div>

    <div v-if="!loading && !error" class="stats-row">
      <div class="stat-card"><div class="stat-num">{{ statusCounts.Pending }}</div><div class="stat-lbl">{{ t('pending') }}</div></div>
      <div class="stat-card"><div class="stat-num in-progress">{{ statusCounts['In Progress'] }}</div><div class="stat-lbl">{{ t('in-progress') }}</div></div>
      <div class="stat-card"><div class="stat-num completed">{{ statusCounts.Completed }}</div><div class="stat-lbl">{{ t('completed') }}</div></div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">assignment</span>
      <p>{{ t('no-pick-lists') }}</p>
    </div>

    <div v-else class="pick-grid">
      <div v-for="pl in items" :key="pl.id" class="pick-card" @click="$router.push(`/warehouse/pick-lists/${pl.id}`)">
        <div class="pick-card-header">
          <span class="pick-number">{{ pl.pick_list_number }}</span>
          <span class="badge" :class="statusBadge(pl.status)">{{ pl.status }}</span>
        </div>
        <div class="pick-card-body">
          <div class="pick-info"><span class="info-label">{{ t('order') }}:</span><span>#{{ pl.sales_order_id }}</span></div>
          <div class="pick-info"><span class="info-label">{{ t('items') }}:</span><span>{{ pl.item_count || '-' }}</span></div>
        </div>
        <div v-if="pl.progress_pct !== undefined" class="progress-bar-wrap">
          <div class="progress-bar" :style="{ width: pl.progress_pct + '%' }"></div>
          <span class="progress-text">{{ pl.progress_pct }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])

const statusCounts = computed(() => {
  const counts = { Pending: 0, 'In Progress': 0, Completed: 0 }
  for (const pl of items.value) {
    if (counts[pl.status] !== undefined) counts[pl.status]++
  }
  return counts
})

function statusBadge(status) {
  const map = { Pending: 'badge-warning', 'In Progress': 'badge-info', Completed: 'badge-active', Cancelled: 'badge-inactive' }
  return map[status] || 'badge-inactive'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0101I/')
    const raw = res.data || []
    const enriched = await Promise.all(raw.map(async (pl) => {
      try {
        const detail = await api.get(`/T0101I/${pl.id}/detail`)
        const d = detail.data
        return { ...pl, item_count: d.items?.length || 0, progress_pct: d.progress_pct || 0 }
      } catch {
        return { ...pl, item_count: 0, progress_pct: 0 }
      }
    }))
    items.value = enriched
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }

.stats-row { display: flex; gap: 16px; margin-bottom: 20px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px 24px; flex: 1; text-align: center; }
.stat-num { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-num.in-progress { color: #0284c7; }
.stat-num.completed { color: #16a34a; }
.stat-lbl { font-size: 12px; color: #888; margin-top: 2px; }

.pick-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.pick-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; cursor: pointer; transition: box-shadow 0.15s; }
.pick-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.pick-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.pick-number { font-family: monospace; font-weight: 700; color: #5d3fd3; font-size: 14px; }
.pick-card-body { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.pick-info { display: flex; gap: 8px; font-size: 13px; }
.info-label { color: #888; min-width: 50px; }

.progress-bar-wrap { height: 6px; background: #f0f0f0; border-radius: 3px; position: relative; overflow: visible; }
.progress-bar { height: 100%; background: #5d3fd3; border-radius: 3px; transition: width 0.3s; }
.progress-text { position: absolute; right: 0; top: -18px; font-size: 11px; color: #888; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f3f4f6; color: #888; }
</style>

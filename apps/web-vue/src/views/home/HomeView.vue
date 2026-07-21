<template>
  <div class="home" :dir="dir">
    <!-- 1. Greeting Bar -->
    <section class="greeting">
      <span class="accent-bar" aria-hidden="true"></span>
      <div class="greeting-body">
        <h1>{{ t('welcome') }} {{ userName }}</h1>
        <p class="sub-greeting">{{ subGreeting }}</p>
      </div>
    </section>

    <!-- 2. Search Box -->
    <div class="search-box">
      <span class="search-icon" aria-hidden="true">
        <span class="material-symbols-outlined">search</span>
      </span>
      <input
        ref="searchInputRef"
        v-model="searchQuery"
        type="text"
        :placeholder="t('home.search-placeholder')"
        @keydown.escape="clearSearch"
      />
      <kbd class="search-hint">/</kbd>
    </div>

    <!-- 3. Stats Bar -->
    <div class="stats">
      <StatsCard
        v-for="tile in statTiles"
        :key="tile.key"
        :label="t(tile.labelKey)"
        :value="tile.value"
        :to="tile.to"
      />
    </div>

    <!-- 4. App Card Grid -->
    <div class="apps">
      <SkeletonTable v-if="appsLoading" :rows="2" :columns="6" />
      <template v-else-if="filteredCards.length">
        <button
          v-for="card in filteredCards"
          :key="card.id"
          class="app-card"
          type="button"
          @click="goTo(card)"
        >
          <span class="app-icon" :style="{ background: colorFor(card.module) }">
            <span class="material-symbols-outlined filled">{{ card.icon }}</span>
          </span>
          <span class="app-label">{{ displayLabel(card) }}</span>
        </button>
      </template>
      <div v-else class="apps-empty">{{ t('home.search-empty') }}</div>
    </div>

    <!-- 5 & 6. Chart + Insights -->
    <div class="bottom">
      <div class="chart-card">
        <div class="card-head">
          <h2>{{ t('home.chart-title') }}</h2>
          <span class="live-badge">● {{ t('home.chart-live') }}</span>
        </div>
        <div v-if="chartBars.length" class="chart-bars">
          <div
            v-for="bar in chartBars"
            :key="bar.key"
            class="chart-bar"
            :style="{ height: bar.heightPct + '%', background: bar.color }"
            :title="`${bar.label}: ${bar.value}`"
          ></div>
        </div>
        <div v-else class="chart-empty">{{ t('home.chart-empty') }}</div>
      </div>

      <div class="insights-card">
        <div class="card-head">
          <h2>{{ t('home.insights-title') }}</h2>
        </div>
        <div class="insight-row" v-for="row in insightRows" :key="row.key">
          <span class="insight-icon" :style="{ color: row.color }">
            <span class="material-symbols-outlined">{{ row.icon }}</span>
          </span>
          <span class="insight-label">{{ t(row.labelKey) }}</span>
          <span class="insight-value">{{ row.value }}</span>
        </div>
        <button class="view-reports-btn" type="button" @click="goToDashboard">
          {{ t('home.view-reports') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { useNavStore } from '../../stores/nav.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { api } from '../../api/client.js'
import StatsCard from '../../components/StatsCard.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'

/* ------------------------------------------------------------------ */
/* Module-level constants & cache                                     */
/* ------------------------------------------------------------------ */

// Persists across component mounts for the lifetime of the SPA session.
const statsCache = { data: null, timestamp: 0 }
const CACHE_TTL = 30000

const MODULE_COLORS = {
  dashboard: '#5d3fd3',
  products: '#0D9488',
  inventory: '#0EA5E9',
  warehouse: '#6366F1',
  customers: '#EC4899',
  suppliers: '#F59E0B',
  sales: '#22C55E',
  purchasing: '#F97316',
  finance: '#5C6BC0',
  uom: '#8B5CF6',
  pos: '#14B8A6',
  manufacturing: '#EF4444',
  planning: '#3B82F6',
  quality: '#84CC16',
  settings: '#64748B',
  admin: '#334155',
  modules: '#A855F7',
}

const CHART_COLORS = ['#cabeff', '#5d3fd3', '#cabeff', '#5d3fd3', '#cabeff']

/* ------------------------------------------------------------------ */
/* Pure helpers (unit-testable, no Vue dependency)                    */
/* ------------------------------------------------------------------ */

/**
 * Normalizes wildly-shaped "count" responses:
 * a bare number, { count }, { total }, an array, or a nested { data }.
 */
export function extractCount(payload) {
  if (payload == null) return 0
  if (typeof payload === 'number') return payload
  if (Array.isArray(payload)) return payload.length
  if (typeof payload === 'object') {
    if (typeof payload.count === 'number') return payload.count
    if (typeof payload.total === 'number') return payload.total
    if (payload.data !== undefined) return extractCount(payload.data)
  }
  return 0
}

/**
 * Normalizes wildly-shaped "list" responses into a plain array.
 */
export function extractArray(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  if (payload && payload.data && Array.isArray(payload.data.items)) return payload.data.items
  if (payload && Array.isArray(payload.items)) return payload.items
  if (payload && Array.isArray(payload.results)) return payload.results
  return []
}

export function computeAlertCount(products) {
  return products.filter((p) => {
    const stock = p.stock ?? 0
    const minStock = p.minStock ?? p.min_stock ?? 0
    return stock > 0 && stock < minStock
  }).length
}

/* ------------------------------------------------------------------ */
/* Composable: home stats (products list + 4 counts), with 30s cache  */
/* ------------------------------------------------------------------ */

function useHomeStats({ toast, t }) {
  const products = ref([])
  const counts = reactive({ suppliers: 0, salesOrders: 0, purchaseOrders: 0, uoms: 0 })
  const loading = ref(true)

  const alertCount = computed(() => computeAlertCount(products.value))

  function applyPayload(payload) {
    products.value = payload.products
    counts.suppliers = payload.suppliers
    counts.salesOrders = payload.salesOrders
    counts.purchaseOrders = payload.purchaseOrders
    counts.uoms = payload.uoms
  }

  async function fetchFresh() {
    // Every individual request is defensive: a single failing endpoint
    // degrades that stat to zero/empty rather than failing the page.
    const [prodRes, supRes, soRes, poRes, uomRes] = await Promise.all([
      api.get('/T0003I/').catch(() => null),
      api.get('/T0011I/count').catch(() => null),
      api.get('/T0012I/count').catch(() => null),
      api.get('/T0014I/count').catch(() => null),
      api.get('/T0001I/count').catch(() => null),
    ])

    return {
      products: extractArray(prodRes?.data),
      suppliers: extractCount(supRes?.data),
      salesOrders: extractCount(soRes?.data),
      purchaseOrders: extractCount(poRes?.data),
      uoms: extractCount(uomRes?.data),
    }
  }

  async function load({ force = false } = {}) {
    loading.value = true
    const now = Date.now()

    if (!force && statsCache.data && now - statsCache.timestamp < CACHE_TTL) {
      applyPayload(statsCache.data)
      loading.value = false
      return
    }

    try {
      const payload = await fetchFresh()
      statsCache.data = payload
      statsCache.timestamp = now
      applyPayload(payload)
    } catch (err) {
      toast(t('failed-load'), 'error')
    } finally {
      loading.value = false
    }
  }

  return { products, counts, loading, alertCount, load }
}

/* ------------------------------------------------------------------ */
/* Composable: chart bars derived from stats                          */
/* ------------------------------------------------------------------ */

function useChartData(stats) {
  return computed(() => {
    const entries = [
      { key: 'products', label: 'P', value: stats.products.value.length },
      { key: 'suppliers', label: 'S', value: stats.counts.suppliers },
      { key: 'salesOrders', label: 'SO', value: stats.counts.salesOrders },
      { key: 'purchaseOrders', label: 'PO', value: stats.counts.purchaseOrders },
      { key: 'uoms', label: 'U', value: stats.counts.uoms },
    ]
    const max = Math.max(0, ...entries.map((e) => e.value))
    if (max === 0) return []
    return entries.map((e, i) => ({
      ...e,
      color: CHART_COLORS[i],
      heightPct: Math.max((e.value / max) * 100, 3),
    }))
  })
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

const router = useRouter()
const auth = useAuthStore()
const navStore = useNavStore()
const { t, dir, isRTL } = useI18n()
const { show: toast } = useToast()

const stats = useHomeStats({ toast, t })
const chartBars = useChartData(stats)

const appsLoading = ref(true)
const searchQuery = ref('')
const searchInputRef = ref(null)

const userName = computed(() => auth.user?.fullName || auth.user?.username || 'User')

const subGreeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return t('home.greeting.morning')
  if (hour < 18) return t('home.greeting.afternoon')
  return t('home.greeting.evening')
})

const statTiles = computed(() => [
  { key: 'products', labelKey: 'home.stats.products', value: stats.products.value.length, to: 'products' },
  { key: 'suppliers', labelKey: 'home.stats.suppliers', value: stats.counts.suppliers, to: 'suppliers' },
  { key: 'sales-orders', labelKey: 'home.stats.sales-orders', value: stats.counts.salesOrders, to: 'sales' },
  { key: 'purchase-orders', labelKey: 'home.stats.purchase-orders', value: stats.counts.purchaseOrders, to: 'purchasing' },
  { key: 'uoms', labelKey: 'home.stats.uoms', value: stats.counts.uoms, to: 'uom' },
])

const filteredCards = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return (navStore.items || [])
    .filter((item) => item.module && MODULE_COLORS[item.module])
    .filter((item) => {
      if (!q) return true
      const label = isRTL.value ? item.label_ar || item.label : item.label
      return (label || '').toLowerCase().includes(q)
    })
})

const insightRows = computed(() => [
  {
    key: 'sales-target',
    icon: 'trending_up',
    color: '#5d3fd3',
    labelKey: 'home.insights.sales-target',
    value: '82%',
  },
  {
    key: 'active-stock',
    icon: 'inventory',
    color: '#0D9488',
    labelKey: 'home.insights.active-stock',
    value: stats.products.value.length,
  },
  {
    key: 'pending-alerts',
    icon: 'warning',
    color: '#D97706',
    labelKey: 'home.insights.pending-alerts',
    value: stats.alertCount.value,
  },
  {
    key: 'invoices',
    icon: 'receipt',
    color: '#5C6BC0',
    labelKey: 'home.insights.invoices',
    // No invoice-count endpoint was specified for this page; wire one up
    // here if/when the API exposes it.
    value: 0,
  },
])

function colorFor(moduleKey) {
  return MODULE_COLORS[moduleKey] || 'var(--color-primary)'
}

function displayLabel(card) {
  return isRTL.value ? card.label_ar || card.label : card.label
}

function goTo(card) {
  router.push({ name: card.route || card.module })
}

function goToDashboard() {
  router.push({ name: 'dashboard' })
}

function clearSearch() {
  searchQuery.value = ''
  searchInputRef.value?.blur()
}

function handleKeydown(e) {
  const target = e.target
  const isTyping =
    target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)

  if (e.key === '/' && !isTyping) {
    e.preventDefault()
    searchInputRef.value?.focus()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)

  const navLoad = Promise.resolve(navStore.load())
    .catch(() => {
      toast(t('failed-load'), 'error')
    })
    .finally(() => {
      appsLoading.value = false
    })

  await Promise.allSettled([navLoad, stats.load()])
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.greeting {
  display: flex;
  align-items: stretch;
  gap: 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}

.accent-bar {
  width: 4px;
  background: var(--color-primary);
  flex-shrink: 0;
}

.greeting-body {
  padding: 16px 20px;
}

.greeting-body h1 {
  margin: 0 0 4px;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.sub-greeting {
  margin: 0;
  color: var(--text-primary);
  opacity: 0.7;
  font-size: 0.9rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 10px 14px;
}

.search-box:focus-within {
  box-shadow: 0 0 0 2px var(--color-primary);
  border-color: var(--color-primary);
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.search-icon {
  font-size: 20px;
  color: var(--text-muted);
  flex-shrink: 0;
  display: flex;
}

.search-hint {
  font-size: 0.75rem;
  color: var(--text-primary);
  opacity: 0.5;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 1px 6px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.apps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}

.app-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  cursor: pointer;
  color: inherit;
  font: inherit;
}

.app-card:hover {
  border-color: var(--color-primary);
}

.app-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.app-icon .filled { font-variation-settings: 'FILL' 1; }

.app-label {
  font-size: 0.85rem;
  text-align: center;
  color: var(--text-primary);
}

.apps-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 24px;
  color: var(--text-primary);
  opacity: 0.6;
}

.bottom {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
}

.chart-card,
.insights-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 16px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-head h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary);
}

.live-badge {
  font-size: 0.75rem;
  color: var(--color-primary);
}

.chart-bars {
  height: 150px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.chart-bar {
  flex: 1;
  border-radius: 4px 4px 0 0;
  min-height: 3%;
}

.chart-empty {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  opacity: 0.6;
}

.insight-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-default);
}

.insight-row:last-of-type {
  border-bottom: none;
}

.insight-icon {
  width: 28px;
  display: flex;
  justify-content: center;
}

.insight-label {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-primary);
}

.insight-value {
  font-weight: 600;
  color: var(--text-primary);
}

.view-reports-btn {
  margin-top: 12px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-primary);
  background: transparent;
  color: var(--color-primary);
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
}

.view-reports-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

/* RTL overrides */
[dir='rtl'] .greeting {
  flex-direction: row-reverse;
}

[dir='rtl'] .card-head {
  flex-direction: row-reverse;
}

[dir='rtl'] .insight-row {
  flex-direction: row-reverse;
}

@media (max-width: 900px) {
  .bottom {
    grid-template-columns: 1fr;
  }
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

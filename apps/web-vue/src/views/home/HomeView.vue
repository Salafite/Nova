<template>
  <section class="home">
    <SkeletonTable v-if="loading" />
    <template v-else>
      <div class="greeting" :dir="dir">
        <div class="greeting-bar"></div>
        <div class="greeting-body">
          <h1 class="greeting-title">{{ t('welcome') }} {{ userName }}</h1>
          <p class="greeting-sub">{{ timeGreeting }}</p>
        </div>
      </div>

      <div class="search-box">
        <span class="material-symbols-outlined search-icon">search</span>
        <input
          ref="searchRef"
          v-model="query"
          class="search-input"
          :placeholder="t('home.search-placeholder')"
          @keydown.escape="query = ''; $event.target.blur()"
        />
        <kbd v-if="!query" class="search-hint">/</kbd>
      </div>

      <div class="stats">
        <div v-for="s in statsList" :key="s.key" class="stat">
          <span class="stat-val">{{ s.value }}</span>
          <span class="stat-lbl">{{ s.label }}</span>
        </div>
      </div>

      <div class="apps">
        <div
          v-for="card in filteredCards"
          :key="card.id"
          class="app-card"
          @click="navigate(card.route)"
        >
          <div class="app-icon" :style="{ background: card.color }">
            <span class="material-symbols-outlined filled">{{ card.icon }}</span>
          </div>
          <span class="app-name">{{ card.label }}</span>
        </div>
        <div v-if="query && !filteredCards.length" class="apps-empty">
          <span class="material-symbols-outlined">search_off</span>
          <p>{{ t('home.search-empty') }}</p>
        </div>
      </div>

      <div class="bottom">
        <div class="chart-card">
          <div class="card-head">
            <h3>{{ t('home.chart-title') }}</h3>
            <span class="card-badge">● {{ t('home.chart-live') }}</span>
          </div>
          <div v-if="chartData.length" class="chart-bars">
            <div v-for="(b, i) in chartData" :key="i" class="bar-wrap">
              <div
                class="bar"
                :style="{ height: b.pct + '%', background: b.color }"
                :title="b.label"
              ></div>
              <span class="bar-label">{{ b.short }}</span>
            </div>
          </div>
          <p v-else class="chart-empty">{{ t('home.chart-empty') }}</p>
        </div>

        <div class="insights-card">
          <h3>{{ t('home.insights-title') }}</h3>
          <div class="insights-list">
            <div v-for="ins in insights" :key="ins.key" class="insight">
              <span
                class="material-symbols-outlined insight-icon"
                :style="{ color: ins.color }"
              >{{ ins.icon }}</span>
              <div class="insight-body">
                <span class="insight-lbl">{{ ins.label }}</span>
                <span class="insight-val" :style="{ color: ins.color }">{{ ins.value }}</span>
              </div>
            </div>
          </div>
          <button class="view-btn" @click="navigate('dashboard')">{{ t('home.view-reports') }}</button>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import { useNavStore } from '../../stores/nav.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { api } from '../../api/client.js'
import SkeletonTable from '../../components/SkeletonTable.vue'

const router = useRouter()
const auth = useAuthStore()
const navStore = useNavStore()
const { dir, isRTL, t } = useI18n()
const { show: toast } = useToast()

const loading = ref(true)
const query = ref('')
const searchRef = ref(null)
const userName = ref(auth.user?.fullName || auth.user?.username || 'User')

const stats = reactive({
  products: 0, suppliers: 0,
  salesOrders: 0, purchaseOrders: 0,
  uoms: 0, invoices: 0, alertCount: 0
})

const colorMap = {
  dashboard: '#8D6E63', products: '#5C6BC0', inventory: '#5C6BC0',
  warehouse: '#78909C', customers: '#66BB6A', suppliers: '#66BB6A',
  sales: '#EF5350', purchasing: '#EF5350', finance: '#26A69A',
  uom: '#7E57C2',
  pos: '#EC407A', manufacturing: '#AB47BC', planning: '#42A5F5',
  quality: '#26C6DA', settings: '#607D8B', admin: '#607D8B',
  modules: '#607D8B'
}

const labelArMap = {
  dashboard: 'لوحة البيانات', products: 'المنتجات', inventory: 'المخزون',
  warehouse: 'المستودعات', customers: 'العملاء', suppliers: 'الموردون',
  sales: 'المبيعات', purchasing: 'المشتريات', finance: 'المالية',
  uom: 'وحدات القياس',
  admin: 'المستخدمون والصلاحيات', modules: 'الوحدات', settings: 'الإعدادات',
  home: 'الرئيسية'
}

const chartColors = ['#cabeff', '#5d3fd3', '#cabeff', '#5d3fd3', '#cabeff']

const timeGreeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return t('home.greeting.morning')
  if (h < 17) return t('home.greeting.afternoon')
  return t('home.greeting.evening')
})

const statsList = computed(() => [
  { key: 'products', value: stats.products.toLocaleString(), label: t('home.stats.products') },
  { key: 'suppliers', value: stats.suppliers.toLocaleString(), label: t('home.stats.suppliers') },
  { key: 'salesOrders', value: stats.salesOrders.toLocaleString(), label: t('home.stats.sales-orders') },
  { key: 'purchaseOrders', value: stats.purchaseOrders.toLocaleString(), label: t('home.stats.purchase-orders') },
  { key: 'uoms', value: stats.uoms.toLocaleString(), label: t('home.stats.uoms') },
])

const appCards = computed(() =>
  navStore.items
    .filter(item => item.module && item.module !== 'home' && colorMap[item.module])
    .map(item => ({
      id: item.id,
      icon: item.icon,
      label: isRTL.value && labelArMap[item.module] ? labelArMap[item.module] : item.label,
      route: item.module,
      color: colorMap[item.module]
    }))
)

const filteredCards = computed(() => {
  if (!query.value) return appCards.value
  const q = query.value.toLowerCase()
  return appCards.value.filter(c => c.label.toLowerCase().includes(q))
})

const chartData = computed(() => {
  const max = Math.max(stats.products, stats.suppliers, stats.salesOrders, stats.purchaseOrders, stats.uoms, 1)
  const labels = [
    { short: 'P', full: t('home.stats.products') },
    { short: 'S', full: t('home.stats.suppliers') },
    { short: 'SO', full: t('home.stats.sales-orders') },
    { short: 'PO', full: t('home.stats.purchase-orders') },
    { short: 'U', full: t('home.stats.uoms') },
  ]
  const values = [stats.products, stats.suppliers, stats.salesOrders, stats.purchaseOrders, stats.uoms]
  return values.map((v, i) => ({
    label: labels[i].full,
    short: labels[i].short,
    pct: Math.round((v / max) * 100) || 3,
    color: chartColors[i]
  }))
})

const insights = computed(() => [
  {
    key: 'sales',
    icon: 'trending_up',
    color: '#5d3fd3',
    label: t('home.insights.sales-target'),
    value: t('home.sales-target-reached', { count: 82 }),
  },
  {
    key: 'stock',
    icon: 'inventory',
    color: '#0D9488',
    label: t('home.insights.active-stock'),
    value: t('home.items-count', { count: stats.products }),
  },
  {
    key: 'alerts',
    icon: 'warning',
    color: '#D97706',
    label: t('home.insights.pending-alerts'),
    value: t('home.critical-count', { count: stats.alertCount }),
  },
  {
    key: 'invoices',
    icon: 'receipt',
    color: '#5C6BC0',
    label: t('home.insights.invoices'),
    value: String(stats.invoices),
  },
])

function navigate(name) { router.push({ name }) }

function onKeydown(e) {
  if (e.key === '/' && document.activeElement !== searchRef.value) {
    e.preventDefault()
    searchRef.value?.focus()
  }
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  try {
    await navStore.load()
    const [prods, sups, sos, pos, uoms] = await Promise.all([
      api.get('/T0003I/').then(r => r.data || []).catch(() => []),
      api.get('/T0011I/').then(r => r.data || []).catch(() => []),
      api.get('/T0012I/').then(r => r.data || []).catch(() => []),
      api.get('/T0014I/').then(r => r.data || []).catch(() => []),
      api.get('/T0001I/').then(r => r.data || []).catch(() => []),
    ])
    stats.products = prods.length
    stats.suppliers = sups.length
    stats.salesOrders = sos.length
    stats.purchaseOrders = pos.length
    stats.uoms = uoms.length
    stats.invoices = 0
    stats.alertCount = prods.filter(p => (p.stock || 0) > 0 && (p.stock || 0) < (p.minStock || 5)).length
  } catch (e) {
    toast(t('failed-load'), 'error')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
}

/* ── Greeting ── */
.greeting {
  display: flex;
  gap: 16px;
  align-items: stretch;
  margin-bottom: 24px;
}
.greeting-bar {
  width: 4px;
  background: var(--color-primary);
  border-radius: 4px;
  flex-shrink: 0;
}
.greeting-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.greeting-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.greeting-sub {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Search ── */
.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 0 14px;
  margin-bottom: 24px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--bg-primary-faded);
}
.search-icon {
  font-size: 20px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  height: 48px;
  border: none;
  background: none;
  font-size: 15px;
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
}
.search-input::placeholder { color: var(--text-faint); }
.search-hint {
  font-size: 12px;
  color: var(--text-faint);
  background: var(--bg-body);
  border: 1px solid var(--border-light);
  border-radius: 4px;
  padding: 2px 7px;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}

/* ── Stats ── */
.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 24px;
}
.stat {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 14px 12px;
  text-align: center;
}
.stat-val {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.1;
}
.stat-lbl {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* ── App Grid ── */
.apps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 24px;
}
.app-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.app-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  transform: translateY(-2px);
  border-color: var(--color-primary);
}
.app-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: transform 0.2s;
}
.app-card:hover .app-icon { transform: translateY(-3px); }
.app-icon .material-symbols-outlined { font-size: 26px; }
.app-icon .filled { font-variation-settings: 'FILL' 1; }
.app-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: center;
  line-height: 1.2;
}
.app-card:hover .app-name { color: var(--color-primary); }

.apps-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--text-faint);
}
.apps-empty .material-symbols-outlined { font-size: 40px; }
.apps-empty p { font-size: 13px; }

/* ── Bottom Grid ── */
.bottom {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
}
.chart-card,
.insights-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.card-head h3,
.insights-card h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.card-badge {
  font-size: 11px;
  color: var(--color-success);
  font-weight: 600;
}
.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 150px;
  padding: 0 4px;
}
.bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  height: 100%;
}
.bar {
  width: 100%;
  border-radius: 4px 4px 0 0;
  transition: opacity 0.2s;
  min-height: 4px;
  align-self: flex-end;
}
.bar:hover { opacity: 0.7; }
.bar-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  flex-shrink: 0;
}
.chart-empty {
  text-align: center;
  padding: 50px 0;
  color: var(--text-faint);
  font-size: 13px;
}

.insights-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}
.insight {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-body);
  border-radius: 8px;
}
.insight-icon { font-size: 20px; }
.insight-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.insight-lbl { font-size: 11px; color: var(--text-muted); }
.insight-val { font-size: 14px; font-weight: 700; }
.view-btn {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  font-weight: 700;
  border-radius: 8px;
  background: none;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 13px;
  font-family: inherit;
}
.view-btn:hover { background: var(--bg-primary-faded); }

/* ── RTL ── */
[dir="rtl"] .greeting { flex-direction: row-reverse; }
[dir="rtl"] .insight { flex-direction: row-reverse; }
[dir="rtl"] .card-head { flex-direction: row-reverse; }
</style>

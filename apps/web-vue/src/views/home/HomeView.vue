<template>
  <section class="home" :dir="dir">
    <SkeletonTable v-if="loading" />
    <div v-else>
      <div class="header">
        <div>
          <h2 class="greeting">{{ locale === 'ar-EG' ? 'مرحباً،' : 'Welcome,' }} {{ userName }}</h2>
          <p class="subtitle">{{ locale === 'ar-EG' ? 'اختر تطبيقاً لبدء سير عملك.' : 'Select an application to start your workflow.' }}</p>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-num">{{ stats.products }}</span>
          <span class="stat-lbl">{{ locale === 'ar-EG' ? 'المنتجات' : 'Products' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ stats.suppliers }}</span>
          <span class="stat-lbl">{{ locale === 'ar-EG' ? 'الموردون' : 'Suppliers' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ stats.salesOrders }}</span>
          <span class="stat-lbl">{{ locale === 'ar-EG' ? 'أوامر البيع' : 'Sales Orders' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ stats.purchaseOrders }}</span>
          <span class="stat-lbl">{{ locale === 'ar-EG' ? 'أوامر الشراء' : 'Purchase Orders' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ stats.uoms }}</span>
          <span class="stat-lbl">{{ locale === 'ar-EG' ? 'وحدات القياس' : 'UOMs' }}</span>
        </div>
      </div>

      <div class="app-grid">
        <div v-for="card in appCards" :key="card.id" class="app-card" @click="navigate(card.route)">
          <div class="app-icon" :class="'icon-' + card.id" :style="{ backgroundColor: card.color }">
            <span class="material-symbols-outlined filled">{{ card.icon }}</span>
          </div>
          <span class="app-label">{{ card.label }}</span>
        </div>
      </div>

      <div class="bottom-grid">
        <div class="chart-card">
          <div class="card-head">
            <h3>{{ locale === 'ar-EG' ? 'أداء الشركة' : 'Company Performance' }}</h3>
            <span class="badge">{{ locale === 'ar-EG' ? 'مباشر' : 'Live' }}</span>
          </div>
          <div class="chart-bars">
            <div v-for="(bar, i) in chartData" :key="i" class="bar" :style="{ height: bar.pct + '%', background: bar.color }" :title="locale === 'ar-EG' ? bar.labelAr : bar.label"></div>
          </div>
          <div v-if="!chartData.length" class="chart-empty">{{ locale === 'ar-EG' ? 'لا توجد بيانات' : 'No data available' }}</div>
        </div>

        <div class="insights-card">
          <h3>{{ locale === 'ar-EG' ? 'نظرة سريعة' : 'Quick Insights' }}</h3>
          <div class="insights-list">
            <div class="insight-item">
              <span class="material-symbols-outlined insight-icon trending">trending_up</span>
              <div>
                <p class="insight-label">{{ locale === 'ar-EG' ? 'هدف المبيعات' : 'Sales Target' }}</p>
                <p class="insight-value trending">82% {{ locale === 'ar-EG' ? 'تم تحقيقه' : 'Reached' }}</p>
              </div>
            </div>
            <div class="insight-item">
              <span class="material-symbols-outlined insight-icon stock">inventory</span>
              <div>
                <p class="insight-label">{{ locale === 'ar-EG' ? 'المخزون النشط' : 'Active Stock' }}</p>
                <p class="insight-value stock">{{ stats.products }} {{ locale === 'ar-EG' ? 'صنف' : 'Items' }}</p>
              </div>
            </div>
            <div class="insight-item">
              <span class="material-symbols-outlined insight-icon warning">warning</span>
              <div>
                <p class="insight-label">{{ locale === 'ar-EG' ? 'المنبهات المعلقة' : 'Pending Alerts' }}</p>
                <p class="insight-value warning">{{ stats.alertCount }} {{ locale === 'ar-EG' ? 'حرجة' : 'Critical' }}</p>
              </div>
            </div>
            <div class="insight-item">
              <span class="material-symbols-outlined insight-icon invoice">receipt</span>
              <div>
                <p class="insight-label">{{ locale === 'ar-EG' ? 'الفواتير' : 'Invoices' }}</p>
                <p class="insight-value invoice">{{ stats.invoices }}</p>
              </div>
            </div>
          </div>
          <button class="view-btn" @click="navigate('dashboard')">{{ locale === 'ar-EG' ? 'عرض التقارير التفصيلية' : 'View Detailed Reports' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
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
const { locale, dir, isRTL } = useI18n()
const { show: toast } = useToast()

const loading = ref(true)
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

const chartColors = ['#cabeff', '#5d3fd3', '#cabeff', '#5d3fd3', '#cabeff', '#5d3fd3']

const appCards = computed(() =>
  navStore.items
    .filter(item => item.module && item.module !== 'home' && colorMap[item.module])
    .map(item => ({
      id: item.id, icon: item.icon,
      label: locale.value === 'ar-EG' && labelArMap[item.module] ? labelArMap[item.module] : item.label,
      route: item.module, color: colorMap[item.module]
    }))
)

const chartData = computed(() => {
  const max = Math.max(stats.products, stats.suppliers, stats.salesOrders, stats.purchaseOrders, stats.uoms, 1)
  const labels = [
    { key: 'Products', ar: 'المنتجات' },
    { key: 'Suppliers', ar: 'الموردون' },
    { key: 'Sales Orders', ar: 'أوامر البيع' },
    { key: 'Purchase Orders', ar: 'أوامر الشراء' },
    { key: 'UOMs', ar: 'وحدات القياس' },
  ]
  const values = [stats.products, stats.suppliers, stats.salesOrders, stats.purchaseOrders, stats.uoms]
  return values.map((v, i) => ({
    label: labels[i].key,
    labelAr: labels[i].ar,
    pct: Math.round((v / max) * 100) || 3,
    color: chartColors[i]
  }))
})

function navigate(name) { router.push({ name }) }

onMounted(async () => {
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
    toast(locale.value === 'ar-EG' ? 'فشل تحميل بيانات الصفحة الرئيسية' : 'Failed to load homepage data', 'error')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home { max-width: 1200px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.greeting { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.subtitle { font-size: 14px; color: #666; margin-top: 4px; }

.stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-item { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; text-align: center; }
.stat-num { display: block; font-size: 26px; font-weight: 700; color: #5d3fd3; }
.stat-lbl { font-size: 12px; color: #666; margin-top: 4px; }

.app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; margin-bottom: 24px; }
.app-card { display: flex; flex-direction: column; align-items: center; padding: 16px 8px; background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
.app-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.app-icon { width: 56px; height: 56px; border-radius: 14px; display: flex; align-items: center; justify-content: center; color: #fff; margin-bottom: 8px; transition: transform 0.2s; }
.app-card:hover .app-icon { transform: translateY(-4px); }
.app-icon .material-symbols-outlined { font-size: 28px; }
.app-icon .filled { font-variation-settings: 'FILL' 1; }
.app-label { font-size: 13px; font-weight: 600; color: #333; text-align: center; }
.app-card:hover .app-label { color: #5d3fd3; }

.bottom-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
.chart-card, .insights-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 24px; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-head h3, .insights-card h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.badge { font-size: 11px; color: #666; }
.chart-bars { display: flex; align-items: flex-end; gap: 8px; height: 180px; padding: 0 8px; }
.bar { flex: 1; border-radius: 6px 6px 0 0; transition: opacity 0.2s; min-height: 6px; }
.bar:hover { opacity: 0.7; }
.chart-empty { text-align: center; padding: 60px 0; color: #999; font-size: 13px; }

.insights-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.insight-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: #f5f5f9; border-radius: 8px; }
.insight-label { font-size: 11px; color: #666; }
.insight-value { font-size: 14px; font-weight: 700; margin-top: 2px; }
.insight-icon { font-size: 20px; }
.insight-icon.trending { color: #5d3fd3; }
.insight-icon.stock { color: #008080; }
.insight-icon.warning { color: #ba1a1a; }
.insight-icon.invoice { color: #26A69A; }
.insight-value.trending { color: #5d3fd3; }
.insight-value.stock { color: #008080; }
.insight-value.warning { color: #ba1a1a; }
.insight-value.invoice { color: #26A69A; }

.view-btn { width: 100%; margin-top: 12px; padding: 10px; border: 1px solid #5d3fd3; color: #5d3fd3; font-weight: 700; border-radius: 8px; background: none; cursor: pointer; transition: all 0.15s; }
.view-btn:hover { background: #e6deff; }

[dir="rtl"] .header { flex-direction: row-reverse; }
[dir="rtl"] .insight-item { flex-direction: row-reverse; }
[dir="rtl"] .card-head { flex-direction: row-reverse; }
[dir="rtl"] .greeting { text-align: right; }
[dir="rtl"] .subtitle { text-align: right; }
[dir="rtl"] .badge { text-align: left; }
</style>

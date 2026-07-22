<template>
  <div :dir="dir">
    <header class="modules-header">
      <div class="modules-header-text">
        <h1 class="modules-title">{{ t('module-manager') }}</h1>
        <p class="modules-subtitle">{{ t('module-sub') }}</p>
      </div>
      <button class="scan-btn" @click="scanModules" :disabled="scanning">
        <span class="material-symbols-outlined">refresh</span>
        {{ scanning ? t('scanning') : t('scan-modules') }}
      </button>
    </header>

    <div class="modules-stats">
      <div class="stat" aria-label="13 total modules">
        <span class="stat-value">{{ MODULE_MAP.length }}</span>
        <span class="stat-label">{{ t('modules') }}</span>
      </div>
      <div class="stat" aria-label="63 total sub-modules">
        <span class="stat-value">{{ totalSubModules }}</span>
        <span class="stat-label">{{ t('sub-modules') }}</span>
      </div>
      <div class="stat" aria-label="installed modules">
        <span class="stat-value">{{ installedCount }}</span>
        <span class="stat-label">{{ t('installed') }}</span>
      </div>
      <div class="stat" aria-label="active modules">
        <span class="stat-value accent">{{ activeCount }}</span>
        <span class="stat-label">{{ t('active') }}</span>
      </div>
    </div>

    <div class="modules-filter" role="tablist">
      <button
        v-for="f in filterOptions"
        :key="f.key"
        :class="['filter-chip', { active: activeFilter === f.key }]"
        @click="activeFilter = f.key"
        role="tab"
        :aria-selected="activeFilter === f.key"
      >{{ f.label }}</button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadInstalled" />

    <template v-else>
      <div v-if="filteredModules.length" class="modules-grid">
        <article
          v-for="mod in filteredModules"
          :key="mod.id"
          class="module-card"
          :style="{ '--cat-color': mod.color }"
        >
          <div class="card-accent" :style="{ '--accent': mod.color }"></div>
          <div class="card-body">
            <div class="card-head">
              <span class="card-icon material-symbols-outlined" aria-hidden="true">{{ mod.icon }}</span>
              <div class="card-title-block">
                <h2 class="card-name">{{ mod.name }}</h2>
                <span class="card-meta">{{ mod.subs.length }} {{ t('sub-modules') }} · {{ statusLabel(mod) }}</span>
              </div>
            </div>

            <ul class="card-subs">
              <li v-for="sub in mod.subs" :key="sub" class="sub-row">
                <span :class="['sub-indicator', subDotClass(mod)]" aria-hidden="true"></span>
                <span class="sub-label">{{ sub }}</span>
              </li>
            </ul>

            <div class="card-foot">
              <span class="foot-tag">UI: {{ mod.frontend }}</span>
              <span class="foot-tag">API: {{ mod.backend }}</span>
              <span v-if="mod.mcp" class="foot-tag">MCP: {{ mod.mcp }}</span>
            </div>

            <div class="card-actions" v-if="mod.installed || mod.available">
              <template v-if="mod.installed">
                <button
                  v-if="!mod.isCore"
                  :class="['action-btn', mod.isActive ? 'action-warn' : 'action-neutral']"
                  @click="toggleModule(mod.installData)"
                  :title="mod.isActive ? t('disable') : t('enable')"
                  :aria-label="mod.isActive ? t('disable') : t('enable')"
                >
                  <span class="material-symbols-outlined">{{ mod.isActive ? 'toggle_off' : 'toggle_on' }}</span>
                  <span class="action-label">{{ mod.isActive ? t('disable') : t('enable') }}</span>
                </button>
                <button
                  v-if="!mod.isCore"
                  class="action-btn action-danger"
                  @click="uninstallModule(mod.installData)"
                  :title="t('uninstall')"
                  :aria-label="t('uninstall')"
                >
                  <span class="material-symbols-outlined">delete</span>
                  <span class="action-label">{{ t('uninstall') }}</span>
                </button>
              </template>
              <template v-else-if="mod.available">
                <button class="action-btn action-primary" @click="installModule(mod.installKey)">
                  <span class="material-symbols-outlined">download</span>
                  <span class="action-label">{{ t('install') }}</span>
                </button>
              </template>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="modules-empty">
        <span class="material-symbols-outlined empty-icon">extension_off</span>
        <p>{{ t('no-modules-filter') }}</p>
        <button class="reset-filter-btn" @click="activeFilter = 'all'">{{ t('filter-all') }}</button>
      </div>

      <details v-if="availableExtra.length" class="available-section" :open="showAvailable">
        <summary class="available-summary" @click.prevent="showAvailable = !showAvailable">
          <span class="material-symbols-outlined">{{ showAvailable ? 'expand_less' : 'expand_more' }}</span>
          <span class="available-heading">{{ t('available-modules') }}</span>
          <span class="available-badge">{{ availableExtra.length }}</span>
        </summary>
        <div v-if="showAvailable" class="available-grid">
          <div v-for="a in availableExtra" :key="a.module_key" class="extra-card">
            <div class="extra-body">
              <span class="extra-name">{{ a.name }}</span>
              <span class="extra-desc">{{ a.description }}</span>
            </div>
            <button
              v-if="!isInstalled(a.module_key)"
              class="install-btn"
              @click="installModule(a.module_key)"
            >{{ t('install') }}</button>
            <span v-else class="installed-tag">{{ t('installed') }}</span>
          </div>
        </div>
      </details>
    </template>

    <ConfirmDialog
      v-if="confirmTarget"
      :title="t('confirm-delete')"
      :message="t('confirm-delete-msg') + ' ' + confirmTarget.name"
      @confirm="executeUninstallModule(confirmTarget)"
      @cancel="confirmTarget = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const MODULE_MAP = [
  { id: 'foundation',    name: 'Foundation',     icon: 'layers',               color: '#4A6FA5', subs: ['Home', 'Dashboard', 'Products', 'Inventory', 'Warehouse', 'Batch Numbers', 'Serial Numbers'],              frontend: '16', backend: '9',  mcp: 'inventory, warehouse' },
  { id: 'accounting',    name: 'Accounting',     icon: 'account_balance',      color: '#2D6A4F', subs: ['Chart of Accounts', 'Journal Entries', 'Invoices', 'Payments', 'Payment Terms', 'Payment Methods', 'Finance'], frontend: '6',  backend: '7',  mcp: 'accounting' },
  { id: 'crm',           name: 'CRM',            icon: 'groups',               color: '#C96B3E', subs: ['Customers', 'Leads', 'Opportunities'],                                                             frontend: '4',  backend: '5',  mcp: 'crm' },
  { id: 'sales',         name: 'Sales',          icon: 'point_of_sale',         color: '#7C3AED', subs: ['Sales', 'Sales Orders', 'Quotations', 'Delivery', 'Sales Returns', 'Price Lists', 'Tax Rates', 'POS'], frontend: '8',  backend: '12', mcp: 'sales, pos' },
  { id: 'procurement',   name: 'Procurement',    icon: 'shopping_cart',         color: '#059669', subs: ['Suppliers', 'Purchasing', 'Purchase Requisitions', 'RFQs', 'Goods Receipt', 'Purchase Returns'],   frontend: '6',  backend: '14', mcp: 'purchasing, warehouse' },
  { id: 'administration', name: 'Administration', icon: 'admin_panel_settings', color: '#4A6FA5', subs: ['Admin', 'Module Manager', 'Settings', 'Notifications', 'Audit Log', 'Scheduled Tasks', 'Multi-Tenant', 'Workflow', 'Governance', 'Platform'], frontend: '10', backend: '10', mcp: 'admin, notifications' },
  { id: 'hr',            name: 'HR',             icon: 'badge',                color: '#C96B3E', subs: ['HRMS', 'Attendance', 'Leave', 'Payroll', 'Recruitment', 'Timesheets'],                             frontend: '9',  backend: '13', mcp: 'hr' },
  { id: 'bi',            name: 'BI',             icon: 'bar_chart',             color: '#6366F1', subs: ['BI Foundation', 'Executive Dashboards', 'Operational Analytics', 'Forecasting', 'AI & Insights'],  frontend: '5',  backend: '4',  mcp: 'bi' },
  { id: 'manufacturing', name: 'Manufacturing',  icon: 'precision_manufacturing', color: '#B45309', subs: ['Manufacturing', 'Quality', 'Shopfloor'],                                                      frontend: '4',  backend: '4',  mcp: 'manufacturing' },
  { id: 'planning',      name: 'Planning',       icon: 'calendar_month',        color: '#6366F1', subs: ['Planning', 'Resource Planning'],                                                             frontend: '2',  backend: '1',  mcp: '' },
  { id: 'mobile',        name: 'Mobile',         icon: 'phone_android',         color: '#0891B2', subs: ['Mobile Foundation', 'Mobile POS'],                                                             frontend: '—',  backend: '—',  mcp: '' },
  { id: 'integrations',  name: 'Integrations',   icon: 'integration_instructions', color: '#6B7280', subs: ['E-commerce', 'Third-Party', 'API Platform'],                                                  frontend: '3',  backend: '3',  mcp: '' },
  { id: 'service-projects', name: 'Service & Projects', icon: 'handyman',      color: '#C96B3E', subs: ['Service', 'Projects', 'Maintenance', 'Contracts & SLAs', 'Documents'],                          frontend: '8',  backend: '10', mcp: 'projects, maintenance' },
]

const loading = ref(true)
const error = ref('')
const scanning = ref(false)
const installed = ref([])
const available = ref([])
const activeFilter = ref('all')
const showAvailable = ref(false)
const confirmTarget = ref(null)

function normalizeKey(s) {
  return String(s || '').toLowerCase().replace(/[\s_-]+/g, '')
}

const installedLookup = computed(() => {
  const map = new Map()
  for (const m of installed.value) {
    const key = normalizeKey(m.module_key || m.name)
    if (key) map.set(key, m)
  }
  return map
})

const availableKeys = computed(() => {
  const set = new Set()
  for (const a of available.value) {
    const key = normalizeKey(a.module_key)
    if (key) set.add(key)
  }
  return set
})

const filterOptions = computed(() => {
  const names = MODULE_MAP.map(m => ({ key: m.id, label: m.name }))
  return [{ key: 'all', label: t('filter-all') }, ...names]
})

const filteredModules = computed(() => {
  const active = activeFilter.value
  const lookup = installedLookup.value
  const availKeys = availableKeys.value

  return MODULE_MAP
    .filter(m => active === 'all' || m.id === active)
    .map(m => {
      const key = normalizeKey(m.id)
      const installData = lookup.get(key) || null
      const installed_ = !!installData
      const isActive = installData?.is_active ?? false
      const isCore = installData?.is_core ?? false
      const avail = availKeys.has(key)

      if (installData && !installData.module_key) {
        installData.module_key = m.id
      }

      return {
        ...m,
        installData,
        installed: installed_,
        isActive,
        isCore,
        available: avail,
        installKey: m.id
      }
    })
})

const totalSubModules = computed(() => MODULE_MAP.reduce((sum, m) => sum + m.subs.length, 0))
const installedCount = computed(() => installed.value.length)
const activeCount = computed(() => installed.value.filter(m => m.is_active).length)

const availableExtra = computed(() => {
  const mapKeys = new Set(MODULE_MAP.map(m => normalizeKey(m.id)))
  return available.value.filter(a => !mapKeys.has(normalizeKey(a.module_key)))
})

function statusLabel(mod) {
  if (mod.installed && mod.isActive) return t('module-status-active')
  if (mod.installed && !mod.isActive) return t('module-status-disabled')
  return t('not-installed')
}

function subDotClass(mod) {
  if (mod.installed && mod.isActive) return 'dot-active'
  if (mod.installed && !mod.isActive) return 'dot-disabled'
  return 'dot-missing'
}

function isInstalled(key) {
  return installedLookup.value.has(normalizeKey(key))
}

async function loadInstalled() {
  try {
    const res = await api.get('/T0100I/')
    installed.value = Array.isArray(res.data) ? res.data : []
  } catch {
    installed.value = []
  }
}

async function scanModules() {
  scanning.value = true
  try {
    const res = await api.get('/T0100I/discover')
    available.value = Array.isArray(res.data) ? res.data : []
    showAvailable.value = true
  } catch {
    available.value = []
  } finally {
    scanning.value = false
  }
}

async function installModule(key) {
  try {
    const res = await api.post(`/T0100I/${encodeURIComponent(key)}/install`)
    if (res.data?.ok) {
      if (res.data.module) installed.value.push(res.data.module)
      toast(t('module-installed'), 'success')
    }
  } catch {
    toast(t('install-failed'), 'error')
  }
}

function uninstallModule(m) {
  confirmTarget.value = m
}

async function executeUninstallModule(m) {
  confirmTarget.value = null
  try {
    const res = await api.post(`/T0100I/${m.id}/uninstall`)
    if (res.data?.ok) {
      installed.value = installed.value.filter(x => x.id !== m.id)
      toast(t('module-uninstalled'), 'success')
    }
  } catch {
    toast(t('uninstall-failed'), 'error')
  }
}

async function toggleModule(m) {
  try {
    const res = await api.put(`/T0100I/${m.id}/toggle`, { is_active: !m.is_active })
    if (res.data?.ok && res.data.module) Object.assign(m, res.data.module)
    toast(m.is_active ? t('module-enabled') : t('module-disabled'), 'success')
  } catch {
    toast(t('toggle-failed'), 'error')
  }
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadInstalled(), scanModules()])
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* ── Header ── */
.modules-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
}
.modules-title {
  font-size: 22px;
  font-weight: 700;
  color: #1E2229;
  margin: 0;
  line-height: 1.2;
}
.modules-subtitle {
  font-size: 13px;
  color: #7A808E;
  margin-top: 4px;
}
.scan-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #1B2A4A;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  flex-shrink: 0;
  min-height: 44px;
}
.scan-btn:hover { background: #243454; }
.scan-btn:disabled { opacity: 0.5; cursor: default; }
.scan-btn .material-symbols-outlined { font-size: 18px; }

/* ── Stats ── */
.modules-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat {
  background: #fff;
  border: 1px solid #E4E7EC;
  border-radius: 10px;
  padding: 16px 12px;
  text-align: center;
}
.stat-value {
  display: block;
  font-size: 26px;
  font-weight: 700;
  color: #1E2229;
  line-height: 1;
  margin-bottom: 4px;
}
.stat-value.accent { color: #C96B3E; }
.stat-label {
  font-size: 11px;
  font-weight: 600;
  color: #7A808E;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

/* ── Filter ── */
.modules-filter {
  display: flex;
  gap: 6px;
  padding-bottom: 4px;
  margin-bottom: 20px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: #E4E7EC transparent;
}
.filter-chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid #E4E7EC;
  background: #fff;
  font-size: 12px;
  font-weight: 500;
  color: #6E7684;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  min-height: 32px;
}
.filter-chip:hover {
  border-color: #1B2A4A;
  color: #1B2A4A;
}
.filter-chip.active {
  background: #1B2A4A;
  border-color: #1B2A4A;
  color: #fff;
}

/* ── Grid ── */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

/* ── Card ── */
.module-card {
  display: flex;
  background: #fff;
  border: 1px solid #E4E7EC;
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.module-card:hover {
  border-color: #d0d4dc;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
@media (prefers-reduced-motion: reduce) {
  .module-card { transition: none; }
}

.card-accent {
  width: 4px;
  flex-shrink: 0;
  background: var(--accent, #4A6FA5);
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-width: 0;
}

.card-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}
.card-icon {
  font-size: 22px;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--accent, #4A6FA5);
}
.card-title-block {
  min-width: 0;
}
.card-name {
  font-size: 15px;
  font-weight: 600;
  color: #1E2229;
  margin: 0;
  line-height: 1.3;
}
.card-meta {
  font-size: 11px;
  color: #7A808E;
  line-height: 1.4;
}

/* ── Sub-module list ── */
.card-subs {
  list-style: none;
  margin: 0 0 12px 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sub-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #3D434F;
  line-height: 1.4;
}
.sub-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.sub-indicator.dot-active {
  background: #2B6B4B;
}
.sub-indicator.dot-disabled {
  background: #B45309;
}
.sub-indicator.dot-missing {
  background: transparent;
  border: 1.5px solid #C5CAD4;
}

/* ── Card footer (metadata tags) ── */
.card-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
  margin-top: auto;
}
.foot-tag {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  background: #EDF0F5;
  color: #6E7684;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

/* ── Card actions ── */
.card-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 10px;
  border-top: 1px solid #EDF0F5;
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  min-height: 32px;
  background: #F5F6F8;
  color: #3D434F;
}
.action-btn:hover { background: #EDF0F5; }
.action-btn .material-symbols-outlined { font-size: 15px; }
.action-label { white-space: nowrap; }
.action-primary { background: #1B2A4A; color: #fff; }
.action-primary:hover { background: #243454; }
.action-warn { color: #B45309; }
.action-warn:hover { background: #FEF3C7; }
.action-danger { color: #C44536; }
.action-danger:hover { background: #FEE2E2; }
.action-neutral { color: #2B6B4B; }
.action-neutral:hover { background: #D1FAE5; }

/* ── Empty state ── */
.modules-empty {
  text-align: center;
  padding: 56px 24px;
  color: #7A808E;
}
.modules-empty .empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
  color: #C5CAD4;
}
.modules-empty p {
  font-size: 14px;
  margin-bottom: 16px;
}
.reset-filter-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border: 1px solid #E4E7EC;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  font-weight: 600;
  color: #1B2A4A;
  cursor: pointer;
  transition: all 0.15s;
  min-height: 36px;
}
.reset-filter-btn:hover { border-color: #1B2A4A; }

/* ── Available section ── */
.available-section {
  background: #fff;
  border: 1px solid #E4E7EC;
  border-radius: 10px;
  overflow: hidden;
}
.available-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  cursor: pointer;
  list-style: none;
  user-select: none;
}
.available-summary::-webkit-details-marker { display: none; }
.available-summary .material-symbols-outlined {
  font-size: 18px;
  color: #7A808E;
}
.available-heading {
  font-size: 14px;
  font-weight: 600;
  color: #1E2229;
  flex: 1;
}
.available-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 11px;
  background: #EDF0F5;
  color: #6E7684;
  font-size: 11px;
  font-weight: 700;
}
.available-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 0 16px 16px 16px;
}
.extra-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #EDF0F5;
  border-radius: 8px;
}
.extra-body {
  flex: 1;
  min-width: 0;
}
.extra-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #1E2229;
}
.extra-desc {
  display: block;
  font-size: 11px;
  color: #7A808E;
  margin-top: 2px;
}
.install-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  background: #1B2A4A;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  min-height: 32px;
}
.install-btn:hover { background: #243454; }
.installed-tag {
  font-size: 11px;
  font-weight: 600;
  color: #2B6B4B;
  flex-shrink: 0;
}

/* ── Responsive ── */
@media (max-width: 1023px) {
  .modules-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .modules-header { flex-direction: column; }
  .scan-btn { align-self: stretch; justify-content: center; }
  .modules-stats { grid-template-columns: repeat(2, 1fr); }
  .modules-grid { grid-template-columns: 1fr; }
  .available-grid { grid-template-columns: 1fr; }
}
</style>

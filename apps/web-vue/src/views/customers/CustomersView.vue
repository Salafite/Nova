<template>
  <div class="page" :dir="dir">
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ t('customers-title') }}</h1>
        <p class="page-subtitle">{{ t('customers-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openPanel()">
        <span class="material-symbols-outlined">add</span>
        {{ t('new-customer') }}
      </button>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ items.length }}</span>
        <span class="stat-label">{{ t('total') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ activeCount }}</span>
        <span class="stat-label">{{ t('active') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">${{ totalOutstanding }}</span>
        <span class="stat-label">{{ t('outstanding') }}</span>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-wrap">
        <span class="material-symbols-outlined search-icon">search</span>
        <input type="text" v-model="searchQuery" class="search-input" :placeholder="t('search-customers')" />
      </div>
      <select v-model="groupFilter" class="filter-select">
        <option value="">{{ t('all-groups') }}</option>
        <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
      </select>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">group</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <template v-else>
      <div v-if="!filteredItems.length && (searchQuery || groupFilter)" class="empty-state">
        <span class="material-symbols-outlined empty-icon">search_off</span>
        <p>{{ t('no-records') }}</p>
      </div>

      <div v-else class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-name">{{ t('name') }}</th>
                <th class="col-group">{{ t('customer-group') }}</th>
                <th class="col-contact">{{ t('customer-phone') }}</th>
                <th class="col-num">{{ t('customer-credit') }}</th>
                <th class="col-num">{{ t('customer-balance') }}</th>
                <th class="col-usage">{{ t('credit-usage') }}</th>
                <th class="text-center">{{ t('status') }}</th>
                <th class="text-center col-actions">{{ t('actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredItems" :key="item.id">
                <td class="col-name"><a class="name-link" @click="router.push(`/customers/${item.id}`)">{{ item.name }}</a></td>
                <td class="col-group"><span class="group-tag">{{ item.group_name || '-' }}</span></td>
                <td class="col-contact cell-mono">{{ item.phone || '-' }}</td>
                <td class="col-num cell-mono">{{ formatNum(item.credit_limit) }}</td>
                <td class="col-num cell-mono">{{ formatNum(item.balance) }}</td>
                <td class="col-usage">
                  <div v-if="(item.credit_limit || 0) > 0" class="util-track" :title="utilTitle(item)">
                    <div class="util-fill" :class="utilLevel(item)" :style="{ width: utilPct(item) + '%' }"></div>
                  </div>
                  <span v-else class="util-na">{{ t('unlimited') }}</span>
                </td>
                <td class="text-center">
                  <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                    {{ item.is_active ? t('active') : t('inactive') }}
                  </span>
                </td>
                <td class="text-center col-actions">
                  <button class="btn-icon" @click="openPanel(item)" :title="t('edit')" :aria-label="t('edit')">
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button class="btn-icon btn-icon-danger" @click="confirmTarget = item" :title="t('delete')" :aria-label="t('delete')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-if="panelOpen" class="panel-overlay" :class="{ 'panel-shown': panelOpen }" @click.self="closePanel"></div>
    <div class="slide-panel" :class="{ 'panel-shown': panelOpen }" :dir="dir">
      <div class="panel-header">
        <h3>{{ editing ? t('edit-customer') : t('new-customer') }}</h3>
        <button class="btn-icon" @click="closePanel" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
      </div>
      <div class="panel-body">
        <div class="form-row">
          <div class="form-group">
            <label>{{ t('name') }} <span class="required">*</span></label>
            <input type="text" v-model="form.name" required class="form-input" maxlength="200" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-group') }}</label>
            <select v-model="form.group_name" class="form-input">
              <option value="Retail">Retail</option>
              <option value="Wholesale">Wholesale</option>
              <option value="Corporate">Corporate</option>
              <option value="VIP">VIP</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>{{ t('customer-phone') }}</label>
            <input type="text" v-model="form.phone" class="form-input" maxlength="30" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-email') }}</label>
            <input type="email" v-model="form.email" class="form-input" maxlength="200" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>{{ t('customer-credit') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="form.credit_limit" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-balance') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="form.balance" class="form-input" />
          </div>
        </div>
        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.is_active" />
            <span>{{ t('active') }}</span>
          </label>
        </div>
      </div>
      <div class="panel-footer">
        <button class="btn-outline" @click="closePanel">{{ t('cancel') }}</button>
        <button class="btn-primary" :disabled="saving" @click="saveItem">
          {{ saving ? t('saving') : t('save') }}
        </button>
      </div>
    </div>

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.name" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const items = ref([])
const searchQuery = ref('')
const groupFilter = ref('')
const panelOpen = ref(false)
const editing = ref(false)
const saving = ref(false)
const editId = ref(null)
const confirmTarget = ref(null)
const form = ref({ name: '', group_name: 'Retail', phone: '', email: '', credit_limit: 0, balance: 0, is_active: true })

const activeCount = computed(() => items.value.filter(i => i.is_active).length)
const totalOutstanding = computed(() => items.value.reduce((s, i) => s + (i.balance || 0), 0).toLocaleString('en-US', { minimumFractionDigits: 2 }))

const groups = computed(() => {
  const s = new Set(items.value.map(i => i.group_name).filter(Boolean))
  return [...s].sort()
})

const filteredItems = computed(() => {
  let result = items.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(i =>
      i.name.toLowerCase().includes(q) ||
      (i.phone || '').toLowerCase().includes(q) ||
      (i.email || '').toLowerCase().includes(q)
    )
  }
  if (groupFilter.value) {
    result = result.filter(i => i.group_name === groupFilter.value)
  }
  return result
})

function formatNum(val) {
  return val ? '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '$0.00'
}

function utilPct(item) {
  const cl = item.credit_limit || 0
  const bal = item.balance || 0
  if (cl <= 0) return 0
  return Math.min(Math.round((bal / cl) * 100), 100)
}

function utilLevel(item) {
  const cl = item.credit_limit || 0
  const bal = item.balance || 0
  if (cl <= 0) return ''
  const pct = bal / cl
  if (pct >= 1) return 'util-danger'
  if (pct >= 0.8) return 'util-warning'
  return 'util-ok'
}

function utilTitle(item) {
  const pct = utilPct(item)
  return `${pct}% ${t('credit-usage')}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0010I/')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openPanel(item) {
  if (item) {
    editing.value = true
    editId.value = item.id
    form.value = {
      name: item.name,
      group_name: item.group_name || 'Retail',
      phone: item.phone || '',
      email: item.email || '',
      credit_limit: item.credit_limit || 0,
      balance: item.balance || 0,
      is_active: item.is_active,
    }
  } else {
    editing.value = false
    editId.value = null
    form.value = { name: '', group_name: 'Retail', phone: '', email: '', credit_limit: 0, balance: 0, is_active: true }
  }
  panelOpen.value = true
}

function closePanel() {
  panelOpen.value = false
}

async function saveItem() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      phone: form.value.phone || null,
      email: form.value.email || null,
    }
    if (editing.value) {
      await api.put(`/T0010I/${editId.value}`, payload)
      toast(t('customer-saved'), 'success')
    } else {
      await api.post('/T0010I/', payload)
      toast(t('customer-saved'), 'success')
    }
    closePanel()
    await load()
  } catch {
    toast(t('failed-save'), 'error')
  } finally {
    saving.value = false
  }
}

async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0010I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast(t('customer-deleted'), 'success')
  } catch {
    toast(t('failed-save'), 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page { }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }

.stats-row { display: flex; gap: 12px; margin-bottom: 16px; }
.stat-card { flex: 1; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 4px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }

.toolbar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
.search-wrap { position: relative; flex: 1; max-width: 320px; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 18px; color: var(--text-muted); pointer-events: none; }
.search-input { width: 100%; padding: 8px 10px 8px 34px; border: 1px solid var(--border-input); border-radius: 8px; font-size: 13px; background: var(--bg-surface); color: var(--text-primary); outline: none; min-height: 44px; }
.search-input:focus { border-color: var(--color-primary); }
.search-input::placeholder { color: var(--text-faint); }
.filter-select { padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 8px; font-size: 13px; background: var(--bg-surface); color: var(--text-primary); outline: none; min-height: 44px; cursor: pointer; }
.filter-select:focus { border-color: var(--color-primary); }

[dir="rtl"] .search-icon { left: auto; right: 10px; }
[dir="rtl"] .search-input { padding: 8px 34px 8px 10px; }

.data-card { margin-top: 0; }
.col-name { min-width: 150px; }
.col-group { width: 110px; }
.col-contact { width: 130px; }
.col-num { width: 120px; text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.col-usage { width: 130px; }
.col-actions { width: 80px; }

.name-link { color: var(--color-primary); cursor: pointer; font-weight: 600; }
.name-link:hover { text-decoration: underline; }

.cell-mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.group-tag { display: inline-block; padding: 2px 8px; background: var(--bg-surface-low); border-radius: 4px; font-size: 12px; color: var(--text-muted); }

.util-track { width: 100%; height: 6px; background: var(--border-light); border-radius: 3px; overflow: hidden; }
.util-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.util-fill.util-ok { background: var(--color-success); }
.util-fill.util-warning { background: var(--color-warning, #d97706); }
.util-fill.util-danger { background: var(--color-error); }
.util-na { font-size: 11px; color: var(--text-faint); }

[dir="rtl"] .col-num { text-align: left; }

.panel-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }
.panel-overlay.panel-shown { opacity: 1; pointer-events: auto; }

.slide-panel { position: fixed; top: 0; inset-inline-end: 0; width: 480px; height: 100vh; background: var(--bg-surface); z-index: 101; transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1); display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,0.1); }
.slide-panel.panel-shown { transform: translateX(0); }
[dir="rtl"] .slide-panel { transform: translateX(-100%); box-shadow: 4px 0 24px rgba(0,0,0,0.1); }
[dir="rtl"] .slide-panel.panel-shown { transform: translateX(0); }

.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); flex-shrink: 0; }
.panel-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.panel-body { padding: 24px; overflow-y: auto; flex: 1; }
.panel-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border-default); flex-shrink: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; background: var(--bg-surface); color: var(--text-primary); outline: none; }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { cursor: pointer; }
.required { color: var(--color-error); }
.checkbox-group { display: flex; margin-top: 4px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.checkbox-label input { width: 16px; height: 16px; accent-color: var(--color-primary); }

@media (max-width: 767px) {
  .page-head { flex-direction: column; align-items: flex-start; gap: 12px; }
  .page-head .btn-primary { align-self: stretch; justify-content: center; }
  .stats-row { flex-direction: column; }
  .toolbar { flex-direction: column; align-items: stretch; }
  .search-wrap { max-width: none; }
  .slide-panel { width: 100%; }
  .form-row { grid-template-columns: 1fr; }
}

[dir="rtl"] .panel-header { flex-direction: row-reverse; }
</style>

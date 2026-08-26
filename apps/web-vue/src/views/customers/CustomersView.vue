<template>
  <div class="page" :dir="dir">
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ t('customers-title', 'Customers') }}</h1>
        <p class="page-subtitle">{{ t('customers-sub', 'Manage your customer accounts') }}</p>
      </div>
      <div class="page-actions">
        <div class="view-mode-toggle">
          <button
            type="button"
            class="mode-btn"
            :class="{ active: !isInfiniteMode }"
            @click="setInfiniteMode(false)"
            :title="t('pagination-paged-mode', 'Paginated Table')"
          >
            <span class="material-symbols-outlined">table_rows</span>
          </button>
          <button
            type="button"
            class="mode-btn"
            :class="{ active: isInfiniteMode }"
            @click="setInfiniteMode(true)"
            :title="t('pagination-infinite-mode', 'Infinite Scroll')"
          >
            <span class="material-symbols-outlined">view_stream</span>
          </button>
        </div>
        <button class="btn-primary" @click="openPanel()">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-customer', 'New Customer') }}
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ totalCount }}</span>
        <span class="stat-label">{{ t('total', 'Total') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ activeCount }}</span>
        <span class="stat-label">{{ t('active', 'Active') }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">${{ totalOutstanding }}</span>
        <span class="stat-label">{{ t('outstanding', 'Outstanding') }}</span>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-wrap">
        <span class="material-symbols-outlined search-icon">search</span>
        <input type="text" v-model="searchQuery" class="search-input" :placeholder="t('search-customers', 'Search customers...')" />
      </div>
      <select v-model="groupFilter" class="filter-select">
        <option value="">{{ t('all-groups', 'All Groups') }}</option>
        <option v-for="g in groups" :key="g" :value="g">{{ g }}</option>
      </select>
    </div>

    <SkeletonTable v-if="loading && !items.length" :rows="6" :columns="8" />
    <ErrorState v-else-if="error && !items.length" :message="error" @retry="load()" />

    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">group</span>
      <p>{{ t('no-records', 'No records found') }}</p>
      <button class="btn-primary" @click="openPanel()">{{ t('new-customer', 'New Customer') }}</button>
    </div>

    <template v-else>
      <div v-if="!filteredItems.length && (searchQuery || groupFilter)" class="empty-state">
        <span class="material-symbols-outlined empty-icon">search_off</span>
        <p>{{ t('no-records', 'No records found') }}</p>
      </div>

      <div v-else class="data-card">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-name th-sortable" :class="{ 'is-sorted': orderBy === 'name' }" @click="toggleSort('name')">
                  <span class="th-content">
                    {{ t('name', 'Name') }}
                    <span class="material-symbols-outlined sort-icon">
                      {{ orderBy === 'name' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                    </span>
                  </span>
                </th>
                <th class="col-group th-sortable" :class="{ 'is-sorted': orderBy === 'group_name' }" @click="toggleSort('group_name')">
                  <span class="th-content">
                    {{ t('customer-group', 'Group') }}
                    <span class="material-symbols-outlined sort-icon">
                      {{ orderBy === 'group_name' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                    </span>
                  </span>
                </th>
                <th class="col-contact">{{ t('customer-phone', 'Phone') }}</th>
                <th class="col-num th-sortable" :class="{ 'is-sorted': orderBy === 'credit_limit' }" @click="toggleSort('credit_limit')">
                  <span class="th-content th-content-end">
                    {{ t('customer-credit', 'Credit Limit') }}
                    <span class="material-symbols-outlined sort-icon">
                      {{ orderBy === 'credit_limit' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                    </span>
                  </span>
                </th>
                <th class="col-num th-sortable" :class="{ 'is-sorted': orderBy === 'balance' }" @click="toggleSort('balance')">
                  <span class="th-content th-content-end">
                    {{ t('customer-balance', 'Balance') }}
                    <span class="material-symbols-outlined sort-icon">
                      {{ orderBy === 'balance' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                    </span>
                  </span>
                </th>
                <th class="col-usage">{{ t('credit-usage', 'Credit Usage') }}</th>
                <th class="text-center th-sortable" :class="{ 'is-sorted': orderBy === 'is_active' }" @click="toggleSort('is_active')">
                  <span class="th-content th-content-center">
                    {{ t('status', 'Status') }}
                    <span class="material-symbols-outlined sort-icon">
                      {{ orderBy === 'is_active' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                    </span>
                  </span>
                </th>
                <th class="text-center col-actions">{{ t('actions', 'Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredItems" :key="item.id" :class="{ 'row-inactive': !item.is_active }">
                <td class="col-name"><a class="name-link" @click="router.push(`/customers/${item.id}`)">{{ item.name }}</a></td>
                <td class="col-group"><span class="group-tag">{{ item.group_name || '-' }}</span></td>
                <td class="col-contact cell-mono">{{ item.phone || '-' }}</td>
                <td class="col-num cell-mono">{{ formatNum(item.credit_limit) }}</td>
                <td class="col-num cell-mono">{{ formatNum(item.balance) }}</td>
                <td class="col-usage">
                  <div v-if="(item.credit_limit || 0) > 0" class="util-track" :title="utilTitle(item)">
                    <div class="util-fill" :class="utilLevel(item)" :style="{ width: utilPct(item) + '%' }"></div>
                  </div>
                  <span v-else class="util-na">{{ t('unlimited', 'Unlimited') }}</span>
                </td>
                <td class="text-center">
                  <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                    {{ item.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                  </span>
                </td>
                <td class="text-center col-actions">
                  <button class="btn-icon" @click="openPanel(item)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')">
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button class="btn-icon btn-icon-danger" @click="confirmTarget = item" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Infinite Scroll Sentinel & Controls -->
        <div v-if="isInfiniteMode" class="infinite-scroll-container">
          <div v-if="loadingMore" class="infinite-loading">
            <span class="material-symbols-outlined spinner">progress_activity</span>
            <span>{{ t('pagination-loading-more', 'Loading more customers...') }}</span>
          </div>
          <div v-else-if="hasNextPage" class="infinite-action">
            <button type="button" class="btn-outline btn-sm" @click="loadMore">
              <span class="material-symbols-outlined">expand_more</span>
              {{ t('pagination-load-more', 'Load More') }} ({{ items.length }} / {{ totalCount }})
            </button>
          </div>
          <div v-else class="infinite-end">
            <span>{{ t('pagination-all-loaded', 'All') }} {{ totalCount }} {{ t('pagination-items-loaded', 'customers loaded') }}</span>
          </div>
          <div ref="infiniteSentinel" class="infinite-sentinel"></div>
        </div>

        <!-- Standard Pagination Bar -->
        <PaginationBar
          v-else
          :pagination="pagination"
        />
      </div>
    </template>

    <div v-if="panelOpen" class="panel-overlay" :class="{ 'panel-shown': panelOpen }" @click.self="closePanel"></div>
    <div class="slide-panel" :class="{ 'panel-shown': panelOpen }" :dir="dir">
      <div class="panel-header">
        <h3>{{ editing ? t('edit-customer', 'Edit Customer') : t('new-customer', 'New Customer') }}</h3>
        <button class="btn-icon" @click="closePanel" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
      </div>
      <div class="panel-body">
        <div class="form-row">
          <div class="form-group">
            <label>{{ t('name', 'Name') }} <span class="required">*</span></label>
            <input type="text" v-model="form.name" required class="form-input" maxlength="200" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-group', 'Group') }}</label>
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
            <label>{{ t('customer-phone', 'Phone') }}</label>
            <input type="text" v-model="form.phone" class="form-input" maxlength="30" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-email', 'Email') }}</label>
            <input type="email" v-model="form.email" class="form-input" maxlength="200" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>{{ t('customer-credit', 'Credit Limit') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="form.credit_limit" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('customer-balance', 'Balance') }}</label>
            <input type="number" step="0.01" min="0" v-model.number="form.balance" class="form-input" />
          </div>
        </div>
        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.is_active" />
            <span>{{ t('active', 'Active') }}</span>
          </label>
        </div>
      </div>
      <div class="panel-footer">
        <button class="btn-outline" @click="closePanel">{{ t('cancel', 'Cancel') }}</button>
        <button class="btn-primary" :disabled="saving" @click="saveItem">
          {{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}
        </button>
      </div>
    </div>

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete Customer')" :message="t('confirm-delete-msg', 'Are you sure you want to delete') + ' ' + confirmTarget.name + '?'" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import { usePagination } from '../../composables/usePagination.js'
import PaginationBar from '../../components/PaginationBar.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const router = useRouter()

const isInfiniteMode = ref(false)
const infiniteSentinel = ref(null)
let observer = null

const pagination = usePagination({
  fetchFn: async (params) => {
    return await api.get('/T0010I/', { params })
  },
  defaultLimit: 50,
  defaultOrderBy: 'name',
  defaultOrderDir: 'asc',
})

const {
  items,
  totalCount,
  page,
  limit,
  totalPages,
  loading,
  loadingMore,
  error,
  orderBy,
  orderDir,
  hasNextPage,
  load,
  loadMore,
  toggleSort,
} = pagination

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
      (i.name || '').toLowerCase().includes(q) ||
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
  return `${pct}% ${t('credit-usage', 'Credit Usage')}`
}

function setInfiniteMode(val) {
  isInfiniteMode.value = val
  pagination.isInfinite.value = val
  if (val) {
    nextTick(setupObserver)
  } else {
    if (observer) {
      observer.disconnect()
      observer = null
    }
    load(1)
  }
}

function setupObserver() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  if (!isInfiniteMode.value) return

  observer = new IntersectionObserver((entries) => {
    const entry = entries[0]
    if (entry && entry.isIntersecting && hasNextPage.value && !loading.value && !loadingMore.value) {
      loadMore()
    }
  }, { threshold: 0.1 })

  if (infiniteSentinel.value) {
    observer.observe(infiniteSentinel.value)
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
      toast(t('customer-saved', 'Customer updated'), 'success')
    } else {
      await api.post('/T0010I/', payload)
      toast(t('customer-saved', 'Customer created'), 'success')
    }
    closePanel()
    await load()
  } catch {
    toast(t('failed-save', 'Failed to save customer'), 'error')
  } finally {
    saving.value = false
  }
}

async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0010I/${item.id}`)
    toast(t('customer-deleted', 'Customer deleted'), 'success')
    await load()
  } catch {
    toast(t('failed-save', 'Failed to delete customer'), 'error')
  }
}

onMounted(() => {
  load()
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<style scoped>
.page { }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-actions { display: flex; align-items: center; gap: 8px; }

.view-mode-toggle { display: inline-flex; background: var(--bg-surface-hover, #f3f4f6); border-radius: 8px; padding: 2px; border: 1px solid var(--border-light, #e5e7eb); }
.mode-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; background: transparent; border-radius: 6px; color: var(--text-muted, #6b7280); cursor: pointer; transition: all 0.15s ease; }
.mode-btn .material-symbols-outlined { font-size: 18px; }
.mode-btn:hover { color: var(--text-primary, #111827); }
.mode-btn.active { background: var(--bg-surface, #ffffff); color: var(--color-primary, #5d3fd3); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

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

.data-card { margin-top: 0; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low, #f9fafb); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-secondary, #555); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default, #e0e0e0); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light, #f0f0f0); }
.data-table tbody tr:hover { background: var(--bg-surface-hover, #fafaff); }

.th-sortable { cursor: pointer; user-select: none; transition: background-color 0.15s; }
.th-sortable:hover { background-color: var(--bg-surface-hover, #f3f4f6); }
.th-content { display: inline-flex; align-items: center; gap: 4px; }
.th-content-end { justify-content: flex-end; width: 100%; }
.th-content-center { justify-content: center; width: 100%; }
.sort-icon { font-size: 15px; color: var(--text-faint, #9ca3af); vertical-align: middle; }
.th-sortable.is-sorted .sort-icon { color: var(--color-primary, #5d3fd3); }

.col-name { min-width: 150px; }
.col-group { width: 110px; }
.col-contact { width: 130px; }
.col-num { width: 120px; text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.col-usage { width: 130px; }
.col-actions { width: 80px; }
.row-inactive { opacity: 0.55; }

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

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: var(--bg-surface-hover, #f3f4f6); color: var(--text-faint, #888); }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: var(--color-primary, #5d3fd3); color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--text-primary, #333); padding: 8px 20px; border: 1px solid var(--border-default, #ddd); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover, #f5f5f5); }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-muted, #888); }
.btn-icon:hover { background: var(--bg-surface-hover, #f0f0f0); color: var(--color-primary, #5d3fd3); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.empty-state { text-align: center; padding: 48px; color: var(--text-muted, #999); font-size: 14px; }
.empty-icon { font-size: 48px; color: var(--border-default, #ccc); margin-bottom: 16px; display: block; }

.infinite-scroll-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; border-top: 1px solid var(--border-light, #f0f0f0); }
.infinite-loading { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 13px; }
.spinner { animation: spin 1s linear infinite; font-size: 20px; color: var(--color-primary); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.infinite-action { display: flex; justify-content: center; }
.btn-sm { padding: 6px 14px !important; font-size: 12px !important; }
.infinite-end { font-size: 12px; color: var(--text-faint); }
.infinite-sentinel { width: 100%; height: 4px; pointer-events: none; }

[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .page-actions { flex-direction: row-reverse; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }

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
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; background: var(--bg-surface); color: var(--text-primary); outline: none; box-sizing: border-box; }
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

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('invoices-title', 'Invoices') }}</h1>
        <p class="page-subtitle">{{ t('invoices-sub', 'Manage customer and vendor invoices') }}</p>
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
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-invoice', 'New Invoice') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading && !items.length" :rows="6" :columns="8" />
    <ErrorState v-else-if="error && !items.length" :message="error" @retry="load()" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">receipt_long</span>
      <p>{{ t('no-records', 'No records found') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-invoice', 'New Invoice') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'invoice_number' }" @click="toggleSort('invoice_number')">
                <span class="th-content">
                  {{ t('invoices-number', 'Invoice #') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'invoice_number' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'invoice_type' }" @click="toggleSort('invoice_type')">
                <span class="th-content">
                  {{ t('invoices-type', 'Type') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'invoice_type' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'partner_id' }" @click="toggleSort('partner_id')">
                <span class="th-content">
                  {{ t('invoices-partner', 'Partner') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'partner_id' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'issue_date' }" @click="toggleSort('issue_date')">
                <span class="th-content">
                  {{ t('invoices-issue-date', 'Issue Date') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'issue_date' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'due_date' }" @click="toggleSort('due_date')">
                <span class="th-content">
                  {{ t('invoices-due-date', 'Due Date') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'due_date' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="col-num th-sortable" :class="{ 'is-sorted': orderBy === 'total_amount' }" @click="toggleSort('total_amount')">
                <span class="th-content th-content-end">
                  {{ t('invoices-total', 'Total') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'total_amount' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="text-center th-sortable" :class="{ 'is-sorted': orderBy === 'status' }" @click="toggleSort('status')">
                <span class="th-content th-content-center">
                  {{ t('status', 'Status') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'status' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="text-center col-actions">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-mono"><a class="inv-link" @click="router.push(`/finance/${item.id}`)">{{ item.invoice_number }}</a></td>
              <td><span :class="'inv-type inv-' + (item.invoice_type || 'sales').toLowerCase()">{{ item.invoice_type }}</span></td>
              <td>{{ item.partner_id }}</td>
              <td class="cell-mono">{{ item.issue_date }}</td>
              <td class="cell-mono">{{ item.due_date }}</td>
              <td class="col-num">${{ (item.total_amount || 0).toFixed(2) }}</td>
              <td class="text-center">
                <span :class="statusBadge(item.status)">{{ item.status }}</span>
              </td>
              <td class="text-center col-actions">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')">
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
          <span>{{ t('pagination-loading-more', 'Loading more invoices...') }}</span>
        </div>
        <div v-else-if="hasNextPage" class="infinite-action">
          <button type="button" class="btn-outline btn-sm" @click="loadMore">
            <span class="material-symbols-outlined">expand_more</span>
            {{ t('pagination-load-more', 'Load More') }} ({{ items.length }} / {{ totalCount }})
          </button>
        </div>
        <div v-else class="infinite-end">
          <span>{{ t('pagination-all-loaded', 'All') }} {{ totalCount }} {{ t('pagination-items-loaded', 'invoices loaded') }}</span>
        </div>
        <div ref="infiniteSentinel" class="infinite-sentinel"></div>
      </div>

      <!-- Standard Pagination Bar -->
      <PaginationBar
        v-else
        :pagination="pagination"
      />
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-invoice', 'Edit Invoice') : t('new-invoice', 'New Invoice') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-number', 'Invoice #') }} <span class="required">*</span></label>
              <input type="text" v-model="form.invoice_number" class="form-input" maxlength="50" />
            </div>
            <div class="form-group">
              <label>{{ t('invoices-type', 'Type') }} <span class="required">*</span></label>
              <select v-model="form.invoice_type" class="form-input">
                <option value="Sales">Sales</option>
                <option value="Purchase">Purchase</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-partner', 'Partner') }} (ID) <span class="required">*</span></label>
              <input type="number" min="1" v-model.number="form.partner_id" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('invoices-total', 'Total') }} <span class="required">*</span></label>
              <input type="number" step="0.01" min="0" v-model.number="form.total_amount" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('invoices-issue-date', 'Issue Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.issue_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('invoices-due-date', 'Due Date') }} <span class="required">*</span></label>
              <input type="date" v-model="form.due_date" class="form-input" />
            </div>
          </div>
          <div class="form-row" v-if="!editing">
            <div class="form-group">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Draft">Draft</option>
                <option value="Unpaid">Unpaid</option>
                <option value="Paid">Paid</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete', 'Delete Invoice') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p class="delete-text">{{ t('invoices-delete-confirm', 'Are you sure you want to delete invoice') }} <strong>{{ deleteTarget?.invoice_number }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? t('deleting', 'Deleting...') : t('delete', 'Delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import { usePagination } from '../../composables/usePagination.js'
import PaginationBar from '../../components/PaginationBar.vue'
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
    return await api.get('/T0090I/', { params })
  },
  defaultLimit: 50,
  defaultOrderBy: 'issue_date',
  defaultOrderDir: 'desc',
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

const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ invoice_number: '', invoice_type: 'Sales', partner_id: null, issue_date: '', due_date: '', total_amount: 0, status: 'Draft' })
const editId = ref(null)

function statusBadge(status) {
  if (status === 'Paid') return 'badge badge-active'
  if (status === 'Unpaid' || status === 'Draft') return 'badge badge-warning'
  if (status === 'Cancelled') return 'badge badge-inactive'
  return 'badge badge-inactive'
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

function openAdd() {
  editing.value = false
  editId.value = null
  const today = new Date().toISOString().split('T')[0]
  form.value = { invoice_number: '', invoice_type: 'Sales', partner_id: null, issue_date: today, due_date: today, total_amount: 0, status: 'Draft' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    invoice_number: item.invoice_number,
    invoice_type: item.invoice_type,
    partner_id: item.partner_id,
    issue_date: item.issue_date,
    due_date: item.due_date,
    total_amount: item.total_amount,
    status: item.status,
  }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  if (!form.value.invoice_number || !form.value.partner_id || !form.value.issue_date || !form.value.due_date) return
  saving.value = true
  try {
    if (editing.value) {
      await api.put(`/T0090I/${editId.value}`, form.value)
      toast('Invoice ' + t('saved-ok', 'saved successfully'), 'success')
    } else {
      await api.post('/T0090I/', form.value)
      toast('Invoice ' + t('saved-ok', 'saved successfully'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save', 'Failed to save') + ' Invoice', 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  deleteTarget.value = item
  showDelete.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await api.delete(`/T0090I/${deleteTarget.value.id}`)
    toast('Invoice deleted', 'success')
    showDelete.value = false
    await load()
  } catch {
    toast(t('failed-save', 'Failed to delete') + ' Invoice', 'error')
  } finally {
    deleting.value = false
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
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-actions { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary, #1a1a2e); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-muted, #666); margin-top: 4px; }

.view-mode-toggle { display: inline-flex; background: var(--bg-surface-hover, #f3f4f6); border-radius: 8px; padding: 2px; border: 1px solid var(--border-light, #e5e7eb); }
.mode-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; background: transparent; border-radius: 6px; color: var(--text-muted, #6b7280); cursor: pointer; transition: all 0.15s ease; }
.mode-btn .material-symbols-outlined { font-size: 18px; }
.mode-btn:hover { color: var(--text-primary, #111827); }
.mode-btn.active { background: var(--bg-surface, #ffffff); color: var(--color-primary, #5d3fd3); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

.empty-state { text-align: center; padding: 48px; color: var(--text-muted, #999); font-size: 14px; }
.empty-icon { font-size: 48px; color: var(--border-default, #ccc); margin-bottom: 16px; display: block; }

.data-card { background: var(--bg-surface, #fff); border: 1px solid var(--border-default, #e0e0e0); border-radius: 12px; overflow: hidden; }
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

.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-muted, #888); }
.inv-link { color: var(--color-primary, #5d3fd3); cursor: pointer; font-weight: 600; }
.inv-link:hover { text-decoration: underline; }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.col-actions { width: 80px; text-align: center; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-inactive { background: var(--bg-surface-hover, #f3f4f6); color: var(--text-faint, #888); }

.inv-type { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.inv-sales { background: #dbeafe; color: #2563eb; }
.inv-purchase { background: #ede9fe; color: #7c3aed; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: var(--color-primary, #5d3fd3); color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--text-primary, #333); padding: 8px 20px; border: 1px solid var(--border-default, #ddd); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover, #f5f5f5); }
.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: var(--color-error, #dc2626); color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-muted, #888); }
.btn-icon:hover { background: var(--bg-surface-hover, #f0f0f0); color: var(--color-primary, #5d3fd3); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.infinite-scroll-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; border-top: 1px solid var(--border-light, #f0f0f0); }
.infinite-loading { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 13px; }
.spinner { animation: spin 1s linear infinite; font-size: 20px; color: var(--color-primary); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.infinite-action { display: flex; justify-content: center; }
.btn-sm { padding: 6px 14px !important; font-size: 12px !important; }
.infinite-end { font-size: 12px; color: var(--text-faint); }
.infinite-sentinel { width: 100%; height: 4px; pointer-events: none; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface, #fff); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-light, #eee); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary, #1a1a2e); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.delete-text { font-size: 14px; color: var(--text-secondary, #555); margin: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary, #444); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input, #ddd); border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; background: var(--bg-surface, #fff); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary, #5d3fd3); }
select.form-input { appearance: auto; }
.required { color: var(--color-error, #dc2626); }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .page-actions { flex-direction: row-reverse; }
</style>

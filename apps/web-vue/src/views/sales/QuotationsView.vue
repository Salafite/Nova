<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('quotations-title', 'Quotations') }}</h1>
        <p class="page-subtitle">{{ t('quotations-sub', 'Manage sales quotations and convert to orders') }}</p>
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
          <span class="material-symbols-outlined">add</span> {{ t('new-quotation', 'New Quotation') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading && !items.length" :rows="6" :columns="7" />
    <ErrorState v-else-if="error && !items.length" :message="error" @retry="load()" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">request_quote</span>
      <p>{{ t('no-records', 'No records found') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-quotation', 'New Quotation') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'quote_number' }" @click="toggleSort('quote_number')">
                <span class="th-content">
                  {{ t('quote-number', 'Quote #') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'quote_number' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th>{{ t('customer', 'Customer') }}</th>
              <th class="col-num th-sortable" :class="{ 'is-sorted': orderBy === 'grand_total' }" @click="toggleSort('grand_total')">
                <span class="th-content th-content-end">
                  {{ t('grand-total', 'Total') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'grand_total' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
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
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'quote_date' }" @click="toggleSort('quote_date')">
                <span class="th-content">
                  {{ t('quote-date', 'Date') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'quote_date' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'valid_until' }" @click="toggleSort('valid_until')">
                <span class="th-content">
                  {{ t('valid-until', 'Valid Until') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'valid_until' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="text-center col-actions">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-order"><a class="order-link" @click="router.push(`/sales/quotations/${item.id}`)">{{ item.quote_number }}</a></td>
              <td>{{ customerName(item.customer_id) }}</td>
              <td class="col-num"><strong>${{ (item.grand_total || 0).toFixed(2) }}</strong></td>
              <td class="text-center"><span class="badge" :class="statusBadge(item.status)">{{ item.status }}</span></td>
              <td class="cell-mono">{{ item.quote_date }}</td>
              <td class="cell-mono">{{ item.valid_until || '-' }}</td>
              <td class="text-center col-actions">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit', 'Edit')" :aria-label="t('edit', 'Edit')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete', 'Delete')" :aria-label="t('delete', 'Delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Infinite Scroll Sentinel & Controls -->
      <div v-if="isInfiniteMode" class="infinite-scroll-container">
        <div v-if="loadingMore" class="infinite-loading">
          <span class="material-symbols-outlined spinner">progress_activity</span>
          <span>{{ t('pagination-loading-more', 'Loading more quotations...') }}</span>
        </div>
        <div v-else-if="hasNextPage" class="infinite-action">
          <button type="button" class="btn-outline btn-sm" @click="loadMore">
            <span class="material-symbols-outlined">expand_more</span>
            {{ t('pagination-load-more', 'Load More') }} ({{ items.length }} / {{ totalCount }})
          </button>
        </div>
        <div v-else class="infinite-end">
          <span>{{ t('pagination-all-loaded', 'All') }} {{ totalCount }} {{ t('pagination-items-loaded', 'quotations loaded') }}</span>
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
          <h3>{{ editing ? t('edit-quotation', 'Edit Quotation') : t('new-quotation', 'New Quotation') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('quote-number', 'Quote #') }} <span class="required">*</span></label>
              <input type="text" v-model="form.quote_number" required class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('customer', 'Customer') }} <span class="required">*</span></label>
              <select v-model="form.customer_id" required class="form-input">
                <option value="">-- Select --</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('quote-date', 'Quote Date') }}</label>
              <input type="date" v-model="form.quote_date" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('valid-until', 'Valid Until') }}</label>
              <input type="date" v-model="form.valid_until" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('subtotal', 'Subtotal') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.subtotal" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('tax', 'Tax') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.tax" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('grand-total', 'Grand Total') }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.grand_total" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('status', 'Status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Draft">Draft</option>
                <option value="Sent">Sent</option>
                <option value="Accepted">Accepted</option>
                <option value="Rejected">Rejected</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('notes', 'Notes') }}</label>
            <textarea v-model="form.notes" class="form-input" rows="2"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving', 'Saving...') : t('save', 'Save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete?')" :message="t('confirm-delete-msg', 'Delete') + ' ' + confirmTarget.quote_number + '?'" @confirm="executeDelete" @cancel="confirmTarget = null" />
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
    return await api.get('/T0067I/', { params })
  },
  defaultLimit: 50,
  defaultOrderBy: 'quote_date',
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

const customers = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ quote_number: '', customer_id: null, quote_date: '', valid_until: '', subtotal: 0, tax: 0, grand_total: 0, status: 'Draft', notes: '' })
const editId = ref(null)
const confirmTarget = ref(null)

function statusBadge(status) {
  const map = { Draft: 'badge-inactive', Sent: 'badge-info', Accepted: 'badge-active', Rejected: 'badge-danger', Converted: 'badge-active', Cancelled: 'badge-inactive' }
  return map[status] || 'badge-inactive'
}

function customerName(id) {
  const c = customers.value.find(x => x.id === id)
  return c ? c.name : `#${id}`
}

async function loadCustomers() {
  try { const res = await api.get('/T0010I/'); customers.value = res.data || [] } catch {}
}

function today() { return new Date().toISOString().split('T')[0] }

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
  editing.value = false; editId.value = null
  form.value = { quote_number: '', customer_id: null, quote_date: today(), valid_until: '', subtotal: 0, tax: 0, grand_total: 0, status: 'Draft', notes: '' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true; editId.value = item.id
  form.value = { quote_number: item.quote_number, customer_id: item.customer_id, quote_date: item.quote_date || today(), valid_until: item.valid_until || '', subtotal: item.subtotal || 0, tax: item.tax || 0, grand_total: item.grand_total || 0, status: item.status || 'Draft', notes: item.notes || '' }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function saveItem() {
  saving.value = true
  try {
    const payload = { ...form.value, notes: form.value.notes || null, valid_until: form.value.valid_until || null }
    if (editing.value) { await api.put(`/T0067I/${editId.value}`, payload); toast(t('saved-ok', 'Saved successfully'), 'success') }
    else { await api.post('/T0067I/', payload); toast(t('created', 'Created successfully'), 'success') }
    closeModal(); await load()
  } catch { toast(t('failed-save', 'Failed to save'), 'error') }
  finally { saving.value = false }
}

function deleteItem(item) { confirmTarget.value = item }
async function executeDelete() {
  const item = confirmTarget.value; confirmTarget.value = null
  try { await api.delete(`/T0067I/${item.id}`); toast(t('deleted', 'Deleted successfully'), 'success'); await load() }
  catch { toast(t('failed-save', 'Failed to delete'), 'error') }
}

onMounted(() => {
  loadCustomers()
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
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.view-mode-toggle { display: inline-flex; background: var(--bg-surface-hover, #f3f4f6); border-radius: 8px; padding: 2px; border: 1px solid var(--border-light, #e5e7eb); }
.mode-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; background: transparent; border-radius: 6px; color: var(--text-muted, #6b7280); cursor: pointer; transition: all 0.15s ease; }
.mode-btn .material-symbols-outlined { font-size: 18px; }
.mode-btn:hover { color: var(--text-primary, #111827); }
.mode-btn.active { background: var(--bg-surface, #ffffff); color: var(--color-primary, #5d3fd3); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

.data-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: var(--bg-surface-low); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default); white-space: nowrap; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:hover { background: var(--bg-surface-hover); }

.th-sortable { cursor: pointer; user-select: none; transition: background-color 0.15s; }
.th-sortable:hover { background-color: var(--bg-surface-hover, #f3f4f6); }
.th-content { display: inline-flex; align-items: center; gap: 4px; }
.th-content-end { justify-content: flex-end; width: 100%; }
.th-content-center { justify-content: center; width: 100%; }
.sort-icon { font-size: 15px; color: var(--text-faint, #9ca3af); vertical-align: middle; }
.th-sortable.is-sorted .sort-icon { color: var(--color-primary, #5d3fd3); }

.cell-order { font-family: monospace; font-weight: 600; }
.order-link { color: var(--color-primary); cursor: pointer; text-decoration: none; }
.order-link:hover { text-decoration: underline; }
.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-subtle); }
.col-num { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
.col-actions { width: 80px; }
.text-center { text-align: center; }
.empty-state { text-align: center; padding: 48px; color: var(--text-faint); font-size: 14px; }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 16px; display: block; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-inactive { background: var(--bg-surface-low); color: var(--text-subtle); }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: var(--color-primary, #5d3fd3); color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--text-primary, #333); padding: 8px 20px; border: 1px solid var(--border-default, #ddd); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover, #f5f5f5); }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
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
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
textarea.form-input { resize: vertical; }
.required { color: #dc2626; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-num { text-align: left; }
[dir="rtl"] .page-actions { flex-direction: row-reverse; }
</style>

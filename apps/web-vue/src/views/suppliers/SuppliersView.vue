<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('suppliers-title', 'Suppliers') }}</h1>
        <p class="page-subtitle">{{ t('suppliers-sub', 'Manage your supplier and vendor directory') }}</p>
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
          <span class="material-symbols-outlined">add</span> {{ t('new-supplier', 'New Supplier') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading && !items.length" :rows="6" :columns="8" />
    <ErrorState v-else-if="error && !items.length" :message="error" @retry="load()" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">local_shipping</span>
      <p>{{ t('no-records', 'No records found') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('new-supplier', 'New Supplier') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'name' }" @click="toggleSort('name')">
                <span class="th-content">
                  {{ t('name', 'Name') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'name' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th class="th-sortable" :class="{ 'is-sorted': orderBy === 'category' }" @click="toggleSort('category')">
                <span class="th-content">
                  {{ t('category', 'Category') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'category' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
              <th>{{ t('supplier-phone', 'Phone') }}</th>
              <th>{{ t('supplier-email', 'Email') }}</th>
              <th>{{ t('supplier-payment-terms', 'Payment Terms') }}</th>
              <th class="text-center th-sortable" :class="{ 'is-sorted': orderBy === 'rating' }" @click="toggleSort('rating')">
                <span class="th-content th-content-center">
                  {{ t('supplier-rating', 'Rating') }}
                  <span class="material-symbols-outlined sort-icon">
                    {{ orderBy === 'rating' ? (orderDir === 'desc' ? 'arrow_downward' : 'arrow_upward') : 'unfold_more' }}
                  </span>
                </span>
              </th>
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
            <tr v-for="item in items" :key="item.id" :class="{ 'row-inactive': !item.is_active }">
              <td class="cell-name">{{ item.name }}</td>
              <td>{{ item.category || '-' }}</td>
              <td class="cell-mono">{{ item.phone || '-' }}</td>
              <td class="cell-mono">{{ item.email || '-' }}</td>
              <td>{{ item.payment_terms || '-' }}</td>
              <td class="text-center">
                <span v-if="item.rating > 0" class="badge" :class="ratingBadge(item.rating)">{{ item.rating }}/5</span>
                <span v-else class="badge badge-inactive">-</span>
              </td>
              <td class="text-center">
                <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ item.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}
                </span>
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
          <span>{{ t('pagination-loading-more', 'Loading more suppliers...') }}</span>
        </div>
        <div v-else-if="hasNextPage" class="infinite-action">
          <button type="button" class="btn-outline btn-sm" @click="loadMore">
            <span class="material-symbols-outlined">expand_more</span>
            {{ t('pagination-load-more', 'Load More') }} ({{ items.length }} / {{ totalCount }})
          </button>
        </div>
        <div v-else class="infinite-end">
          <span>{{ t('pagination-all-loaded', 'All') }} {{ totalCount }} {{ t('pagination-items-loaded', 'suppliers loaded') }}</span>
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
          <h3>{{ editing ? t('edit-supplier', 'Edit Supplier') : t('new-supplier', 'New Supplier') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('name', 'Name') }} <span class="required">*</span></label>
              <input type="text" v-model="form.name" required class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('category', 'Category') }}</label>
              <input type="text" v-model="form.category" class="form-input" maxlength="100" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('supplier-phone', 'Phone') }}</label>
              <input type="text" v-model="form.phone" class="form-input" maxlength="30" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier-email', 'Email') }}</label>
              <input type="email" v-model="form.email" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('supplier-payment-terms', 'Payment Terms') }}</label>
              <input type="text" v-model="form.payment_terms" class="form-input" maxlength="100" />
            </div>
            <div class="form-group">
              <label>{{ t('supplier-rating', 'Rating') }} (0-5)</label>
              <input type="number" min="0" max="5" v-model.number="form.rating" class="form-input" />
            </div>
          </div>
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              <span>{{ t('active', 'Active') }}</span>
            </label>
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
    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete', 'Delete Supplier')" :message="t('confirm-delete-msg', 'Are you sure you want to delete') + ' ' + confirmTarget.name + '?'" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
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

const isInfiniteMode = ref(false)
const infiniteSentinel = ref(null)
let observer = null

const pagination = usePagination({
  fetchFn: async (params) => {
    return await api.get('/T0011I/', { params })
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

const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ name: '', category: '', phone: '', email: '', payment_terms: '', rating: 0, is_active: true })
const editId = ref(null)
const confirmTarget = ref(null)

function ratingBadge(rating) {
  if (rating >= 4) return 'badge-active'
  if (rating >= 2) return 'badge-warning'
  return 'badge-inactive'
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
  form.value = { name: '', category: '', phone: '', email: '', payment_terms: '', rating: 0, is_active: true }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    name: item.name,
    category: item.category || '',
    phone: item.phone || '',
    email: item.email || '',
    payment_terms: item.payment_terms || '',
    rating: item.rating || 0,
    is_active: item.is_active,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      phone: form.value.phone || null,
      email: form.value.email || null,
      category: form.value.category || null,
      payment_terms: form.value.payment_terms || null,
    }
    if (editing.value) {
      await api.put(`/T0011I/${editId.value}`, payload)
      toast('Supplier ' + t('saved-ok', 'saved successfully'), 'success')
    } else {
      await api.post('/T0011I/', payload)
      toast('Supplier ' + t('saved-ok', 'saved successfully'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save', 'Failed to save') + ' Supplier', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0011I/${item.id}`)
    toast('Supplier deleted', 'success')
    await load()
  } catch {
    toast(t('failed-save', 'Failed to delete') + ' Supplier', 'error')
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
.data-table th { background: var(--bg-surface-low, #f9fafb); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--text-secondary, #555); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-default, #e0e0e0); }
.data-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-light, #f0f0f0); }
.data-table tbody tr:hover { background: var(--bg-surface-hover, #fafaff); }

.th-sortable { cursor: pointer; user-select: none; transition: background-color 0.15s; }
.th-sortable:hover { background-color: var(--bg-surface-hover, #f3f4f6); }
.th-content { display: inline-flex; align-items: center; gap: 4px; }
.th-content-center { justify-content: center; width: 100%; }
.sort-icon { font-size: 15px; color: var(--text-faint, #9ca3af); vertical-align: middle; }
.th-sortable.is-sorted .sort-icon { color: var(--color-primary, #5d3fd3); }

.cell-name { font-weight: 600; color: var(--text-primary, #1a1a2e); }
.cell-mono { font-family: monospace; font-size: 12px; color: var(--text-muted, #888); }
.col-actions { width: 80px; }
.text-center { text-align: center; }
.row-inactive { opacity: 0.55; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
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
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-light, #eee); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary, #1a1a2e); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary, #444); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input, #ddd); border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; background: var(--bg-surface, #fff); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary, #5d3fd3); }
.required { color: var(--color-error, #dc2626); }
.checkbox-group { display: flex; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-top: 8px; }
.checkbox-label input { width: 16px; height: 16px; accent-color: var(--color-primary, #5d3fd3); }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .page-actions { flex-direction: row-reverse; }
</style>

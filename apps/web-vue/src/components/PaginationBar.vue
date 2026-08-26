<template>
  <div
    class="pagination-bar"
    :class="{
      'pagination-compact': compact,
      'is-loading': effectiveLoading,
      'is-disabled': effectiveDisabled,
    }"
    :dir="dir"
    role="navigation"
    aria-label="Pagination Navigation"
  >
    <!-- Left: Showing range and total -->
    <div v-if="showTotal" class="pagination-info">
      <template v-if="currentTotal > 0">
        <span class="info-text">
          {{ t('pagination-showing', 'Showing') }}
          <strong class="info-num">{{ from }}</strong>
          -
          <strong class="info-num">{{ to }}</strong>
          {{ t('pagination-of', 'of') }}
          <strong class="info-num">{{ formattedTotal }}</strong>
          {{ t('pagination-items', 'items') }}
        </span>
      </template>
      <template v-else>
        <span class="info-empty">{{ t('pagination-no-records', 'No records found') }}</span>
      </template>
    </div>

    <!-- Right / Controls: Page size selector and page navigation buttons -->
    <div class="pagination-controls">
      <!-- Page Size Selector -->
      <div v-if="showPageSize" class="pagination-size">
        <label :for="sizeSelectId" class="size-label">
          {{ t('pagination-rows-per-page', 'Rows per page:') }}
        </label>
        <select
          :id="sizeSelectId"
          class="size-select"
          :value="currentLimit"
          :disabled="effectiveDisabled || effectiveLoading"
          @change="onSizeChange"
          aria-label="Items per page"
        >
          <option v-for="size in effectivePageSizeOptions" :key="size" :value="size">
            {{ size }}
          </option>
        </select>
      </div>

      <!-- Navigation buttons -->
      <div class="pagination-nav">
        <!-- First Page -->
        <button
          v-if="showFirstLast"
          type="button"
          class="page-btn page-btn-icon"
          :disabled="!hasPrev || effectiveDisabled || effectiveLoading"
          :title="t('pagination-first-page', 'First page')"
          :aria-label="t('pagination-first-page', 'First page')"
          @click="goToPage(1)"
        >
          <span class="material-symbols-outlined">{{ isRTL ? 'last_page' : 'first_page' }}</span>
        </button>

        <!-- Previous Page -->
        <button
          type="button"
          class="page-btn page-btn-icon"
          :disabled="!hasPrev || effectiveDisabled || effectiveLoading"
          :title="t('pagination-prev-page', 'Previous page')"
          :aria-label="t('pagination-prev-page', 'Previous page')"
          @click="goToPage(currentPage - 1)"
        >
          <span class="material-symbols-outlined">{{ isRTL ? 'chevron_right' : 'chevron_left' }}</span>
        </button>

        <!-- Page Numbers -->
        <div v-if="showPageNumbers" class="pagination-pages">
          <template v-for="(p, idx) in visiblePages" :key="idx">
            <span v-if="p === '...'" class="page-ellipsis">&hellip;</span>
            <button
              v-else
              type="button"
              class="page-btn page-btn-num"
              :class="{ 'is-active': p === currentPage }"
              :disabled="effectiveDisabled || effectiveLoading"
              :aria-current="p === currentPage ? 'page' : undefined"
              :aria-label="`${t('pagination-page', 'Page')} ${p}`"
              @click="goToPage(p)"
            >
              {{ p }}
            </button>
          </template>
        </div>

        <!-- Current Page Indicator in Compact Mode -->
        <div v-else-if="compact" class="pagination-compact-indicator">
          {{ currentPage }} / {{ totalPages }}
        </div>

        <!-- Next Page -->
        <button
          type="button"
          class="page-btn page-btn-icon"
          :disabled="!hasNext || effectiveDisabled || effectiveLoading"
          :title="t('pagination-next-page', 'Next page')"
          :aria-label="t('pagination-next-page', 'Next page')"
          @click="goToPage(currentPage + 1)"
        >
          <span class="material-symbols-outlined">{{ isRTL ? 'chevron_left' : 'chevron_right' }}</span>
        </button>

        <!-- Last Page -->
        <button
          v-if="showFirstLast"
          type="button"
          class="page-btn page-btn-icon"
          :disabled="!hasNext || effectiveDisabled || effectiveLoading"
          :title="t('pagination-last-page', 'Last page')"
          :aria-label="t('pagination-last-page', 'Last page')"
          @click="goToPage(totalPages)"
        >
          <span class="material-symbols-outlined">{{ isRTL ? 'first_page' : 'last_page' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'
import { useI18n } from '../composables/useI18n.js'

const props = defineProps({
  pagination: {
    type: Object,
    default: null,
  },
  modelValue: {
    type: Number,
    default: null,
  },
  page: {
    type: Number,
    default: 1,
  },
  limit: {
    type: Number,
    default: null,
  },
  pageSize: {
    type: Number,
    default: 50,
  },
  total: {
    type: Number,
    default: null,
  },
  totalCount: {
    type: Number,
    default: 0,
  },
  pageSizeOptions: {
    type: Array,
    default: () => [10, 25, 50, 100, 200, 500],
  },
  maxVisibleButtons: {
    type: Number,
    default: 5,
  },
  showPageSize: {
    type: Boolean,
    default: true,
  },
  showTotal: {
    type: Boolean,
    default: true,
  },
  showPageNumbers: {
    type: Boolean,
    default: true,
  },
  showFirstLast: {
    type: Boolean,
    default: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'update:modelValue',
  'update:page',
  'update:pageSize',
  'update:limit',
  'page-change',
  'size-change',
  'change',
])

const { t, dir, isRTL } = useI18n()
const sizeSelectId = useId ? useId() : `page-size-${Math.random().toString(36).slice(2, 7)}`

// Unified reactive accessors (supporting both props.pagination instance and direct props)
const currentPage = computed(() => {
  if (props.pagination?.page !== undefined) {
    return Number(props.pagination.page.value ?? props.pagination.page) || 1
  }
  if (props.modelValue !== null && props.modelValue !== undefined) {
    return Number(props.modelValue) || 1
  }
  return Number(props.page) || 1
})

const currentLimit = computed(() => {
  if (props.pagination?.limit !== undefined) {
    return Number(props.pagination.limit.value ?? props.pagination.limit) || 50
  }
  if (props.limit !== null && props.limit !== undefined) {
    return Number(props.limit) || 50
  }
  return Number(props.pageSize) || 50
})

const currentTotal = computed(() => {
  if (props.pagination?.totalCount !== undefined) {
    return Number(props.pagination.totalCount.value ?? props.pagination.totalCount) || 0
  }
  if (props.total !== null && props.total !== undefined) {
    return Number(props.total) || 0
  }
  return Number(props.totalCount) || 0
})

const effectiveLoading = computed(() => {
  if (props.pagination?.loading !== undefined) {
    return Boolean(props.pagination.loading.value ?? props.pagination.loading)
  }
  return props.loading
})

const effectiveDisabled = computed(() => props.disabled)

const totalPages = computed(() => {
  if (props.pagination?.totalPages !== undefined) {
    return Number(props.pagination.totalPages.value ?? props.pagination.totalPages) || 1
  }
  if (!currentTotal.value || currentTotal.value <= 0) return 1
  return Math.max(1, Math.ceil(currentTotal.value / (currentLimit.value || 50)))
})

const from = computed(() => {
  if (currentTotal.value === 0) return 0
  return (currentPage.value - 1) * currentLimit.value + 1
})

const to = computed(() => {
  if (currentTotal.value === 0) return 0
  return Math.min(currentPage.value * currentLimit.value, currentTotal.value)
})

const formattedTotal = computed(() => {
  return currentTotal.value.toLocaleString()
})

const hasPrev = computed(() => currentPage.value > 1)
const hasNext = computed(() => currentPage.value < totalPages.value)

const effectivePageSizeOptions = computed(() => {
  const opts = Array.isArray(props.pageSizeOptions) ? [...props.pageSizeOptions] : [10, 25, 50, 100, 200, 500]
  if (!opts.includes(currentLimit.value)) {
    opts.push(currentLimit.value)
    opts.sort((a, b) => a - b)
  }
  return opts
})

// Smart visible page numbers computation
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const maxButtons = Math.max(3, props.maxVisibleButtons)

  if (total <= maxButtons + 2) {
    const pages = []
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
    return pages
  }

  const pages = []
  const half = Math.floor(maxButtons / 2)
  let start = Math.max(2, current - half)
  let end = Math.min(total - 1, current + half)

  if (current <= half + 2) {
    start = 2
    end = maxButtons
  } else if (current >= total - half - 1) {
    start = total - maxButtons + 1
    end = total - 1
  }

  pages.push(1)
  if (start > 2) {
    pages.push('...')
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (end < total - 1) {
    pages.push('...')
  }
  pages.push(total)

  return pages
})

function goToPage(targetPage) {
  const p = Math.max(1, Math.min(Number(targetPage) || 1, totalPages.value))
  if (p === currentPage.value) return

  emit('update:modelValue', p)
  emit('update:page', p)
  emit('page-change', p)
  emit('change', {
    page: p,
    limit: currentLimit.value,
    offset: (p - 1) * currentLimit.value,
  })

  if (props.pagination?.setPage && typeof props.pagination.setPage === 'function') {
    props.pagination.setPage(p)
  }
}

function onSizeChange(event) {
  const newSize = Number(event.target.value) || 50
  if (newSize === currentLimit.value) return

  emit('update:pageSize', newSize)
  emit('update:limit', newSize)
  emit('size-change', newSize)
  emit('change', {
    page: 1,
    limit: newSize,
    offset: 0,
  })

  if (props.pagination?.setLimit && typeof props.pagination.setLimit === 'function') {
    props.pagination.setLimit(newSize)
  }
}
</script>

<style scoped>
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-light);
  font-size: 13px;
  color: var(--text-secondary);
  user-select: none;
  flex-wrap: wrap;
}

.pagination-bar.is-loading {
  opacity: 0.75;
  pointer-events: none;
}

.pagination-bar.is-disabled {
  opacity: 0.5;
  pointer-events: none;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
}

.info-num {
  color: var(--text-primary);
  font-weight: 600;
}

.info-empty {
  color: var(--text-faint);
  font-style: italic;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.pagination-size {
  display: flex;
  align-items: center;
  gap: 8px;
}

.size-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.size-select {
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-input, #dddddd);
  border-radius: 6px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.size-select:hover:not(:disabled) {
  border-color: var(--color-primary);
}

.size-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--bg-primary-faded, rgba(93, 63, 211, 0.15));
}

.pagination-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination-pages {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-light, #f0f0f0);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.page-btn .material-symbols-outlined {
  font-size: 18px;
}

.page-btn:hover:not(:disabled) {
  background: var(--bg-surface-hover, #f5f5f5);
  border-color: var(--border-default, #e0e0e0);
  color: var(--color-primary);
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  border-color: transparent;
}

.page-btn-num.is-active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #ffffff;
  font-weight: 700;
}

html.dark .page-btn-num.is-active {
  color: #1a1a2e;
}

.page-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 32px;
  color: var(--text-faint);
  font-weight: 600;
}

.pagination-compact {
  padding: 8px 12px;
}

.pagination-compact-indicator {
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

[dir="rtl"] .pagination-bar {
  direction: rtl;
}

[dir="rtl"] .pagination-controls {
  flex-direction: row-reverse;
}

@media (max-width: 640px) {
  .pagination-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .pagination-controls {
    justify-content: space-between;
  }
}
</style>

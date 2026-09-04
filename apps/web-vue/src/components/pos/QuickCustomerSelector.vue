<template>
  <div class="quick-customer-selector">
    <div class="selector-row">
      <span class="material-symbols-outlined icon">person</span>
      <input
        type="text"
        v-model="searchQuery"
        @focus="isFocused = true"
        @input="onSearchInput"
        @keydown.enter.prevent="selectCurrent"
        @keydown.esc="isFocused = false"
        :placeholder="t('pos-select-customer', 'Walk-in Customer (click to change...)')"
        class="customer-input"
      />
      <button v-if="selectedCustomer.id" class="clear-cust-btn" @click="resetToWalkIn" title="Reset to Walk-in">
        &times;
      </button>
    </div>

    <!-- Quick Picker Pills -->
    <div class="quick-picks" v-if="quickCustomers.length">
      <button
        v-for="c in quickCustomers"
        :key="c.id"
        :class="['pick-pill', { active: selectedCustomer.id === c.id }]"
        @click="selectCustomer(c)"
      >
        {{ c.name }}
      </button>
    </div>

    <!-- Dropdown search results -->
    <div class="dropdown-results" v-if="isFocused && searchResults.length">
      <div
        v-for="c in searchResults"
        :key="c.id"
        class="dropdown-item"
        @mousedown.prevent="selectCustomer(c)"
      >
        <div class="cust-name">{{ c.name }}</div>
        <div class="cust-details" v-if="c.phone || c.customer_group">
          <span>{{ c.phone }}</span>
          <span v-if="c.customer_group" class="badge">{{ c.customer_group }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ id: null, name: 'Walk-in Customer' })
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const { t } = useI18n()

const searchQuery = ref(props.modelValue.name || 'Walk-in Customer')
const isFocused = ref(false)
const selectedCustomer = ref(props.modelValue)
const quickCustomers = ref([])
const searchResults = ref([])

let debounceTimer = null

async function loadCustomers(q = '') {
  try {
    const res = await api.get('/pos/customers', { params: { q, limit: 8 } })
    const data = res.data || []
    if (!q) {
      quickCustomers.value = data.slice(0, 4)
    }
    searchResults.value = data
  } catch (e) {
    console.warn('Failed to load customers:', e)
  }
}

function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    loadCustomers(searchQuery.value.trim())
  }, 200)
}

function selectCustomer(cust) {
  selectedCustomer.value = cust
  searchQuery.value = cust.name
  isFocused.value = false
  emit('update:modelValue', cust)
  emit('change', cust)
}

function resetToWalkIn() {
  const walkIn = { id: null, name: t('pos-walkin', 'Walk-in Customer') }
  selectCustomer(walkIn)
}

function selectCurrent() {
  if (searchResults.value.length) {
    selectCustomer(searchResults.value[0])
  } else {
    isFocused.value = false
  }
}

onMounted(() => {
  loadCustomers()
})
</script>

<style scoped>
.quick-customer-selector {
  position: relative;
  width: 100%;
}
.selector-row {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface-low);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 6px 12px;
}
.icon {
  font-size: 18px;
  color: var(--text-subtle);
}
.customer-input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  background: transparent;
  font-family: inherit;
}
.clear-cust-btn {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-subtle);
  padding: 0 4px;
}
.quick-picks {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  overflow-x: auto;
}
.pick-pill {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
}
.pick-pill:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.pick-pill.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.dropdown-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.dropdown-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-light);
}
.dropdown-item:hover {
  background: var(--bg-surface-hover);
}
.cust-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.cust-details {
  font-size: 11px;
  color: var(--text-subtle);
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 2px;
}
.badge {
  background: var(--bg-surface-low);
  padding: 1px 6px;
  border-radius: 4px;
}
</style>

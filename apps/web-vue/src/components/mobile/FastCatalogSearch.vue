<template>
  <div class="fast-catalog-container">
    <!-- Search & Scanner Toolbar -->
    <div class="catalog-toolbar">
      <!-- Search Input & Barcode Combined Row -->
      <div class="search-row">
        <div class="search-input-box">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            ref="searchInputRef"
            v-model="store.searchQuery"
            type="text"
            class="catalog-search-input"
            placeholder="Search by SKU, name, or description..."
            aria-label="Search catalog"
          />
          <button
            v-if="store.searchQuery"
            class="clear-btn"
            @click="store.searchQuery = ''"
            aria-label="Clear search"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Barcode Scanner Input / Trigger -->
        <div class="barcode-box">
          <span class="material-symbols-outlined barcode-icon">qr_code_scanner</span>
          <input
            ref="barcodeInputRef"
            v-model="barcodeQuery"
            type="text"
            class="barcode-input"
            placeholder="Scan barcode..."
            aria-label="Scan barcode"
            @keydown.enter.prevent="handleBarcodeSubmit"
          />
          <button
            class="barcode-action-btn"
            :disabled="!barcodeQuery"
            @click="handleBarcodeSubmit"
            title="Search by barcode"
          >
            <span class="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>

      <!-- Filters & Category Carousel -->
      <div class="filter-controls-row">
        <!-- Category Filter Pills -->
        <div class="category-scroll-container">
          <button
            class="cat-pill"
            :class="{ active: store.selectedCategory === 'all' || !store.selectedCategory }"
            @click="store.setSelectedCategory('all')"
          >
            All Products
            <span class="cat-count">{{ store.totalProductsCount }}</span>
          </button>

          <button
            v-for="cat in store.categories"
            :key="cat.name"
            class="cat-pill"
            :class="{ active: store.selectedCategory === cat.name }"
            @click="store.setSelectedCategory(cat.name)"
          >
            {{ cat.name }}
            <span class="cat-count">{{ cat.count }}</span>
          </button>
        </div>

        <!-- Extra Filter Options (Stock & Sort) -->
        <div class="quick-options-row">
          <button
            class="toggle-stock-btn"
            :class="{ active: store.inStockOnlyFilter }"
            @click="store.toggleInStockOnly"
          >
            <span class="material-symbols-outlined stock-icon">
              {{ store.inStockOnlyFilter ? 'check_box' : 'check_box_outline_blank' }}
            </span>
            In-Stock Only
          </button>

          <div class="sort-selector-wrapper">
            <span class="material-symbols-outlined sort-icon">sort</span>
            <select
              :value="store.sortBy"
              class="sort-dropdown"
              @change="store.setSortBy($event.target.value)"
            >
              <option value="relevance">Relevance</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="price_asc">Price (Low-High)</option>
              <option value="price_desc">Price (High-Low)</option>
              <option value="stock_desc">Stock (Highest)</option>
            </select>
          </div>

          <span v-if="store.searchResults.executionTimeMs !== undefined" class="latency-badge" title="IndexedDB In-Memory Query Latency">
            ⚡ {{ store.searchResults.executionTimeMs }}ms
          </span>
        </div>
      </div>
    </div>

    <!-- Product Grid / List -->
    <div class="products-grid-container">
      <div v-if="store.catalogLoading" class="catalog-feedback loading">
        <span class="material-symbols-outlined spin-icon">sync</span>
        <span>Loading product catalog...</span>
      </div>

      <template v-else>
        <div
          v-for="product in productsList"
          :key="product.id"
          class="product-card"
          :class="{ 'in-cart': getCartQty(product.id) > 0, 'out-of-stock': (product.available_qty || product.stock_quantity || 0) <= 0 }"
          @click="handleQuickAdd(product)"
        >
          <!-- Top Row: Category & In-Cart Badge -->
          <div class="card-header-line">
            <span class="product-category-tag">{{ product.category || 'General' }}</span>
            <span v-if="getCartQty(product.id) > 0" class="in-cart-counter">
              <span class="material-symbols-outlined in-cart-icon">shopping_bag</span>
              {{ getCartQty(product.id) }} in cart
            </span>
          </div>

          <!-- Product Info -->
          <div class="card-main-info">
            <h4 class="product-title">{{ product.name }}</h4>
            <div class="sku-barcode-subline">
              <span class="sku-text">SKU: {{ product.sku }}</span>
              <span v-if="product.barcode" class="barcode-text">
                <span class="material-symbols-outlined mini-icon">qr_code</span>
                {{ product.barcode }}
              </span>
            </div>
          </div>

          <!-- Price & Stock Footer -->
          <div class="card-footer-row">
            <div class="pricing-box">
              <div class="price-main-line">
                <span class="price-currency">{{ formatMoney(getProductPrice(product).price) }}</span>
                <span class="uom-suffix">/ {{ product.uom_code || product.uom || 'ea' }}</span>
              </div>
              <div v-if="getProductPrice(product).isContracted" class="contract-pricing-tag">
                <span class="material-symbols-outlined mini-icon">verified</span>
                Contract Price
              </div>
            </div>

            <!-- Stock Availability Badge -->
            <div class="stock-status-box">
              <span
                class="stock-pill"
                :class="getStockBadgeClass(product.available_qty ?? product.stock_quantity ?? 0)"
              >
                {{ formatStockText(product.available_qty ?? product.stock_quantity ?? 0) }}
              </span>
            </div>

            <!-- Quick Add Action -->
            <button
              class="btn-quick-add"
              :class="{ added: getCartQty(product.id) > 0 }"
              @click.stop="handleQuickAdd(product)"
              aria-label="Add to cart"
            >
              <span class="material-symbols-outlined">add</span>
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="productsList.length === 0" class="catalog-feedback empty">
          <span class="material-symbols-outlined empty-box-icon">search_off</span>
          <p class="empty-title">No products found</p>
          <p class="empty-desc">
            No items matched your search criteria. Try clearing search filters or changing the category.
          </p>
          <button class="btn-reset-filters" @click="resetFilters">
            Reset Filters
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'

const store = useFieldSalesStore()
const { show: toast } = useToast()

const searchInputRef = ref(null)
const barcodeInputRef = ref(null)
const barcodeQuery = ref('')

const productsList = computed(() => {
  return store.filteredProducts
})

function getCartQty(productId) {
  const line = store.draft.lines.find((l) => l.product_id === productId)
  return line ? line.qty : 0
}

function getProductPrice(product) {
  if (!product) return { price: 0, isContracted: false }
  // Check if customer has contracted pricing
  if (store.selectedCustomer?.default_price_list_id) {
    const listId = store.selectedCustomer.default_price_list_id
    // Price rules might be loaded in store
  }
  const base = Number(product.base_price !== undefined ? product.base_price : product.price || 0)
  return { price: base, isContracted: false }
}

function getStockBadgeClass(qty) {
  const n = Number(qty) || 0
  if (n <= 0) return 'stock-out'
  if (n < 10) return 'stock-low'
  return 'stock-good'
}

function formatStockText(qty) {
  const n = Number(qty) || 0
  if (n <= 0) return 'Out of Stock'
  if (n < 10) return `${n} in Stock`
  return `${n} in Stock`
}

function formatMoney(amount) {
  const num = Number(amount) || 0
  return '$' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

async function handleQuickAdd(product) {
  if (!store.selectedCustomer) {
    toast('Please select a customer before adding items to order', 'warning')
    return
  }
  try {
    await store.addItemToCart(product, 1)
    toast(`Added ${product.name} (Qty: ${getCartQty(product.id)})`, 'success')
  } catch (err) {
    toast(`Failed to add item: ${err.message}`, 'error')
  }
}

async function handleBarcodeSubmit() {
  const code = barcodeQuery.value.trim()
  if (!code) return

  const product = store.lookupBarcode(code) || store.lookupSku(code)
  if (product) {
    await handleQuickAdd(product)
    barcodeQuery.value = ''
    barcodeInputRef.value?.focus()
  } else {
    toast(`Barcode or SKU not found: ${code}`, 'error')
    barcodeInputRef.value?.select()
  }
}

function resetFilters() {
  store.setSearchQuery('')
  store.setSelectedCategory('all')
  if (store.inStockOnlyFilter) {
    store.toggleInStockOnly()
  }
}

// Hardware Barcode Scanner listener (captures fast scanner bursts)
let barcodeBuffer = ''
let lastKeyTime = 0
const SCANNER_THRESHOLD = 50

function onKeydown(e) {
  if (e.target === searchInputRef.value || e.target === barcodeInputRef.value) return
  if (e.ctrlKey || e.altKey || e.metaKey) return

  const now = Date.now()
  const elapsed = now - lastKeyTime

  if (e.key === 'Enter') {
    if (barcodeBuffer.length >= 3 && elapsed < 300) {
      e.preventDefault()
      const scannedCode = barcodeBuffer
      barcodeBuffer = ''
      lastKeyTime = 0
      const product = store.lookupBarcode(scannedCode) || store.lookupSku(scannedCode)
      if (product) {
        handleQuickAdd(product)
      } else {
        toast(`Scanned product not found: ${scannedCode}`, 'error')
      }
      return
    }
    barcodeBuffer = ''
    lastKeyTime = 0
    return
  }

  if (e.key.length === 1) {
    if (elapsed < SCANNER_THRESHOLD || !lastKeyTime) {
      barcodeBuffer += e.key
    } else {
      barcodeBuffer = e.key
    }
    lastKeyTime = now
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.fast-catalog-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

/* Toolbar */
.catalog-toolbar {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.search-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.search-input-box {
  position: relative;
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-subtle);
  font-size: 20px;
  pointer-events: none;
}

.catalog-search-input {
  width: 100%;
  height: 42px;
  padding: 8px 36px 8px 38px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s ease;
}

.catalog-search-input:focus {
  border-color: var(--color-primary);
}

.clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 4px;
}

.clear-btn .material-symbols-outlined {
  font-size: 16px;
}

.barcode-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 170px;
}

@media (max-width: 500px) {
  .barcode-box {
    width: 100%;
  }
}

.barcode-icon {
  position: absolute;
  left: 8px;
  color: var(--text-subtle);
  font-size: 18px;
  pointer-events: none;
}

.barcode-input {
  width: 100%;
  height: 42px;
  padding: 8px 36px 8px 32px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
}

.barcode-input:focus {
  border-color: var(--color-primary);
}

.barcode-action-btn {
  position: absolute;
  right: 4px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.barcode-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.barcode-action-btn .material-symbols-outlined {
  font-size: 16px;
}

/* Category Pills & Filters */
.filter-controls-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-scroll-container {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}

.cat-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  background: var(--bg-surface-low, #f9fafb);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.cat-pill:hover {
  border-color: var(--color-primary);
}

.cat-pill.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.cat-count {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.08);
}

.cat-pill.active .cat-count {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

.quick-options-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 4px;
  border-top: 1px solid var(--border-light);
}

.toggle-stock-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
}

.toggle-stock-btn.active {
  color: var(--color-primary);
}

.stock-icon {
  font-size: 18px;
}

.sort-selector-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sort-icon {
  font-size: 16px;
  color: var(--text-subtle);
}

.sort-dropdown {
  background: var(--bg-surface);
  border: 1px solid var(--border-input);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--text-primary);
  outline: none;
}

.latency-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-success, #16a34a);
  font-family: monospace;
  background: #f0fdf4;
  border: 1px solid #dcfce7;
  padding: 2px 6px;
  border-radius: 6px;
}

/* Product Cards Grid */
.products-grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

@media (max-width: 600px) {
  .products-grid-container {
    grid-template-columns: 1fr;
  }
}

.product-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
  transition: all 0.18s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.product-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06);
}

.product-card.in-cart {
  border-color: var(--color-primary);
  background: var(--bg-surface);
}

.product-card.out-of-stock {
  opacity: 0.75;
}

.card-header-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-category-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-subtle);
  background: var(--bg-surface-low, #f9fafb);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-light);
}

.in-cart-counter {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--bg-primary-faded, #e6deff);
  padding: 2px 6px;
  border-radius: 6px;
}

.in-cart-icon {
  font-size: 13px;
}

.card-main-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.sku-barcode-subline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-subtle);
}

.barcode-text {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
}

.pricing-box {
  display: flex;
  flex-direction: column;
}

.price-main-line {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.price-currency {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.uom-suffix {
  font-size: 11px;
  color: var(--text-muted);
}

.contract-pricing-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  font-weight: 700;
  color: #2563eb;
}

.stock-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
}

.stock-good {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.stock-low {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
}

.stock-out {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.btn-quick-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-quick-add:hover {
  background: var(--color-primary-hover);
  transform: scale(1.05);
}

.btn-quick-add.added {
  background: #16a34a;
}

.btn-quick-add .material-symbols-outlined {
  font-size: 20px;
}

/* Feedback states */
.catalog-feedback {
  grid-column: 1 / -1;
  padding: 40px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-subtle);
}

.empty-box-icon {
  font-size: 40px;
  color: var(--text-muted);
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  max-width: 360px;
  margin: 0;
}

.btn-reset-filters {
  margin-top: 10px;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.spin-icon {
  animation: spin 1s infinite linear;
  font-size: 28px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

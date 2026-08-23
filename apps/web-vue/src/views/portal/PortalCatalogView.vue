<template>
  <div class="portal-catalog-page" :dir="dir">
    <div class="portal-container">
      <!-- Page Header -->
      <div class="page-header-row">
        <div>
          <h1 class="page-title">{{ t('portal-catalog-title', 'Order Supplies & Replenishment') }}</h1>
          <p class="page-subtitle">{{ t('portal-catalog-subtitle', 'Browse wholesale catalog with your contracted pricing and stock availability.') }}</p>
        </div>
        <div class="header-actions">
          <router-link to="/portal/cart" class="btn-checkout-link" :class="{ 'btn-highlight': portal.cartItemCount > 0 }">
            <span class="material-symbols-outlined">shopping_bag</span>
            <span>{{ t('portal-view-cart', 'View Cart') }} ({{ portal.cartItemCount }})</span>
            <span class="subtotal-pill">${{ portal.cartSubtotal.toFixed(2) }}</span>
          </router-link>
        </div>
      </div>

      <!-- Cutoff & Minimum Order Notification Banners -->
      <div class="notifications-grid">
        <!-- Live Cutoff Time Countdown Banner -->
        <div class="banner-card cutoff-banner" :class="{ 'past-cutoff': portal.isPastCutoff }">
          <div class="banner-icon-col">
            <span class="material-symbols-outlined">
              {{ portal.isPastCutoff ? 'warning' : 'schedule' }}
            </span>
          </div>
          <div class="banner-content">
            <div class="banner-title-row">
              <span class="banner-heading">
                {{ portal.isPastCutoff ? t('cutoff-past-heading', 'Order Cutoff Passed for Next-Day Delivery') : t('cutoff-active-heading', 'Order Cutoff Countdown') }}
              </span>
              <span class="badge" :class="portal.isPastCutoff ? 'badge-amber' : 'badge-green'">
                {{ portal.cutoffStatus?.schedule_rule || (portal.isPastCutoff ? 'D+2 Delivery' : 'D+1 Next-Day') }}
              </span>
            </div>
            <p class="banner-desc">
              <span v-if="!portal.isPastCutoff && countdownText">
                {{ t('order-within', 'Order within') }} <strong>{{ countdownText }}</strong> {{ t('for-delivery-on', 'for next-day delivery on') }} <strong>{{ portal.nextDeliveryDate }}</strong>.
              </span>
              <span v-else-if="portal.isPastCutoff">
                {{ t('past-cutoff-desc', 'The daily order cutoff has passed. Orders placed now will be scheduled for delivery on') }} <strong>{{ portal.nextDeliveryDate }}</strong>.
              </span>
              <span v-else>
                {{ portal.cutoffStatus?.message || t('cutoff-standard', 'Daily cutoff applies for wholesale fulfillment.') }}
              </span>
            </p>
          </div>
          <div class="banner-extra" v-if="portal.cutoffStatus?.cutoff_time">
            <span class="extra-label">{{ t('daily-cutoff', 'Daily Cutoff') }}</span>
            <span class="extra-value">{{ portal.cutoffStatus.cutoff_time.slice(0, 5) }}</span>
          </div>
        </div>

        <!-- Minimum Order Progress Banner -->
        <div class="banner-card min-order-banner" v-if="portal.minOrderAmount > 0">
          <div class="banner-icon-col">
            <span class="material-symbols-outlined" :class="{ 'icon-green': portal.meetsMinOrder }">
              {{ portal.meetsMinOrder ? 'check_circle' : 'trending_up' }}
            </span>
          </div>
          <div class="banner-content">
            <div class="banner-title-row">
              <span class="banner-heading">{{ t('min-order-heading', 'Minimum Order Requirement') }}</span>
              <span class="badge" :class="portal.meetsMinOrder ? 'badge-green' : 'badge-blue'">
                ${{ portal.cartSubtotal.toFixed(2) }} / ${{ portal.minOrderAmount.toFixed(2) }}
              </span>
            </div>
            <!-- Progress Bar -->
            <div class="progress-bar-track">
              <div
                class="progress-bar-fill"
                :class="{ 'fill-complete': portal.meetsMinOrder }"
                :style="{ width: `${portal.minOrderProgress}%` }"
              ></div>
            </div>
            <p class="banner-desc">
              <span v-if="portal.meetsMinOrder" class="text-success font-medium">
                {{ t('min-order-met', 'Minimum order amount met! Your order is ready for checkout.') }}
              </span>
              <span v-else>
                {{ t('min-order-shortfall', 'Add') }} <strong>${{ portal.minOrderShortfall.toFixed(2) }}</strong> {{ t('more-to-meet-min', 'more to meet the minimum order threshold of') }} ${{ portal.minOrderAmount.toFixed(2) }}.
              </span>
            </p>
          </div>
        </div>
      </div>

      <!-- Filters, Search & Categories Bar -->
      <div class="catalog-controls-card">
        <div class="controls-top-row">
          <!-- Search Box -->
          <div class="search-field-wrap">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              v-model="searchQuery"
              @input="handleSearchInput"
              type="text"
              class="search-input"
              :placeholder="t('search-catalog-placeholder', 'Search products by name, SKU, or barcode...')"
            />
            <button v-if="searchQuery" class="clear-search-btn" @click="clearSearch" title="Clear search">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Controls Right (In-Stock Toggle & View Switcher) -->
          <div class="controls-right-actions">
            <label class="toggle-control">
              <input
                type="checkbox"
                v-model="inStockOnly"
                @change="handleFilterChange"
              />
              <span class="toggle-label">{{ t('in-stock-only', 'In Stock Only') }}</span>
            </label>

            <div class="view-mode-toggle">
              <button
                class="view-btn"
                :class="{ active: viewMode === 'grid' }"
                @click="viewMode = 'grid'"
                title="Grid view"
              >
                <span class="material-symbols-outlined">grid_view</span>
              </button>
              <button
                class="view-btn"
                :class="{ active: viewMode === 'table' }"
                @click="viewMode = 'table'"
                title="Table list view"
              >
                <span class="material-symbols-outlined">view_list</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Category Pills Navigation -->
        <div class="category-pills-bar" v-if="portal.categories && portal.categories.length">
          <button
            class="cat-pill"
            :class="{ active: selectedCategory === null || selectedCategory === '' }"
            @click="selectCategory(null)"
          >
            <span class="cat-name">{{ t('all-items', 'All Products') }}</span>
            <span class="cat-count">{{ portal.catalogTotal }}</span>
          </button>
          <button
            v-for="cat in portal.categories"
            :key="cat.id"
            class="cat-pill"
            :class="{ active: selectedCategory === cat.id }"
            @click="selectCategory(cat.id)"
          >
            <span class="cat-name">{{ cat.name }}</span>
            <span class="cat-count">{{ cat.product_count }}</span>
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portal.catalogLoading" class="catalog-loading-grid">
        <div v-for="i in 8" :key="i" class="product-skeleton-card">
          <div class="skeleton-shimmer skeleton-img"></div>
          <div class="skeleton-body">
            <div class="skeleton-shimmer skeleton-line w-60"></div>
            <div class="skeleton-shimmer skeleton-line w-80"></div>
            <div class="skeleton-shimmer skeleton-line w-40"></div>
          </div>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="portal.catalogError" class="catalog-error-state">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('catalog-error-title', 'Unable to Load Catalog') }}</h3>
        <p>{{ portal.catalogError }}</p>
        <button class="btn-primary" @click="retryLoad">
          <span class="material-symbols-outlined">refresh</span>
          {{ t('retry', 'Retry') }}
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="!portal.catalog || portal.catalog.length === 0" class="catalog-empty-state">
        <div class="empty-icon-wrap">
          <span class="material-symbols-outlined">inventory_2</span>
        </div>
        <h3>{{ t('no-products-found', 'No Products Found') }}</h3>
        <p>{{ t('no-products-desc', 'Try clearing your search filters or selecting a different category.') }}</p>
        <button class="btn-outline" @click="resetFilters">
          <span class="material-symbols-outlined">restart_alt</span>
          {{ t('reset-filters', 'Reset Filters') }}
        </button>
      </div>

      <!-- Products Grid View -->
      <div v-else-if="viewMode === 'grid'" class="catalog-products-grid">
        <div
          v-for="item in portal.catalog"
          :key="item.id"
          class="product-item-card"
          :class="{ 'is-contracted-item': item.is_contracted, 'out-of-stock': !item.is_in_stock }"
        >
          <!-- Contracted Badge -->
          <div class="contracted-badge-top" v-if="item.is_contracted">
            <span class="material-symbols-outlined">verified</span>
            <span>{{ t('contracted-price-badge', 'Contracted Price') }}</span>
            <span v-if="item.discount_percent > 0" class="discount-pill">-{{ Math.round(item.discount_percent) }}%</span>
          </div>

          <!-- Product Card Header / Visual -->
          <div class="product-visual-area">
            <div class="product-icon-avatar">
              <span class="material-symbols-outlined">package_2</span>
            </div>
            <div class="stock-status-pill" :class="item.is_in_stock ? 'stock-in' : 'stock-out'">
              <span class="stock-dot"></span>
              <span>{{ item.is_in_stock ? (item.stock_qty > 0 ? `${item.stock_qty} ${item.uom_name || 'in stock'}` : 'In Stock') : 'Out of Stock' }}</span>
            </div>
          </div>

          <!-- Product Info -->
          <div class="product-details">
            <div class="product-meta-row">
              <span class="sku-tag">{{ item.product_code }}</span>
              <span class="category-tag" v-if="item.category_name">{{ item.category_name }}</span>
            </div>
            <h3 class="product-title" :title="item.product_name">{{ item.product_name }}</h3>
            <p class="product-description" v-if="item.description">{{ item.description }}</p>
          </div>

          <!-- Pricing Area -->
          <div class="product-price-section">
            <div class="price-stack">
              <div class="active-price">
                <span class="currency-symbol">$</span>
                <span class="price-number">{{ item.contracted_price.toFixed(2) }}</span>
                <span class="uom-suffix" v-if="item.uom_name">/ {{ item.uom_name }}</span>
              </div>
              <div class="regular-price-struck" v-if="item.is_contracted && item.base_price > item.contracted_price">
                <span class="strikethrough-label">Regular:</span>
                <span class="struck-price">${{ item.base_price.toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- Fast Quantity Stepper & Add Action -->
          <div class="product-cart-controls">
            <!-- If Item Already in Cart -->
            <div v-if="getCartQty(item.id) > 0" class="qty-stepper-container">
              <button
                class="stepper-btn btn-decrement"
                @click="decrementQty(item)"
                aria-label="Decrease quantity"
              >
                <span class="material-symbols-outlined">remove</span>
              </button>
              <input
                type="number"
                min="0"
                class="stepper-input"
                :value="getCartQty(item.id)"
                @change="handleQtyChange(item, $event.target.value)"
                aria-label="Quantity in cart"
              />
              <button
                class="stepper-btn btn-increment"
                @click="incrementQty(item)"
                aria-label="Increase quantity"
              >
                <span class="material-symbols-outlined">add</span>
              </button>
            </div>

            <!-- If Not in Cart -->
            <button
              v-else
              class="btn-add-to-cart"
              :disabled="!item.is_in_stock"
              @click="quickAddToCart(item)"
            >
              <span class="material-symbols-outlined">add_shopping_cart</span>
              <span>{{ t('add-to-cart', 'Add to Cart') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Products Table View -->
      <div v-else class="catalog-table-container">
        <div class="table-card">
          <table class="catalog-table">
            <thead>
              <tr>
                <th>{{ t('sku-code', 'SKU / Code') }}</th>
                <th>{{ t('product-name', 'Product Name') }}</th>
                <th>{{ t('category', 'Category') }}</th>
                <th>{{ t('uom', 'UOM') }}</th>
                <th>{{ t('stock-status', 'Stock Status') }}</th>
                <th class="text-right">{{ t('unit-price', 'Unit Price') }}</th>
                <th class="text-center">{{ t('quantity', 'Quantity & Action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in portal.catalog"
                :key="item.id"
                :class="{ 'row-contracted': item.is_contracted }"
              >
                <td class="cell-sku font-mono">{{ item.product_code }}</td>
                <td class="cell-name">
                  <div class="product-name-block">
                    <span class="name-text">{{ item.product_name }}</span>
                    <span v-if="item.is_contracted" class="contract-badge-inline">
                      <span class="material-symbols-outlined">verified</span> Contracted
                    </span>
                  </div>
                </td>
                <td class="cell-category">{{ item.category_name || '-' }}</td>
                <td class="cell-uom"><span class="uom-pill">{{ item.uom_name || 'Ea' }}</span></td>
                <td>
                  <span class="stock-pill" :class="item.is_in_stock ? 'stock-in' : 'stock-out'">
                    {{ item.is_in_stock ? (item.stock_qty > 0 ? `${item.stock_qty} in stock` : 'In Stock') : 'Out of Stock' }}
                  </span>
                </td>
                <td class="cell-price text-right">
                  <div class="table-price-stack">
                    <span class="table-main-price">${{ item.contracted_price.toFixed(2) }}</span>
                    <span v-if="item.is_contracted && item.base_price > item.contracted_price" class="table-struck-price">
                      ${{ item.base_price.toFixed(2) }}
                    </span>
                  </div>
                </td>
                <td class="cell-actions text-center">
                  <div class="table-qty-controls">
                    <div v-if="getCartQty(item.id) > 0" class="table-stepper">
                      <button class="step-btn" @click="decrementQty(item)">−</button>
                      <input
                        type="number"
                        min="0"
                        class="step-input"
                        :value="getCartQty(item.id)"
                        @change="handleQtyChange(item, $event.target.value)"
                      />
                      <button class="step-btn" @click="incrementQty(item)">+</button>
                    </div>
                    <button
                      v-else
                      class="btn-table-add"
                      :disabled="!item.is_in_stock"
                      @click="quickAddToCart(item)"
                    >
                      <span class="material-symbols-outlined">add</span>
                      {{ t('add', 'Add') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pagination Footer -->
      <div class="pagination-bar" v-if="portal.catalogTotal > portal.catalogLimit">
        <span class="pagination-info">
          {{ t('showing-items', 'Showing') }} {{ ((portal.catalogPage - 1) * portal.catalogLimit) + 1 }} -
          {{ Math.min(portal.catalogPage * portal.catalogLimit, portal.catalogTotal) }} {{ t('of', 'of') }} {{ portal.catalogTotal }}
        </span>
        <div class="pagination-buttons">
          <button
            class="page-nav-btn"
            :disabled="portal.catalogPage <= 1"
            @click="changePage(portal.catalogPage - 1)"
          >
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <span class="current-page-num">{{ portal.catalogPage }}</span>
          <button
            class="page-nav-btn"
            :disabled="portal.catalogPage * portal.catalogLimit >= portal.catalogTotal"
            @click="changePage(portal.catalogPage + 1)"
          >
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Sticky Floating Replenishment Checkout Summary Bar -->
    <div class="sticky-cart-bar" v-if="portal.cartItemCount > 0">
      <div class="sticky-cart-inner">
        <div class="sticky-cart-left">
          <div class="cart-items-counter">
            <span class="material-symbols-outlined">shopping_bag</span>
            <span class="items-count-text">{{ portal.cartItemCount }} {{ portal.cartItemCount === 1 ? 'item' : 'items' }} in Cart</span>
          </div>
          <div class="cart-subtotal-counter">
            <span class="subtotal-label">{{ t('subtotal', 'Subtotal') }}:</span>
            <span class="subtotal-value">${{ portal.cartSubtotal.toFixed(2) }}</span>
          </div>
          <div class="min-order-status-badge" :class="portal.meetsMinOrder ? 'status-met' : 'status-shortfall'">
            <span class="material-symbols-outlined">{{ portal.meetsMinOrder ? 'check_circle' : 'info' }}</span>
            <span>{{ portal.meetsMinOrder ? 'Min order met' : `$${portal.minOrderShortfall.toFixed(2)} to minimum` }}</span>
          </div>
        </div>

        <div class="sticky-cart-right">
          <router-link to="/portal/cart" class="btn-primary-checkout">
            <span>{{ t('review-and-checkout', 'Review Cart & Checkout') }}</span>
            <span class="material-symbols-outlined">arrow_forward</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePortalStore } from '../../stores/portal.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const portal = usePortalStore()
const { show: showToast } = useToast()
const { t, dir } = useI18n()

const searchQuery = ref('')
const selectedCategory = ref(null)
const inStockOnly = ref(false)
const viewMode = ref('grid')
const searchTimeout = ref(null)
const countdownText = ref('')
let countdownTimer = null

// Real-time Cutoff Countdown Calculation
function updateCountdown() {
  if (!portal.cutoffStatus?.cutoff_time) {
    countdownText.value = ''
    return
  }

  const now = new Date()
  const cutoffParts = portal.cutoffStatus.cutoff_time.split(':')
  const cutoffHours = parseInt(cutoffParts[0], 10) || 22
  const cutoffMins = parseInt(cutoffParts[1], 10) || 0

  const cutoffDate = new Date()
  cutoffDate.setHours(cutoffHours, cutoffMins, 0, 0)

  const diffMs = cutoffDate.getTime() - now.getTime()
  if (diffMs <= 0) {
    countdownText.value = ''
    return
  }

  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)

  if (hours > 0) {
    countdownText.value = `${hours}h ${minutes}m`
  } else {
    countdownText.value = `${minutes}m ${seconds}s`
  }
}

function handleSearchInput() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    portal.fetchCatalog({
      search: searchQuery.value,
      categoryId: selectedCategory.value,
      inStockOnly: inStockOnly.value,
      page: 1,
    })
  }, 350)
}

function clearSearch() {
  searchQuery.value = ''
  portal.fetchCatalog({
    search: '',
    categoryId: selectedCategory.value,
    inStockOnly: inStockOnly.value,
    page: 1,
  })
}

function selectCategory(catId) {
  selectedCategory.value = catId
  portal.fetchCatalog({
    search: searchQuery.value,
    categoryId: catId,
    inStockOnly: inStockOnly.value,
    page: 1,
  })
}

function handleFilterChange() {
  portal.fetchCatalog({
    search: searchQuery.value,
    categoryId: selectedCategory.value,
    inStockOnly: inStockOnly.value,
    page: 1,
  })
}

function resetFilters() {
  searchQuery.value = ''
  selectedCategory.value = null
  inStockOnly.value = false
  portal.fetchCatalog({ search: '', categoryId: null, inStockOnly: false, page: 1 })
}

function changePage(page) {
  portal.fetchCatalog({
    page,
    search: searchQuery.value,
    categoryId: selectedCategory.value,
    inStockOnly: inStockOnly.value,
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function retryLoad() {
  portal.fetchCatalog({ page: 1 })
  portal.fetchAccountSummary()
  portal.fetchCutoffStatus()
}

// Cart Quantity Stepper Helpers
function getCartQty(productId) {
  const item = portal.cart.find(i => i.product_id === productId)
  return item ? Number(item.qty || 0) : 0
}

function quickAddToCart(product) {
  portal.addToCart(product, 1)
  showToast(`Added ${product.product_name} to cart`, 'success', 2000)
}

function incrementQty(product) {
  const current = getCartQty(product.id)
  portal.addToCart(product, 1)
}

function decrementQty(product) {
  const current = getCartQty(product.id)
  if (current <= 1) {
    portal.removeFromCart(product.id)
  } else {
    portal.updateCartQty(product.id, current - 1)
  }
}

function handleQtyChange(product, newQty) {
  const parsed = parseInt(newQty, 10)
  if (isNaN(parsed) || parsed <= 0) {
    portal.removeFromCart(product.id)
  } else {
    portal.updateCartQty(product.id, parsed)
  }
}

onMounted(async () => {
  await Promise.all([
    portal.fetchCatalog(),
    portal.fetchAccountSummary(),
    portal.fetchCutoffStatus(),
  ])
  updateCountdown()
  countdownTimer = setInterval(updateCountdown, 1000)
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
})
</script>

<style scoped>
.portal-catalog-page {
  width: 100%;
}

.portal-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  letter-spacing: -0.4px;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #94a3b8);
}

.btn-checkout-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-checkout-link:hover {
  background: var(--bg-surface-hover, #2a2a4a);
  border-color: #6366f1;
}

.btn-checkout-link.btn-highlight {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-color: #6366f1;
  color: #fff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.subtotal-pill {
  background: rgba(0, 0, 0, 0.25);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}

/* Notification Banners Grid */
.notifications-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 900px) {
  .notifications-grid {
    grid-template-columns: 1fr;
  }
}

.banner-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 12px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
}

.cutoff-banner {
  border-left: 4px solid #22c55e;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.05) 0%, var(--bg-surface, #1a1a2e) 100%);
}

.cutoff-banner.past-cutoff {
  border-left-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, var(--bg-surface, #1a1a2e) 100%);
}

.min-order-banner {
  border-left: 4px solid #6366f1;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, var(--bg-surface, #1a1a2e) 100%);
}

.banner-icon-col {
  padding-top: 2px;
}

.banner-icon-col .material-symbols-outlined {
  font-size: 26px;
  color: #22c55e;
}

.past-cutoff .banner-icon-col .material-symbols-outlined {
  color: #f59e0b;
}

.icon-green {
  color: #22c55e !important;
}

.banner-content {
  flex: 1;
}

.banner-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.banner-heading {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.banner-desc {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
  margin: 0;
}

.banner-extra {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  padding-left: 12px;
  border-left: 1px solid var(--border-default, #2a2a4a);
}

.extra-label {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.5px;
}

.extra-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #fff);
  font-family: monospace;
}

.progress-bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin: 8px 0;
}

.progress-bar-fill {
  height: 100%;
  background: #6366f1;
  transition: width 0.3s ease;
}

.progress-bar-fill.fill-complete {
  background: #22c55e;
}

/* Badges */
.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.badge-green {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-amber {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-blue {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

/* Controls Card */
.catalog-controls-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}

.controls-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.search-field-wrap {
  flex: 1;
  min-width: 260px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 20px;
  color: var(--text-muted, #64748b);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 10px 38px 10px 40px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: #6366f1;
}

.clear-search-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.clear-search-btn .material-symbols-outlined {
  font-size: 18px;
}

.controls-right-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
  user-select: none;
}

.toggle-control input[type="checkbox"] {
  accent-color: #6366f1;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.view-mode-toggle {
  display: inline-flex;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-input, #3a3a5a);
  border-radius: 8px;
  padding: 2px;
}

.view-btn {
  background: none;
  border: none;
  color: var(--text-muted, #64748b);
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
}

.view-btn.active {
  background: var(--bg-surface, #1a1a2e);
  color: #a5b4fc;
}

.view-btn .material-symbols-outlined {
  font-size: 18px;
}

/* Category Pills */
.category-pills-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-top: 14px;
  margin-top: 12px;
  border-top: 1px solid var(--border-default, #2a2a4a);
}

.cat-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.cat-pill:hover {
  background: var(--bg-surface-hover, #2a2a4a);
  color: var(--text-primary, #fff);
}

.cat-pill.active {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

.cat-count {
  background: rgba(255, 255, 255, 0.15);
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
}

/* Catalog Grid View */
.catalog-products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.product-item-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.product-item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  border-color: rgba(99, 102, 241, 0.4);
}

.product-item-card.is-contracted-item {
  border-color: rgba(99, 102, 241, 0.35);
}

.contracted-badge-top {
  position: absolute;
  top: -10px;
  left: 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.3);
}

.contracted-badge-top .material-symbols-outlined {
  font-size: 12px;
}

.discount-pill {
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 4px;
  border-radius: 6px;
  font-size: 9px;
}

.product-visual-area {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  margin-bottom: 12px;
}

.product-icon-avatar {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--bg-surface-low, #222240);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a5b4fc;
}

.product-icon-avatar .material-symbols-outlined {
  font-size: 24px;
}

.stock-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.stock-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.stock-in {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
}

.stock-in .stock-dot {
  background: #22c55e;
}

.stock-out {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

.stock-out .stock-dot {
  background: #ef4444;
}

.product-details {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.product-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.sku-tag {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted, #64748b);
  background: rgba(255, 255, 255, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
}

.category-tag {
  font-size: 11px;
  color: #a5b4fc;
}

.product-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  line-height: 1.3;
  margin-bottom: 4px;
}

.product-description {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  line-height: 1.4;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-price-section {
  padding: 10px 0;
  border-top: 1px dashed var(--border-default, #2a2a4a);
  margin-top: auto;
  margin-bottom: 12px;
}

.price-stack {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.active-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.currency-symbol {
  font-size: 14px;
  font-weight: 600;
  color: #a5b4fc;
}

.price-number {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.uom-suffix {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  margin-left: 2px;
}

.regular-price-struck {
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.struck-price {
  text-decoration: line-through;
  margin-left: 2px;
}

.product-cart-controls {
  width: 100%;
}

.btn-add-to-cart {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-to-cart:hover:not(:disabled) {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.btn-add-to-cart:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.qty-stepper-container {
  display: flex;
  align-items: center;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid #6366f1;
  border-radius: 8px;
  overflow: hidden;
}

.stepper-btn {
  background: none;
  border: none;
  color: #a5b4fc;
  width: 38px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}

.stepper-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  color: #fff;
}

.stepper-input {
  flex: 1;
  text-align: center;
  background: none;
  border: none;
  color: var(--text-primary, #fff);
  font-size: 14px;
  font-weight: 700;
  outline: none;
  width: 50px;
}

/* Table View */
.catalog-table-container {
  margin-bottom: 40px;
}

.table-card {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  border-radius: 12px;
  overflow-x: auto;
}

.catalog-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.catalog-table th {
  text-align: left;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  color: var(--text-secondary, #94a3b8);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
}

.catalog-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
}

.catalog-table tr:hover td {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.02));
}

.row-contracted td {
  background: rgba(99, 102, 241, 0.02);
}

.cell-sku {
  color: var(--text-muted, #94a3b8);
  font-size: 12px;
}

.product-name-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-text {
  font-weight: 600;
}

.contract-badge-inline {
  font-size: 10px;
  font-weight: 700;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  padding: 2px 6px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.contract-badge-inline .material-symbols-outlined {
  font-size: 11px;
}

.uom-pill {
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.stock-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.table-price-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.table-main-price {
  font-weight: 700;
  font-size: 14px;
}

.table-struck-price {
  font-size: 11px;
  text-decoration: line-through;
  color: var(--text-muted, #64748b);
}

.table-qty-controls {
  display: flex;
  justify-content: center;
}

.table-stepper {
  display: inline-flex;
  align-items: center;
  background: var(--bg-body, #0f0f1a);
  border: 1px solid #6366f1;
  border-radius: 6px;
}

.step-btn {
  background: none;
  border: none;
  color: #a5b4fc;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-weight: bold;
}

.step-input {
  width: 36px;
  text-align: center;
  background: none;
  border: none;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
}

.btn-table-add {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-table-add:hover:not(:disabled) {
  background: #6366f1;
  color: #fff;
}

/* Pagination */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding: 12px 0;
}

.pagination-info {
  font-size: 13px;
  color: var(--text-muted, #94a3b8);
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-nav-btn {
  background: var(--bg-surface, #1a1a2e);
  border: 1px solid var(--border-default, #2a2a4a);
  color: var(--text-primary, #fff);
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.page-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.current-page-num {
  font-size: 13px;
  font-weight: 700;
  padding: 0 8px;
}

/* Skeleton Loading */
.catalog-loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.product-skeleton-card {
  background: var(--bg-surface, #1a1a2e);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-default, #2a2a4a);
}

.skeleton-img {
  height: 120px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.skeleton-shimmer {
  background: linear-gradient(90deg, #222240 25%, #2e2e54 50%, #222240 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.w-60 { width: 60%; }
.w-80 { width: 80%; }
.w-40 { width: 40%; }

/* Error & Empty States */
.catalog-error-state, .catalog-empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--bg-surface, #1a1a2e);
  border: 1px dashed var(--border-default, #2a2a4a);
  border-radius: 12px;
  margin-bottom: 30px;
}

.error-icon {
  font-size: 48px;
  color: #ef4444;
  margin-bottom: 12px;
}

.empty-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--bg-surface-low, #222240);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #94a3b8);
  margin-bottom: 16px;
}

.empty-icon-wrap .material-symbols-outlined {
  font-size: 32px;
}

/* Sticky Cart Bar */
.sticky-cart-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(26, 26, 46, 0.95);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(99, 102, 241, 0.3);
  padding: 14px 24px;
  z-index: 90;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
}

.sticky-cart-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.sticky-cart-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.cart-items-counter {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #a5b4fc;
}

.cart-subtotal-counter {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.subtotal-label {
  font-size: 13px;
  color: var(--text-secondary, #94a3b8);
}

.subtotal-value {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.min-order-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.min-order-status-badge.status-met {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.min-order-status-badge.status-shortfall {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.btn-primary-checkout {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  padding: 10px 22px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  transition: all 0.2s ease;
}

.btn-primary-checkout:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.6);
}
</style>

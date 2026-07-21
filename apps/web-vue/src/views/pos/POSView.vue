<template>
  <div class="pos-shell" :dir="dir">
    <div class="pos-grid">
      <div class="pos-toolbar">
        <div class="search-box">
          <span class="material-symbols-outlined">search</span>
          <input v-model="searchQuery" placeholder="Search products, SKUs..." />
        </div>
        <div class="category-pills" v-if="categories.length">
          <button :class="['pill', { active: !activeCategory }]" @click="activeCategory = ''">All</button>
          <button v-for="cat in categories" :key="cat" :class="['pill', { active: activeCategory === cat }]" @click="activeCategory = cat">{{ cat }}</button>
        </div>
      </div>
      <div class="product-grid">
        <div v-if="loading" class="grid-feedback">Loading products…</div>
        <div v-else-if="error" class="grid-feedback error">{{ error }}</div>
        <template v-else>
          <div v-for="p in filteredProducts" :key="p.id" class="product-card" @click="addToCart(p)">
            <div class="product-icon">
              <span class="material-symbols-outlined">inventory_2</span>
            </div>
            <div class="product-body">
              <div class="product-name">{{ p.name }}</div>
              <div class="product-sku">{{ p.sku }}</div>
              <div class="product-price">{{ formatMoney(p.price) }}</div>
            </div>
            <button class="product-add" @click.stop="addToCart(p)">
              <span class="material-symbols-outlined">add</span>
            </button>
          </div>
          <div v-if="!filteredProducts.length" class="grid-feedback empty">No products found</div>
        </template>
      </div>
    </div>

    <div class="pos-cart">
      <div class="cart-header">
        <div class="cart-header-left">
          <span class="material-symbols-outlined">shopping_basket</span>
          <span class="cart-header-title">Cart</span>
          <span class="cart-badge">{{ cart.length }}</span>
        </div>
        <button class="cart-clear" @click="clearCart">Clear</button>
      </div>

      <div class="cart-customer" v-if="!checkingOut">
        <span class="material-symbols-outlined">person</span>
        <input v-model="customerName" placeholder="Walk-in Customer" class="customer-input" />
      </div>

      <div class="cart-items" :class="{ 'checking-out': checkingOut }">
        <div v-if="!cart.length" class="cart-empty">Cart is empty</div>
        <div v-for="(item, idx) in cart" :key="item.productId" class="cart-item">
          <div class="cart-item-row">
            <span class="item-qty">{{ pad(item.qty, 2) }} ×</span>
            <span class="item-name">{{ item.name }}</span>
            <span class="item-amount">{{ formatMoney(item.qty * item.price) }}</span>
          </div>
          <div class="cart-stepper">
            <button class="step-btn" @click="decrement(idx)">−</button>
            <span class="step-value">{{ pad(item.qty, 2) }}</span>
            <button class="step-btn" @click="addToCart(findProduct(item.productId))">+</button>
          </div>
        </div>
      </div>

      <div class="cart-footer">
        <div class="total-line">
          <span class="total-label">Subtotal</span>
          <span class="mono-amount">{{ formatMoney(subtotal) }}</span>
        </div>
        <div class="total-line">
          <span class="total-label">Tax (5%)</span>
          <span class="mono-amount">{{ formatMoney(tax) }}</span>
        </div>
        <div class="total-line grand">
          <span class="total-label">Total</span>
          <span class="grand-amount" :class="{ pop: totalPop }">{{ formatMoney(grandTotal) }}</span>
        </div>
        <div class="cart-actions">
          <button class="action-hold" :disabled="checkingOut">Hold</button>
          <button class="action-pay" :disabled="!cart.length || checkingOut" @click="checkout">
            {{ checkingOut ? 'Processing…' : 'Pay ' + formatMoney(grandTotal) }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const { show: toast } = useToast()
const { dir } = useI18n()

const products = ref([])
const cart = ref([])
const searchQuery = ref('')
const activeCategory = ref('')
const customerName = ref('')
const loading = ref(true)
const error = ref('')
const checkingOut = ref(false)
const totalPop = ref(false)

const categories = computed(() => {
  const cats = new Set(products.value.map(p => p.category).filter(Boolean))
  return [...cats].sort()
})

const filteredProducts = computed(() => {
  let list = products.value
  if (activeCategory.value) {
    list = list.filter(p => p.category === activeCategory.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      (p.sku && p.sku.toLowerCase().includes(q))
    )
  }
  return list
})

const subtotal = computed(() => {
  return cart.value.reduce((s, i) => s + i.qty * i.price, 0)
})
const tax = computed(() => subtotal.value * 0.05)
const grandTotal = computed(() => subtotal.value + tax.value)

const productMap = computed(() => {
  const map = {}
  for (const p of products.value) {
    map[p.id] = p
  }
  return map
})

function findProduct(id) {
  return productMap.value[id]
}

function formatMoney(n) {
  return '$' + (n || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function pad(n, len) {
  return String(Math.round(n)).padStart(len, '0')
}

function addToCart(product) {
  if (!product) return
  const existing = cart.value.find(c => c.productId === product.id)
  if (existing) {
    existing.qty++
    cart.value = [...cart.value]
  } else {
    cart.value = [...cart.value, { productId: product.id, name: product.name, price: product.price, qty: 1 }]
  }
}

function decrement(idx) {
  const item = cart.value[idx]
  if (!item) return
  if (item.qty > 1) {
    item.qty--
    cart.value = [...cart.value]
  } else {
    cart.value = cart.value.filter((_, i) => i !== idx)
  }
}

function clearCart() {
  cart.value = []
}

watch(grandTotal, () => {
  totalPop.value = true
  setTimeout(() => { totalPop.value = false }, 250)
})

async function checkout() {
  if (!cart.value.length) return
  checkingOut.value = true
  try {
    const payload = {
      cart_items: cart.value.map(i => ({
        product_id: i.productId,
        product_name: i.name,
        qty: i.qty,
        unit_price: i.price,
      })),
      customer_name: customerName.value || 'Walk-in Customer',
    }
    const res = await api.post('/pos/checkout', payload)
    const data = res.data
    toast(data.message || 'Sale completed!', 'success')
    cart.value = []
    customerName.value = ''
  } catch (e) {
    const detail = e.response?.data?.detail || e.message || 'Checkout failed'
    toast(detail, 'error')
  } finally {
    checkingOut.value = false
  }
}

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0003I/')
    products.value = res.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to load products'
  } finally {
    loading.value = false
  }
}

onMounted(loadProducts)
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
</style>

<style scoped>
.pos-shell {
  display: flex;
  height: 100%;
  overflow: hidden;
  font-family: 'DM Sans', system-ui, sans-serif;
  background: #fff;
  border-radius: 0;
  margin: -24px;
  min-height: calc(100vh - 64px);
}
@media (max-width: 900px) {
  .pos-shell { flex-direction: column; }
}

/* ── Grid Panel ── */
.pos-grid {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f7f6f3;
  overflow: hidden;
}
.pos-toolbar {
  padding: 16px 20px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0 14px;
  max-width: 400px;
}
.search-box .material-symbols-outlined {
  font-size: 20px;
  color: #9ca3af;
}
.search-box input {
  border: none;
  outline: none;
  flex: 1;
  padding: 10px 0;
  font-size: 14px;
  font-family: inherit;
  background: transparent;
  color: #111827;
}
.search-box input::placeholder { color: #9ca3af; }

.category-pills {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.pill {
  padding: 5px 14px;
  border-radius: 20px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  font-family: inherit;
}
.pill:hover { border-color: #059669; color: #059669; }
.pill.active { background: #059669; color: #fff; border-color: #059669; }

.product-grid {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 10px;
  align-content: start;
}
.product-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  position: relative;
}
.product-card:hover {
  border-color: #059669;
  box-shadow: 0 0 0 1px #05966933;
}
.product-icon {
  aspect-ratio: 1;
  background: #f3f4f6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.product-icon .material-symbols-outlined {
  font-size: 32px;
  color: #9ca3af;
}
.product-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.product-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.product-sku {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: #9ca3af;
  letter-spacing: 0.3px;
}
.product-price {
  font-family: 'DM Mono', monospace;
  font-size: 16px;
  font-weight: 500;
  color: #059669;
  margin-top: 6px;
}
.product-add {
  position: absolute;
  bottom: 14px;
  right: 14px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  opacity: 0;
}
.product-card:hover .product-add { opacity: 1; }
.product-add:hover { background: #059669; color: #fff; }
.product-add .material-symbols-outlined { font-size: 18px; }

.grid-feedback {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 20px;
  color: #9ca3af;
  font-size: 14px;
}
.grid-feedback.error { color: #dc2626; }

/* ── Cart Panel ── */
.pos-cart {
  width: 380px;
  flex-shrink: 0;
  background: #fff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (max-width: 900px) {
  .pos-cart { width: 100%; border-left: none; border-top: 1px solid #e5e7eb; }
}

.cart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
  flex-shrink: 0;
}
.cart-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cart-header-left .material-symbols-outlined { color: #059669; font-size: 20px; }
.cart-header-title { font-size: 15px; font-weight: 600; color: #111827; }
.cart-badge {
  background: #059669;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  font-family: 'DM Mono', monospace;
}
.cart-clear {
  border: none;
  background: none;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}
.cart-clear:hover { background: #fef2f2; }

.cart-customer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-bottom: 1px solid #f3f4f6;
  background: #fafafa;
  flex-shrink: 0;
}
.cart-customer .material-symbols-outlined { color: #9ca3af; font-size: 18px; }
.customer-input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  font-family: inherit;
  background: transparent;
  padding: 2px 0;
}
.customer-input::placeholder { color: #9ca3af; font-weight: 400; }

.cart-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 18px;
}
.cart-items.checking-out { opacity: 0.5; pointer-events: none; }
.cart-empty {
  text-align: center;
  padding: 48px 0;
  color: #9ca3af;
  font-size: 13px;
  font-family: 'DM Mono', monospace;
}
.cart-item {
  padding: 10px 0;
  border-bottom: 1px solid #f3f4f6;
}
.cart-item:last-child { border-bottom: none; }
.cart-item-row {
  display: flex;
  gap: 6px;
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  color: #111827;
  margin-bottom: 6px;
}
.item-qty { color: #059669; font-weight: 500; flex-shrink: 0; }
.item-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-amount { flex-shrink: 0; font-weight: 500; }

.cart-stepper {
  display: flex;
  align-items: center;
  gap: 4px;
}
.step-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #d97706;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  font-family: inherit;
  line-height: 1;
}
.step-btn:hover { background: #d97706; color: #fff; border-color: #d97706; }
.step-value {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  color: #111827;
  min-width: 24px;
  text-align: center;
}

.cart-footer {
  border-top: 2px solid #e5e7eb;
  padding: 14px 18px 18px;
  flex-shrink: 0;
  background: #fafafa;
}
.total-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
}
.total-label { font-size: 13px; color: #6b7280; }
.mono-amount {
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  color: #111827;
}
.total-line.grand {
  padding: 8px 0 12px;
  border-top: 1px solid #e5e7eb;
  margin-top: 6px;
}
.total-line.grand .total-label { font-size: 15px; font-weight: 700; color: #111827; }
.grand-amount {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #059669;
  line-height: 1;
  transition: transform 0.2s ease;
}
.grand-amount.pop {
  animation: pop 0.25s ease;
}
@keyframes pop {
  0% { transform: scale(1); }
  40% { transform: scale(1.06); }
  100% { transform: scale(1); }
}

.cart-actions {
  display: flex;
  gap: 8px;
}
.action-hold, .action-pay {
  flex: 1;
  padding: 14px 0;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  font-family: inherit;
  transition: all 0.15s;
}
.action-hold {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}
.action-hold:hover:not(:disabled) { background: #e5e7eb; }
.action-pay {
  background: #059669;
  color: #fff;
}
.action-pay:hover:not(:disabled) { background: #047857; }
.action-pay:disabled { opacity: 0.4; cursor: default; }
</style>

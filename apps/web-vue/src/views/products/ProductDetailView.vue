<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="page-title">{{ product?.name || t('loading') }}</h1>
          <span v-if="product?.is_catch_weight" class="badge badge-cw">
            <span class="material-symbols-outlined icon-xs">scale</span>
            {{ t('catch-weight', 'Catch-Weight / Dual UOM') }}
          </span>
        </div>
        <p class="page-subtitle">{{ t('product-detail-sub', 'View product details, stock levels, and dual unit-of-measure configuration') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="$router.push('/products')">{{ t('back', 'Back') }}</button>
        <button class="btn-primary" @click="openEdit">{{ t('edit', 'Edit') }}</button>
      </div>
    </div>

    <SkeletonCard v-if="loading" variant="detail" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="product">
      <div class="detail-grid">
        <!-- Basic Info Card -->
        <div class="data-card">
          <div class="card-header"><h3>{{ t('basic-info', 'Basic Information') }}</h3></div>
          <div class="card-body">
            <div class="info-row"><span class="info-label">{{ t('sku', 'SKU') }}</span><span class="info-value cell-mono">{{ product.sku }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('category', 'Category') }}</span><span class="info-value">{{ product.category || '-' }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('brand', 'Brand') }}</span><span class="info-value">{{ product.brand || '-' }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('price', 'Base Price') }}</span><span class="info-value">${{ (product.price || 0).toFixed(2) }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('cost', 'Cost Price') }}</span><span class="info-value">${{ (product.cost_price || 0).toFixed(2) }}</span></div>
            <div class="info-row"><span class="info-label">{{ t('tax', 'Tax Rate') }}</span><span class="info-value">{{ ((product.tax_rate || 0) * 100).toFixed(1) }}%</span></div>
            <div class="info-row"><span class="info-label">{{ t('status', 'Status') }}</span><span class="info-value"><span :class="product.is_active ? 'badge badge-active' : 'badge badge-inactive'">{{ product.is_active ? t('active', 'Active') : t('inactive', 'Inactive') }}</span></span></div>
            <div class="info-row" v-if="product.is_phantom"><span class="info-label">{{ t('phantom', 'Phantom') }}</span><span class="info-value"><span class="badge badge-warning">{{ t('yes', 'Yes') }}</span></span></div>
          </div>
        </div>

        <!-- Dual UOM & Catch-Weight Configuration Card -->
        <div class="data-card" :class="{ 'card-cw-highlight': product.is_catch_weight }">
          <div class="card-header flex justify-between items-center">
            <h3>{{ t('dual-uom-config', 'Dual UOM & Catch-Weight') }}</h3>
            <span v-if="product.is_catch_weight" class="badge badge-cw-sm">
              <span class="material-symbols-outlined icon-xs">scale</span>
              {{ t('dual-uom-active', 'Dual UOM Active') }}
            </span>
          </div>
          <div class="card-body">
            <div class="info-row">
              <span class="info-label">{{ t('catch-weight-mode', 'Catch-Weight Mode') }}</span>
              <span class="info-value">
                <span :class="product.is_catch_weight ? 'badge badge-cw' : 'badge badge-inactive'">
                  {{ product.is_catch_weight ? t('enabled', 'Enabled') : t('disabled', 'Disabled') }}
                </span>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('pricing-uom', 'Pricing UOM') }}</span>
              <span class="info-value font-semibold">
                {{ pricingUomDisplay }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('nominal-weight', 'Nominal Weight / Case') }}</span>
              <span class="info-value cell-mono">
                {{ product.nominal_weight != null ? `${product.nominal_weight} ${pricingUomCode}` : '-' }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('tolerance-pct', 'Weight Tolerance') }}</span>
              <span class="info-value cell-mono">
                {{ product.tolerance_pct != null ? `±${product.tolerance_pct}%` : '-' }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('pricing-basis', 'Pricing Basis') }}</span>
              <span class="info-value capitalize">
                {{ product.pricing_basis || 'weight' }}
              </span>
            </div>
            <div v-if="product.is_catch_weight" class="cw-note-box mt-3">
              <span class="material-symbols-outlined cw-note-icon">info</span>
              <p class="cw-note-text">
                {{ t('cw-explanation', 'Physical stock is handled in stocking units (e.g. Cases), and invoiced dynamically based on exact scale weight captured during warehouse picking within') }}
                <strong>±{{ product.tolerance_pct || 0 }}%</strong> {{ t('tolerance-limits', 'tolerance limits.') }}
              </p>
            </div>
          </div>
        </div>

        <!-- Stock Levels Card -->
        <div class="data-card">
          <div class="card-header"><h3>{{ t('stock-levels', 'Stock Levels') }}</h3></div>
          <div class="card-body">
            <SkeletonTable v-if="stockLoading" :rows="3" :columns="3" />
            <div v-else-if="!stockLevels.length" class="empty-section">{{ t('no-stock', 'No stock records found') }}</div>
            <div v-else>
              <div class="stock-row" v-for="sl in stockLevels" :key="sl.id">
                <span class="warehouse-name">{{ sl.warehouse_name || sl.warehouse_id }}</span>
                <span class="stock-qty" :class="stockClass(sl)">{{ sl.qty }}</span>
                <span v-if="sl.reserved_qty" class="stock-reserved">({{ sl.reserved_qty }} {{ t('reserved', 'Reserved') }})</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Suppliers Card -->
        <div class="data-card">
          <div class="card-header"><h3>{{ t('suppliers', 'Suppliers') }}</h3></div>
          <div class="card-body">
            <div v-if="supplierLinks.length">
              <div class="supplier-row" v-for="link in supplierLinks" :key="link.id">
                <span>{{ supplierName(link.supplier_id) }}</span>
                <span class="cell-mono">${{ (link.unit_cost || 0).toFixed(2) }}</span>
                <span class="cell-mono">{{ link.lead_time_days || '-' }}d</span>
                <span class="badge badge-sm" :class="link.is_preferred ? 'badge-active' : 'badge-inactive'">{{ link.is_preferred ? t('preferred', 'Preferred') : '-' }}</span>
              </div>
            </div>
            <div v-else class="empty-section">{{ t('no-suppliers', 'No suppliers linked') }}</div>
          </div>
        </div>
      </div>

      <!-- Edit Product Modal -->
      <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
        <div class="modal-content modal-wide">
          <div class="modal-header">
            <h3>{{ t('edit-product', 'Edit Product') }}</h3>
            <button class="btn-icon" @click="showEdit = false" aria-label="Close">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <form @submit.prevent="saveProduct" class="modal-body">
            <div class="form-tabs">
              <button type="button" class="tab-btn" :class="{ active: activeTab === 'general' }" @click="activeTab = 'general'">
                {{ t('tab-general', 'General') }}
              </button>
              <button type="button" class="tab-btn" :class="{ active: activeTab === 'pricing' }" @click="activeTab = 'pricing'">
                {{ t('tab-pricing', 'Pricing') }}
              </button>
              <button type="button" class="tab-btn" :class="{ active: activeTab === 'dual-uom' }" @click="activeTab = 'dual-uom'">
                {{ t('tab-dual-uom', 'Dual UOM & Catch-Weight') }}
              </button>
            </div>

            <!-- General Tab -->
            <div v-show="activeTab === 'general'" class="tab-content">
              <div class="form-row">
                <div class="form-group">
                  <label>{{ t('name', 'Name') }} <span class="required">*</span></label>
                  <input type="text" v-model="form.name" class="form-input" required />
                </div>
                <div class="form-group">
                  <label>{{ t('prod-sku', 'SKU') }} <span class="required">*</span></label>
                  <input type="text" v-model="form.sku" class="form-input" required />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>{{ t('category', 'Category') }}</label>
                  <input type="text" v-model="form.category" class="form-input" />
                </div>
                <div class="form-group">
                  <label>{{ t('brand', 'Brand') }}</label>
                  <input type="text" v-model="form.brand" class="form-input" />
                </div>
              </div>
              <div class="form-group">
                <label>{{ t('description', 'Description') }}</label>
                <textarea v-model="form.description" class="form-input form-textarea" rows="3"></textarea>
              </div>
              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="form.is_active" />
                  {{ t('active', 'Active') }}
                </label>
              </div>
            </div>

            <!-- Pricing Tab -->
            <div v-show="activeTab === 'pricing'" class="tab-content">
              <div class="form-row">
                <div class="form-group">
                  <label>{{ t('price', 'Base Price ($)') }}</label>
                  <input type="number" step="0.01" min="0" v-model.number="form.price" class="form-input" />
                </div>
                <div class="form-group">
                  <label>{{ t('cost-price', 'Cost Price ($)') }}</label>
                  <input type="number" step="0.01" min="0" v-model.number="form.cost_price" class="form-input" />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>{{ t('tax-rate', 'Tax Rate') }}</label>
                  <div class="input-suffix">
                    <input type="number" step="0.01" min="0" max="1" v-model.number="form.tax_rate" class="form-input" />
                    <span class="suffix">%</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Dual UOM & Catch-Weight Tab -->
            <div v-show="activeTab === 'dual-uom'" class="tab-content">
              <div class="form-group">
                <label class="checkbox-label font-semibold">
                  <input type="checkbox" v-model="form.is_catch_weight" />
                  {{ t('enable-catch-weight', 'Enable Catch-Weight / Dual Unit-of-Measure') }}
                </label>
                <p class="field-hint">
                  {{ t('catch-weight-desc', 'Check this if the item is inventoried by pack/case and billed based on exact weighed physical weight (e.g. cheese blocks, meat cuts).') }}
                </p>
              </div>

              <div v-if="form.is_catch_weight" class="cw-form-fields p-3 rounded-lg border border-purple-200 bg-purple-50 mt-3">
                <div class="form-row">
                  <div class="form-group">
                    <label>{{ t('pricing-uom', 'Pricing Unit of Measure (UOM)') }} <span class="required">*</span></label>
                    <select v-model.number="form.pricing_uom_id" class="form-input">
                      <option :value="null">{{ t('select-uom', '-- Select Pricing UOM --') }}</option>
                      <option v-for="uom in uoms" :key="uom.id" :value="uom.id">
                        {{ uom.uom_code }} - {{ uom.uom_name }} ({{ uom.category }})
                      </option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label>{{ t('nominal-weight', 'Nominal Weight per Stocking Unit') }}</label>
                    <input type="number" step="0.001" min="0" v-model.number="form.nominal_weight" class="form-input" placeholder="e.g. 20.0" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>{{ t('tolerance-pct', 'Weight Tolerance Percentage (±%)') }}</label>
                    <div class="input-suffix">
                      <input type="number" step="0.1" min="0" max="100" v-model.number="form.tolerance_pct" class="form-input" placeholder="e.g. 5.0" />
                      <span class="suffix">%</span>
                    </div>
                  </div>
                  <div class="form-group">
                    <label>{{ t('pricing-basis', 'Pricing Basis') }}</label>
                    <select v-model="form.pricing_basis" class="form-input">
                      <option value="weight">{{ t('basis-weight', 'Physical Weight (Catch-Weight)') }}</option>
                      <option value="quantity">{{ t('basis-quantity', 'Fixed Unit Quantity') }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-outline" @click="showEdit = false">{{ t('cancel', 'Cancel') }}</button>
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? t('saving', 'Saving...') : t('save', 'Save Changes') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import SkeletonCard from '../../components/SkeletonCard.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const product = ref(null)
const stockLevels = ref([])
const stockLoading = ref(true)
const supplierLinks = ref([])
const suppliers = ref([])
const uoms = ref([])
const showEdit = ref(false)
const saving = ref(false)
const activeTab = ref('general')

const form = reactive({
  name: '',
  sku: '',
  description: '',
  category: '',
  brand: '',
  price: 0,
  cost_price: 0,
  tax_rate: 0.05,
  is_active: true,
  is_catch_weight: false,
  pricing_uom_id: null,
  nominal_weight: null,
  tolerance_pct: null,
  pricing_basis: 'weight'
})

const pricingUom = computed(() => {
  if (!product.value?.pricing_uom_id || !uoms.value.length) return null
  return uoms.value.find(u => u.id === product.value.pricing_uom_id)
})

const pricingUomDisplay = computed(() => {
  if (!product.value?.is_catch_weight) return '-'
  if (pricingUom.value) {
    return `${pricingUom.value.uom_code} - ${pricingUom.value.uom_name}`
  }
  return product.value?.pricing_uom_id ? `UOM #${product.value.pricing_uom_id}` : '-'
})

const pricingUomCode = computed(() => {
  return pricingUom.value?.uom_code || 'kg'
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [prodRes, stockRes, suppRes, linksRes, uomsRes] = await Promise.all([
      api.get(`/T0003I/${route.params.id}`),
      api.get('/T0009I/', { params: { product_id: route.params.id } }),
      api.get('/T0011I/'),
      api.get(`/T0103I/by-product/${route.params.id}`),
      api.get('/T0001I/').catch(() => ({ data: [] })),
    ])
    product.value = prodRes.data
    stockLevels.value = stockRes.data || []
    suppliers.value = suppRes.data || []
    supplierLinks.value = linksRes.data || []
    uoms.value = uomsRes.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load product'
  } finally {
    loading.value = false
    stockLoading.value = false
  }
}

function openEdit() {
  if (!product.value) return
  form.name = product.value.name || ''
  form.sku = product.value.sku || ''
  form.description = product.value.description || ''
  form.category = product.value.category || ''
  form.brand = product.value.brand || ''
  form.price = product.value.price || 0
  form.cost_price = product.value.cost_price || 0
  form.tax_rate = product.value.tax_rate ?? 0.05
  form.is_active = product.value.is_active ?? true
  form.is_catch_weight = product.value.is_catch_weight ?? false
  form.pricing_uom_id = product.value.pricing_uom_id ?? null
  form.nominal_weight = product.value.nominal_weight ?? null
  form.tolerance_pct = product.value.tolerance_pct ?? null
  form.pricing_basis = product.value.pricing_basis || 'weight'
  activeTab.value = 'general'
  showEdit.value = true
}

async function saveProduct() {
  saving.value = true
  try {
    const payload = {
      name: form.name,
      sku: form.sku,
      description: form.description || null,
      category: form.category || null,
      brand: form.brand || null,
      price: form.price,
      cost_price: form.cost_price || 0,
      tax_rate: form.tax_rate,
      is_active: form.is_active,
      is_catch_weight: form.is_catch_weight,
      pricing_uom_id: form.pricing_uom_id ? Number(form.pricing_uom_id) : null,
      nominal_weight: form.nominal_weight !== null && form.nominal_weight !== '' ? Number(form.nominal_weight) : null,
      tolerance_pct: form.tolerance_pct !== null && form.tolerance_pct !== '' ? Number(form.tolerance_pct) : null,
      pricing_basis: form.pricing_basis || 'weight'
    }
    await api.put(`/T0003I/${product.value.id}`, payload)
    toast(t('product-updated', 'Product updated successfully'), 'success')
    showEdit.value = false
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-save-product', 'Failed to save product'), 'error')
  } finally {
    saving.value = false
  }
}

function supplierName(id) {
  const s = suppliers.value.find(x => x.id === id)
  return s ? s.name : `#${id}`
}

function stockClass(sl) {
  const avail = sl.qty - (sl.reserved_qty || 0)
  if (avail <= 0) return 'stock-out'
  if (avail <= (sl.reorder_level || 5)) return 'stock-low'
  return ''
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.header-actions { display: flex; gap: 10px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
.card-header { padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.card-header h3 { font-size: 14px; font-weight: 700; margin: 0; color: #1a1a2e; }
.card-body { padding: 16px 20px; }
.info-row { display: flex; padding: 8px 0; border-bottom: 1px solid #f8f8f8; font-size: 13px; align-items: center; }
.info-row:last-child { border-bottom: none; }
.info-label { color: #888; min-width: 140px; flex-shrink: 0; }
.info-value { color: #1a1a2e; font-weight: 500; }
.cell-mono { font-family: monospace; }
.stock-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f8f8f8; font-size: 13px; }
.stock-row:last-child { border-bottom: none; }
.warehouse-name { flex: 1; color: #555; }
.stock-qty { font-weight: 700; min-width: 40px; text-align: right; }
.stock-reserved { color: #d97706; font-size: 11px; }
.stock-out { color: #dc2626; }
.stock-low { color: #d97706; }
.supplier-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.supplier-row span { min-width: 60px; }
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: #f3f4f6; color: #888; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-cw { background: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
.badge-cw-sm { background: #f3e8ff; color: #7e22ce; font-size: 11px; padding: 2px 8px; border-radius: 12px; }
.card-cw-highlight { border-color: #d8b4fe; box-shadow: 0 1px 3px rgba(126, 34, 206, 0.05); }
.badge-sm { font-size: 10px !important; padding: 1px 6px !important; }
.empty-section { font-size: 12px; color: #999; padding: 12px 0; text-align: center; }
.icon-xs { font-size: 14px; }
.cw-note-box { display: flex; gap: 8px; background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 6px; padding: 10px 12px; align-items: flex-start; }
.cw-note-icon { color: #7e22ce; font-size: 18px; flex-shrink: 0; }
.cw-note-text { font-size: 12px; color: #581c87; margin: 0; line-height: 1.4; }
.field-hint { font-size: 12px; color: #6b7280; margin-top: 4px; margin-left: 24px; }

/* Modal & Tabs */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 12px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
.modal-wide { max-width: 680px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #111827; }
.modal-body { padding: 20px; }
.form-tabs { display: flex; gap: 8px; border-bottom: 1px solid #e5e7eb; margin-bottom: 16px; }
.tab-btn { padding: 8px 16px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; border-bottom: 2px solid transparent; }
.tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.form-textarea { resize: vertical; }
.required { color: #ef4444; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; }
.input-suffix { position: relative; display: flex; align-items: center; }
.input-suffix .suffix { position: absolute; right: 12px; color: #9ca3af; font-size: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; padding-top: 16px; border-top: 1px solid #e5e7eb; }
.btn-primary { background: #2563eb; color: #fff; padding: 8px 16px; border-radius: 6px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-icon { background: transparent; border: none; cursor: pointer; color: #6b7280; padding: 4px; border-radius: 4px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-3 { gap: 12px; }
.mt-3 { margin-top: 12px; }
.font-semibold { font-weight: 600; }
.capitalize { text-transform: capitalize; }
</style>

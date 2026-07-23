<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('products-title', 'Products') }}</h1>
        <p class="page-subtitle">{{ t('products-sub', 'Manage your product catalog') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn-outline" @click="scanPhantoms" :disabled="scanning">
          <span class="material-symbols-outlined">scan</span> {{ scanning ? t('scanning', 'Scanning...') : t('scan-phantoms', 'Scan Phantoms') }}
        </button>
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-product', 'New Product') }}
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ items.length }}</div>
        <div class="stat-lbl">{{ t('total') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num active">{{ activeCount }}</div>
        <div class="stat-lbl">{{ t('active') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num inactive">{{ inactiveCount }}</div>
        <div class="stat-lbl">{{ t('inactive') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num categories">{{ categoryCount }}</div>
        <div class="stat-lbl">{{ t('categories', 'Categories') }}</div>
      </div>
    </div>

    <SkeletonTable v-if="loading" :rows="6" :columns="7" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">inventory_2</span>
      <p>{{ t('no-products', 'No products found') }}</p>
      <button class="btn-primary" @click="openAdd">{{ t('add-product', 'Add Product') }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('prod-sku', 'SKU') }}</th>
              <th>{{ t('name') }}</th>
              <th>{{ t('prod-type', 'Type') }}</th>
              <th>{{ t('category') }}</th>
              <th class="col-price">{{ t('price') }}</th>
              <th>{{ t('status') }}</th>
              <th class="col-actions">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" :class="{ 'row-inactive': !item.is_active }">
              <td class="cell-sku">{{ item.sku || '-' }}</td>
              <td class="cell-name"><router-link :to="`/products/${item.id}`" class="product-link">{{ item.name }}</router-link></td>
              <td class="cell-type"><span class="badge badge-type">{{ item.type || 'stockable' }}</span></td>
              <td class="cell-category">{{ item.category || '-' }}</td>
              <td class="cell-price">${{ (item.price || 0).toFixed(2) }}</td>
              <td>
                <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ item.is_active ? t('active') : t('inactive') }}
                </span>
              </td>
              <td class="cell-actions">
                <button class="btn-icon" @click="openEdit(item)" :title="t('edit')" :aria-label="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="confirmDelete(item)" :title="t('delete')" :aria-label="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3>{{ isEditing ? t('edit-product', 'Edit Product') : t('new-product', 'New Product') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="save" class="modal-body">
          <div class="form-tabs">
            <button type="button" class="tab-btn" :class="{ active: activeTab === 'general' }" @click="activeTab = 'general'">{{ t('tab-general', 'General') }}</button>
            <button type="button" class="tab-btn" :class="{ active: activeTab === 'sales' }" @click="activeTab = 'sales'">{{ t('tab-sales', 'Sales') }}</button>
            <button type="button" class="tab-btn" :class="{ active: activeTab === 'inventory' }" @click="activeTab = 'inventory'">{{ t('tab-inventory', 'Inventory') }}</button>
            <button type="button" v-if="isEditing" class="tab-btn" :class="{ active: activeTab === 'suppliers' }" @click="activeTab = 'suppliers'">{{ t('tab-suppliers', 'Suppliers') }}</button>
          </div>

          <div v-show="activeTab === 'general'" class="tab-content">
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('name') }} <span class="required">*</span></label>
                <input type="text" v-model="form.name" @blur="fv.touch('name'); fv.validate('name', form.name)" class="form-input" :class="{ 'input-error': fv.touched.name && fv.errors.name }" />
                <FormFieldError :message="fv.touched.name ? fv.errors.name : ''" />
              </div>
              <div class="form-group">
                <label>{{ t('prod-type', 'Type') }}</label>
                <select v-model="form.type" class="form-input">
                  <option value="stockable">{{ t('type-stockable', 'Stockable Product') }}</option>
                  <option value="consumable">{{ t('type-consumable', 'Consumable') }}</option>
                  <option value="service">{{ t('type-service', 'Service') }}</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('prod-sku', 'SKU') }} <span class="required">*</span></label>
                <input type="text" v-model="form.sku" @blur="fv.touch('sku'); fv.validate('sku', form.sku)" class="form-input" :class="{ 'input-error': fv.touched.sku && fv.errors.sku }" />
                <FormFieldError :message="fv.touched.sku ? fv.errors.sku : ''" />
              </div>
              <div class="form-group">
                <label>{{ t('barcode', 'Barcode') }}</label>
                <input type="text" v-model="form.barcode" class="form-input" placeholder="EAN / UPC / CODE128" />
              </div>
            </div>
            <div class="form-group">
              <label>{{ t('description', 'Description') }}</label>
              <textarea v-model="form.description" class="form-input form-textarea" rows="3"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="form.is_saleable" />
                  {{ t('can-be-sold', 'Can be Sold') }}
                </label>
              </div>
              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="form.is_purchasable" />
                  {{ t('can-be-purchased', 'Can be Purchased') }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" />
                {{ t('active') }}
              </label>
            </div>
          </div>

          <div v-show="activeTab === 'sales'" class="tab-content">
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('price') }}</label>
                <div class="input-prefix">
                  <span class="prefix">$</span>
                  <input type="number" step="0.01" min="0" v-model.number="form.price" @blur="fv.touch('price'); fv.validate('price', form.price)" class="form-input" :class="{ 'input-error': fv.touched.price && fv.errors.price }" />
                </div>
                <FormFieldError :message="fv.touched.price ? fv.errors.price : ''" />
              </div>
              <div class="form-group">
                <label>{{ t('tax-rate', 'Tax Rate') }}</label>
                <div class="input-suffix">
                  <input type="number" step="0.01" min="0" max="1" v-model.number="form.tax_rate" @blur="fv.touch('tax_rate'); fv.validate('tax_rate', form.tax_rate)" class="form-input" :class="{ 'input-error': fv.touched.tax_rate && fv.errors.tax_rate }" />
                  <span class="suffix">%</span>
                </div>
                <FormFieldError :message="fv.touched.tax_rate ? fv.errors.tax_rate : ''" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('cost-price', 'Cost Price') }}</label>
                <div class="input-prefix">
                  <span class="prefix">$</span>
                  <input type="number" step="0.01" min="0" v-model.number="form.cost_price" class="form-input" />
                </div>
              </div>
            </div>
          </div>

          <div v-show="activeTab === 'inventory'" class="tab-content">
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('category') }}</label>
                <input type="text" v-model="form.category" class="form-input" list="category-list" />
                <datalist id="category-list">
                  <option v-for="c in allCategories" :key="c" :value="c" />
                </datalist>
              </div>
              <div class="form-group">
                <label>{{ t('brand', 'Brand') }}</label>
                <input type="text" v-model="form.brand" class="form-input" list="brand-list" />
                <datalist id="brand-list">
                  <option v-for="b in allBrands" :key="b" :value="b" />
                </datalist>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ t('weight', 'Weight (kg)') }}</label>
                <input type="number" step="0.001" min="0" v-model.number="form.weight" class="form-input" />
              </div>
              <div class="form-group">
                <label>{{ t('volume', 'Volume (m\u00B3)') }}</label>
                <input type="number" step="0.001" min="0" v-model.number="form.volume" class="form-input" />
              </div>
            </div>
            <div class="form-group">
              <label>{{ t('image-url', 'Image URL') }}</label>
              <input type="text" v-model="form.image_url" class="form-input" placeholder="https://..." />
            </div>
          </div>

          <div v-show="activeTab === 'suppliers'" class="tab-content">
            <div class="supplier-section">
              <h4 class="section-title">{{ t('linked-suppliers', 'Linked Suppliers') }}</h4>
              <div v-if="supplierLinks.length">
                <div class="supplier-row" v-for="link in supplierLinks" :key="link.id">
                  <span class="supplier-name">{{ supplierName(link.supplier_id) }}</span>
                  <span class="cell-mono">${{ (link.unit_cost || 0).toFixed(2) }}</span>
                  <span class="cell-mono">{{ link.lead_time_days || '-' }}d</span>
                  <span class="badge badge-sm" :class="link.is_preferred ? 'badge-active' : 'badge-inactive'">{{ link.is_preferred ? t('preferred', 'Preferred') : '-' }}</span>
                  <button class="btn-icon btn-icon-danger btn-xs" @click="removeSupplier(link)" :aria-label="t('remove')"><span class="material-symbols-outlined">close</span></button>
                </div>
              </div>
              <div v-else class="empty-section">{{ t('no-suppliers', 'No suppliers linked') }}</div>
              <div class="add-supplier-row">
                <select v-model="newSupplier.supplier_id" class="form-input form-input-sm">
                  <option value="">{{ t('select-supplier', '-- Select Supplier --') }}</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
                <input type="number" step="0.01" v-model.number="newSupplier.unit_cost" class="form-input form-input-sm" :placeholder="t('cost', 'Cost')" />
                <input type="number" v-model.number="newSupplier.lead_time_days" class="form-input form-input-sm form-input-xs" :placeholder="t('days', 'Days')" />
                <button class="btn-primary btn-xs" :disabled="!newSupplier.supplier_id" @click="addSupplier">{{ t('add', 'Add') }}</button>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? t('saving') : t('save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p>{{ t('confirm-delete-msg') }} <strong>{{ deletingItem?.name }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel') }}</button>
            <button class="btn-danger" @click="doDelete">{{ t('delete') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import { useWebSocket } from '../../composables/useWebSocket.js'
import { useAuthStore } from '../../stores/auth.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import FormFieldError from '../../components/FormFieldError.vue'
import { useFormValidation, required, minValue, maxLength } from '../../composables/useFormValidation.js'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const items = ref([])
const showModal = ref(false)
const showDelete = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const scanning = ref(false)
const deletingItem = ref(null)
const editingId = ref(null)
const suppliers = ref([])
const supplierLinks = ref([])
const newSupplier = ref({ supplier_id: null, unit_cost: 0, lead_time_days: 0 })
const activeTab = ref('general')

const auth = useAuthStore()
const businessId = auth.user?.business_id || '1'
const wsInventory = useWebSocket(`/ws/inventory/${businessId}`)
wsInventory.on('stock_updated', () => {
  load()
})

const fv = useFormValidation({
  name: [required('Name is required'), maxLength(200)],
  sku: [required('SKU is required'), maxLength(50)],
  price: [minValue(0, 'Price cannot be negative')],
  tax_rate: [minValue(0, 'Tax rate cannot be negative')],
})

const form = reactive({
  name: '', sku: '', barcode: '', description: '', type: 'stockable',
  price: 0, cost_price: null, tax_rate: 0.05,
  category: '', brand: '', weight: 0, volume: 0,
  image_url: '', is_purchasable: true, is_saleable: true, is_active: true
})

const allCategories = computed(() => {
  return [...new Set(items.value.map(p => p.category).filter(Boolean))]
})

const allBrands = computed(() => {
  return [...new Set(items.value.map(p => p.brand).filter(Boolean))]
})

const activeCount = computed(() => items.value.filter(p => p.is_active).length)
const inactiveCount = computed(() => items.value.filter(p => !p.is_active).length)
const categoryCount = computed(() => {
  const cats = new Set(items.value.map(p => p.category).filter(Boolean))
  return cats.size
})

function resetForm() {
  form.name = ''
  form.sku = ''
  form.barcode = ''
  form.description = ''
  form.type = 'stockable'
  form.price = 0
  form.cost_price = null
  form.tax_rate = 0.05
  form.category = ''
  form.brand = ''
  form.weight = 0
  form.volume = 0
  form.image_url = ''
  form.is_purchasable = true
  form.is_saleable = true
  form.is_active = true
  activeTab.value = 'general'
  fv.reset()
}

function openAdd() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  showModal.value = true
}

function openEdit(item) {
  isEditing.value = true
  editingId.value = item.id
  form.name = item.name
  form.sku = item.sku
  form.barcode = item.barcode || ''
  form.description = item.description || ''
  form.type = item.type || 'stockable'
  form.price = item.price
  form.cost_price = item.cost_price
  form.tax_rate = item.tax_rate
  form.category = item.category || ''
  form.brand = item.brand || ''
  form.weight = item.weight || 0
  form.volume = item.volume || 0
  form.image_url = item.image_url || ''
  form.is_purchasable = item.is_purchasable ?? true
  form.is_saleable = item.is_saleable ?? true
  form.is_active = item.is_active
  activeTab.value = 'general'
  loadSupplierLinks(item.id)
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  if (!fv.validateAll(form)) {
    toast('Please fix validation errors', 'error')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name, sku: form.sku,
      barcode: form.barcode || null, description: form.description || null,
      type: form.type,
      price: form.price, cost_price: form.cost_price || 0,
      category: form.category || null, brand: form.brand || null,
      tax_rate: form.tax_rate, weight: form.weight || 0, volume: form.volume || 0,
      image_url: form.image_url || null,
      is_purchasable: form.is_purchasable, is_saleable: form.is_saleable,
      is_active: form.is_active
    }
    if (isEditing.value) {
      await api.put(`/T0003I/${editingId.value}`, payload)
      toast('Product updated', 'success')
    } else {
      await api.post('/T0003I/', payload)
      toast('Product created', 'success')
    }
    closeModal()
    await load()
  } catch {
    toast('Failed to save product', 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  deletingItem.value = item
  showDelete.value = true
}

async function doDelete() {
  try {
    await api.delete(`/T0003I/${deletingItem.value.id}`)
    toast('Product deleted', 'success')
    showDelete.value = false
    await load()
  } catch {
    toast('Failed to delete product', 'error')
  }
}

function supplierName(id) {
  const s = suppliers.value.find(x => x.id === id)
  return s ? s.name : `#${id}`
}

async function loadSupplierLinks(productId) {
  try {
    const [linksRes, suppRes] = await Promise.all([
      api.get(`/T0103I/by-product/${productId}`),
      suppliers.value.length ? Promise.resolve({ data: suppliers.value }) : api.get('/T0011I/'),
    ])
    supplierLinks.value = linksRes.data || []
    if (suppRes.data) suppliers.value = suppRes.data
  } catch {
    supplierLinks.value = []
  }
  newSupplier.value = { supplier_id: null, unit_cost: 0, lead_time_days: 0 }
}

async function addSupplier() {
  if (!newSupplier.value.supplier_id || !editingId.value) return
  try {
    await api.post('/T0103I/', {
      product_id: editingId.value,
      supplier_id: newSupplier.value.supplier_id,
      unit_cost: newSupplier.value.unit_cost || 0,
      lead_time_days: newSupplier.value.lead_time_days || 0,
    })
    await loadSupplierLinks(editingId.value)
  } catch {
    toast('Failed to link supplier', 'error')
  }
}

async function removeSupplier(link) {
  try {
    await api.delete(`/T0103I/${link.id}`)
    supplierLinks.value = supplierLinks.value.filter(l => l.id !== link.id)
    toast('Supplier removed', 'success')
  } catch {
    toast('Failed to remove supplier', 'error')
  }
}

async function scanPhantoms() {
  scanning.value = true
  try {
    const res = await api.post('/T0003I/scan-phantoms')
    toast(`${res.data?.flagged || 0} products flagged as phantom`, 'success')
    await load()
  } catch {
    toast('Failed to scan phantoms', 'error')
  } finally {
    scanning.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0003I/')
    items.value = res.data || []
  } catch {
    error.value = 'Failed to load products.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-actions { display: flex; align-items: center; gap: 8px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; text-align: center; }
.stat-num { font-size: 24px; font-weight: 700; color: var(--color-primary); }
.stat-num.active { color: var(--color-success); }
.stat-num.inactive { color: var(--text-muted); }
.stat-num.categories { color: #0891b2; }
.stat-lbl { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.table-wrap { overflow-x: auto; }
.row-inactive { opacity: 0.55; }
.cell-sku { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-subtle); }
.cell-name { font-weight: 600; }
.product-link { color: var(--text-primary); text-decoration: none; }
.product-link:hover { color: var(--color-primary); text-decoration: underline; }
.cell-type { text-align: center; }
.badge-type { background: var(--bg-surface-hover); color: var(--text-secondary); font-size: 11px; }
.cell-category { color: var(--text-muted); }
.cell-price { text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.col-price, .col-actions { text-align: right; }
.cell-actions { text-align: right; white-space: nowrap; }
.cell-mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-subtle); }

.badge-inactive { background: var(--bg-surface-hover); color: var(--text-faint); }

.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: var(--color-error); color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-icon-danger:hover { background: #fee2e2; color: var(--color-error); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-wide { width: 680px; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-light); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-body { padding: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border-light); }

.form-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-light); padding: 0 24px; background: var(--bg-surface-hover); }
.tab-btn { padding: 10px 18px; font-size: 13px; font-weight: 600; color: var(--text-muted); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--color-primary); border-bottom-color: var(--color-primary); background: var(--bg-surface); }

.tab-content { padding: 20px 24px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; transition: border 0.15s; background: var(--bg-surface); color: var(--text-primary); box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }
.input-error { border-color: var(--color-error) !important; }
.input-error:focus { border-color: var(--color-error) !important; }
.required { color: var(--color-error); }
.form-textarea { resize: vertical; font-family: inherit; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; color: var(--text-primary); }
.checkbox-label input { width: 16px; height: 16px; accent-color: var(--color-primary); }

.input-prefix, .input-suffix { display: flex; align-items: center; }
.input-prefix .form-input { border-top-left-radius: 0; border-bottom-left-radius: 0; }
.input-suffix .form-input { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.prefix, .suffix { padding: 8px 10px; background: var(--bg-surface-hover); border: 1px solid var(--border-input); font-size: 13px; color: var(--text-muted); font-weight: 600; }
.prefix { border-right: none; border-radius: 6px 0 0 6px; }
.suffix { border-left: none; border-radius: 0 6px 6px 0; }

.supplier-section { }
.section-title { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 0 0 10px; }
.supplier-name { flex: 1; }
.supplier-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }
.add-supplier-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.form-input-sm { padding: 6px 8px; font-size: 12px; }
.form-input-xs { width: 60px; }
.btn-xs { padding: 4px 12px !important; font-size: 12px !important; }
.badge-sm { font-size: 10px !important; padding: 1px 6px !important; }
.empty-section { font-size: 12px; color: var(--text-faint); padding: 8px 0; }

[dir="rtl"] .page-actions { flex-direction: row-reverse; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .cell-price,
[dir="rtl"] .col-price,
[dir="rtl"] .cell-actions,
[dir="rtl"] .col-actions { text-align: left; }
[dir="rtl"] .modal-actions { flex-direction: row-reverse; }
[dir="rtl"] .form-row { direction: rtl; }
[dir="rtl"] .form-tabs { direction: rtl; }
[dir="rtl"] .checkbox-label { flex-direction: row-reverse; }
[dir="rtl"] .prefix { border-left: none; border-right: 1px solid var(--border-input); border-radius: 0 6px 6px 0; }
[dir="rtl"] .input-prefix .form-input { border-radius: 6px 0 0 6px; }
</style>

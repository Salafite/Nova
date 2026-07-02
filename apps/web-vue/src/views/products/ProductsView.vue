<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ locale === 'ar-EG' ? 'المنتجات' : 'Products' }}</h2>
        <p class="page-subtitle">{{ locale === 'ar-EG' ? 'إدارة كتالوج المنتجات' : 'Manage your product catalog' }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">
        <span class="material-symbols-outlined">add</span> {{ locale === 'ar-EG' ? 'منتج جديد' : 'New Product' }}
      </button>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ items.length }}</div>
        <div class="stat-lbl">{{ locale === 'ar-EG' ? 'الإجمالي' : 'Total' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num active">{{ activeCount }}</div>
        <div class="stat-lbl">{{ locale === 'ar-EG' ? 'نشط' : 'Active' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num inactive">{{ inactiveCount }}</div>
        <div class="stat-lbl">{{ locale === 'ar-EG' ? 'غير نشط' : 'Inactive' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num categories">{{ categoryCount }}</div>
        <div class="stat-lbl">{{ locale === 'ar-EG' ? 'التصنيفات' : 'Categories' }}</div>
      </div>
    </div>

    <SkeletonTable v-if="loading" :rows="6" :columns="7" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">inventory_2</span>
      <p>{{ locale === 'ar-EG' ? 'لا توجد منتجات' : 'No products found' }}</p>
      <button class="btn-primary" @click="openAdd">{{ locale === 'ar-EG' ? 'إضافة منتج' : 'Add Product' }}</button>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ locale === 'ar-EG' ? 'رمز SKU' : 'SKU' }}</th>
              <th>{{ locale === 'ar-EG' ? 'الاسم' : 'Name' }}</th>
              <th>{{ locale === 'ar-EG' ? 'التصنيف' : 'Category' }}</th>
              <th class="col-price">{{ locale === 'ar-EG' ? 'السعر' : 'Price' }}</th>
              <th>{{ locale === 'ar-EG' ? 'الحالة' : 'Status' }}</th>
              <th class="col-actions">{{ locale === 'ar-EG' ? 'إجراءات' : 'Actions' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" :class="{ 'row-inactive': !item.is_active }">
              <td class="cell-sku">{{ item.sku || '-' }}</td>
              <td class="cell-name"><router-link :to="`/products/${item.id}`" class="product-link">{{ item.name }}</router-link></td>
              <td class="cell-category">{{ item.category || '-' }}</td>
              <td class="cell-price">${{ (item.price || 0).toFixed(2) }}</td>
              <td>
                <span :class="item.is_active ? 'badge badge-active' : 'badge badge-inactive'">
                  {{ item.is_active ? (locale === 'ar-EG' ? 'نشط' : 'Active') : (locale === 'ar-EG' ? 'غير نشط' : 'Inactive') }}
                </span>
              </td>
              <td class="cell-actions">
                <button class="btn-icon" @click="openEdit(item)" title="Edit" aria-label="Edit">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="confirmDelete(item)" title="Delete" aria-label="Delete">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? (locale === 'ar-EG' ? 'تعديل المنتج' : 'Edit Product') : (locale === 'ar-EG' ? 'منتج جديد' : 'New Product') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="save" class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'الاسم' : 'Name' }} <span class="required">*</span></label>
              <input type="text" v-model="form.name" @blur="fv.touch('name'); fv.validate('name', form.name)" class="form-input" :class="{ 'input-error': fv.touched.name && fv.errors.name }" />
              <FormFieldError :message="fv.touched.name ? fv.errors.name : ''" />
            </div>
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'رمز SKU' : 'SKU' }} <span class="required">*</span></label>
              <input type="text" v-model="form.sku" @blur="fv.touch('sku'); fv.validate('sku', form.sku)" class="form-input" :class="{ 'input-error': fv.touched.sku && fv.errors.sku }" />
              <FormFieldError :message="fv.touched.sku ? fv.errors.sku : ''" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'السعر' : 'Price' }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.price" @blur="fv.touch('price'); fv.validate('price', form.price)" class="form-input" :class="{ 'input-error': fv.touched.price && fv.errors.price }" />
              <FormFieldError :message="fv.touched.price ? fv.errors.price : ''" />
            </div>
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'تكلفة الشراء' : 'Cost Price' }}</label>
              <input type="number" step="0.01" min="0" v-model.number="form.cost_price" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'التصنيف' : 'Category' }}</label>
              <input type="text" v-model="form.category" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'العلامة التجارية' : 'Brand' }}</label>
              <input type="text" v-model="form.brand" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ locale === 'ar-EG' ? 'نسبة الضريبة' : 'Tax Rate' }}</label>
              <input type="number" step="0.01" min="0" max="1" v-model.number="form.tax_rate" @blur="fv.touch('tax_rate'); fv.validate('tax_rate', form.tax_rate)" class="form-input" :class="{ 'input-error': fv.touched.tax_rate && fv.errors.tax_rate }" />
              <FormFieldError :message="fv.touched.tax_rate ? fv.errors.tax_rate : ''" />
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" />
                {{ locale === 'ar-EG' ? 'نشط' : 'Active' }}
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>{{ locale === 'ar-EG' ? 'رابط الصورة' : 'Image URL' }}</label>
            <input type="text" v-model="form.image_url" class="form-input" />
          </div>
          <div v-if="isEditing" class="supplier-section">
            <h4 class="section-title">{{ locale === 'ar-EG' ? 'الموردون المرتبطون' : 'Linked Suppliers' }}</h4>
            <div v-if="supplierLinks.length">
              <div class="supplier-row" v-for="link in supplierLinks" :key="link.id">
                <span>{{ supplierName(link.supplier_id) }}</span>
                <span class="cell-mono">${{ (link.unit_cost || 0).toFixed(2) }}</span>
                <span class="cell-mono">{{ link.lead_time_days || '-' }}d</span>
                <span class="badge badge-sm" :class="link.is_preferred ? 'badge-active' : 'badge-inactive'">{{ link.is_preferred ? (locale === 'ar-EG' ? 'مفضل' : 'Preferred') : '-' }}</span>
                <button class="btn-icon btn-icon-danger btn-xs" @click="removeSupplier(link)" aria-label="Remove supplier"><span class="material-symbols-outlined">close</span></button>
              </div>
            </div>
            <div v-else class="empty-section">{{ locale === 'ar-EG' ? 'لا يوجد موردون مرتبطون' : 'No suppliers linked' }}</div>
            <div class="add-supplier-row">
              <select v-model="newSupplier.supplier_id" class="form-input form-input-sm">
                <option value="">{{ locale === 'ar-EG' ? '-- اختر مورد --' : '-- Select Supplier --' }}</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <input type="number" step="0.01" v-model.number="newSupplier.unit_cost" class="form-input form-input-sm" :placeholder="locale === 'ar-EG' ? 'التكلفة' : 'Cost'" />
              <input type="number" v-model.number="newSupplier.lead_time_days" class="form-input form-input-sm form-input-xs" :placeholder="locale === 'ar-EG' ? 'أيام' : 'Days'" />
              <button class="btn-primary btn-xs" :disabled="!newSupplier.supplier_id" @click="addSupplier">{{ locale === 'ar-EG' ? 'إضافة' : 'Add' }}</button>
            </div>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeModal">{{ locale === 'ar-EG' ? 'إلغاء' : 'Cancel' }}</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? (locale === 'ar-EG' ? 'جاري الحفظ...' : 'Saving...') : (locale === 'ar-EG' ? 'حفظ' : 'Save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ locale === 'ar-EG' ? 'تأكيد الحذف' : 'Confirm Delete' }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p>{{ locale === 'ar-EG' ? 'هل أنت متأكد من حذف' : 'Are you sure you want to delete' }} <strong>{{ deletingItem?.name }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ locale === 'ar-EG' ? 'إلغاء' : 'Cancel' }}</button>
            <button class="btn-danger" @click="doDelete">{{ locale === 'ar-EG' ? 'حذف' : 'Delete' }}</button>
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
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import FormFieldError from '../../components/FormFieldError.vue'
import { useFormValidation, required, minValue, maxLength } from '../../composables/useFormValidation.js'

const { show: toast } = useToast()
const { locale, dir } = useI18n()

const loading = ref(true)
const error = ref('')
const items = ref([])
const showModal = ref(false)
const showDelete = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const deletingItem = ref(null)
const editingId = ref(null)
const suppliers = ref([])
const supplierLinks = ref([])
const newSupplier = ref({ supplier_id: null, unit_cost: 0, lead_time_days: 0 })

const fv = useFormValidation({
  name: [required('Name is required'), maxLength(200)],
  sku: [required('SKU is required'), maxLength(50)],
  price: [minValue(0, 'Price cannot be negative')],
  tax_rate: [minValue(0, 'Tax rate cannot be negative')],
})

const form = reactive({
  name: '', sku: '', price: 0, cost_price: null,
  category: '', brand: '', tax_rate: 0.05,
  image_url: '', is_active: true
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
  form.price = 0
  form.cost_price = null
  form.category = ''
  form.brand = ''
  form.tax_rate = 0.05
  form.image_url = ''
  form.is_active = true
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
  form.price = item.price
  form.cost_price = item.cost_price
  form.category = item.category || ''
  form.brand = item.brand || ''
  form.tax_rate = item.tax_rate
  form.image_url = item.image_url || ''
  form.is_active = item.is_active
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
      name: form.name, sku: form.sku, price: form.price,
      cost_price: form.cost_price || 0, category: form.category || null,
      brand: form.brand || null, tax_rate: form.tax_rate,
      image_url: form.image_url || null, is_active: form.is_active
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
  } catch (e) {
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
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.page-subtitle { font-size: 13px; color: #888; margin-top: 2px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; text-align: center; }
.stat-num { font-size: 24px; font-weight: 700; color: #5d3fd3; }
.stat-num.active { color: #16a34a; }
.stat-num.inactive { color: #888; }
.stat-num.categories { color: #0891b2; }
.stat-lbl { font-size: 12px; color: #666; margin-top: 2px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.row-inactive { opacity: 0.55; }
.cell-sku { font-family: monospace; font-size: 12px; color: #888; }
.cell-name { font-weight: 600; }
.product-link { color: #1a1a2e; text-decoration: none; }
.product-link:hover { color: #5d3fd3; text-decoration: underline; }
.cell-category { color: #666; }
.cell-price { text-align: right; font-family: monospace; font-weight: 600; }
.col-price, .col-actions { text-align: right; }
.cell-actions { text-align: right; white-space: nowrap; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: #f3f4f6; color: #888; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: #dc2626; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; transition: border 0.15s; }
.form-input:focus { border-color: #5d3fd3; }
.input-error { border-color: #dc2626 !important; }
.input-error:focus { border-color: #dc2626 !important; }
.required { color: #dc2626; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-top: 24px; }
.checkbox-label input { width: 16px; height: 16px; }

.loading-state { text-align: center; padding: 80px 0; color: #999; font-size: 14px; }
.error-state { text-align: center; padding: 80px 0; color: #dc2626; }
.error-state p { margin-bottom: 16px; }
.empty-state { text-align: center; padding: 80px 0; color: #999; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }
.empty-state p { margin-bottom: 16px; }

.supplier-section { border-top: 1px solid #eee; margin-top: 16px; padding-top: 16px; }
.section-title { font-size: 13px; font-weight: 700; color: #1a1a2e; margin: 0 0 10px; }
.supplier-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.supplier-row span { min-width: 60px; }
.add-supplier-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.form-input-sm { padding: 6px 8px; font-size: 12px; }
.form-input-xs { width: 60px; }
.btn-xs { padding: 4px 12px !important; font-size: 12px !important; }
.badge-sm { font-size: 10px !important; padding: 1px 6px !important; }
.empty-section { font-size: 12px; color: #999; padding: 8px 0; }

[dir="rtl"] .page-header { flex-direction: row-reverse; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .cell-price,
[dir="rtl"] .col-price,
[dir="rtl"] .cell-actions,
[dir="rtl"] .col-actions { text-align: left; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
[dir="rtl"] .modal-actions { flex-direction: row-reverse; }
[dir="rtl"] .form-row { direction: rtl; }
[dir="rtl"] .checkbox-label { flex-direction: row-reverse; }
</style>

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('categories') }}</h1>
        <p class="page-subtitle">{{ t('categories-sub') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">{{ t('new-category') }}</button>
    </div>

    <SkeletonTable v-if="loading" :rows="5" :columns="3" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">category</span>
      <p>{{ t('no-categories') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('name') }}</th>
              <th class="text-center">{{ t('products') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cat in items" :key="cat.name">
              <td class="cell-name">{{ cat.name }}</td>
              <td class="text-center">{{ cat.product_count }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="startRename(cat)" :aria-label="t('rename')"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon btn-icon-danger" @click="confirmDelete(cat)" :aria-label="t('delete')"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ editing ? t('rename-category') : t('new-category') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('name') }} <span class="required">*</span></label>
            <input type="text" v-model="form.name" class="form-input" @blur="fv.touch('name'); fv.validate('name', form.name)" :class="{ 'input-error': fv.touched.name && fv.errors.name }" />
            <FormFieldError :message="fv.touched.name ? fv.errors.name : ''" />
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? t('saving') : t('save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <p>{{ t('delete-warning') }} <strong>{{ deletingItem?.name }}</strong>?</p>
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
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { useFormValidation, required } from '../../composables/useFormValidation.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import FormFieldError from '../../components/FormFieldError.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()

const loading = ref(true)
const error = ref('')
const items = ref([])
const showModal = ref(false)
const showDelete = ref(false)
const editing = ref(false)
const saving = ref(false)
const deletingItem = ref(null)
const form = ref({ name: '' })

const fv = useFormValidation({ name: [required(t('name-required'))] })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/categories/product-counts')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  form.value = { name: '' }
  fv.reset()
  showModal.value = true
}

function startRename(cat) {
  editing.value = true
  form.value = { name: cat.name, original: cat.name }
  fv.reset()
  showModal.value = true
}

async function save() {
  if (!fv.validateAll(form.value)) return
  saving.value = true
  try {
    if (editing.value) {
      await api.put('/categories/rename', null, { params: { old_name: form.value.original, new_name: form.value.name } })
      toast(t('renamed'), 'success')
    } else {
      await api.put('/categories/rename', null, { params: { old_name: '', new_name: form.value.name } })
      toast(t('created'), 'success')
    }
    closeModal()
    await load()
  } catch (e) {
    toast(e.response?.data?.detail || t('failed-save'), 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(cat) {
  deletingItem.value = cat
  showDelete.value = true
}

async function doDelete() {
  try {
    await api.put('/categories/rename', null, { params: { old_name: deletingItem.value.name, new_name: '' } })
    toast(t('deleted'), 'success')
    showDelete.value = false
    await load()
  } catch {
    toast(t('failed-delete'), 'error')
  }
}

function closeModal() { showModal.value = false }

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.text-center { text-align: center; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; transition: border 0.15s; }
.form-input:focus { border-color: #5d3fd3; }
.input-error { border-color: #dc2626 !important; }
.required { color: #dc2626; }
.empty-state { text-align: center; padding: 80px 0; color: #999; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }
</style>

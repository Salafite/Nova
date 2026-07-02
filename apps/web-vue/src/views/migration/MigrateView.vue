<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('migrate-title') }}</h2>
        <p class="page-subtitle">{{ t('migrate-sub') }}</p>
      </div>
    </div>

    <div v-if="step === 'upload'" class="data-card">
      <div class="card-body">
        <div class="form-group">
          <label>{{ t('migrate-entity') }}</label>
          <select v-model="entityType" class="form-input">
            <option value="products">{{ t('products') }}</option>
            <option value="customers">{{ t('customers') }}</option>
            <option value="suppliers">{{ t('suppliers') }}</option>
          </select>
        </div>
        <div class="upload-zone" @drop.prevent="handleDrop" @dragover.prevent>
          <input type="file" ref="fileInput" accept=".csv" @change="handleFile" hidden />
          <span class="material-symbols-outlined upload-icon">cloud_upload</span>
          <p>{{ t('migrate-drop-hint') }}</p>
          <button class="btn-outline btn-sm" @click="$refs.fileInput.click()">{{ t('migrate-browse') }}</button>
          <p v-if="selectedFile" class="file-name">{{ selectedFile.name }}</p>
        </div>
        <button class="btn-primary" :disabled="!selectedFile || uploading" @click="upload">
          {{ uploading ? t('uploading') : t('migrate-upload') }}
        </button>
      </div>
    </div>

    <div v-if="step === 'preview'" class="data-card">
      <div class="card-body">
        <div class="preview-summary">
          <div class="stat"><span class="stat-label">{{ t('migrate-total') }}</span><span class="stat-value">{{ preview.total_rows }}</span></div>
          <div class="stat"><span class="stat-label">{{ t('migrate-valid') }}</span><span class="stat-value stat-ok">{{ preview.valid_rows }}</span></div>
          <div class="stat"><span class="stat-label">{{ t('migrate-errors') }}</span><span class="stat-value" :class="preview.error_rows ? 'stat-err' : 'stat-ok'">{{ preview.error_rows }}</span></div>
        </div>

        <div v-if="preview.errors.length" class="error-list">
          <h4>{{ t('migrate-validation-errors') }}</h4>
          <div v-for="err in preview.errors" :key="err.row" class="error-row">
            <strong>{{ t('row') }} {{ err.row }}:</strong> {{ err.error }}
          </div>
        </div>

        <div v-if="preview.sample.length" class="sample-section">
          <h4>{{ t('migrate-sample') }} ({{ preview.sample.length }} {{ t('of') }} {{ preview.valid_rows }})</h4>
          <div class="table-wrap">
            <table class="data-table table-sm">
              <thead>
                <tr>
                  <th v-for="col in Object.keys(preview.sample[0])" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in preview.sample" :key="i">
                  <td v-for="val in row" :key="val">{{ val }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="preview-actions">
          <button class="btn-outline" @click="reset">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="!preview.valid_rows || committing" @click="commit">
            {{ committing ? t('committing') : t('migrate-commit') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="step === 'done'" class="data-card">
      <div class="card-body text-center">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <h3>{{ t('migrate-success') }}</h3>
        <p>{{ result.inserted_rows }} / {{ preview.total_rows }} {{ t('migrate-rows-imported') }}</p>
        <button class="btn-primary" @click="reset">{{ t('migrate-another') }}</button>
      </div>
    </div>

    <div v-if="step === 'error'" class="data-card">
      <div class="card-body text-center">
        <span class="material-symbols-outlined error-icon">error</span>
        <h3>{{ t('migrate-failed') }}</h3>
        <p>{{ errorMsg }}</p>
        <button class="btn-primary" @click="reset">{{ t('try-again') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../services/api'

const dir = computed(() => localStorage.getItem('nova_locale') === 'ar-EG' ? 'rtl' : 'ltr')
const locale = computed(() => localStorage.getItem('nova_locale') || 'en')

function t(key) {
  const labels = {
    'migrate-title': 'Data Migration',
    'migrate-sub': 'Import records from CSV files',
    'migrate-entity': 'Entity Type',
    products: 'Products',
    customers: 'Customers',
    suppliers: 'Suppliers',
    'migrate-drop-hint': 'Drag & drop a CSV file here, or click to browse',
    'migrate-browse': 'Browse Files',
    'migrate-upload': 'Upload & Preview',
    uploading: 'Uploading...',
    'migrate-total': 'Total Rows',
    'migrate-valid': 'Valid',
    'migrate-errors': 'Errors',
    'migrate-validation-errors': 'Validation Errors',
    row: 'Row',
    'migrate-sample': 'Sample Preview',
    of: 'of',
    cancel: 'Cancel',
    'migrate-commit': 'Commit Import',
    committing: 'Committing...',
    'migrate-success': 'Import Completed Successfully!',
    'migrate-rows-imported': 'rows imported successfully.',
    'migrate-another': 'Import Another File',
    'migrate-failed': 'Import Failed',
    'try-again': 'Try Again',
  }
  return labels[key] || key
}

const entityType = ref('products')
const selectedFile = ref(null)
const uploading = ref(false)
const committing = ref(false)
const step = ref('upload')
const preview = ref({})
const result = ref({})
const errorMsg = ref('')
const fileInput = ref(null)

function handleFile(e) {
  selectedFile.value = e.target.files[0] || null
}

function handleDrop(e) {
  selectedFile.value = e.dataTransfer.files[0] || null
}

async function upload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', selectedFile.value)
    form.append('entity_type', entityType.value)
    form.append('column_mapping', '{}')
    const res = await api.post('/v1/migration/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    preview.value = res.data
    step.value = 'preview'
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || e.message
    step.value = 'error'
  } finally {
    uploading.value = false
  }
}

async function commit() {
  committing.value = true
  try {
    const res = await api.post('/v1/migration/commit', { batch_id: preview.value.batch_id })
    result.value = res.data
    step.value = 'done'
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || e.message
    step.value = 'error'
  } finally {
    committing.value = false
  }
}

function reset() {
  step.value = 'upload'
  selectedFile.value = null
  preview.value = {}
  result.value = {}
  errorMsg.value = ''
  if (fileInput.value) fileInput.value.value = ''
}
</script>

<style scoped>
.card-body { padding: 24px; }
.upload-zone { border: 2px dashed #d0d5dd; border-radius: 8px; padding: 40px; text-align: center; margin-bottom: 16px; cursor: pointer; transition: border-color .2s; }
.upload-zone:hover { border-color: #3b82f6; }
.upload-icon { font-size: 48px; color: #9ca3af; margin-bottom: 8px; }
.file-name { margin-top: 8px; font-size: 13px; color: #3b82f6; font-weight: 600; }
.preview-summary { display: flex; gap: 24px; margin-bottom: 20px; }
.stat { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px 20px; text-align: center; flex: 1; }
.stat-label { display: block; font-size: 11px; text-transform: uppercase; color: #6b7280; margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.stat-ok { color: #16a34a; }
.stat-err { color: #dc2626; }
.error-list { margin-bottom: 16px; }
.error-list h4 { font-size: 13px; color: #dc2626; margin: 0 0 8px; }
.error-row { font-size: 12px; color: #991b1b; background: #fef2f2; padding: 6px 10px; border-radius: 4px; margin-bottom: 4px; }
.sample-section { margin-bottom: 20px; }
.sample-section h4 { font-size: 13px; margin: 0 0 8px; color: #374151; }
.table-sm th, .table-sm td { padding: 6px 10px; font-size: 12px; }
.preview-actions { display: flex; gap: 12px; justify-content: flex-end; }
.text-center { text-align: center; }
.done-icon { font-size: 56px; color: #16a34a; margin-bottom: 12px; }
.error-icon { font-size: 56px; color: #dc2626; margin-bottom: 12px; }
.btn-sm { padding: 6px 16px; font-size: 13px; }
</style>

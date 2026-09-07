<template>
  <div :dir="dir">
    <header class="flex justify-between items-center mb-6 flex-wrap gap-3">
      <div>
        <button class="btn-link" @click="$router.push('/accounting/einvoicing')">&larr; {{ t('back-to-einvoicing', 'Back to E-Invoicing') }}</button>
        <h1 class="page-title">{{ t('fiscal-profiles-title', 'Fiscal Authority Profiles & Tax Credentials') }}</h1>
        <p class="page-subtitle">{{ t('fiscal-profiles-subtitle', 'Configure ZATCA, European e-invoicing, and regional tax authority credentials and environments.') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-outline" @click="openKeypairModal" :disabled="generatingKeypair">
          <span class="material-symbols-outlined icon-xs">key</span>
          {{ generatingKeypair ? t('generating', 'Generating...') : t('generate-keypair', 'Generate Keypair') }}
        </button>
        <button class="btn-primary" @click="openAddModal">
          <span class="material-symbols-outlined icon-xs">add</span>
          {{ t('new-profile', 'New Fiscal Profile') }}
        </button>
      </div>
    </header>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!profiles.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">account_balance</span>
      <p>{{ t('no-fiscal-profiles', 'No fiscal authority profiles configured yet.') }}</p>
      <button class="btn-primary mt-3" @click="openAddModal">
        <span class="material-symbols-outlined icon-xs">add</span>
        {{ t('create-first-profile', 'Configure Tax Profile') }}
      </button>
    </div>

    <div v-else class="profiles-grid">
      <div
        v-for="prof in profiles"
        :key="prof.id"
        class="profile-card"
        :class="{ 'profile-default': prof.is_default }"
      >
        <div class="profile-card-header">
          <div class="flex items-center gap-3">
            <div class="authority-icon">
              <span class="material-symbols-outlined">account_balance</span>
            </div>
            <div>
              <h3 class="profile-name">{{ prof.profile_name || prof.authority_name || prof.seller_name || 'Fiscal Profile' }}</h3>
              <span class="country-badge">{{ prof.country_code || 'SA' }} &bull; {{ prof.authority_code || prof.tax_scheme || 'VAT' }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="prof.is_default" class="badge badge-default">{{ t('default', 'Default') }}</span>
            <span class="badge" :class="envBadge(prof.environment)">{{ prof.environment || 'Sandbox' }}</span>
          </div>
        </div>

        <div class="profile-card-body">
          <div class="info-row">
            <span class="info-label">{{ t('vat-number', 'VAT / Tax ID') }}:</span>
            <span class="cell-mono font-bold">{{ prof.tax_id || prof.vat_number || prof.seller_vat_number || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('endpoint-url', 'Endpoint URL') }}:</span>
            <span class="cell-mono text-xs text-muted url-truncate" :title="prof.api_base_url || prof.endpoint_url || '-'">{{ prof.api_base_url || prof.endpoint_url || 'Default Standard API' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('certificate-csid', 'CSID / Certificate') }}:</span>
            <span class="badge" :class="(prof.certificate || prof.csid) ? 'badge-active' : 'badge-inactive'">
              <span class="material-symbols-outlined icon-xs">{{ (prof.certificate || prof.csid) ? 'verified_user' : 'warning' }}</span>
              {{ (prof.certificate || prof.csid) ? t('installed', 'Installed') : t('not-installed', 'Not Configured') }}
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('private-key', 'Private Key') }}:</span>
            <span class="badge" :class="prof.private_key ? 'badge-active' : 'badge-inactive'">
              <span class="material-symbols-outlined icon-xs">{{ prof.private_key ? 'key' : 'key_off' }}</span>
              {{ prof.private_key ? t('secured', 'Secured') : t('missing', 'Missing') }}
            </span>
          </div>
        </div>

        <div class="profile-card-actions">
          <button class="btn-outline btn-sm" @click="editProfile(prof)">
            <span class="material-symbols-outlined icon-xs">edit</span>
            {{ t('edit', 'Edit') }}
          </button>
          <button class="btn-icon btn-icon-danger" @click="confirmDeleteProfile(prof)" :title="t('delete', 'Delete')">
            <span class="material-symbols-outlined icon-xs">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Create / Edit Profile Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content modal-lg" :dir="dir">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-profile', 'Edit Fiscal Authority Profile') : t('new-profile', 'New Fiscal Profile') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('profile-name', 'Profile Name / Label') }} <span class="required">*</span></label>
              <input type="text" v-model="form.profile_name" class="form-input" placeholder="e.g. Saudi ZATCA Production Profile" required />
            </div>
            <div class="form-group">
              <label>{{ t('seller-name', 'Legal Seller Name (English)') }} <span class="required">*</span></label>
              <input type="text" v-model="form.seller_name" class="form-input" placeholder="e.g. Nova Global Trading LLC" required />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('seller-name-ar', 'Legal Seller Name (Arabic)') }}</label>
              <input type="text" v-model="form.seller_name_ar" class="form-input" placeholder="شركة نوفا للتجارة العامة" />
            </div>
            <div class="form-group">
              <label>{{ t('tax-id', 'VAT / Tax Registration Number') }} <span class="required">*</span></label>
              <input type="text" v-model="form.tax_id" class="form-input" placeholder="e.g. 300012345600003" required />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('country-code', 'Country Code (ISO 2-letter)') }} <span class="required">*</span></label>
              <input type="text" v-model="form.country_code" class="form-input" maxlength="2" placeholder="SA, DE, FR, NL" required />
            </div>
            <div class="form-group">
              <label>{{ t('authority-code', 'Authority Provider Code') }}</label>
              <input type="text" v-model="form.authority_code" class="form-input" placeholder="ZATCA, PEPPOL, NTS" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('environment', 'Environment') }} <span class="required">*</span></label>
              <select v-model="form.environment" class="form-input">
                <option value="Sandbox">Sandbox</option>
                <option value="Simulation">Simulation</option>
                <option value="Production">Production</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('api-base-url', 'API Base URL / Endpoint (Optional)') }}</label>
              <input type="text" v-model="form.api_base_url" class="form-input" placeholder="https://gw.zatca.gov.sa/..." />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('api-secret', 'CSID Secret / OTP / API Secret') }}</label>
              <input type="password" v-model="form.api_secret" class="form-input" placeholder="••••••••" />
            </div>
            <div class="form-group">
              <label>{{ t('auth-token', 'Bearer Auth Token') }}</label>
              <input type="password" v-model="form.auth_token" class="form-input" placeholder="Optional active bearer token" />
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('certificate-pem', 'Cryptographic Stamp / CSID Certificate (PEM / Base64)') }}</label>
            <textarea v-model="form.certificate" class="form-input textarea" rows="3" placeholder="-----BEGIN CERTIFICATE----- ..."></textarea>
          </div>

          <div class="form-group">
            <label>{{ t('private-key-pem', 'ECDSA / RSA Private Key (PEM format)') }}</label>
            <textarea v-model="form.private_key" class="form-input textarea" rows="3" placeholder="-----BEGIN EC PRIVATE KEY----- ..."></textarea>
          </div>

          <div class="form-row flex items-center gap-4">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_active" />
              <span>{{ t('is-active', 'Active Profile') }}</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.is_default" />
              <span>{{ t('is-default', 'Set as Default Profile') }}</span>
            </label>
          </div>

          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveProfile">
              <span v-if="saving" class="material-symbols-outlined spin icon-xs">progress_activity</span>
              <span v-else class="material-symbols-outlined icon-xs">check</span>
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save Profile') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Keypair Generator Modal -->
    <div v-if="showKeypairModal" class="modal-overlay" @click.self="showKeypairModal = false">
      <div class="modal-content modal-lg" :dir="dir">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">key</span>
            <h3>{{ t('keypair-generator-title', 'ECDSA secp256k1 Keypair Generator') }}</h3>
          </div>
          <button class="btn-icon" @click="showKeypairModal = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-muted mb-3">
            {{ t('keypair-description', 'Cryptographically secure SECP256k1 ECDSA private key and public key generated for ZATCA Phase 2 signing.') }}
          </p>
          <div v-if="generatedKeypair" class="keypair-results">
            <div class="form-group">
              <label>{{ t('private-key', 'Private Key (PEM format - Keep Secret!)') }}</label>
              <textarea class="form-input textarea key-textarea" rows="5" readonly :value="generatedKeypair.private_key"></textarea>
            </div>
            <div class="form-group">
              <label>{{ t('public-key', 'Public Key (PEM format)') }}</label>
              <textarea class="form-input textarea key-textarea" rows="4" readonly :value="generatedKeypair.public_key"></textarea>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="showKeypairModal = false">{{ t('close', 'Close') }}</button>
            <button class="btn-primary" @click="useGeneratedKeypair">{{ t('use-in-new-profile', 'Use in New Profile') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const profiles = ref([])
const showModal = ref(false)
const editing = ref(false)
const editId = ref(null)

const showKeypairModal = ref(false)
const generatingKeypair = ref(false)
const generatedKeypair = ref(null)

const form = ref({
  profile_name: 'Main Store ZATCA',
  authority_code: 'ZATCA',
  seller_name: '',
  seller_name_ar: '',
  tax_id: '',
  country_code: 'SA',
  environment: 'Sandbox',
  api_base_url: '',
  api_secret: '',
  auth_token: '',
  certificate: '',
  private_key: '',
  is_active: true,
  is_default: false,
})

function envBadge(env) {
  if (env === 'Production') return 'badge-danger'
  if (env === 'Simulation') return 'badge-warning'
  return 'badge-info'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0125I/')
    profiles.value = res.data || []
  } catch {
    error.value = t('failed-load-profiles', 'Failed to load fiscal profiles')
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  editing.value = false
  editId.value = null
  form.value = {
    profile_name: '',
    authority_code: 'ZATCA',
    seller_name: '',
    seller_name_ar: '',
    tax_id: '',
    country_code: 'SA',
    environment: 'Sandbox',
    api_base_url: '',
    api_secret: '',
    auth_token: '',
    certificate: '',
    private_key: '',
    is_active: true,
    is_default: profiles.value.length === 0,
  }
  showModal.value = true
}

function editProfile(prof) {
  editing.value = true
  editId.value = prof.id
  form.value = {
    profile_name: prof.profile_name || prof.authority_name || '',
    authority_code: prof.authority_code || 'ZATCA',
    seller_name: prof.seller_name || '',
    seller_name_ar: prof.seller_name_ar || '',
    tax_id: prof.tax_id || prof.vat_number || '',
    country_code: prof.country_code || 'SA',
    environment: prof.environment || 'Sandbox',
    api_base_url: prof.api_base_url || prof.endpoint_url || '',
    api_secret: prof.api_secret || '',
    auth_token: prof.auth_token || '',
    certificate: prof.certificate || '',
    private_key: prof.private_key || '',
    is_active: prof.is_active ?? true,
    is_default: prof.is_default ?? false,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function openKeypairModal() {
  generatingKeypair.value = true
  try {
    const res = await api.post('/T0125I/generate-keypair')
    generatedKeypair.value = res.data || {}
    showKeypairModal.value = true
  } catch (err) {
    toast(err.response?.data?.detail || 'Failed to generate keypair', 'error')
  } finally {
    generatingKeypair.value = false
  }
}

function useGeneratedKeypair() {
  if (generatedKeypair.value) {
    openAddModal()
    form.value.private_key = generatedKeypair.value.private_key || ''
  }
  showKeypairModal.value = false
}

async function saveProfile() {
  if (!form.value.profile_name || !form.value.seller_name || !form.value.tax_id) {
    toast('Please fill all required fields', 'error')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.put(`/T0125I/${editId.value}`, form.value)
      toast('Fiscal profile updated', 'success')
    } else {
      await api.post('/T0125I/', form.value)
      toast('Fiscal profile created', 'success')
    }
    closeModal()
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || 'Failed to save fiscal profile', 'error')
  } finally {
    saving.value = false
  }
}

async function confirmDeleteProfile(prof) {
  if (!confirm(`Delete profile for ${prof.profile_name || prof.authority_name || 'profile'}?`)) return
  try {
    await api.delete(`/T0125I/${prof.id}`)
    toast('Profile deleted', 'success')
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || 'Failed to delete profile', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.btn-link { background: none; border: none; color: #5d3fd3; font-size: 13px; cursor: pointer; padding: 0; margin-bottom: 6px; }
.btn-link:hover { text-decoration: underline; }

.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.profiles-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.profile-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s; }
.profile-card:hover { border-color: #5d3fd3; box-shadow: 0 4px 12px rgba(93, 63, 211, 0.08); }
.profile-default { border-color: #8b5cf6; background: #faf8ff; }

.profile-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.authority-icon { width: 38px; height: 38px; background: #ede9fe; color: #7c3aed; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.profile-name { font-size: 15px; font-weight: 700; color: #1e293b; margin: 0; }
.country-badge { font-size: 11px; color: #64748b; }

.profile-card-body { border-top: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9; padding: 10px 0; margin-bottom: 14px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; }
.info-label { color: #64748b; font-weight: 500; }
.url-truncate { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.profile-card-actions { display: flex; justify-content: space-between; align-items: center; }
.btn-sm { padding: 6px 12px; font-size: 12px; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-default { background: #ede9fe; color: #7c3aed; border: 1px solid #ddd6fe; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: #f1f5f9; color: #94a3b8; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-danger { background: #fee2e2; color: #dc2626; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #64748b; }
.btn-icon:hover { background: #f0f0f0; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.icon-xs { font-size: 15px !important; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Modals */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 620px; max-width: 92vw; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-body { padding: 20px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
.textarea { font-family: monospace; font-size: 11px; resize: vertical; }
.checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #333; cursor: pointer; }
.required { color: #dc2626; }
.cell-mono { font-family: monospace; font-size: 12px; }
.keypair-results { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
</style>

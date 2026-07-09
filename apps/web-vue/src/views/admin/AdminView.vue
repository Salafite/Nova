<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('admin-title') }}</h1>
        <p class="page-subtitle">{{ t('admin-sub') }}</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span> {{ t('new-user') }}
        </button>
        <button class="btn-outline" @click="openInvite">
          <span class="material-symbols-outlined">person_add</span> {{ t('invite-user') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">group</span>
      <p>{{ t('no-records') }}</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('admin-username') }}</th>
              <th>{{ t('admin-full-name') }}</th>
              <th>{{ t('admin-email') }}</th>
              <th>{{ t('admin-role') }}</th>
              <th class="text-center">{{ t('status') }}</th>
              <th>{{ t('admin-last-login') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td class="cell-name">{{ item.username }}</td>
              <td>{{ item.full_name || '-' }}</td>
              <td class="cell-mono">{{ item.email || '-' }}</td>
              <td>
                <span :class="'role-badge role-' + item.role.toLowerCase()">{{ item.role }}</span>
              </td>
              <td class="text-center">
                <span :class="item.status === 'Active' ? 'badge badge-active' : item.status === 'Invited' ? 'badge badge-invited' : 'badge badge-inactive'">
                  {{ item.status === 'Active' ? t('active') : item.status === 'Invited' ? 'Invited' : t('inactive') }}
                </span>
              </td>
              <td class="cell-mono">{{ item.last_login ? formatDate(item.last_login) : '-' }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')" :aria-label="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')" :aria-label="t('delete')">
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
          <h3>{{ editing ? t('edit-user') : t('new-user') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('admin-username') }} <span class="required">*</span></label>
              <input type="text" v-model="form.username" required class="form-input" maxlength="50" />
            </div>
            <div class="form-group">
              <label>{{ t('admin-full-name') }}</label>
              <input type="text" v-model="form.full_name" class="form-input" maxlength="200" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('admin-email') }}</label>
              <input type="email" v-model="form.email" class="form-input" maxlength="200" />
            </div>
            <div class="form-group">
              <label>{{ t('admin-role') }} <span class="required">*</span></label>
              <select v-model="form.role" class="form-input">
                <option value="Admin">Admin</option>
                <option value="Manager">Manager</option>
                <option value="Viewer">Viewer</option>
              </select>
            </div>
          </div>
          <div class="form-row" v-if="!editing">
            <div class="form-group">
              <label>{{ t('admin-password') }} <span class="required">*</span></label>
              <input type="password" v-model="form.password_hash" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('status') }}</label>
              <select v-model="form.status" class="form-input">
                <option value="Active">{{ t('active') }}</option>
                <option value="Inactive">{{ t('inactive') }}</option>
              </select>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-outline" @click="closeModal">{{ t('cancel') }}</button>
            <button class="btn-primary" :disabled="saving" @click="saveItem">
              {{ saving ? t('saving') : t('save') }}
            </button>
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
          <p class="delete-text">{{ t('admin-delete-confirm') }} <strong>{{ deleteTarget?.username }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? t('deleting') : t('delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showInvite" class="modal-overlay" @click.self="closeInvite">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ t('invite-user') }}</h3>
          <button class="btn-icon" @click="closeInvite" aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div v-if="inviteResult" class="invite-result">
            <p class="invite-success">{{ t('invite-sent') }}</p>
            <div class="form-group">
              <label>{{ t('invite-link') }}</label>
              <div class="invite-link-box">
                <input type="text" :value="inviteResult.invite_link" readonly class="form-input" @click="$event.target.select()" />
                <button class="btn-icon" @click="copyLink" :title="t('edit')" :aria-label="t('edit')">
                  <span class="material-symbols-outlined">content_copy</span>
                </button>
              </div>
            </div>
            <div class="modal-actions">
              <button class="btn-primary" @click="closeInvite">{{ t('close') }}</button>
            </div>
          </div>
          <div v-else>
            <div class="form-group">
              <label>{{ t('invite-email') }} <span class="required">*</span></label>
              <input type="email" v-model="inviteForm.email" class="form-input" required />
            </div>
            <div class="form-group">
              <label>{{ t('invite-role') }} <span class="required">*</span></label>
              <select v-model="inviteForm.role" class="form-input">
                <option value="Sales Rep">Sales Rep</option>
                <option value="Salesman">Salesman</option>
                <option value="Warehouse">Warehouse</option>
                <option value="Accountant">Accountant</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('invite-full-name') }}</label>
              <input type="text" v-model="inviteForm.full_name" class="form-input" />
            </div>
            <div v-if="inviteError" class="alert error">{{ inviteError }}</div>
            <div class="modal-actions">
              <button class="btn-outline" @click="closeInvite">{{ t('cancel') }}</button>
              <button class="btn-primary" :disabled="inviting" @click="sendInvite">
                {{ inviting ? t('invite-sending') : t('invite-user') }}
              </button>
            </div>
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
const error = ref('')
const items = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const form = ref({ username: '', password_hash: '', full_name: '', email: '', role: 'Viewer', status: 'Active' })
const editId = ref(null)
const showInvite = ref(false)
const inviting = ref(false)
const inviteError = ref('')
const inviteResult = ref(null)
const inviteForm = ref({ email: '', role: 'Sales Rep', full_name: '' })

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0021I/')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = false
  editId.value = null
  form.value = { username: '', password_hash: '', full_name: '', email: '', role: 'Viewer', status: 'Active' }
  showModal.value = true
}

function editItem(item) {
  editing.value = true
  editId.value = item.id
  form.value = {
    username: item.username,
    password_hash: '',
    full_name: item.full_name || '',
    email: item.email || '',
    role: item.role,
    status: item.status,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function saveItem() {
  if (!form.value.username) return
  if (!editing.value && !form.value.password_hash) return
  saving.value = true
  try {
    const payload = {
      ...form.value,
      full_name: form.value.full_name || null,
      email: form.value.email || null,
    }
    if (!editing.value) {
      await api.post('/T0021I/', payload)
      toast('User ' + t('saved-ok'), 'success')
    } else {
      const update = { ...payload }
      if (!update.password_hash) delete update.password_hash
      await api.put(`/T0021I/${editId.value}`, update)
      toast('User ' + t('saved-ok'), 'success')
    }
    closeModal()
    await load()
  } catch {
    toast(t('failed-save') + ' User', 'error')
  } finally {
    saving.value = false
  }
}

function deleteItem(item) {
  deleteTarget.value = item
  showDelete.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    await api.delete(`/T0021I/${deleteTarget.value.id}`)
    items.value = items.value.filter(i => i.id !== deleteTarget.value.id)
    toast('User deleted', 'success')
    showDelete.value = false
  } catch {
    toast(t('failed-save') + ' User', 'error')
  } finally {
    deleting.value = false
  }
}

function openInvite() {
  inviteForm.value = { email: '', role: 'Sales Rep', full_name: '' }
  inviteResult.value = null
  inviteError.value = ''
  showInvite.value = true
}

function closeInvite() {
  showInvite.value = false
  inviteResult.value = null
  inviteError.value = ''
}

async function sendInvite() {
  if (!inviteForm.value.email) return
  inviting.value = true
  inviteError.value = ''
  try {
    const res = await api.post('/auth/invite', {
      email: inviteForm.value.email,
      role: inviteForm.value.role,
      full_name: inviteForm.value.full_name || null,
    })
    inviteResult.value = res.data
    await load()
  } catch {
    inviteError.value = t('invite-failed')
  } finally {
    inviting.value = false
  }
}

async function copyLink() {
  if (!inviteResult.value) return
  try {
    await navigator.clipboard.writeText(window.location.origin + '/#' + inviteResult.value.invite_link)
    toast(t('invite-copied'), 'success')
  } catch {
    const input = document.querySelector('.invite-link-box input')
    if (input) { input.select(); document.execCommand('copy') }
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f9fafb; padding: 10px 14px; text-align: left; font-weight: 600; color: #555; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e0e0e0; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #fafaff; }
.cell-name { font-weight: 600; color: #1a1a2e; }
.cell-mono { font-family: monospace; font-size: 12px; color: #888; }
.text-center { text-align: center; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-invited { background: #fef3c7; color: #b45309; }
.badge-inactive { background: #f3f4f6; color: #888; }

.role-badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.role-admin { background: #ede9fe; color: #7c3aed; }
.role-manager { background: #dbeafe; color: #2563eb; }
.role-viewer { background: #f3f4f6; color: #6b7280; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #5d3fd3; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: #f5f5f5; }
.btn-danger { display: inline-flex; align-items: center; gap: 6px; background: #dc2626; color: #fff; padding: 8px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: #888; }
.btn-icon:hover { background: #f0f0f0; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eee; }
.modal-header h3 { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.delete-text { font-size: 14px; color: #555; margin: 0; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #444; margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
.required { color: #dc2626; }
.invite-result { padding: 0; }
.invite-success { color: #16a34a; font-weight: 600; font-size: 14px; margin-bottom: 12px; }
.invite-link-box { display: flex; gap: 6px; align-items: center; }
.invite-link-box input { flex: 1; }
.alert { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; text-align: center; }
.alert.error { background: #fef2f2; color: #ba1a1a; border: 1px solid #fecaca; }
.flex { display: flex; }
.gap-2 { gap: 8px; }

[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .modal-header { flex-direction: row-reverse; }
</style>

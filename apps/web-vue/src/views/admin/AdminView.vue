<template>
  <div class="au-page" :dir="dir">
    <!-- Header -->
    <header class="au-header">
      <div class="au-header-left">
        <h1 class="au-title">{{ t('admin-title') }}</h1>
        <p class="au-subtitle">{{ t('admin-sub') }}</p>
      </div>
      <div class="au-header-actions">
        <div class="au-search">
          <span class="material-symbols-outlined au-search-icon">search</span>
          <input
            v-model="searchQuery"
            class="au-search-input"
            :placeholder="t('search-users')"
          />
          <kbd v-if="!searchQuery" class="au-search-hint">/</kbd>
        </div>
        <button class="btn-outline" @click="openInvite">
          <span class="material-symbols-outlined">person_add</span>
          <span class="au-btn-label">{{ t('invite-user') }}</span>
        </button>
        <button class="btn-primary" @click="openAdd">
          <span class="material-symbols-outlined">add</span>
          <span class="au-btn-label">{{ t('new-user') }}</span>
        </button>
      </div>
    </header>

    <!-- Stats bar -->
    <div class="au-stats">
      <span class="au-count">{{ t('admin-count', { count: filteredItems.length }) }}</span>
    </div>

    <!-- States -->
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filteredItems.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">
        {{ searchQuery ? 'search_off' : 'group' }}
      </span>
      <p>{{ searchQuery ? t('no-records') : t('no-records') }}</p>
    </div>

    <!-- User Roster Table -->
    <div v-else class="au-card">
      <div class="au-table-wrap">
        <table class="au-table">
          <thead>
            <tr>
              <th class="au-th-user">{{ t('admin-username') }}</th>
              <th class="au-th-role">{{ t('admin-role') }}</th>
              <th class="au-th-status">{{ t('status') }}</th>
              <th class="au-th-login">{{ t('admin-last-login') }}</th>
              <th class="au-th-prefs"></th>
              <th class="au-th-actions">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredItems"
              :key="item.id"
              :class="['au-row', { 'au-row-expanded': expandedId === item.id }]"
            >
              <!-- User identity cell (avatar + info stacked) -->
              <td class="au-cell-user">
                <div class="au-user">
                  <span class="au-avatar" :style="{ background: avatarColor(item.username) }">
                    {{ item.username.charAt(0).toUpperCase() }}
                  </span>
                  <div class="au-user-info">
                    <span class="au-user-name">{{ item.full_name || item.username }}</span>
                    <span class="au-user-username">{{ item.username }}</span>
                    <span v-if="item.email" class="au-user-email">{{ item.email }}</span>
                  </div>
                </div>
              </td>
              <!-- Role -->
              <td class="au-cell-role">
                <span :class="'au-role au-role-' + item.role.toLowerCase()">{{ item.role }}</span>
              </td>
              <!-- Status -->
              <td class="au-cell-status">
                <span :class="'au-status au-status-' + statusClass(item.status)">
                  <span class="au-status-dot"></span>
                  {{ item.status === 'Active' ? t('active') : item.status === 'Invited' ? 'Invited' : t('inactive') }}
                </span>
              </td>
              <!-- Last Login -->
              <td class="au-cell-login">
                <span class="au-login-text">{{ item.last_login ? formatDate(item.last_login) : '—' }}</span>
              </td>
              <!-- Expand prefs -->
              <td class="au-cell-prefs">
                <button
                  class="au-expand-btn"
                  :class="{ 'au-expand-open': expandedId === item.id }"
                  @click="toggleExpand(item)"
                  :aria-label="t('admin-preferences')"
                  :title="t('admin-preferences')"
                >
                  <span class="material-symbols-outlined">tune</span>
                </button>
              </td>
              <!-- Actions -->
              <td class="au-cell-actions">
                <button class="btn-icon" @click="editItem(item)" :title="t('edit')" :aria-label="t('edit')">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" :title="t('delete')" :aria-label="t('delete')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
            <!-- Expanded preference row -->
            <tr v-if="expandedId" class="au-prefs-row">
              <td :colspan="expandedColspan">
                <div class="au-prefs-panel">
                  <div class="au-prefs-header">
                    <span class="material-symbols-outlined au-prefs-icon">tune</span>
                    <span class="au-prefs-title">{{ t('admin-preferences-title') }}</span>
                    <span v-if="prefLoading" class="au-prefs-spinner">
                      <span class="material-symbols-outlined au-spin">progress_activity</span>
                      {{ t('admin-pref-loading') }}
                    </span>
                  </div>
                  <div v-if="!prefLoading" class="au-prefs-body">
                    <div class="au-prefs-grid">
                      <div class="au-pref-item">
                        <span class="au-pref-label">{{ t('admin-pref-theme') }}</span>
                        <div class="au-pref-control">
                          <div class="au-opt-group">
                            <button
                              v-for="opt in ['light', 'dark']"
                              :key="opt"
                              :class="['au-opt-btn', { active: expandedPrefs.THEME === opt }]"
                              @click="expandedPrefs.THEME = opt"
                            >{{ optionLabel(opt) }}</button>
                          </div>
                        </div>
                      </div>
                      <div class="au-pref-item">
                        <span class="au-pref-label">{{ t('admin-pref-accent') }}</span>
                        <div class="au-pref-control">
                          <div class="au-opt-group">
                            <button
                              v-for="opt in ['blue', 'purple', 'green', 'amber', 'red']"
                              :key="opt"
                              :class="['au-opt-btn', { active: expandedPrefs.ACCENT_COLOR === opt }]"
                              @click="expandedPrefs.ACCENT_COLOR = opt"
                            >{{ optionLabel(opt) }}</button>
                          </div>
                        </div>
                      </div>
                      <div class="au-pref-item">
                        <span class="au-pref-label">{{ t('admin-pref-font') }}</span>
                        <div class="au-pref-control">
                          <div class="au-opt-group">
                            <button
                              v-for="opt in ['inter', 'roboto', 'open-sans', 'system']"
                              :key="opt"
                              :class="['au-opt-btn', { active: expandedPrefs.FONT_FAMILY === opt }]"
                              @click="expandedPrefs.FONT_FAMILY = opt"
                            >{{ optionLabel(opt) }}</button>
                          </div>
                        </div>
                      </div>
                      <div class="au-pref-item">
                        <span class="au-pref-label">{{ t('admin-pref-sidebar') }}</span>
                        <div class="au-pref-control">
                          <div class="au-opt-group">
                            <button
                              v-for="opt in ['expanded', 'overlay', 'auto-hide']"
                              :key="opt"
                              :class="['au-opt-btn', { active: expandedPrefs.SIDEBAR_MODE === opt }]"
                              @click="expandedPrefs.SIDEBAR_MODE = opt"
                            >{{ optionLabel(opt) }}</button>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="au-prefs-footer">
                      <button
                        class="au-pref-save-btn"
                        :disabled="prefSaving || !prefDirty"
                        @click="savePrefs"
                      >
                        <span class="material-symbols-outlined">check</span>
                        {{ prefSaving ? t('saving') : t('admin-save-prefs') }}
                      </button>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add / Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editing ? t('edit-user') : t('new-user') }}</h3>
          <button class="btn-icon" @click="closeModal" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
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

    <!-- Delete Modal -->
    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3>{{ t('confirm-delete') }}</h3>
          <button class="btn-icon" @click="showDelete = false" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="delete-text">
            {{ t('admin-delete-confirm') }}
            <strong>{{ deleteTarget?.username }}</strong>?
          </p>
          <div class="modal-actions">
            <button class="btn-outline" @click="showDelete = false">{{ t('cancel') }}</button>
            <button class="btn-danger" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? t('deleting') : t('delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Invite Modal -->
    <div v-if="showInvite" class="modal-overlay" @click.self="closeInvite">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ t('invite-user') }}</h3>
          <button class="btn-icon" @click="closeInvite" aria-label="Close">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="inviteResult" class="invite-result">
            <p class="invite-success">{{ t('invite-sent') }}</p>
            <div class="form-group">
              <label>{{ t('invite-link') }}</label>
              <div class="invite-link-box">
                <input
                  type="text"
                  :value="inviteResult.invite_link"
                  readonly
                  class="form-input"
                  @click="$event.target.select()"
                />
                <button class="btn-icon" @click="copyLink" title="Copy" aria-label="Copy">
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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

const searchQuery = ref('')

const expandedId = ref(null)
const expandedPrefs = ref({ THEME: '', ACCENT_COLOR: '', FONT_FAMILY: '', SIDEBAR_MODE: '' })
const prefLoading = ref(false)
const prefSaving = ref(false)
const prefOriginal = ref({})

const expandedColspan = 6

const filteredItems = computed(() => {
  if (!searchQuery.value) return items.value
  const q = searchQuery.value.toLowerCase()
  return items.value.filter(item =>
    (item.username && item.username.toLowerCase().includes(q)) ||
    (item.full_name && item.full_name.toLowerCase().includes(q)) ||
    (item.email && item.email.toLowerCase().includes(q)) ||
    (item.role && item.role.toLowerCase().includes(q))
  )
})

const prefDirty = computed(() => {
  const p = expandedPrefs.value
  const o = prefOriginal.value
  return p.THEME !== o.THEME || p.ACCENT_COLOR !== o.ACCENT_COLOR ||
    p.FONT_FAMILY !== o.FONT_FAMILY || p.SIDEBAR_MODE !== o.SIDEBAR_MODE
})

const AVATAR_COLORS = [
  '#5d3fd3', '#2563eb', '#059669', '#d97706', '#dc2626',
  '#7c3aed', '#0891b2', '#65a30d', '#ca8a04', '#db2777',
]

function avatarColor(username) {
  let hash = 0
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function statusClass(status) {
  if (status === 'Active') return 'active'
  if (status === 'Invited') return 'invited'
  return 'inactive'
}

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}

function optionLabel(opt) {
  const key = `settings.option.${opt}`
  const label = t(key)
  if (label !== key) return label
  return opt.split(/[-_\s]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
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

// Search keyboard shortcut
function onKeydown(e) {
  if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
    e.preventDefault()
    const input = document.querySelector('.au-search-input')
    input?.focus()
  }
  if (e.key === 'Escape' && expandedId.value) {
    expandedId.value = null
  }
}

// Expand / collapse preference panel
async function toggleExpand(item) {
  if (expandedId.value === item.id) {
    expandedId.value = null
    return
  }
  expandedId.value = item.id
  prefLoading.value = true
  const prefs = { THEME: '', ACCENT_COLOR: '', FONT_FAMILY: '', SIDEBAR_MODE: '' }
  try {
    const res = await api.get(`/admin/users/${item.id}/preferences`)
    const server = res.data?.preferences || {}
    prefs.THEME = server.THEME || 'light'
    prefs.ACCENT_COLOR = server.ACCENT_COLOR || 'purple'
    prefs.FONT_FAMILY = server.FONT_FAMILY || 'inter'
    prefs.SIDEBAR_MODE = server.SIDEBAR_MODE || 'expanded'
  } catch {
    toast(t('pref-load-failed'), 'error')
  }
  expandedPrefs.value = { ...prefs }
  prefOriginal.value = { ...prefs }
  prefLoading.value = false
}

async function savePrefs() {
  if (!expandedId.value) return
  prefSaving.value = true
  const lowerPrefs = {}
  for (const [k, v] of Object.entries(expandedPrefs.value)) {
    lowerPrefs[k] = String(v).toLowerCase()
  }
  try {
    await api.put(`/admin/users/${expandedId.value}/preferences`, {
      preferences: lowerPrefs,
    })
    prefOriginal.value = { ...expandedPrefs.value }
    toast(t('pref-saved'), 'success')
  } catch {
    toast(t('pref-save-failed'), 'error')
  } finally {
    prefSaving.value = false
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
    const payload = { ...form.value, full_name: form.value.full_name || null, email: form.value.email || null }
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
    await navigator.clipboard.writeText(window.location.origin + inviteResult.value.invite_link)
    toast(t('invite-copied'), 'success')
  } catch {
    const input = document.querySelector('.invite-link-box input')
    if (input) { input.select(); document.execCommand('copy') }
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  load()
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/* ── Page ── */
.au-page {
  max-width: 1200px;
  margin: 0 auto;
}

/* ── Header ── */
.au-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.au-header-left { display: flex; flex-direction: column; gap: 2px; }
.au-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0; }
.au-subtitle { font-size: 13px; color: var(--text-muted); margin: 0; }
.au-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* ── Search ── */
.au-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-input);
  border-radius: 8px;
  padding: 0 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.au-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--bg-primary-faded);
}
.au-search-icon { font-size: 18px; color: var(--text-faint); flex-shrink: 0; }
.au-search-input {
  height: 40px;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  width: 180px;
}
.au-search-input::placeholder { color: var(--text-faint); }
.au-search-hint {
  font-size: 11px;
  color: var(--text-faint);
  background: var(--bg-body);
  border: 1px solid var(--border-light);
  border-radius: 4px;
  padding: 1px 6px;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}

/* ── Stats ── */
.au-stats {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.au-count {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

/* ── Table Card ── */
.au-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
}
.au-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; overscroll-behavior-x: contain; }

/* ── Table ── */
.au-table { width: 100%; border-collapse: collapse; }
.au-table th {
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-surface-low);
  border-bottom: 1px solid var(--border-default);
  text-align: left;
  white-space: nowrap;
}
.au-table td { padding: 10px 16px; border-bottom: 1px solid var(--border-light); }
.au-table tbody tr:not(.au-prefs-row):hover td { background: var(--bg-surface-hover); }

.au-th-user { min-width: 220px; }
.au-th-role { width: 100px; }
.au-th-status { width: 90px; }
.au-th-login { width: 110px; }
.au-th-prefs { width: 48px; }
.au-th-actions { width: 80px; }

/* ── User Cell ── */
.au-cell-user { padding: 8px 16px !important; }
.au-user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.au-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  line-height: 1;
}
.au-user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.au-user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.au-user-username {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.au-user-email {
  font-size: 11px;
  color: var(--text-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Role Badge ── */
.au-role {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.au-role-admin { background: var(--bg-primary-faded); color: var(--color-primary); }
.au-role-manager { background: #dbeafe; color: #2563eb; }
.au-role-viewer { background: var(--bg-surface-hover); color: var(--text-muted); }

/* ── Status ── */
.au-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
}
.au-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.au-status-active .au-status-dot { background: var(--color-success); }
.au-status-active { color: var(--color-success); }
.au-status-invited .au-status-dot { background: #d97706; }
.au-status-invited { color: #d97706; }
.au-status-inactive .au-status-dot { background: var(--text-faint); }
.au-status-inactive { color: var(--text-faint); }

/* ── Login ── */
.au-login-text { font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

/* ── Expand Button ── */
.au-cell-prefs { text-align: center; padding: 0 !important; }
.au-expand-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: var(--text-faint);
  transition: all 0.2s;
}
.au-expand-btn:hover {
  background: var(--bg-primary-faded);
  color: var(--color-primary);
}
.au-expand-btn .material-symbols-outlined {
  font-size: 18px;
  transition: transform 0.25s ease;
}
.au-expand-open .material-symbols-outlined {
  transform: rotate(90deg);
}

/* ── Expanded Preference Panel ── */
.au-prefs-row td {
  padding: 0 !important;
  background: var(--bg-surface-low);
  border-bottom: 1px solid var(--border-default);
}
.au-prefs-panel {
  padding: 16px 24px;
  animation: au-slideIn 0.2s ease-out;
}
@keyframes au-slideIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .au-prefs-panel { animation: none; }
}
.au-prefs-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.au-prefs-icon { font-size: 18px; color: var(--color-primary); }
.au-prefs-title { font-size: 13px; font-weight: 600; color: var(--text-primary); flex: 1; }
.au-prefs-spinner {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
.au-spin { animation: au-spin 1s linear infinite; font-size: 16px; }
@keyframes au-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .au-spin { animation: none; }
}

.au-prefs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.au-pref-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.au-pref-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

/* ── Option Group ── */
.au-opt-group {
  display: flex;
  gap: 3px;
  background: var(--bg-body);
  padding: 3px;
  border-radius: 8px;
  flex-wrap: wrap;
}
.au-opt-btn {
  padding: 5px 10px;
  border: none;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
  text-transform: capitalize;
}
.au-opt-btn:hover { color: var(--text-primary); }
.au-opt-btn.active {
  background: var(--bg-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.au-prefs-footer {
  display: flex;
  justify-content: flex-end;
}
.au-pref-save-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-primary);
  color: #fff;
  transition: background 0.15s, opacity 0.15s;
  font-family: inherit;
}
.au-pref-save-btn:hover { background: var(--color-primary-hover); }
.au-pref-save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.au-pref-save-btn .material-symbols-outlined { font-size: 15px; }

/* ── Actions ── */
.au-cell-actions { text-align: center; white-space: nowrap; }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-light); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
select.form-input { appearance: auto; }
.required { color: var(--color-error); }

.delete-text { font-size: 14px; color: var(--text-muted); margin: 0; }

.invite-result { padding: 0; }
.invite-success { color: var(--color-success); font-weight: 600; font-size: 14px; margin-bottom: 12px; }
.invite-link-box { display: flex; gap: 6px; align-items: center; }
.invite-link-box input { flex: 1; }
.alert { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; text-align: center; }
.alert.error { background: #fef2f2; color: #ba1a1a; border: 1px solid #fecaca; }

/* ── RTL ── */
[dir="rtl"] .au-table th { text-align: right; }
[dir="rtl"] .au-table td { text-align: right; }
[dir="rtl"] .au-user { flex-direction: row-reverse; }
[dir="rtl"] .au-header { flex-direction: row-reverse; }
[dir="rtl"] .au-header-actions { flex-direction: row-reverse; }
[dir="rtl"] .au-prefs-header { flex-direction: row-reverse; }
[dir="rtl"] .au-prefs-footer { justify-content: flex-start; }

/* ── Responsive ── */
@media (max-width: 1023px) {
  .au-title { font-size: 18px; }
  .au-subtitle { font-size: 12px; }
}

@media (max-width: 767px) {
  .au-header { flex-direction: column; gap: 12px; }
  .au-header-left { width: 100%; }
  .au-header-actions { width: 100%; }
  .au-search { flex: 1; min-width: 0; }
  .au-search-input { width: 100%; }
  .au-card { border-radius: 0; margin: -16px; border-left: none; border-right: none; }

  .au-table th, .au-table td { white-space: nowrap; }
  .au-th-user { min-width: 180px; }
  .au-th-login { display: none; }
  .au-cell-login { display: none; }

  .au-prefs-panel { padding: 12px 16px; }
  .au-prefs-grid { grid-template-columns: 1fr; gap: 10px; }

  .btn-primary, .btn-outline { justify-content: center; min-height: 44px; }
  .au-btn-label { display: none; }

  .form-row { grid-template-columns: 1fr; gap: 10px; }
  .modal-content { width: 100% !important; max-width: 100% !important; max-height: 100vh !important; border-radius: 0 !important; }
  .modal-body { padding: 16px !important; }

  [dir="rtl"] .au-header { flex-direction: column-reverse; }
}
</style>

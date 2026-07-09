<template>
  <div :dir="dir">
    <div class="page-header flex-wrap">
      <div>
        <h1 class="page-title">Notifications</h1>
        <p class="page-subtitle">View and manage system notifications</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" :disabled="!unreadCount || saving" @click="markAllRead">
          <span class="material-symbols-outlined">mark_email_read</span>
          Mark All Read
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num">{{ items.length }}</div>
        <div class="stat-lbl">Total</div>
      </div>
      <div class="stat-card">
        <div class="stat-num unread">{{ unreadCount }}</div>
        <div class="stat-lbl">Unread</div>
      </div>
      <div class="stat-card">
        <div class="stat-num read">{{ readCount }}</div>
        <div class="stat-lbl">Read</div>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">notifications_none</span>
      <p>No notifications found</p>
    </div>

    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="col-status">Status</th>
              <th class="col-type">Type</th>
              <th class="col-title">Title</th>
              <th class="col-message">Message</th>
              <th class="col-date">Date</th>
              <th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id" :class="{ 'row-unread': !item.is_read, 'row-read': item.is_read }">
              <td class="col-status">
                <span :class="item.is_read ? 'badge badge-read' : 'badge badge-unread'">
                  {{ item.is_read ? 'Read' : 'New' }}
                </span>
              </td>
              <td class="col-type">
                <span :class="['badge', typeBadgeClass(item.notification_type)]">
                  {{ item.notification_type }}
                </span>
              </td>
              <td class="col-title">{{ item.title }}</td>
              <td class="col-message">{{ item.message || '-' }}</td>
              <td class="col-date">{{ formatDate(item.created_at) }}</td>
              <td class="col-actions">
                <button v-if="!item.is_read" class="btn-icon" @click="markRead(item)" title="Mark as read">
                  <span class="material-symbols-outlined">mark_email_read</span>
                </button>
                <button class="btn-icon btn-icon-danger" @click="deleteItem(item)" title="Delete">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.title" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useAuthStore } from '../../stores/auth.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const auth = useAuthStore()

const loading = ref(true)
const error = ref('')
const items = ref([])
const saving = ref(false)
const confirmTarget = ref(null)

const unreadCount = computed(() => items.value.filter(n => !n.is_read).length)
const readCount = computed(() => items.value.filter(n => n.is_read).length)

function typeBadgeClass(type) {
  const map = { Info: 'badge-info', Warning: 'badge-warning', Error: 'badge-error', Success: 'badge-success' }
  return map[type] || 'badge-info'
}

function formatDate(dt) {
  if (!dt) return '-'
  const d = new Date(dt)
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/T0098I/')
    items.value = res.data || []
  } catch {
    error.value = 'Failed to load notifications.'
  } finally {
    loading.value = false
  }
}

async function markRead(item) {
  try {
    await api.put(`/T0098I/${item.id}/read`)
    item.is_read = true
    toast('Notification marked as read', 'success')
  } catch {
    toast('Failed to mark as read', 'error')
  }
}

async function markAllRead() {
  saving.value = true
  try {
    const userId = auth.user?.id
    if (!userId) { toast('User not identified', 'error'); return }
    await api.put(`/T0098I/read-all/${userId}`)
    items.value.forEach(n => { n.is_read = true })
    toast('All notifications marked as read', 'success')
  } catch {
    toast('Failed to mark all as read', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) {
  confirmTarget.value = null
  try {
    await api.delete(`/T0098I/${item.id}`)
    items.value = items.value.filter(i => i.id !== item.id)
    toast('Notification deleted', 'success')
  } catch {
    toast('Failed to delete notification', 'error')
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.flex-wrap { flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; text-align: center; }
.stat-num { font-size: 24px; font-weight: 700; color: #5d3fd3; }
.stat-num.unread { color: #e65100; }
.stat-num.read { color: #16a34a; }
.stat-lbl { font-size: 12px; color: #666; margin-top: 2px; }

.loading-state, .error-state, .empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }
.error-state p { margin-bottom: 16px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 16px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.row-unread { background: #fafcff; }
.row-unread td { font-weight: 500; }
.row-read td { color: #888; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.badge-unread { background: #e3f2fd; color: #1565c0; }
.badge-read { background: #f5f5f5; color: #999; }
.badge-info { background: #e3f2fd; color: #1565c0; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-error { background: #fce4ec; color: #c62828; }
.badge-success { background: #e8f5e9; color: #2e7d32; }

.col-status, .col-type { width: 80px; }
.col-date { width: 160px; white-space: nowrap; }
.col-actions { width: 100px; text-align: center; white-space: nowrap; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary .material-symbols-outlined { font-size: 18px; }

.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: #333; padding: 8px 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-outline:hover:not(:disabled) { background: #f5f5f5; border-color: #5d3fd3; color: #5d3fd3; }
.btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline .material-symbols-outlined { font-size: 18px; }

.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; transition: all 0.15s; color: #666; }
.btn-icon:hover { background: #f0f0f4; color: #5d3fd3; }
.btn-icon-danger:hover { background: #fce4ec; color: #c62828; }
.btn-icon .material-symbols-outlined { font-size: 18px; }

[dir="rtl"] .page-header { flex-direction: row-reverse; }
[dir="rtl"] .data-table th { text-align: right; }
[dir="rtl"] .data-table td { text-align: right; }
[dir="rtl"] .col-actions { text-align: left; }
</style>

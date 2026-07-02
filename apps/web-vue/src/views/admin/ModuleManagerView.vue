<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('module-manager', 'Module Manager') }}</h2>
        <p class="page-subtitle">{{ t('module-sub', 'Install, enable, or disable Nova ERP modules') }}</p>
      </div>
      <button class="btn-primary" @click="scanModules">
        <span class="material-symbols-outlined">search</span> {{ t('scan-modules', 'Scan for Modules') }}
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else>
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ installed.length }}</div>
          <div class="stat-label">{{ t('installed') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value active-color">{{ activeCount }}</div>
          <div class="stat-label">{{ t('active') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value danger-color">{{ available.length }}</div>
          <div class="stat-label">{{ t('available', 'Available') }}</div>
        </div>
      </div>

      <div class="data-card mb-6">
        <div class="data-card-header">{{ t('installed-modules', 'Installed Modules') }}</div>
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('module') }}</th>
              <th>{{ t('version') }}</th>
              <th>{{ t('category') }}</th>
              <th class="text-center">{{ t('status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in installed" :key="m.id">
              <td>
                <span class="module-name">{{ m.name }}</span>
                <span v-if="m.is_core" class="core-badge">core</span>
              </td>
              <td><span class="mono">{{ m.version }}</span></td>
              <td>{{ m.category || '-' }}</td>
              <td class="text-center">
                <span v-if="m.is_active" class="badge badge-active">{{ t('active') }}</span>
                <span v-else class="badge badge-disabled">{{ t('disabled') }}</span>
              </td>
              <td class="text-center">
                <button v-if="!m.is_core"
                        :class="['btn-icon', m.is_active ? 'text-amber-600' : 'text-green-600']"
                        @click="toggleModule(m)"
                        :title="m.is_active ? t('disable') : t('enable')">
                  <span class="material-symbols-outlined">{{ m.is_active ? 'toggle_off' : 'toggle_on' }}</span>
                </button>
                <button v-if="!m.is_core"
                        class="btn-icon text-red-500"
                        @click="uninstallModule(m)"
                        :title="t('uninstall')">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </td>
            </tr>
            <tr v-if="!installed.length">
              <td colspan="5" class="empty-cell">{{ t('no-modules') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="data-card">
        <div class="data-card-header">{{ t('available-modules', 'Available Modules') }}</div>
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('module') }}</th>
              <th>{{ t('description') }}</th>
              <th>{{ t('controllers', 'Controllers') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in available" :key="a.module_key">
              <td><span class="module-name">{{ a.name }}</span></td>
              <td class="text-sm text-gray-500">{{ a.description }}</td>
              <td>
                <span v-if="a.has_controllers" class="badge badge-active">{{ t('yes') }}</span>
                <span v-else class="badge badge-disabled">{{ t('no') }}</span>
              </td>
              <td class="text-center">
                <button v-if="!isInstalled(a.module_key)" class="btn-primary btn-sm" @click="installModule(a.module_key)">{{ t('install') }}</button>
                <span v-else class="text-gray-400 text-sm">{{ t('installed') }}</span>
              </td>
            </tr>
            <tr v-if="!available.length">
              <td colspan="4" class="empty-cell">{{ t('scan-hint') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.name" @confirm="executeUninstallModule(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const loading = ref(true)
const error = ref('')
const installed = ref([])
const available = ref([])
const confirmTarget = ref(null)

const activeCount = computed(() => installed.value.filter(m => m.is_active).length)

async function loadInstalled() {
  try {
    const res = await api.get('/T0100I/')
    installed.value = Array.isArray(res.data) ? res.data : []
  } catch {
    installed.value = []
  }
}

async function scanModules() {
  try {
    const res = await api.get('/T0100I/discover')
    available.value = Array.isArray(res.data) ? res.data : []
  } catch {
    available.value = []
  }
}

function isInstalled(key) {
  return installed.value.some(m => m.module_key === key)
}

async function installModule(key) {
  try {
    const res = await api.post(`/T0100I/${encodeURIComponent(key)}/install`)
    if (res.data?.ok) {
      if (res.data.module) installed.value.push(res.data.module)
      toast(t('module-installed', 'Module installed'), 'success')
    }
  } catch { toast(t('install-failed', 'Install failed'), 'error') }
}

async function uninstallModule(m) { confirmTarget.value = m }
async function executeUninstallModule(m) {
  confirmTarget.value = null
  try {
    const res = await api.post(`/T0100I/${m.id}/uninstall`)
    if (res.data?.ok) {
      installed.value = installed.value.filter(x => x.id !== m.id)
      toast(t('module-uninstalled', 'Module uninstalled'), 'success')
    }
  } catch { toast(t('uninstall-failed', 'Uninstall failed'), 'error') }
}

async function toggleModule(m) {
  try {
    const res = await api.put(`/T0100I/${m.id}/toggle`, { is_active: !m.is_active })
    if (res.data?.ok && res.data.module) Object.assign(m, res.data.module)
    toast(m.is_active ? t('module-enabled', 'Module enabled') : t('module-disabled', 'Module disabled'), 'success')
  } catch { toast(t('toggle-failed', 'Toggle failed'), 'error') }
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadInstalled(), scanModules()])
  } catch {
    error.value = t('failed-load')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.loading-state, .error-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.error-state { color: #ba1a1a; }

.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-value.active-color { color: #008080; }
.stat-value.danger-color { color: #ba1a1a; }
.stat-label { font-size: 12px; color: #999; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.data-card-header { padding: 14px 20px; border-bottom: 1px solid #eee; background: #fafafe; font-weight: 700; font-size: 14px; color: #1a1a2e; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; }
.empty-cell { text-align: center; padding: 32px 20px; color: #bbb; font-size: 13px; }

.module-name { font-weight: 600; color: #5d3fd3; }
.core-badge { font-size: 11px; color: #999; background: #f0f0f4; padding: 1px 6px; border-radius: 4px; margin-left: 6px; font-weight: 600; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #999; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-disabled { background: #f5f5f5; color: #999; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-primary:hover { background: #4a32b0; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.btn-sm { padding: 6px 14px; font-size: 12px; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; transition: all 0.15s; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }
</style>

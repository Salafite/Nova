<template>
  <div class="sync-status-container" :class="{ offline: !store.isOnline, syncing: store.isSyncing }">
    <!-- Status Pill -->
    <div class="status-pill" @click="toggleDetails" :title="statusTooltip">
      <span class="status-indicator">
        <span class="pulse-dot" :class="statusClass"></span>
      </span>
      <span class="status-label">{{ statusText }}</span>

      <!-- Pending Orders Badge -->
      <span v-if="store.pendingCount > 0" class="badge badge-pending" title="Orders pending sync">
        <span class="material-symbols-outlined badge-icon">schedule</span>
        {{ store.pendingCount }}
      </span>

      <!-- Conflict Badge -->
      <span v-if="store.conflictCount > 0" class="badge badge-conflict" title="Orders with conflicts">
        <span class="material-symbols-outlined badge-icon">warning</span>
        {{ store.conflictCount }}
      </span>

      <button class="expand-btn" :class="{ open: showDetails }" aria-label="Toggle details">
        <span class="material-symbols-outlined">expand_more</span>
      </button>
    </div>

    <!-- Manual Sync Trigger Button -->
    <button
      class="sync-btn"
      :disabled="!store.isOnline || store.isSyncing"
      @click.stop="handleManualSync"
      :title="store.isOnline ? 'Sync queued orders now' : 'Offline - sync will resume when online'"
    >
      <span class="material-symbols-outlined" :class="{ 'spin-icon': store.isSyncing }">
        sync
      </span>
    </button>

    <!-- Expandable Details Popover / Card -->
    <div v-if="showDetails" class="details-popover" @click.stop>
      <div class="popover-header">
        <div class="popover-title">
          <span class="material-symbols-outlined">cloud_sync</span>
          Sync Diagnostics
        </div>
        <button class="close-btn" @click="showDetails = false">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>

      <div class="popover-body">
        <div class="diag-row">
          <span class="diag-label">Network Status</span>
          <span class="diag-value" :class="{ 'text-success': store.isOnline, 'text-danger': !store.isOnline }">
            {{ store.isOnline ? 'Connected' : 'Offline (Local Only)' }}
          </span>
        </div>

        <div class="diag-row">
          <span class="diag-label">Sync State</span>
          <span class="diag-value">
            {{ store.isSyncing ? 'Syncing...' : 'Idle' }}
          </span>
        </div>

        <div class="diag-row">
          <span class="diag-label">Pending Orders</span>
          <span class="diag-value font-mono">{{ store.pendingCount }}</span>
        </div>

        <div class="diag-row">
          <span class="diag-label">Stock Conflicts</span>
          <span class="diag-value font-mono" :class="{ 'text-danger font-bold': store.conflictCount > 0 }">
            {{ store.conflictCount }}
          </span>
        </div>

        <div class="diag-row">
          <span class="diag-label">Synced Orders</span>
          <span class="diag-value font-mono text-success">{{ store.syncedCount }}</span>
        </div>

        <div class="diag-row">
          <span class="diag-label">Last Successful Sync</span>
          <span class="diag-value text-muted">{{ formatTime(store.lastSyncTime) }}</span>
        </div>

        <div v-if="store.lastSyncError" class="diag-error">
          <span class="material-symbols-outlined error-icon">error_outline</span>
          <span class="error-msg">{{ store.lastSyncError }}</span>
        </div>
      </div>

      <div class="popover-actions">
        <button
          class="btn-sync-action"
          :disabled="!store.isOnline || store.isSyncing"
          @click="handleManualSync"
        >
          <span class="material-symbols-outlined" :class="{ 'spin-icon': store.isSyncing }">sync</span>
          {{ store.isSyncing ? 'Syncing...' : 'Sync Now' }}
        </button>

        <button
          v-if="store.syncedCount > 0"
          class="btn-clear-action"
          @click="handleClearSynced"
        >
          <span class="material-symbols-outlined">done_all</span>
          Clear Synced ({{ store.syncedCount }})
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useFieldSalesStore } from '../../stores/fieldSales.js'
import { useToast } from '../../composables/useToast.js'

const store = useFieldSalesStore()
const { show: toast } = useToast()
const showDetails = ref(false)

const statusClass = computed(() => {
  if (store.isSyncing) return 'pulse-syncing'
  if (store.conflictCount > 0) return 'pulse-conflict'
  if (!store.isOnline) return 'pulse-offline'
  return 'pulse-online'
})

const statusText = computed(() => {
  if (store.isSyncing) return 'Syncing...'
  if (store.conflictCount > 0) return `${store.conflictCount} Conflict${store.conflictCount > 1 ? 's' : ''}`
  if (!store.isOnline) return 'Offline'
  if (store.pendingCount > 0) return `${store.pendingCount} Queued`
  return 'Online'
})

const statusTooltip = computed(() => {
  if (store.isSyncing) return 'Synchronizing orders with server'
  if (!store.isOnline) return 'Offline mode - orders saved locally to IndexedDB'
  if (store.conflictCount > 0) return `${store.conflictCount} orders require conflict resolution`
  return 'Connected to Nova ERP server'
})

function toggleDetails() {
  showDetails.value = !showDetails.value
}

function formatTime(isoStr) {
  if (!isoStr) return 'Never'
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}

async function handleManualSync() {
  if (!store.isOnline) {
    toast('Cannot sync: Device is offline', 'error')
    return
  }
  try {
    const res = await store.triggerSync({ force: true })
    if (res && res.success) {
      toast('Sync completed successfully', 'success')
    }
  } catch (err) {
    toast(`Sync error: ${err.message || 'Unknown error'}`, 'error')
  }
}

async function handleClearSynced() {
  try {
    const cleared = await store.clearSyncedOrders()
    toast(`Cleared ${cleared} synced orders from local queue`, 'info')
  } catch (err) {
    toast(`Failed to clear synced orders: ${err.message}`, 'error')
  }
}
</script>

<style scoped>
.sync-status-container {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.18s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.status-pill:hover {
  background: var(--bg-surface-hover);
  border-color: var(--color-primary);
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 10px;
  height: 10px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.pulse-online {
  background-color: var(--color-success, #16a34a);
  box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2);
}

.pulse-offline {
  background-color: var(--color-error, #dc2626);
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.2);
}

.pulse-syncing {
  background-color: #2563eb;
  animation: pulse-ring 1.2s infinite ease-in-out;
}

.pulse-conflict {
  background-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
  animation: pulse-ring 1.5s infinite ease-in-out;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.9);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.25);
    opacity: 1;
  }
  100% {
    transform: scale(0.9);
    opacity: 0.8;
  }
}

.status-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.badge-conflict {
  background: #fee2e2;
  color: #991b1b;
}

.badge-icon {
  font-size: 12px;
}

.expand-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--text-subtle);
  display: inline-flex;
  align-items: center;
  transition: transform 0.2s ease;
}

.expand-btn.open {
  transform: rotate(180deg);
}

.expand-btn .material-symbols-outlined {
  font-size: 16px;
}

.sync-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.sync-btn:hover:not(:disabled) {
  background: var(--bg-surface-hover);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.sync-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sync-btn .material-symbols-outlined {
  font-size: 16px;
}

.spin-icon {
  animation: spin 1s infinite linear;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Popover details */
.details-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 280px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  z-index: 100;
  padding: 12px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
  margin-bottom: 10px;
}

.popover-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.popover-title .material-symbols-outlined {
  font-size: 18px;
  color: var(--color-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 2px;
}

.close-btn:hover {
  color: var(--text-primary);
}

.close-btn .material-symbols-outlined {
  font-size: 16px;
}

.popover-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diag-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.diag-label {
  color: var(--text-muted);
}

.diag-value {
  font-weight: 600;
  color: var(--text-primary);
}

.font-mono {
  font-family: monospace;
}

.font-bold {
  font-weight: 700;
}

.text-success {
  color: var(--color-success, #16a34a);
}

.text-danger {
  color: var(--color-error, #dc2626);
}

.text-muted {
  color: var(--text-muted);
}

.diag-error {
  margin-top: 6px;
  padding: 6px 8px;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 6px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: #991b1b;
}

.error-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}

.error-msg {
  word-break: break-word;
}

.popover-actions {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.btn-sync-action,
.btn-clear-action {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-sync-action {
  background: var(--color-primary);
  color: #fff;
  border: none;
}

.btn-sync-action:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-sync-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-clear-action {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.btn-clear-action:hover {
  background: var(--bg-surface-hover);
}

.btn-sync-action .material-symbols-outlined,
.btn-clear-action .material-symbols-outlined {
  font-size: 16px;
}
</style>

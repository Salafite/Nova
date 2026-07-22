<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div><h1 class="page-title">{{ t('sched-title', 'Maintenance Schedules') }}</h1><p class="page-subtitle">{{ t('sched-sub', 'Schedule and manage preventive maintenance') }}</p></div>
      <button class="btn-primary" @click="openAdd"><span class="material-symbols-outlined">add</span> {{ t('new-schedule', 'New Schedule') }}</button>
    </div>
    <SkeletonTable v-if="loading" /><ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">calendar_month</span><p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>{{ t('task', 'Task') }}</th><th>{{ t('asset') }}</th><th>{{ t('frequency') }}</th><th>{{ t('next-due', 'Next Due') }}</th><th>{{ t('assigned-to') }}</th><th>{{ t('status') }}</th><th class="text-center">{{ t('actions') }}</th></tr></thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><strong>{{ item.name || item.task_name || item.title }}</strong></td>
              <td>{{ item.asset_id || '-' }}</td>
              <td>{{ item.frequency || item.interval || '-' }}</td>
              <td>{{ formatDate(item.next_due_date) }}</td>
              <td>{{ item.assigned_to || '-' }}</td>
              <td><span class="badge" :class="'badge-' + (item.status || '').toLowerCase()">{{ item.status || 'Active' }}</span></td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon text-red-500" @click="deleteItem(item)"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
const { t, dir } = useI18n()
const loading = ref(true); const error = ref(''); const items = ref([])
function formatDate(d) { if (!d) return '-'; return new Date(d).toLocaleDateString() }
async function load() { loading.value = true; error.value = ''; try { const res = await api.get('/T0042I/'); items.value = res.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
function openAdd() { }
function editItem(item) { }
function deleteItem(item) { }
onMounted(() => { load() })
</script>
<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 16px; }
.data-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 10px 20px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #fafafe; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }
.data-table td { padding: 12px 20px; border-bottom: 1px solid #f5f5f5; font-size: 13px; color: #333; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafafe; }
.text-center { text-align: center; } .text-red-500 { color: #e53935; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-overdue { background: #ffebee; color: #c62828; }
.badge-completed { background: #e3f2fd; color: #1565c0; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; color: #666; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }
</style>
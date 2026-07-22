<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div><h1 class="page-title">{{ t('ecom-title', 'E-Commerce Integration') }}</h1><p class="page-subtitle">{{ t('ecom-sub', 'Manage e-commerce platform connections') }}</p></div>
      <button class="btn-primary" @click="openAdd"><span class="material-symbols-outlined">add</span> {{ t('new-store', 'Connect Store') }}</button>
    </div>
    <SkeletonTable v-if="loading" /><ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">shopping_cart</span><p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>{{ t('store', 'Store') }}</th><th>{{ t('platform') }}</th><th>{{ t('products-synced', 'Products') }}</th><th>{{ t('orders-synced', 'Orders') }}</th><th>{{ t('status') }}</th><th>{{ t('last-sync') }}</th><th class="text-center">{{ t('actions') }}</th></tr></thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><strong>{{ item.store_name || item.name }}</strong></td>
              <td>{{ item.platform || item.ecommerce_platform || '-' }}</td>
              <td class="text-center">{{ item.products_synced || 0 }}</td>
              <td class="text-center">{{ item.orders_synced || 0 }}</td>
              <td><span class="badge" :class="item.is_active ? 'badge-active' : 'badge-disabled'">{{ item.is_active ? 'Connected' : 'Disconnected' }}</span></td>
              <td>{{ formatDate(item.last_sync_at) }}</td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon" @click="syncNow(item)" title="Sync"><span class="material-symbols-outlined">sync</span></button>
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
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
const { show: toast } = useToast()
const { t, dir } = useI18n()
const loading = ref(true); const error = ref(''); const items = ref([])
function formatDate(d) { if (!d) return '-'; return new Date(d).toLocaleString() }
async function load() { loading.value = true; error.value = ''; try { const res = await api.get('/T0057I/'); items.value = res.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
function openAdd() { }
function editItem(item) { }
async function syncNow(item) { try { await api.post(`/T0057I/${item.id}/sync`); toast('Sync triggered', 'success') } catch { toast(t('failed-save'), 'error') } }
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
.text-center { text-align: center; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-disabled { background: #f5f5f5; color: #999; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; color: #666; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }
</style>
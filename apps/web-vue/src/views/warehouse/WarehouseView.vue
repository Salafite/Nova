<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-gray-800">Warehouse</h2>
      <button class="btn-primary"><span class="material-symbols-outlined text-lg">add</span> New Transfer</button>
    </div>
    <div v-if="loading" class="text-center py-12 text-gray-400">Loading...</div>
    <div v-else class="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          <tr><th class="px-6 py-3">Name</th><th class="px-6 py-3">Location</th><th class="px-6 py-3 text-center">Status</th></tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="w in warehouses" :key="w.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 font-semibold">{{ w.name }}</td>
            <td class="px-6 py-4 text-sm text-gray-500">{{ w.location || '-' }}</td>
            <td class="px-6 py-4 text-center"><span class="badge badge-success">Active</span></td>
          </tr>
          <tr v-if="!warehouses.length"><td colspan="3" class="px-6 py-8 text-center text-gray-400">No warehouses found</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
const warehouses = ref([])
const loading = ref(true)
onMounted(async () => {
  try { warehouses.value = await api.get('/T0008I/').then(r => r.data || []) }
  catch { warehouses.value = [] }
  finally { loading.value = false }
})
</script>
<style scoped>
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-success { background: #dcfce7; color: #16a34a; }
</style>

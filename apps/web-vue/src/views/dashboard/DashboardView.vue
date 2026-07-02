<template>
  <div :dir="dir">
    <h2 class="page-title mb-6">{{ t('dash-title', 'Dashboard') }}</h2>

    <div v-if="loading" class="text-center py-12 text-gray-400">{{ t('loading', 'Loading...') }}</div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
      {{ t('dash-load-error', 'Failed to load dashboard data') }}
    </div>

    <template v-else>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard :label="t('dash-total-products', 'Total Products')" :value="stats.products" />
        <StatsCard :label="t('dash-total-customers', 'Total Customers')" :value="stats.customers" />
        <StatsCard :label="t('dash-total-suppliers', 'Total Suppliers')" :value="stats.suppliers" />
        <StatsCard :label="t('dash-active-orders', 'Active Orders')" :value="stats.salesOrders" color="#008080" />
        <StatsCard :label="t('dash-total-invoices', 'Invoices')" :value="stats.invoices" color="#ba1a1a" />
        <StatsCard :label="t('dash-total-payments', 'Payments')" :value="stats.payments" color="#1a6bba" />
        <StatsCard :label="t('dash-total-employees', 'Employees')" :value="stats.employees" color="#6bba1a" />
        <StatsCard :label="t('dash-total-users', 'Users')" :value="stats.users" color="#9b1aba" />
      </div>

      <div class="bg-white border border-gray-200 rounded-xl p-6">
        <h3 class="font-semibold mb-4">{{ t('dash-recent-activity', 'Recent Activity') }}</h3>
        <div v-if="recent.length === 0" class="text-gray-400 text-sm">
          {{ t('no-records', 'No records found') }}
        </div>
        <ul v-else class="divide-y divide-gray-100 text-sm">
          <li v-for="(item, i) in recent" :key="i" class="py-2 flex justify-between">
            <span class="text-gray-700">{{ item.label }}</span>
            <span class="text-gray-400">{{ item.date }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'
import { api } from '../../api/client.js'
import StatsCard from '../../components/StatsCard.vue'

const { t, dir } = useI18n()

const loading = ref(true)
const error = ref(false)
const stats = reactive({ products: 0, customers: 0, suppliers: 0, salesOrders: 0, invoices: 0, payments: 0, employees: 0, users: 0 })
const recent = ref([])

async function count(endpoint) {
  try {
    const res = await api.get('/' + endpoint + '/')
    return (res.data || []).length
  } catch {
    return 0
  }
}

onMounted(async () => {
  try {
    const [products, customers, suppliers, salesOrders, invoices, payments, employees, users] = await Promise.all([
      count('T0003I'), count('T0010I'), count('T0011I'), count('T0012I'),
      count('T0090I'), count('T0091I'), count('T0030I'), count('T0021I')
    ])
    stats.products = products
    stats.customers = customers
    stats.suppliers = suppliers
    stats.salesOrders = salesOrders
    stats.invoices = invoices
    stats.payments = payments
    stats.employees = employees
    stats.users = users

    const res = await api.get('/T0090I/')
    const invoicesData = res.data || []
    recent.value = invoicesData.slice(-5).reverse().map(inv => ({
      label: inv.invoice_no || inv.id || 'Invoice',
      date: inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString() : '-'
    }))
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

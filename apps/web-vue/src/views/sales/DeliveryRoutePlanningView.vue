<template>
  <div class="delivery-route-planning" :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('delivery-route-planning', 'Delivery Route Planning & Driver Dispatch') }}</h1>
        <p class="page-subtitle">{{ t('delivery-route-planning-sub', 'Group confirmed orders by zone, assign vehicles & drivers, and manage LIFO staging') }}</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="loadData">
          <span class="material-symbols-outlined icon-xs">refresh</span> {{ t('refresh', 'Refresh') }}
        </button>
        <button class="btn-primary" @click="openCreateRunModal" :disabled="!selectedOrders.length">
          <span class="material-symbols-outlined icon-xs">add_road</span>
          {{ t('create-run-from-selected', 'Create Delivery Run') }} ({{ selectedOrders.length }})
        </button>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="filter-card mb-4">
      <div class="grid-filters">
        <div class="form-group">
          <label>{{ t('zone-territory', 'Zone / Territory') }}</label>
          <input type="text" v-model="filters.zone_name" placeholder="e.g. North Zone" class="form-input" @change="loadUnassignedOrders" />
        </div>
        <div class="form-group">
          <label>{{ t('delivery-date', 'Delivery Date') }}</label>
          <input type="date" v-model="filters.delivery_date" class="form-input" @change="loadUnassignedOrders" />
        </div>
        <div class="form-group">
          <label>{{ t('warehouse', 'Warehouse') }}</label>
          <select v-model="filters.warehouse_id" class="form-input" @change="loadUnassignedOrders">
            <option :value="null">{{ t('all-warehouses', 'All Warehouses') }}</option>
            <option v-for="wh in warehouses" :key="wh.id" :value="wh.id">{{ wh.name }}</option>
          </select>
        </div>
        <div class="form-group align-end">
          <button class="btn-secondary w-full" @click="clearFilters">
            {{ t('clear-filters', 'Clear Filters') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Active Delivery Runs Overview & Unassigned Orders Tabs -->
    <div class="tabs-header mb-4">
      <button :class="['tab-btn', { active: activeTab === 'unassigned' }]" @click="activeTab = 'unassigned'">
        <span class="material-symbols-outlined icon-xs">inventory_2</span>
        {{ t('unassigned-orders', 'Unassigned Delivery Orders') }}
        <span class="tab-badge">{{ unassignedOrders.length }}</span>
      </button>
      <button :class="['tab-btn', { active: activeTab === 'runs' }]" @click="activeTab = 'runs'">
        <span class="material-symbols-outlined icon-xs">local_shipping</span>
        {{ t('active-delivery-runs', 'Delivery Runs & Dispatch') }}
        <span class="tab-badge">{{ deliveryRuns.length }}</span>
      </button>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadData" />

    <!-- Unassigned Orders Tab Content -->
    <div v-else-if="activeTab === 'unassigned'" class="data-card">
      <div v-if="!unassignedOrders.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">assignment_turned_in</span>
        <p>{{ t('no-unassigned-orders', 'No unassigned confirmed delivery orders found') }}</p>
      </div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="w-10 text-center">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th>{{ t('order-number', 'Order #') }}</th>
              <th>{{ t('customer', 'Customer') }}</th>
              <th>{{ t('zone', 'Zone') }}</th>
              <th>{{ t('address', 'Delivery Address') }}</th>
              <th>{{ t('delivery-date', 'Date') }}</th>
              <th>{{ t('weight-kg', 'Weight (kg)') }}</th>
              <th>{{ t('volume-m3', 'Volume (m³)') }}</th>
              <th>{{ t('item-count', 'Items') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in unassignedOrders" :key="order.order_id">
              <td class="text-center">
                <input type="checkbox" :value="order.order_id" v-model="selectedOrders" />
              </td>
              <td class="font-bold cell-order">
                <a @click="$router.push(`/sales/${order.order_id}`)" class="order-link">{{ order.order_number }}</a>
              </td>
              <td>{{ order.customer_name }}</td>
              <td><span class="badge badge-info">{{ order.zone_name || 'Default Zone' }}</span></td>
              <td class="cell-address">{{ order.delivery_address || '-' }}</td>
              <td>{{ order.delivery_date }}</td>
              <td class="cell-mono">{{ order.total_weight ? order.total_weight.toFixed(1) : '0.0' }}</td>
              <td class="cell-mono">{{ order.total_volume ? order.total_volume.toFixed(2) : '0.00' }}</td>
              <td>{{ order.item_count || 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Active Delivery Runs Tab Content -->
    <div v-else-if="activeTab === 'runs'" class="data-card">
      <div v-if="!deliveryRuns.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">alt_route</span>
        <p>{{ t('no-delivery-runs', 'No active delivery runs found') }}</p>
      </div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('run-code', 'Run Code') }}</th>
              <th>{{ t('run-date', 'Run Date') }}</th>
              <th>{{ t('zone', 'Zone') }}</th>
              <th>{{ t('vehicle', 'Vehicle / Driver') }}</th>
              <th>{{ t('stops', 'Stops') }}</th>
              <th>{{ t('weight-load', 'Payload / Max') }}</th>
              <th>{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in deliveryRuns" :key="run.id">
              <td class="font-bold cell-order">{{ run.run_code }}</td>
              <td>{{ run.run_date }}</td>
              <td><span class="badge badge-info">{{ run.zone_name }}</span></td>
              <td>
                <div class="flex flex-col text-sm">
                  <span class="font-semibold">{{ run.vehicle_name && run.vehicle_code ? run.vehicle_name + ' (' + run.vehicle_code + ')' : (run.vehicle_name || run.vehicle_code || t('unassigned-truck', 'Unassigned Truck')) }}</span>
                  <span class="text-xs text-muted">{{ run.driver_name || t('unassigned-driver', 'No Driver') }}</span>
                </div>
              </td>
              <td><span class="badge badge-neutral">{{ run.stop_count || (run.stops ? run.stops.length : 0) }} {{ t('stops', 'stops') }}</span></td>
              <td>
                <span class="cell-mono text-xs">
                  {{ run.total_weight ? run.total_weight.toFixed(1) : 0 }} / {{ run.max_weight_capacity ? run.max_weight_capacity.toFixed(0) : '∞' }} kg
                </span>
              </td>
              <td>
                <span :class="['badge', runStatusClass(run.status)]">{{ run.status }}</span>
              </td>
              <td class="text-center">
                <div class="flex items-center justify-center gap-1">
                  <button class="btn-xs btn-secondary" @click="openAssignVehicleModal(run)" :title="t('assign-vehicle', 'Assign Vehicle / Driver')">
                    <span class="material-symbols-outlined icon-xs">directions_bus</span>
                  </button>
                  <button class="btn-xs btn-primary" @click="$router.push(`/sales/driver-manifest/${run.id}`)" :title="t('view-manifest', 'View Driver Manifest')">
                    <span class="material-symbols-outlined icon-xs">list_alt</span>
                  </button>
                  <button class="btn-xs btn-warning" @click="openLIFOModal(run)" :title="t('lifo-staging', 'LIFO Staging Pick List')">
                    <span class="material-symbols-outlined icon-xs">unfold_more</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create Run Modal -->
    <div v-if="showCreateRunModal" class="modal-overlay" @click.self="closeCreateRunModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ t('create-delivery-run', 'Create Delivery Run') }}</h3>
          <button class="btn-icon" @click="closeCreateRunModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitCreateRun">
            <div class="form-group mb-3">
              <label>{{ t('run-code', 'Run Code') }} <span class="required">*</span></label>
              <input type="text" v-model="runForm.run_code" required class="form-input" placeholder="RUN-2026-001" />
            </div>
            <div class="form-group mb-3">
              <label>{{ t('run-date', 'Delivery Run Date') }} <span class="required">*</span></label>
              <input type="date" v-model="runForm.run_date" required class="form-input" />
            </div>
            <div class="form-group mb-3">
              <label>{{ t('zone-name', 'Geographic Zone / Territory') }} <span class="required">*</span></label>
              <input type="text" v-model="runForm.zone_name" required class="form-input" placeholder="North Zone" />
            </div>
            <div class="form-group mb-3">
              <label>{{ t('notes', 'Notes / Instructions') }}</label>
              <textarea v-model="runForm.notes" class="form-input" rows="2"></textarea>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeCreateRunModal">{{ t('cancel', 'Cancel') }}</button>
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? t('saving', 'Saving...') : t('create-run', 'Create Run') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Assign Vehicle / Driver Modal -->
    <div v-if="showAssignModal" class="modal-overlay" @click.self="closeAssignModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ t('assign-vehicle-driver', 'Assign Vehicle & Driver') }} ({{ activeRun?.run_code }})</h3>
          <button class="btn-icon" @click="closeAssignModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitVehicleAssignment">
            <div class="form-group mb-3">
              <label>{{ t('vehicle-code', 'Vehicle Code / Plate') }} <span class="required">*</span></label>
              <input type="text" v-model="assignForm.vehicle_code" required class="form-input" placeholder="TRK-01" />
            </div>
            <div class="form-group mb-3">
              <label>{{ t('vehicle-name', 'Vehicle Description') }}</label>
              <input type="text" v-model="assignForm.vehicle_name" class="form-input" placeholder="Isuzu 5-Ton Refrigerated Truck" />
            </div>
            <div class="form-group mb-3">
              <label>{{ t('driver-name', 'Driver Name') }} <span class="required">*</span></label>
              <input type="text" v-model="assignForm.driver_name" required class="form-input" placeholder="John Doe" />
            </div>
            <div class="grid grid-cols-2 gap-3 mb-3">
              <div class="form-group">
                <label>{{ t('max-weight-kg', 'Max Weight Capacity (kg)') }}</label>
                <input type="number" step="0.1" v-model.number="assignForm.max_weight_capacity" class="form-input" placeholder="3500" />
              </div>
              <div class="form-group">
                <label>{{ t('max-volume-m3', 'Max Volume Capacity (m³)') }}</label>
                <input type="number" step="0.1" v-model.number="assignForm.max_volume_capacity" class="form-input" placeholder="18.5" />
              </div>
            </div>

            <div v-if="assignmentWarning" class="alert alert-warning mb-3">
              <span class="material-symbols-outlined">warning</span>
              <div>{{ assignmentWarning }}</div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeAssignModal">{{ t('cancel', 'Cancel') }}</button>
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? t('assigning', 'Assigning...') : t('save-assignment', 'Save Assignment') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- LIFO Staging Pick List Modal -->
    <div v-if="showLIFOModal" class="modal-overlay" @click.self="showLIFOModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div>
            <h3>{{ t('lifo-staging-pick-list', 'Last-In, First-Out (LIFO) Vehicle Loading Pick List') }}</h3>
            <p class="text-sm text-muted">{{ activeRun?.run_code }} — {{ activeRun?.zone_name }}</p>
          </div>
          <button class="btn-icon" @click="showLIFOModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="modal-body">
          <div class="staging-banner mb-3">
            <span class="material-symbols-outlined">info</span>
            <div>
              <strong>{{ t('lifo-loading-rule', 'Vehicle Loading Rule:') }}</strong>
              {{ t('lifo-explain', 'Stage and load LAST drop-off items FIRST into the front of the truck. First drop-off items are staged and loaded LAST at the tail door for immediate unloading.') }}
            </div>
          </div>

          <div v-if="!lifoPickList?.staging_items?.length" class="empty-state">
            <p>{{ t('no-staging-items', 'No staging items found for this run.') }}</p>
          </div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="w-16">{{ t('load-seq', 'Load Seq') }}</th>
                  <th>{{ t('drop-stop', 'Drop Stop #') }}</th>
                  <th>{{ t('customer', 'Customer') }}</th>
                  <th>{{ t('product', 'Product / Item') }}</th>
                  <th>{{ t('qty', 'Quantity') }}</th>
                  <th>{{ t('staging-dock', 'Staging Bay') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in lifoPickList.staging_items" :key="item.id || item.staging_sequence">
                  <td class="font-bold text-center highlight-seq">#{{ item.staging_sequence }}</td>
                  <td><span class="badge badge-neutral">Stop #{{ item.stop_sequence }}</span></td>
                  <td class="font-semibold">{{ item.customer_name }}</td>
                  <td>{{ item.product_name || item.item_code }}</td>
                  <td class="cell-mono font-bold">{{ item.quantity }} {{ item.uom || 'PCS' }}</td>
                  <td><span class="badge badge-info">{{ item.staging_bay || 'Bay-A' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../../api/client.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import { useToast } from '../../composables/useToast.js'

export default {
  name: 'DeliveryRoutePlanningView',
  components: { SkeletonTable, ErrorState },
  setup() {
    const toast = useToast()
    const dir = ref('ltr')
    const loading = ref(false)
    const saving = ref(false)
    const error = ref(null)

    const activeTab = ref('unassigned')
    const unassignedOrders = ref([])
    const deliveryRuns = ref([])
    const warehouses = ref([])
    const selectedOrders = ref([])

    const filters = ref({
      zone_name: '',
      delivery_date: '',
      warehouse_id: null,
    })

    const showCreateRunModal = ref(false)
    const runForm = ref({
      run_code: '',
      run_date: new Date().toISOString().split('T')[0],
      zone_name: '',
      notes: '',
    })

    const showAssignModal = ref(false)
    const activeRun = ref(null)
    const assignForm = ref({
      vehicle_code: '',
      vehicle_name: '',
      driver_name: '',
      max_weight_capacity: 3500,
      max_volume_capacity: 20,
    })
    const assignmentWarning = ref('')

    const showLIFOModal = ref(false)
    const lifoPickList = ref(null)

    const t = (key, fallback) => fallback

    const isAllSelected = computed(() => {
      return unassignedOrders.value.length > 0 && selectedOrders.value.length === unassignedOrders.value.length
    })

    const toggleSelectAll = (e) => {
      if (e.target.checked) {
        selectedOrders.value = unassignedOrders.value.map(o => o.order_id)
      } else {
        selectedOrders.value = []
      }
    }

    const loadUnassignedOrders = async () => {
      try {
        const params = {}
        if (filters.value.zone_name) params.zone_name = filters.value.zone_name
        if (filters.value.delivery_date) params.delivery_date = filters.value.delivery_date
        if (filters.value.warehouse_id) params.warehouse_id = filters.value.warehouse_id

        const res = await api.get('/api/sales/delivery-routes/unassigned-orders', { params })
        unassignedOrders.value = res.data || []
      } catch (err) {
        console.error('Error loading unassigned orders:', err)
        error.value = err.message || 'Failed to load unassigned delivery orders'
      }
    }

    const loadDeliveryRuns = async () => {
      try {
        const res = await api.get('/api/sales/delivery-routes/runs')
        deliveryRuns.value = res.data || []
      } catch (err) {
        console.error('Error loading delivery runs:', err)
      }
    }

    const loadData = async () => {
      loading.value = true
      error.value = null
      try {
        await Promise.all([loadUnassignedOrders(), loadDeliveryRuns()])
      } finally {
        loading.value = false
      }
    }

    const clearFilters = () => {
      filters.value = { zone_name: '', delivery_date: '', warehouse_id: null }
      loadUnassignedOrders()
    }

    const openCreateRunModal = () => {
      if (!selectedOrders.value.length) return
      const firstSel = unassignedOrders.value.find(o => o.order_id === selectedOrders.value[0])
      runForm.value = {
        run_code: `RUN-${Date.now().toString().slice(-6)}`,
        run_date: firstSel?.delivery_date || new Date().toISOString().split('T')[0],
        zone_name: firstSel?.zone_name || 'North Zone',
        notes: '',
      }
      showCreateRunModal.value = true
    }

    const closeCreateRunModal = () => {
      showCreateRunModal.value = false
    }

    const submitCreateRun = async () => {
      saving.value = true
      try {
        const payload = {
          ...runForm.value,
          order_ids: selectedOrders.value,
        }
        await api.post('/api/sales/delivery-routes/runs', payload)
        toast.show('Delivery run created successfully')
        showCreateRunModal.value = false
        selectedOrders.value = []
        activeTab.value = 'runs'
        await loadData()
      } catch (err) {
        toast.show(err.response?.data?.detail || 'Failed to create delivery run', 'error')
      } finally {
        saving.value = false
      }
    }

    const openAssignVehicleModal = (run) => {
      activeRun.value = run
      assignForm.value = {
        vehicle_code: run.vehicle_code || '',
        vehicle_name: run.vehicle_name || '',
        driver_name: run.driver_name || '',
        max_weight_capacity: run.max_weight_capacity || 3500,
        max_volume_capacity: run.max_volume_capacity || 20,
      }
      assignmentWarning.value = ''
      showAssignModal.value = true
    }

    const closeAssignModal = () => {
      showAssignModal.value = false
      activeRun.value = null
    }

    const submitVehicleAssignment = async () => {
      if (!activeRun.value) return
      saving.value = true
      try {
        const res = await api.post(`/api/sales/delivery-routes/runs/${activeRun.value.id}/assign-vehicle`, assignForm.value)
        if (res.data?.capacity_exceeded) {
          assignmentWarning.value = `Warning: Payload weight/volume exceeds capacity limits!`
        }
        toast.show('Vehicle & Driver assigned successfully')
        closeAssignModal()
        await loadDeliveryRuns()
      } catch (err) {
        toast.show(err.response?.data?.detail || 'Failed to assign vehicle', 'error')
      } finally {
        saving.value = false
      }
    }

    const openLIFOModal = async (run) => {
      activeRun.value = run
      try {
        const res = await api.get(`/api/sales/delivery-routes/runs/${run.id}/lifo-staging`)
        lifoPickList.value = res.data
        showLIFOModal.value = true
      } catch (err) {
        toast.show('Failed to fetch LIFO staging list', 'error')
      }
    }

    const runStatusClass = (status) => {
      switch (status) {
        case 'Draft': return 'badge-neutral'
        case 'Planned': return 'badge-info'
        case 'Dispatched': return 'badge-warning'
        case 'In Transit': return 'badge-primary'
        case 'Completed': return 'badge-success'
        default: return 'badge-neutral'
      }
    }

    onMounted(() => {
      loadData()
    })

    return {
      dir,
      loading,
      saving,
      error,
      activeTab,
      unassignedOrders,
      deliveryRuns,
      warehouses,
      selectedOrders,
      filters,
      showCreateRunModal,
      runForm,
      showAssignModal,
      activeRun,
      assignForm,
      assignmentWarning,
      showLIFOModal,
      lifoPickList,
      t,
      isAllSelected,
      toggleSelectAll,
      loadUnassignedOrders,
      loadDeliveryRuns,
      loadData,
      clearFilters,
      openCreateRunModal,
      closeCreateRunModal,
      submitCreateRun,
      openAssignVehicleModal,
      closeAssignModal,
      submitVehicleAssignment,
      openLIFOModal,
      runStatusClass,
    }
  }
}
</script>

<style scoped>
.delivery-route-planning {
  padding: 1.5rem;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.grid-filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
.tabs-header {
  display: flex;
  gap: 1rem;
  border-bottom: 2px solid #e5e7eb;
}
.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: none;
  background: transparent;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}
.tab-badge {
  background: #e5e7eb;
  color: #374151;
  border-radius: 9999px;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal-content {
  background: #fff;
  border-radius: 0.5rem;
  width: 100%;
  max-width: 500px;
  padding: 1.5rem;
}
.modal-lg {
  max-width: 800px;
}
.staging-banner {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
  display: flex;
  gap: 0.75rem;
  color: #1e40af;
}
.highlight-seq {
  color: #dc2626;
  font-size: 1.1rem;
}
</style>

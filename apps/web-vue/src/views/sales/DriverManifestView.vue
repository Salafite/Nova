<template>
  <div class="driver-manifest-view" :dir="dir">
    <div class="header-bar print:hidden mb-4">
      <div class="flex items-center gap-3">
        <button class="btn-link" @click="$router.push('/sales/delivery-routes')">
          &larr; {{ t('back-to-routes', 'Back to Route Planning') }}
        </button>
        <h1 class="page-title">{{ t('driver-manifest', 'Driver Delivery Manifest') }}</h1>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="printManifest">
          <span class="material-symbols-outlined icon-xs">print</span> {{ t('print-run-sheet', 'Print Run Sheet') }}
        </button>
        <button class="btn-primary" @click="loadManifest">
          <span class="material-symbols-outlined icon-xs">refresh</span> {{ t('refresh', 'Refresh') }}
        </button>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadManifest" />

    <template v-else-if="manifest">
      <!-- Run Summary Card -->
      <div class="manifest-card mb-6">
        <div class="flex justify-between items-start flex-wrap gap-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="run-badge">{{ manifest.run_code }}</span>
              <span :class="['badge', statusClass(manifest.status)]">{{ manifest.status }}</span>
            </div>
            <h2 class="text-xl font-bold mt-2">{{ manifest.zone_name }} {{ t('route', 'Route') }}</h2>
            <p class="text-sm text-muted">{{ manifest.run_date }}</p>
          </div>
          <div class="driver-info">
            <div class="info-row">
              <span class="label">{{ t('driver', 'Driver') }}:</span>
              <span class="val font-semibold">{{ manifest.driver_name || 'Unassigned' }}</span>
            </div>
            <div class="info-row">
              <span class="label">{{ t('vehicle', 'Vehicle') }}:</span>
              <span class="val font-semibold">{{ manifest.vehicle_name && manifest.vehicle_code ? `${manifest.vehicle_name} (${manifest.vehicle_code})` : (manifest.vehicle_name || manifest.vehicle_code || 'Unassigned') }}</span>
            </div>
            <div class="info-row">
              <span class="label">{{ t('total-stops', 'Total Drop-offs') }}:</span>
              <span class="val font-bold text-primary">{{ manifest.stops ? manifest.stops.length : 0 }} {{ t('stops', 'stops') }}</span>
            </div>
            <div class="info-row">
              <span class="label">{{ t('total-payload', 'Total Payload') }}:</span>
              <span class="val font-mono">{{ manifest.total_weight ? manifest.total_weight.toFixed(1) : 0 }} kg</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Sequential Drop-off Stops -->
      <div class="stops-section">
        <h3 class="section-title mb-3 flex items-center gap-2">
          <span class="material-symbols-outlined">route</span>
          {{ t('sequential-dropoffs', 'Sequential Daily Drop-offs') }}
        </h3>

        <div v-if="!manifest.stops || !manifest.stops.length" class="empty-state">
          <p>{{ t('no-stops', 'No delivery stops registered for this run.') }}</p>
        </div>

        <div v-else class="stops-list space-y-4">
          <div
            v-for="stop in manifest.stops"
            :key="stop.id || stop.stop_sequence"
            :class="['stop-card', { 'completed-stop': stop.status === 'Delivered' }]"
          >
            <div class="stop-header">
              <div class="stop-number">
                <span>{{ t('stop', 'STOP') }}</span> <strong>#{{ stop.stop_sequence }}</strong>
              </div>
              <div class="stop-customer-info flex-1">
                <h4 class="customer-name">{{ stop.customer_name }}</h4>
                <div class="order-ref flex items-center gap-2 text-sm text-muted">
                  <span>SO #{{ stop.sales_order_number || stop.sales_order_id }}</span>
                  <span>•</span>
                  <span>{{ stop.item_count || 0 }} {{ t('items', 'items') }}</span>
                  <span>•</span>
                  <span class="font-mono">{{ stop.weight_kg ? stop.weight_kg.toFixed(1) : 0 }} kg</span>
                </div>
              </div>
              <div class="stop-status-actions flex items-center gap-2">
                <span :class="['badge', stopStatusClass(stop.status)]">{{ stop.status }}</span>
                <select
                  v-model="stop.status"
                  class="form-input text-xs print:hidden"
                  @change="updateStopStatus(stop)"
                >
                  <option value="Pending">Pending</option>
                  <option value="Arrived">Arrived</option>
                  <option value="Delivered">Delivered</option>
                  <option value="Failed">Failed</option>
                  <option value="Skipped">Skipped</option>
                </select>
              </div>
            </div>

            <div class="stop-body grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t">
              <div class="address-box">
                <span class="material-symbols-outlined icon-sm text-muted">location_on</span>
                <div>
                  <strong>{{ t('delivery-address', 'Delivery Address:') }}</strong>
                  <p class="text-sm text-gray-700">{{ stop.delivery_address || 'No address specified' }}</p>
                </div>
              </div>
              <div class="contact-box">
                <span class="material-symbols-outlined icon-sm text-muted">call</span>
                <div>
                  <strong>{{ t('contact-details', 'Contact Info:') }}</strong>
                  <p class="text-sm text-gray-700">
                    {{ stop.contact_person || 'N/A' }} — 
                    <a v-if="stop.contact_phone" :href="`tel:${stop.contact_phone}`" class="text-primary font-semibold">{{ stop.contact_phone }}</a>
                    <span v-else class="text-muted">No phone</span>
                  </p>
                </div>
              </div>
            </div>

            <div v-if="stop.delivery_notes" class="stop-notes mt-2 text-xs text-amber-800 bg-amber-50 p-2 rounded">
              <strong>{{ t('special-instructions', 'Notes:') }}</strong> {{ stop.delivery_notes }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api/client.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'
import { useToast } from '../../composables/useToast.js'

export default {
  name: 'DriverManifestView',
  components: { SkeletonTable, ErrorState },
  setup() {
    const route = useRoute()
    const toast = useToast()
    const dir = ref('ltr')
    const loading = ref(false)
    const error = ref(null)
    const manifest = ref(null)

    const t = (key, fallback) => fallback

    const loadManifest = async () => {
      const runId = route.params.id || 1
      loading.value = true
      error.value = null
      try {
        const res = await api.get(`/api/sales/delivery-routes/runs/${runId}/manifest`)
        manifest.value = res.data
      } catch (err) {
        console.error('Error loading driver manifest:', err)
        error.value = err.message || 'Failed to load driver manifest'
      } finally {
        loading.value = false
      }
    }

    const updateStopStatus = async (stop) => {
      try {
        await api.put(`/api/sales/delivery-routes/stops/${stop.id}/status?status=${encodeURIComponent(stop.status)}`)
        toast.show(`Stop #${stop.stop_sequence} status updated to ${stop.status}`)
      } catch (err) {
        toast.show('Failed to update stop status', 'error')
      }
    }

    const printManifest = () => {
      window.print()
    }

    const statusClass = (status) => {
      switch (status) {
        case 'Draft': return 'badge-neutral'
        case 'Planned': return 'badge-info'
        case 'Dispatched': return 'badge-warning'
        case 'In Transit': return 'badge-primary'
        case 'Completed': return 'badge-success'
        default: return 'badge-neutral'
      }
    }

    const stopStatusClass = (status) => {
      switch (status) {
        case 'Pending': return 'badge-neutral'
        case 'Arrived': return 'badge-info'
        case 'Delivered': return 'badge-success'
        case 'Failed': return 'badge-danger'
        case 'Skipped': return 'badge-warning'
        default: return 'badge-neutral'
      }
    }

    onMounted(() => {
      loadManifest()
    })

    return {
      dir,
      loading,
      error,
      manifest,
      t,
      loadManifest,
      updateStopStatus,
      printManifest,
      statusClass,
      stopStatusClass,
    }
  }
}
</script>

<style scoped>
.driver-manifest-view {
  padding: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
}
.manifest-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 1.25rem;
}
.run-badge {
  background: #1e293b;
  color: #fff;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}
.driver-info {
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.info-row {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
}
.stop-card {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 1rem;
}
.completed-stop {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.stop-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.stop-number {
  background: #2563eb;
  color: #fff;
  border-radius: 0.375rem;
  padding: 0.4rem 0.8rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  line-height: 1;
}
.stop-number span {
  font-size: 0.65rem;
  opacity: 0.8;
}
.stop-number strong {
  font-size: 1.1rem;
}
.address-box, .contact-box {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}
@media print {
  .print\:hidden {
    display: none !important;
  }
}
</style>

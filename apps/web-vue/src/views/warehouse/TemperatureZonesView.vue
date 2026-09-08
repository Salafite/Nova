<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('temp-zones-title', 'Warehouse Temperature Zones & Bins') }}</h1>
        <p class="page-subtitle">{{ t('temp-zones-sub', 'Configure temperature-controlled zones (Ambient, Chilled, Frozen, Deep Freeze) and assign bin constraints.') }}</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="load">
          <span class="material-symbols-outlined icon-xs">refresh</span> {{ t('refresh', 'Refresh') }}
        </button>
        <button class="btn-primary" @click="openCreateZoneModal">
          <span class="material-symbols-outlined icon-xs">add</span> {{ t('new-temp-zone', 'New Temperature Zone') }}
        </button>
      </div>
    </div>

    <!-- Summary KPI Cards -->
    <div class="stats-row mb-6">
      <div class="stat-card">
        <div class="stat-num">{{ zones.length }}</div>
        <div class="stat-lbl">{{ t('total-zones', 'Total Zones') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num text-blue">{{ chilledZonesCount }}</div>
        <div class="stat-lbl">{{ t('chilled-zones', 'Chilled Zones (2-4°C)') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num text-purple">{{ frozenZonesCount }}</div>
        <div class="stat-lbl">{{ t('frozen-zones', 'Frozen / Deep Freeze') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" :class="excursionZonesCount > 0 ? 'text-red' : 'text-green'">
          {{ excursionZonesCount }}
        </div>
        <div class="stat-lbl">{{ t('excursions', 'Active Excursions') }}</div>
      </div>
    </div>

    <!-- Warehouse Filter & Search Bar -->
    <div class="filter-card mb-4 flex justify-between items-center gap-4">
      <div class="flex gap-3 items-center flex-1">
        <div class="search-wrap flex-1">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            v-model="searchQuery"
            class="form-input search-input"
            :placeholder="t('search-zones-placeholder', 'Search by zone name, code, or sensor ID...')"
          />
        </div>
        <select v-model="selectedWarehouse" class="form-input select-wh">
          <option value="">{{ t('all-warehouses', 'All Warehouses') }}</option>
          <option v-for="wh in warehouses" :key="wh.id" :value="wh.id">{{ wh.name }}</option>
        </select>
        <select v-model="selectedZoneType" class="form-input select-type">
          <option value="">{{ t('all-zone-types', 'All Zone Types') }}</option>
          <option value="Ambient">Ambient (15°C to 25°C)</option>
          <option value="Chilled">Chilled (2°C to 4°C)</option>
          <option value="Frozen">Frozen (≤ -18°C)</option>
          <option value="Deep Freeze">Deep Freeze (≤ -25°C)</option>
        </select>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filteredZones.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">ac_unit</span>
      <p>{{ t('no-zones-found', 'No temperature zones found matching the selected filters.') }}</p>
    </div>

    <!-- Zones Grid / Table -->
    <div v-else class="zones-grid mb-6">
      <div v-for="zone in filteredZones" :key="zone.id" class="zone-card">
        <div class="zone-card-header flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined zone-type-icon" :class="'icon-' + getZoneTypeClass(zone.zone_type)">
              {{ getZoneIcon(zone.zone_type) }}
            </span>
            <div>
              <h3 class="zone-name">{{ zone.name }}</h3>
              <span class="zone-code">{{ zone.zone_code }}</span>
            </div>
          </div>
          <span class="badge" :class="getZoneStatusBadge(zone.status)">
            {{ zone.status }}
          </span>
        </div>

        <div class="zone-card-body">
          <div class="temp-readout-box my-3 flex items-center justify-between">
            <div>
              <span class="readout-label">{{ t('current-temp', 'Current Temp') }}</span>
              <div class="readout-val" :class="getTempStatusClass(zone)">
                {{ zone.current_temperature !== null && zone.current_temperature !== undefined ? zone.current_temperature + '°C' : '-' }}
              </div>
            </div>
            <div class="text-right">
              <span class="readout-label">{{ t('target-range', 'Target Range') }}</span>
              <div class="readout-range font-mono">
                {{ zone.min_temperature }}°C ~ {{ zone.max_temperature }}°C
              </div>
            </div>
          </div>

          <div class="zone-info-grid">
            <div class="info-item">
              <span class="info-label">{{ t('warehouse', 'Warehouse') }}:</span>
              <span>{{ getWarehouseName(zone.warehouse_id) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('zone-type', 'Zone Type') }}:</span>
              <span class="badge" :class="'badge-' + getZoneTypeClass(zone.zone_type)">{{ zone.zone_type }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('sensor-id', 'Sensor ID') }}:</span>
              <span class="font-mono text-xs">{{ zone.sensor_id || t('none', 'None') }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('capacity', 'Capacity') }}:</span>
              <span>{{ zone.capacity_m3 ? zone.capacity_m3 + ' m³' : '-' }}</span>
            </div>
          </div>
        </div>

        <div class="zone-card-footer flex justify-between items-center">
          <button class="btn-link-sm" @click="viewZoneBins(zone)">
            <span class="material-symbols-outlined icon-xs">grid_view</span>
            {{ t('view-bins', 'Assigned Bins') }}
          </button>
          <div class="flex gap-2">
            <button class="btn-icon" @click="editZone(zone)" :title="t('edit', 'Edit')">
              <span class="material-symbols-outlined icon-xs">edit</span>
            </button>
            <button class="btn-icon text-red" @click="deleteZone(zone)" :title="t('delete', 'Delete')">
              <span class="material-symbols-outlined icon-xs">delete</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Zone Create / Edit Modal -->
    <Teleport to="body">
      <div v-if="showZoneModal" class="modal-overlay" @click.self="showZoneModal = false">
        <div class="modal-dialog" :dir="dir">
          <div class="modal-header">
            <h3 class="modal-title">{{ editingZone ? t('edit-zone', 'Edit Temperature Zone') : t('new-temp-zone', 'New Temperature Zone') }}</h3>
            <button class="modal-close" @click="showZoneModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group mb-3">
              <label class="form-label">{{ t('name', 'Zone Name') }} <span class="text-red">*</span></label>
              <input type="text" v-model="zoneForm.name" class="form-input w-full" placeholder="e.g. Cold Storage Chamber 1" required />
            </div>

            <div class="grid grid-cols-2 gap-3 mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('warehouse', 'Warehouse') }} <span class="text-red">*</span></label>
                <select v-model="zoneForm.warehouse_id" class="form-input w-full" required>
                  <option v-for="wh in warehouses" :key="wh.id" :value="wh.id">{{ wh.name }}</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('zone-type', 'Zone Type') }} <span class="text-red">*</span></label>
                <select v-model="zoneForm.zone_type" class="form-input w-full" @change="onZoneTypeChange">
                  <option value="Ambient">Ambient (15°C to 25°C)</option>
                  <option value="Chilled">Chilled (2°C to 4°C)</option>
                  <option value="Frozen">Frozen (≤ -18°C)</option>
                  <option value="Deep Freeze">Deep Freeze (≤ -25°C)</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-3 gap-3 mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('min-temp', 'Min Temp (°C)') }} <span class="text-red">*</span></label>
                <input type="number" step="0.1" v-model.number="zoneForm.min_temperature" class="form-input w-full" required />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('target-temp', 'Target Temp (°C)') }} <span class="text-red">*</span></label>
                <input type="number" step="0.1" v-model.number="zoneForm.target_temperature" class="form-input w-full" required />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('max-temp', 'Max Temp (°C)') }} <span class="text-red">*</span></label>
                <input type="number" step="0.1" v-model.number="zoneForm.max_temperature" class="form-input w-full" required />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('sensor-id', 'IoT Sensor ID') }}</label>
                <input type="text" v-model="zoneForm.sensor_id" class="form-input w-full" placeholder="e.g. SENSOR-COLD-01" />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('capacity-m3', 'Capacity (m³)') }}</label>
                <input type="number" step="0.1" v-model.number="zoneForm.capacity_m3" class="form-input w-full" placeholder="0.00" />
              </div>
            </div>

            <div class="form-group mb-3">
              <label class="form-label">{{ t('notes', 'Notes & Remarks') }}</label>
              <textarea v-model="zoneForm.notes" class="form-input form-textarea w-full" rows="2"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-outline" @click="showZoneModal = false">{{ t('cancel', 'Cancel') }}</button>
            <button class="btn-primary" @click="saveZone" :disabled="saving">
              {{ saving ? t('saving', 'Saving...') : t('save', 'Save Zone') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const zones = ref([])
const warehouses = ref([])
const searchQuery = ref('')
const selectedWarehouse = ref('')
const selectedZoneType = ref('')

const showZoneModal = ref(false)
const editingZone = ref(null)

const zoneForm = reactive({
  name: '',
  warehouse_id: 1,
  zone_type: 'Ambient',
  min_temperature: 15.0,
  max_temperature: 25.0,
  target_temperature: 20.0,
  sensor_id: '',
  capacity_m3: 0,
  notes: ''
})

const chilledZonesCount = computed(() => {
  return zones.value.filter(z => z.zone_type === 'Chilled').length
})

const frozenZonesCount = computed(() => {
  return zones.value.filter(z => z.zone_type === 'Frozen' || z.zone_type === 'Deep Freeze').length
})

const excursionZonesCount = computed(() => {
  return zones.value.filter(z => z.status === 'Excursion' || z.status === 'Warning').length
})

const filteredZones = computed(() => {
  let list = zones.value
  if (selectedWarehouse.value) {
    list = list.filter(z => Number(z.warehouse_id) === Number(selectedWarehouse.value))
  }
  if (selectedZoneType.value) {
    list = list.filter(z => z.zone_type === selectedZoneType.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(z =>
      (z.name && z.name.toLowerCase().includes(q)) ||
      (z.zone_code && z.zone_code.toLowerCase().includes(q)) ||
      (z.sensor_id && z.sensor_id.toLowerCase().includes(q))
    )
  }
  return list
})

function getWarehouseName(whId) {
  const w = warehouses.value.find(x => x.id === whId)
  return w ? w.name : `#${whId}`
}

function getZoneTypeClass(type) {
  const tStr = (type || '').toLowerCase()
  if (tStr.includes('chill')) return 'chilled'
  if (tStr.includes('deep')) return 'deep-freeze'
  if (tStr.includes('froz')) return 'frozen'
  return 'ambient'
}

function getZoneIcon(type) {
  const tStr = (type || '').toLowerCase()
  if (tStr.includes('chill')) return 'ac_unit'
  if (tStr.includes('deep')) return 'severe_cold'
  if (tStr.includes('froz')) return 'ac_unit'
  return 'thermostat'
}

function getZoneStatusBadge(status) {
  const map = {
    Normal: 'badge-active',
    Warning: 'badge-warning',
    Excursion: 'badge-danger',
    Maintenance: 'badge-info',
    Inactive: 'badge-inactive'
  }
  return map[status] || 'badge-inactive'
}

function getTempStatusClass(zone) {
  if (zone.current_temperature === null || zone.current_temperature === undefined) return 'text-muted'
  if (zone.current_temperature < zone.min_temperature || zone.current_temperature > zone.max_temperature) {
    return 'text-red font-bold'
  }
  return 'text-green font-bold'
}

function onZoneTypeChange() {
  const presets = {
    Ambient: { min: 15.0, max: 25.0, target: 20.0 },
    Chilled: { min: 2.0, max: 4.0, target: 3.0 },
    Frozen: { min: -22.0, max: -18.0, target: -20.0 },
    'Deep Freeze': { min: -30.0, max: -25.0, target: -28.0 }
  }
  const p = presets[zoneForm.zone_type]
  if (p) {
    zoneForm.min_temperature = p.min
    zoneForm.max_temperature = p.max
    zoneForm.target_temperature = p.target
  }
}

function openCreateZoneModal() {
  editingZone.value = null
  zoneForm.name = ''
  zoneForm.warehouse_id = warehouses.value[0]?.id || 1
  zoneForm.zone_type = 'Ambient'
  zoneForm.min_temperature = 15.0
  zoneForm.max_temperature = 25.0
  zoneForm.target_temperature = 20.0
  zoneForm.sensor_id = ''
  zoneForm.capacity_m3 = 0
  zoneForm.notes = ''
  showZoneModal.value = true
}

function editZone(zone) {
  editingZone.value = zone
  zoneForm.name = zone.name
  zoneForm.warehouse_id = zone.warehouse_id
  zoneForm.zone_type = zone.zone_type
  zoneForm.min_temperature = zone.min_temperature
  zoneForm.max_temperature = zone.max_temperature
  zoneForm.target_temperature = zone.target_temperature
  zoneForm.sensor_id = zone.sensor_id || ''
  zoneForm.capacity_m3 = zone.capacity_m3 || 0
  zoneForm.notes = zone.notes || ''
  showZoneModal.value = true
}

async function saveZone() {
  if (!zoneForm.name.trim()) {
    toast(t('name-required', 'Zone name is required'), 'error')
    return
  }
  saving.value = true
  try {
    if (editingZone.value) {
      await api.put(`/T0124I/${editingZone.value.id}`, zoneForm)
      toast(t('zone-updated', 'Temperature zone updated'), 'success')
    } else {
      await api.post('/T0124I/', zoneForm)
      toast(t('zone-created', 'Temperature zone created'), 'success')
    }
    showZoneModal.value = false
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || t('failed-save', 'Failed to save zone'), 'error')
  } finally {
    saving.value = false
  }
}

async function deleteZone(zone) {
  if (!confirm(`Delete temperature zone "${zone.name}"?`)) return
  try {
    await api.delete(`/T0124I/${zone.id}`)
    toast(t('zone-deleted', 'Temperature zone deleted'), 'success')
    await load()
  } catch (err) {
    toast(err.response?.data?.detail || t('failed-delete', 'Failed to delete zone'), 'error')
  }
}

function viewZoneBins(zone) {
  toast(`Viewing bins for zone ${zone.name}`, 'info')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [zRes, whRes] = await Promise.all([
      api.get('/T0124I/').catch(() => ({ data: [] })),
      api.get('/T0008I/').catch(() => ({ data: [] }))
    ])
    zones.value = zRes.data || []
    warehouses.value = whRes.data || []
  } catch {
    error.value = t('failed-load', 'Failed to load temperature zones')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #64748b; margin-top: 4px; }
.mb-6 { margin-bottom: 24px; }
.mb-4 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 12px; }
.my-3 { margin-top: 12px; margin-bottom: 12px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.w-full { width: 100%; }

.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
.stat-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; text-align: center; }
.stat-num { font-size: 26px; font-weight: 700; color: #1e293b; }
.stat-lbl { font-size: 12px; color: #64748b; margin-top: 2px; }
.text-blue { color: #0284c7; }
.text-purple { color: #7c3aed; }
.text-red { color: #dc2626; }
.text-green { color: #16a34a; }

.filter-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; }
.search-wrap { position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #94a3b8; }
.search-input { padding-left: 36px; }
.select-wh, .select-type { min-width: 180px; }

.zones-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.zone-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; }
.zone-name { font-size: 15px; font-weight: 700; color: #1e293b; margin: 0; }
.zone-code { font-family: monospace; font-size: 11px; color: #64748b; }
.zone-type-icon { font-size: 28px; padding: 6px; border-radius: 8px; }
.icon-ambient { color: #d97706; background: #fef3c7; }
.icon-chilled { color: #0284c7; background: #e0f2fe; }
.icon-frozen { color: #2563eb; background: #dbeafe; }
.icon-deep-freeze { color: #7c3aed; background: #ede9fe; }

.temp-readout-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; }
.readout-label { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; }
.readout-val { font-size: 20px; }
.readout-range { font-size: 12px; color: #475569; }

.zone-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; }
.info-item { display: flex; flex-direction: column; }
.info-label { color: #94a3b8; font-size: 10px; font-weight: 600; }

.zone-card-footer { border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 12px; }
.btn-link-sm { background: none; border: none; color: #5d3fd3; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; padding: 0; }
.btn-link-sm:hover { text-decoration: underline; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-warning { background: #fef3c7; color: #d97706; }
.badge-danger { background: #fee2e2; color: #dc2626; }
.badge-info { background: #e0f2fe; color: #0284c7; }
.badge-inactive { background: #f1f5f9; color: #64748b; }

.badge-ambient { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.badge-chilled { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
.badge-frozen { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-deep-freeze { background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe; }

.btn-primary { background: #5d3fd3; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary:hover { background: #4a32b0; }
.btn-secondary { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-outline { background: transparent; border: 1px solid #cbd5e1; color: #475569; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-icon { background: none; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
.btn-icon:hover { background: #f8fafc; }

.form-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }
.form-textarea { resize: vertical; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 10000; }
.modal-dialog { background: #fff; border-radius: 12px; width: 90%; max-width: 540px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; }
.modal-header { padding: 16px 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-close { background: none; border: none; font-size: 24px; color: #94a3b8; cursor: pointer; }
.modal-body { padding: 20px; max-height: 75vh; overflow-y: auto; }
.modal-footer { padding: 14px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 8px; }

.icon-xs { font-size: 16px !important; }
.font-mono { font-family: monospace; }
.grid { display: grid; }
.grid-cols-2 { grid-template-columns: 1fr 1fr; }
.grid-cols-3 { grid-template-columns: 1fr 1fr 1fr; }
</style>

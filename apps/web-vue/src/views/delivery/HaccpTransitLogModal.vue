<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-overlay" @click.self="$emit('update:modelValue', false)">
      <div class="modal-dialog" :dir="dir">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-blue">ac_unit</span>
            <h3 class="modal-title">{{ t('log-transit-temp', 'Log HACCP Transit Temperature') }}</h3>
          </div>
          <button class="modal-close" @click="$emit('update:modelValue', false)">&times;</button>
        </div>

        <div class="modal-body">
          <p class="text-sm text-muted mb-4">
            {{ t('transit-log-desc', 'Record physical temperature checkpoint reading for cold-chain compliance tracking.') }}
          </p>

          <div class="form-group mb-3">
            <label class="form-label">{{ t('checkpoint-stage', 'Checkpoint Stage') }} <span class="text-red">*</span></label>
            <select v-model="form.checkpoint_stage" class="form-input w-full">
              <option value="VehicleDeparture">Vehicle Departure (Dock Departure)</option>
              <option value="TransitCheckpoint">In-Transit Checkpoint</option>
              <option value="DestinationDelivery">Destination Delivery (Customer Dock)</option>
              <option value="GoodsReceipt">Inbound Goods Receipt</option>
            </select>
          </div>

          <div class="form-group mb-3">
            <label class="form-label">{{ t('checkpoint-name', 'Checkpoint Description / Name') }} <span class="text-red">*</span></label>
            <input type="text" v-model="form.checkpoint_name" class="form-input w-full" placeholder="e.g. Stop #1 Customer Arrival Reading" required />
          </div>

          <div class="grid grid-cols-2 gap-3 mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('recorded-temp', 'Recorded Temp (°C)') }} <span class="text-red">*</span></label>
              <input type="number" step="0.1" v-model.number="form.recorded_temperature" class="form-input w-full" placeholder="e.g. -19.5" required />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('ambient-temp', 'Ambient Outside Temp (°C)') }}</label>
              <input type="number" step="0.1" v-model.number="form.ambient_temperature" class="form-input w-full" placeholder="e.g. 28.0" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 mb-3">
            <div class="form-group">
              <label class="form-label">{{ t('batch-number', 'Batch / Lot #') }}</label>
              <input type="text" v-model="form.batch_number" class="form-input w-full" placeholder="Optional batch #" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('sensor-device', 'Sensor / Probe ID') }}</label>
              <input type="text" v-model="form.sensor_device_id" class="form-input w-full" placeholder="e.g. PROBE-01" />
            </div>
          </div>

          <div class="form-group mb-3">
            <label class="form-label">{{ t('corrective-action', 'Corrective Action (if excursion occurred)') }}</label>
            <textarea v-model="form.corrective_action" class="form-input w-full" rows="2" placeholder="Describe any corrective actions taken..."></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="$emit('update:modelValue', false)">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="submitLog" :disabled="submitting || form.recorded_temperature === null">
            <span class="material-symbols-outlined icon-xs">check</span>
            {{ submitting ? t('saving', 'Saving...') : t('submit-log', 'Submit Log') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'

const props = defineProps({
  modelValue: Boolean,
  deliveryRunId: { type: Number, default: null },
  deliveryStopId: { type: Number, default: null },
  vehicleId: { type: Number, default: null },
  compartmentId: { type: Number, default: null },
  defaultStage: { type: String, default: 'TransitCheckpoint' }
})

const emit = defineEmits(['update:modelValue', 'logged'])

const { t, dir } = useI18n()
const { show: toast } = useToast()
const submitting = ref(false)

const form = reactive({
  checkpoint_stage: props.defaultStage,
  checkpoint_name: 'Transit Temperature Check',
  recorded_temperature: null,
  ambient_temperature: null,
  batch_number: '',
  sensor_device_id: '',
  corrective_action: ''
})

async function submitLog() {
  if (form.recorded_temperature === null || isNaN(form.recorded_temperature)) {
    toast(t('temp-required', 'Recorded temperature is required'), 'error')
    return
  }
  submitting.value = true
  try {
    const payload = {
      checkpoint_stage: form.checkpoint_stage,
      checkpoint_name: form.checkpoint_name,
      recorded_temperature: form.recorded_temperature,
      ambient_temperature: form.ambient_temperature,
      delivery_run_id: props.deliveryRunId,
      delivery_stop_id: props.deliveryStopId,
      vehicle_id: props.vehicleId,
      compartment_id: props.compartmentId,
      batch_number: form.batch_number || undefined,
      sensor_device_id: form.sensor_device_id || undefined,
      corrective_action: form.corrective_action || undefined,
      logged_by_id: 1
    }
    const res = await api.post('/T0128I/checkpoint', payload)
    toast(t('log-recorded-success', 'HACCP temperature checkpoint recorded'), 'success')
    emit('logged', res.data)
    emit('update:modelValue', false)
  } catch (err) {
    toast(err.response?.data?.detail || t('failed-log', 'Failed to record checkpoint log'), 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 10000; }
.modal-dialog { background: #fff; border-radius: 12px; width: 90%; max-width: 520px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; }
.modal-header { padding: 16px 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-close { background: none; border: none; font-size: 24px; color: #94a3b8; cursor: pointer; }
.modal-body { padding: 20px; max-height: 75vh; overflow-y: auto; }
.modal-footer { padding: 14px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 8px; }

.form-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 4px; }
.btn-primary { background: #5d3fd3; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-outline { background: transparent; border: 1px solid #cbd5e1; color: #475569; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }

.icon-xs { font-size: 16px !important; }
.text-blue { color: #0284c7; }
.text-red { color: #dc2626; }
.text-muted { color: #64748b; }
.w-full { width: 100%; }
.grid { display: grid; }
.grid-cols-2 { grid-template-columns: 1fr 1fr; }
.gap-3 { gap: 12px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.flex { display: flex; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
</style>

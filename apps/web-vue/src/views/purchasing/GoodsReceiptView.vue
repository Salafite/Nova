<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('gr-title', 'Goods Receipt') }}</h1>
        <p class="page-subtitle">{{ t('gr-sub', 'Record and manage goods received from suppliers') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd"><span class="material-symbols-outlined">add</span> {{ t('new-gr', 'New Receipt') }}</button>
    </div>
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">inventory_2</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('gr-number', 'Receipt #') }}</th>
              <th>{{ t('po-ref', 'PO Ref') }}</th>
              <th>{{ t('supplier') }}</th>
              <th>Warehouse</th>
              <th class="text-center">{{ t('items', 'Items') }}</th>
              <th>{{ t('date') }}</th>
              <th>{{ t('status') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><span class="mono">{{ item.receipt_number }}</span></td>
              <td>{{ item.purchase_order_id || '-' }}</td>
              <td>{{ supplierName(item.supplier_id) }}</td>
              <td>{{ warehouseName(item.warehouse_id) }}</td>
              <td class="text-center">{{ item.total_items || item.lines?.length || 0 }}</td>
              <td>{{ formatDate(item.receipt_date || item.created_at) }}</td>
              <td><span class="badge" :class="item.status === 'completed' ? 'badge-active' : 'badge-disabled'">{{ item.status || 'Draft' }}</span></td>
              <td class="text-center">
                <button class="btn-icon" @click="editItem(item)"><span class="material-symbols-outlined">edit</span></button>
                <button class="btn-icon text-red-500" @click="deleteItem(item)"><span class="material-symbols-outlined">delete</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header"><h3>{{ editing ? t('edit-gr', 'Edit Receipt') : t('new-gr', 'New Receipt') }}</h3><button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button></div>
        <div class="modal-body">
          <div class="form-group"><label>{{ t('gr-number', 'Receipt #') }} <span class="text-red-500">*</span></label><input type="text" v-model="form.receipt_number" class="form-input" /></div>
          <div class="form-group"><label>{{ t('po-ref', 'Purchase Order') }}</label><input type="number" v-model.number="form.purchase_order_id" class="form-input" /></div>
          <div class="form-group"><label>{{ t('supplier') }}</label><select v-model="form.supplier_id" class="form-input"><option value="">-- Select --</option><option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name || s.company_name }}</option></select></div>
          <div class="form-group"><label>Warehouse</label><select v-model="form.warehouse_id" class="form-input"><option value="">-- Select --</option><option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option></select></div>
          <div class="form-group"><label>{{ t('date') }}</label><input type="date" v-model="form.receipt_date" class="form-input" /></div>
          <div class="form-group"><label>{{ t('status') }}</label><select v-model="form.status" class="form-input"><option value="Draft">Draft</option><option value="completed">Completed</option></select></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
        </div>
      </div>
    </div>
    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + confirmTarget.receipt_number" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
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
const items = ref([])
const suppliers = ref([])
const warehouses = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ receipt_number: '', purchase_order_id: null, supplier_id: null, warehouse_id: null, receipt_date: '', status: 'Draft' })
const editId = ref(null)
const confirmTarget = ref(null)
function formatDate(d) { if (!d) return '-'; return new Date(d).toLocaleDateString() }
function supplierName(id) { const s = suppliers.value.find(x => x.id === id); return s ? (s.name || s.company_name) : `#${id}` }
function warehouseName(id) { const w = warehouses.value.find(x => x.id === id); return w ? w.name : `#${id}` }
async function load() { loading.value = true; error.value = ''; try { const [gRes, sRes, wRes] = await Promise.all([api.get('/T0075I/'), api.get('/T0103I/').catch(() => ({ data: [] })), api.get('/T0008I/').catch(() => ({ data: [] }))]); items.value = gRes.data || []; suppliers.value = sRes.data || []; warehouses.value = wRes.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
function openAdd() { editing.value = false; editId.value = null; form.value = { receipt_number: '', purchase_order_id: null, supplier_id: null, warehouse_id: null, receipt_date: '', status: 'Draft' }; showModal.value = true }
function editItem(item) { editing.value = true; editId.value = item.id; form.value = { receipt_number: item.receipt_number, purchase_order_id: item.purchase_order_id, supplier_id: item.supplier_id, warehouse_id: item.warehouse_id, receipt_date: item.receipt_date || '', status: item.status || 'Draft' }; showModal.value = true }
function closeModal() { showModal.value = false }
async function saveItem() { saving.value = true; try { if (editing.value) { await api.put(`/T0075I/${editId.value}`, form.value); toast('Receipt ' + t('saved-ok'), 'success') } else { await api.post('/T0075I/', form.value); toast('Receipt ' + t('saved-ok'), 'success') } closeModal(); await load() } catch { toast(t('failed-save'), 'error') } finally { saving.value = false } }
async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) { confirmTarget.value = null; try { await api.delete(`/T0075I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); toast('Receipt deleted', 'success') } catch { toast(t('failed-save'), 'error') } }
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
.mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5d3fd3; font-weight: 600; }
.text-red-500 { color: #e53935; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-disabled { background: #f5f5f5; color: #999; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #5d3fd3; color: #fff; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary .material-symbols-outlined { font-size: 18px; }
.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; background: #f0f0f4; color: #333; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-secondary:hover { background: #e0e0e0; }
.btn-icon { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: none; border-radius: 6px; background: none; cursor: pointer; color: #666; }
.btn-icon:hover { background: #f0f0f4; }
.btn-icon .material-symbols-outlined { font-size: 18px; }
.mb-6 { margin-bottom: 24px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal { background: #fff; border-radius: 12px; width: 480px; max-width: 90vw; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1a1a2e; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid #eee; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #5d3fd3; }
select.form-input { appearance: auto; }
</style>
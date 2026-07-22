<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('opp-title', 'Opportunities') }}</h1>
        <p class="page-subtitle">{{ t('opp-sub', 'Manage sales opportunities and pipeline') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd"><span class="material-symbols-outlined">add</span> {{ t('new-opp', 'New Opportunity') }}</button>
    </div>
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">trending_up</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('name') }}</th>
              <th>{{ t('customer') }}</th>
              <th class="text-center">{{ t('amount', 'Amount') }}</th>
              <th>{{ t('stage') }}</th>
              <th>{{ t('probability', 'Probability') }}</th>
              <th>{{ t('expected-close', 'Expected Close') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><strong>{{ item.name || item.opportunity_name }}</strong></td>
              <td>{{ customerName(item.customer_id) }}</td>
              <td class="text-center">{{ formatCurrency(item.expected_amount || item.amount) }}</td>
              <td><span class="badge" :class="'badge-' + (item.stage || 'Prospecting').toLowerCase()">{{ item.stage || 'Prospecting' }}</span></td>
              <td>{{ item.probability || 0 }}%</td>
              <td>{{ item.expected_close_date ? formatDate(item.expected_close_date) : '-' }}</td>
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
        <div class="modal-header"><h3>{{ editing ? t('edit-opp', 'Edit Opportunity') : t('new-opp', 'New Opportunity') }}</h3><button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button></div>
        <div class="modal-body">
          <div class="form-group"><label>{{ t('name') }} <span class="text-red-500">*</span></label><input type="text" v-model="form.name" class="form-input" /></div>
          <div class="form-group"><label>{{ t('customer') }}</label><select v-model="form.customer_id" class="form-input"><option value="">-- Select --</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name || c.company_name }}</option></select></div>
          <div class="form-group"><label>{{ t('amount', 'Amount') }}</label><input type="number" step="0.01" v-model.number="form.expected_amount" class="form-input" /></div>
          <div class="form-group"><label>{{ t('stage') }}</label><select v-model="form.stage" class="form-input"><option value="Prospecting">Prospecting</option><option value="Qualification">Qualification</option><option value="Needs Analysis">Needs Analysis</option><option value="Proposal">Proposal</option><option value="Negotiation">Negotiation</option><option value="Closed Won">Closed Won</option><option value="Closed Lost">Closed Lost</option></select></div>
          <div class="form-group"><label>{{ t('probability') }}</label><input type="number" min="0" max="100" v-model.number="form.probability" class="form-input" /></div>
          <div class="form-group"><label>{{ t('expected-close', 'Expected Close') }}</label><input type="date" v-model="form.expected_close_date" class="form-input" /></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
        </div>
      </div>
    </div>
    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + (confirmTarget.name || confirmTarget.opportunity_name)" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
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
const customers = ref([])
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ name: '', customer_id: null, expected_amount: 0, stage: 'Prospecting', probability: 0, expected_close_date: '' })
const editId = ref(null)
const confirmTarget = ref(null)
function formatDate(d) { if (!d) return '-'; return new Date(d).toLocaleDateString() }
function formatCurrency(v) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0) }
function customerName(id) { const c = customers.value.find(x => x.id === id); return c ? (c.name || c.company_name) : `#${id}` }
async function load() { loading.value = true; error.value = ''; try { const [oRes, cRes] = await Promise.all([api.get('/T0094I/'), api.get('/T0010I/').catch(() => ({ data: [] }))]); items.value = oRes.data || []; customers.value = cRes.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
function openAdd() { editing.value = false; editId.value = null; form.value = { name: '', customer_id: null, expected_amount: 0, stage: 'Prospecting', probability: 0, expected_close_date: '' }; showModal.value = true }
function editItem(item) { editing.value = true; editId.value = item.id; form.value = { name: item.name || item.opportunity_name, customer_id: item.customer_id, expected_amount: item.expected_amount || item.amount || 0, stage: item.stage || 'Prospecting', probability: item.probability || 0, expected_close_date: item.expected_close_date || '' }; showModal.value = true }
function closeModal() { showModal.value = false }
async function saveItem() { saving.value = true; try { if (editing.value) { await api.put(`/T0094I/${editId.value}`, form.value); toast('Opportunity ' + t('saved-ok'), 'success') } else { await api.post('/T0094I/', form.value); toast('Opportunity ' + t('saved-ok'), 'success') } closeModal(); await load() } catch { toast(t('failed-save'), 'error') } finally { saving.value = false } }
async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) { confirmTarget.value = null; try { await api.delete(`/T0094I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); toast('Opportunity deleted', 'success') } catch { toast(t('failed-save'), 'error') } }
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
.text-red-500 { color: #e53935; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-prospecting { background: #e3f2fd; color: #1565c0; }
.badge-qualification { background: #fff3e0; color: #e65100; }
.badge-needs_analysis, .badge-needs-analysis { background: #fce4ec; color: #c62828; }
.badge-proposal { background: #f3e5f5; color: #7b1fa2; }
.badge-negotiation { background: #fff8e1; color: #f9a825; }
.badge-closed_won, .badge-closed-won { background: #e8f5e9; color: #1b5e20; }
.badge-closed_lost, .badge-closed-lost { background: #ffebee; color: #c62828; }
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
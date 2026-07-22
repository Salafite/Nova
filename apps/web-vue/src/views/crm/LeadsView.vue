<template>
  <div :dir="dir">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('leads-title', 'Leads') }}</h1>
        <p class="page-subtitle">{{ t('leads-sub', 'Track and manage sales leads') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd"><span class="material-symbols-outlined">add</span> {{ t('new-lead', 'New Lead') }}</button>
    </div>
    <SkeletonTable v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!items.length" class="empty-state">
      <span class="material-symbols-outlined empty-icon">person_search</span>
      <p>{{ t('no-records') }}</p>
    </div>
    <div v-else class="data-card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('name') }}</th>
              <th>{{ t('company') }}</th>
              <th>Email</th>
              <th>Phone</th>
              <th>{{ t('status') }}</th>
              <th>{{ t('source') }}</th>
              <th class="text-center">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td><strong>{{ item.contact_person || item.name }}</strong></td>
              <td>{{ item.company_name || '-' }}</td>
              <td>{{ item.email || '-' }}</td>
              <td>{{ item.phone || '-' }}</td>
              <td><span class="badge" :class="'badge-' + (item.status || 'new')">{{ item.status || 'New' }}</span></td>
              <td>{{ item.source || '-' }}</td>
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
        <div class="modal-header"><h3>{{ editing ? t('edit-lead', 'Edit Lead') : t('new-lead', 'New Lead') }}</h3><button class="btn-icon" @click="closeModal"><span class="material-symbols-outlined">close</span></button></div>
        <div class="modal-body">
          <div class="form-group"><label>{{ t('name') }} <span class="text-red-500">*</span></label><input type="text" v-model="form.contact_person" class="form-input" /></div>
          <div class="form-group"><label>{{ t('company') }}</label><input type="text" v-model="form.company_name" class="form-input" /></div>
          <div class="form-group"><label>Email</label><input type="email" v-model="form.email" class="form-input" /></div>
          <div class="form-group"><label>Phone</label><input type="text" v-model="form.phone" class="form-input" /></div>
          <div class="form-group"><label>{{ t('status') }}</label><select v-model="form.status" class="form-input"><option value="New">New</option><option value="Contacted">Contacted</option><option value="Qualified">Qualified</option><option value="Proposal">Proposal</option><option value="Won">Won</option><option value="Lost">Lost</option></select></div>
          <div class="form-group"><label>{{ t('source') }}</label><input type="text" v-model="form.source" class="form-input" /></div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">{{ t('cancel') }}</button>
          <button class="btn-primary" :disabled="saving" @click="saveItem">{{ saving ? t('saving') : t('save') }}</button>
        </div>
      </div>
    </div>
    <ConfirmDialog v-if="confirmTarget" :title="t('confirm-delete')" :message="t('confirm-delete-msg') + ' ' + (confirmTarget.contact_person || confirmTarget.name)" @confirm="executeDelete(confirmTarget)" @cancel="confirmTarget = null" />
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
const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = ref({ contact_person: '', company_name: '', email: '', phone: '', status: 'New', source: '' })
const editId = ref(null)
const confirmTarget = ref(null)
async function load() { loading.value = true; error.value = ''; try { const res = await api.get('/T0092I/'); items.value = res.data || [] } catch { error.value = t('failed-load') } finally { loading.value = false } }
function openAdd() { editing.value = false; editId.value = null; form.value = { contact_person: '', company_name: '', email: '', phone: '', status: 'New', source: '' }; showModal.value = true }
function editItem(item) { editing.value = true; editId.value = item.id; form.value = { contact_person: item.contact_person || item.name, company_name: item.company_name || '', email: item.email || '', phone: item.phone || '', status: item.status || 'New', source: item.source || '' }; showModal.value = true }
function closeModal() { showModal.value = false }
async function saveItem() { saving.value = true; try { if (editing.value) { await api.put(`/T0092I/${editId.value}`, form.value); toast('Lead ' + t('saved-ok'), 'success') } else { await api.post('/T0092I/', form.value); toast('Lead ' + t('saved-ok'), 'success') } closeModal(); await load() } catch { toast(t('failed-save'), 'error') } finally { saving.value = false } }
async function deleteItem(item) { confirmTarget.value = item }
async function executeDelete(item) { confirmTarget.value = null; try { await api.delete(`/T0092I/${item.id}`); items.value = items.value.filter(i => i.id !== item.id); toast('Lead deleted', 'success') } catch { toast(t('failed-save'), 'error') } }
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
.badge-new { background: #e3f2fd; color: #1565c0; }
.badge-Contacted { background: #fff3e0; color: #e65100; }
.badge-Qualified { background: #e8f5e9; color: #2e7d32; }
.badge-Proposal { background: #f3e5f5; color: #7b1fa2; }
.badge-Won { background: #e8f5e9; color: #1b5e20; }
.badge-Lost { background: #ffebee; color: #c62828; }
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
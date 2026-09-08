<template>
  <div :dir="dir" class="edi-partners-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="page-title">{{ t('edi-partners-title', 'EDI Trading Partners') }}</h1>
        <p class="page-subtitle">{{ t('edi-partners-sub', 'Configure B2B Supermarket Chains, Retailers, Delimiters & Automated Order Policies') }}</p>
      </div>
      <div class="header-actions">
        <button class="btn-outline" @click="router.push('/integrations/edi-gateway')">
          <span class="material-symbols-outlined">hub</span>
          {{ t('edi-gateway', 'EDI Gateway') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-sku-mapping')">
          <span class="material-symbols-outlined">dataset</span>
          {{ t('sku-matrix', 'SKU Matrix') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-pallet-sscc')">
          <span class="material-symbols-outlined">inventory_2</span>
          {{ t('sscc-pallets', 'SSCC Pallets') }}
        </button>
        <button class="btn-outline" @click="router.push('/integrations/edi-transactions')">
          <span class="material-symbols-outlined">receipt_long</span>
          {{ t('edi-transactions', 'Transactions') }}
        </button>
        <button class="btn-primary" @click="openCreateModal">
          <span class="material-symbols-outlined">add</span>
          {{ t('new-partner', 'New Trading Partner') }}
        </button>
        <button class="btn-icon" @click="loadData" :title="t('refresh', 'Refresh')">
          <span class="material-symbols-outlined">refresh</span>
        </button>
      </div>
    </div>

    <!-- KPI Metric Cards -->
    <div class="kpi-grid mb-6">
      <div class="kpi-card">
        <div class="kpi-icon icon-purple"><span class="material-symbols-outlined">corporate_fare</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('total-partners', 'Total Partners') }}</span>
          <span class="kpi-value">{{ kpis.total }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-green"><span class="material-symbols-outlined">check_circle</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('active-connections', 'Active EDI Connections') }}</span>
          <span class="kpi-value">{{ kpis.active }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-blue"><span class="material-symbols-outlined">code</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('ansi-x12-partners', 'ANSI X12 Partners') }}</span>
          <span class="kpi-value">{{ kpis.x12 }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-teal"><span class="material-symbols-outlined">language</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('edifact-partners', 'UN/EDIFACT Partners') }}</span>
          <span class="kpi-value">{{ kpis.edifact }}</span>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon icon-amber"><span class="material-symbols-outlined">bolt</span></div>
        <div class="kpi-info">
          <span class="kpi-label">{{ t('auto-confirm-enabled', 'Auto-Confirm Enabled') }}</span>
          <span class="kpi-value">{{ kpis.autoConfirm }}</span>
        </div>
      </div>
    </div>

    <!-- Partner Filter & Table Section -->
    <div class="data-card">
      <div class="card-filter-bar">
        <div class="search-wrap">
          <span class="material-symbols-outlined search-icon">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('search-partners', 'Search partner by name, code, sender ID, receiver ID...')"
          />
        </div>

        <div class="filters-wrap">
          <select v-model="filterStandard" class="filter-select">
            <option value="">{{ t('all-standards', 'All Standards') }}</option>
            <option value="ANSI_X12">ANSI X12</option>
            <option value="EDIFACT">UN/EDIFACT</option>
          </select>

          <select v-model="filterProtocol" class="filter-select">
            <option value="">{{ t('all-protocols', 'All Protocols') }}</option>
            <option value="MANUAL">MANUAL</option>
            <option value="API">API</option>
            <option value="AS2">AS2</option>
            <option value="SFTP">SFTP</option>
          </select>

          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ t('all-statuses', 'All Statuses') }}</option>
            <option value="active">{{ t('active-only', 'Active Only') }}</option>
            <option value="inactive">{{ t('inactive-only', 'Inactive Only') }}</option>
          </select>
        </div>
      </div>

      <SkeletonTable v-if="loading" />
      <ErrorState v-else-if="error" :message="error" @retry="loadData" />

      <div v-else-if="!filteredPartners.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">corporate_fare</span>
        <p>{{ t('no-partners-found', 'No EDI trading partners found.') }}</p>
        <button class="btn-primary" @click="openCreateModal">{{ t('create-first-partner', 'Create First Trading Partner') }}</button>
      </div>

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('partner-code', 'Partner Code') }}</th>
              <th>{{ t('company-name', 'Company Name') }}</th>
              <th>{{ t('customer-supplier', 'Linked Account') }}</th>
              <th>{{ t('edi-standard', 'Standard') }}</th>
              <th>{{ t('interchange-sender-receiver', 'Interchange (Sender → Receiver)') }}</th>
              <th>{{ t('delimiters', 'Delimiters') }}</th>
              <th>{{ t('order-automation', 'Automation Policy') }}</th>
              <th>{{ t('protocol', 'Protocol') }}</th>
              <th class="text-center">{{ t('status', 'Status') }}</th>
              <th class="text-center">{{ t('actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in filteredPartners" :key="p.id">
              <td>
                <span class="font-mono font-bold text-primary">{{ p.partner_code }}</span>
              </td>
              <td>
                <div>
                  <strong>{{ p.partner_name }}</strong>
                  <div v-if="p.gs1_company_prefix" class="text-xs text-muted">
                    GS1 Prefix: <span class="font-mono">{{ p.gs1_company_prefix }}</span>
                  </div>
                </div>
              </td>
              <td>
                <span v-if="p.customer_id" class="text-xs font-semibold text-blue-700">
                  Customer #{{ p.customer_id }} {{ getCustomerName(p.customer_id) }}
                </span>
                <span v-else-if="p.supplier_id" class="text-xs font-semibold text-amber-700">
                  Supplier #{{ p.supplier_id }} {{ getSupplierName(p.supplier_id) }}
                </span>
                <span v-else class="text-xs text-muted">-</span>
              </td>
              <td>
                <span class="badge" :class="p.edi_standard === 'EDIFACT' ? 'badge-edifact' : 'badge-x12'">
                  {{ p.edi_standard }}
                </span>
              </td>
              <td>
                <div class="text-xs font-mono">
                  <div><span class="text-muted">From:</span> {{ p.sender_qualifier || 'ZZ' }}:{{ p.interchange_sender_id }}</div>
                  <div><span class="text-muted">To:</span> {{ p.receiver_qualifier || 'ZZ' }}:{{ p.interchange_receiver_id }}</div>
                </div>
              </td>
              <td>
                <span class="delimiters-tag font-mono text-xs" :title="getDelimitersTitle(p)">
                  Seg: {{ p.segment_terminator || '~' }} | Elm: {{ p.element_separator || '*' }}
                </span>
              </td>
              <td>
                <div class="text-xs">
                  <div>
                    <span class="badge-xs" :class="p.auto_confirm_orders ? 'badge-success' : 'badge-disabled'">
                      {{ p.auto_confirm_orders ? 'Auto-Confirm: ON' : 'Auto-Confirm: OFF' }}
                    </span>
                  </div>
                  <div class="text-muted mt-0.5">
                    Tol: ±{{ (p.price_tolerance_percent || 0).toFixed(1) }}%
                  </div>
                </div>
              </td>
              <td>
                <span class="badge badge-doc">{{ p.communication_method || 'MANUAL' }}</span>
              </td>
              <td class="text-center">
                <span class="badge" :class="p.is_active ? 'badge-success' : 'badge-disabled'">
                  {{ p.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="text-center">
                <div class="flex justify-center gap-1">
                  <button class="btn-icon btn-sm" @click="openEditModal(p)" :title="t('edit', 'Edit Partner')">
                    <span class="material-symbols-outlined">edit</span>
                  </button>
                  <button class="btn-icon btn-sm" @click="toggleActive(p)" :title="p.is_active ? t('deactivate', 'Deactivate') : t('activate', 'Activate')">
                    <span class="material-symbols-outlined">{{ p.is_active ? 'pause_circle' : 'play_circle' }}</span>
                  </button>
                  <button class="btn-icon btn-sm text-red-600" @click="deletePartner(p)" :title="t('delete', 'Delete Partner')">
                    <span class="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Partner Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">{{ isEditing ? 'edit_note' : 'add_business' }}</span>
            <h3 class="modal-title">{{ isEditing ? t('edit-partner-title', 'Edit Trading Partner') : t('new-partner-title', 'Configure New Trading Partner') }}</h3>
          </div>
          <button class="btn-icon" @click="showModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>

        <div class="modal-body">
          <!-- Form Tabs -->
          <div class="tabs mb-4">
            <button class="tab-btn" :class="{ active: formTab === 'profile' }" @click="formTab = 'profile'">
              <span class="material-symbols-outlined">storefront</span> {{ t('tab-profile', 'Partner Profile') }}
            </button>
            <button class="tab-btn" :class="{ active: formTab === 'edi' }" @click="formTab = 'edi'">
              <span class="material-symbols-outlined">settings_ethernet</span> {{ t('tab-edi', 'EDI Envelope & Delimiters') }}
            </button>
            <button class="tab-btn" :class="{ active: formTab === 'policy' }" @click="formTab = 'policy'">
              <span class="material-symbols-outlined">rule</span> {{ t('tab-policy', 'Order Rules & Protocol') }}
            </button>
          </div>

          <!-- Tab 1: Partner Profile -->
          <div v-if="formTab === 'profile'">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('partner-name', 'Partner / Supermarket Name') }} <span class="required">*</span></label>
                <input
                  type="text"
                  v-model="form.partner_name"
                  class="form-control"
                  placeholder="e.g. Carrefour Hypermarkets UAE"
                  required
                />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('partner-code', 'Partner Code') }} <span class="required">*</span></label>
                <input
                  type="text"
                  v-model="form.partner_code"
                  class="form-control font-mono"
                  placeholder="e.g. CRF-UAE or LULU-HQ"
                  required
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('linked-customer', 'Linked Customer Account (T0010)') }}</label>
                <select v-model="form.customer_id" class="form-control">
                  <option :value="null">{{ t('none-standalone', '-- None / Standalone --') }}</option>
                  <option v-for="c in customers" :key="c.id" :value="c.id">
                    #{{ c.id }} - {{ c.name || c.customer_name }}
                  </option>
                </select>
                <span class="text-xs text-muted block mt-1">Inbound 850 POs will generate sales orders for this customer.</span>
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('gs1-prefix', 'GS1 Company Prefix (for SSCC-18 Logistics)') }}</label>
                <input
                  type="text"
                  v-model="form.gs1_company_prefix"
                  class="form-control font-mono"
                  placeholder="e.g. 0614141 or 6291041"
                  maxlength="20"
                />
                <span class="text-xs text-muted block mt-1">Used to generate unique SSCC pallet barcodes for EDI 856 ASN.</span>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="form.is_active" />
                <span class="font-semibold">{{ t('active-partner-toggle', 'Active Trading Partner (Enabled for EDI Processing)') }}</span>
              </label>
            </div>
          </div>

          <!-- Tab 2: EDI Standard & Delimiters -->
          <div v-if="formTab === 'edi'">
            <div class="form-row mb-3">
              <div class="form-group">
                <label class="form-label">{{ t('edi-standard', 'EDI Standard') }} <span class="required">*</span></label>
                <select v-model="form.edi_standard" class="form-control" @change="onStandardChange">
                  <option value="ANSI_X12">ANSI X12 (Retail / US / FMCG)</option>
                  <option value="EDIFACT">UN/EDIFACT (EANCOM / European / Global)</option>
                </select>
              </div>
              <div class="form-group flex items-end">
                <button type="button" class="btn-sm btn-outline mb-1" @click="resetDelimitersToDefault">
                  <span class="material-symbols-outlined">restart_alt</span> {{ t('load-standard-delimiters', 'Load Standard Delimiters') }}
                </button>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('sender-qualifier', 'Sender Qualifier') }}</label>
                <input
                  type="text"
                  v-model="form.sender_qualifier"
                  class="form-control font-mono"
                  placeholder="ZZ, 01, 14, 16"
                  maxlength="10"
                />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('sender-id', 'Interchange Sender ID (ISA06 / UNB 0004)') }} <span class="required">*</span></label>
                <input
                  type="text"
                  v-model="form.interchange_sender_id"
                  class="form-control font-mono"
                  placeholder="e.g. 006945855 or 5412345000013"
                  required
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('receiver-qualifier', 'Receiver Qualifier') }}</label>
                <input
                  type="text"
                  v-model="form.receiver_qualifier"
                  class="form-control font-mono"
                  placeholder="ZZ, 01, 14, 16"
                  maxlength="10"
                />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('receiver-id', 'Interchange Receiver ID (ISA08 / UNB 0010)') }} <span class="required">*</span></label>
                <input
                  type="text"
                  v-model="form.interchange_receiver_id"
                  class="form-control font-mono"
                  placeholder="e.g. NOVADISTRIB or NOVA"
                  required
                />
              </div>
            </div>

            <h4 class="text-xs font-bold text-muted uppercase mt-4 mb-2">{{ t('delimiter-syntax', 'Delimiter & Character Syntax') }}</h4>
            <div class="grid-delimiters">
              <div class="form-group">
                <label class="form-label text-xs">{{ t('segment-terminator', 'Segment Terminator') }}</label>
                <input type="text" v-model="form.segment_terminator" class="form-control font-mono text-center" maxlength="5" />
              </div>
              <div class="form-group">
                <label class="form-label text-xs">{{ t('element-separator', 'Element Separator') }}</label>
                <input type="text" v-model="form.element_separator" class="form-control font-mono text-center" maxlength="5" />
              </div>
              <div class="form-group">
                <label class="form-label text-xs">{{ t('subelement-separator', 'Subelement Delimiter') }}</label>
                <input type="text" v-model="form.subelement_separator" class="form-control font-mono text-center" maxlength="5" />
              </div>
              <div class="form-group">
                <label class="form-label text-xs">{{ t('release-char', 'EDIFACT Escape (?)') }}</label>
                <input type="text" v-model="form.release_character" class="form-control font-mono text-center" maxlength="5" />
              </div>
            </div>
          </div>

          <!-- Tab 3: Order Automation & Protocols -->
          <div v-if="formTab === 'policy'">
            <div class="form-group mb-4">
              <label class="checkbox-label font-medium">
                <input type="checkbox" v-model="form.auto_confirm_orders" />
                <span>{{ t('auto-confirm-clean-orders', 'Auto-Confirm Inbound Purchase Orders (Skip Draft Review)') }}</span>
              </label>
              <span class="text-xs text-muted block mt-1">
                When enabled, clean EDI 850 / ORDERS matching contract prices will automatically advance directly to "Confirmed" status.
              </span>
            </div>

            <div class="form-group mb-4">
              <label class="form-label">{{ t('price-tol-percent', 'Allowed Price Discrepancy Tolerance (%)') }}</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                v-model.number="form.price_tolerance_percent"
                class="form-control"
                placeholder="0.0"
              />
              <span class="text-xs text-muted block mt-1">
                Orders with pricing deviations below this percentage will not trigger a PRICE_DISCREPANCY_HOLD.
              </span>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">{{ t('comm-protocol', 'Communication Protocol') }}</label>
                <select v-model="form.communication_method" class="form-control">
                  <option value="MANUAL">MANUAL (Upload & Paste)</option>
                  <option value="API">API / Webhook Push</option>
                  <option value="AS2">AS2 (Applicability Statement 2)</option>
                  <option value="SFTP">SFTP (Secure FTP)</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('endpoint-url', 'Endpoint URL / AS2 Identifier') }}</label>
                <input
                  type="text"
                  v-model="form.endpoint_url"
                  class="form-control"
                  placeholder="https://as2.retailer.com/as2 or sftp://..."
                />
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-outline" @click="showModal = false">{{ t('cancel', 'Cancel') }}</button>
          <button class="btn-primary" @click="savePartner" :disabled="saving">
            <span v-if="saving" class="spinner-sm"></span>
            <span v-else class="material-symbols-outlined">save</span>
            {{ saving ? t('saving', 'Saving...') : t('save-partner', 'Save Trading Partner') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const router = useRouter()
const { show: toast } = useToast()
const { t, dir } = useI18n()

// State
const loading = ref(true)
const error = ref('')
const partners = ref([])
const customers = ref([])
const suppliers = ref([])

// Filters
const searchQuery = ref('')
const filterStandard = ref('')
const filterProtocol = ref('')
const filterStatus = ref('')

// Modal & Form State
const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formTab = ref('profile')
const saving = ref(false)

const form = ref({
  partner_name: '',
  partner_code: '',
  edi_standard: 'ANSI_X12',
  interchange_sender_id: '',
  interchange_receiver_id: 'NOVADISTRIB',
  sender_qualifier: 'ZZ',
  receiver_qualifier: 'ZZ',
  communication_method: 'MANUAL',
  endpoint_url: '',
  customer_id: null,
  supplier_id: null,
  segment_terminator: '~',
  element_separator: '*',
  subelement_separator: '>',
  release_character: '?',
  auto_confirm_orders: true,
  price_tolerance_percent: 0.0,
  gs1_company_prefix: '',
  is_active: true,
})

// Computed KPIs
const kpis = computed(() => {
  const total = partners.value.length
  let active = 0
  let x12 = 0
  let edifact = 0
  let autoConfirm = 0

  for (const p of partners.value) {
    if (p.is_active) active++
    if (p.edi_standard === 'ANSI_X12') x12++
    if (p.edi_standard === 'EDIFACT') edifact++
    if (p.auto_confirm_orders) autoConfirm++
  }

  return { total, active, x12, edifact, autoConfirm }
})

// Filtered Partners
const filteredPartners = computed(() => {
  return partners.value.filter(p => {
    if (filterStandard.value && p.edi_standard !== filterStandard.value) return false
    if (filterProtocol.value && p.communication_method !== filterProtocol.value) return false
    if (filterStatus.value === 'active' && !p.is_active) return false
    if (filterStatus.value === 'inactive' && p.is_active) return false

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const name = (p.partner_name || '').toLowerCase()
      const code = (p.partner_code || '').toLowerCase()
      const sId = (p.interchange_sender_id || '').toLowerCase()
      const rId = (p.interchange_receiver_id || '').toLowerCase()
      return name.includes(q) || code.includes(q) || sId.includes(q) || rId.includes(q)
    }
    return true
  })
})

function getCustomerName(id) {
  if (!id) return ''
  const c = customers.value.find(x => x.id === id)
  return c ? `(${c.name || c.customer_name})` : ''
}

function getSupplierName(id) {
  if (!id) return ''
  const s = suppliers.value.find(x => x.id === id)
  return s ? `(${s.name || s.supplier_name})` : ''
}

function getDelimitersTitle(p) {
  return `Segment: '${p.segment_terminator || '~'}' | Element: '${p.element_separator || '*'}' | Sub: '${p.subelement_separator || '>'}' | Release: '${p.release_character || '?'}'`
}

function onStandardChange() {
  resetDelimitersToDefault()
}

function resetDelimitersToDefault() {
  if (form.value.edi_standard === 'EDIFACT') {
    form.value.segment_terminator = "'"
    form.value.element_separator = "+"
    form.value.subelement_separator = ":"
    form.value.release_character = "?"
    form.value.sender_qualifier = "14"
    form.value.receiver_qualifier = "ZZ"
  } else {
    form.value.segment_terminator = "~"
    form.value.element_separator = "*"
    form.value.subelement_separator = ">"
    form.value.release_character = "?"
    form.value.sender_qualifier = "ZZ"
    form.value.receiver_qualifier = "ZZ"
  }
}

// Load Data
async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [pRes, cRes, sRes] = await Promise.allSettled([
      api.get('/T0124I/?limit=100'),
      api.get('/T0010I/?limit=100'),
      api.get('/T0014I/?limit=100')
    ])

    if (pRes.status === 'fulfilled') {
      partners.value = Array.isArray(pRes.value.data) ? pRes.value.data : (pRes.value.data?.items || [])
    }
    if (cRes.status === 'fulfilled') {
      customers.value = Array.isArray(cRes.value.data) ? cRes.value.data : (cRes.value.data?.items || [])
    }
    if (sRes.status === 'fulfilled') {
      suppliers.value = Array.isArray(sRes.value.data) ? sRes.value.data : (sRes.value.data?.items || [])
    }
  } catch (err) {
    console.error('Failed to load EDI partners:', err)
    error.value = t('failed-load', 'Failed to load EDI partners')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  isEditing.value = false
  editingId.value = null
  formTab.value = 'profile'
  form.value = {
    partner_name: '',
    partner_code: '',
    edi_standard: 'ANSI_X12',
    interchange_sender_id: '',
    interchange_receiver_id: 'NOVADISTRIB',
    sender_qualifier: 'ZZ',
    receiver_qualifier: 'ZZ',
    communication_method: 'MANUAL',
    endpoint_url: '',
    customer_id: null,
    supplier_id: null,
    segment_terminator: '~',
    element_separator: '*',
    subelement_separator: '>',
    release_character: '?',
    auto_confirm_orders: true,
    price_tolerance_percent: 0.0,
    gs1_company_prefix: '',
    is_active: true,
  }
  showModal.value = true
}

function openEditModal(partner) {
  isEditing.value = true
  editingId.value = partner.id
  formTab.value = 'profile'
  form.value = {
    partner_name: partner.partner_name || '',
    partner_code: partner.partner_code || '',
    edi_standard: partner.edi_standard || 'ANSI_X12',
    interchange_sender_id: partner.interchange_sender_id || '',
    interchange_receiver_id: partner.interchange_receiver_id || 'NOVADISTRIB',
    sender_qualifier: partner.sender_qualifier || 'ZZ',
    receiver_qualifier: partner.receiver_qualifier || 'ZZ',
    communication_method: partner.communication_method || 'MANUAL',
    endpoint_url: partner.endpoint_url || '',
    customer_id: partner.customer_id || null,
    supplier_id: partner.supplier_id || null,
    segment_terminator: partner.segment_terminator || '~',
    element_separator: partner.element_separator || '*',
    subelement_separator: partner.subelement_separator || '>',
    release_character: partner.release_character || '?',
    auto_confirm_orders: partner.auto_confirm_orders ?? true,
    price_tolerance_percent: partner.price_tolerance_percent || 0.0,
    gs1_company_prefix: partner.gs1_company_prefix || '',
    is_active: partner.is_active ?? true,
  }
  showModal.value = true
}

async function savePartner() {
  if (!form.value.partner_name.trim() || !form.value.partner_code.trim()) {
    toast(t('name-code-required', 'Partner Name and Partner Code are required'), 'error')
    return
  }
  if (!form.value.interchange_sender_id.trim()) {
    toast(t('sender-id-required', 'Interchange Sender ID is required'), 'error')
    return
  }

  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await api.put(`/T0124I/${editingId.value}`, form.value)
      toast(t('partner-updated', 'Trading Partner updated successfully'), 'success')
    } else {
      await api.post('/T0124I/', form.value)
      toast(t('partner-created', 'Trading Partner created successfully'), 'success')
    }
    showModal.value = false
    await loadData()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    toast(t('save-failed', `Save failed: ${detail}`), 'error')
  } finally {
    saving.value = false
  }
}

async function toggleActive(partner) {
  try {
    await api.put(`/T0124I/${partner.id}`, { is_active: !partner.is_active })
    toast(partner.is_active ? 'Partner deactivated' : 'Partner activated', 'success')
    await loadData()
  } catch (err) {
    toast('Status update failed', 'error')
  }
}

async function deletePartner(partner) {
  if (!confirm(`Are you sure you want to delete trading partner ${partner.partner_code} (${partner.partner_name})?`)) return
  try {
    await api.delete(`/T0124I/${partner.id}`)
    toast('Trading partner deleted', 'success')
    await loadData()
  } catch (err) {
    toast('Failed to delete partner', 'error')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.edi-partners-view {
  padding-bottom: 32px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}
.page-subtitle {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.kpi-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-purple { background: #ede7f6; color: #5d3fd3; }
.icon-green { background: #e8f5e9; color: #2e7d32; }
.icon-blue { background: #e3f2fd; color: #1976d2; }
.icon-teal { background: #e0f2f1; color: #00796b; }
.icon-amber { background: #fff3e0; color: #f57c00; }
.kpi-info {
  display: flex;
  flex-direction: column;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #777;
  text-transform: uppercase;
}
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-top: 2px;
}

/* Data Table Card */
.data-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
}
.card-filter-bar {
  padding: 14px 20px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  min-width: 280px;
  flex: 1;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: #999;
}
.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.filters-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-select {
  padding: 7px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 12px;
  background: #fff;
  color: #444;
}

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #fafafe;
  border-bottom: 1px solid #eee;
  text-align: left;
  white-space: nowrap;
}
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
  color: #333;
}
.data-table tr:hover td { background: #fbfbfe; }

/* Badges */
.badge { display: inline-block; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; }
.badge-xs { display: inline-block; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 600; }
.badge-x12 { background: #f3e8ff; color: #7e22ce; }
.badge-edifact { background: #e0f2fe; color: #0369a1; }
.badge-doc { background: #f1f5f9; color: #475569; font-family: monospace; font-weight: 700; }
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #ef6c00; }
.badge-disabled { background: #f1f5f9; color: #94a3b8; }
.delimiters-tag {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  color: #334155;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #5d3fd3;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #4a32b0; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #fff;
  color: #4b5563;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.btn-sm { padding: 5px 10px; font-size: 12px; }
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: #666;
}
.btn-icon:hover { background: #f0f0f4; }

/* Modals & Tabs */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: #fff;
  border-radius: 14px;
  width: 90%;
  max-width: 580px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}
.modal-lg { max-width: 740px; }
.modal-header {
  padding: 16px 22px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 0; }
.modal-body { padding: 20px 22px; overflow-y: auto; flex: 1; }
.modal-footer {
  padding: 14px 22px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: #fafafa;
}

.tabs { display: flex; gap: 4px; border-bottom: 1px solid #e2e8f0; padding-bottom: 2px; }
.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: none;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
}
.tab-btn.active {
  color: #5d3fd3;
  border-bottom: 2px solid #5d3fd3;
  background: #f5f3ff;
}

/* Forms */
.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.grid-delimiters { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.required { color: #e53935; }
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: 48px; color: #999; font-size: 14px; }
.empty-icon { font-size: 48px; color: #ccc; margin-bottom: 12px; }
</style>

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('inv-config-title', 'Inventory & Dual UOM Configuration') }}</h1>
        <p class="page-subtitle">{{ t('inv-config-sub', 'Manage Dual Unit-of-Measure rules, Catch-Weight tolerance defaults, and warehouse policies') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn-outline" @click="$router.push('/uom-conversions')">
          <span class="material-symbols-outlined icon-xs">swap_horiz</span> {{ t('uom-conversions', 'UOM Conversions') }}
        </button>
        <button class="btn-outline" @click="$router.push('/uom')">
          <span class="material-symbols-outlined icon-xs">straighten</span> {{ t('uom-title', 'Units of Measure') }}
        </button>
        <button class="btn-primary" @click="saveConfig" :disabled="saving">
          <span class="material-symbols-outlined icon-xs">{{ saving ? 'progress_activity' : 'save' }}</span>
          {{ saving ? t('saving', 'Saving...') : t('save-config', 'Save Configuration') }}
        </button>
      </div>
    </div>

    <!-- Stats Summary Row -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-num cw">{{ catchWeightProducts.length }}</div>
        <div class="stat-lbl">{{ t('cw-products-count', 'Catch-Weight Products') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num active">{{ config.default_tolerance_pct }}%</div>
        <div class="stat-lbl">{{ t('default-tolerance', 'Default Tolerance') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num uom">{{ uoms.length }}</div>
        <div class="stat-lbl">{{ t('active-uoms-count', 'Configured UOMs') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-num conversions">{{ conversions.length }}</div>
        <div class="stat-lbl">{{ t('uom-conversions-count', 'UOM Conversions') }}</div>
      </div>
    </div>

    <SkeletonTable v-if="loading" :rows="4" :columns="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else class="config-layout">
      <!-- Tab Navigation -->
      <div class="config-tabs">
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'catch-weight' }" @click="activeTab = 'catch-weight'">
          <span class="material-symbols-outlined icon-xs tab-icon">scale</span>
          {{ t('tab-catch-weight-rules', 'Catch-Weight & Dual UOM') }}
        </button>
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'uom-overview' }" @click="activeTab = 'uom-overview'">
          <span class="material-symbols-outlined icon-xs tab-icon">straighten</span>
          {{ t('tab-uom-overview', 'Units of Measure Directory') }}
        </button>
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'warehouse-rules' }" @click="activeTab = 'warehouse-rules'">
          <span class="material-symbols-outlined icon-xs tab-icon">warehouse</span>
          {{ t('tab-warehouse-rules', 'Warehouse & Stock Policies') }}
        </button>
      </div>

      <!-- Tab 1: Catch-Weight & Dual UOM Rules -->
      <div v-show="activeTab === 'catch-weight'" class="tab-panel">
        <div class="settings-grid">
          <!-- Global Dual UOM Settings Card -->
          <div class="data-card">
            <div class="card-header">
              <h3>{{ t('cw-global-rules', 'Catch-Weight Engine Defaults') }}</h3>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label>{{ t('default-tolerance-label', 'Default Weight Tolerance Percentage (±%)') }}</label>
                <div class="input-suffix">
                  <input type="number" step="0.1" min="0" max="100" v-model.number="config.default_tolerance_pct" class="form-input" />
                  <span class="suffix">%</span>
                </div>
                <p class="field-hint">
                  {{ t('default-tolerance-hint', 'Standard allowed deviation between nominal weight and actual scale weight when creating new catch-weight products.') }}
                </p>
              </div>

              <div class="form-group">
                <label>{{ t('scale-precision', 'Scale Weight Precision') }}</label>
                <select v-model.number="config.scale_precision" class="form-input">
                  <option :value="2">2 {{ t('decimals', 'Decimals (e.g. 12.35 kg)') }}</option>
                  <option :value="3">3 {{ t('decimals', 'Decimals (e.g. 12.350 kg / high precision)') }}</option>
                </select>
              </div>

              <div class="form-group checkbox-group mt-4">
                <label class="checkbox-label font-semibold">
                  <input type="checkbox" v-model="config.require_supervisor_approval" />
                  {{ t('require-supervisor-approval', 'Enforce Supervisor Approval for Tolerance Discrepancies') }}
                </label>
                <p class="field-hint">
                  {{ t('supervisor-approval-hint', 'Strictly block pick list completion and order delivery/invoicing whenever actual weighed weight deviates beyond the allowed tolerance until authorized.') }}
                </p>
              </div>

              <div class="form-group checkbox-group">
                <label class="checkbox-label font-semibold">
                  <input type="checkbox" v-model="config.auto_recalculate_invoice" />
                  {{ t('auto-recalc-invoice', 'Automatic Catch-Weight Invoicing Price Recalculation') }}
                </label>
                <p class="field-hint">
                  {{ t('auto-recalc-hint', 'Automatically recompute sales order line totals and invoice balances based on true picked scale weights.') }}
                </p>
              </div>
            </div>
          </div>

          <!-- Dual UOM Architecture Info Card -->
          <div class="data-card bg-purple-subtle">
            <div class="card-header">
              <h3>
                <span class="material-symbols-outlined icon-xs text-purple">info</span>
                {{ t('dual-uom-concept-title', 'How Dual UOM Works in Nova ERP') }}
              </h3>
            </div>
            <div class="card-body text-sm">
              <div class="concept-step">
                <div class="step-num">1</div>
                <div>
                  <strong>{{ t('step-1-title', 'Product Master Definition') }}</strong>
                  <p>{{ t('step-1-desc', 'Configure Stocking UOM (e.g. Cases) and Pricing UOM (e.g. Kilograms) with nominal weight and tolerance %.') }}</p>
                </div>
              </div>
              <div class="concept-step">
                <div class="step-num">2</div>
                <div>
                  <strong>{{ t('step-2-title', 'Warehouse Scale Capture') }}</strong>
                  <p>{{ t('step-2-desc', 'Pickers scan items and input actual scale weight. The system validates variance against tolerance limits.') }}</p>
                </div>
              </div>
              <div class="concept-step">
                <div class="step-num">3</div>
                <div>
                  <strong>{{ t('step-3-title', 'Tolerance Gate & Invoicing') }}</strong>
                  <p>{{ t('step-3-desc', 'Discrepant weights require supervisor sign-off; billing automatically recalculates for true weight.') }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Configured Catch-Weight Products Table -->
        <div class="data-card mt-6">
          <div class="card-header flex justify-between items-center">
            <h3>{{ t('configured-cw-products', 'Configured Catch-Weight Products') }} ({{ catchWeightProducts.length }})</h3>
            <button class="btn-outline btn-sm" @click="$router.push('/products')">
              <span class="material-symbols-outlined icon-xs">add</span> {{ t('configure-new-product', 'Add Product') }}
            </button>
          </div>
          <div class="card-body p-0">
            <div v-if="!catchWeightProducts.length" class="empty-section">
              <span class="material-symbols-outlined empty-icon-sm">scale</span>
              <p>{{ t('no-cw-products', 'No catch-weight products configured yet.') }}</p>
              <button class="btn-primary btn-sm mt-2" @click="$router.push('/products')">{{ t('manage-products', 'Manage Products') }}</button>
            </div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('prod-sku', 'SKU') }}</th>
                    <th>{{ t('name', 'Product Name') }}</th>
                    <th>{{ t('pricing-uom', 'Pricing UOM') }}</th>
                    <th>{{ t('nominal-weight', 'Nominal Weight') }}</th>
                    <th>{{ t('tolerance-pct', 'Tolerance') }}</th>
                    <th>{{ t('pricing-basis', 'Pricing Basis') }}</th>
                    <th class="text-center">{{ t('actions', 'Actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="prod in catchWeightProducts" :key="prod.id">
                    <td class="cell-sku">{{ prod.sku }}</td>
                    <td class="cell-name font-semibold">
                      <router-link :to="`/products/${prod.id}`" class="product-link">{{ prod.name }}</router-link>
                    </td>
                    <td>{{ getUomName(prod.pricing_uom_id) }}</td>
                    <td class="cell-mono">{{ prod.nominal_weight != null ? `${prod.nominal_weight} ${getUomCode(prod.pricing_uom_id)}` : '-' }}</td>
                    <td class="cell-mono">±{{ prod.tolerance_pct || 0 }}%</td>
                    <td class="capitalize">{{ prod.pricing_basis || 'weight' }}</td>
                    <td class="text-center">
                      <router-link :to="`/products/${prod.id}`" class="btn-icon" :title="t('view-product', 'View Product')">
                        <span class="material-symbols-outlined">visibility</span>
                      </router-link>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 2: UOM Overview -->
      <div v-show="activeTab === 'uom-overview'" class="tab-panel">
        <div class="data-card">
          <div class="card-header flex justify-between items-center">
            <h3>{{ t('uom-directory', 'Units of Measure Directory') }} ({{ uoms.length }})</h3>
            <div class="flex gap-2">
              <button class="btn-outline btn-sm" @click="$router.push('/uom')">
                <span class="material-symbols-outlined icon-xs">open_in_new</span> {{ t('full-uom-manager', 'Open UOM Master') }}
              </button>
            </div>
          </div>
          <div class="card-body p-0">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ t('code', 'Code') }}</th>
                    <th>{{ t('name', 'Name') }}</th>
                    <th>{{ t('category', 'Category') }}</th>
                    <th class="text-center">{{ t('base-unit', 'Base Unit') }}</th>
                    <th class="text-center">{{ t('status', 'Status') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="uom in uoms" :key="uom.id">
                    <td><span class="cell-mono font-bold">{{ uom.uom_code }}</span></td>
                    <td class="font-semibold">{{ uom.uom_name }}</td>
                    <td><span class="badge badge-type">{{ uom.category }}</span></td>
                    <td class="text-center">
                      <span v-if="uom.is_base_unit" class="badge badge-active">{{ t('yes', 'Yes') }}</span>
                      <span v-else class="badge badge-inactive">{{ t('no', 'No') }}</span>
                    </td>
                    <td class="text-center">
                      <span v-if="uom.is_active" class="badge badge-active">{{ t('active', 'Active') }}</span>
                      <span v-else class="badge badge-inactive">{{ t('inactive', 'Inactive') }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 3: Warehouse & Stock Policies -->
      <div v-show="activeTab === 'warehouse-rules'" class="tab-panel">
        <div class="data-card">
          <div class="card-header">
            <h3>{{ t('warehouse-stock-policies', 'Warehouse & Stock Handling Policies') }}</h3>
          </div>
          <div class="card-body">
            <div class="form-group checkbox-group">
              <label class="checkbox-label font-semibold">
                <input type="checkbox" v-model="config.fefo_picking_enabled" />
                {{ t('fefo-picking', 'Enable FEFO (First-Expired, First-Out) Priority Picking') }}
              </label>
              <p class="field-hint">
                {{ t('fefo-picking-hint', 'Automatically sort and prioritize lots/batches with earlier expiration dates on warehouse pick lists.') }}
              </p>
            </div>

            <div class="form-group checkbox-group mt-4">
              <label class="checkbox-label font-semibold">
                <input type="checkbox" v-model="config.block_negative_stock" />
                {{ t('block-negative-stock', 'Prevent Negative Stock Movements') }}
              </label>
              <p class="field-hint">
                {{ t('block-negative-hint', 'Disallow outbound shipments and picks if warehouse physical on-hand quantity is insufficient.') }}
              </p>
            </div>

            <div class="form-group mt-4">
              <label>{{ t('phantom-scan-days', 'Phantom Inventory Inactivity Threshold (Days)') }}</label>
              <input type="number" min="30" max="1000" v-model.number="config.phantom_inactivity_days" class="form-input" style="max-width: 240px;" />
              <p class="field-hint">
                {{ t('phantom-scan-hint', 'Products with no sales order activity beyond this threshold will be flagged during automated phantom scans.') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../api/client.js'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import SkeletonTable from '../../components/SkeletonTable.vue'
import ErrorState from '../../components/ErrorState.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const router = useRouter()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const activeTab = ref('catch-weight')

const products = ref([])
const uoms = ref([])
const conversions = ref([])

const config = reactive({
  default_tolerance_pct: 5.0,
  scale_precision: 2,
  require_supervisor_approval: true,
  auto_recalculate_invoice: true,
  fefo_picking_enabled: true,
  block_negative_stock: true,
  phantom_inactivity_days: 365
})

const catchWeightProducts = computed(() => {
  return products.value.filter(p => p.is_catch_weight)
})

function getUomName(uomId) {
  if (!uomId) return '-'
  const u = uoms.value.find(x => x.id === uomId)
  return u ? `${u.uom_code} - ${u.uom_name}` : `#${uomId}`
}

function getUomCode(uomId) {
  if (!uomId) return 'kg'
  const u = uoms.value.find(x => x.id === uomId)
  return u ? u.uom_code : 'kg'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [prodRes, uomRes, convRes] = await Promise.all([
      api.get('/T0003I/'),
      api.get('/T0001I/').catch(() => ({ data: [] })),
      api.get('/T0002I/').catch(() => ({ data: [] })),
    ])
    products.value = prodRes.data || []
    uoms.value = uomRes.data || []
    conversions.value = convRes.data || []

    // Load persisted local preferences if available
    const saved = localStorage.getItem('nova_inventory_config')
    if (saved) {
      try {
        Object.assign(config, JSON.parse(saved))
      } catch {
        // ignore parse error
      }
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load inventory configuration'
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    localStorage.setItem('nova_inventory_config', JSON.stringify(config))
    toast(t('config-saved', 'Inventory & Dual UOM configuration saved successfully'), 'success')
  } catch {
    toast(t('failed-save-config', 'Failed to save configuration'), 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }
.page-subtitle { font-size: 13px; color: #666; margin-top: 4px; }
.page-actions { display: flex; align-items: center; gap: 10px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 16px; text-align: center; }
.stat-num { font-size: 24px; font-weight: 700; color: var(--color-primary); }
.stat-num.active { color: var(--color-success); }
.stat-num.cw { color: #7e22ce; }
.stat-num.uom { color: #0284c7; }
.stat-num.conversions { color: #d97706; }
.stat-lbl { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.config-layout { display: flex; flex-direction: column; gap: 16px; }
.config-tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--border-light); background: var(--bg-surface); padding: 4px 12px 0; border-radius: 8px 8px 0 0; }
.tab-btn { display: inline-flex; align-items: center; padding: 10px 18px; font-size: 13px; font-weight: 600; color: var(--text-muted); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--color-primary); border-bottom-color: var(--color-primary); background: var(--bg-surface); }
.tab-icon { margin-right: 6px; }

.tab-panel { animation: fadeIn 0.15s ease-in-out; }
.settings-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }

.data-card { background: #fff; border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.card-header { padding: 14px 20px; border-bottom: 1px solid var(--border-light); }
.card-header h3 { font-size: 14px; font-weight: 700; margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.card-body { padding: 20px; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: #fff; box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary); }

.input-suffix { position: relative; display: flex; align-items: center; max-width: 240px; }
.input-suffix .form-input { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.suffix { padding: 8px 10px; background: var(--bg-surface-hover); border: 1px solid var(--border-input); border-left: none; border-radius: 0 6px 6px 0; font-size: 13px; color: var(--text-muted); font-weight: 600; }

.checkbox-group { margin-bottom: 12px; }
.checkbox-label { display: flex; align-items: flex-start; gap: 8px; cursor: pointer; font-size: 13px; color: var(--text-primary); line-height: 1.4; }
.checkbox-label input { width: 16px; height: 16px; margin-top: 2px; accent-color: var(--color-primary); }

.field-hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; margin-left: 24px; line-height: 1.4; }

.bg-purple-subtle { background: #faf5ff; border-color: #e9d5ff; }
.text-purple { color: #7e22ce; }
.concept-step { display: flex; gap: 12px; margin-bottom: 14px; align-items: flex-start; }
.concept-step:last-child { margin-bottom: 0; }
.step-num { width: 24px; height: 24px; border-radius: 50%; background: #7e22ce; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.concept-step p { margin: 2px 0 0; color: #6b7280; font-size: 12px; line-height: 1.4; }

.table-wrap { overflow-x: auto; }
.cell-sku { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-subtle); }
.cell-mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.cell-name { font-weight: 600; }
.product-link { color: var(--text-primary); text-decoration: none; }
.product-link:hover { color: var(--color-primary); text-decoration: underline; }

.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-inactive { background: var(--bg-surface-hover); color: var(--text-faint); }
.badge-type { background: var(--bg-surface-hover); color: var(--text-secondary); }

.btn-primary { background: var(--color-primary, #2563eb); color: #fff; padding: 8px 16px; border-radius: 6px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline { background: #fff; color: var(--text-primary, #374151); border: 1px solid var(--border-default, #d1d5db); padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-icon { background: transparent; border: none; cursor: pointer; color: var(--text-muted); padding: 4px; border-radius: 4px; display: inline-flex; align-items: center; justify-content: center; }
.btn-sm { padding: 4px 10px !important; font-size: 12px !important; }

.empty-section { padding: 28px 16px; text-align: center; color: var(--text-muted); font-size: 13px; }
.empty-icon-sm { font-size: 36px; color: var(--text-faint); display: block; margin-bottom: 8px; }

.icon-xs { font-size: 14px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 8px; }
.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
.p-0 { padding: 0 !important; }
.text-center { text-align: center; }
.capitalize { text-transform: capitalize; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
</style>

<template>
  <div :dir="dir">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('dashbuilder-title', 'Dashboard Builder') }}</h2>
        <p class="page-subtitle">{{ t('dashbuilder-subtitle', 'Create and manage custom dashboards with widgets') }}</p>
      </div>
      <button class="btn-primary" @click="openAddDashboard">
        <span class="material-symbols-outlined">add</span> {{ t('dashbuilder-new', 'New Dashboard') }}
      </button>
    </div>

    <div class="builder-layout">
      <div class="sidebar-list">
        <div v-if="store.loading" class="text-center py-8 text-gray-400">{{ t('loading', 'Loading...') }}</div>
        <div v-else-if="!store.dashboards.length" class="empty-section">
          <p>{{ t('dashbuilder-empty', 'No dashboards yet') }}</p>
        </div>
        <div v-else class="dashboard-list">
          <div v-for="dash in store.dashboards" :key="dash.id"
            class="dash-item" :class="{ active: activeDashboard?.id === dash.id }"
            @click="selectDashboard(dash)">
            <div class="dash-item-info">
              <span class="dash-item-name">{{ dash.dashboard_name }}</span>
              <span class="dash-item-code">{{ dash.dashboard_code }}</span>
            </div>
            <div class="dash-item-actions" @click.stop>
              <button class="btn-icon btn-icon-sm" @click="viewDashboard(dash)" :title="t('view', 'View')"><span class="material-symbols-outlined">visibility</span></button>
              <button class="btn-icon btn-icon-sm" @click="openEditDashboard(dash)" :title="t('edit', 'Edit')"><span class="material-symbols-outlined">edit</span></button>
              <button class="btn-icon btn-icon-sm btn-icon-danger" @click="confirmDeleteDashboard(dash)" :title="t('delete', 'Delete')"><span class="material-symbols-outlined">delete</span></button>
            </div>
          </div>
        </div>
      </div>

      <div class="builder-main">
        <div v-if="!activeDashboard" class="placeholder">
          <span class="material-symbols-outlined placeholder-icon">dashboard_customize</span>
          <p>{{ t('dashbuilder-select', 'Select a dashboard to edit or create a new one') }}</p>
        </div>

        <template v-else>
          <div class="dashboard-toolbar">
            <h3>{{ activeDashboard.dashboard_name }}</h3>
            <button class="btn-primary btn-xs" @click="openAddWidget">
              <span class="material-symbols-outlined">add</span> {{ t('add-widget', 'Add Widget') }}
            </button>
          </div>

          <div v-if="!store.widgets.length" class="empty-state-sm">
            <p>{{ t('no-widgets', 'No widgets yet. Add your first widget.') }}</p>
          </div>

          <div v-else class="widget-grid">
            <div v-for="(widget, idx) in store.widgets" :key="widget.id"
              class="widget-card" :class="['w-' + widget.widget_type, { clickable: widgetTo(widget) }]"
              @click="navigateToWidget(widget)">
              <div class="widget-head">
                <span class="widget-title">{{ widget.title || widget.widget_type }}</span>
                <div class="widget-actions" @click.stop>
                  <button class="btn-icon btn-icon-sm" @click="openEditWidget(widget)"><span class="material-symbols-outlined">edit</span></button>
                  <button class="btn-icon btn-icon-sm btn-icon-danger" @click="confirmDeleteWidget(widget)"><span class="material-symbols-outlined">delete</span></button>
                </div>
              </div>
              <div class="widget-body">
                <ChartRenderer v-bind="widgetChartProps(widget)" />
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="showDashModal" class="modal-overlay" @click.self="closeDashModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditingDash ? t('dash-edit', 'Edit Dashboard') : t('dash-new', 'New Dashboard') }}</h3>
          <button class="btn-icon" @click="closeDashModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="saveDashboard" class="modal-body">
          <div class="form-group">
            <label>{{ t('dash-code', 'Code') }} <span class="required">*</span></label>
            <input type="text" v-model="dashForm.dashboard_code" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('dash-name', 'Name') }} <span class="required">*</span></label>
            <input type="text" v-model="dashForm.dashboard_name" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('dash-owner', 'Owner ID') }}</label>
            <input type="number" v-model.number="dashForm.owner_id" class="form-input" />
          </div>
          <div class="form-group">
            <label>{{ t('dash-config', 'Config (JSON)') }}</label>
            <textarea v-model="dashForm.config" class="form-input form-textarea" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="dashForm.is_active" />
              {{ t('active', 'Active') }}
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeDashModal">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary">{{ t('save', 'Save') }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showWidgetModal" class="modal-overlay" @click.self="closeWidgetModal">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>{{ isEditingWidget ? t('widget-edit', 'Edit Widget') : t('widget-new', 'New Widget') }}</h3>
          <button class="btn-icon" @click="closeWidgetModal"><span class="material-symbols-outlined">close</span></button>
        </div>
        <form @submit.prevent="saveWidget" class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>{{ t('widget-type', 'Type') }} <span class="required">*</span></label>
              <select v-model="widgetForm.widget_type" class="form-input" @change="onWidgetTypeChange">
                <option value="Metric">Metric (Stat Card)</option>
                <option value="KPI">KPI (Progress)</option>
                <option value="Chart">Chart</option>
                <option value="Table">Table</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('widget-title', 'Title') }}</label>
              <input type="text" v-model="widgetForm.title" class="form-input" />
            </div>
          </div>

          <div v-if="widgetForm.widget_type === 'Chart'" class="form-row">
            <div class="form-group">
              <label>{{ t('chart-type', 'Chart Type') }}</label>
              <select v-model="widgetConfig.chart_subtype" class="form-input">
                <option value="bar">Bar</option>
                <option value="line">Line</option>
                <option value="pie">Pie</option>
                <option value="donut">Donut</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('chart-color', 'Color') }}</label>
              <input type="color" v-model="widgetConfig.color" class="form-input form-input-color" />
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('widget-config', 'Widget Configuration') }}</label>
            <textarea v-model="widgetConfigRaw" class="form-input form-textarea" rows="4" placeholder='{"key": "value"}'></textarea>
          </div>

          <div v-if="widgetForm.widget_type === 'Metric' || widgetForm.widget_type === 'Chart'" class="preview-section">
            <label class="preview-label">{{ t('preview', 'Preview') }}</label>
            <ChartRenderer v-bind="previewProps" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('position-x', 'Position X') }}</label>
              <input type="number" v-model.number="widgetForm.position_x" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('position-y', 'Position Y') }}</label>
              <input type="number" v-model.number="widgetForm.position_y" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>{{ t('widget-nav-route', 'Navigation Route (optional)') }}</label>
            <input type="text" v-model="widgetConfig.to" class="form-input" :placeholder="t('widget-nav-placeholder', 'Route name, e.g. customers')" />
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="widgetForm.is_active" />
              {{ t('active', 'Active') }}
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeWidgetModal">{{ t('cancel', 'Cancel') }}</button>
            <button type="submit" class="btn-primary">{{ t('save', 'Save') }}</button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog v-if="showDeleteDash" :message="t('dash-delete-msg', 'Delete this dashboard?')" @confirm="doDeleteDashboard" @cancel="showDeleteDash = false" />
    <ConfirmDialog v-if="showDeleteWidget" :message="t('widget-delete-msg', 'Delete this widget?')" @confirm="doDeleteWidget" @cancel="showDeleteWidget = false" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { useBiStore } from '../../stores/bi.js'
import { widgetChartProps, widgetTo, navigateToWidget as navigateToWidgetRoute } from '../../composables/useWidgetConfig.js'
import ChartRenderer from '../../components/charts/ChartRenderer.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const router = useRouter()
const store = useBiStore()

const activeDashboard = ref(null)
const showDashModal = ref(false)
const showWidgetModal = ref(false)
const showDeleteDash = ref(false)
const showDeleteWidget = ref(false)
const isEditingDash = ref(false)
const isEditingWidget = ref(false)
const saving = ref(false)
const deletingDashItem = ref(null)
const deletingWidgetItem = ref(null)

const dashForm = reactive({ dashboard_code: '', dashboard_name: '', owner_id: null, config: '', is_active: true })
const widgetForm = reactive({ dashboard_id: null, widget_type: 'Metric', title: '', config: '', position_x: 0, position_y: 0, is_active: true })
const widgetConfig = reactive({ chart_subtype: 'bar', color: '#5d3fd3', label: '', statLabel: '', statValue: 0, statPrefix: '', statSuffix: '', statIcon: '', trend: '', trendDir: 'up', progressLabel: '', progressValue: 0, progressSubtext: '', labels: [], values: [], to: '' })

const widgetConfigRaw = computed({
  get: () => JSON.stringify({ ...widgetConfig }, null, 2),
  set: (val) => {
    try { Object.assign(widgetConfig, JSON.parse(val)) } catch {}
  }
})

function resetDashForm() {
  dashForm.dashboard_code = ''; dashForm.dashboard_name = ''
  dashForm.owner_id = null; dashForm.config = ''; dashForm.is_active = true
}

function resetWidgetForm() {
  widgetForm.dashboard_id = activeDashboard.value?.id || null
  widgetForm.widget_type = 'Metric'; widgetForm.title = ''
  widgetForm.config = ''; widgetForm.position_x = 0; widgetForm.position_y = 0
  widgetForm.is_active = true
  widgetConfig.chart_subtype = 'bar'; widgetConfig.color = '#5d3fd3'
  widgetConfig.label = ''; widgetConfig.statLabel = ''; widgetConfig.statValue = 0
  widgetConfig.statPrefix = ''; widgetConfig.statSuffix = ''; widgetConfig.statIcon = ''
  widgetConfig.trend = ''; widgetConfig.trendDir = 'up'
  widgetConfig.progressLabel = ''; widgetConfig.progressValue = 0
  widgetConfig.progressSubtext = ''; widgetConfig.labels = []; widgetConfig.values = []; widgetConfig.to = ''
}

function onWidgetTypeChange() {
  if (widgetForm.widget_type === 'Metric') {
    widgetConfig.statIcon = 'analytics'; widgetConfig.statValue = 0; widgetConfig.statLabel = widgetForm.title || 'Metric'
  } else if (widgetForm.widget_type === 'KPI') {
    widgetConfig.progressLabel = widgetForm.title || 'KPI'; widgetConfig.progressValue = 75
  } else if (widgetForm.widget_type === 'Chart') {
    widgetConfig.labels = ['Jan', 'Feb', 'Mar']; widgetConfig.values = [30, 50, 80]
    widgetConfig.label = 'Series 1'; widgetConfig.chart_subtype = 'bar'; widgetConfig.color = '#5d3fd3'
  }
}

const previewProps = computed(() => {
  if (widgetForm.widget_type === 'Metric') {
    return { type: 'stat', statLabel: widgetConfig.statLabel, statValue: widgetConfig.statValue, statPrefix: widgetConfig.statPrefix, statSuffix: widgetConfig.statSuffix, statIcon: widgetConfig.statIcon, trend: widgetConfig.trend, trendDir: widgetConfig.trendDir }
  }
  if (widgetForm.widget_type === 'KPI') {
    return { type: 'progress', progressLabel: widgetConfig.progressLabel, progressValue: widgetConfig.progressValue, progressSubtext: widgetConfig.progressSubtext, color: widgetConfig.color }
  }
  if (widgetForm.widget_type === 'Chart') {
    return { type: widgetConfig.chart_subtype, labels: widgetConfig.labels, values: widgetConfig.values, label: widgetConfig.label, color: widgetConfig.color, height: 200 }
  }
  return { type: 'stat', statLabel: 'Widget', statValue: 0 }
})

function navigateToWidget(widget) { navigateToWidgetRoute(router, widget) }

function openAddDashboard() { isEditingDash.value = false; resetDashForm(); showDashModal.value = true }
function openEditDashboard(dash) {
  isEditingDash.value = true
  dashForm.dashboard_code = dash.dashboard_code; dashForm.dashboard_name = dash.dashboard_name
  dashForm.owner_id = dash.owner_id; dashForm.config = dash.config || ''
  dashForm.is_active = dash.is_active; editingDashId.value = dash.id
  showDashModal.value = true
}
const editingDashId = ref(null)
function closeDashModal() { showDashModal.value = false }

async function saveDashboard() {
  if (!dashForm.dashboard_code || !dashForm.dashboard_name) { toast(t('dash-required', 'Code and name required'), 'error'); return }
  saving.value = true
  try {
    const payload = { ...dashForm, config: dashForm.config || null, owner_id: dashForm.owner_id || null }
    if (isEditingDash.value) {
      await store.updateDashboard(editingDashId.value, payload)
      toast(t('dash-updated', 'Dashboard updated'), 'success')
    } else {
      await store.createDashboard(payload)
      toast(t('dash-created', 'Dashboard created'), 'success')
    }
    closeDashModal()
  } catch { toast(t('dash-save-error', 'Failed to save dashboard'), 'error') }
  finally { saving.value = false }
}

function confirmDeleteDashboard(dash) { deletingDashItem.value = dash; showDeleteDash.value = true }
async function doDeleteDashboard() {
  try {
    await store.deleteDashboard(deletingDashItem.value.id)
    if (activeDashboard.value?.id === deletingDashItem.value.id) activeDashboard.value = null
    toast(t('dash-deleted', 'Dashboard deleted'), 'success')
    showDeleteDash.value = false
  } catch { toast(t('dash-delete-error', 'Failed to delete dashboard'), 'error') }
}

function viewDashboard(dash) {
  router.push({ name: 'bi-view', params: { id: dash.id } })
}

async function selectDashboard(dash) {
  activeDashboard.value = dash
  await store.loadWidgets(dash.id)
}

function openAddWidget() { isEditingWidget.value = false; resetWidgetForm(); showWidgetModal.value = true }
function openEditWidget(widget) {
  isEditingWidget.value = true; editingWidgetId.value = widget.id
  widgetForm.dashboard_id = widget.dashboard_id; widgetForm.widget_type = widget.widget_type
  widgetForm.title = widget.title || ''; widgetForm.config = widget.config || ''
  widgetForm.is_active = widget.is_active
  let pos = { x: 0, y: 0 }
  try { pos = typeof widget.position === 'string' ? JSON.parse(widget.position) : (widget.position || {}) } catch {}
  widgetForm.position_x = pos.x || 0; widgetForm.position_y = pos.y || 0
  let cfg = {}
  try { cfg = typeof widget.config === 'string' ? JSON.parse(widget.config) : (widget.config || {}) } catch { cfg = {} }
  Object.assign(widgetConfig, { chart_subtype: 'bar', color: '#5d3fd3', label: '', statLabel: '', statValue: 0, statPrefix: '', statSuffix: '', statIcon: '', trend: '', trendDir: 'up', progressLabel: '', progressValue: 0, progressSubtext: '', labels: [], values: [], ...cfg })
  showWidgetModal.value = true
}
const editingWidgetId = ref(null)
function closeWidgetModal() { showWidgetModal.value = false }

async function saveWidget() {
  saving.value = true
  try {
    const configStr = JSON.stringify({ ...widgetConfig })
    const positionStr = JSON.stringify({ x: widgetForm.position_x, y: widgetForm.position_y })
    const payload = {
      dashboard_id: activeDashboard.value.id,
      widget_type: widgetForm.widget_type,
      title: widgetForm.title || null,
      config: configStr,
      position: positionStr,
      is_active: widgetForm.is_active
    }
    if (isEditingWidget.value) {
      await store.updateWidget(editingWidgetId.value, payload)
      toast(t('widget-updated', 'Widget updated'), 'success')
    } else {
      await store.createWidget(payload)
      toast(t('widget-created', 'Widget created'), 'success')
    }
    closeWidgetModal()
  } catch { toast(t('widget-save-error', 'Failed to save widget'), 'error') }
  finally { saving.value = false }
}

function confirmDeleteWidget(widget) { deletingWidgetItem.value = widget; showDeleteWidget.value = true }
async function doDeleteWidget() {
  try {
    await store.deleteWidget(deletingWidgetItem.value.id, activeDashboard.value.id)
    toast(t('widget-deleted', 'Widget deleted'), 'success')
    showDeleteWidget.value = false
  } catch { toast(t('widget-delete-error', 'Failed to delete widget'), 'error') }
}

onMounted(async () => {
  await store.loadDashboards()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-subtitle { font-size: 13px; color: var(--text-subtle); margin-top: 2px; }

.builder-layout { display: grid; grid-template-columns: 280px 1fr; gap: 20px; min-height: 500px; }

.sidebar-list { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; overflow-y: auto; max-height: 600px; }
.dashboard-list { display: flex; flex-direction: column; }
.dash-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border-light); cursor: pointer; transition: all 0.15s; }
.dash-item:hover { background: var(--bg-surface-hover); }
.dash-item.active { background: var(--bg-primary-faded); border-left: 3px solid var(--color-primary); }
.dash-item-info { display: flex; flex-direction: column; }
.dash-item-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.dash-item-code { font-size: 11px; color: var(--text-subtle); font-family: monospace; }
.dash-item-actions { display: flex; gap: 4px; opacity: 0; transition: opacity 0.15s; }
.dash-item:hover .dash-item-actions { opacity: 1; }

.builder-main { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; padding: 20px; min-height: 500px; }

.placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 100px 0; color: var(--text-faint); }
.placeholder-icon { font-size: 64px; color: var(--border-default); margin-bottom: 12px; }

.dashboard-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-default); }
.dashboard-toolbar h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }

.empty-state-sm { text-align: center; padding: 60px 0; color: var(--text-faint); }
.empty-section { text-align: center; padding: 40px 0; color: var(--text-faint); font-size: 13px; }

.widget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.widget-card { background: var(--bg-chart); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.widget-card.clickable { cursor: pointer; transition: box-shadow 0.15s, transform 0.15s; }
.widget-card.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.widget-card.w-Table { grid-column: 1 / -1; }
.widget-head { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-surface); border-bottom: 1px solid var(--border-light); }
.widget-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.widget-actions { display: flex; gap: 2px; }
.widget-body { padding: 14px; }

.btn-icon { background: none; border: none; padding: 6px; cursor: pointer; border-radius: 6px; color: var(--text-subtle); }
.btn-icon:hover { background: var(--bg-surface-hover); color: var(--color-primary); }
.btn-icon-danger:hover { background: #fee2e2; color: #dc2626; }
.btn-icon-sm { padding: 4px; }
.btn-icon-sm .material-symbols-outlined { font-size: 16px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg-surface); border-radius: 12px; width: 580px; max-width: 90vw; max-height: 85vh; overflow-y: auto; }
.modal-lg { width: 700px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border-default); }
.modal-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.modal-body { padding: 24px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border-input); border-radius: 6px; font-size: 13px; outline: none; background: var(--bg-surface); color: var(--text-primary); }
.form-input:focus { border-color: var(--color-primary); }
.form-input-color { height: 40px; padding: 4px; }
.form-textarea { resize: vertical; font-family: monospace; font-size: 12px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-secondary); }
.checkbox-label input { width: 16px; height: 16px; }
.preview-section { border-top: 1px solid var(--border-default); padding-top: 16px; margin-top: 16px; }
.preview-label { display: block; font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }

@media (max-width: 767px) {
  .builder-layout { grid-template-columns: 1fr; }
  .sidebar-list { max-height: 200px; }
}
@media (max-width: 480px) {
  .widget-grid { grid-template-columns: 1fr; }
}
</style>

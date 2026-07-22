<template>
  <div :dir="dir">
    <div v-if="loading" class="text-center py-12 text-gray-400">{{ t('loading', 'Loading...') }}</div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
      {{ t('dash-load-error', 'Failed to load dashboard') }}
    </div>

    <template v-else>
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ dashboard.dashboard_name }}</h1>
          <p class="page-subtitle">{{ t('dash-view-subtitle', 'Dashboard') }} · {{ dashboard.dashboard_code }}</p>
        </div>
        <button class="btn-outline" @click="goBack">
          <span class="material-symbols-outlined">arrow_back</span> {{ t('back', 'Back') }}
        </button>
      </div>

      <div v-if="!widgets.length" class="empty-state">
        <span class="material-symbols-outlined empty-icon">dashboard</span>
        <p>{{ t('dash-no-widgets', 'This dashboard has no widgets yet') }}</p>
      </div>

      <div v-else class="widget-grid">
        <div v-for="widget in widgets" :key="widget.id" class="widget-card"
          :class="['w-' + widget.widget_type, { clickable: widgetTo(widget) }]"
          @click="navigateToWidget(widget)">
          <div class="widget-head">
            <span class="widget-title">{{ widget.title || widget.widget_type }}</span>
          </div>
          <div class="widget-body">
            <ChartRenderer v-bind="widgetChartProps(widget)" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../../composables/useI18n.js'
import { useToast } from '../../composables/useToast.js'
import { api } from '../../api/client.js'
import { widgetChartProps, widgetTo, navigateToWidget as navigateToWidgetRoute } from '../../composables/useWidgetConfig.js'
import ChartRenderer from '../../components/charts/ChartRenderer.vue'

const { t, dir } = useI18n()
const { show: toast } = useToast()
const route = useRoute()
const router = useRouter()

const dashboard = ref({})
const widgets = ref([])
const loading = ref(true)
const error = ref(false)

function goBack() { router.push({ name: 'bi-dashboards' }) }

function navigateToWidget(widget) { navigateToWidgetRoute(router, widget) }

onMounted(async () => {
  const id = route.params.id
  if (!id) { error.value = true; loading.value = false; return }
  try {
    const [dashRes, widgetRes] = await Promise.all([
      api.get(`/T0054I/${id}`),
      api.get('/T0055I/')
    ])
    dashboard.value = dashRes.data || {}
    widgets.value = (widgetRes.data || []).filter(w => w.dashboard_id === parseInt(id))
  } catch {
    error.value = true
    toast(t('dash-load-error', 'Failed to load dashboard'), 'error')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.page-subtitle { font-size: 13px; color: var(--text-subtle); margin-top: 2px; }

.widget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.widget-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden; }
.widget-card.clickable { cursor: pointer; transition: box-shadow 0.15s, transform 0.15s; }
.widget-card.clickable:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.widget-card.w-Table { grid-column: 1 / -1; }
.widget-head { padding: 10px 14px; background: var(--bg-surface-low); border-bottom: 1px solid var(--border-light); }
.widget-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.widget-body { padding: 14px; }

.btn-outline { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--text-secondary); padding: 8px 20px; border: 1px solid var(--border-input); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-outline:hover { background: var(--bg-surface-hover); }
.btn-outline .material-symbols-outlined { font-size: 18px; }

.empty-state { text-align: center; padding: 80px 0; color: var(--text-faint); }
.empty-icon { font-size: 48px; color: var(--border-default); margin-bottom: 12px; }
.empty-state p { margin-bottom: 16px; }

@media (max-width: 480px) {
  .widget-grid { grid-template-columns: 1fr; }
}

</style>

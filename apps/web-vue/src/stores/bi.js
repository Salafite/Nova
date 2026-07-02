import { defineStore } from 'pinia'
import { api } from '../api/client.js'

export const useBiStore = defineStore('bi', {
  state: () => ({
    kpis: [],
    kpiValues: [],
    dashboards: [],
    widgets: [],
    loading: false
  }),

  actions: {
    async loadKpis() {
      this.loading = true
      try {
        const res = await api.get('/T0052I/')
        this.kpis = res.data || []
      } catch (e) { this.kpis = []; console.error('Failed to load KPIs:', e) }
      finally { this.loading = false }
    },

    async createKpi(payload) {
      const res = await api.post('/T0052I/', payload)
      await this.loadKpis()
      return res.data
    },

    async updateKpi(id, payload) {
      const res = await api.put(`/T0052I/${id}`, payload)
      await this.loadKpis()
      return res.data
    },

    async deleteKpi(id) {
      await api.delete(`/T0052I/${id}`)
      await this.loadKpis()
    },

    async loadKpiValues(kpiId) {
      try {
        const res = await api.get('/T0053I/')
        this.kpiValues = (res.data || []).filter(v => v.kpi_id === kpiId)
      } catch (e) { this.kpiValues = []; console.error('Failed to load KPI values:', e) }
    },

    async createKpiValue(payload) {
      await api.post('/T0053I/', payload)
      await this.loadKpiValues(payload.kpi_id)
    },

    async deleteKpiValue(id, kpiId) {
      await api.delete(`/T0053I/${id}`)
      await this.loadKpiValues(kpiId)
    },

    async loadDashboards() {
      this.loading = true
      try {
        const res = await api.get('/T0054I/')
        this.dashboards = res.data || []
      } catch (e) { this.dashboards = []; console.error('Failed to load dashboards:', e) }
      finally { this.loading = false }
    },

    async createDashboard(payload) {
      const res = await api.post('/T0054I/', payload)
      await this.loadDashboards()
      return res.data
    },

    async updateDashboard(id, payload) {
      const res = await api.put(`/T0054I/${id}`, payload)
      await this.loadDashboards()
      return res.data
    },

    async deleteDashboard(id) {
      await api.delete(`/T0054I/${id}`)
      await this.loadDashboards()
    },

    async loadWidgets(dashboardId) {
      try {
        const res = await api.get('/T0055I/')
        this.widgets = (res.data || []).filter(w => w.dashboard_id === dashboardId)
      } catch (e) { this.widgets = []; console.error('Failed to load widgets:', e) }
    },

    async createWidget(payload) {
      const res = await api.post('/T0055I/', payload)
      await this.loadWidgets(payload.dashboard_id)
      return res.data
    },

    async updateWidget(id, payload) {
      const res = await api.put(`/T0055I/${id}`, payload)
      await this.loadWidgets(payload.dashboard_id || this.widgets.find(w => w.id === id)?.dashboard_id)
      return res.data
    },

    async deleteWidget(id, dashboardId) {
      await api.delete(`/T0055I/${id}`)
      await this.loadWidgets(dashboardId)
    }
  }
})

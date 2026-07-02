import { setActivePinia, createPinia } from 'pinia'
import { useBiStore } from '../stores/bi.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('../api/client.js', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } },
  CONFIG: { apiBase: 'http://test.local' },
}))

describe('bi store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loadKpis fetches and stores KPIs', async () => {
    const fakeKpis = [{ id: 1, name: 'Revenue', target: 100000 }]
    api.get.mockResolvedValue({ data: fakeKpis })
    const store = useBiStore()
    await store.loadKpis()
    expect(api.get).toHaveBeenCalledWith('/T0052I/')
    expect(store.kpis).toEqual(fakeKpis)
    expect(store.loading).toBe(false)
  })

  it('loadKpis handles API failure gracefully', async () => {
    api.get.mockRejectedValue(new Error('fail'))
    const store = useBiStore()
    await store.loadKpis()
    expect(store.kpis).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('createKpi posts and reloads KPIs', async () => {
    api.post.mockResolvedValue({ data: { id: 2 } })
    api.get.mockResolvedValue({ data: [{ id: 2, name: 'Test KPI' }] })
    const store = useBiStore()
    const result = await store.createKpi({ name: 'Test KPI' })
    expect(api.post).toHaveBeenCalledWith('/T0052I/', { name: 'Test KPI' })
    expect(result).toEqual({ id: 2 })
    expect(store.kpis).toEqual([{ id: 2, name: 'Test KPI' }])
  })

  it('updateKpi puts and reloads KPIs', async () => {
    api.put.mockResolvedValue({ data: { id: 1, name: 'Updated' } })
    api.get.mockResolvedValue({ data: [{ id: 1, name: 'Updated' }] })
    const store = useBiStore()
    const result = await store.updateKpi(1, { name: 'Updated' })
    expect(api.put).toHaveBeenCalledWith('/T0052I/1', { name: 'Updated' })
    expect(result).toEqual({ id: 1, name: 'Updated' })
  })

  it('deleteKpi deletes and reloads KPIs', async () => {
    api.delete.mockResolvedValue({})
    api.get.mockResolvedValue({ data: [] })
    const store = useBiStore()
    await store.deleteKpi(1)
    expect(api.delete).toHaveBeenCalledWith('/T0052I/1')
    expect(store.kpis).toEqual([])
  })

  it('loadDashboards fetches and stores dashboards', async () => {
    const fake = [{ id: 1, title: 'Sales Dashboard' }]
    api.get.mockResolvedValue({ data: fake })
    const store = useBiStore()
    await store.loadDashboards()
    expect(api.get).toHaveBeenCalledWith('/T0054I/')
    expect(store.dashboards).toEqual(fake)
    expect(store.loading).toBe(false)
  })

  it('loadDashboards handles failure gracefully', async () => {
    api.get.mockRejectedValue(new Error('fail'))
    const store = useBiStore()
    await store.loadDashboards()
    expect(store.dashboards).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('createDashboard posts and reloads dashboards', async () => {
    api.post.mockResolvedValue({ data: { id: 1 } })
    api.get.mockResolvedValue({ data: [{ id: 1, title: 'New' }] })
    const store = useBiStore()
    await store.createDashboard({ title: 'New' })
    expect(api.post).toHaveBeenCalledWith('/T0054I/', { title: 'New' })
    expect(store.dashboards).toEqual([{ id: 1, title: 'New' }])
  })

  it('deleteDashboard deletes and reloads', async () => {
    api.delete.mockResolvedValue({})
    api.get.mockResolvedValue({ data: [] })
    const store = useBiStore()
    await store.deleteDashboard(1)
    expect(api.delete).toHaveBeenCalledWith('/T0054I/1')
    expect(store.dashboards).toEqual([])
  })

  it('loadWidgets filters by dashboardId', async () => {
    const allWidgets = [
      { id: 1, dashboard_id: 5, title: 'Chart A' },
      { id: 2, dashboard_id: 9, title: 'Chart B' },
    ]
    api.get.mockResolvedValue({ data: allWidgets })
    const store = useBiStore()
    await store.loadWidgets(9)
    expect(store.widgets).toEqual([{ id: 2, dashboard_id: 9, title: 'Chart B' }])
  })

  it('createWidget posts and reloads widgets', async () => {
    api.post.mockResolvedValue({ data: { id: 3, dashboard_id: 5 } })
    api.get.mockResolvedValue({ data: [{ id: 3, dashboard_id: 5 }] })
    const store = useBiStore()
    await store.createWidget({ dashboard_id: 5, title: 'New Widget' })
    expect(api.post).toHaveBeenCalledWith('/T0055I/', { dashboard_id: 5, title: 'New Widget' })
    expect(store.widgets).toEqual([{ id: 3, dashboard_id: 5 }])
  })
})

import { setActivePinia, createPinia } from 'pinia'
import { useNavStore } from '../stores/nav.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('../api/client.js', () => ({
  api: { get: vi.fn(), post: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } },
  CONFIG: { apiBase: 'http://test.local' },
}))

describe('nav store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('getFallback returns expected structure', () => {
    const store = useNavStore()
    const fallback = store.getFallback()
    expect(Array.isArray(fallback)).toBe(true)
    expect(fallback.length).toBeGreaterThan(0)
    const sections = fallback.filter(i => i.section)
    expect(sections.length).toBeGreaterThanOrEqual(4)
    const items = fallback.filter(i => i.id)
    expect(items.length).toBeGreaterThan(0)
    expect(items[0]).toHaveProperty('id')
    expect(items[0]).toHaveProperty('icon')
    expect(items[0]).toHaveProperty('label')
    expect(items[0]).toHaveProperty('module')
  })

  it('loads nav from NavigationData.json on load()', async () => {
    const fakeNav = [{ id: 'dashboard', label: 'Dashboard', module: 'dashboard', icon: 'home' }]
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ nav: fakeNav }),
    })
    api.get.mockResolvedValue({ data: [] })
    const store = useNavStore()
    await store.load()
    expect(store.items).toEqual(fakeNav)
  })

  it('falls back to getFallback on fetch failure', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network fail'))
    api.get.mockResolvedValue({ data: [] })
    const store = useNavStore()
    await store.load()
    const fallback = store.getFallback()
    expect(store.items).toEqual(fallback)
  })

  it('loads nav style from API on load()', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ nav: [{ id: 'home', label: 'Home', module: 'home', icon: 'home' }] }),
    })
    api.get.mockResolvedValue({
      data: [{ setting_key: 'NAV_STYLE', setting_value: 'horizontal' }],
    })
    const store = useNavStore()
    await store.load()
    expect(store.navStyle).toBe('horizontal')
  })

  it('includes field-sales in navigation fallback items with correct metadata', () => {
    const store = useNavStore()
    const fallback = store.getFallback()
    const fieldSalesItem = fallback.find(i => i.id === 'field-sales')
    expect(fieldSalesItem).toBeDefined()
    expect(fieldSalesItem.label).toBe('Field Sales')
    expect(fieldSalesItem.label_ar).toBe('مبيعات الميدان')
    expect(fieldSalesItem.module).toBe('field-sales')
    expect(fieldSalesItem.permission).toBe('FIELD_SALES_MOBILE')
    expect(fieldSalesItem.icon).toBe('point_of_sale')
  })

  it('includes stock-transfers in navigation fallback items with correct metadata', () => {
    const store = useNavStore()
    const fallback = store.getFallback()
    const transferItem = fallback.find(i => i.id === 'stock-transfers')
    expect(transferItem).toBeDefined()
    expect(transferItem.label).toBe('Stock Transfers')
    expect(transferItem.label_ar).toBe('تحويلات المخزون')
    expect(transferItem.module).toBe('stock-transfers')
    expect(transferItem.permission).toBe('WAREHOUSE_VIEW')
    expect(transferItem.icon).toBe('sync_alt')
  })

  it('includes inventory-replenishment in navigation fallback items with correct metadata', () => {
    const store = useNavStore()
    const fallback = store.getFallback()
    const replenishmentItem = fallback.find(i => i.id === 'inventory-replenishment')
    expect(replenishmentItem).toBeDefined()
    expect(replenishmentItem.label).toBe('Replenishment')
    expect(replenishmentItem.label_ar).toBe('إعادة التموين')
    expect(replenishmentItem.module).toBe('inventory-replenishment')
    expect(replenishmentItem.permission).toBe('INVENTORY_VIEW')
    expect(replenishmentItem.icon).toBe('auto_mode')
  })

  it('setNavStyle updates the style', () => {
    const store = useNavStore()
    store.setNavStyle('compact')
    expect(store.navStyle).toBe('compact')
  })
})

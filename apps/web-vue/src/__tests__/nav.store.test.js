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

  it('setNavStyle updates the style', () => {
    const store = useNavStore()
    store.setNavStyle('compact')
    expect(store.navStyle).toBe('compact')
  })
})

import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../stores/auth.js'
import { api } from '../api/client.js'
import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('../api/client.js', () => ({
  api: { post: vi.fn(), get: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } },
  CONFIG: { apiBase: 'http://test.local' },
}))

const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] ?? null),
    setItem: vi.fn((key, val) => { store[key] = val }),
    removeItem: vi.fn(key => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  it('has initial state from localStorage', () => {
    localStorageMock.getItem.mockReturnValue(null)
    const store = useAuthStore()
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('reads user and token from localStorage', () => {
    localStorageMock.getItem.mockImplementation(key => {
      if (key === 'nova_token') return 'test-token'
      if (key === 'nova_user') return JSON.stringify({ id: 1, username: 'admin', permissions: ['*'], role: 'Admin' })
      return null
    })
    const store = useAuthStore()
    expect(store.token).toBe('test-token')
    expect(store.user.username).toBe('admin')
  })

  it('isLoggedIn returns true when token exists', () => {
    localStorageMock.getItem.mockImplementation(key => key === 'nova_token' ? 'tok' : null)
    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(true)
  })

  it('isLoggedIn returns false when token is null', () => {
    localStorageMock.getItem.mockReturnValue(null)
    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(false)
  })

  describe('hasPermission', () => {
    it('returns true for wildcard', () => {
      localStorageMock.getItem.mockImplementation(key =>
        key === 'nova_user' ? JSON.stringify({ permissions: ['*'] }) : null
      )
      const store = useAuthStore()
      expect(store.hasPermission('some.module')).toBe(true)
    })

    it('returns true for exact match', () => {
      localStorageMock.getItem.mockImplementation(key =>
        key === 'nova_user' ? JSON.stringify({ permissions: ['sales.read'] }) : null
      )
      const store = useAuthStore()
      expect(store.hasPermission('sales.read')).toBe(true)
    })

    it('returns false for no match', () => {
      localStorageMock.getItem.mockImplementation(key =>
        key === 'nova_user' ? JSON.stringify({ permissions: ['inventory.read'] }) : null
      )
      const store = useAuthStore()
      expect(store.hasPermission('sales.write')).toBe(false)
    })

    it('returns true when permission arg is empty', () => {
      localStorageMock.getItem.mockImplementation(key =>
        key === 'nova_user' ? JSON.stringify({ permissions: [] }) : null
      )
      const store = useAuthStore()
      expect(store.hasPermission('')).toBe(true)
      expect(store.hasPermission(null)).toBe(true)
      expect(store.hasPermission(undefined)).toBe(true)
    })
  })

  describe('login', () => {
    it('calls API and stores token and user', async () => {
      localStorageMock.getItem.mockReturnValue(null)
      const store = useAuthStore()
      api.post.mockResolvedValue({
        data: { access_token: 'new-token', user: { id: 2, username: 'test' } },
      })
      const result = await store.login('test', 'pass')
      expect(result).toBe(true)
      expect(api.post).toHaveBeenCalledWith('/auth/login', { username: 'test', password: 'pass' })
      expect(store.token).toBe('new-token')
      expect(store.user.username).toBe('test')
    })

    it('returns false on API error', async () => {
      localStorageMock.getItem.mockReturnValue(null)
      const store = useAuthStore()
      api.post.mockRejectedValue(new Error('fail'))
      const result = await store.login('test', 'wrong')
      expect(result).toBe(false)
      expect(store.token).toBeNull()
    })
  })
})

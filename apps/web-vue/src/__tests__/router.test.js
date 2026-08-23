import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import router from '../router/index.js'
import { useAuthStore } from '../stores/auth.js'

describe('Router & Field Sales Navigation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('has mobile/field-sales route registered with correct name and auth meta', () => {
    const route = router.getRoutes().find(r => r.name === 'field-sales')
    expect(route).toBeDefined()
    expect(route.path).toBe('/mobile/field-sales')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('redirects /field-sales to field-sales route', () => {
    const redirectRoute = router.getRoutes().find(r => r.path === '/field-sales')
    expect(redirectRoute).toBeDefined()
    expect(redirectRoute.redirect).toEqual({ name: 'field-sales' })
  })

  it('blocks unauthenticated user from accessing /mobile/field-sales', async () => {
    localStorage.removeItem('nova_token')
    await router.push('/mobile/field-sales')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('blocks user without FIELD_SALES_MOBILE permission and redirects to /dashboard', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'testuser', permissions: ['PRODUCTS_VIEW'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/mobile/field-sales')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('allows access to /mobile/field-sales for user with FIELD_SALES_MOBILE permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'salesrep', permissions: ['FIELD_SALES_MOBILE'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/mobile/field-sales')
    expect(router.currentRoute.value.path).toBe('/mobile/field-sales')
    expect(router.currentRoute.value.name).toBe('field-sales')
  })

  it('allows access to /mobile/field-sales for admin with wildcard permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'admin', permissions: ['*'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/mobile/field-sales')
    expect(router.currentRoute.value.path).toBe('/mobile/field-sales')
  })
})

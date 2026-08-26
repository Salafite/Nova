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

describe('Router & Stock Transfers Navigation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('has /warehouse/transfers route registered with correct name and auth meta', () => {
    const route = router.getRoutes().find(r => r.name === 'stock-transfers')
    expect(route).toBeDefined()
    expect(route.path).toBe('/warehouse/transfers')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('has /warehouse/transfers/:id route registered with correct name and auth meta', () => {
    const route = router.getRoutes().find(r => r.name === 'stock-transfer-detail')
    expect(route).toBeDefined()
    expect(route.path).toBe('/warehouse/transfers/:id')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('redirects /stock-transfers to stock-transfers route', () => {
    const redirectRoute = router.getRoutes().find(r => r.path === '/stock-transfers')
    expect(redirectRoute).toBeDefined()
    expect(redirectRoute.redirect).toEqual({ name: 'stock-transfers' })
  })

  it('blocks unauthenticated user from accessing /warehouse/transfers', async () => {
    localStorage.removeItem('nova_token')
    await router.push('/warehouse/transfers')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('blocks unauthenticated user from accessing /warehouse/transfers/42', async () => {
    localStorage.removeItem('nova_token')
    await router.push('/warehouse/transfers/42')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('blocks user without warehouse permission and redirects to /dashboard', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'testuser', permissions: ['PRODUCTS_VIEW'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/warehouse/transfers')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('allows access to /warehouse/transfers for user with WAREHOUSE_VIEW permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'logistics', permissions: ['WAREHOUSE_VIEW'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/warehouse/transfers')
    expect(router.currentRoute.value.path).toBe('/warehouse/transfers')
    expect(router.currentRoute.value.name).toBe('stock-transfers')
  })

  it('allows access to /warehouse/transfers/:id for user with warehouse permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'logistics', permissions: ['warehouse'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/warehouse/transfers/123')
    expect(router.currentRoute.value.path).toBe('/warehouse/transfers/123')
    expect(router.currentRoute.value.name).toBe('stock-transfer-detail')
    expect(router.currentRoute.value.params.id).toBe('123')
  })
})

describe('Router & Inter-Branch Replenishment Navigation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('has /inventory/replenishment route registered with correct name and auth meta', () => {
    const route = router.getRoutes().find(r => r.name === 'inventory-replenishment')
    expect(route).toBeDefined()
    expect(route.path).toBe('/inventory/replenishment')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('redirects /replenishment to inventory-replenishment route', () => {
    const redirectRoute = router.getRoutes().find(r => r.path === '/replenishment')
    expect(redirectRoute).toBeDefined()
    expect(redirectRoute.redirect).toEqual({ name: 'inventory-replenishment' })
  })

  it('blocks unauthenticated user from accessing /inventory/replenishment', async () => {
    localStorage.removeItem('nova_token')
    await router.push('/inventory/replenishment')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('blocks user without inventory permission and redirects to /dashboard', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'testuser', permissions: ['CRM_VIEW'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/inventory/replenishment')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('allows access to /inventory/replenishment for user with INVENTORY_VIEW permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'invmgr', permissions: ['INVENTORY_VIEW'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/inventory/replenishment')
    expect(router.currentRoute.value.path).toBe('/inventory/replenishment')
    expect(router.currentRoute.value.name).toBe('inventory-replenishment')
  })

  it('allows access to /inventory/replenishment for user with inventory permission', async () => {
    localStorage.setItem('nova_token', 'test-token')
    const auth = useAuthStore()
    auth.user = { id: 1, username: 'invmgr', permissions: ['inventory'] }
    localStorage.setItem('nova_user', JSON.stringify(auth.user))

    await router.push('/inventory/replenishment')
    expect(router.currentRoute.value.path).toBe('/inventory/replenishment')
    expect(router.currentRoute.value.name).toBe('inventory-replenishment')
  })
})

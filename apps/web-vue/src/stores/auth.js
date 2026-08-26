import { defineStore } from 'pinia'
import { api } from '../api/client.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('nova_user') || 'null'),
    token: localStorage.getItem('nova_token') || null,
  }),
  getters: {
    isLoggedIn: state => !!state.token,
    permissions: state => state.user?.permissions || [],
    role: state => state.user?.role || '',
    businessId: state => state.user?.business_id || null,
    customerId: state => state.user?.customer_id || null,
    isPortalCustomer: state => state.user?.role === 'Customer' || !!state.user?.customer_id,
  },
  actions: {
    async fetchUser() {
      if (!this.token) return null
      try {
        const res = await api.get('/auth/me')
        if (res && res.data) {
          this.user = res.data
          localStorage.setItem('nova_user', JSON.stringify(this.user))
        }
        return this.user
      } catch {
        return null
      }
    },
    async login(username, password) {
      try {
        const res = await api.post('/auth/login', { username, password })
        this.token = res.data.access_token
        this.user = res.data.user
        localStorage.setItem('nova_token', this.token)
        localStorage.setItem('nova_user', JSON.stringify(this.user))
        try {
          const meRes = await api.get('/auth/me')
          if (meRes && meRes.data) {
            this.user = meRes.data
            localStorage.setItem('nova_user', JSON.stringify(this.user))
          }
        } catch {
          // Keep user from login response if /auth/me fails
        }
        return true
      } catch { return false }
    },
    async signup(payload) {
      const res = await api.post('/auth/signup', payload)
      this.token = res.data.access_token
      this.user = res.data.user
      localStorage.setItem('nova_token', this.token)
      localStorage.setItem('nova_user', JSON.stringify(this.user))
      try {
        const meRes = await api.get('/auth/me')
        if (meRes && meRes.data) {
          this.user = meRes.data
          localStorage.setItem('nova_user', JSON.stringify(this.user))
        }
      } catch {
        // Keep user from signup response if /auth/me fails
      }
    },
    async restoreAuth() {
      if (this.token) {
        return await this.fetchUser()
      }
      return null
    },
    async invite(payload) {
      const res = await api.post('/auth/invite', payload)
      return res.data
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
    },
    hasPermission(p) {
      if (!p) return true
      if (this.permissions.includes('*')) return true
      if (p.toLowerCase() === 'portal' && (
        this.permissions.includes('PORTAL_VIEW') ||
        this.permissions.includes('PORTAL_ORDER') ||
        this.permissions.includes('PORTAL_PAY') ||
        this.permissions.includes('portal') ||
        this.role === 'Customer'
      )) {
        return true
      }
      return this.permissions.includes(p) ||
        this.permissions.includes(p.toUpperCase()) ||
        this.permissions.includes(p.toLowerCase())
    }
  }
})

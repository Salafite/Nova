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
  },
  actions: {
    async login(username, password) {
      try {
        const res = await api.post('/auth/login', { username, password })
        this.token = res.data.access_token
        this.user = res.data.user
        localStorage.setItem('nova_token', this.token)
        localStorage.setItem('nova_user', JSON.stringify(this.user))
        return true
      } catch { return false }
    },
    async signup(payload) {
      const res = await api.post('/auth/signup', payload)
      this.token = res.data.access_token
      this.user = res.data.user
      localStorage.setItem('nova_token', this.token)
      localStorage.setItem('nova_user', JSON.stringify(this.user))
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
      return this.permissions.includes('*') || this.permissions.includes(p)
    }
  }
})

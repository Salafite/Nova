const CurrentUser = { role: '', permissions: [] }

const Permission = {
  can(p) {
    if (!p) return true
    return CurrentUser.permissions.includes('*') || CurrentUser.permissions.includes(p)
  },
  filterNav(items) {
    return items.filter(item => {
      if (item.section) return true
      return this.can(item.permission)
    })
  }
}

const Auth = {
  async login(username, password) {
    const url = (CONFIG.apiBase || '') + '/api/auth/login'
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      if (!res.ok) return false
      const authResult = await res.json()
      localStorage.setItem('nova_token', authResult.access_token)
      CurrentUser.role = authResult.user.role
      CurrentUser.permissions = authResult.user.permissions
      localStorage.setItem('nova_user', JSON.stringify({ role: authResult.user.role, permissions: authResult.user.permissions }))
      return true
    } catch (e) {
      console.warn('Login error', e)
      return false
    }
  },
  logout() {
    CurrentUser.role = ''
    CurrentUser.permissions = []
    localStorage.removeItem('nova_token')
    localStorage.removeItem('nova_user')
  },
  async restoreSession() {
    try {
      const saved = localStorage.getItem('nova_user')
      const token = localStorage.getItem('nova_token')
      if (!saved || !token) return false
      const sessionData = JSON.parse(saved)
      CurrentUser.role = sessionData.role
      CurrentUser.permissions = sessionData.permissions
      return true
    } catch (e) {
      console.warn('Session restore error', e)
      return false
    }
  },
  get isLoggedIn() {
    return CurrentUser.permissions.length > 0
  }
}

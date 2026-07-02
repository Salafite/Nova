class ApiClient {
  constructor(tableId) {
    this.base = (CONFIG.apiBase || '') + '/api/' + tableId.replace(/^\/?api\//, '')
  }

  _headers() {
    const h = { 'Content-Type': 'application/json' }
    const token = ApiClient.getToken()
    if (token) h['Authorization'] = 'Bearer ' + token
    return h
  }

  list(filters) {
    const params = filters ? '?' + new URLSearchParams(filters).toString() : ''
    return this._fetch(this.base + '/' + params)
  }

  get(id) {
    return this._fetch(this.base + '/' + id)
  }

  create(data) {
    return this._fetch(this.base + '/', {
      method: 'POST',
      body: JSON.stringify(ApiClient._snake(data)),
    })
  }

  update(id, data) {
    return this._fetch(this.base + '/' + id, {
      method: 'PUT',
      body: JSON.stringify(ApiClient._snake(data)),
    })
  }

  delete(id) {
    return this._fetch(this.base + '/' + id, { method: 'DELETE' })
  }

  async _fetch(url, options) {
    options = options || {}
    options.headers = Object.assign(this._headers(), options.headers || {})
    try {
      const res = await fetch(url, options)
      if (res.status === 401) {
        localStorage.removeItem('nova_token')
        localStorage.removeItem('nova_user')
        if (typeof Auth !== 'undefined' && Auth.logout) Auth.logout()
        if (typeof app !== 'undefined' && app.renderAuth) app.renderAuth('login')
        throw new Error('Session expired')
      }
      if (!res.ok) {
        const err = await res.text()
        throw new Error(res.status + ': ' + err)
      }
      const text = await res.text()
      if (!text) return null
      return ApiClient._camel(JSON.parse(text))
    } catch (e) {
      if (e.message === 'Session expired') throw e
      throw new Error('API call failed: ' + e.message)
    }
  }

  static getToken() {
    try { return localStorage.getItem('nova_token') } catch (e) { console.warn('Failed to read token', e); return null }
  }

  static setToken(token) {
    if (token) localStorage.setItem('nova_token', token)
    else localStorage.removeItem('nova_token')
  }

  static _camel(o) {
    if (Array.isArray(o)) return o.map(ApiClient._camel)
    if (o && typeof o === 'object') {
      return Object.fromEntries(
        Object.entries(o).map(([k, v]) => [k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()), ApiClient._camel(v)])
      )
    }
    return o
  }

  static _snake(o) {
    if (Array.isArray(o)) return o.map(ApiClient._snake)
    if (o && typeof o === 'object') {
      return Object.fromEntries(
        Object.entries(o).map(([k, v]) => [k.replace(/[A-Z]/g, c => '_' + c.toLowerCase()), ApiClient._snake(v)])
      )
    }
    return o
  }
}

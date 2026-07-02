window.ModuleRegistryService = class ModuleRegistryService {
  constructor() {
    this.api = new ApiClient('T0100I')
    this._installed = []
    this._available = []
  }

  async load() {
    try {
      this._installed = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load installed modules', e)
      this._installed = []
    }
  }

  getInstalled() { return this._installed }

  async discover() {
    try {
      var res = await fetch(this.api.base + '/discover', { headers: this.api._headers() })
      this._available = await res.json()
    } catch (e) {
      console.warn('Failed to discover modules', e)
      this._available = []
    }
    return this._available
  }

  async install(moduleKey) {
    var res = await fetch(this.api.base + '/' + encodeURIComponent(moduleKey) + '/install', { method: 'POST', headers: this.api._headers() })
    var result = await res.json()
    if (result.ok) {
      this._installed.push(result.module)
    }
    return result
  }

  async uninstall(id) {
    var res = await fetch(this.api.base + '/' + id + '/uninstall', { method: 'POST', headers: this.api._headers() })
    var result = await res.json()
    if (result.ok) {
      this._installed = this._installed.filter(function(m) { return m.id !== id })
    }
    return result
  }

  async toggle(id, isActive) {
    var res = await fetch(this.api.base + '/' + id + '/toggle', { method: 'PUT', headers: this.api._headers(), body: JSON.stringify({ is_active: isActive }) })
    var result = await res.json()
    if (result.ok) {
      var idx = this._installed.findIndex(function(m) { return m.id === id })
      if (idx !== -1) this._installed[idx] = result.module
    }
    return result
  }
}

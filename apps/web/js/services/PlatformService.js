window.PlatformService = class PlatformService {
  constructor() {
    this.api = new ApiClient('T0064I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load platform services', e)
      this._data = []
    }
  }
  getAll() { return this._data }
  getById(id) { return this._data.find(function(x) { return x.id == id }) }
  getHealthyCount() {
    return this._data.filter(function(x) { return x.status === 'Healthy' || x.status === 'Online' }).length
  }
  getVersion() {
    return this._data.length ? (this._data[0].version || '1.0.0') : '1.0.0'
  }
}

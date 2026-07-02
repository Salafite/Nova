window.ServiceManagementService = class ServiceManagementService {
  constructor() {
    this.api = new ApiClient('T0048I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load service requests', e)
      this._data = []
    }
  }
  getAll() { return this._data }
  getById(id) { return this._data.find(function(x) { return x.id == id }) }
  async create(payload) {
    var item = await this.api.create(payload)
    this._data.push(item)
    return item
  }
  async update(id, payload) {
    var item = await this.api.update(id, payload)
    var i = this._data.findIndex(function(x) { return x.id == id })
    if (i > -1) this._data[i] = item
    return item
  }
  async remove(id) {
    await this.api.delete(id)
    this._data = this._data.filter(function(x) { return x.id != id })
  }
  getOpenCount() {
    return this._data.filter(function(x) { return x.status !== 'Resolved' && x.status !== 'Closed' }).length
  }
  getSlaCompliance() {
    if (!this._data.length) return 100
    var within = this._data.filter(function(x) { return x.slaCompliant !== false }).length
    return Math.round(within / this._data.length * 100)
  }
  getAvgResponseTime() {
    var withResponse = this._data.filter(function(x) { return x.responseTime })
    if (!withResponse.length) return 0
    var total = withResponse.reduce(function(s, x) { return s + (parseFloat(x.responseTime) || 0) }, 0)
    return (total / withResponse.length).toFixed(1)
  }
}

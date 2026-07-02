window.ResourcePlanningService = class ResourcePlanningService {
  constructor() {
    this.api = new ApiClient('T0046I')
    this._data = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load resource allocations', e)
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
  getUtilizationRate() {
    if (!this._data.length) return 0
    var allocated = this._data.filter(function(x) { return x.status === 'Allocated' || x.status === 'Active' }).length
    return Math.round(allocated / this._data.length * 100)
  }
  getAvailableCount() {
    return this._data.filter(function(x) { return x.status === 'Available' }).length
  }
}

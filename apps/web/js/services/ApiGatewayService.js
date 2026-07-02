window.ApiGatewayService = class ApiGatewayService {
  constructor() {
    this.api = new ApiClient('T0061I')
    this._data = []
    this._endpoints = []
  }
  async load() {
    try {
      this._data = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load API gateway data', e)
      this._data = []
    }
    try {
      var epApi = new ApiClient('T0062I')
      this._endpoints = await epApi.list() || []
    } catch (e) {
      console.warn('Failed to load API endpoints', e)
      this._endpoints = []
    }
  }
  getAll() { return this._data }
  getEndpoints() { return this._endpoints }
  async create(payload) {
    var item = await this.api.create(payload)
    this._data.push(item)
    return item
  }
  async remove(id) {
    await this.api.delete(id)
    this._data = this._data.filter(function(x) { return x.id != id })
  }
}
